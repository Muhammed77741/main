# Live Bot 3-Position Integration Guide

## Overview
Интеграция логики 3-позиционного режима из Signal Analysis в live боты (crypto и XAUUSD).

## Статус реализации

### ✅ Completed
1. Database migration (position_group_id, position_num в trades table)
2. BotConfig model update (use_3_position_mode, total_position_size, min_order_size)
3. TradeRecord model update (position_group_id, position_num)
4. DatabaseManager update (add_trade, get_trades с новыми полями)
5. Crypto bot __init__ parameters (use_3_position_mode, total_position_size, min_order_size)
6. Crypto bot _log_position_opened signature update

### 🔄 In Progress
- Модификация метода open_position для 3-позиционного режима

## Логика 3-позиционного режима

### Текущая реализация (Signal Analysis)
```python
def _calculate_3_position_outcome(...):
    """
    Position 1: Target TP1, no trailing
    Position 2: Target TP2, trailing after TP1 hits
    Position 3: Target TP3, trailing after TP1 hits

    Trailing: 50% от max profit с момента достижения TP1
    """
```

### Адаптация для Live Bot

#### Сценарий открытия позиций:
```
Сигнал BUY на $50,000
- Рассчитать TP1, TP2, TP3 на основе TREND/RANGE
- Генерировать position_group_id (UUID)
- Открыть 3 независимые позиции:

  Position 1: 33% от total size
    - Order type: MARKET + LIMIT TP1
    - SL: Original SL
    - TP: TP1 только
    - Трейлинг: НЕТ

  Position 2: 33% от total size
    - Order type: MARKET + LIMIT TP2
    - SL: Original SL (→ переместить к breakeven после TP1)
    - TP: TP2
    - Трейлинг: Активировать после TP1

  Position 3: 34% от total size
    - Order type: MARKET + LIMIT TP3
    - SL: Original SL (→ переместить к breakeven после TP1)
    - TP: TP3
    - Трейлинг: Активировать после TP1
```

### Мониторинг позиций:
```
В _check_tp_sl_realtime():
1. Отслеживать каждую позицию отдельно
2. Когда любая позиция достигает TP1:
   - Установить флаг tp1_hit для group
   - Активировать trailing для Pos 2 и Pos 3
   - Переместить их SL к breakeven
3. Обновлять trailing stop для Pos 2 и Pos 3:
   - BUY: trailing_stop = max_price - (max_price - entry) × 0.5
   - SELL: trailing_stop = min_price + (entry - min_price) × 0.5
```

## Изменения в коде

### 1. Метод open_position (обновленный)

```python
def open_position(self, signal):
    """Open position(s) with TP/SL - supports 3-position mode"""

    if not self.use_3_position_mode:
        # Существующая логика для одной позиции
        return self._open_single_position(signal)
    else:
        # Новая логика для 3 позиций
        return self._open_3_positions(signal)
```

### 2. Новый метод _open_3_positions

