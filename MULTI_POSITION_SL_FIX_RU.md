# Анализ и решение проблемы преждевременного закрытия позиций 2 и 3 по Stop Loss

## 🔍 Анализ проблемы

### Описание ситуации
Торговый бот открывает группу из 3 позиций (TP1, TP2, TP3) с одного сигнала:
- **Позиция 1 (TP1)**: Работает нормально
- **Позиции 2 и 3 (TP2, TP3)**: Закрываются почти сразу по Stop Loss

### Наиболее вероятные причины

#### 1. **RACE CONDITION между open → modify → sync** ⚠️ КРИТИЧНО
**Вероятность: 95%**

**Суть проблемы:**
- Позиции открываются последовательно с задержкой 0.2 секунды (строка 2414)
- В ЭТОМ ЖЕ цикле мониторинга вызывается `_update_3position_trailing()` (строка 1103)
- Трейлинг-логика срабатывает **ДО** того, как позиции полностью подтверждены брокером
- SL для позиций 2 и 3 модифицируется слишком рано

**Код проблемы:**
```python
# live_bot_mt5_fullauto.py, строка 1102-1103
# Phase 2: Update trailing stops for 3-position groups
self._update_3position_trailing({ticket: tracked_pos}, current_price)
```

Эта функция вызывается для **КАЖДОЙ** открытой позиции при каждой проверке, **без учёта**:
- Времени с момента открытия
- Подтверждения от брокера
- Статуса синхронизации с MT5

#### 2. **Неправильный reference price (bid/ask)**
**Вероятность: 30%**

Для BUY позиций:
- Открытие по ASK (более высокая цена)
- Закрытие и проверка SL по BID (более низкая цена)
- Спред может составлять 0.3-0.5 пункта для XAUUSD
- Если SL рассчитан относительно ASK, но проверяется относительно BID - возможно преждевременное срабатывание

#### 3. **Trailing SL применяется сразу после открытия**
**Вероятность: 80%** ⚠️ КРИТИЧНО

**Логика ошибки:**
```python
# _update_3position_trailing, строка 700-716
if not group_info['tp1_hit']:  # Only check if not already hit
    # Activate trailing if position 1 is being closed/processed
    if pos1_status != 'OPEN':
        group_info['tp1_hit'] = True
```

**Проблема:** Нет проверки на минимальное время после открытия. Трейлинг может активироваться в том же цикле, что и открытие позиций.

#### 4. **SL пересчитан до подтверждения позиции брокером**
**Вероятность: 70%**

Последовательность событий:
1. `mt5.order_send()` отправляет ордер - возвращает `result.order`
2. Позиция добавляется в `positions_tracker` и БД
3. В следующем цикле (через 0-5 секунд) вызывается `_check_tp_sl_realtime()`
4. `_update_3position_trailing()` вызывается для позиций, которые **ещё могут быть не подтверждены** на сервере MT5

#### 5. **Shared state между позициями**
**Вероятность: 50%**

```python
# Все 3 позиции используют общий group_id и общие max_price/min_price
self.position_groups[group_id] = {
    'tp1_hit': False,
    'max_price': entry_price,
    'min_price': entry_price,
    'positions': [p[0] for p in group_positions],
    ...
}
```

Если несколько потоков/циклов обращаются к `position_groups[group_id]` одновременно - возможна гонка данных.

#### 6. **Ошибка округления / min stop level / tick size**
**Вероятность: 60%**

Для XAUUSD:
- Минимальный stop level у многих брокеров: 50-200 пунктов (0.50-2.00$)
- Tick size: 0.01
- Если рассчитанный SL слишком близко к цене входа - брокер может **округлить** его или **отклонить** модификацию

**Проверка в коде (строка 794-802):**
```python
# For BUY: SL must be at least min_distance below current price
if new_sl > (current_price - min_distance):
    # SL too close to current price - skip this update
    print(f"   ⚠️  SL too close to price (${current_price:.2f}), skipping update")
    continue
```

**Проблема:** Эта проверка выполняется для **уже открытых** позиций при трейлинге, но **НЕ** проверяется при первоначальном открытии!

#### 7. **Partial Open (1/3)**
**Вероятность: 40%**

```python
# Код открывает 3 позиции последовательно
for tp_price, lot_size, tp_name, tp_distance, pos_num in tp_levels:
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"   ❌ {tp_name} order failed!")
        continue  # Продолжает открывать следующие позиции
```

