"""
Telegram notification module for trading alerts with connection pooling and async queue
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
from datetime import datetime, timedelta
import queue
import threading
import time


class TelegramNotifier:
    """Send trading alerts to Telegram channel/chat with connection pooling and async queue"""

    def __init__(self, bot_token, chat_id, timezone_offset=5, max_pool_connections=10):
        """
        Initialize Telegram notifier with connection pool

        Args:
            bot_token: Telegram bot token (get from @BotFather)
            chat_id: Chat ID or channel username (e.g., @your_channel or -100123456789)
            timezone_offset: Timezone offset in hours from UTC (default: 5 for UTC+5)
            max_pool_connections: Maximum connections in pool (default: 10)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timezone_offset = timezone_offset
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Create session with connection pooling
        self.session = self._create_session(max_pool_connections)
        
        # Message queue for async sending
        self.message_queue = queue.Queue()
        self.queue_thread = None
        self.running = False
        
        # Rate limiting
        self.last_send_time = 0
        self.min_interval = 0.5  # Min 0.5 seconds between messages
        
        # Start queue processor
        self._start_queue_processor()
    
    def _create_session(self, max_connections):
        """Create requests session with connection pooling and retry"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # 3 retry attempts
            backoff_factor=1,  # 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP codes
            method_whitelist=["POST", "GET"]
        )
        
        # Configure adapter with connection pool
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=max_connections,  # Connection pool size
            pool_maxsize=max_connections * 2,  # Max connections per host
            pool_block=False  # Don't block if pool is full, raise error instead
        )
        
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _start_queue_processor(self):
        """Start background thread to process message queue"""
        if self.queue_thread and self.queue_thread.is_alive():
            return  # Already running
        
        self.running = True
        self.queue_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.queue_thread.start()
    
    def _process_queue(self):
        """Process messages from queue in background thread"""
        while self.running:
            try:
                # Get message from queue with timeout
                try:
                    message_data = self.message_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Rate limiting
                time_since_last = time.time() - self.last_send_time
                if time_since_last < self.min_interval:
                    time.sleep(self.min_interval - time_since_last)
                
                # Send message
                self._send_message_direct(message_data['text'], message_data['parse_mode'])
                self.last_send_time = time.time()
                
                # Mark task as done
                self.message_queue.task_done()
                
            except Exception as e:
                print(f"⚠️  Error in Telegram queue processor: {e}")
    
    def _send_message_direct(self, text, parse_mode='HTML'):
        """Send message directly (called by queue processor)"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }

            response = self.session.post(url, data=data, timeout=10)

            if response.status_code == 200:
                return True
            else:
                print(f"❌ Telegram error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.ConnectionError as e:
            print(f"❌ Telegram connection error: {e}")
            return False
        except requests.exceptions.Timeout as e:
            print(f"❌ Telegram timeout: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def wait_for_queue(self, timeout=5):
        """Wait for all queued messages to be sent (useful for shutdown)"""
        try:
            self.message_queue.join()  # Wait for queue to empty
        except Exception as e:
            print(f"⚠️  Error waiting for queue: {e}")
    
    def shutdown(self):
        """Shutdown queue processor"""
        self.running = False
        if self.queue_thread:
            self.queue_thread.join(timeout=2.0)

    def _convert_to_local_time(self, timestamp):
        """
        Convert timestamp to local timezone
        
        Args:
            timestamp: datetime or pandas Timestamp
            
        Returns:
            datetime in local timezone
        """
        # Convert pandas Timestamp to datetime
        if hasattr(timestamp, 'to_pydatetime'):
            timestamp = timestamp.to_pydatetime()
        
        # Handle timezone-aware datetime - convert to naive UTC
        if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
            # Convert to UTC and make naive
            timestamp = timestamp.replace(tzinfo=None)
        
        # Apply timezone offset
        return timestamp + timedelta(hours=self.timezone_offset)

    def send_message(self, text, parse_mode='HTML', async_send=True):
        """
        Send text message to Telegram
        
        Args:
            text: Message text
            parse_mode: HTML or Markdown
            async_send: If True, queue message for async sending. If False, send immediately.
        
        Returns:
            True if queued/sent successfully
        """
        try:
            if async_send:
                # Add to queue for async sending
                self.message_queue.put({
                    'text': text,
                    'parse_mode': parse_mode
                })
                return True
            else:
                # Send immediately (blocking)
                return self._send_message_direct(text, parse_mode)
                
        except Exception as e:
            print(f"❌ Failed to queue Telegram message: {e}")
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

        # Convert to local timezone
        timestamp_local = self._convert_to_local_time(timestamp)

        # Calculate R:R (using TP3 as max reward)
        risk = abs(entry_price - stop_loss)
        reward_tp3 = abs(tp3 - entry_price)
        rr_ratio = reward_tp3 / risk if risk > 0 else 0

        emoji = "🟢" if direction == "LONG" else "🔴"
        regime_emoji = "📈" if regime == "TREND" else "📊"

        message = f"""
{emoji} <b>НОВЫЙ СИГНАЛ - PAPER TRADING</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')} (UTC+{self.timezone_offset})

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
        
        # TP hit information
        tp1_hit = exit_data.get('tp1_hit', False)
        tp2_hit = exit_data.get('tp2_hit', False)
        tp3_hit = exit_data.get('tp3_hit', False)

        # Convert to local timezone
        timestamp_local = self._convert_to_local_time(timestamp)

        # Determine emoji based on profit/loss
        if pnl_pct > 0:
            result_emoji = "✅"
            result_text = "ПРИБЫЛЬ"
        else:
            result_emoji = "❌"
            result_text = "УБЫТОК"

        # Exit type emoji and text
        exit_emoji_map = {
            'TP': '🎯',
            'SL': '🛑',
            'TRAILING_SL': '🔄',
            'TIMEOUT': '⏱️',
            'ALL_TPS_HIT': '🎯🎯🎯',
            'FULLY_CLOSED': '✅'
        }
        exit_emoji = exit_emoji_map.get(exit_type, '🔔')
        
        exit_text_map = {
            'TP': 'Take Profit сработал!',
            'SL': 'Stop Loss сработал!',
            'TRAILING_SL': 'Trailing Stop сработал!',
            'TIMEOUT': 'Закрыто по тайм-ауту',
            'ALL_TPS_HIT': 'Все Take Profits достигнуты!',
            'FULLY_CLOSED': 'Позиция полностью закрыта'
        }
        exit_text = exit_text_map.get(exit_type, exit_type)
        
        # Build TP status
        tp_status = ""
        if tp1_hit or tp2_hit or tp3_hit:
            tp_hits = []
            if tp1_hit:
                tp_hits.append("TP1 ✅")
            if tp2_hit:
                tp_hits.append("TP2 ✅")
            if tp3_hit:
                tp_hits.append("TP3 ✅")
            tp_status = f"\n🎯 <b>TPs:</b> {' | '.join(tp_hits)}"

        message = f"""
{result_emoji} <b>{result_text} - ЗАКРЫТИЕ ПОЗИЦИИ</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')} (UTC+{self.timezone_offset})

{result_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
💵 <b>Выход:</b> {exit_price:.2f}

{exit_emoji} <b>Тип выхода:</b> {exit_type}
{exit_text}{tp_status}

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

    def send_partial_close(self, partial_data):
        """Send partial close notification (TP1, TP2, or TP3 hit)"""

        direction = partial_data['direction']
        tp_level = partial_data['tp_level']  # 'TP1', 'TP2', or 'TP3'
        tp_price = partial_data['tp_price']
        entry_price = partial_data['entry_price']
        close_pct = partial_data['close_pct']  # 0.5, 0.3, 0.2
        pnl_pct = partial_data['pnl_pct']
        pnl_points = partial_data['pnl_points']
        position_remaining = partial_data['position_remaining']
        regime = partial_data.get('regime', 'N/A')
        trailing_activated = partial_data.get('trailing_activated', False)
        trailing_distance = partial_data.get('trailing_distance', 0)
        timestamp = partial_data.get('timestamp', datetime.now())

        # Convert to local timezone
        if hasattr(timestamp, 'tz_localize'):
            timestamp = timestamp.to_pydatetime()
        timestamp_local = timestamp + timedelta(hours=self.timezone_offset)

        emoji = "🎯" if tp_level == 'TP1' else ("🎯🎯" if tp_level == 'TP2' else "🎯🎯🎯")
        regime_emoji = "📈" if regime == "TREND" else "📊"

        # Calculate profit in USD (for 0.01 lot)
        profit_usd = pnl_points * 0.01

        message = f"""
{emoji} <b>ЧАСТИЧНОЕ ЗАКРЫТИЕ - {tp_level} HIT!</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')} (UTC+{self.timezone_offset})

{regime_emoji} <b>Режим:</b> {regime}
{"🟢" if direction == "LONG" else "🔴"} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
{emoji} <b>{tp_level}:</b> {tp_price:.2f}

📊 <b>Закрыто:</b> {close_pct*100:.0f}% позиции
💵 <b>Прибыль:</b> {pnl_pct:+.2f}% ({pnl_points:+.2f}п)
💰 <b>Прибыль USD (лот 0.01):</b> ${profit_usd:+.2f}

📈 <b>Осталось открыто:</b> {position_remaining*100:.0f}% позиции
"""

        if trailing_activated:
            message += f"""
🔄 <b>TRAILING STOP АКТИВИРОВАН!</b>
   Расстояние: {trailing_distance}п
   SL будет двигаться за ценой
"""

        message += """
⚡ <b>Продолжаем держать оставшуюся позицию!</b>
"""

        return self.send_message(message)

        return self.send_message(message)

    def send_tp_hit(self, tp_data):
        """Send TP hit notification"""
        tp_level = tp_data['tp_level']  # 1, 2, or 3
        order_id = tp_data['order_id']
        direction = tp_data['direction']
        entry_price = tp_data['entry_price']
        close_price = tp_data['close_price']
        profit = tp_data['profit']
        profit_pct = tp_data['profit_pct']
        position_num = tp_data.get('position_num', tp_level)
        timestamp = tp_data.get('timestamp', datetime.now())
        
        timestamp_local = self._convert_to_local_time(timestamp)
        
        emoji = "🎯"
        direction_emoji = "🟢" if direction == "LONG" else "🔴"
        
        message = f"""
{emoji} <b>TAKE PROFIT {tp_level} ДОСТИГНУТ!</b>

📊 <b>Позиция #{position_num}</b>
⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')}

{direction_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
🎯 <b>Выход TP{tp_level}:</b> {close_price:.2f}

✅ <b>Прибыль:</b> ${profit:.2f} ({profit_pct:+.2f}%)

🔔 <b>Ордер:</b> {order_id}
"""
        
        return self.send_message(message)

    def send_sl_hit(self, sl_data):
        """Send SL hit notification"""
        order_id = sl_data['order_id']
        direction = sl_data['direction']
        entry_price = sl_data['entry_price']
        sl_price = sl_data['sl_price']
        close_price = sl_data['close_price']
        loss = sl_data['loss']
        loss_pct = sl_data['loss_pct']
        timestamp = sl_data.get('timestamp', datetime.now())
        
        timestamp_local = self._convert_to_local_time(timestamp)
        
        emoji = "🛑"
        direction_emoji = "🟢" if direction == "LONG" else "🔴"
        
        message = f"""
{emoji} <b>STOP LOSS СРАБОТАЛ</b>

⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')}

{direction_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
🛑 <b>Stop Loss:</b> {sl_price:.2f}
❌ <b>Выход:</b> {close_price:.2f}

📉 <b>Убыток:</b> -${abs(loss):.2f} ({loss_pct:.2f}%)

🔔 <b>Ордер:</b> {order_id}

💡 Защита капитала сработала корректно
"""
        
        return self.send_message(message)

    def send_trailing_activated(self, trailing_data):
        """Send trailing stop activation notification"""
        order_id = trailing_data['order_id']
        direction = trailing_data['direction']
        entry_price = trailing_data['entry_price']
        tp1_price = trailing_data['tp1_price']
        initial_sl = trailing_data['initial_sl']
        new_sl = trailing_data['new_sl']
        timestamp = trailing_data.get('timestamp', datetime.now())
        
        timestamp_local = self._convert_to_local_time(timestamp)
        
        emoji = "🔄"
        direction_emoji = "🟢" if direction == "LONG" else "🔴"
        
        message = f"""
{emoji} <b>TRAILING STOP АКТИВИРОВАН!</b>

⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')}

{direction_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
🎯 <b>TP1 достигнут:</b> {tp1_price:.2f}

🛡️ <b>Stop Loss обновлён:</b>
   Было: {initial_sl:.2f}
   Стало: {new_sl:.2f} (безубыток)

📊 Позиции TP2 и TP3 теперь под защитой trailing stop
🔒 Гарантированная прибыль зафиксирована

🔔 <b>Ордер:</b> {order_id}
"""
        
        return self.send_message(message)

    def send_trailing_hit(self, trailing_data):
        """Send trailing stop hit notification"""
        order_id = trailing_data['order_id']
        direction = trailing_data['direction']
        entry_price = trailing_data['entry_price']
        max_price = trailing_data['max_price']
        close_price = trailing_data['close_price']
        profit = trailing_data['profit']
        profit_pct = trailing_data['profit_pct']
        protected_profit_pct = trailing_data.get('protected_profit_pct', 0)  # How much profit was protected
        timestamp = trailing_data.get('timestamp', datetime.now())
        
        timestamp_local = self._convert_to_local_time(timestamp)
        
        emoji = "🔒"
        direction_emoji = "🟢" if direction == "LONG" else "🔴"
        
        message = f"""
{emoji} <b>TRAILING STOP ЗАКРЫЛ ПОЗИЦИЮ</b>

⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')}

{direction_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
🚀 <b>Макс. цена:</b> {max_price:.2f}
🔒 <b>Выход (trailing):</b> {close_price:.2f}

✅ <b>Зафиксированная прибыль:</b> ${profit:.2f} ({profit_pct:+.2f}%)
🛡️ <b>Защищено от отката:</b> {protected_profit_pct:.1f}%

🔔 <b>Ордер:</b> {order_id}

💡 Trailing stop защитил вашу прибыль от разворота
"""
        
        return self.send_message(message)

    def send_startup_message(self):
        """Send bot startup notification"""

        # Get current time in local timezone
        now_local = datetime.now() + timedelta(hours=self.timezone_offset)

        message = f"""
🤖 <b>PAPER TRADING БОТ ЗАПУЩЕН</b>

📊 <b>Стратегия:</b> Pattern Recognition (1.618)
⏰ <b>Время запуска:</b> {now_local.strftime('%Y-%m-%d %H:%M:%S')} (UTC+{self.timezone_offset})

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
            response = self.session.get(url, timeout=10)

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