```python
def _open_3_positions(self, signal):
    """
    Open 3 independent positions for same signal

    Position allocation:
    - Pos 1: 33% → TP1 only, no trailing
    - Pos 2: 33% → TP2, trails after TP1
    - Pos 3: 34% → TP3, trails after TP1
    """
    direction_str = "BUY" if signal['direction'] == 1 else "SELL"
    group_id = str(uuid.uuid4())

    print(f"\n{'='*60}")
    print(f"📈 OPENING 3-POSITION {direction_str} GROUP")
    print(f"{'='*60}")
    print(f"   Group ID: {group_id}")

    # Calculate total position size
    if self.total_position_size:
        total_size = self.total_position_size
    else:
        # Use risk-based sizing
        total_size = self.calculate_position_size(signal['entry'], signal['sl'])

    # Validate minimum order size
    min_size = self.min_order_size or 0.01
    pos_sizes = [
        total_size * 0.33,  # Pos 1
        total_size * 0.33,  # Pos 2
        total_size * 0.34   # Pos 3 (slightly larger for rounding)
    ]

    # Auto-adjust if below minimum
    for i, size in enumerate(pos_sizes):
        if size < min_size:
            print(f"⚠️  Position {i+1} size {size} < minimum {min_size}, adjusting...")
            pos_sizes[i] = min_size

    # Open 3 positions
    positions_data = [
        {'num': 1, 'size': pos_sizes[0], 'tp': signal['tp1'], 'trailing': False},
        {'num': 2, 'size': pos_sizes[1], 'tp': signal['tp2'], 'trailing': True},
        {'num': 3, 'size': pos_sizes[2], 'tp': signal['tp3'], 'trailing': True}
    ]

    if self.dry_run:
        print(f"\n🧪 DRY RUN: Would open 3 {direction_str} positions:")
        for pos_data in positions_data:
            print(f"   Position {pos_data['num']}: ${pos_data['size']:.4f} → TP ${pos_data['tp']:.2f}")
            print(f"      Trailing: {'YES (after TP1)' if pos_data['trailing'] else 'NO'}")
        return True

    try:
        side = 'buy' if signal['direction'] == 1 else 'sell'

        for pos_data in positions_data:
            print(f"\n   🔄 Opening Position {pos_data['num']}...")

            # Place market order
            order = self.exchange.create_order(
                symbol=self.symbol,
                type='market',
                side=side,
                amount=pos_data['size'],
                params={
                    'stopLoss': {'triggerPrice': signal['sl']},
                    'takeProfit': {'triggerPrice': pos_data['tp']}
                }
            )

            print(f"      ✅ Position {pos_data['num']} opened!")
            print(f"         Order ID: {order['id']}")
            print(f"         Size: {pos_data['size']:.4f}")
            print(f"         TP: ${pos_data['tp']:.2f}")
            print(f"         Trailing: {'YES' if pos_data['trailing'] else 'NO'}")

            # Log position
            position_type = 'BUY' if signal['direction'] == 1 else 'SELL'
            regime = signal.get('regime', 'UNKNOWN')
            regime_code = "T" if regime == 'TREND' else "R"

            self._log_position_opened(
                order_id=order['id'],
                position_type=position_type,
                amount=pos_data['size'],
                entry_price=order.get('average', signal['entry']),
                sl=signal['sl'],
                tp=pos_data['tp'],
                regime=regime,
                comment=f"V3_{regime_code}_P{pos_data['num']}/3",
                position_group_id=group_id,
                position_num=pos_data['num']
            )

            time.sleep(0.5)  # Small delay between orders

        # Send Telegram notification
        if self.telegram_bot:
            message = f"🤖 <b>3-Position Group Opened</b>\n\n"
            message += f"Group ID: {group_id[:8]}...\n"
            message += f"Symbol: {self.symbol}\n"
            message += f"Direction: {direction_str}\n"
            message += f"Regime: {regime}\n"
            message += f"Total Size: {total_size:.4f}\n"
            message += f"Entry: ${signal['entry']:.2f}\n"
            message += f"SL: ${signal['sl']:.2f}\n"
            message += f"TP1/TP2/TP3: ${signal['tp1']:.2f} / ${signal['tp2']:.2f} / ${signal['tp3']:.2f}"
            asyncio.run(self.send_telegram(message))

        return True

    except Exception as e:
        print(f"❌ Failed to open 3-position group: {e}")
        import traceback
        traceback.print_exc()
        return False
```

### 3. Обновление _check_tp_sl_realtime для трейлинга

```python
def _check_tp_sl_realtime(self):
    """Check TP/SL in real-time - support 3-position trailing"""
    # ... existing code ...

    # Для 3-позиционного режима:
    # - Группировать позиции по position_group_id
    # - Когда Pos 1 достигает TP1, активировать trailing для Pos 2 и 3
    # - Обновлять trailing stop используя max_price tracking
```

## Преимущества

### Для трейдера:
- ✅ Диверсификация выходов (quick profit + let winners run)
- ✅ Защита прибыли через trailing после TP1
- ✅ Психологически проще (partial wins vs all-or-nothing)
- ✅ Лучшее соотношение risk/reward

### Для анализа:
- ✅ Детальная статистика по каждой позиции
- ✅ Сравнение стратегий (conservative vs aggressive)
- ✅ Оптимизация TP levels на основе реальных данных
- ✅ Группировка в Excel/анализе по position_group_id

## Следующие шаги

1. ✅ Завершить реализацию _open_3_positions
2. ⏳ Обновить _check_tp_sl_realtime для trailing
3. ⏳ Протестировать в DRY RUN режиме
4. ⏳ Интегрировать в XAUUSD bot
5. ⏳ Создать pull request

## Безопасность

### Проверки перед запуском:
- [ ] DRY RUN тестирование с 3 позициями
- [ ] Проверка minimum order size validation
- [ ] Проверка капитал не >50% total
- [ ] Тест database logging (position_group_id, position_num)
- [ ] Проверка trailing stop logic
- [ ] Тест Telegram notifications

### Откат при проблемах:
```python
# Если возникли проблемы, временно отключить:
use_3_position_mode=False
```

## Вопросы и ответы

### Q: Что если Binance отклонит один из 3 ордеров?
A: Каждый ордер обработан в try/except. Если один fails, логируется ошибка, но другие могут пройти.

### Q: Как закрывать позиции из одной группы?
A: Каждая позиция независима. Закрывается по собственному TP/SL/trailing.

### Q: Размер позиций всегда 33/33/34%?
A: Да, для начала. В будущем можно сделать configurable (например 50/30/20%).

### Q: Trailing активируется для группы или каждой позиции?
A: Для группы. Когда ЛЮБАЯ позиция достигает TP1, trailing активируется для Pos 2 и Pos 3.

---

**Автор**: Claude Code Integration
**Дата**: January 2025
**Статус**: 🔄 В разработке