Если открылась только 1 позиция из 3:
- `group_id` создаётся в БД
- Логика трейлинга пытается найти все 3 позиции
- Может произойти сбой в инициализации группы

---

## 🔬 Необходимые проверки и логи

### 1. Добавить детальное логирование времени событий

```python
def _open_3_positions(self, signal):
    # ...
    import time
    timestamp_group_created = time.time()
    
    for tp_price, lot_size, tp_name, tp_distance, pos_num in tp_levels:
        timestamp_before_send = time.time()
        result = mt5.order_send(request)
        timestamp_after_send = time.time()
        
        print(f"   ⏱️  {tp_name} order execution time: {timestamp_after_send - timestamp_before_send:.3f}s")
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            # Log to tracker with timestamp
            self.positions_tracker[result.order] = {
                'opened_at': time.time(),  # ⬅️ ДОБАВИТЬ ЭТО
                'confirmed_at': None,      # ⬅️ ДОБАВИТЬ ЭТО
                ...
            }
```

### 2. Логировать каждое изменение SL

```python
def _update_3position_trailing(self, positions_to_check, current_price):
    # В начале функции:
    print(f"\n{'='*60}")
    print(f"🔄 TRAILING STOP CHECK - {datetime.now()}")
    print(f"   Current price: {current_price:.2f}")
    print(f"   Positions to check: {list(positions_to_check.keys())}")
    print(f"{'='*60}")
    
    # При каждом изменении SL:
    if new_sl > pos_data['sl']:
        print(f"\n⚠️  ATTEMPTING SL MODIFICATION:")
        print(f"   Position: #{ticket}, Type: {pos_data['type']}")
        print(f"   Entry: {entry_price:.2f}")
        print(f"   Current price: {current_price:.2f}")
        print(f"   Old SL: {old_sl:.2f}")
        print(f"   New SL: {new_sl:.2f}")
        print(f"   Distance from entry: {abs(new_sl - entry_price):.2f}")
        print(f"   Distance from current: {abs(current_price - new_sl):.2f}")
        print(f"   Min required distance: {min_distance:.2f}")
```

### 3. Проверка синхронизации с MT5

```python
def _verify_position_on_mt5(self, ticket):
    """Проверить, что позиция действительно открыта на MT5"""
    positions = mt5.positions_get(ticket=ticket)
    if positions and len(positions) > 0:
        pos = positions[0]
        return {
            'exists': True,
            'sl': pos.sl,
            'tp': pos.tp,
            'price_open': pos.price_open,
            'time_create': pos.time,
        }
    return {'exists': False}
```

### 4. Проверка расстояния SL от цены входа

```python
def _validate_sl_distance(self, entry_price, sl_price, position_type, symbol):
    """Валидация минимального расстояния SL"""
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return False, "Symbol info not available"
    
    # Минимальное расстояние
    stop_level = symbol_info.trade_stops_level
    point = symbol_info.point
    min_distance = stop_level * point
    
    # Расстояние от entry до SL
    sl_distance = abs(entry_price - sl_price)
    
    # Дополнительная проверка: минимум 0.5% от цены входа для XAUUSD
    min_distance_pct = entry_price * 0.005  # 0.5%
    
    if sl_distance < min_distance:
        return False, f"SL too close (broker stop level): {sl_distance:.2f} < {min_distance:.2f}"
    
    if sl_distance < min_distance_pct:
        return False, f"SL too close (0.5% rule): {sl_distance:.2f} < {min_distance_pct:.2f}"
    
    return True, "OK"
```

### 5. Лог состояния группы позиций

```python
def _log_position_group_state(self, group_id):
    """Логировать полное состояние группы позиций"""
    if group_id not in self.position_groups:
        print(f"⚠️  Group {group_id[:8]} not found in memory")
        return
    
    group = self.position_groups[group_id]
    print(f"\n📊 POSITION GROUP STATE: {group_id[:8]}")
    print(f"   TP1 hit: {group['tp1_hit']}")
    print(f"   Entry: {group['entry_price']:.2f}")
    print(f"   Max price: {group['max_price']:.2f}")
    print(f"   Min price: {group['min_price']:.2f}")
    print(f"   Trade type: {group['trade_type']}")
    print(f"   Positions: {group['positions']}")
    
    for ticket in group['positions']:
        if ticket in self.positions_tracker:
            pos = self.positions_tracker[ticket]
            print(f"   Position #{ticket}:")
            print(f"      SL: {pos['sl']:.2f}, TP: {pos['tp']:.2f}")
            print(f"      Status: {pos.get('status', 'UNKNOWN')}")
```

