"""
Live MT5 Trading Bot - SEMI-AUTOMATIC (V9 Strategy)

РЕЖИМ ПОЛУАВТОМАТА:
1. Бот анализирует рынок каждый час
2. Находит сигналы по стратегии V9
3. СПРАШИВАЕТ подтверждение через Telegram
4. Открывает позицию ТОЛЬКО после вашего "ДА"
5. АВТОМАТИЧЕСКИ управляет открытыми позициями (TP, SL, Trailing)

БЕЗОПАСНОСТЬ:
- Никаких сделок без вашего подтверждения
- Контроль каждого входа
- Автоматический выход (удобно)
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading

from simplified_smc_strategy import SimplifiedSMCStrategy
from telegram_notifier import TelegramNotifier
from mt5_data_downloader import MT5DataDownloader
from telegram_command_handler import TelegramCommandHandler
from telegram.ext import Application


class LiveBotMT5SemiAuto:
    """
    Live MT5 Trading Bot - Semi-Automatic Mode

    V9 PARAMETERS (CHAMPION):
    - LONG TREND: TP 35/65/100п, Trailing 25п, Timeout 60ч
    - LONG RANGE: TP 25/45/65п, Trailing 20п, Timeout 48ч
    - SHORT TREND: TP 18/30/42п, Trailing 13п, Timeout 24ч
    - Partial close: 30%/30%/40%
    """

    def __init__(self, telegram_token=None, telegram_chat_id=None,
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1,
                 check_interval=3600, timezone_offset=5):
        """
        Initialize Semi-Auto Live Bot

        Args:
            telegram_token: Telegram bot token (REQUIRED for semi-auto)
            telegram_chat_id: Telegram chat ID (REQUIRED for semi-auto)
            symbol: MT5 symbol (default: 'XAUUSD')
            timeframe: MT5 timeframe (default: mt5.TIMEFRAME_H1)
            check_interval: How often to check for signals (seconds)
            timezone_offset: Timezone offset from UTC
        """
        if not telegram_token or not telegram_chat_id:
            raise ValueError("❌ Telegram credentials required for semi-auto mode!")

        self.strategy = SimplifiedSMCStrategy()
        self.symbol = symbol
        self.timeframe = timeframe
        self.check_interval = check_interval

        # V9 LONG TREND parameters
        self.long_trend_tp1 = 35
        self.long_trend_tp2 = 65
        self.long_trend_tp3 = 100
        self.long_trend_trailing = 25
        self.long_trend_timeout = 60

        # V9 LONG RANGE parameters
        self.long_range_tp1 = 25
        self.long_range_tp2 = 45
        self.long_range_tp3 = 65
        self.long_range_trailing = 20
        self.long_range_timeout = 48

        # V9 SHORT TREND parameters
        self.short_trend_tp1 = 18
        self.short_trend_tp2 = 30
        self.short_trend_tp3 = 42
        self.short_trend_trailing = 13
        self.short_trend_timeout = 24

        # V9 partial close
        self.close_pct1 = 0.3
        self.close_pct2 = 0.3
        self.close_pct3 = 0.4

        # SHORT RANGE disabled
        self.short_range_enabled = False

        # MT5 data downloader
        self.mt5_downloader = MT5DataDownloader(symbol=symbol, timeframe=timeframe)

        # Telegram notifier
        self.notifier = TelegramNotifier(telegram_token, telegram_chat_id, timezone_offset=timezone_offset)

        # Telegram bot application (for command handling)
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_app = None

        # Command handler
        self.command_handler = TelegramCommandHandler(self)

        # Pending signals waiting for confirmation
        self.pending_signals = {}
        self.pending_signal_lock = threading.Lock()

        # Tracking
        self.open_positions = []
        self.open_positions_lock = threading.Lock()
        self.last_check = None

        # Position monitoring
        self.position_monitor_running = False
        self.position_monitor_thread = None

        print("✅ Live Trading Bot - SEMI-AUTO initialized")
        print(f"   Symbol: {symbol}")
        print(f"   Mode: SEMI-AUTOMATIC (confirmation required)")
        print(f"   Partial Close: {self.close_pct1*100:.0f}%/{self.close_pct2*100:.0f}%/{self.close_pct3*100:.0f}%")

    def detect_market_regime(self, df, lookback=100):
        """Detect market regime: TREND or RANGE"""
        if len(df) < lookback:
            return 'RANGE'

        recent_data = df.iloc[-lookback:]

        # 5-signal system
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()
        ema_diff_pct = abs((ema_fast.iloc[-1] - ema_slow.iloc[-1]) / ema_slow.iloc[-1]) * 100
        ema_trend = ema_diff_pct > 0.3

        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()
        high_volatility = atr > avg_atr * 1.05

        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()
        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35

        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        sequential_trend = abs(up_moves - down_moves) > lookback * 0.15

        highs = recent_data['high'].values[-20:]
        lows = recent_data['low'].values[-20:]
        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
        structural_trend = (higher_highs > 12) or (lower_lows > 12)

        trend_signals = sum([ema_trend, high_volatility, strong_direction, sequential_trend, structural_trend])
        return 'TREND' if trend_signals >= 3 else 'RANGE'

    def connect_mt5(self, login=None, password=None, server=None):
        """Connect to MT5 terminal"""
        return self.mt5_downloader.connect(login=login, password=password, server=server)

    def get_account_info(self):
        """Get MT5 account information"""
        account_info = mt5.account_info()
        if account_info is None:
            return None

        return {
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'margin_free': account_info.margin_free,
            'profit': account_info.profit,
            'leverage': account_info.leverage,
        }

    def calculate_lot_size(self, account_balance, risk_percent=2.0, sl_points=20):
        """
        Calculate lot size based on risk management

        Args:
            account_balance: Current account balance
            risk_percent: Risk per trade (default 2%)
            sl_points: Stop loss in points

        Returns:
            Lot size
        """
        risk_amount = account_balance * (risk_percent / 100)

        # For XAUUSD: 1 lot = 100 oz, 1 point = $1 per 0.01 lot
        point_value = 1.0  # $1 per point per 1 lot

        lot_size = risk_amount / (sl_points * point_value)

        # Round to 2 decimals (0.01 minimum for most brokers)
        lot_size = round(lot_size, 2)

        # Minimum lot
        if lot_size < 0.01:
            lot_size = 0.01

        return lot_size

    def send_market_order(self, symbol, order_type, volume, sl=None, tp=None, comment=""):
        """
        Send market order to MT5

        Args:
            symbol: Symbol to trade
            order_type: mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL
            volume: Lot size
            sl: Stop loss price
            tp: Take profit price
            comment: Order comment

        Returns:
            OrderSendResult or None
        """
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"❌ Symbol {symbol} not found")
            return None

        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                print(f"❌ Failed to select symbol {symbol}")
                return None

        # Get current price
        if order_type == mt5.ORDER_TYPE_BUY:
            price = mt5.symbol_info_tick(symbol).ask
        else:
            price = mt5.symbol_info_tick(symbol).bid

        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Add SL/TP if provided
        if sl:
            request["sl"] = sl
        if tp:
            request["tp"] = tp

        # Send order
        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Order failed: {result.retcode}, {result.comment}")
            return None

        return result

    def modify_position(self, ticket, sl=None, tp=None):
        """
        Modify position SL/TP

        Args:
            ticket: Position ticket
            sl: New stop loss
            tp: New take profit
        """
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl if sl else 0,
            "tp": tp if tp else 0,
        }

        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def close_position_partial(self, ticket, volume):
        """
        Close part of position

        Args:
            ticket: Position ticket
            volume: Volume to close
        """
        position = None
        positions = mt5.positions_get(ticket=ticket)
        if positions and len(positions) > 0:
            position = positions[0]

        if not position:
            return False

        # Opposite order type
        if position.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(position.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(position.symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Partial close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def check_for_signals(self):
        """Check for new trading signals"""

        print(f"\n{'='*80}")
        print(f"🔍 Checking for signals at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Download latest data
        df = self.mt5_downloader.get_realtime_data(period_hours=120)

        if df is None or len(df) == 0:
            print("❌ Failed to download data")
            return

        # Run strategy
        try:
            df_strategy = self.strategy.run_strategy(df.copy())

            # Detect market regime
            regime = self.detect_market_regime(df)
            print(f"📊 Market Regime: {regime}")

            # Get signals
            df_signals = df_strategy[df_strategy['signal'] != 0]

            if len(df_signals) == 0:
                print("📊 No signals found")
                return

            # Check last signal
            last_signal = df_signals.iloc[-1]
            last_signal_time = df_signals.index[-1]

            # Check if signal is recent
            if self.last_check is not None:
                time_since_last = (datetime.now() - self.last_check).total_seconds()
                signal_age = (datetime.now() - last_signal_time.to_pydatetime()).total_seconds()

                if signal_age > time_since_last + 3600:
                    print(f"📊 Last signal is old ({signal_age/3600:.1f}h ago), ignoring")
                    return

            direction = 'LONG' if last_signal['signal'] == 1 else 'SHORT'

            # Filter SHORT in RANGE
            if direction == 'SHORT' and regime == 'RANGE' and not self.short_range_enabled:
                print(f"⚠️  SHORT in RANGE filtered (disabled)")
                return

            print(f"🎯 NEW SIGNAL DETECTED!")
            print(f"   Time: {last_signal_time}")
            print(f"   Direction: {direction}")
            print(f"   Regime: {regime}")
            print(f"   Entry: {last_signal['entry_price']:.2f}")
            print(f"   SL: {last_signal['stop_loss']:.2f}")

            # Send signal to Telegram and ask for confirmation
            self.request_trade_confirmation(last_signal, regime, direction)

        except Exception as e:
            print(f"❌ Error checking signals: {e}")
            import traceback
            traceback.print_exc()

            if self.notifier:
                self.notifier.send_error(f"Error: {str(e)}")

    def request_trade_confirmation(self, signal, regime, direction):
        """
        Send signal to Telegram and request confirmation

        Signal will be stored and executed when user confirms
        """
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']

        # Calculate TP based on regime
        if direction == 'LONG':
            if regime == 'TREND':
                tp1, tp2, tp3 = self.long_trend_tp1, self.long_trend_tp2, self.long_trend_tp3
                trailing = self.long_trend_trailing
                timeout = self.long_trend_timeout
            else:
                tp1, tp2, tp3 = self.long_range_tp1, self.long_range_tp2, self.long_range_tp3
                trailing = self.long_range_trailing
                timeout = self.long_range_timeout

            tp1_price = entry_price + tp1
            tp2_price = entry_price + tp2
            tp3_price = entry_price + tp3
        else:
            tp1, tp2, tp3 = self.short_trend_tp1, self.short_trend_tp2, self.short_trend_tp3
            trailing = self.short_trend_trailing
            timeout = self.short_trend_timeout

            tp1_price = entry_price - tp1
            tp2_price = entry_price - tp2
            tp3_price = entry_price - tp3

        # Get account info
        account = self.get_account_info()
        if account:
            suggested_lot = self.calculate_lot_size(
                account['balance'],
                risk_percent=2.0,
                sl_points=abs(entry_price - stop_loss)
            )
        else:
            suggested_lot = 0.01

        # Create signal data
        signal_id = f"{direction}_{int(time.time())}"
        signal_data = {
            'id': signal_id,
            'direction': direction,
            'regime': regime,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'tp1': tp1_price,
            'tp2': tp2_price,
            'tp3': tp3_price,
            'trailing': trailing,
            'timeout': timeout,
            'suggested_lot': suggested_lot,
            'timestamp': datetime.now()
        }

        # Store pending signal
        with self.pending_signal_lock:
            self.pending_signals[signal_id] = signal_data

        # Send confirmation request via Telegram
        message = f"🚨 **НОВЫЙ СИГНАЛ V9** 🚨\n\n"
        message += f"📍 **Направление:** {direction}\n"
        message += f"📊 **Режим:** {regime}\n"
        message += f"💵 **Вход:** {entry_price:.2f}\n"
        message += f"🛑 **SL:** {stop_loss:.2f} ({abs(entry_price-stop_loss):.1f}п)\n"
        message += f"🎯 **TP1:** {tp1_price:.2f} (закрыть 30%)\n"
        message += f"🎯 **TP2:** {tp2_price:.2f} (закрыть 30%)\n"
        message += f"🎯 **TP3:** {tp3_price:.2f} (закрыть 40%)\n"
        message += f"📊 **Trailing:** {trailing}п\n"
        message += f"⏱ **Timeout:** {timeout}ч\n\n"

        if account:
            message += f"💰 **Баланс:** ${account['balance']:.2f}\n"
            message += f"📊 **Equity:** ${account['equity']:.2f}\n"
            message += f"💼 **Suggested lot:** {suggested_lot:.2f}\n\n"

        message += f"⚠️ **Signal ID:** `{signal_id}`\n\n"
        message += f"✅ Для подтверждения отправь: `/confirm {signal_id} [lot_size]`\n"
        message += f"❌ Для отмены отправь: `/cancel {signal_id}`\n"
        message += f"⏰ Сигнал действителен 15 минут"

        # Send to Telegram
        if self.notifier:
            self.notifier.send_message(
                chat_id=self.notifier.chat_id,
                text=message,
                parse_mode='Markdown'
            )

        print(f"📱 Signal sent to Telegram. Waiting for confirmation...")
        print(f"   Signal ID: {signal_id}")

    async def start_telegram_bot(self):
        """Start Telegram bot application for command handling"""
        self.telegram_app = Application.builder().token(self.telegram_token).build()

        # Setup command handlers
        self.command_handler.setup_handlers(self.telegram_app)

        # Start bot
        await self.telegram_app.initialize()
        await self.telegram_app.start()
        await self.telegram_app.updater.start_polling()

        print("✅ Telegram command bot started")

    def run_telegram_bot_thread(self):
        """Run Telegram bot in separate thread"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start_telegram_bot())
        loop.run_forever()

    def run(self):
        """Main loop - check for signals periodically"""
        print(f"\n🚀 Starting Live Trading Bot - SEMI-AUTO MODE")
        print(f"   Check interval: {self.check_interval}s ({self.check_interval/3600:.1f}h)")
        print(f"   ⚠️  Trades require YOUR confirmation via Telegram")

        # Start position monitor thread
        self.position_monitor_running = True
        self.position_monitor_thread = threading.Thread(target=self.monitor_positions_loop, daemon=True)
        self.position_monitor_thread.start()
        print("✅ Position monitor started")

        # Start Telegram bot thread
        telegram_thread = threading.Thread(target=self.run_telegram_bot_thread, daemon=True)
        telegram_thread.start()
        print("✅ Telegram bot thread started")

        # Give threads time to start
        time.sleep(2)

        # Test Telegram connection
        if self.notifier:
            if self.notifier.test_connection():
                message = "🚀 **Live Bot Started - SEMI-AUTO MODE**\n\n"
                message += "✅ Connected to MT5\n"
                message += "📊 Analyzing market every hour\n"
                message += "⚠️ Will ask confirmation before each trade\n\n"
                message += "**Commands:**\n"
                message += "/status - Check bot status\n"
                message += "/positions - Show open positions\n"
                message += "/confirm <id> [lot] - Confirm signal\n"
                message += "/cancel <id> - Cancel signal\n"
                message += "/help - Show help"

                self.notifier.send_message(
                    chat_id=self.notifier.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )

        while True:
            try:
                # Check for new signals
                self.check_for_signals()

                # Update last check time
                self.last_check = datetime.now()

                # Clean up old pending signals (>15 min)
                self.cleanup_old_signals()

                # Sleep until next check
                print(f"💤 Sleeping {self.check_interval/3600:.1f}h until next check...")
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                print("\n⚠️  Bot stopped by user")
                self.position_monitor_running = False
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                import traceback
                traceback.print_exc()

                if self.notifier:
                    self.notifier.send_error(f"Main loop error: {str(e)}")

                time.sleep(60)

    def monitor_positions_loop(self):
        """
        Monitor open positions continuously
        - Check TP1/TP2/TP3 hits
        - Execute partial closes
        - Update trailing stops
        - Handle timeouts
        """
        print("🔍 Position monitor thread started")

        while self.position_monitor_running:
            try:
                with self.open_positions_lock:
                    if len(self.open_positions) == 0:
                        time.sleep(60)
                        continue

                    # Check each position
                    for position in self.open_positions[:]:  # Copy list to avoid modification issues
                        self.check_position(position)

                time.sleep(60)  # Check every minute

            except Exception as e:
                print(f"❌ Error in position monitor: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)

        print("⚠️  Position monitor thread stopped")

    def check_position(self, position):
        """Check single position for TP hits, trailing, timeout"""

        ticket = position['ticket']

        # Get current position from MT5
        mt5_positions = mt5.positions_get(ticket=ticket)

        if not mt5_positions or len(mt5_positions) == 0:
            # Position closed (SL hit or manual close)
            print(f"📍 Position {ticket} closed")
            with self.open_positions_lock:
                self.open_positions.remove(position)

            # Notify
            if self.notifier:
                message = f"🔴 **POSITION CLOSED**\n\n"
                message += f"Ticket: {ticket}\n"
                message += f"Direction: {position['direction']}\n"
                message += f"Reason: SL or Manual"
                self.notifier.send_message(
                    chat_id=self.notifier.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
            return

        mt5_pos = mt5_positions[0]
        current_price = mt5_pos.price_current
        current_volume = mt5_pos.volume

        # Update current volume
        position['current_volume'] = current_volume

        # Check for timeout
        entry_time = position['entry_time']
        hours_open = (datetime.now() - entry_time).total_seconds() / 3600

        if hours_open > position['timeout_hours']:
            print(f"⏰ Position {ticket} timeout ({hours_open:.1f}h)")
            self.close_position_full(ticket, "TIMEOUT")
            with self.open_positions_lock:
                self.open_positions.remove(position)
            return

        # Check TP hits
        direction = position['direction']

        if direction == 'LONG':
            # Check TP3
            if not position['tp3_hit'] and current_price >= position['tp3_price']:
                print(f"🎯 TP3 HIT! Closing remaining {self.close_pct3*100:.0f}%")
                self.execute_partial_close(position, self.close_pct3, 'TP3')
                position['tp3_hit'] = True

            # Check TP2
            elif not position['tp2_hit'] and current_price >= position['tp2_price']:
                print(f"🎯 TP2 HIT! Closing {self.close_pct2*100:.0f}%")
                self.execute_partial_close(position, self.close_pct2, 'TP2')
                position['tp2_hit'] = True

            # Check TP1
            elif not position['tp1_hit'] and current_price >= position['tp1_price']:
                print(f"🎯 TP1 HIT! Closing {self.close_pct1*100:.0f}%")
                self.execute_partial_close(position, self.close_pct1, 'TP1')
                position['tp1_hit'] = True

                # Move to trailing stop after TP1
                new_sl = position['entry_price'] + position['trailing_distance']
                print(f"📊 Moving SL to trailing: {new_sl:.2f}")
                self.modify_position(ticket, sl=new_sl)
                position['stop_loss'] = new_sl

        else:  # SHORT
            # Check TP3
            if not position['tp3_hit'] and current_price <= position['tp3_price']:
                print(f"🎯 TP3 HIT! Closing remaining {self.close_pct3*100:.0f}%")
                self.execute_partial_close(position, self.close_pct3, 'TP3')
                position['tp3_hit'] = True

            # Check TP2
            elif not position['tp2_hit'] and current_price <= position['tp2_price']:
                print(f"🎯 TP2 HIT! Closing {self.close_pct2*100:.0f}%")
                self.execute_partial_close(position, self.close_pct2, 'TP2')
                position['tp2_hit'] = True

            # Check TP1
            elif not position['tp1_hit'] and current_price <= position['tp1_price']:
                print(f"🎯 TP1 HIT! Closing {self.close_pct1*100:.0f}%")
                self.execute_partial_close(position, self.close_pct1, 'TP1')
                position['tp1_hit'] = True

                # Move to trailing stop after TP1
                new_sl = position['entry_price'] - position['trailing_distance']
                print(f"📊 Moving SL to trailing: {new_sl:.2f}")
                self.modify_position(ticket, sl=new_sl)
                position['stop_loss'] = new_sl

        # Update trailing stop (if TP1 already hit)
        if position['tp1_hit']:
            self.update_trailing_stop(position, current_price)

    def execute_partial_close(self, position, close_pct, tp_name):
        """Execute partial close and send notification"""

        ticket = position['ticket']
        volume_to_close = position['initial_volume'] * close_pct
        volume_to_close = round(volume_to_close, 2)

        if volume_to_close < 0.01:
            volume_to_close = 0.01

        # Close partial
        success = self.close_position_partial(ticket, volume_to_close)

        if success:
            print(f"✅ Closed {volume_to_close:.2f} lots at {tp_name}")

            # Send Telegram notification
            if self.notifier:
                message = f"✅ **{tp_name} HIT!**\n\n"
                message += f"Ticket: {ticket}\n"
                message += f"Direction: {position['direction']}\n"
                message += f"Closed: {volume_to_close:.2f} lots ({close_pct*100:.0f}%)\n"
                message += f"Price: {position[f'{tp_name.lower()}_price']:.2f}"

                self.notifier.send_message(
                    chat_id=self.notifier.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
        else:
            print(f"❌ Failed to close partial at {tp_name}")

    def update_trailing_stop(self, position, current_price):
        """Update trailing stop if price moved favorably"""

        ticket = position['ticket']
        direction = position['direction']
        trailing_distance = position['trailing_distance']
        current_sl = position['stop_loss']

        if direction == 'LONG':
            # New trailing SL
            new_sl = current_price - trailing_distance

            # Only move SL up
            if new_sl > current_sl:
                print(f"📈 Updating trailing SL: {current_sl:.2f} → {new_sl:.2f}")
                self.modify_position(ticket, sl=new_sl)
                position['stop_loss'] = new_sl

        else:  # SHORT
            # New trailing SL
            new_sl = current_price + trailing_distance

            # Only move SL down
            if new_sl < current_sl:
                print(f"📉 Updating trailing SL: {current_sl:.2f} → {new_sl:.2f}")
                self.modify_position(ticket, sl=new_sl)
                position['stop_loss'] = new_sl

    def close_position_full(self, ticket, reason):
        """Close entire position"""

        # Get position
        mt5_positions = mt5.positions_get(ticket=ticket)
        if not mt5_positions or len(mt5_positions) == 0:
            return

        mt5_pos = mt5_positions[0]

        # Close with opposite order
        if mt5_pos.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(mt5_pos.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(mt5_pos.symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_pos.symbol,
            "volume": mt5_pos.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": reason,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Position {ticket} closed: {reason}")

            # Notify
            if self.notifier:
                message = f"🔴 **POSITION CLOSED**\n\n"
                message += f"Ticket: {ticket}\n"
                message += f"Reason: {reason}\n"
                message += f"Close price: {price:.2f}"

                self.notifier.send_message(
                    chat_id=self.notifier.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
        else:
            print(f"❌ Failed to close position {ticket}: {result.comment}")

    def cleanup_old_signals(self):
        """Remove pending signals older than 15 minutes"""
        with self.pending_signal_lock:
            current_time = datetime.now()
            expired = []

            for signal_id, signal_data in self.pending_signals.items():
                age = (current_time - signal_data['timestamp']).total_seconds() / 60
                if age > 15:
                    expired.append(signal_id)

            for signal_id in expired:
                del self.pending_signals[signal_id]
                print(f"⏰ Signal {signal_id} expired")


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Get credentials from env
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not telegram_token or not telegram_chat_id:
        print("❌ Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required!")
        print("   Add them to .env file")
        exit(1)

    # Create bot
    bot = LiveBotMT5SemiAuto(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        symbol='XAUUSD',
        timeframe=mt5.TIMEFRAME_H1,
        check_interval=3600  # 1 hour
    )

    # Connect to MT5
    if not bot.connect_mt5():
        print("❌ Failed to connect to MT5")
        print("   Make sure MT5 terminal is running")
        print("   Enable 'Algo Trading' in MT5")
        exit(1)

    print("✅ Connected to MT5")

    # Show account info
    account = bot.get_account_info()
    if account:
        print(f"\n💰 Account Info:")
        print(f"   Balance: ${account['balance']:.2f}")
        print(f"   Equity: ${account['equity']:.2f}")
        print(f"   Leverage: {account['leverage']}x")

    # Run bot
    bot.run()
