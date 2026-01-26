# 🐛 BUG: All Positions Closing as TP1 Instead of TP2/TP3

**Date:** 2026-01-22
**Issue:** When opening 3 positions (TP1, TP2, TP3), all are logged/closed as TP1
**Status:** 🔍 ROOT CAUSE IDENTIFIED → Ready for Fix

---

## 🚨 ПРОБЛЕМА

### Симптомы:
- Открываются 3 позиции для одного сигнала (с TP1, TP2, TP3)
- При достижении TP2 → закрывается как **TP1** ❌
- При достижении TP3 → закрывается как **TP1** ❌
- Происходит в **обоих режимах**: dry-run И live trading

### Пример:
```
Сигнал SELL:
- Position 1: Entry $3097.82, TP1 $3060.65
- Position 2: Entry $3097.82, TP2 $3042.06
- Position 3: Entry $3097.82, TP3 $3020.37

Текущая цена: $3042.00

Ожидаемый результат:
✅ Position 1 закрыта как TP1
✅ Position 2 закрыта как TP2  ← ПРОБЛЕМА!
❌ Position 3 еще открыта (TP не достигнут)

Фактический результат:
✅ Position 1 закрыта как TP1
❌ Position 2 закрыта как TP1 (WRONG!)
❌ Position 3 еще открыта
```

---

## 🔍 ROOT CAUSE ANALYSIS

### Цепочка событий:

#### 1. Position Opening (ПРАВИЛЬНО)
```python
# trading_bots/crypto_bot/live_bot_binance_fullauto.py:1711
# trading_bots/xauusd_bot/live_bot_mt5_fullauto.py:1947

for pos_data in positions_data:
    self._log_position_opened(
        order_id=order['id'],
        position_type='SELL',
        amount=pos_data['size'],
        entry_price=order['average'],
        sl=signal['sl'],
        tp=pos_data['tp'],  # ← Разные TP для каждой позиции!
        regime=regime,
        comment=f"V3_{regime_code}_P{pos_data['num']}/3",  # ← P1/3, P2/3, P3/3
        position_group_id=group_id,
        position_num=pos_data['num']  # ← 1, 2, или 3 ✅
    )
```

✅ **position_num передаётся правильно**: 1, 2, 3

#### 2. Position Logging (ПРОБЛЕМА!)
```python
# trading_bots/crypto_bot/live_bot_binance_fullauto.py:198-214
# trading_bots/xauusd_bot/live_bot_mt5_fullauto.py:257-273

def _log_position_opened(self, order_id, position_type, amount, entry_price,
                         sl, tp, regime, comment='', position_group_id=None, position_num=0):

    # In-memory tracker
    self.positions_tracker[order_id] = {
        'order_id': order_id,
        'open_time': open_time,
        'type': position_type,
        'amount': amount,
        'entry_price': entry_price,
        'sl': sl,
        'tp': tp,
        'close_price': None,
        'profit': None,
        'regime': regime,
        'status': 'OPEN',
        'comment': comment
        # ❌ ОТСУТСТВУЕТ: 'position_num'
        # ❌ ОТСУТСТВУЕТ: 'position_group_id'
    }

    # Database (ПРАВИЛЬНО)
    trade = TradeRecord(
        ...
        position_group_id=position_group_id,  # ✅ Сохраняется в БД
        position_num=position_num              # ✅ Сохраняется в БД
    )
    self.db.add_trade(trade)
```

❌ **BUG**: `position_num` и `position_group_id` сохраняются в БД, но **НЕ** добавляются в `positions_tracker`!

#### 3. TP Level Detection (ПРОВАЛ!)
```python
# trading_bots/crypto_bot/live_bot_binance_fullauto.py:1076-1090
# trading_bots/xauusd_bot/live_bot_mt5_fullauto.py:1060-1074

# Determine which TP level this is from position_num or comment
tp_level = 'TP1'  # Default for single-position mode
position_num = tracked_pos.get('position_num', 0)  # ← Возвращает 0 (default)!

if position_num == 1:
    tp_level = 'TP1'
elif position_num == 2:
    tp_level = 'TP2'
elif position_num == 3:
    tp_level = 'TP3'
elif 'TP1' in tracked_pos.get('comment', ''):  # ← Fallback
    tp_level = 'TP1'
elif 'TP2' in tracked_pos.get('comment', ''):
    tp_level = 'TP2'
elif 'TP3' in tracked_pos.get('comment', ''):
    tp_level = 'TP3'
```

**Проблема:**
1. `tracked_pos.get('position_num', 0)` возвращает **0** (default), так как ключ не существует
2. `position_num = 0` не соответствует 1, 2, или 3
3. Код переходит к fallback: проверка `comment`
4. Comment = `"V3_R_P2/3"` для Position 2
5. **НО**: Проверка `'TP1' in comment` идёт **ПЕРВОЙ**
6. Строка `'TP1'` **НЕ найдена** в `"V3_R_P2/3"`
7. Строка `'TP2'` **НЕ найдена** в `"V3_R_P2/3"` (нет подстроки "TP2")
8. Результат: `tp_level` остаётся **'TP1'** (default) ❌