---

## 🏗️ Правильная архитектура

### Принципы изоляции TP1 / TP2 / TP3

#### 1. **Фазы жизненного цикла позиции**

```python
POSITION_PHASES = {
    'OPENING': 'Position order sent, waiting for broker confirmation',
    'CONFIRMED': 'Position confirmed by broker, no modifications allowed yet',
    'ACTIVE': 'Position active, normal monitoring',
    'TRAILING_ACTIVE': 'Trailing stop enabled for this position',
    'CLOSING': 'TP/SL hit, position being closed',
    'CLOSED': 'Position fully closed'
}
```

#### 2. **Временные ограничения**

```python
# Константы для защиты от преждевременных модификаций
MIN_POSITION_AGE_FOR_TRAILING = 60  # секунд - минимум 1 минута после открытия
MIN_POSITION_AGE_FOR_SL_MODIFY = 30  # секунд - минимум 30 секунд до любой модификации SL
BROKER_CONFIRMATION_TIMEOUT = 10    # секунд - ожидание подтверждения от брокера
```

#### 3. **Изолированное управление каждой позицией**

```python
class PositionManager:
    """Управление индивидуальной позицией с полной изоляцией"""
    
    def __init__(self, ticket, entry_price, sl, tp, position_type, position_num, group_id):
        self.ticket = ticket
        self.entry_price = entry_price
        self.sl = sl
        self.tp = tp
        self.position_type = position_type  # 'BUY' or 'SELL'
        self.position_num = position_num    # 1, 2, or 3
        self.group_id = group_id
        
        # Временные метки
        self.created_at = time.time()
        self.confirmed_at = None
        self.last_sl_modify_at = None
        
        # Состояние
        self.phase = 'OPENING'
        self.trailing_enabled = False
        
        # Защита от модификаций
        self._modification_lock = threading.Lock()
    
    def can_modify_sl(self) -> tuple[bool, str]:
        """Проверка, можно ли модифицировать SL"""
        # Проверка 1: Позиция подтверждена брокером
        if self.phase == 'OPENING':
            return False, "Position not confirmed by broker yet"
        
        # Проверка 2: Прошло достаточно времени с момента открытия
        age = time.time() - self.created_at
        if age < MIN_POSITION_AGE_FOR_SL_MODIFY:
            return False, f"Position too young: {age:.1f}s < {MIN_POSITION_AGE_FOR_SL_MODIFY}s"
        
        # Проверка 3: Для позиций 2 и 3 - трейлинг должен быть активирован
        if self.position_num in [2, 3] and not self.trailing_enabled:
            return False, "Trailing not enabled yet (TP1 not hit)"
        
        # Проверка 4: Не слишком частые модификации
        if self.last_sl_modify_at:
            time_since_last = time.time() - self.last_sl_modify_at
            if time_since_last < 10:  # минимум 10 секунд между модификациями
                return False, f"SL modified too recently: {time_since_last:.1f}s ago"
        
        return True, "OK"
    
    def enable_trailing(self):
        """Активировать трейлинг (только для позиций 2 и 3)"""
        if self.position_num not in [2, 3]:
            return False, "Trailing only for positions 2 and 3"
        
        age = time.time() - self.created_at
        if age < MIN_POSITION_AGE_FOR_TRAILING:
            return False, f"Position too young for trailing: {age:.1f}s"
        
        self.trailing_enabled = True
        print(f"✅ Trailing enabled for position #{self.ticket} (Pos {self.position_num})")
        return True, "OK"
```

### Когда именно разрешать SL-modification

