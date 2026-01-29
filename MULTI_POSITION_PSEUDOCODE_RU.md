# Псевдокод: Правильная логика multi-position стратегии

## 1. Открытие группы из 3 позиций

```python
def open_3_position_group(signal):
    """
    Открывает группу из 3 позиций с защитой от race condition
    
    Args:
        signal: Торговый сигнал с параметрами entry, sl, tp1, tp2, tp3, direction, regime
        
    Returns:
        True если все позиции успешно открыты, False иначе
    """
    # Шаг 1: Генерировать уникальный ID группы
    group_id = generate_uuid()
    timestamp_start = current_unix_time()  # Важно: Unix timestamp для точных расчетов
    
    print(f"\n{'='*60}")
    print(f"📈 OPENING 3-POSITION GROUP")
    print(f"   Group ID: {group_id[:8]}")
    print(f"   Timestamp: {timestamp_start}")
    print(f"{'='*60}")
    
    # Шаг 2: Предварительная валидация
    
    # 2.1 Проверить доступность слотов для позиций
    available_slots = MAX_POSITIONS - count_open_positions()
    if available_slots < 3:
        log_error(f"Insufficient slots: need 3, have {available_slots}")
        return False
    
    # 2.2 Рассчитать размеры позиций
    total_lot_size = calculate_position_size(signal.entry, signal.sl, RISK_PERCENT)
    lot1 = round(total_lot_size * 0.33, 2)
    lot2 = round(total_lot_size * 0.33, 2)
    lot3 = round(total_lot_size * 0.34, 2)
    
    # 2.3 Валидировать минимальные размеры
    broker_min_lot = get_broker_min_lot(SYMBOL)
    if lot1 < broker_min_lot OR lot2 < broker_min_lot OR lot3 < broker_min_lot:
        log_error(f"Position sizes below broker minimum:")
        log_error(f"  Lot1={lot1}, Lot2={lot2}, Lot3={lot3}, Min={broker_min_lot}")
        log_error(f"  Required total lot: {broker_min_lot * 3}")
        return False
    
    # 2.4 Валидировать SL distance
    sl_distance = abs(signal.entry - signal.sl)
    broker_stop_level = get_broker_stop_level(SYMBOL)
    min_sl_distance_broker = broker_stop_level * POINT
    min_sl_distance_custom = signal.entry * 0.005  # минимум 0.5%
    min_sl_distance = max(min_sl_distance_broker, min_sl_distance_custom)
    
    if sl_distance < min_sl_distance:
        log_error(f"SL too close to entry:")
        log_error(f"  SL distance: {sl_distance:.2f}")
        log_error(f"  Min required: {min_sl_distance:.2f}")
        log_error(f"  Entry: {signal.entry:.2f}, SL: {signal.sl:.2f}")
        return False
    
    print(f"✅ Pre-validation passed")
    print(f"   Lot sizes: {lot1} / {lot2} / {lot3}")
    print(f"   SL distance: {sl_distance:.2f} (min: {min_sl_distance:.2f})")
    
    # Шаг 3: Открыть позиции последовательно
    opened_positions = []
    order_type = ORDER_TYPE_BUY if signal.direction == 1 else ORDER_TYPE_SELL
    
    # Получить текущую цену для исполнения ордера
    tick = get_current_tick(SYMBOL)
    if not tick:
        log_error("Failed to get current price")
        return False
    
    execution_price = tick.ask if signal.direction == 1 else tick.bid
    
    # Параметры для каждой позиции
    positions_config = [
        {'num': 1, 'lot': lot1, 'tp': signal.tp1, 'name': 'TP1'},
        {'num': 2, 'lot': lot2, 'tp': signal.tp2, 'name': 'TP2'},
        {'num': 3, 'lot': lot3, 'tp': signal.tp3, 'name': 'TP3'}
    ]
    
    for config in positions_config:
        print(f"\n📤 Sending {config['name']} order...")
        
        # Создать ордер
        order_request = {
            'symbol': SYMBOL,
            'volume': config['lot'],
            'type': order_type,
            'price': execution_price,
            'sl': signal.sl,  # ⬅️ ВАЖНО: Одинаковый исходный SL для всех позиций
            'tp': config['tp'],
            'deviation': 20,
            'magic': MAGIC_NUMBER,
            'comment': f"V3_{signal.regime[0]}_P{config['num']}/3",
            'type_time': ORDER_TIME_GTC,
            'type_filling': get_filling_mode()
        }
        
        # Отправить ордер
        timestamp_before = current_unix_time()
        result = broker.send_order(order_request)
        timestamp_after = current_unix_time()
        execution_time = timestamp_after - timestamp_before
        
        print(f"   Order execution time: {execution_time:.3f}s")
        
        if result.success AND result.retcode == TRADE_RETCODE_DONE:
            # Ордер успешно выполнен
            position_data = {
                'ticket': result.ticket,
                'position_num': config['num'],
                'lot': config['lot'],
                'tp': config['tp'],
                'tp_name': config['name'],
                'entry_price': result.price,
                'sl': signal.sl,
                'type': 'BUY' if signal.direction == 1 else 'SELL',
                # КРИТИЧНО: Временные метки
                'opened_at': timestamp_after,  # Unix timestamp
                'confirmed_at': None,          # Будет установлено после проверки
                'last_sl_modify_at': None,     # Для отслеживания модификаций
                'phase': 'OPENING'             # OPENING -> CONFIRMED -> ACTIVE -> TRAILING_ACTIVE
            }
            
            opened_positions.append(position_data)
            
            # Сохранить в локальный трекер
            positions_tracker[result.ticket] = position_data
            
            # Сохранить в базу данных
            save_position_to_database(position_data, group_id, signal)
            
            print(f"   ✅ {config['name']} opened: #{result.ticket} at {result.price:.2f}")
        else:
            # Ордер не выполнен
            error_code = result.retcode if result else 'NO_RESULT'
            error_msg = result.comment if result else 'No response from broker'
            
            log_error(f"❌ {config['name']} failed!")
            log_error(f"   Error code: {error_code}")
            log_error(f"   Message: {error_msg}")
            log_error(f"   Volume: {config['lot']}, Price: {execution_price:.2f}")
        
        # Задержка между ордерами
        sleep(0.3)
    
    # Шаг 4: Обработать результат открытия
    total_opened = len(opened_positions)
    
    print(f"\n📊 Opening result: {total_opened}/3 positions")
    
    # 4.1 Ни одна позиция не открылась
    if total_opened == 0:
        log_error("FAILED: No positions opened - ABORT")
        return False
    
    # 4.2 Частичное открытие (1 или 2 позиции)
    if total_opened < 3:
        log_warning(f"PARTIAL OPEN: {total_opened}/3 positions")
        
        # Проверить, какие позиции открыты
        opened_nums = [p['position_num'] for p in opened_positions]
        log_warning(f"Opened positions: {opened_nums}")
        
        # Критично: Позиция 1 (TP1) ОБЯЗАТЕЛЬНА для 3-position стратегии
        if 1 not in opened_nums:
            log_error("Position 1 (TP1) missing - strategy unusable")
            log_error("Closing all opened positions...")
            
            for pos in opened_positions:
                close_position_immediately(
                    ticket=pos['ticket'],
                    reason="No TP1 - safety close"
                )
            
            return False
        
        # Если есть позиция 1, но всего открылась только 1 позиция
        if total_opened == 1:
            log_warning("Only 1 position - closing for safety")
            close_position_immediately(
                ticket=opened_positions[0]['ticket'],
                reason="Partial open 1/3 - unsafe"
            )
            return False
        
        # Если открылись 2 позиции и среди них есть позиция 1
        if total_opened == 2:
            log_warning("2/3 positions opened - can proceed with reduced strategy")
            # Продолжаем, но НЕ будем активировать трейлинг для отсутствующей позиции
    
    # Шаг 5: Создать группу позиций в памяти
    position_groups[group_id] = {
        'group_id': group_id,
        'created_at': timestamp_start,      # КРИТИЧНО: для проверки возраста группы
        'confirmed_at': None,               # Будет установлено после подтверждения
        'tp1_hit': False,                   # Флаг достижения TP1
        'entry_price': signal.entry,
        'max_price': signal.entry,          # Для BUY: отслеживание максимума
        'min_price': signal.entry,          # Для SELL: отслеживание минимума
        'trade_type': 'BUY' if signal.direction == 1 else 'SELL',
        'positions': [p['ticket'] for p in opened_positions],
        'positions_count': total_opened,
        'partial_open': (total_opened < 3),
        'trailing_enabled': False,          # КРИТИЧНО: трейлинг НЕ активен
        'modification_allowed': False,      # КРИТИЧНО: модификации SL запрещены
        'phase': 'OPENING'
    }
    
    # Шаг 6: Сохранить группу в базу данных
    save_position_group_to_database(position_groups[group_id])
    
    # Шаг 7: Запланировать задачи на будущее
    
    # 7.1 Подтверждение позиций через 10 секунд
    schedule_task(
        delay=10,  # seconds
        task=confirm_positions_task,
        params={
            'group_id': group_id,
            'tickets': [p['ticket'] for p in opened_positions]
        }
    )
    
    # 7.2 Разрешение модификаций SL через 60 секунд
    schedule_task(
        delay=60,  # seconds
        task=enable_modifications_task,
        params={'group_id': group_id}
    )
    
    print(f"\n✅ Group {group_id[:8]} created successfully!")
    print(f"   Positions: {total_opened}/3")
    print(f"   Scheduled tasks:")
    print(f"      - Confirm positions in 10s")
    print(f"      - Enable modifications in 60s")
    
    # Шаг 8: Отправить уведомление в Telegram
    send_telegram_notification(
        title="3-Position Group Opened",
        group_id=group_id,
        positions=opened_positions,
        signal=signal
    )
    
    return True


def confirm_positions_task(group_id, tickets):
    """
    Подтверждение позиций на брокере через 10 секунд после открытия
    
    Эта задача запускается автоматически через 10 секунд после открытия группы
    """
    print(f"\n🔍 Confirming positions for group {group_id[:8]}...")
    
    all_confirmed = True
    confirmed_count = 0
    
    for ticket in tickets:
        # Проверить, существует ли позиция на MT5
        broker_position = broker.get_position(ticket)
        
        if broker_position AND broker_position.exists:
            # Позиция найдена на MT5
            if ticket in positions_tracker:
                positions_tracker[ticket]['confirmed_at'] = current_unix_time()
                positions_tracker[ticket]['phase'] = 'CONFIRMED'
                confirmed_count += 1
                print(f"   ✅ Position #{ticket} confirmed")
            else:
                log_warning(f"Position #{ticket} found on broker but not in tracker")
        else:
            # Позиция НЕ найдена на MT5
            log_error(f"   ❌ Position #{ticket} NOT found on broker!")
            all_confirmed = False
    
    if all_confirmed:
        print(f"   ✅ All {confirmed_count} positions confirmed on broker")
        
        # Обновить статус группы
        if group_id in position_groups:
            position_groups[group_id]['confirmed_at'] = current_unix_time()
            position_groups[group_id]['phase'] = 'CONFIRMED'
            update_position_group_in_database(position_groups[group_id])
    else:
        log_warning(f"   ⚠️  Not all positions confirmed ({confirmed_count}/{len(tickets)})")


def enable_modifications_task(group_id):
    """
    Разрешить модификации SL для группы через 60 секунд после открытия
    
    Эта задача запускается автоматически через 60 секунд после открытия группы
    """
    if group_id not in position_groups:
        log_warning(f"Group {group_id[:8]} not found - may have been closed")
        return
    
    group = position_groups[group_id]
    
    print(f"\n✅ Enabling modifications for group {group_id[:8]}")
    
    # Разрешить модификации
    group['modification_allowed'] = True
    group['phase'] = 'ACTIVE'
    
    # Обновить в базе данных
    update_position_group_in_database(group)
    
    # Обновить фазу для всех позиций группы
    for ticket in group['positions']:
        if ticket in positions_tracker:
            positions_tracker[ticket]['phase'] = 'ACTIVE'
    
    print(f"   Group age: {current_unix_time() - group['created_at']:.1f}s")
    print(f"   Modifications now allowed")


def close_position_immediately(ticket, reason):
    """
    Немедленно закрыть позицию (для обработки ошибок при частичном открытии)
    """
    print(f"\n🔄 Emergency close: #{ticket}")
    print(f"   Reason: {reason}")
    
    # Получить данные позиции
    broker_position = broker.get_position(ticket)
    if not broker_position:
        log_warning(f"Position #{ticket} not found on broker")
        return False
    
    # Получить текущую цену для закрытия
    tick = get_current_tick(SYMBOL)
    if not tick:
        log_error("Cannot get current price for closing")
        return False
    
    # Определить тип ордера для закрытия (противоположный)
    close_order_type = ORDER_TYPE_SELL if broker_position.type == ORDER_TYPE_BUY else ORDER_TYPE_BUY
    close_price = tick.bid if broker_position.type == ORDER_TYPE_BUY else tick.ask
    
    # Создать запрос на закрытие
    close_request = {
        'action': TRADE_ACTION_DEAL,
        'symbol': SYMBOL,
        'volume': broker_position.volume,
        'type': close_order_type,
        'position': ticket,
        'price': close_price,
        'deviation': 20,
        'magic': MAGIC_NUMBER,
        'comment': reason,
        'type_time': ORDER_TIME_GTC,
        'type_filling': get_filling_mode()
    }
    
    # Отправить запрос
    result = broker.send_order(close_request)
    
    if result.success AND result.retcode == TRADE_RETCODE_DONE:
        print(f"   ✅ Position #{ticket} closed")
        
        # Логировать закрытие
        log_position_closed(ticket, close_price, profit=0, status='EMERGENCY_CLOSE')
        
        return True
    else:
        error = result.comment if result else "No result"
        log_error(f"   ❌ Failed to close: {error}")
        return False
```

