#!/usr/bin/env python3
"""
Live MT5 Trading Bot - FULL AUTOMATIC (V9 Strategy)

РЕЖИМ ПОЛНОГО АВТОМАТА:
1. Бот анализирует рынок каждый час
2. Находит сигналы по стратегии V9
3. АВТОМАТИЧЕСКИ открывает позицию (БЕЗ подтверждения)
4. АВТОМАТИЧЕСКИ управляет открытыми позициями (TP, SL, Trailing)

ОПАСНОСТЬ:
- Бот торгует САМОСТОЯТЕЛЬНО
- Убедитесь что параметры правильные
- Рекомендуется только для опытных трейдеров
- ВСЕГДА начинайте с DEMO счёта
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


class LiveBotMT5FullAuto:
    """
    Live MT5 Trading Bot - Full Automatic Mode

    V9 PARAMETERS (CHAMPION):
    - LONG TREND: TP 35/65/100п, Trailing 25п, Timeout 60ч
    - LONG RANGE: TP 25/45/65п, Trailing 20п, Timeout 48ч
    - SHORT TREND: TP 18/30/42п, Trailing 13п, Timeout 24ч
    - Partial close: 30%/30%/40%
    """

    def __init__(self, telegram_token=None, telegram_chat_id=None,
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1,
                 check_interval=3600, timezone_offset=5,
                 risk_percent=2.0, max_positions=3):
        """
        Initialize Full-Auto Live Bot

        Args:
            telegram_token: Telegram bot token (optional, for notifications)
            telegram_chat_id: Telegram chat ID (optional)
            symbol: MT5 symbol (default: 'XAUUSD')
            timeframe: MT5 timeframe (default: mt5.TIMEFRAME_H1)
            check_interval: How often to check for signals (seconds)
            timezone_offset: Timezone offset from UTC
            risk_percent: Risk per trade (default 2%)
            max_positions: Maximum simultaneous positions (default 3)
        """
        self.strategy = SimplifiedSMCStrategy()
        self.symbol = symbol
        self.timeframe = timeframe
        self.check_interval = check_interval
        self.risk_percent = risk_percent
        self.max_positions = max_positions

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

        # Telegram notifier (optional)
        self.notifier = None
        if telegram_token and telegram_chat_id:
            self.notifier = TelegramNotifier(telegram_token, telegram_chat_id, timezone_offset=timezone_offset)

        # Tracking
        self.open_positions = []
        self.open_positions_lock = threading.Lock()
        self.last_check = None
        self.last_signal_time = None

        # Position monitoring
        self.position_monitor_running = False
        self.position_monitor_thread = None

        print("✅ Live Trading Bot - FULL AUTO initialized")
        print(f"   Symbol: {symbol}")
        print(f"   Mode: FULL AUTOMATIC ⚠️")
        print(f"   Risk per trade: {risk_percent}%")
        print(f"   Max positions: {max_positions}")
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

    def calculate_lot_size(self, account_balance, sl_points):
        """
        Calculate lot size based on risk management

        Args:
            account_balance: Current account balance
            sl_points: Stop loss in points

        Returns:
            Lot size
        """
        risk_amount = account_balance * (self.risk_percent / 100)

        # For XAUUSD: 1 lot = 100 oz, 1 point = $1 per 0.01 lot
        point_value = 1.0

        lot_size = risk_amount / (sl_points * point_value)

        # Round to 2 decimals
        lot_size = round(lot_size, 2)

        # Minimum lot
        if lot_size < 0.01:
            lot_size = 0.01

        return lot_size

    def send_market_order(self, symbol, order_type, volume, sl=None, tp=None, comment=""):
        """Send market order to MT5"""
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
        """Modify position SL/TP"""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl if sl else 0,
            "tp": tp if tp else 0,
        }

        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def close_position_partial(self, ticket, volume):
        """Close part of position"""
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
        """Check for new trading signals and execute automatically"""

        print(f"\n{'='*80}")
        print(f"🔍 Checking for signals at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Check if max positions reached
        with self.open_positions_lock:
            if len(self.open_positions) >= self.max_positions:
                print(f"⚠️  Max positions ({self.max_positions}) reached, skipping new signals")
                return

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

            # Check if we already traded this signal
            if self.last_signal_time is not None:
                if last_signal_time <= self.last_signal_time:
                    print(f"📊 Signal already traded")
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

            # Execute trade automatically
            self.execute_trade(last_signal, regime, direction, last_signal_time)

        except Exception as e:
            print(f"❌ Error checking signals: {e}")
            import traceback
            traceback.print_exc()

            if self.notifier:
                self.notifier.send_error(f"Error: {str(e)}")

    def execute_trade(self, signal, regime, direction, signal_time):
        """
        Execute trade automatically (NO confirmation required)
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
            order_type = mt5.ORDER_TYPE_BUY
        else:
            tp1, tp2, tp3 = self.short_trend_tp1, self.short_trend_tp2, self.short_trend_tp3
            trailing = self.short_trend_trailing
            timeout = self.short_trend_timeout

            tp1_price = entry_price - tp1
            tp2_price = entry_price - tp2
            tp3_price = entry_price - tp3
            order_type = mt5.ORDER_TYPE_SELL

        # Get account info
        account = self.get_account_info()
        if not account:
            print("❌ Failed to get account info")
            return

        # Calculate lot size
        lot_size = self.calculate_lot_size(
            account['balance'],
            sl_points=abs(entry_price - stop_loss)
        )

        print(f"\n⏳ Opening {direction} position...")
        print(f"   Entry: {entry_price:.2f}")
        print(f"   SL: {stop_loss:.2f}")
        print(f"   TP1: {tp1_price:.2f} (30%)")
        print(f"   TP2: {tp2_price:.2f} (30%)")
        print(f"   TP3: {tp3_price:.2f} (40%)")
        print(f"   Lot: {lot_size:.2f}")

        # Send order
        result = self.send_market_order(
            symbol=self.symbol,
            order_type=order_type,
            volume=lot_size,
            sl=stop_loss,
            tp=None,  # No TP - bot manages
            comment=f"V9_{direction}_{regime}"
        )

        if not result:
            print("❌ Failed to open position")
            return

        print(f"✅ Position opened!")
        print(f"   Ticket: {result.order}")

        # Track position
        position_data = {
            'ticket': result.order,
            'direction': direction,
            'regime': regime,
            'entry_price': result.price,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss,
            'tp1_price': tp1_price,
            'tp2_price': tp2_price,
            'tp3_price': tp3_price,
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'trailing_distance': trailing,
            'timeout_hours': timeout,
            'initial_volume': lot_size,
            'current_volume': lot_size,
        }

        with self.open_positions_lock:
            self.open_positions.append(position_data)

        # Update last signal time
        self.last_signal_time = signal_time

        # Send Telegram notification
        if self.notifier:
            message = f"✅ **POSITION OPENED (AUTO)**\n\n"
            message += f"📍 Direction: {direction}\n"
            message += f"📊 Regime: {regime}\n"
            message += f"💵 Entry: {result.price:.2f}\n"
            message += f"💼 Lot: {lot_size:.2f}\n"
            message += f"🛑 SL: {stop_loss:.2f}\n"
            message += f"🎯 TP1: {tp1_price:.2f} (30%)\n"
            message += f"🎯 TP2: {tp2_price:.2f} (30%)\n"
            message += f"🎯 TP3: {tp3_price:.2f} (40%)\n"
            message += f"🎫 Ticket: {result.order}\n\n"
            message += f"✨ Bot will manage TP/SL automatically"

            self.notifier.send_message(message)

    def run(self):
        """Main loop - check for signals periodically"""
        print(f"\n🚀 Starting Live Trading Bot - FULL AUTO MODE")
        print(f"   Check interval: {self.check_interval}s ({self.check_interval/3600:.1f}h)")
        print(f"   ⚠️  Bot will trade AUTOMATICALLY without confirmation!")

        # Start position monitor thread
        self.position_monitor_running = True
        self.position_monitor_thread = threading.Thread(target=self.monitor_positions_loop, daemon=True)
        self.position_monitor_thread.start()
        print("✅ Position monitor started")

        # Send startup notification
        if self.notifier:
            if self.notifier.test_connection():
                message = "🚀 **Live Bot Started - FULL AUTO MODE**\n\n"
                message += "✅ Connected to MT5\n"
                message += "📊 Analyzing market every hour\n"
                message += "⚠️ **Bot will trade AUTOMATICALLY**\n\n"
                message += f"Risk per trade: {self.risk_percent}%\n"
                message += f"Max positions: {self.max_positions}\n\n"
                message += "⚠️ Monitor your account regularly!"

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
        """Monitor open positions continuously"""
        print("🔍 Position monitor thread started")

        while self.position_monitor_running:
            try:
                with self.open_positions_lock:
                    if len(self.open_positions) == 0:
                        time.sleep(60)
                        continue

                    for position in self.open_positions[:]:
                        self.check_position(position)

                time.sleep(60)

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
            print(f"📍 Position {ticket} closed")
            with self.open_positions_lock:
                self.open_positions.remove(position)

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

        position['current_volume'] = current_volume

        # Check timeout
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
            if not position['tp3_hit'] and current_price >= position['tp3_price']:
                print(f"🎯 TP3 HIT! Closing remaining {self.close_pct3*100:.0f}%")
                self.execute_partial_close(position, self.close_pct3, 'TP3')
                position['tp3_hit'] = True

            elif not position['tp2_hit'] and current_price >= position['tp2_price']:
                print(f"🎯 TP2 HIT! Closing {self.close_pct2*100:.0f}%")
                self.execute_partial_close(position, self.close_pct2, 'TP2')
                position['tp2_hit'] = True

            elif not position['tp1_hit'] and current_price >= position['tp1_price']:
                print(f"🎯 TP1 HIT! Closing {self.close_pct1*100:.0f}%")
                self.execute_partial_close(position, self.close_pct1, 'TP1')
                position['tp1_hit'] = True

                new_sl = position['entry_price'] + position['trailing_distance']
                print(f"📊 Moving SL to trailing: {new_sl:.2f}")
                self.modify_position(ticket, sl=new_sl)
                position['stop_loss'] = new_sl

        else:  # SHORT
            if not position['tp3_hit'] and current_price <= position['tp3_price']:
                print(f"🎯 TP3 HIT! Closing remaining {self.close_pct3*100:.0f}%")
                self.execute_partial_close(position, self.close_pct3, 'TP3')
                position['tp3_hit'] = True

            elif not position['tp2_hit'] and current_price <= position['tp2_price']:
                print(f"🎯 TP2 HIT! Closing {self.close_pct2*100:.0f}%")
                self.execute_partial_close(position, self.close_pct2, 'TP2')
                position['tp2_hit'] = True

            elif not position['tp1_hit'] and current_price <= position['tp1_price']:
                print(f"🎯 TP1 HIT! Closing {self.close_pct1*100:.0f}%")
                self.execute_partial_close(position, self.close_pct1, 'TP1')
                position['tp1_hit'] = True

                new_sl = position['entry_price'] - position['trailing_distance']
                print(f"📊 Moving SL to trailing: {new_sl:.2f}")
                self.modify_position(ticket, sl=new_sl)
                position['stop_loss'] = new_sl

        if position['tp1_hit']:
            self.update_trailing_stop(position, current_price)

    def execute_partial_close(self, position, close_pct, tp_name):
        """Execute partial close"""
        ticket = position['ticket']
        volume_to_close = position['initial_volume'] * close_pct
        volume_to_close = round(volume_to_close, 2)

        if volume_to_close < 0.01:
            volume_to_close = 0.01

        success = self.close_position_partial(ticket, volume_to_close)

        if success:
            print(f"✅ Closed {volume_to_close:.2f} lots at {tp_name}")

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
        """Update trailing stop"""
        ticket = position['ticket']
        direction = position['direction']
        trailing_distance = position['trailing_distance']
        current_sl = position['stop_loss']

        if direction == 'LONG':
            new_sl = current_price - trailing_distance
            if new_sl > current_sl:
                print(f"📈 Updating trailing SL: {current_sl:.2f} → {new_sl:.2f}")
                self.modify_position(ticket, sl=new_sl)
                position['stop_loss'] = new_sl
        else:
            new_sl = current_price + trailing_distance
            if new_sl < current_sl:
                print(f"📉 Updating trailing SL: {current_sl:.2f} → {new_sl:.2f}")
                self.modify_position(ticket, sl=new_sl)
                position['stop_loss'] = new_sl

    def close_position_full(self, ticket, reason):
        """Close entire position"""
        mt5_positions = mt5.positions_get(ticket=ticket)
        if not mt5_positions or len(mt5_positions) == 0:
            return

        mt5_pos = mt5_positions[0]

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


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    print("\n" + "="*80)
    print("⚠️  FULL AUTOMATIC MODE WARNING ⚠️")
    print("="*80)
    print("\nThis bot will:")
    print("  - Find signals automatically")
    print("  - Open positions WITHOUT your confirmation")
    print("  - Manage positions automatically")
    print("\n⚠️  ONLY use on DEMO account for testing!")
    print("⚠️  Monitor your account regularly!")
    print("="*80)

    confirm = input("\nType 'I UNDERSTAND' to continue: ")
    if confirm != "I UNDERSTAND":
        print("Aborted.")
        exit(0)

    # Get credentials from env (optional)
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    # Create bot
    bot = LiveBotMT5FullAuto(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        symbol='XAUUSD',
        timeframe=mt5.TIMEFRAME_H1,
        check_interval=3600,  # 1 hour
        risk_percent=2.0,
        max_positions=3
    )

    # Connect to MT5
    if not bot.connect_mt5():
        print("❌ Failed to connect to MT5")
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