```python
def _update_3position_trailing(self, positions_to_check, current_price):
    """
    Обновление трейлинг-стопов с защитой от преждевременной активации
    """
    if not self.use_3_position_mode or not self.use_trailing_stops:
        return
    
    # Group positions by position_group_id
    groups = {}
    for ticket, pos_data in positions_to_check.items():
        group_id = pos_data.get('position_group_id')
        if not group_id:
            continue
        
        if group_id not in groups:
            groups[group_id] = []
        groups[group_id].append((ticket, pos_data))
    
    # Process each group
    for group_id, group_positions in groups.items():
        # ===== КРИТИЧЕСКАЯ ПРОВЕРКА #1: Возраст группы =====
        if group_id in self.position_groups:
            group_created_at = self.position_groups[group_id].get('created_at', 0)
            group_age = time.time() - group_created_at
            
            # НЕ МОДИФИЦИРОВАТЬ SL в течение первых 60 секунд после создания группы
            if group_age < MIN_POSITION_AGE_FOR_TRAILING:
                # Молчаливо пропустить (не спамить логи)
                continue
        
        # Initialize group tracking if needed
        if group_id not in self.position_groups:
            # ... существующий код инициализации ...
            self.position_groups[group_id]['created_at'] = time.time()  # ⬅️ ДОБАВИТЬ
        
        group_info = self.position_groups[group_id]
        
        # Update max/min price
        # ... существующий код ...
        
        # ===== КРИТИЧЕСКАЯ ПРОВЕРКА #2: TP1 действительно достигнут =====
        # Проверить не только флаг, но и РЕАЛЬНОЕ состояние позиции 1
        tp1_confirmed_hit = False
        
        # Найти позицию 1
        pos1_ticket = None
        for ticket, pos_data in group_positions:
            if pos_data.get('position_num') == 1:
                pos1_ticket = ticket
                break
        
        if pos1_ticket:
            # Позиция 1 ещё открыта - TP1 точно НЕ достигнут
            tp1_confirmed_hit = False
        else:
            # Позиция 1 закрыта - проверить в истории, что это был именно TP1
            if self.use_database and self.db:
                try:
                    # Получить историю позиции 1
                    closed_trade = self.db.get_trade_by_order_id(str(pos1_ticket))
                    if closed_trade and closed_trade.status in ['TP1', 'TP1_PROCESSING']:
                        tp1_confirmed_hit = True
                except:
                    pass
        
        # Если TP1 НЕ подтверждён - НЕ активировать трейлинг
        if not tp1_confirmed_hit:
            continue
        
        # Теперь активировать трейлинг для позиций 2 и 3
        group_info['tp1_hit'] = True
        
        # ===== КРИТИЧЕСКАЯ ПРОВЕРКА #3: Возраст каждой позиции =====
        for ticket, pos_data in group_positions:
            pos_num = pos_data.get('position_num', 0)
            if pos_num not in [2, 3]:
                continue
            
            # Проверить возраст позиции
            if ticket in self.positions_tracker:
                pos_created = self.positions_tracker[ticket].get('opened_at', 0)
                if pos_created > 0:
                    pos_age = time.time() - pos_created
                    if pos_age < MIN_POSITION_AGE_FOR_TRAILING:
                        print(f"   ⏳ Position #{ticket} too young for trailing: {pos_age:.1f}s")
                        continue
            
            # Теперь безопасно модифицировать SL
            # ... существующий код модификации SL ...
```

### Защита от premature trailing stop

```python
def _safe_modify_sl(self, ticket, new_sl, current_price, position_type):
    """
    Безопасная модификация SL с множественными проверками
    
    Returns:
        (success: bool, message: str)
    """
    # Проверка 1: Позиция существует на MT5
    mt5_pos = mt5.positions_get(ticket=ticket)
    if not mt5_pos or len(mt5_pos) == 0:
        return False, "Position not found on MT5"
    
    pos = mt5_pos[0]
    entry_price = pos.price_open
    current_sl = pos.sl
    
    # Проверка 2: Новый SL отличается от текущего
    if abs(new_sl - current_sl) < 0.01:  # меньше 1 цента
        return False, "New SL same as current SL"
    
    # Проверка 3: Новый SL лучше старого
    if position_type == 'BUY':
        if new_sl <= current_sl:
            return False, f"New SL not better: {new_sl:.2f} <= {current_sl:.2f}"
    else:  # SELL
        if new_sl >= current_sl:
            return False, f"New SL not better: {new_sl:.2f} >= {current_sl:.2f}"
    
    # Проверка 4: Расстояние от текущей цены
    symbol_info = mt5.symbol_info(self.symbol)
    if symbol_info:
        stop_level = symbol_info.trade_stops_level
        point = symbol_info.point
        min_distance = max(stop_level * point, entry_price * 0.002)  # минимум 0.2%
        
        actual_distance = abs(current_price - new_sl)
        if actual_distance < min_distance:
            return False, f"SL too close to price: {actual_distance:.2f} < {min_distance:.2f}"
    
    # Проверка 5: Расстояние от цены входа (минимум 0.3%)
    min_distance_from_entry = entry_price * 0.003
    actual_distance_from_entry = abs(entry_price - new_sl)
    if actual_distance_from_entry < min_distance_from_entry:
        return False, f"SL too close to entry: {actual_distance_from_entry:.2f} < {min_distance_from_entry:.2f}"
    
    # Выполнить модификацию
    try:
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": pos.tp,
            "symbol": self.symbol,
            "magic": 234000,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            # Обновить время последней модификации
            if ticket in self.positions_tracker:
                self.positions_tracker[ticket]['last_sl_modify_at'] = time.time()
            
            print(f"   ✅ SL modified successfully: {current_sl:.2f} → {new_sl:.2f}")
            return True, "OK"
        else:
            error = result.comment if result else "No result"
            return False, f"MT5 error: {error}"
            
    except Exception as e:
        return False, f"Exception: {str(e)}"
```