## 2. Мониторинг позиций и обновление трейлинга

```python
def monitor_positions_loop():
    """
    Основной цикл мониторинга всех открытых позиций
    
    Выполняется каждые 5 секунд для проверки:
    - Достижения TP/SL
    - Обновления трейлинг-стопов
    - Синхронизации с брокером
    """
    iteration = 0
    
    while bot_running:
        iteration += 1
        print(f"\n{'='*80}")
        print(f"🔄 Monitor iteration #{iteration} - {current_datetime()}")
        print(f"{'='*80}")
        
        # Шаг 1: Получить все активные группы позиций
        active_groups = get_active_position_groups()
        
        print(f"📊 Active groups: {len(active_groups)}")
        
        if len(active_groups) == 0:
            print("   No active position groups")
            sleep(5)
            continue
        
        # Шаг 2: Обработать каждую группу
        for group in active_groups:
            group_id = group['group_id']
            
            # 2.1 ПРОВЕРКА #1: Возраст группы
            group_age = current_unix_time() - group['created_at']
            
            # Пропустить слишком молодые группы
            if group_age < MIN_POSITION_AGE_FOR_TRAILING:
                # Логировать только первые 2 минуты
                if group_age < 120:
                    print(f"\n⏳ Group {group_id[:8]} too young: {group_age:.1f}s < {MIN_POSITION_AGE_FOR_TRAILING}s")
                continue
            
            # 2.2 ПРОВЕРКА #2: Модификации разрешены?
            if not group['modification_allowed']:
                if group_age < 120:
                    print(f"\n🔒 Group {group_id[:8]} modifications not allowed yet (age: {group_age:.1f}s)")
                continue
            
            print(f"\n🔍 Processing group {group_id[:8]} (age: {group_age:.1f}s)")
            
            # 2.3 Получить текущую цену
            tick = get_current_tick(SYMBOL)
            if not tick:
                log_warning("Cannot get current price - skipping this iteration")
                continue
            
            current_price = tick.bid if group['trade_type'] == 'BUY' else tick.ask
            print(f"   Current price: {current_price:.2f}")
            
            # 2.4 Обновить max/min цену группы
            price_changed = False
            if group['trade_type'] == 'BUY':
                if current_price > group['max_price']:
                    old_max = group['max_price']
                    group['max_price'] = current_price
                    price_changed = True
                    print(f"   📈 New max price: {old_max:.2f} → {current_price:.2f}")
            else:  # SELL
                if current_price < group['min_price']:
                    old_min = group['min_price']
                    group['min_price'] = current_price
                    price_changed = True
                    print(f"   📉 New min price: {old_min:.2f} → {current_price:.2f}")
            
            # Сохранить в БД при изменении цены
            if price_changed:
                update_position_group_in_database(group)
            
            # 2.5 Проверить статус позиции 1 (TP1)
            position_1 = find_position_by_num(group['positions'], 1)
            
            if position_1 AND is_position_open(position_1):
                # Позиция 1 ещё открыта - проверить TP1
                tp1_price = position_1['tp']
                
                if check_tp_reached(position_1, current_price, tp1_price):
                    print(f"   🎯 TP1 REACHED at {current_price:.2f}!")
                    
                    # Закрыть позицию 1
                    close_position(
                        ticket=position_1['ticket'],
                        close_price=current_price,
                        reason='TP1'
                    )
                    
                    # АКТИВИРОВАТЬ ТРЕЙЛИНГ для позиций 2 и 3
                    if not group['tp1_hit']:
                        group['tp1_hit'] = True
                        group['trailing_enabled'] = True
                        update_position_group_in_database(group)
                        
                        print(f"   ✅ TP1 confirmed - trailing activated for positions 2 & 3")
                else:
                    # TP1 ещё не достигнут
                    print(f"   ⏳ Position 1 active, TP1 not reached (target: {tp1_price:.2f})")
            else:
                # Позиция 1 уже закрыта
                if not group['tp1_hit']:
                    # Проверить историю - закрылась по TP1 или по SL?
                    closed_pos_1 = get_closed_position_from_history(position_1['ticket'])
                    
                    if closed_pos_1 AND closed_pos_1['status'] == 'TP1':
                        # Подтверждено: закрылась по TP1
                        group['tp1_hit'] = True
                        group['trailing_enabled'] = True
                        update_position_group_in_database(group)
                        
                        print(f"   ✅ Position 1 closed by TP1 (confirmed from history)")
                        print(f"   ✅ Trailing activated for positions 2 & 3")
                    else:
                        # Закрылась по SL или вручную - НЕ активировать трейлинг
                        status = closed_pos_1['status'] if closed_pos_1 else 'UNKNOWN'
                        print(f"   ⚠️  Position 1 closed by {status} - NO trailing activation")
            
            # 2.6 Применить трейлинг-стоп (только если TP1 подтверждён)
            if group['tp1_hit'] AND group['trailing_enabled']:
                apply_trailing_stop_to_group(group, current_price)
        
        # Пауза между итерациями
        sleep(5)


def apply_trailing_stop_to_group(group, current_price):
    """
    Применить трейлинг-стоп к позициям 2 и 3 в группе
    """
    group_id = group['group_id']
    print(f"\n   📊 Applying trailing stop to group {group_id[:8]}")
    
    # Получить позиции 2 и 3
    positions_to_trail = []
    for ticket in group['positions']:
        if ticket in positions_tracker:
            pos = positions_tracker[ticket]
            if pos['position_num'] in [2, 3] AND pos.get('phase') == 'ACTIVE':
                positions_to_trail.append(pos)
    
    if len(positions_to_trail) == 0:
        print(f"      No positions 2/3 to trail (may be already closed)")
        return
    
    print(f"      Positions to trail: {len(positions_to_trail)}")
    
    # Обработать каждую позицию
    for pos in positions_to_trail:
        ticket = pos['ticket']
        pos_num = pos['position_num']
        entry_price = pos['entry_price']
        current_sl = pos['sl']
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА #1: Возраст позиции
        pos_age = current_unix_time() - pos['opened_at']
        if pos_age < MIN_POSITION_AGE_FOR_TRAILING:
            print(f"      ⏳ Position #{ticket} (P{pos_num}) too young: {pos_age:.1f}s")
            continue
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА #2: Недавние модификации
        last_modify = pos.get('last_sl_modify_at', 0)
        if last_modify > 0:
            time_since_last = current_unix_time() - last_modify
            if time_since_last < MIN_SL_MODIFY_INTERVAL:
                print(f"      ⏳ Position #{ticket} (P{pos_num}) modified recently: {time_since_last:.1f}s ago")
                continue
        
        # Рассчитать новый SL
        if pos['type'] == 'BUY':
            # Trailing для BUY: 50% retracement от максимальной прибыли
            max_price = group['max_price']
            profit_range = max_price - entry_price
            new_sl = max_price - (profit_range * TRAILING_STOP_PCT)
            
            # Новый SL должен быть выше текущего (улучшение)
            if new_sl <= current_sl:
                # Не ухудшаем SL
                continue
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА #3: Минимальное расстояние от entry
            distance_from_entry = new_sl - entry_price
            min_distance_from_entry = entry_price * 0.003  # 0.3%
            if distance_from_entry < min_distance_from_entry:
                print(f"      ⚠️  P{pos_num} new SL too close to entry: {distance_from_entry:.2f} < {min_distance_from_entry:.2f}")
                continue
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА #4: Минимальное расстояние от current price
            distance_from_price = current_price - new_sl
            broker_stop_level = get_broker_stop_level(SYMBOL)
            min_distance_broker = broker_stop_level * POINT
            min_distance_custom = current_price * 0.002  # 0.2%
            min_distance = max(min_distance_broker, min_distance_custom)
            
            if distance_from_price < min_distance:
                print(f"      ⚠️  P{pos_num} new SL too close to price: {distance_from_price:.2f} < {min_distance:.2f}")
                continue
            
        else:  # SELL
            # Trailing для SELL: 50% retracement от максимальной прибыли
            min_price = group['min_price']
            profit_range = entry_price - min_price
            new_sl = min_price + (profit_range * TRAILING_STOP_PCT)
            
            # Новый SL должен быть ниже текущего (улучшение)
            if new_sl >= current_sl:
                # Не ухудшаем SL
                continue
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА #3: Минимальное расстояние от entry
            distance_from_entry = entry_price - new_sl
            min_distance_from_entry = entry_price * 0.003  # 0.3%
            if distance_from_entry < min_distance_from_entry:
                print(f"      ⚠️  P{pos_num} new SL too close to entry: {distance_from_entry:.2f} < {min_distance_from_entry:.2f}")
                continue
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА #4: Минимальное расстояние от current price
            distance_from_price = new_sl - current_price
            broker_stop_level = get_broker_stop_level(SYMBOL)
            min_distance_broker = broker_stop_level * POINT
            min_distance_custom = current_price * 0.002  # 0.2%
            min_distance = max(min_distance_broker, min_distance_custom)
            
            if distance_from_price < min_distance:
                print(f"      ⚠️  P{pos_num} new SL too close to price: {distance_from_price:.2f} < {min_distance:.2f}")
                continue
        
        # Все проверки пройдены - модифицировать SL
        print(f"      📊 P{pos_num} trailing: {current_sl:.2f} → {new_sl:.2f}")
        print(f"         Entry: {entry_price:.2f}, Distance from entry: {abs(new_sl - entry_price):.2f}")
        print(f"         Current: {current_price:.2f}, Distance from price: {abs(current_price - new_sl):.2f}")
        
        # Выполнить модификацию на брокере
        success = modify_sl_on_broker(
            ticket=ticket,
            new_sl=new_sl,
            current_tp=pos['tp']
        )
        
        if success:
            # Обновить в памяти
            pos['sl'] = new_sl
            pos['last_sl_modify_at'] = current_unix_time()
            pos['phase'] = 'TRAILING_ACTIVE'
            
            # Обновить в БД
            update_position_in_database(pos)
            
            print(f"         ✅ SL modified successfully on broker")
            
            # Уведомление Telegram
            send_telegram_notification(
                title="Trailing Stop Updated",
                position=pos,
                old_sl=current_sl,
                new_sl=new_sl,
                group=group
            )
        else:
            log_error(f"         ❌ Failed to modify SL on broker")


def modify_sl_on_broker(ticket, new_sl, current_tp):
    """
    Безопасная модификация SL на брокере с валидацией
    """
    # Получить позицию с брокера для проверки
    broker_position = broker.get_position(ticket)
    if not broker_position:
        log_error(f"Position #{ticket} not found on broker")
        return False
    
    # Создать запрос на модификацию
    modify_request = {
        'action': TRADE_ACTION_SLTP,
        'position': ticket,
        'symbol': SYMBOL,
        'sl': new_sl,
        'tp': current_tp,  # TP не меняется
        'magic': MAGIC_NUMBER
    }
    
    # Отправить запрос
    result = broker.send_order(modify_request)
    
    if result.success AND result.retcode == TRADE_RETCODE_DONE:
        return True
    else:
        error = result.comment if result else "No result"
        retcode = result.retcode if result else "N/A"
        log_error(f"Modify SL failed: retcode={retcode}, error={error}")
        return False


# Вспомогательные функции

def check_tp_reached(position, current_price, tp_price):
    """Проверить, достигнут ли TP"""
    if position['type'] == 'BUY':
        return current_price >= tp_price
    else:  # SELL
        return current_price <= tp_price


def is_position_open(position):
    """Проверить, открыта ли позиция"""
    if position['ticket'] not in positions_tracker:
        return False
    
    pos = positions_tracker[position['ticket']]
    return pos.get('status') == 'OPEN' AND pos.get('phase') in ['CONFIRMED', 'ACTIVE', 'TRAILING_ACTIVE']


def find_position_by_num(tickets_list, position_num):
    """Найти позицию по номеру (1, 2, или 3)"""
    for ticket in tickets_list:
        if ticket in positions_tracker:
            pos = positions_tracker[ticket]
            if pos.get('position_num') == position_num:
                return pos
    return None
```