### Почему fallback на comment тоже не работает?

Comment format: `"V3_R_P2/3"`
- V3 = Version 3 strategy
- R = Regime (T=TREND, R=RANGE)
- P2/3 = Position 2 of 3

Проверка:
```python
'TP1' in 'V3_R_P2/3'  # False
'TP2' in 'V3_R_P2/3'  # False (нет подстроки "TP2")
'TP3' in 'V3_R_P2/3'  # False (нет подстроки "TP3")
```

Правильно было бы:
```python
'P1/3' in 'V3_R_P1/3'  # True → TP1
'P2/3' in 'V3_R_P2/3'  # True → TP2
'P3/3' in 'V3_R_P3/3'  # True → TP3
```

---

## ✅ РЕШЕНИЕ

### Fix #1: Добавить position_num и position_group_id в positions_tracker

#### Crypto Bot (`live_bot_binance_fullauto.py:198-214`)

**БЫЛО:**
```python
self.positions_tracker[order_id] = {
    'order_id': order_id,
    'open_time': open_time,
    'close_time': None,
    'type': position_type,
    'amount': amount,
    'entry_price': entry_price,
    'sl': sl,
    'tp': tp,
    'close_price': None,
    'profit': None,
    'profit_pct': None,
    'regime': regime,
    'duration': None,
    'status': 'OPEN',
    'comment': comment
}
```

**СТАЛО:**
```python
self.positions_tracker[order_id] = {
    'order_id': order_id,
    'open_time': open_time,
    'close_time': None,
    'type': position_type,
    'amount': amount,
    'entry_price': entry_price,
    'sl': sl,
    'tp': tp,
    'close_price': None,
    'profit': None,
    'profit_pct': None,
    'regime': regime,
    'duration': None,
    'status': 'OPEN',
    'comment': comment,
    'position_group_id': position_group_id,  # ✅ ДОБАВЛЕНО
    'position_num': position_num              # ✅ ДОБАВЛЕНО
}
```

#### XAUUSD Bot (`live_bot_mt5_fullauto.py:257-273`)

**БЫЛО:**
```python
self.positions_tracker[ticket] = {
    'ticket': ticket,
    'open_time': open_time,
    'close_time': None,
    'type': position_type,
    'volume': volume,
    'entry_price': entry_price,
    'sl': sl,
    'tp': tp,
    'close_price': None,
    'profit': None,
    'pips': None,
    'regime': regime,
    'duration': None,
    'status': 'OPEN',
    'comment': comment
}
```

**СТАЛО:**
```python
self.positions_tracker[ticket] = {
    'ticket': ticket,
    'open_time': open_time,
    'close_time': None,
    'type': position_type,
    'volume': volume,
    'entry_price': entry_price,
    'sl': sl,
    'tp': tp,
    'close_price': None,
    'profit': None,
    'pips': None,
    'regime': regime,
    'duration': None,
    'status': 'OPEN',
    'comment': comment,
    'position_group_id': position_group_id,  # ✅ ДОБАВЛЕНО
    'position_num': position_num              # ✅ ДОБАВЛЕНО
}
```

### Fix #2: Улучшить fallback на comment (опционально)

Если по какой-то причине `position_num` будет 0, улучшить парсинг comment:

**БЫЛО:**
```python
elif 'TP1' in tracked_pos.get('comment', ''):
    tp_level = 'TP1'
elif 'TP2' in tracked_pos.get('comment', ''):
    tp_level = 'TP2'
elif 'TP3' in tracked_pos.get('comment', ''):
    tp_level = 'TP3'
```

**СТАЛО:**
```python
elif 'P1/3' in tracked_pos.get('comment', ''):
    tp_level = 'TP1'
elif 'P2/3' in tracked_pos.get('comment', ''):
    tp_level = 'TP2'
elif 'P3/3' in tracked_pos.get('comment', ''):
    tp_level = 'TP3'
elif 'TP1' in tracked_pos.get('comment', ''):  # Old format fallback
    tp_level = 'TP1'
elif 'TP2' in tracked_pos.get('comment', ''):
    tp_level = 'TP2'
elif 'TP3' in tracked_pos.get('comment', ''):
    tp_level = 'TP3'
```

---

## 🎯 ЧТО ТЕПЕРЬ БУДЕТ РАБОТАТЬ