### Как работать с partial opens (1/3)

```python
def _open_3_positions(self, signal):
    """Открытие 3 позиций с обработкой частичного открытия"""
    # ... начальный код ...
    
    # Открыть позиции
    positions_opened = []
    failed_positions = []
    
    for tp_price, lot_size, tp_name, tp_distance, pos_num in tp_levels:
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            positions_opened.append({
                'ticket': result.order,
                'tp_name': tp_name,
                'position_num': pos_num,
                'opened_at': time.time()
            })
            print(f"   ✅ {tp_name} opened: #{result.order}")
        else:
            failed_positions.append({
                'tp_name': tp_name,
                'position_num': pos_num,
                'error': result.comment if result else 'No result'
            })
            print(f"   ❌ {tp_name} failed: {result.comment if result else 'No result'}")
        
        time.sleep(0.2)
    
    # ===== КРИТИЧЕСКАЯ ПРОВЕРКА: Обработка частичного открытия =====
    total_opened = len(positions_opened)
    
    if total_opened == 0:
        print(f"\n❌ FAILED: No positions opened")
        return False
    
    if total_opened < 3:
        print(f"\n⚠️  WARNING: Partial open - {total_opened}/3 positions opened")
        print(f"   Opened: {[p['tp_name'] for p in positions_opened]}")
        print(f"   Failed: {[p['tp_name'] for p in failed_positions]}")
        
        # ВАРИАНТ 1: Закрыть частично открытые позиции
        if total_opened == 1:
            print(f"   ⚠️  Only 1 position opened - UNSAFE for 3-position strategy")
            print(f"   → Closing the single position to avoid issues")
            
            for pos in positions_opened:
                self._close_position_immediately(pos['ticket'], "Partial open - safety close")
            
            return False
        
        # ВАРИАНТ 2: Продолжить с частичным открытием (2 позиции)
        elif total_opened == 2:
            print(f"   ⚠️  2/3 positions opened - can proceed with reduced strategy")
            # Создать группу только для открытых позиций
            # НЕ активировать трейлинг, если отсутствует позиция 1
            if not any(p['position_num'] == 1 for p in positions_opened):
                print(f"   ❌ Position 1 (TP1) not opened - cannot use 3-position strategy")
                print(f"   → Closing opened positions")
                for pos in positions_opened:
                    self._close_position_immediately(pos['ticket'], "No TP1 - safety close")
                return False
    
    # Сохранить группу в БД с флагом partial_open
    if self.use_database and self.db:
        try:
            PositionGroup = self._get_position_group_model()
            if PositionGroup:
                new_group = PositionGroup(
                    group_id=group_id,
                    bot_id=self.bot_id,
                    tp1_hit=False,
                    entry_price=signal['entry'],
                    max_price=signal['entry'],
                    min_price=signal['entry'],
                    trade_type=direction_str,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    partial_open=(total_opened < 3),  # ⬅️ ДОБАВИТЬ
                    positions_count=total_opened       # ⬅️ ДОБАВИТЬ
                )
                self.db.save_position_group(new_group)
        except Exception as e:
            print(f"⚠️  Failed to save position group: {e}")
    
    return True

def _close_position_immediately(self, ticket, reason):
    """Немедленно закрыть позицию"""
    try:
        pos = mt5.positions_get(ticket=ticket)
        if not pos or len(pos) == 0:
            return False
        
        pos = pos[0]
        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": ticket,
            "price": mt5.symbol_info_tick(self.symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(self.symbol).ask,
            "deviation": 20,
            "magic": 234000,
            "comment": reason,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_mode(),
        }
        
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   ✅ Position #{ticket} closed: {reason}")
            return True
        else:
            print(f"   ❌ Failed to close position #{ticket}: {result.comment if result else 'No result'}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error closing position #{ticket}: {e}")
        return False
```

