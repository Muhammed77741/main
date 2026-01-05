"""
Live Trading Bot V9 - CHAMPION CONFIGURATION 🏆
Uses V9 parameters: bigger TP (35/65/100), wider trailing (25п), partial close 30%/30%/40%
V9 achieved +49.33% PnL in backtest - BEST RESULT!
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import MetaTrader5 as mt5

from simplified_smc_strategy import SimplifiedSMCStrategy
from telegram_notifier import TelegramNotifier
from mt5_data_downloader import MT5DataDownloader


class LiveTradingBotV9:
    """
    Live trading bot with V9 configuration (CHAMPION! 🏆)

    V9 PARAMETERS - BIGGER TARGETS:
    - LONG TREND: TP 35/65/100п (was 30/55/90), Trailing 25п (was 18), Timeout 60ч
    - LONG RANGE: TP 25/45/65п (was 20/35/50), Trailing 20п (was 15), Timeout 48ч
    - SHORT TREND: TP 18/30/42п (was 15/25/35), Trailing 13п (was 10), Timeout 24ч
    - Partial close: 30%/30%/40%
    - Market regime detection: TREND/RANGE

    WHY V9 IS BETTER:
    - Trailing 25п = 2.6x avg range (was 1.9x) - gives more room
    - TP3 100п covers 90% of realistic 12h movements
    - Reduced timeout losses: -19.53% vs V8: -40.58%
    - +49.33% PnL, 63.2% Win Rate, Profit Factor 1.47
    """

    def __init__(self, telegram_token=None, telegram_chat_id=None, check_interval=3600,
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1, timezone_offset=5):
        """
        Initialize live trading bot with V9 configuration

        Args:
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            check_interval: How often to check for signals (seconds), default 1 hour
            symbol: MT5 symbol (default: 'XAUUSD')
            timeframe: MT5 timeframe (default: mt5.TIMEFRAME_H1)
            timezone_offset: Timezone offset in hours from UTC (default: 5 for UTC+5)
        """
        self.strategy = SimplifiedSMCStrategy()
        self.check_interval = check_interval
        self.symbol = symbol
        self.timeframe = timeframe

        # V9 LONG TREND parameters - INCREASED (+17-20%)
        self.long_trend_tp1 = 35  # Was 30 (+17%)
        self.long_trend_tp2 = 65  # Was 55 (+18%)
        self.long_trend_tp3 = 100  # Was 90 (+11%)
        self.long_trend_trailing = 25  # Was 18 (+39%)
        self.long_trend_timeout = 60

        # V9 LONG RANGE parameters - INCREASED (+25-30%)
        self.long_range_tp1 = 25  # Was 20 (+25%)
        self.long_range_tp2 = 45  # Was 35 (+29%)
        self.long_range_tp3 = 65  # Was 50 (+30%)
        self.long_range_trailing = 20  # Was 15 (+33%)
        self.long_range_timeout = 48

        # V9 SHORT TREND parameters - INCREASED (+20%)
        self.short_trend_tp1 = 18  # Was 15 (+20%)
        self.short_trend_tp2 = 30  # Was 25 (+20%)
        self.short_trend_tp3 = 42  # Was 35 (+20%)
        self.short_trend_trailing = 13  # Was 10 (+30%)
        self.short_trend_timeout = 24

        # V9 partial close (30%/30%/40%)
        self.close_pct1 = 0.3
        self.close_pct2 = 0.3
        self.close_pct3 = 0.4

        # SHORT RANGE disabled
        self.short_range_enabled = False

        # MT5 data downloader
        self.mt5_downloader = MT5DataDownloader(symbol=symbol, timeframe=timeframe)

        # Telegram notifier
        if telegram_token and telegram_chat_id:
            self.notifier = TelegramNotifier(telegram_token, telegram_chat_id, timezone_offset=timezone_offset)
        else:
            self.notifier = None
            print("⚠️  Telegram notifications disabled")

        # Open positions tracking
        self.open_positions = []
        self.df = None
        self.last_check = None
        self.closed_trades = []

        print("✅ Live Trading Bot V9 initialized 🏆")
        print(f"   Symbol: {symbol}")
        print(f"   Partial Close: {self.close_pct1*100:.0f}%/{self.close_pct2*100:.0f}%/{self.close_pct3*100:.0f}%")
        print(f"   LONG TREND: TP {self.long_trend_tp1}/{self.long_trend_tp2}/{self.long_trend_tp3}п, Trailing {self.long_trend_trailing}п")

    def detect_market_regime(self, df, lookback=100):
        """
        Detect market regime: TREND or RANGE
        (Same logic as V9 backtest)
        """
        if len(df) < lookback:
            return 'RANGE'

        recent_data = df.iloc[-lookback:]

        # 1. EMA CROSSOVER
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()

        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]

        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
        ema_trend = ema_diff_pct > 0.3

        # 2. ATR
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()

        high_volatility = atr > avg_atr * 1.05

        # 3. Directional movement
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()

        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35

        # 4. Sequential movements
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])

        sequential_trend = abs(up_moves - down_moves) > lookback * 0.15

        # 5. Price breaks
        recent_high = recent_data['high'].max()
        recent_low = recent_data['low'].min()
        prev_high = recent_data['high'].iloc[:-20].max() if len(recent_data) > 20 else recent_high
        prev_low = recent_data['low'].iloc[:-20].min() if len(recent_data) > 20 else recent_low

        breakout = (recent_high > prev_high * 1.01) or (recent_low < prev_low * 0.99)

        # Count trend signals
        trend_signals = sum([
            ema_trend,
            high_volatility,
            strong_direction,
            sequential_trend,
            breakout
        ])

        is_trend = trend_signals >= 3

        return 'TREND' if is_trend else 'RANGE'

    def connect_mt5(self, login=None, password=None, server=None):
        """Connect to MT5 terminal"""
        return self.mt5_downloader.connect(login=login, password=password, server=server)

    def download_realtime_data(self, period_hours=120):
        """Download real-time data from MT5"""
        try:
            print(f"📥 Downloading {self.symbol} data from MT5...")
            df = self.mt5_downloader.get_realtime_data(period_hours=period_hours)

            if df is None or len(df) == 0:
                print(f"❌ Failed to download data")
                return None

            print(f"✅ Downloaded {len(df)} candles")
            print(f"   Latest: {df.index[-1]} | Price: {df['close'].iloc[-1]:.2f}")

            return df

        except Exception as e:
            print(f"❌ Error downloading data: {e}")
            return None

    def get_current_price(self):
        """Get current price from MT5"""
        return self.mt5_downloader.get_current_price()

    def check_for_signals(self):
        """Check for new trading signals with market regime detection"""

        print(f"\n{'='*80}")
        print(f"🔍 Checking for signals at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Download latest data
        df = self.download_realtime_data()

        if df is None:
            print("❌ Failed to download data")
            return

        self.df = df

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

            # Open position with regime-specific parameters
            self.open_position(last_signal, last_signal_time, regime)

        except Exception as e:
            print(f"❌ Error checking signals: {e}")
            import traceback
            traceback.print_exc()

            if self.notifier:
                self.notifier.send_error(f"Error: {str(e)}")

    def open_position(self, signal, timestamp, regime):
        """Open a new position with V9 parameters"""

        entry_price = signal['entry_price']
        direction = 'LONG' if signal['signal'] == 1 else 'SHORT'

        # Select parameters based on direction and regime
        if direction == 'LONG':
            if regime == 'TREND':
                tp1, tp2, tp3 = self.long_trend_tp1, self.long_trend_tp2, self.long_trend_tp3
                trailing = self.long_trend_trailing
                timeout = self.long_trend_timeout
            else:  # RANGE
                tp1, tp2, tp3 = self.long_range_tp1, self.long_range_tp2, self.long_range_tp3
                trailing = self.long_range_trailing
                timeout = self.long_range_timeout
        else:  # SHORT (only TREND)
            tp1, tp2, tp3 = self.short_trend_tp1, self.short_trend_tp2, self.short_trend_tp3
            trailing = self.short_trend_trailing
            timeout = self.short_trend_timeout

        # Calculate TP levels
        if direction == 'LONG':
            tp1_price = entry_price + tp1
            tp2_price = entry_price + tp2
            tp3_price = entry_price + tp3
        else:  # SHORT
            tp1_price = entry_price - tp1
            tp2_price = entry_price - tp2
            tp3_price = entry_price - tp3

        position = {
            'entry_time': timestamp,
            'direction': direction,
            'regime': regime,
            'entry_price': entry_price,
            'stop_loss': signal['stop_loss'],
            'tp1_price': tp1_price,
            'tp2_price': tp2_price,
            'tp3_price': tp3_price,
            'trailing_distance': trailing,
            'timeout_hours': timeout,
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'trailing_active': False,
            'trailing_sl': None,
            'position_remaining': 1.0,
            'total_pnl_pct': 0.0,
            'pattern': signal.get('pattern', 'N/A'),
        }

        self.open_positions.append(position)

        print(f"✅ Position opened: {direction} {regime} @ {entry_price:.2f}")
        print(f"   TP1: {tp1_price:.2f} ({self.close_pct1*100:.0f}%)")
        print(f"   TP2: {tp2_price:.2f} ({self.close_pct2*100:.0f}%)")
        print(f"   TP3: {tp3_price:.2f} ({self.close_pct3*100:.0f}%)")
        print(f"   SL:  {signal['stop_loss']:.2f}")
        print(f"   Trailing: {trailing}п, Timeout: {timeout}ч")

        # Send Telegram notification
        if self.notifier:
            signal_data = {
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': signal['stop_loss'],
                'take_profit': tp1_price,
                'tp1': tp1_price,
                'tp2': tp2_price,
                'tp3': tp3_price,
                'regime': regime,
                'pattern': position['pattern'],
                'timestamp': timestamp
            }
            self.notifier.send_entry_signal(signal_data)

    def check_open_positions(self):
        """Check open positions with V9 logic: TP, trailing, timeout"""

        if len(self.open_positions) == 0 or self.df is None:
            return

        latest_candle = self.df.iloc[-1]
        latest_time = self.df.index[-1]
        latest_high = latest_candle['high']
        latest_low = latest_candle['low']
        latest_close = latest_candle['close']

        positions_to_close = []

        for i, pos in enumerate(self.open_positions):
            if pos['position_remaining'] <= 0:
                positions_to_close.append((i, pos['entry_price'], 'CLOSED', pos['total_pnl_pct']))
                continue

            # Check timeout
            time_in_trade = (latest_time - pos['entry_time']).total_seconds() / 3600

            if time_in_trade >= pos['timeout_hours']:
                # Close by timeout
                if pos['direction'] == 'LONG':
                    pnl_pct = ((latest_close - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                else:
                    pnl_pct = ((pos['entry_price'] - latest_close) / pos['entry_price']) * 100 * pos['position_remaining']

                pos['total_pnl_pct'] += pnl_pct
                positions_to_close.append((i, latest_close, 'TIMEOUT', pos['total_pnl_pct']))
                print(f"   ⏱️  TIMEOUT @ {latest_close:.2f} ({time_in_trade:.1f}h)")
                continue

            # Check SL/TP/Trailing
            if pos['direction'] == 'LONG':
                # Check SL (or trailing SL)
                active_sl = pos['trailing_sl'] if pos['trailing_active'] else pos['stop_loss']

                if latest_low <= active_sl:
                    pnl_pct = ((active_sl - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                    positions_to_close.append((i, active_sl, exit_type, pos['total_pnl_pct']))
                    print(f"   🛑 {exit_type} @ {active_sl:.2f}")
                    continue

                # Check TP3
                if latest_high >= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['tp3_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 @ {pos['tp3_price']:.2f} (closed {self.close_pct3*100:.0f}%)")

                    # Send Telegram notification
                    if self.notifier:
                        pnl_points = (pnl_pct / 100) * pos['entry_price']
                        self.notifier.send_partial_close({
                            'direction': pos['direction'],
                            'tp_level': 'TP3',
                            'tp_price': pos['tp3_price'],
                            'entry_price': pos['entry_price'],
                            'close_pct': self.close_pct3,
                            'pnl_pct': pnl_pct,
                            'pnl_points': pnl_points,
                            'position_remaining': pos['position_remaining'],
                            'regime': pos.get('regime', 'N/A'),
                            'timestamp': latest_time
                        })

                # Check TP2
                if latest_high >= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['tp2_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 @ {pos['tp2_price']:.2f} (closed {self.close_pct2*100:.0f}%)")

                    # Send Telegram notification
                    if self.notifier:
                        pnl_points = (pnl_pct / 100) * pos['entry_price']
                        self.notifier.send_partial_close({
                            'direction': pos['direction'],
                            'tp_level': 'TP2',
                            'tp_price': pos['tp2_price'],
                            'entry_price': pos['entry_price'],
                            'close_pct': self.close_pct2,
                            'pnl_pct': pnl_pct,
                            'pnl_points': pnl_points,
                            'position_remaining': pos['position_remaining'],
                            'regime': pos.get('regime', 'N/A'),
                            'timestamp': latest_time
                        })

                # Check TP1
                if latest_high >= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['tp1_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 @ {pos['tp1_price']:.2f} (closed {self.close_pct1*100:.0f}%)")

                    # Send Telegram notification
                    if self.notifier:
                        pnl_points = (pnl_pct / 100) * pos['entry_price']
                        self.notifier.send_partial_close({
                            'direction': pos['direction'],
                            'tp_level': 'TP1',
                            'tp_price': pos['tp1_price'],
                            'entry_price': pos['entry_price'],
                            'close_pct': self.close_pct1,
                            'pnl_pct': pnl_pct,
                            'pnl_points': pnl_points,
                            'position_remaining': pos['position_remaining'],
                            'regime': pos.get('regime', 'N/A'),
                            'timestamp': latest_time
                        })

                    # Activate trailing stop
                    pos['trailing_active'] = True
                    pos['trailing_sl'] = latest_close - pos['trailing_distance']
                    print(f"   📊 Trailing activated @ {pos['trailing_sl']:.2f}")

                # Update trailing SL
                if pos['trailing_active']:
                    new_trailing_sl = latest_close - pos['trailing_distance']
                    if new_trailing_sl > pos['trailing_sl']:
                        pos['trailing_sl'] = new_trailing_sl
                        print(f"   📈 Trailing updated @ {pos['trailing_sl']:.2f}")

            else:  # SHORT
                # Same logic but reversed
                active_sl = pos['trailing_sl'] if pos['trailing_active'] else pos['stop_loss']

                if latest_high >= active_sl:
                    pnl_pct = ((pos['entry_price'] - active_sl) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                    positions_to_close.append((i, active_sl, exit_type, pos['total_pnl_pct']))
                    print(f"   🛑 {exit_type} @ {active_sl:.2f}")
                    continue

                # TP3, TP2, TP1 (reversed for SHORT)
                if latest_low <= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp3_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 @ {pos['tp3_price']:.2f} (closed {self.close_pct3*100:.0f}%)")

                    # Send Telegram notification
                    if self.notifier:
                        pnl_points = (pnl_pct / 100) * pos['entry_price']
                        self.notifier.send_partial_close({
                            'direction': pos['direction'],
                            'tp_level': 'TP3',
                            'tp_price': pos['tp3_price'],
                            'entry_price': pos['entry_price'],
                            'close_pct': self.close_pct3,
                            'pnl_pct': pnl_pct,
                            'pnl_points': pnl_points,
                            'position_remaining': pos['position_remaining'],
                            'regime': pos.get('regime', 'N/A'),
                            'timestamp': latest_time
                        })

                if latest_low <= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp2_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 @ {pos['tp2_price']:.2f} (closed {self.close_pct2*100:.0f}%)")

                    # Send Telegram notification
                    if self.notifier:
                        pnl_points = (pnl_pct / 100) * pos['entry_price']
                        self.notifier.send_partial_close({
                            'direction': pos['direction'],
                            'tp_level': 'TP2',
                            'tp_price': pos['tp2_price'],
                            'entry_price': pos['entry_price'],
                            'close_pct': self.close_pct2,
                            'pnl_pct': pnl_pct,
                            'pnl_points': pnl_points,
                            'position_remaining': pos['position_remaining'],
                            'regime': pos.get('regime', 'N/A'),
                            'timestamp': latest_time
                        })

                if latest_low <= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp1_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 @ {pos['tp1_price']:.2f} (closed {self.close_pct1*100:.0f}%)")

                    # Send Telegram notification
                    if self.notifier:
                        pnl_points = (pnl_pct / 100) * pos['entry_price']
                        self.notifier.send_partial_close({
                            'direction': pos['direction'],
                            'tp_level': 'TP1',
                            'tp_price': pos['tp1_price'],
                            'entry_price': pos['entry_price'],
                            'close_pct': self.close_pct1,
                            'pnl_pct': pnl_pct,
                            'pnl_points': pnl_points,
                            'position_remaining': pos['position_remaining'],
                            'regime': pos.get('regime', 'N/A'),
                            'timestamp': latest_time
                        })

                    # Activate trailing stop
                    pos['trailing_active'] = True
                    pos['trailing_sl'] = latest_close + pos['trailing_distance']
                    print(f"   📊 Trailing activated @ {pos['trailing_sl']:.2f}")

                if pos['trailing_active']:
                    new_trailing_sl = latest_close + pos['trailing_distance']
                    if new_trailing_sl < pos['trailing_sl']:
                        pos['trailing_sl'] = new_trailing_sl

        # Close positions
        for i, exit_price, exit_type, total_pnl in reversed(positions_to_close):
            pos = self.open_positions.pop(i)

            trade_record = {
                'entry_time': pos['entry_time'],
                'exit_time': latest_time,
                'direction': pos['direction'],
                'regime': pos['regime'],
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'exit_type': exit_type,
                'pnl_pct': total_pnl,
                'duration_hours': time_in_trade
            }

            self.closed_trades.append(trade_record)

            print(f"🔔 Position closed: {pos['direction']} | Exit: {exit_type} | PnL: {total_pnl:+.2f}%")

            # Telegram notification
            if self.notifier:
                exit_data = {
                    'direction': pos['direction'],
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'pnl_pct': total_pnl,
                    'duration_hours': time_in_trade,
                    'entry_time': pos['entry_time'],
                    'exit_time': latest_time
                }
                self.notifier.send_exit_signal(exit_data)

    def run(self):
        """Main loop"""
        print(f"\n🚀 Starting Live Trading Bot V9 - CHAMPION! 🏆")
        print(f"   Check interval: {self.check_interval}s ({self.check_interval/3600:.1f}h)")
        print(f"   V9 Backtest: +49.33% PnL, 63.2% Win Rate")

        # Test Telegram connection and send startup message
        if self.notifier:
            if self.notifier.test_connection():
                self.notifier.send_startup_message()

        while True:
            try:
                # Check for new signals
                self.check_for_signals()

                # Update open positions
                self.check_open_positions()

                # Update last check time
                self.last_check = datetime.now()

                # Show status
                print(f"\n📊 Status: {len(self.open_positions)} open positions")
                if len(self.closed_trades) > 0:
                    total_pnl = sum(t['pnl_pct'] for t in self.closed_trades)
                    print(f"   Total PnL: {total_pnl:+.2f}% ({len(self.closed_trades)} trades)")

                # Sleep until next check
                print(f"💤 Sleeping {self.check_interval/3600:.1f}h until next check...")
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                print("\n⚠️  Bot stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                import traceback
                traceback.print_exc()

                if self.notifier:
                    self.notifier.send_error(f"Main loop error: {str(e)}")

                time.sleep(60)  # Wait 1 minute before retry


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Get credentials from env
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    # Create bot
    bot = LiveTradingBotV9(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        check_interval=3600,  # Check every hour
        symbol='XAUUSD',
        timeframe=mt5.TIMEFRAME_H1
    )

    # Connect to MT5
    if not bot.connect_mt5():
        print("❌ Failed to connect to MT5")
        exit(1)

    print("✅ Connected to MT5")

    # Run bot
    bot.run()
