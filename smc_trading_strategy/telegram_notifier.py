"""
Telegram notification module for paper trading alerts
"""

import requests
import json
from datetime import datetime


class TelegramNotifier:
    """Send trading alerts to Telegram channel/chat"""

    def __init__(self, bot_token, chat_id):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token (get from @BotFather)
            chat_id: Chat ID or channel username (e.g., @your_channel or -100123456789)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text, parse_mode='HTML'):
        """Send text message to Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }

            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                return True
            else:
                print(f"❌ Telegram error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False

    def send_entry_signal(self, signal_data):
        """Send entry signal notification"""

        direction = signal_data['direction']
        entry_price = signal_data['entry_price']
        stop_loss = signal_data['stop_loss']
        tp1 = signal_data.get('tp1', signal_data.get('take_profit'))
        tp2 = signal_data.get('tp2', tp1)
        tp3 = signal_data.get('tp3', tp1)
        pattern = signal_data.get('pattern', 'N/A')
        regime = signal_data.get('regime', 'N/A')
        trailing = signal_data.get('trailing', 0)
        timestamp = signal_data.get('timestamp', datetime.now())

        # Calculate R:R (using TP3 as max reward)
        risk = abs(entry_price - stop_loss)
        reward_tp3 = abs(tp3 - entry_price)
        rr_ratio = reward_tp3 / risk if risk > 0 else 0

        emoji = "🟢" if direction == "LONG" else "🔴"
        regime_emoji = "📈" if regime == "TREND" else "📊"

        message = f"""
{emoji} <b>НОВЫЙ СИГНАЛ - PAPER TRADING</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время:</b> {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

{emoji} <b>Направление:</b> {direction}
{regime_emoji} <b>Режим:</b> {regime}
💰 <b>Вход:</b> {entry_price:.2f}
🛑 <b>Stop Loss:</b> {stop_loss:.2f}

🎯 <b>Take Profits:</b>
   TP1: {tp1:.2f} (50% позиции)
   TP2: {tp2:.2f} (30% позиции)
   TP3: {tp3:.2f} (20% позиции)

🔄 <b>Trailing Stop:</b> {trailing}п (после TP1)

📐 <b>Риск:</b> {risk:.2f} points
💎 <b>Награда:</b> {reward_tp3:.2f} points (TP3)
📊 <b>R:R:</b> 1:{rr_ratio:.2f}

🔍 <b>Паттерн:</b> {pattern}

⚡ <b>Рекомендуемый лот:</b> 0.01 (микро-лот)
💵 <b>Риск на сделку:</b> ~${risk * 0.01:.2f}
"""

        return self.send_message(message)

    def send_exit_signal(self, exit_data):
        """Send exit signal notification"""

        direction = exit_data['direction']
        entry_price = exit_data['entry_price']
        exit_price = exit_data['exit_price']
        exit_type = exit_data['exit_type']
        pnl_pct = exit_data['pnl_pct']
        pnl_points = exit_data['pnl_points']
        duration = exit_data.get('duration_hours', 0)
        timestamp = exit_data.get('timestamp', datetime.now())

        # Determine emoji based on profit/loss
        if pnl_pct > 0:
            result_emoji = "✅"
            result_text = "ПРИБЫЛЬ"
        else:
            result_emoji = "❌"
            result_text = "УБЫТОК"

        # Exit type emoji
        exit_emoji = {
            'TP': '🎯',
            'SL': '🛑',
            'EOD': '⏱️'
        }.get(exit_type, '🔔')

        message = f"""
{result_emoji} <b>{result_text} - ЗАКРЫТИЕ ПОЗИЦИИ</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время:</b> {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

{result_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
💵 <b>Выход:</b> {exit_price:.2f}

{exit_emoji} <b>Тип выхода:</b> {exit_type}
{'🎯 Take Profit сработал!' if exit_type == 'TP' else '🛑 Stop Loss сработал!' if exit_type == 'SL' else '⏱️ Закрыто по тайм-ауту'}

📈 <b>PnL:</b> {pnl_pct:+.2f}% ({pnl_points:+.2f} points)
⏱️ <b>Длительность:</b> {duration:.1f} часов

💰 <b>Доход при лоте 0.01:</b> ${pnl_points * 0.01:+.2f}
"""

        return self.send_message(message)

    def send_daily_summary(self, summary_data):
        """Send daily summary report"""

        total_trades = summary_data.get('total_trades', 0)
        wins = summary_data.get('wins', 0)
        losses = summary_data.get('losses', 0)
        win_rate = summary_data.get('win_rate', 0)
        total_pnl = summary_data.get('total_pnl', 0)
        total_pnl_usd = summary_data.get('total_pnl_usd', 0)

        emoji = "📈" if total_pnl > 0 else "📉"

        message = f"""
{emoji} <b>ЕЖЕДНЕВНЫЙ ОТЧЕТ - PAPER TRADING</b>

📅 <b>Дата:</b> {datetime.now().strftime('%Y-%m-%d')}
📊 <b>Стратегия:</b> Pattern Recognition (1.618)

📊 <b>Всего сделок:</b> {total_trades}
✅ <b>Прибыльных:</b> {wins}
❌ <b>Убыточных:</b> {losses}
📈 <b>Win Rate:</b> {win_rate:.1f}%

💰 <b>Общий PnL:</b> {total_pnl:+.2f}%
💵 <b>PnL в USD (лот 0.01):</b> ${total_pnl_usd:+.2f}

⚡ <b>Продолжаем торговлю!</b>
"""

        return self.send_message(message)

    def send_startup_message(self):
        """Send bot startup notification"""

        message = f"""
🤖 <b>PAPER TRADING БОТ ЗАПУЩЕН</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время запуска:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ <b>Режим:</b> Paper Trading (симуляция)
📈 <b>Актив:</b> XAUUSD (Gold)
⏱️ <b>Таймфрейм:</b> 1H

🔔 <b>Вы будете получать уведомления о:</b>
  • Новых сигналах на вход
  • Закрытии позиций
  • Ежедневных отчетах

💡 <b>Рекомендации:</b>
  • Лот: 0.01 (микро-лот)
  • Риск: 1-2% на сделку
  • Капитал: $500+

⚡ <b>Бот активен и отслеживает рынок!</b>
"""

        return self.send_message(message)

    def send_error(self, error_message):
        """Send error notification"""

        message = f"""
⚠️ <b>ОШИБКА В PAPER TRADING БОТЕ</b>

❌ <b>Описание:</b>
{error_message}

⏰ <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔧 <b>Требуется проверка!</b>
"""

        return self.send_message(message)

    def test_connection(self):
        """Test Telegram bot connection"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data['ok']:
                    bot_info = data['result']
                    print(f"✅ Telegram bot connected: @{bot_info['username']}")
                    return True
            else:
                print(f"❌ Telegram bot connection failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Telegram bot test failed: {e}")
            return False