---

## 📝 Псевдокод правильной логики

### Открытие позиций

```python
def open_3_position_group(signal):
    """
    Псевдокод: Правильное открытие группы из 3 позиций
    """
    # 1. Создать уникальный group_id
    group_id = generate_uuid()
    timestamp_start = current_time()
    
    # 2. Проверить доступность слотов
    if available_position_slots() < 3:
        log_error("Not enough slots for 3 positions")
        return FAILURE
    
    # 3. Рассчитать размеры позиций
    total_lot = calculate_position_size(signal.entry, signal.sl, risk_percent)
    lot1 = total_lot * 0.33
    lot2 = total_lot * 0.33
    lot3 = total_lot * 0.34
    
    # 4. Валидировать минимальные размеры
    if lot1 < broker_min_lot OR lot2 < broker_min_lot OR lot3 < broker_min_lot:
        log_error("Position sizes too small for 3-position strategy")
        return FAILURE
    
    # 5. Валидировать SL distance от entry
    sl_distance = abs(signal.entry - signal.sl)
    min_sl_distance = max(
        broker_stop_level * point,
        signal.entry * 0.005  # минимум 0.5%
    )
    
    if sl_distance < min_sl_distance:
        log_error(f"SL too close to entry: {sl_distance} < {min_sl_distance}")
        return FAILURE
    
    # 6. Открыть позиции последовательно
    opened_positions = []
    
    for position_num in [1, 2, 3]:
        tp_price = signal.tp1 if position_num == 1 else (signal.tp2 if position_num == 2 else signal.tp3)
        lot_size = lot1 if position_num == 1 else (lot2 if position_num == 2 else lot3)
        
        # Отправить ордер
        result = broker.send_order(
            symbol=symbol,
            volume=lot_size,
            type=BUY or SELL,
            sl=signal.sl,  # ⬅️ Исходный SL для ВСЕХ позиций
            tp=tp_price,
            comment=f"V3_P{position_num}/3"
        )
        
        if result.success:
            opened_positions.append({
                'ticket': result.ticket,
                'position_num': position_num,
                'opened_at': current_time(),
                'confirmed_at': NULL,  # будет установлено после проверки
                'sl': signal.sl,
                'tp': tp_price,
                'entry_price': result.price,
                'phase': 'OPENING'
            })
            
            log_success(f"Position {position_num} opened: #{result.ticket}")
        else:
            log_error(f"Position {position_num} failed: {result.error}")
        
        sleep(0.3)  # Задержка между ордерами
    
    # 7. Обработать результат
    if len(opened_positions) == 0:
        log_error("No positions opened - ABORT")
        return FAILURE
    
    if len(opened_positions) < 3:
        log_warning(f"Partial open: {len(opened_positions)}/3")
        
        # Если нет позиции 1 - закрыть всё
        if not has_position_1(opened_positions):
            log_error("Position 1 missing - closing all")
            for pos in opened_positions:
                close_position_immediately(pos.ticket, "No TP1")
            return FAILURE
    
    # 8. Создать запись группы в БД
    group = PositionGroup(
        group_id=group_id,
        created_at=timestamp_start,
        confirmed_at=NULL,  # будет установлено после подтверждения всех позиций
        tp1_hit=FALSE,
        entry_price=signal.entry,
        max_price=signal.entry,
        min_price=signal.entry,
        trade_type=BUY or SELL,
        positions=[p.ticket for p in opened_positions],
        trailing_enabled=FALSE,  # ⬅️ ВАЖНО: Трейлинг НЕ активен
        modification_allowed=FALSE  # ⬅️ ВАЖНО: Модификации запрещены
    )
    
    database.save(group)
    
    # 9. Запланировать подтверждение позиций через 10 секунд
    schedule_task(
        delay=10_seconds,
        task=confirm_positions,
        params=(group_id, [p.ticket for p in opened_positions])
    )
    
    return SUCCESS

def confirm_positions(group_id, tickets):
    """
    Подтверждение открытия позиций через 10 секунд
    """
    all_confirmed = TRUE
    
    for ticket in tickets:
        # Проверить на MT5
        mt5_position = broker.get_position(ticket)
        
        if mt5_position.exists:
            # Обновить локальную запись
            positions_tracker[ticket].confirmed_at = current_time()
            positions_tracker[ticket].phase = 'CONFIRMED'
            log_success(f"Position #{ticket} confirmed on MT5")
        else:
            log_error(f"Position #{ticket} NOT found on MT5!")
            all_confirmed = FALSE
    
    if all_confirmed:
        # Разрешить модификации через 60 секунд
        schedule_task(
            delay=50_seconds,  # 60 - 10 = 50 секунд дополнительно
            task=enable_modifications,
            params=(group_id,)
        )
    else:
        log_warning(f"Group {group_id}: Not all positions confirmed")

def enable_modifications(group_id):
    """
    Разрешить модификации SL для группы (через 60 секунд после открытия)
    """
    group = database.get_position_group(group_id)
    if not group:
        return
    
    group.modification_allowed = TRUE
    group.phase = 'ACTIVE'
    database.update(group)
    
    log_success(f"Group {group_id}: Modifications now allowed")
```

