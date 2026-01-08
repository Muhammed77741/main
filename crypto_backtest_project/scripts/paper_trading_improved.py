"""
Улучшенный Paper Trading Bot с разделением частоты проверок
- Новые сигналы: каждый час (тяжелая операция)
- Открытые позиции: каждые 5 минут (легкая операция)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import sys
from dotenv import load_dotenv
import MetaTrader5 as mt5

sys.path.append('../smc_trading_strategy')
from telegram_notifier import TelegramNotifier
from mt5_data_downloader import MT5DataDownloader
from pattern_recognition_strategy import PatternRecognitionStrategy


class ImprovedPaperTradingBot:
    """
    Paper trading bot с улучшенной частотой проверок

    Ключевое улучшение:
    - Новые сигналы проверяются редко (signal_check_interval, например 1 час)
    - Открытые позиции проверяются часто (position_check_interval, например 5 мин)

    Это решает проблему:
    - TP/SL обнаруживаются в течение 5 минут (не часа!)
    - Новые сигналы ищутся реже (экономия ресурсов)
    """

    def __init__(self, telegram_token=None, telegram_chat_id=None,
                 signal_check_interval=3600,    # 1 час для новых сигналов
                 position_check_interval=300,   # 5 минут для позиций
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1,
                 max_positions=5, timezone_offset=5):
        """
        Initialize improved paper trading bot

        Args:
            signal_check_interval: Как часто искать НОВЫЕ сигналы (секунды, default: 3600 = 1 час)
            position_check_interval: Как часто проверять ОТКРЫТЫЕ позиции (секунды, default: 300 = 5 мин)
            symbol: MT5 symbol
            timeframe: MT5 timeframe
            max_positions: Maximum concurrent positions (default: 5)
            timezone_offset: Timezone offset in hours from UTC (default: 5 for UTC+5)
        """
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')
        self.signal_check_interval = signal_check_interval
        self.position_check_interval = position_check_interval
        self.symbol = symbol
        self.timeframe = timeframe

        # LONG TREND MODE parameters (from baseline)
        self.long_trend_tp1 = 30
        self.long_trend_tp2 = 55
        self.long_trend_tp3 = 90
        self.long_trend_trailing = 18
        self.long_trend_timeout = 60

        # LONG RANGE MODE parameters (from baseline)
        self.long_range_tp1 = 20
        self.long_range_tp2 = 35
        self.long_range_tp3 = 50
        self.long_range_trailing = 15
        self.long_range_timeout = 48

        # SHORT TREND MODE parameters (OPTIMIZED - asymmetric!)
        # Based on analysis: SHORT needs smaller TP, faster trailing, shorter timeout
        self.short_trend_tp1 = 15  # Reduced from 30п
        self.short_trend_tp2 = 25  # Reduced from 55п
        self.short_trend_tp3 = 35  # Reduced from 90п
        self.short_trend_trailing = 10  # Reduced from 18п
        self.short_trend_timeout = 24  # Reduced from 60ч

        # SHORT RANGE MODE - DISABLED (analysis showed -14% PnL in RANGE)
        self.short_range_enabled = False

        # Partial close percentages
        self.close_pct1 = 0.5
        self.close_pct2 = 0.3
        self.close_pct3 = 0.2

        # Risk management
        self.max_positions = max_positions

        # MT5 data downloader
        self.mt5_downloader = MT5DataDownloader(symbol=symbol, timeframe=timeframe)

        # Telegram notifier
        if telegram_token and telegram_chat_id:
            self.notifier = TelegramNotifier(telegram_token, telegram_chat_id, timezone_offset=timezone_offset)
        else:
            self.notifier = None
            print("⚠️  Telegram notifications disabled")

        # Tracking
        self.open_positions = []
        self.df = None
        self.last_signal_check = None
        self.last_position_check = None
        self.last_processed_signal_time = None  # Prevent duplicate signals
        self.closed_trades = []

        # Statistics file
        self.stats_file = f'live_bot_statistics_{symbol}.csv'

        print("✅ Improved Paper Trading Bot (MT5) initialized - ASYMMETRIC MODE")
        print(f"   Symbol: {symbol}")
        print(f"   ⏰ Signal check: every {signal_check_interval}s ({signal_check_interval/60:.0f} min)")
        print(f"   ⏰ Position check: every {position_check_interval}s ({position_check_interval/60:.0f} min)")
        print(f"\n   📈 LONG PARAMETERS:")
        print(f"   TREND: TP {self.long_trend_tp1}/{self.long_trend_tp2}/{self.long_trend_tp3}п, Trailing {self.long_trend_trailing}п, Timeout {self.long_trend_timeout}ч")
        print(f"   RANGE: TP {self.long_range_tp1}/{self.long_range_tp2}/{self.long_range_tp3}п, Trailing {self.long_range_trailing}п, Timeout {self.long_range_timeout}ч")
        print(f"\n   📉 SHORT PARAMETERS (OPTIMIZED!):")
        print(f"   TREND: TP {self.short_trend_tp1}/{self.short_trend_tp2}/{self.short_trend_tp3}п, Trailing {self.short_trend_trailing}п, Timeout {self.short_trend_timeout}ч")
        print(f"   RANGE: {'DISABLED' if not self.short_range_enabled else 'ENABLED'} (analysis: -14% PnL)")
        print(f"\n   🛡️ Max positions: {max_positions}")
        print(f"   💾 Statistics file: {self.stats_file}")

    def connect_mt5(self, login=None, password=None, server=None):
        """Connect to MT5 terminal"""
        return self.mt5_downloader.connect(login=login, password=password, server=server)

    def detect_market_regime(self, df, current_idx=None, lookback=100):
        """
        Detect market regime: TREND or RANGE

        Uses 5 signals:
        1. EMA crossover (trend indicator)
        2. ATR (volatility)
        3. Directional movement
        4. Directional bias (candles in same direction)
        5. Structural trend (higher highs / lower lows)

        Returns 'TREND' if 3+ signals active, otherwise 'RANGE'
        """
        if current_idx is None:
            current_idx = len(df) - 1

        if current_idx < lookback:
            return 'RANGE'  # Default to range

        # Get recent data
        recent_data = df.iloc[current_idx - lookback:current_idx]

        # 1. EMA CROSSOVER (main trend indicator)
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()

        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]

        # EMA difference in %
        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100

        # If EMA diverge > 0.3% = clear trend
        ema_trend = ema_diff_pct > 0.3

        # 2. ATR (volatility - should be above average)
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()

        high_volatility = atr > avg_atr * 1.05

        # 3. Directional movement (price moving in one direction)
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()

        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35

        # 4. Sequential movements (candles in same direction)
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        total_moves = up_moves + down_moves

        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.15

        # 5. Sequential higher highs / lower lows
        highs = recent_data['high'].values[-20:]
        lows = recent_data['low'].values[-20:]

        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])

        # If 60%+ candles make HH or LL = trend
        structural_trend = (higher_highs > 12) or (lower_lows > 12)

        # TREND if 3+ signals out of 5
        trend_signals = sum([
            ema_trend,
            high_volatility,
            strong_direction,
            directional_bias,
            structural_trend
        ])

        is_trend = trend_signals >= 3

        return 'TREND' if is_trend else 'RANGE'

    def download_data(self, period_hours=120):
        """Download data from MT5"""
        try:
            print(f"📥 Downloading {self.symbol} data...")
            df = self.mt5_downloader.get_realtime_data(period_hours=period_hours)

            if df is None or len(df) == 0:
                print(f"❌ Failed to download data")
                return None

            print(f"✅ Downloaded {len(df)} candles | Latest: {df.index[-1]} | Price: {df['close'].iloc[-1]:.2f}")
            return df

        except Exception as e:
            print(f"❌ Error downloading: {e}")
            return None

    def get_current_price(self):
        """Get current price from MT5 (быстро!)"""
        return self.mt5_downloader.get_current_price()

    def check_for_signals(self):
        """Check for new trading signals (ТЯЖЕЛАЯ операция - делаем редко)"""

        print(f"\n{'='*80}")
        print(f"🔍 SIGNAL CHECK at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Download latest data
        df = self.download_data()

        if df is None:
            print("❌ Failed to download data")
            return

        self.df = df

        # Run strategy
        try:
            df_strategy = self.strategy.run_strategy(df.copy())
            df_signals = df_strategy[df_strategy['signal'] != 0]

            if len(df_signals) == 0:
                print("📊 No signals found")
                return

            # Check last signal
            last_signal = df_signals.iloc[-1]
            last_signal_time = df_signals.index[-1]

            # Check if this signal was already processed (PREVENT DUPLICATES!)
            if self.last_processed_signal_time is not None:
                if last_signal_time == self.last_processed_signal_time:
                    print(f"📊 Signal at {last_signal_time} already processed, skipping duplicate")
                    return

            # CRITICAL: Only accept signals on the LAST CLOSED CANDLE
            # This prevents repainting - when old signals appear after new candles form
            latest_candle_time = df_strategy.index[-1]

            # Signal must be on the last candle (or max 1 candle behind for safety)
            candles_behind = len(df_strategy) - 1 - df_strategy.index.get_loc(last_signal_time)

            if candles_behind > 1:
                print(f"📊 Signal is {candles_behind} candles old (time: {last_signal_time})")
                print(f"   Latest candle: {latest_candle_time}")
                print(f"   ⚠️ REPAINTING DETECTED! Only signals on last closed candle are accepted.")
                print(f"   This prevents trading on signals that 'appear' on old candles.")
                return

            # Check max positions limit
            if len(self.open_positions) >= self.max_positions:
                print(f"⚠️  Max positions limit reached ({self.max_positions}), skipping signal")
                return

            # Detect market regime
            signal_idx = len(df_strategy) - 1
            regime = self.detect_market_regime(df_strategy, signal_idx)

            # FILTER: SHORT in RANGE (analysis showed -14% PnL)
            direction = 'LONG' if last_signal['signal'] == 1 else 'SHORT'
            if direction == 'SHORT' and regime == 'RANGE' and not self.short_range_enabled:
                print(f"📊 SHORT signal in RANGE regime - FILTERED")
                print(f"   Analysis: SHORT in RANGE has 46.6% WR and -14% PnL")
                print(f"   Trading SHORT only in TREND regime")
                return

            print(f"🎯 NEW SIGNAL DETECTED!")
            print(f"   Time: {last_signal_time}")
            print(f"   Direction: {direction}")
            print(f"   Entry: {last_signal['entry_price']:.2f}")
            print(f"   Regime: {regime}")

            # Open position
            self.open_position(last_signal, last_signal_time, regime)

            # Mark signal as processed (PREVENT DUPLICATES!)
            self.last_processed_signal_time = last_signal_time

        except Exception as e:
            print(f"❌ Error checking signals: {e}")
            import traceback
            traceback.print_exc()

    def open_position(self, signal, timestamp, regime):
        """Open new position with adaptive parameters based on regime and direction (ASYMMETRIC!)"""

        entry_price = signal['entry_price']
        direction = 'LONG' if signal['signal'] == 1 else 'SHORT'

        # Choose parameters based on DIRECTION and regime (ASYMMETRIC!)
        if direction == 'LONG':
            # LONG: use baseline parameters
            if regime == 'TREND':
                tp1 = self.long_trend_tp1
                tp2 = self.long_trend_tp2
                tp3 = self.long_trend_tp3
                trailing = self.long_trend_trailing
                timeout = self.long_trend_timeout
            else:  # RANGE
                tp1 = self.long_range_tp1
                tp2 = self.long_range_tp2
                tp3 = self.long_range_tp3
                trailing = self.long_range_trailing
                timeout = self.long_range_timeout
        else:  # SHORT
            # SHORT: use optimized parameters (TREND only, RANGE filtered earlier)
            # Analysis: SHORT needs smaller TP, faster trailing, shorter timeout
            tp1 = self.short_trend_tp1
            tp2 = self.short_trend_tp2
            tp3 = self.short_trend_tp3
            trailing = self.short_trend_trailing
            timeout = self.short_trend_timeout

        # Calculate TPs
        if direction == 'LONG':
            tp1_price = entry_price + tp1
            tp2_price = entry_price + tp2
            tp3_price = entry_price + tp3
        else:
            tp1_price = entry_price - tp1
            tp2_price = entry_price - tp2
            tp3_price = entry_price - tp3

        position = {
            'entry_time': timestamp,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': signal['stop_loss'],
            'regime': regime,
            'tp1_price': tp1_price,
            'tp2_price': tp2_price,
            'tp3_price': tp3_price,
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'trailing_active': False,
            'trailing_distance': trailing,
            'trailing_high': entry_price if direction == 'LONG' else 0,
            'trailing_low': entry_price if direction == 'SHORT' else 999999,
            'timeout_hours': timeout,
            'position_remaining': 1.0,
            'total_pnl_pct': 0.0,
            'pattern': signal.get('pattern', 'N/A'),
            'signal_data': signal
        }

        self.open_positions.append(position)

        print(f"✅ Position opened: {direction} @ {entry_price:.2f} [{regime}]")
        print(f"   TP1: {tp1_price:.2f} ({self.close_pct1*100:.0f}%)")
        print(f"   TP2: {tp2_price:.2f} ({self.close_pct2*100:.0f}%)")
        print(f"   TP3: {tp3_price:.2f} ({self.close_pct3*100:.0f}%)")
        print(f"   SL:  {signal['stop_loss']:.2f}")
        print(f"   Trailing: {trailing}п (after TP1)")
        print(f"   Timeout: {timeout}h")

        # Telegram notification
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
                'trailing': trailing,
                'pattern': position['pattern'],
                'timestamp': timestamp
            }
            self.notifier.send_entry_signal(signal_data)

    def check_open_positions_fast(self):
        """
        Check open positions using CURRENT PRICE only (БЫСТРО!)
        Не нужно скачивать всю историю, только текущая цена
        """

        if len(self.open_positions) == 0:
            return

        # Get current price (быстро - один тик!)
        current_price_data = self.get_current_price()

        if current_price_data is None:
            print("⚠️  Could not get current price")
            return

        current_time = current_price_data['time']
        current_bid = current_price_data['bid']
        current_ask = current_price_data['ask']

        # Use bid for LONG exits, ask for SHORT exits (realistic)
        positions_to_close = []

        for i, pos in enumerate(self.open_positions):
            if pos['position_remaining'] <= 0:
                positions_to_close.append((i, pos['entry_price'], 'CLOSED', pos['total_pnl_pct']))
                continue

            # Check timeout (use position's timeout_hours)
            time_in_trade = (current_time - pos['entry_time']).total_seconds() / 3600
            timeout_hours = pos.get('timeout_hours', 48)  # Default to 48 if not set

            if time_in_trade >= timeout_hours:
                # Force close at current price
                exit_price = current_bid if pos['direction'] == 'LONG' else current_ask

                if pos['direction'] == 'LONG':
                    pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                else:
                    pnl_pct = ((pos['entry_price'] - exit_price) / pos['entry_price']) * 100 * pos['position_remaining']

                pos['total_pnl_pct'] += pnl_pct
                positions_to_close.append((i, exit_price, 'TIMEOUT', pos['total_pnl_pct']))
                continue

            # Check SL/TP based on current price
            if pos['direction'] == 'LONG':
                # Use bid for exits
                exit_price = current_bid

                # Update trailing high
                if current_bid > pos.get('trailing_high', pos['entry_price']):
                    pos['trailing_high'] = current_bid

                # Update trailing SL if active
                if pos.get('trailing_active', False):
                    trailing_distance = pos.get('trailing_distance', 15)
                    new_sl = pos['trailing_high'] - trailing_distance
                    if new_sl > pos['stop_loss']:
                        pos['stop_loss'] = new_sl

                # Check SL
                if exit_price <= pos['stop_loss']:
                    pnl_pct = ((pos['stop_loss'] - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    exit_type = 'TRAILING_SL' if pos.get('trailing_active', False) else 'SL'
                    positions_to_close.append((i, pos['stop_loss'], exit_type, pos['total_pnl_pct']))
                    continue

                # Check TPs (обратный порядок)
                if exit_price >= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['tp3_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} ({self.close_pct3*100:.0f}%)")

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
                            'timestamp': current_time
                        })

                if exit_price >= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['tp2_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} ({self.close_pct2*100:.0f}%)")

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
                            'timestamp': current_time
                        })

                if exit_price >= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['tp1_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    # ACTIVATE TRAILING STOP after TP1
                    pos['trailing_active'] = True
                    trailing_distance = pos.get('trailing_distance', 15)
                    pos['stop_loss'] = current_bid - trailing_distance
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} ({self.close_pct1*100:.0f}%)")
                    print(f"   🔄 Trailing stop activated: {trailing_distance}п")

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
                            'trailing_activated': True,
                            'trailing_distance': trailing_distance,
                            'timestamp': current_time
                        })

            else:  # SHORT
                # Use ask for exits
                exit_price = current_ask

                # Update trailing low
                if current_ask < pos.get('trailing_low', 999999):
                    pos['trailing_low'] = current_ask

                # Update trailing SL if active
                if pos.get('trailing_active', False):
                    trailing_distance = pos.get('trailing_distance', 15)
                    new_sl = pos['trailing_low'] + trailing_distance
                    if new_sl < pos['stop_loss']:
                        pos['stop_loss'] = new_sl

                # Check SL
                if exit_price >= pos['stop_loss']:
                    pnl_pct = ((pos['entry_price'] - pos['stop_loss']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    exit_type = 'TRAILING_SL' if pos.get('trailing_active', False) else 'SL'
                    positions_to_close.append((i, pos['stop_loss'], exit_type, pos['total_pnl_pct']))
                    continue

                # Check TPs
                if exit_price <= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp3_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} ({self.close_pct3*100:.0f}%)")

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
                            'timestamp': current_time
                        })

                if exit_price <= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp2_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} ({self.close_pct2*100:.0f}%)")

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
                            'timestamp': current_time
                        })

                if exit_price <= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp1_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    # ACTIVATE TRAILING STOP after TP1
                    pos['trailing_active'] = True
                    trailing_distance = pos.get('trailing_distance', 15)
                    pos['stop_loss'] = current_ask + trailing_distance
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} ({self.close_pct1*100:.0f}%)")
                    print(f"   🔄 Trailing stop activated: {trailing_distance}п")

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
                            'trailing_activated': True,
                            'trailing_distance': trailing_distance,
                            'timestamp': current_time
                        })

        # Close positions
        for idx, exit_price, exit_type, total_pnl in reversed(positions_to_close):
            self.close_position(idx, exit_price, exit_type, current_time, total_pnl)

    def close_position(self, position_idx, exit_price, exit_type, exit_time, total_pnl_pct=None):
        """Close position"""

        pos = self.open_positions[position_idx]

        if total_pnl_pct is not None:
            pnl_pct = total_pnl_pct
        else:
            if pos['direction'] == 'LONG':
                pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
            else:
                pnl_pct = ((pos['entry_price'] - exit_price) / pos['entry_price']) * 100

        pnl_points = (pnl_pct / 100) * pos['entry_price']
        duration_hours = (exit_time - pos['entry_time']).total_seconds() / 3600

        closed_trade = {
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'direction': pos['direction'],
            'regime': pos.get('regime', 'N/A'),
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'stop_loss': pos['stop_loss'],
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
            'pattern': pos['pattern'],
            'trailing_used': pos.get('trailing_active', False)
        }

        self.closed_trades.append(closed_trade)

        emoji = "✅" if pnl_pct > 0 else "❌"
        print(f"\n{emoji} POSITION CLOSED:")
        print(f"   {pos['direction']}: {pos['entry_price']:.2f} → {exit_price:.2f} [{pos.get('regime', 'N/A')}]")
        print(f"   TPs: TP1={pos['tp1_hit']}, TP2={pos['tp2_hit']}, TP3={pos['tp3_hit']}")
        print(f"   Trailing: {pos.get('trailing_active', False)}")
        print(f"   Exit: {exit_type}")
        print(f"   PnL: {pnl_pct:+.2f}% ({pnl_points:+.2f}п)")
        print(f"   Duration: {duration_hours:.1f}h")

        # Telegram notification
        if self.notifier:
            exit_data = {
                'direction': pos['direction'],
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'pnl_points': pnl_points,
                'duration_hours': duration_hours,
                'tp1_hit': pos['tp1_hit'],
                'tp2_hit': pos['tp2_hit'],
                'tp3_hit': pos['tp3_hit'],
                'timestamp': exit_time
            }
            self.notifier.send_exit_signal(exit_data)

        self.open_positions.pop(position_idx)

        # Save statistics after closing position
        self.save_statistics()

    def save_statistics(self):
        """Save trading statistics to CSV file"""
        if len(self.closed_trades) == 0:
            return

        try:
            import pandas as pd
            import os

            # Create DataFrame from closed trades
            df_stats = pd.DataFrame(self.closed_trades)

            # Save to CSV
            df_stats.to_csv(self.stats_file, index=False)

            # Calculate summary statistics
            total_trades = len(df_stats)
            wins = len(df_stats[df_stats['pnl_pct'] > 0])
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            total_pnl = df_stats['pnl_pct'].sum()

            print(f"\n💾 Statistics saved to {self.stats_file}")
            print(f"   Trades: {total_trades} | Wins: {wins} ({win_rate:.1f}%) | Total PnL: {total_pnl:+.2f}%")

        except Exception as e:
            print(f"❌ Error saving statistics: {e}")

    def run(self):
        """Run bot with dual-frequency checking"""

        print("\n" + "="*80)
        print("🤖 IMPROVED PAPER TRADING BOT (MT5) - ASYMMETRIC MODE")
        print("="*80)
        print(f"📊 Strategy: Pattern Recognition (1.618)")
        print(f"📈 Asset: {self.symbol}")
        print(f"\n📈 LONG PARAMETERS:")
        print(f"   TREND: TP {self.long_trend_tp1}/{self.long_trend_tp2}/{self.long_trend_tp3}п, Trailing {self.long_trend_trailing}п")
        print(f"   RANGE: TP {self.long_range_tp1}/{self.long_range_tp2}/{self.long_range_tp3}п, Trailing {self.long_range_trailing}п")
        print(f"\n📉 SHORT PARAMETERS (OPTIMIZED!):")
        print(f"   TREND: TP {self.short_trend_tp1}/{self.short_trend_tp2}/{self.short_trend_tp3}п, Trailing {self.short_trend_trailing}п")
        print(f"   RANGE: DISABLED")
        print(f"")
        print(f"⏰ DUAL FREQUENCY CHECKING:")
        print(f"   🔍 New signals: every {self.signal_check_interval}s ({self.signal_check_interval/60:.0f} min)")
        print(f"   💰 Open positions: every {self.position_check_interval}s ({self.position_check_interval/60:.0f} min)")
        print(f"")
        print(f"💡 Benefits:")
        print(f"   ✅ TP/SL detected within {self.position_check_interval/60:.0f} minutes (not {self.signal_check_interval/60:.0f}!)")
        print(f"   ✅ Less load on MT5 (full data only every {self.signal_check_interval/60:.0f} min)")
        print(f"   ✅ Faster reactions to price movements")
        print(f"   🛡️ Max positions: {self.max_positions}")
        print("="*80)

        # Test Telegram
        if self.notifier:
            if self.notifier.test_connection():
                self.notifier.send_startup_message()

        # Initialize timing
        last_signal_check = datetime.now() - timedelta(seconds=self.signal_check_interval)
        last_position_check = datetime.now()

        try:
            iteration = 0
            while True:
                iteration += 1
                current_time = datetime.now()

                # Check if it's time for signal check
                time_since_signal_check = (current_time - last_signal_check).total_seconds()

                if time_since_signal_check >= self.signal_check_interval:
                    self.check_for_signals()
                    last_signal_check = current_time

                # Check if it's time for position check
                time_since_position_check = (current_time - last_position_check).total_seconds()

                if time_since_position_check >= self.position_check_interval:
                    if len(self.open_positions) > 0:
                        print(f"\n{'='*60}")
                        print(f"💰 POSITION CHECK #{iteration} at {current_time.strftime('%H:%M:%S')}")
                        print(f"{'='*60}")
                        self.check_open_positions_fast()
                    last_position_check = current_time

                # Display status (каждые N итераций)
                if iteration % 5 == 0:
                    print(f"\n📊 Status ({current_time.strftime('%H:%M:%S')}):")
                    print(f"   Open: {len(self.open_positions)} | Closed: {len(self.closed_trades)}")

                    if len(self.closed_trades) > 0:
                        total_pnl = sum([t['pnl_pct'] for t in self.closed_trades])
                        print(f"   Total PnL: {total_pnl:+.2f}%")

                    # Show current price
                    price = self.get_current_price()
                    if price:
                        print(f"   Price: Bid {price['bid']:.2f} | Ask {price['ask']:.2f}")

                    # Next checks
                    next_signal = last_signal_check + timedelta(seconds=self.signal_check_interval)
                    next_position = last_position_check + timedelta(seconds=self.position_check_interval)

                    print(f"\n⏳ Next signal check: {next_signal.strftime('%H:%M:%S')} ({(next_signal - current_time).total_seconds()/60:.0f} min)")
                    print(f"⏳ Next position check: {next_position.strftime('%H:%M:%S')} ({(next_position - current_time).total_seconds()/60:.0f} min)")

                # Sleep for a short time (используем меньший из двух интервалов)
                sleep_time = min(self.position_check_interval, 60)  # Max 1 min sleep
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n\n⚠️  Bot stopped by user")
            print(f"📊 Stats: {len(self.closed_trades)} trades, {len(self.open_positions)} open")
            self.mt5_downloader.disconnect()


def main():
    """Main entry point"""

    load_dotenv()

    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    # Get intervals from env or use defaults
    signal_interval = int(os.getenv('SIGNAL_CHECK_INTERVAL', 3600))      # 1 hour
    position_interval = int(os.getenv('POSITION_CHECK_INTERVAL', 300))   # 5 min

    symbol = os.getenv('MT5_SYMBOL', 'XAUUSD')

    # Initialize bot
    bot = ImprovedPaperTradingBot(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        signal_check_interval=signal_interval,
        position_check_interval=position_interval,
        symbol=symbol,
        timeframe=mt5.TIMEFRAME_H1
    )

    # Connect MT5
    if not bot.connect_mt5():
        print("\n❌ MT5 connection failed")
        return

    # Run
    bot.run()


if __name__ == "__main__":
    main()
