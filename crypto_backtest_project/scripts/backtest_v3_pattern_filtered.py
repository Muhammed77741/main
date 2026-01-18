"""
SHORT Optimized + Pattern Filtering

УЛУЧШЕНИЯ над SHORT Optimized:
1. Асимметричные параметры для SHORT (из SHORT Optimized)
2. SHORT только в TREND (из SHORT Optimized)
3. НОВОЕ: Фильтрация плохих паттернов
   - SKIP: Descending Triangle (-0.95% PnL)
   - SKIP: Rising Wedge (-0.02% PnL)

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
- Win Rate: 77.3% → 78-79%
- Total PnL: +325.70% → +330-340%
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from pattern_recognition_strategy import PatternRecognitionStrategy


class PatternFilteredBacktestV3:
    """SHORT Optimized + Pattern Filtering"""

    def __init__(self, spread_points=2.0, commission_points=0.5, swap_per_day=-0.3):
        self.spread = spread_points
        self.commission = commission_points
        self.swap_per_day = swap_per_day

        # LONG parameters (unchanged from baseline)
        self.long_trend_tp1 = 30
        self.long_trend_tp2 = 55
        self.long_trend_tp3 = 90
        self.long_trend_trailing = 18
        self.long_trend_timeout = 60

        self.long_range_tp1 = 20
        self.long_range_tp2 = 35
        self.long_range_tp3 = 50
        self.long_range_trailing = 15
        self.long_range_timeout = 48

        # SHORT parameters (OPTIMIZED!)
        self.short_trend_tp1 = 15
        self.short_trend_tp2 = 25
        self.short_trend_tp3 = 35
        self.short_trend_trailing = 10
        self.short_trend_timeout = 24

        # SHORT RANGE - DISABLED
        self.short_range_enabled = False

        # Pattern filtering
        self.enable_pattern_filtering = True
        self.bad_patterns = ['desc_triangle', 'rising_wedge']  # Filter these out

        # Daily limits
        self.max_trades_per_day = 10
        self.max_positions = 5

    def detect_market_regime(self, df, current_idx, lookback=100):
        """Detect market regime: TREND or RANGE (same as SHORT Optimized)"""
        if current_idx < lookback:
            return 'RANGE'

        recent_data = df.iloc[current_idx - lookback:current_idx]

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
        total_moves = up_moves + down_moves

        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.15

        # 5. Structural trend
        highs = recent_data['high'].values[-20:]
        lows = recent_data['low'].values[-20:]

        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])

        structural_trend = (higher_highs > 12) or (lower_lows > 12)

        # Count trend signals
        trend_signals = sum([
            ema_trend,
            high_volatility,
            strong_direction,
            directional_bias,
            structural_trend
        ])

        is_trend = trend_signals >= 3

        return 'TREND' if is_trend else 'RANGE'

    def detect_pattern(self, df, idx):
        """
        Detect chart pattern at current signal
        Returns pattern type or None

        Patterns detected:
        - asc_triangle: Ascending Triangle (flat resistance + rising support) - GOOD
        - desc_triangle: Descending Triangle (flat support + falling resistance) - BAD
        - falling_wedge: Falling Wedge (both falling, converging) - GOOD
        - rising_wedge: Rising Wedge (both rising, converging) - BAD
        - sym_triangle: Symmetrical Triangle (converging) - NEUTRAL
        """
        if idx < 40:  # Need enough data
            return None

        # Get recent data
        swing_lookback = 20
        recent_data = df.iloc[max(0, idx-swing_lookback):idx]

        if len(recent_data) < 10:
            return None

        # Find swing highs and lows
        swing_highs = []
        swing_lows = []

        for i in range(5, len(recent_data)-5):
            window_highs = recent_data['high'].iloc[i-5:i+6]
            if recent_data['high'].iloc[i] == window_highs.max():
                swing_highs.append({
                    'idx': i,
                    'high': recent_data['high'].iloc[i]
                })

            window_lows = recent_data['low'].iloc[i-5:i+6]
            if recent_data['low'].iloc[i] == window_lows.min():
                swing_lows.append({
                    'idx': i,
                    'low': recent_data['low'].iloc[i]
                })

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None

        # Get last 2 swings
        high1 = swing_highs[-2]['high']
        high2 = swing_highs[-1]['high']
        low1 = swing_lows[-2]['low']
        low2 = swing_lows[-1]['low']

        tolerance = high1 * 0.02  # 2% tolerance

        # Current direction
        current_close = df['close'].iloc[idx]

        # Detect Ascending Triangle (flat resistance + rising support) - GOOD for LONG
        if abs(high1 - high2) <= tolerance and low2 > low1:
            if current_close > max(high1, high2):
                return 'asc_triangle'

        # Detect Descending Triangle (flat support + falling resistance) - BAD for SHORT
        if abs(low1 - low2) <= tolerance and high2 < high1:
            if current_close < min(low1, low2):
                return 'desc_triangle'

        # Detect Falling Wedge (both falling but converging) - GOOD for LONG
        if high2 < high1 and low2 < low1:
            high_slope = (high1 - high2) / high1
            low_slope = (low1 - low2) / low1
            if high_slope > low_slope:  # Converging
                if current_close > high2:
                    return 'falling_wedge'

        # Detect Rising Wedge (both rising but converging) - BAD for SHORT
        if high2 > high1 and low2 > low1:
            high_slope = (high2 - high1) / high1
            low_slope = (low2 - low1) / low1
            if low_slope > high_slope:  # Converging
                if current_close < low2:
                    return 'rising_wedge'

        # Detect Symmetrical Triangle (converging) - NEUTRAL
        if high2 < high1 and low2 > low1:
            if current_close > high2:
                return 'sym_triangle'

        return None

    def should_filter_pattern(self, pattern, direction):
        """
        Check if pattern should be filtered
        Returns: (should_filter, reason)
        """
        if not self.enable_pattern_filtering or pattern is None:
            return False, None

        # Filter bad patterns
        if pattern in self.bad_patterns:
            if pattern == 'desc_triangle':
                return True, "Descending Triangle: 70.4% WR, -0.95% PnL"
            elif pattern == 'rising_wedge':
                return True, "Rising Wedge: 61.5% WR, -0.02% PnL"

        return False, None

    def backtest(self, df, strategy, close_pct1=0.5, close_pct2=0.3, close_pct3=0.2):
        """Run pattern-filtered backtest"""

        print(f"\n{'='*80}")
        print(f"🎯 PATTERN-FILTERED BACKTEST V3")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")

        print(f"\n   🎯 LONG PARAMETERS:")
        print(f"   TREND: TP {self.long_trend_tp1}/{self.long_trend_tp2}/{self.long_trend_tp3}п, Trail {self.long_trend_trailing}п, TO {self.long_trend_timeout}ч")
        print(f"   RANGE: TP {self.long_range_tp1}/{self.long_range_tp2}/{self.long_range_tp3}п, Trail {self.long_range_trailing}п, TO {self.long_range_timeout}ч")

        print(f"\n   📉 SHORT PARAMETERS:")
        print(f"   TREND: TP {self.short_trend_tp1}/{self.short_trend_tp2}/{self.short_trend_tp3}п, Trail {self.short_trend_trailing}п, TO {self.short_trend_timeout}ч")
        print(f"   RANGE: {'DISABLED' if not self.short_range_enabled else 'ENABLED'}")

        print(f"\n   🎨 PATTERN FILTERING:")
        print(f"   Enabled: {self.enable_pattern_filtering}")
        if self.enable_pattern_filtering:
            print(f"   Bad patterns (SKIP): {', '.join(self.bad_patterns)}")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())

        # Track trades and positions
        trades = []
        open_positions = []

        # Track stats
        trend_signals = 0
        range_signals = 0
        short_filtered_range = 0
        pattern_filtered = 0
        patterns_detected = {}

        # Process chronologically
        for i in range(len(df_strategy)):
            candle = df_strategy.iloc[i]
            candle_time = df_strategy.index[i]
            high = candle['high']
            low = candle['low']
            close = candle['close']
            signal = candle.get('signal', 0)

            # Check for new signal
            if signal != 0:
                # Detect market regime
                regime = self.detect_market_regime(df_strategy, i)

                # FILTER 1: SHORT IN RANGE
                if signal == -1 and regime == 'RANGE' and not self.short_range_enabled:
                    short_filtered_range += 1
                    continue

                # FILTER 2: PATTERN FILTERING (NEW!)
                pattern = self.detect_pattern(df_strategy, i)
                should_filter, filter_reason = self.should_filter_pattern(pattern, 'LONG' if signal == 1 else 'SHORT')

                if should_filter:
                    pattern_filtered += 1
                    continue

                # Track pattern stats
                pattern_key = pattern if pattern else 'none'
                patterns_detected[pattern_key] = patterns_detected.get(pattern_key, 0) + 1

                # Choose parameters based on direction and regime
                direction = 'LONG' if signal == 1 else 'SHORT'

                if direction == 'LONG':
                    if regime == 'TREND':
                        tp1, tp2, tp3 = self.long_trend_tp1, self.long_trend_tp2, self.long_trend_tp3
                        trailing = self.long_trend_trailing
                        timeout = self.long_trend_timeout
                        trend_signals += 1
                    else:  # RANGE
                        tp1, tp2, tp3 = self.long_range_tp1, self.long_range_tp2, self.long_range_tp3
                        trailing = self.long_range_trailing
                        timeout = self.long_range_timeout
                        range_signals += 1
                else:  # SHORT
                    tp1, tp2, tp3 = self.short_trend_tp1, self.short_trend_tp2, self.short_trend_tp3
                    trailing = self.short_trend_trailing
                    timeout = self.short_trend_timeout
                    trend_signals += 1

                # Check max positions limit
                if len(open_positions) >= self.max_positions:
                    continue

                # Open position
                signal_sl = candle.get('stop_loss', close)

                if direction == 'LONG':
                    entry_price = close + self.spread / 2
                    sl_distance = close - signal_sl
                    sl_price = entry_price - sl_distance
                    tp1_price = entry_price + tp1
                    tp2_price = entry_price + tp2
                    tp3_price = entry_price + tp3
                else:
                    entry_price = close - self.spread / 2
                    sl_distance = signal_sl - close
                    sl_price = entry_price + sl_distance
                    tp1_price = entry_price - tp1
                    tp2_price = entry_price - tp2
                    tp3_price = entry_price - tp3

                new_pos = {
                    'entry_time': candle_time,
                    'entry_price': entry_price,
                    'direction': direction,
                    'regime': regime,
                    'pattern': pattern_key,  # Store pattern
                    'sl_price': sl_price,
                    'tp1_price': tp1_price,
                    'tp2_price': tp2_price,
                    'tp3_price': tp3_price,
                    'tp1_hit': False,
                    'tp2_hit': False,
                    'tp3_hit': False,
                    'trailing_active': False,
                    'trailing_distance': trailing,
                    'timeout_hours': timeout,
                    'trailing_high': entry_price if direction == 'LONG' else 0,
                    'trailing_low': entry_price if direction == 'SHORT' else 999999,
                    'position_remaining': 1.0,
                    'total_pnl_pct': 0.0,
                }

                open_positions.append(new_pos)

            # Update all open positions (same logic as SHORT Optimized)
            positions_to_close = []

            for pos_idx, pos in enumerate(open_positions):
                entry_time = pos['entry_time']
                entry_price = pos['entry_price']
                direction = pos['direction']
                trailing_distance = pos['trailing_distance']
                timeout_hours = pos['timeout_hours']

                if entry_time == candle_time:
                    continue

                # Check timeout
                hours_in_trade = (candle_time - entry_time).total_seconds() / 3600

                if hours_in_trade >= timeout_hours:
                    if direction == 'LONG':
                        exit_price = close - self.spread / 2
                    else:
                        exit_price = close + self.spread / 2

                    pnl_points = self._calculate_pnl_points(
                        entry_price, exit_price, direction,
                        pos['position_remaining'], hours_in_trade
                    )

                    pos['total_pnl_pct'] += (pnl_points / entry_price) * 100

                    trade = self._create_trade_record(pos, exit_price, 'TIMEOUT', candle_time)
                    trades.append(trade)
                    positions_to_close.append(pos_idx)
                    continue

                # Check SL/TP for LONG
                if direction == 'LONG':
                    if high > pos['trailing_high']:
                        pos['trailing_high'] = high

                    if pos['trailing_active']:
                        new_sl = pos['trailing_high'] - trailing_distance
                        if new_sl > pos['sl_price']:
                            pos['sl_price'] = new_sl

                    if low <= pos['sl_price']:
                        exit_price = pos['sl_price']
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            pos['position_remaining'], hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._create_trade_record(pos, exit_price, exit_type, candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                    # TP checks
                    if high >= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct1, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = high - trailing_distance

                    if high >= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct2, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    if high >= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct3, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct3
                        pos['tp3_hit'] = True

                    if pos['position_remaining'] <= 0.01:
                        trade = self._create_trade_record(pos, pos['tp3_price'], 'TP3', candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)

                else:  # SHORT
                    if low < pos['trailing_low']:
                        pos['trailing_low'] = low

                    if pos['trailing_active']:
                        new_sl = pos['trailing_low'] + trailing_distance
                        if new_sl < pos['sl_price']:
                            pos['sl_price'] = new_sl

                    if high >= pos['sl_price']:
                        exit_price = pos['sl_price']
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            pos['position_remaining'], hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._create_trade_record(pos, exit_price, exit_type, candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                    if low <= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct1, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = low + trailing_distance

                    if low <= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct2, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    if low <= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct3, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct3
                        pos['tp3_hit'] = True

                    if pos['position_remaining'] <= 0.01:
                        trade = self._create_trade_record(pos, pos['tp3_price'], 'TP3', candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)

            # Remove closed
            for idx in sorted(positions_to_close, reverse=True):
                del open_positions[idx]

        if len(trades) == 0:
            print("❌ No completed trades")
            return None

        trades_df = pd.DataFrame(trades)

        # Print filter statistics
        print(f"\n{'='*80}")
        print(f"📊 FILTER STATISTICS")
        print(f"{'='*80}")
        print(f"   SHORT in RANGE filtered: {short_filtered_range}")
        print(f"   PATTERN filtered: {pattern_filtered}")
        print(f"   Total signals: {trend_signals + range_signals + short_filtered_range + pattern_filtered}")
        print(f"   Trades executed: {len(trades)}")

        # Print pattern distribution
        print(f"\n📊 PATTERN DISTRIBUTION:")
        for pattern, count in sorted(patterns_detected.items(), key=lambda x: x[1], reverse=True):
            print(f"   {pattern}: {count} signals")

        # Print results by pattern
        print(f"\n{'='*80}")
        print(f"📊 RESULTS BY PATTERN")
        print(f"{'='*80}")

        for pattern in trades_df['pattern'].unique():
            pattern_trades = trades_df[trades_df['pattern'] == pattern]
            if len(pattern_trades) > 0:
                wins = len(pattern_trades[pattern_trades['pnl_pct'] > 0])
                win_rate = wins / len(pattern_trades) * 100
                total_pnl = pattern_trades['pnl_pct'].sum()

                print(f"\n   {pattern}:")
                print(f"   Trades: {len(pattern_trades)}")
                print(f"   Win Rate: {win_rate:.1f}%")
                print(f"   Total PnL: {total_pnl:+.2f}%")

        # Print results by direction
        print(f"\n{'='*80}")
        print(f"📊 RESULTS BY DIRECTION")
        print(f"{'='*80}")

        for direction in ['LONG', 'SHORT']:
            dir_trades = trades_df[trades_df['direction'] == direction]
            if len(dir_trades) > 0:
                wins = len(dir_trades[dir_trades['pnl_pct'] > 0])
                win_rate = wins / len(dir_trades) * 100
                total_pnl = dir_trades['pnl_pct'].sum()

                print(f"\n   {direction}:")
                print(f"   Trades: {len(dir_trades)}")
                print(f"   Win Rate: {win_rate:.1f}%")
                print(f"   Total PnL: {total_pnl:+.2f}%")

        # Calculate statistics
        self._print_results(trades_df)

        return trades_df

    def _calculate_pnl_points(self, entry, exit, direction, position_size, hours):
        """Calculate PnL in points"""
        if direction == 'LONG':
            price_pnl = exit - entry
        else:
            price_pnl = entry - exit

        price_pnl *= position_size
        price_pnl -= self.commission * position_size

        if hours > 24:
            days = hours / 24
            price_pnl += self.swap_per_day * days * position_size

        return price_pnl

    def _create_trade_record(self, pos, exit_price, exit_type, exit_time):
        """Create trade record"""
        duration_hours = (exit_time - pos['entry_time']).total_seconds() / 3600
        pnl_pct = pos['total_pnl_pct']
        pnl_points = (pnl_pct / 100) * pos['entry_price']

        return {
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'direction': pos['direction'],
            'regime': pos['regime'],
            'pattern': pos['pattern'],  # Include pattern
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'tp1_hit': pos['tp1_hit'],
            'tp2_hit': pos['tp2_hit'],
            'tp3_hit': pos['tp3_hit'],
            'trailing_used': pos['trailing_active'],
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
        }

    def _print_results(self, trades_df):
        """Print results"""
        print(f"\n{'='*80}")
        print(f"📊 OVERALL RESULTS")
        print(f"{'='*80}")

        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = trades_df['pnl_pct'].sum()
        total_points = trades_df['pnl_points'].sum()

        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if total_trades - wins > 0 else 0

        print(f"\n📈 Performance:")
        print(f"   Total trades: {total_trades}")
        print(f"   Wins: {wins} ({win_rate:.1f}%)")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Total Points: {total_points:+.1f}п")
        print(f"   Avg Win: {avg_win:+.2f}%")
        print(f"   Avg Loss: {avg_loss:+.2f}%")

        if avg_loss != 0:
            profit_factor = abs(avg_win * wins / (avg_loss * (total_trades - wins)))
            print(f"   Profit Factor: {profit_factor:.2f}")

        # Drawdown
        cumulative_pnl = trades_df['pnl_pct'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - running_max
        max_drawdown = drawdown.min()

        print(f"\n📉 Risk Metrics:")
        print(f"   Max Drawdown: {max_drawdown:.2f}%")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Pattern-Filtered Backtest V3')
    parser.add_argument('--file', type=str, required=True, help='CSV file')
    args = parser.parse_args()

    # Load data
    print(f"\n📂 Loading data from {args.file}...")
    df = pd.read_csv(args.file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')

    if 'is_active' not in df.columns:
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_active'] = df['is_london'] | df['is_ny']

    # Create strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Run pattern-filtered backtest
    backtest = PatternFilteredBacktestV3()
    trades_df = backtest.backtest(df, strategy)

    if trades_df is not None:
        trades_df.to_csv('backtest_v3_pattern_filtered_results.csv', index=False)
        print(f"\n💾 Results saved to backtest_v3_pattern_filtered_results.csv")


if __name__ == "__main__":
    main()