### До фикса:
```
1. Position 2 opens → position_num=2 saved to DB
2. positions_tracker[order_id] = {...}  ← NO position_num!
3. TP check:
   position_num = tracked_pos.get('position_num', 0)  # Returns 0
4. Falls back to comment check
5. Comment = "V3_R_P2/3"
6. 'TP1' in "V3_R_P2/3" → False
   'TP2' in "V3_R_P2/3" → False
   'TP3' in "V3_R_P2/3" → False
7. tp_level = 'TP1' (default) ❌
```

### После фикса:
```
1. Position 2 opens → position_num=2 saved to DB
2. positions_tracker[order_id] = {..., 'position_num': 2}  ✅
3. TP check:
   position_num = tracked_pos.get('position_num', 0)  # Returns 2
4. if position_num == 2: tp_level = 'TP2'  ✅
5. Log: "🎯 TP2 HIT for position #xxx"  ✅
```

---

## 📋 ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ

| File | Line Numbers | Change |
|------|--------------|--------|
| `trading_bots/crypto_bot/live_bot_binance_fullauto.py` | 198-214 | Add position_num & position_group_id to tracker |
| `trading_bots/crypto_bot/live_bot_binance_fullauto.py` | 1076-1090 | Improve comment fallback (optional) |
| `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py` | 257-273 | Add position_num & position_group_id to tracker |
| `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py` | 1060-1074 | Improve comment fallback (optional) |

---

## ✅ VERIFICATION TESTS

### Test 1: Single Position Mode
```python
# Should still work (position_num=0 → default TP1)
Signal → Open 1 position → TP hit → Closes as TP1 ✅
```

### Test 2: 3-Position Mode - TP1
```python
Signal → Open 3 positions
Position 1 reaches TP1
Expected: "🎯 TP1 HIT for position #xxx"
Check: position_num=1 in tracker ✅
Result: Closes as TP1 ✅
```

### Test 3: 3-Position Mode - TP2
```python
Position 2 reaches TP2
Expected: "🎯 TP2 HIT for position #xxx"
Check: position_num=2 in tracker ✅
Result: Closes as TP2 ✅
```

### Test 4: 3-Position Mode - TP3
```python
Position 3 reaches TP3
Expected: "🎯 TP3 HIT for position #xxx"
Check: position_num=3 in tracker ✅
Result: Closes as TP3 ✅
```

### Test 5: Check Database
```python
db = DatabaseManager()
events = db.get_trade_events(bot_id='crypto_bot_ETHUSDT', event_type='TP_HIT')
for e in events:
    print(f"{e['timestamp']}: {e['event_type']} @ {e['price']}")

# Should see:
# 2026-01-22 10:15: TP1 @ $3060.65
# 2026-01-22 10:30: TP2 @ $3042.06  ← NOT TP1!
# 2026-01-22 10:45: TP3 @ $3020.37  ← NOT TP1!
```

---

## 📊 СТАТИСТИКА ИЗМЕНЕНИЙ

| File | Lines Added | Description |
|------|-------------|-------------|
| `live_bot_binance_fullauto.py` | +2 | Add position_num & position_group_id to tracker |
| `live_bot_binance_fullauto.py` | +6 (optional) | Improve comment parsing fallback |
| `live_bot_mt5_fullauto.py` | +2 | Add position_num & position_group_id to tracker |
| `live_bot_mt5_fullauto.py` | +6 (optional) | Improve comment parsing fallback |
| **TOTAL** | **+8 to +16** | Minimal changes, maximum impact |

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

### 1. Это критический баг
- Влияет на **все** 3-position mode трейды
- Искажает статистику (все TP2/TP3 записываются как TP1)
- Влияет на оба режима (dry-run И live)

### 2. Почему не заметили раньше?
- Позиции **закрываются правильно** (по правильной цене TP2/TP3)
- Проблема только в **логировании** (запись в БД и CSV)
- Profit расчёт правильный
- Только `event_type` в БД неправильный

### 3. Влияние на историю
- Существующие записи в БД останутся с неправильным TP level
- Можно пересчитать постфактум, если важно:
  ```python
  # Для каждой closed позиции:
  # - Загрузить position_num из БД
  # - Обновить event_type в trade_events
  ```

### 4. Backward compatibility
- Изменения обратно совместимы
- Single-position mode не затронут (position_num=0 → TP1)
- Старые позиции без position_num будут использовать comment fallback

---

## 🚀 НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ

1. **Применить Fix #1** (обязательно)
   - Добавить 2 строки в каждый бот
   - Протестировать dry-run

2. **Применить Fix #2** (опционально, но рекомендуется)
   - Улучшить comment parsing
   - Защита на случай сбоя

3. **Запустить Test Suite**
   - Открыть 3 позиции
   - Дождаться TP2 hit
   - Проверить логи: должно быть "TP2 HIT", не "TP1 HIT"

4. **Проверить Statistics Dialog**
   - TP Hits Viewer должен показывать TP1, TP2, TP3 отдельно
   - Statistics должна считать каждый TP level отдельно

---

**Готово к исправлению! 🔧**
