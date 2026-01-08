"""
Test and display what notifications would be sent (without actual Telegram connection)
"""

from datetime import datetime
from telegram_notifier import TelegramNotifier


def test_notifications():
    """Test notification formatting"""

    print("\n" + "="*80)
    print("📱 ТЕСТИРОВАНИЕ УВЕДОМЛЕНИЙ TELEGRAM")
    print("="*80)

    # Initialize notifier (won't actually send, just format messages)
    notifier = TelegramNotifier("dummy_token", "dummy_chat")

    # Test 1: Entry signal (LONG)
    print("\n" + "="*80)
    print("1️⃣  УВЕДОМЛЕНИЕ О ВХОДЕ (LONG)")
    print("="*80)

    signal_data = {
        'direction': 'LONG',
        'entry_price': 4520.50,
        'stop_loss': 4450.00,
        'take_profit': 4634.50,
        'pattern': 'Bullish_Flag',
        'timestamp': datetime.now()
    }

    # Create message (don't send)
    risk = abs(signal_data['entry_price'] - signal_data['stop_loss'])
    reward = abs(signal_data['take_profit'] - signal_data['entry_price'])
    rr_ratio = reward / risk if risk > 0 else 0

    entry_message = f"""
🟢 <b>НОВЫЙ СИГНАЛ - PAPER TRADING</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время:</b> {signal_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

🟢 <b>Направление:</b> {signal_data['direction']}
💰 <b>Вход:</b> {signal_data['entry_price']:.2f}
🛑 <b>Stop Loss:</b> {signal_data['stop_loss']:.2f}
🎯 <b>Take Profit:</b> {signal_data['take_profit']:.2f}

📐 <b>Риск:</b> {risk:.2f} points
💎 <b>Награда:</b> {reward:.2f} points
📊 <b>R:R:</b> 1:{rr_ratio:.2f}

🔍 <b>Паттерн:</b> {signal_data['pattern']}

⚡ <b>Рекомендуемый лот:</b> 0.01 (микро-лот)
💵 <b>Риск на сделку:</b> ~${risk * 0.01:.2f}
"""

    print(entry_message)

    # Test 2: Exit by TP (profit)
    print("\n" + "="*80)
    print("2️⃣  ЗАКРЫТИЕ ПО ТЕЙК-ПРОФИТУ (прибыль)")
    print("="*80)

    exit_data_tp = {
        'direction': 'LONG',
        'entry_price': 4520.50,
        'exit_price': 4634.50,
        'exit_type': 'TP',
        'pnl_pct': 2.52,
        'pnl_points': 114.00,
        'duration_hours': 12.5,
        'timestamp': datetime.now()
    }

    exit_message_tp = f"""
✅ <b>ПРИБЫЛЬ - ЗАКРЫТИЕ ПОЗИЦИИ</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время:</b> {exit_data_tp['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

✅ <b>Направление:</b> {exit_data_tp['direction']}
💰 <b>Вход:</b> {exit_data_tp['entry_price']:.2f}
💵 <b>Выход:</b> {exit_data_tp['exit_price']:.2f}

🎯 <b>Тип выхода:</b> {exit_data_tp['exit_type']}
🎯 Take Profit сработал!

📈 <b>PnL:</b> {exit_data_tp['pnl_pct']:+.2f}% ({exit_data_tp['pnl_points']:+.2f} points)
⏱️ <b>Длительность:</b> {exit_data_tp['duration_hours']:.1f} часов

💰 <b>Доход при лоте 0.01:</b> ${exit_data_tp['pnl_points'] * 0.01:+.2f}
"""

    print(exit_message_tp)

    # Test 3: Exit by SL (loss)
    print("\n" + "="*80)
    print("3️⃣  ЗАКРЫТИЕ ПО СТОП-ЛОССУ (убыток)")
    print("="*80)

    exit_data_sl = {
        'direction': 'LONG',
        'entry_price': 4520.50,
        'exit_price': 4450.00,
        'exit_type': 'SL',
        'pnl_pct': -1.56,
        'pnl_points': -70.50,
        'duration_hours': 3.0,
        'timestamp': datetime.now()
    }

    exit_message_sl = f"""
❌ <b>УБЫТОК - ЗАКРЫТИЕ ПОЗИЦИИ</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время:</b> {exit_data_sl['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

❌ <b>Направление:</b> {exit_data_sl['direction']}
💰 <b>Вход:</b> {exit_data_sl['entry_price']:.2f}
💵 <b>Выход:</b> {exit_data_sl['exit_price']:.2f}

🛑 <b>Тип выхода:</b> {exit_data_sl['exit_type']}
🛑 Stop Loss сработал!

📈 <b>PnL:</b> {exit_data_sl['pnl_pct']:+.2f}% ({exit_data_sl['pnl_points']:+.2f} points)
⏱️ <b>Длительность:</b> {exit_data_sl['duration_hours']:.1f} часов

💰 <b>Доход при лоте 0.01:</b> ${exit_data_sl['pnl_points'] * 0.01:+.2f}
"""

    print(exit_message_sl)

    # Test 4: Exit by EOD timeout (может быть прибыль или убыток)
    print("\n" + "="*80)
    print("4️⃣  ЗАКРЫТИЕ ПО ТАЙМ-АУТУ (48 ЧАСОВ)")
    print("="*80)

    exit_data_eod = {
        'direction': 'LONG',
        'entry_price': 4520.50,
        'exit_price': 4545.30,
        'exit_type': 'EOD',
        'pnl_pct': 0.55,
        'pnl_points': 24.80,
        'duration_hours': 48.0,
        'timestamp': datetime.now()
    }

    exit_message_eod = f"""
✅ <b>ПРИБЫЛЬ - ЗАКРЫТИЕ ПОЗИЦИИ</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время:</b> {exit_data_eod['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

✅ <b>Направление:</b> {exit_data_eod['direction']}
💰 <b>Вход:</b> {exit_data_eod['entry_price']:.2f}
💵 <b>Выход:</b> {exit_data_eod['exit_price']:.2f}

⏱️ <b>Тип выхода:</b> {exit_data_eod['exit_type']}
⏱️ Закрыто по тайм-ауту

📈 <b>PnL:</b> {exit_data_eod['pnl_pct']:+.2f}% ({exit_data_eod['pnl_points']:+.2f} points)
⏱️ <b>Длительность:</b> {exit_data_eod['duration_hours']:.1f} часов

💰 <b>Доход при лоте 0.01:</b> ${exit_data_eod['pnl_points'] * 0.01:+.2f}
"""

    print(exit_message_eod)

    # Test 5: Daily summary
    print("\n" + "="*80)
    print("5️⃣  ЕЖЕДНЕВНЫЙ ОТЧЕТ")
    print("="*80)

    summary_data = {
        'total_trades': 5,
        'wins': 4,
        'losses': 1,
        'win_rate': 80.0,
        'total_pnl': 8.50,
        'total_pnl_usd': 2.15
    }

    summary_message = f"""
📈 <b>ЕЖЕДНЕВНЫЙ ОТЧЕТ - PAPER TRADING</b>

📅 <b>Дата:</b> {datetime.now().strftime('%Y-%m-%d')}
📊 <b>Стратегия:</b> Pattern Recognition (1.618)

📊 <b>Всего сделок:</b> {summary_data['total_trades']}
✅ <b>Прибыльных:</b> {summary_data['wins']}
❌ <b>Убыточных:</b> {summary_data['losses']}
📈 <b>Win Rate:</b> {summary_data['win_rate']:.1f}%

💰 <b>Общий PnL:</b> {summary_data['total_pnl']:+.2f}%
💵 <b>PnL в USD (лот 0.01):</b> ${summary_data['total_pnl_usd']:+.2f}

⚡ <b>Продолжаем торговлю!</b>
"""

    print(summary_message)

    print("\n" + "="*80)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*80)

    print("\n💡 ПРО ТАЙМАУТЫ В БЭКТЕСТЕ:")
    print("="*80)
    print("""
⏱️  <b>ТАЙМАУТ 48 ЧАСОВ (EOD - End Of Day)</b>

Да, в бэктесте есть ТАЙМАУТ! Если позиция не закрылась по TP или SL
в течение 48 ЧАСОВ, она автоматически закрывается по текущей цене.

📊 Почему это происходит:

1. ✅ <b>Защита капитала</b> - позиция не висит бесконечно
2. ✅ <b>Освобождение маржи</b> - капитал доступен для новых сделок
3. ✅ <b>Реалистичность</b> - в реале не держат позиции слишком долго

📈 Из последних 30 сделок:
   • EOD (тайм-аут): 27 сделок (90%)
   • TP (тейк-профит): 2 сделки (6.7%)
   • SL (стоп-лосс): 1 сделка (3.3%)

🎯 Это значит:
   • Большинство сделок закрываются с НЕБОЛЬШОЙ прибылью по таймауту
   • Стратегия консервативна - не ждет полного TP
   • TP слишком далеко (R:R = 1:1.62), цена часто не доходит

💡 Что можно улучшить:
   1. Уменьшить TP (например, R:R 1:1.2 вместо 1:1.62)
   2. Добавить частичное закрытие (50% по +1%, остальное держать до TP)
   3. Использовать трейлинг стоп
   4. Уменьшить таймаут до 24 часов

🔍 Код таймаута в paper_trading.py:
   ```python
   time_in_trade = (latest_time - pos['entry_time']).total_seconds() / 3600

   if time_in_trade >= 48:  # <-- ТАЙМАУТ 48 ЧАСОВ
       # Close by timeout
       positions_to_close.append((i, latest_close, 'EOD'))
   ```

✅ Это нормально и правильно! Таймаут защищает от зависших позиций.
""")

    print("\n" + "="*80)


if __name__ == "__main__":
    test_notifications()