### Мониторинг и трейлинг

```python
def monitor_positions_loop():
    """
    Основной цикл мониторинга позиций
    """
    while bot_running:
        # 1. Получить все открытые группы
        open_groups = database.get_active_position_groups()
        
        for group in open_groups:
            # ПРОВЕРКА #1: Группа достаточно старая для модификаций?
            age_seconds = current_time() - group.created_at
            if age_seconds < 60:
                # Пропустить - слишком рано для любых модификаций
                continue
            
            # ПРОВЕРКА #2: Модификации разрешены?
            if not group.modification_allowed:
                continue
            
            # 2. Получить текущую цену
            current_price = get_current_price(group.symbol, group.trade_type)
            
            # 3. Обновить max/min price
            if group.trade_type == 'BUY':
                if current_price > group.max_price:
                    group.max_price = current_price
                    database.update(group)
            else:  # SELL
                if current_price < group.min_price:
                    group.min_price = current_price
                    database.update(group)
            
            # 4. Проверить статус TP1
            position_1 = find_position_by_num(group.positions, position_num=1)
            
            if position_1:
                # Позиция 1 ещё открыта - проверить, достигла ли TP1
                if check_tp_hit(position_1, current_price):
                    # TP1 достигнут - закрыть позицию 1
                    close_position(position_1.ticket, current_price, reason='TP1')
                    
                    # Активировать трейлинг для позиций 2 и 3
                    group.tp1_hit = TRUE
                    group.trailing_enabled = TRUE
                    database.update(group)
                    
                    log_success(f"Group {group.group_id}: TP1 hit, trailing activated")
            else:
                # Позиция 1 уже закрыта
                if not group.tp1_hit:
                    # Проверить историю - был ли это TP1 или SL
                    closed_trade = database.get_closed_trade(position_1.ticket)
                    
                    if closed_trade.status == 'TP1':
                        # TP1 подтверждён - активировать трейлинг
                        group.tp1_hit = TRUE
                        group.trailing_enabled = TRUE
                        database.update(group)
                        log_success(f"Group {group.group_id}: TP1 confirmed, trailing activated")
                    else:
                        # Позиция 1 закрылась по SL - НЕ активировать трейлинг
                        log_warning(f"Group {group.group_id}: Position 1 closed by SL, no trailing")
            
            # 5. Применить трейлинг только если TP1 подтверждён
            if group.tp1_hit and group.trailing_enabled:
                apply_trailing_stop(group, current_price)
        
        # Проверять каждые 5 секунд
        sleep(5)

def apply_trailing_stop(group, current_price):
    """
    Применить трейлинг-стоп к позициям 2 и 3
    """
    # Получить позиции 2 и 3
    positions = [p for p in group.positions if p.position_num in [2, 3]]
    
    for position in positions:
        # ПРОВЕРКА #1: Позиция достаточно старая?
        age_seconds = current_time() - position.opened_at
        if age_seconds < MIN_POSITION_AGE_FOR_TRAILING:
            log_debug(f"Position #{position.ticket} too young for trailing: {age_seconds}s")
            continue
        
        # ПРОВЕРКА #2: Не слишком частые модификации?
        if position.last_sl_modify_at:
            time_since_last = current_time() - position.last_sl_modify_at
            if time_since_last < 10:
                continue
        
        # Рассчитать новый SL
        if group.trade_type == 'BUY':
            # Trailing: 50% retracement от максимальной прибыли
            new_sl = group.max_price - (group.max_price - position.entry_price) * 0.5
            
            # Новый SL должен быть выше текущего
            if new_sl <= position.sl:
                continue  # Не ухудшать SL
            
        else:  # SELL
            new_sl = group.min_price + (position.entry_price - group.min_price) * 0.5
            
            # Новый SL должен быть ниже текущего
            if new_sl >= position.sl:
                continue
        
        # ПРОВЕРКА #3: Минимальное расстояние от текущей цены
        distance_from_price = abs(current_price - new_sl)
        min_distance = max(
            broker_stop_level * point,
            current_price * 0.002  # минимум 0.2%
        )
        
        if distance_from_price < min_distance:
            log_warning(f"Position #{position.ticket}: New SL too close to price: {distance_from_price} < {min_distance}")
            continue
        
        # ПРОВЕРКА #4: Минимальное расстояние от entry
        distance_from_entry = abs(new_sl - position.entry_price)
        min_distance_entry = position.entry_price * 0.003  # минимум 0.3%
        
        if distance_from_entry < min_distance_entry:
            log_warning(f"Position #{position.ticket}: New SL too close to entry: {distance_from_entry} < {min_distance_entry}")
            continue
        
        # Выполнить модификацию
        success = modify_sl_on_broker(
            ticket=position.ticket,
            new_sl=new_sl
        )
        
        if success:
            # Обновить локальную запись
            position.sl = new_sl
            position.last_sl_modify_at = current_time()
            database.update(position)
            
            log_success(f"Position #{position.ticket}: SL updated to {new_sl:.2f}")
        else:
            log_error(f"Position #{position.ticket}: Failed to update SL")
```