## 3. Константы и настройки

```python
# Временные ограничения (в секундах)
MIN_POSITION_AGE_FOR_TRAILING = 60    # Минимум 60 секунд после открытия для активации трейлинга
MIN_POSITION_AGE_FOR_SL_MODIFY = 30   # Минимум 30 секунд для любой модификации SL
MIN_SL_MODIFY_INTERVAL = 10           # Минимум 10 секунд между модификациями SL
BROKER_CONFIRMATION_TIMEOUT = 10       # Ожидание подтверждения от брокера

# Минимальные расстояния для SL
MIN_SL_DISTANCE_FROM_ENTRY_PCT = 0.003  # 0.3% от цены входа
MIN_SL_DISTANCE_FROM_PRICE_PCT = 0.002  # 0.2% от текущей цены

# Трейлинг-стоп
TRAILING_STOP_PCT = 0.5  # 50% retracement

# Фазы жизненного цикла позиции
PHASE_OPENING = 'OPENING'              # Ордер отправлен, ждём подтверждения
PHASE_CONFIRMED = 'CONFIRMED'          # Подтверждено брокером, модификации пока запрещены
PHASE_ACTIVE = 'ACTIVE'                # Активна, разрешены модификации
PHASE_TRAILING_ACTIVE = 'TRAILING_ACTIVE'  # Трейлинг активен
PHASE_CLOSING = 'CLOSING'              # TP/SL достигнут, закрывается
PHASE_CLOSED = 'CLOSED'                # Закрыта
```

## Итоговая схема безопасности

```
Время после открытия:    Разрешённые действия:
-----------------------------------------------------------
0-10 секунд             • Только мониторинг
                        • Проверка наличия на брокере

10-30 секунд            • Подтверждение позиции
                        • Синхронизация с БД
                        • Мониторинг TP/SL

30-60 секунд            • Проверка TP1
                        • Закрытие по TP/SL разрешено
                        • Модификация SL ЗАПРЕЩЕНА

60+ секунд              • Все операции разрешены
                        • Трейлинг может активироваться
                        • Модификация SL разрешена
                        • (но только если TP1 подтверждён!)
```

Эта архитектура гарантирует, что:
1. ✅ Позиции НЕ модифицируются сразу после открытия
2. ✅ Трейлинг активируется только после РЕАЛЬНОГО достижения TP1
3. ✅ SL всегда на безопасном расстоянии от текущей цены
4. ✅ Нет гонки данных между открытием и модификацией
5. ✅ Полная прослеживаемость всех действий