---

## ✅ Резюме рекомендаций

### Немедленные исправления (Critical)

1. **Добавить временные задержки:**
   - Минимум 60 секунд после открытия перед любой модификацией SL
   - Минимум 10 секунд между модификациями SL

2. **Добавить проверки возраста позиций:**
   - `opened_at` timestamp для каждой позиции
   - Проверка возраста перед вызовом `_update_3position_trailing()`

3. **Строгая валидация TP1:**
   - НЕ активировать трейлинг, пока позиция 1 не закрыта ПО TP1 (не по SL)
   - Проверять историю закрытия в БД

4. **Улучшить проверки SL distance:**
   - Минимум 0.3% от entry price
   - Минимум 0.2% от current price
   - Учитывать broker stop level

### Долгосрочные улучшения

5. **Рефакторинг архитектуры:**
   - Класс `PositionManager` для изолированного управления позициями
   - Фазы жизненного цикла позиций
   - Thread-safe операции

6. **Обработка partial opens:**
   - Автоматическое закрытие при открытии только 1/3
   - Продолжение при 2/3, если есть позиция 1

7. **Расширенное логирование:**
   - Timestamp для всех событий
   - Детальные логи каждого изменения SL
   - Состояние группы позиций

---

## 🛠️ План внедрения

### Фаза 1: Быстрые исправления (1-2 часа)
1. Добавить timestamp `opened_at` в `positions_tracker`
2. Добавить проверку возраста в `_update_3position_trailing()`
3. Добавить проверки SL distance в `_safe_modify_sl()`

### Фаза 2: Улучшение логики (2-3 часа)
4. Улучшить логику проверки TP1 hit
5. Добавить детальное логирование
6. Реализовать обработку partial opens

### Фаза 3: Рефакторинг (4-6 часов)
7. Создать класс `PositionManager`
8. Внедрить фазы жизненного цикла
9. Полное тестирование на демо-счёте

---

**Итог:** Проблема вызвана **race condition** и отсутствием защиты от преждевременной модификации SL. Решение - добавить временные задержки, строгие проверки и улучшить архитектуру управления позициями.
