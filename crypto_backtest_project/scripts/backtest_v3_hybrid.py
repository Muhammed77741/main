"""
HYBRID Strategy: SHORT Optimized + Pattern Filtering
Combines best of both worlds:
1. SMC signals + asymmetric SHORT parameters from SHORT Optimized
2. Pattern detection and filtering from Patterns Only

IMPROVEMENTS:
- Filter OUT bad patterns (Descending Triangle, Rising Wedge)
- Boost TP for excellent patterns (Ascending Triangle, Falling Wedge)
- Keep all SHORT optimizations (TREND only, reduced TP, faster trailing)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from pattern_recognition_strategy import PatternRecognitionStrategy


class HybridBacktestV3:
    """Hybrid: SHORT Optimized base + Pattern filtering"""

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

        # Pattern boost settings
        self.pattern_boost = 1.20  # 20% TP increase for excellent patterns

        # Pattern filter: BAD patterns to skip
        # Descending Triangle: 70.4% WR, -0.95% PnL
        # Rising Wedge: 61.5% WR, -0.02% PnL
        self.bad_patterns = ['desc_triangle', 'rising_wedge']

        # Pattern boost: EXCELLENT patterns to boost
        # Ascending Triangle: 81.2% WR, +44.70% PnL
        # Falling Wedge: 100% WR, +8.14% PnL
        self.excellent_patterns = ['asc_triangle', 'falling_wedge']

        # Daily limits
        self.max_trades_per_day = 10
        self.max_positions = 5

        print("\n" + "="*80)
        print("🎯 HYBRID STRATEGY: SHORT OPTIMIZED + PATTERN FILTERING")
        print("="*80)
        print("\n📊 ASYMMETRIC PARAMETERS:")
        print(f"   LONG TREND:  TP {self.long_trend_tp1}/{self.long_trend_tp2}/{self.long_trend_tp3}п, Trail {self.long_trend_trailing}п, TO {self.long_trend_timeout}ч")
        print(f"   LONG RANGE:  TP {self.long_range_tp1}/{self.long_range_tp2}/{self.long_range_tp3}п, Trail {self.long_range_trailing}п, TO {self.long_range_timeout}ч")
        print(f"   SHORT TREND: TP {self.short_trend_tp1}/{self.short_trend_tp2}/{self.short_trend_tp3}п, Trail {self.short_trend_trailing}п, TO {self.short_trend_timeout}ч")
        print(f"   SHORT RANGE: DISABLED ❌")

        print("\n🎨 PATTERN FILTERING:")
        print(f"   ❌ BAD patterns (skip):     {', '.join(self.bad_patterns)}")
        print(f"   ✅ EXCELLENT patterns (boost {self.pattern_boost}x): {', '.join(self.excellent_patterns)}")

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

        trend_score = sum([ema_trend, high_volatility, strong_direction, directional_bias, structural_trend])

        if trend_score >= 3:
            return 'TREND'
        else:
            return 'RANGE'

    def detect_pattern(self, df, idx):
        """
        Detect chart pattern at current signal
        Returns pattern type or None
        """
        if idx < 40:  # Need enough data for pattern detection
            return None

        # Get recent swing points
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

        # Detect Ascending Triangle (flat resistance + rising support)
        if abs(high1 - high2) <= tolerance and low2 > low1:
            if df['close'].iloc[idx] > max(high1, high2):
                return 'asc_triangle'

        # Detect Descending Triangle (flat support + falling resistance)
        if abs(low1 - low2) <= tolerance and high2 < high1:
            if df['close'].iloc[idx] < min(low1, low2):
                return 'desc_triangle'

        # Detect Falling Wedge (both falling but converging - bullish)
        if high2 < high1 and low2 < low1:
            high_slope = (high1 - high2) / high1
            low_slope = (low1 - low2) / low1
            if high_slope > low_slope:  # Converging
                if df['close'].iloc[idx] > high2:
                    return 'falling_wedge'

        # Detect Rising Wedge (both rising but converging - bearish)
        if high2 > high1 and low2 > low1:
            high_slope = (high2 - high1) / high1
            low_slope = (low2 - low1) / low1
            if low_slope > high_slope:  # Converging
                if df['close'].iloc[idx] < low2:
                    return 'rising_wedge'

        # Detect Symmetrical Triangle (converging)
        if high2 < high1 and low2 > low1:
            if df['close'].iloc[idx] > high2:
                return 'sym_triangle'

        return None

    def should_filter_pattern(self, pattern, direction):
        """
        Check if pattern should be filtered out
        Returns: (should_filter, reason)
        """
        if pattern is None:
            return False, None

        # Filter bad patterns
        if pattern in self.bad_patterns:
            if pattern == 'desc_triangle':
                return True, "Descending Triangle: 70.4% WR, -0.95% PnL"
            elif pattern == 'rising_wedge':
                return True, "Rising Wedge: 61.5% WR, -0.02% PnL"

        return False, None

    def get_pattern_boost(self, pattern):
        """
        Get TP boost multiplier for excellent patterns
        Returns: boost multiplier (1.0 = no boost, 1.2 = 20% boost)
        """
        if pattern is None:
            return 1.0

        if pattern in self.excellent_patterns:
            return self.pattern_boost

        return 1.0

    def run_backtest(self, df: pd.DataFrame) -> tuple:
        """Run hybrid backtest with pattern filtering"""

        # Run SMC strategy to get signals
        strategy = PatternRecognitionStrategy()
        df = strategy.run_strategy(df)

        results = []
        open_positions = []

        total_signals = 0
        filtered_signals = 0
        boosted_signals = 0

        for idx in range(len(df)):
            current_time = df['timestamp'].iloc[idx]
            current_row = df.iloc[idx]

            # Update open positions
            open_positions, closed_trades = self.update_positions(
                open_positions, current_row, current_time
            )
            results.extend(closed_trades)

            # Check for new signal
            if current_row['signal'] != 0 and len(open_positions) < self.max_positions:
                total_signals += 1

                direction = 'LONG' if current_row['signal'] == 1 else 'SHORT'
                regime = self.detect_market_regime(df, idx)

                # FILTER: SHORT in RANGE
                if direction == 'SHORT' and regime == 'RANGE' and not self.short_range_enabled:
                    filtered_signals += 1
                    continue

                # PATTERN DETECTION
                pattern = self.detect_pattern(df, idx)

                # PATTERN FILTERING
                should_filter, filter_reason = self.should_filter_pattern(pattern, direction)
                if should_filter:
                    filtered_signals += 1
                    continue

                # PATTERN BOOST
                boost = self.get_pattern_boost(pattern)
                if boost > 1.0:
                    boosted_signals += 1

                # Open position with pattern info
                position = self.open_position(
                    current_row, current_time, regime, direction, pattern, boost
                )
                open_positions.append(position)

        # Close remaining positions
        for pos in open_positions:
            trade = self.close_position(pos, df.iloc[-1], df['timestamp'].iloc[-1], 'END')
            results.append(trade)

        print(f"\n📊 PATTERN FILTERING STATISTICS:")
        print(f"   Total SMC signals: {total_signals}")
        print(f"   Filtered out (bad patterns + SHORT RANGE): {filtered_signals}")
        print(f"   Boosted (excellent patterns): {boosted_signals}")
        print(f"   Trades executed: {len(results)}")

        return pd.DataFrame(results), df

    def open_position(self, signal, timestamp, regime, direction, pattern, boost):
        """Open new position with pattern-aware parameters"""

        entry_price = signal['close']

        # Choose base parameters (ASYMMETRIC!)
        if direction == 'LONG':
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
        else:  # SHORT (TREND only)
            tp1 = self.short_trend_tp1
            tp2 = self.short_trend_tp2
            tp3 = self.short_trend_tp3
            trailing = self.short_trend_trailing
            timeout = self.short_trend_timeout

        # Apply pattern boost
        if boost > 1.0:
            tp1 = int(tp1 * boost)
            tp2 = int(tp2 * boost)
            tp3 = int(tp3 * boost)

        # Calculate levels
        pip_value = 0.1

        if direction == 'LONG':
            tp1_price = entry_price + (tp1 * pip_value)
            tp2_price = entry_price + (tp2 * pip_value)
            tp3_price = entry_price + (tp3 * pip_value)
            sl_price = entry_price - (40 * pip_value)
        else:  # SHORT
            tp1_price = entry_price - (tp1 * pip_value)
            tp2_price = entry_price - (tp2 * pip_value)
            tp3_price = entry_price - (tp3 * pip_value)
            sl_price = entry_price + (40 * pip_value)

        return {
            'entry_time': timestamp,
            'entry_price': entry_price,
            'direction': direction,
            'regime': regime,
            'pattern': pattern if pattern else 'none',
            'boosted': boost > 1.0,
            'tp1_price': tp1_price,
            'tp2_price': tp2_price,
            'tp3_price': tp3_price,
            'sl_price': sl_price,
            'current_sl': sl_price,
            'trailing_distance': trailing * pip_value,
            'timeout_hours': timeout,
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'remaining_position': 1.0,
            'closed_pnl': 0.0,
            'trailing_active': False
        }

    def update_positions(self, positions, current_row, current_time):
        """Update all open positions"""
        still_open = []
        closed_trades = []

        for pos in positions:
            current_price = current_row['close']
            high = current_row['high']
            low = current_row['low']

            # Check timeout
            hours_open = (current_time - pos['entry_time']).total_seconds() / 3600
            if hours_open >= pos['timeout_hours']:
                trade = self.close_position(pos, current_row, current_time, 'TIMEOUT')
                closed_trades.append(trade)
                continue

            # Check SL
            if pos['direction'] == 'LONG':
                if low <= pos['current_sl']:
                    trade = self.close_position(pos, current_row, current_time, 'SL')
                    closed_trades.append(trade)
                    continue
            else:  # SHORT
                if high >= pos['current_sl']:
                    trade = self.close_position(pos, current_row, current_time, 'SL')
                    closed_trades.append(trade)
                    continue

            # Check TPs
            if pos['direction'] == 'LONG':
                # TP3
                if not pos['tp3_hit'] and high >= pos['tp3_price']:
                    pos['tp3_hit'] = True
                    pos['closed_pnl'] += self.calculate_pnl(
                        pos['entry_price'], pos['tp3_price'], pos['direction'], pos['remaining_position']
                    )
                    trade = self.close_position(pos, current_row, current_time, 'TP3')
                    closed_trades.append(trade)
                    continue

                # TP2
                elif not pos['tp2_hit'] and high >= pos['tp2_price']:
                    pos['tp2_hit'] = True
                    pos['closed_pnl'] += self.calculate_pnl(
                        pos['entry_price'], pos['tp2_price'], pos['direction'], 0.3
                    )
                    pos['remaining_position'] -= 0.3

                    # Update trailing
                    new_sl = pos['tp2_price'] - pos['trailing_distance']
                    pos['current_sl'] = max(pos['current_sl'], new_sl)
                    pos['trailing_active'] = True

                # TP1
                elif not pos['tp1_hit'] and high >= pos['tp1_price']:
                    pos['tp1_hit'] = True
                    pos['closed_pnl'] += self.calculate_pnl(
                        pos['entry_price'], pos['tp1_price'], pos['direction'], 0.5
                    )
                    pos['remaining_position'] -= 0.5

                    # Activate trailing
                    pos['current_sl'] = pos['entry_price']
                    pos['trailing_active'] = True

                # Update trailing
                if pos['trailing_active']:
                    new_sl = current_price - pos['trailing_distance']
                    pos['current_sl'] = max(pos['current_sl'], new_sl)

            else:  # SHORT
                # TP3
                if not pos['tp3_hit'] and low <= pos['tp3_price']:
                    pos['tp3_hit'] = True
                    pos['closed_pnl'] += self.calculate_pnl(
                        pos['entry_price'], pos['tp3_price'], pos['direction'], pos['remaining_position']
                    )
                    trade = self.close_position(pos, current_row, current_time, 'TP3')
                    closed_trades.append(trade)
                    continue

                # TP2
                elif not pos['tp2_hit'] and low <= pos['tp2_price']:
                    pos['tp2_hit'] = True
                    pos['closed_pnl'] += self.calculate_pnl(
                        pos['entry_price'], pos['tp2_price'], pos['direction'], 0.3
                    )
                    pos['remaining_position'] -= 0.3

                    # Update trailing
                    new_sl = pos['tp2_price'] + pos['trailing_distance']
                    pos['current_sl'] = min(pos['current_sl'], new_sl)
                    pos['trailing_active'] = True

                # TP1
                elif not pos['tp1_hit'] and low <= pos['tp1_price']:
                    pos['tp1_hit'] = True
                    pos['closed_pnl'] += self.calculate_pnl(
                        pos['entry_price'], pos['tp1_price'], pos['direction'], 0.5
                    )
                    pos['remaining_position'] -= 0.5

                    # Activate trailing
                    pos['current_sl'] = pos['entry_price']
                    pos['trailing_active'] = True

                # Update trailing
                if pos['trailing_active']:
                    new_sl = current_price + pos['trailing_distance']
                    pos['current_sl'] = min(pos['current_sl'], new_sl)

            still_open.append(pos)

        return still_open, closed_trades

    def close_position(self, pos, current_row, current_time, exit_type):
        """Close position and calculate final PnL"""

        if pos['remaining_position'] > 0:
            exit_price = current_row['close']
            final_pnl = pos['closed_pnl'] + self.calculate_pnl(
                pos['entry_price'], exit_price, pos['direction'], pos['remaining_position']
            )
        else:
            final_pnl = pos['closed_pnl']

        # Calculate costs
        entry_cost = (self.spread + self.commission) * 0.1
        hours_held = (current_time - pos['entry_time']).total_seconds() / 3600
        days_held = hours_held / 24
        swap_cost = self.swap_per_day * days_held

        total_cost = entry_cost + swap_cost
        net_pnl = final_pnl - total_cost

        return {
            'entry_time': pos['entry_time'],
            'exit_time': current_time,
            'direction': pos['direction'],
            'regime': pos['regime'],
            'pattern': pos['pattern'],
            'boosted': pos['boosted'],
            'entry_price': pos['entry_price'],
            'exit_price': current_row['close'],
            'pnl_pct': net_pnl,
            'exit_type': exit_type,
            'tp1_hit': pos['tp1_hit'],
            'tp2_hit': pos['tp2_hit'],
            'tp3_hit': pos['tp3_hit'],
            'trailing_used': pos['trailing_active'],
            'duration_hours': hours_held
        }

    def calculate_pnl(self, entry_price, exit_price, direction, position_size):
        """Calculate PnL percentage"""
        if direction == 'LONG':
            pnl = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl = ((entry_price - exit_price) / entry_price) * 100

        return pnl * position_size


def print_results(results_df):
    """Print detailed backtest results"""

    print("\n" + "="*80)
    print("📊 HYBRID BACKTEST RESULTS")
    print("="*80)

    total_trades = len(results_df)
    winning_trades = len(results_df[results_df['pnl_pct'] > 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    total_pnl = results_df['pnl_pct'].sum()
    avg_win = results_df[results_df['pnl_pct'] > 0]['pnl_pct'].mean()
    avg_loss = results_df[results_df['pnl_pct'] <= 0]['pnl_pct'].mean()

    print(f"\n📈 OVERALL PERFORMANCE:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Total PnL: {total_pnl:+.2f}%")
    print(f"   Avg Win: {avg_win:+.2f}%")
    print(f"   Avg Loss: {avg_loss:.2f}%")

    # Drawdown
    cumulative = results_df['pnl_pct'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = cumulative - running_max
    max_dd = drawdown.min()
    print(f"   Max Drawdown: {max_dd:.2f}%")

    # Profit factor
    total_wins = results_df[results_df['pnl_pct'] > 0]['pnl_pct'].sum()
    total_losses = abs(results_df[results_df['pnl_pct'] <= 0]['pnl_pct'].sum())
    profit_factor = total_wins / total_losses if total_losses > 0 else 0
    print(f"   Profit Factor: {profit_factor:.2f}")

    # LONG vs SHORT
    print(f"\n📊 DIRECTION BREAKDOWN:")
    for direction in ['LONG', 'SHORT']:
        dir_trades = results_df[results_df['direction'] == direction]
        if len(dir_trades) > 0:
            dir_wins = len(dir_trades[dir_trades['pnl_pct'] > 0])
            dir_wr = dir_wins / len(dir_trades) * 100
            dir_pnl = dir_trades['pnl_pct'].sum()
            print(f"   {direction}: {len(dir_trades)} trades, {dir_wr:.1f}% WR, {dir_pnl:+.2f}% PnL")

    # Pattern breakdown
    print(f"\n🎨 PATTERN BREAKDOWN:")
    pattern_stats = results_df.groupby('pattern').agg({
        'pnl_pct': ['count', 'sum', 'mean'],
        'exit_type': lambda x: (x != 'SL').sum()  # wins
    }).round(2)

    for pattern in results_df['pattern'].unique():
        pattern_trades = results_df[results_df['pattern'] == pattern]
        pattern_wins = len(pattern_trades[pattern_trades['pnl_pct'] > 0])
        pattern_wr = pattern_wins / len(pattern_trades) * 100
        pattern_pnl = pattern_trades['pnl_pct'].sum()
        boosted_count = len(pattern_trades[pattern_trades['boosted'] == True])

        boost_indicator = f" (BOOSTED: {boosted_count})" if boosted_count > 0 else ""
        print(f"   {pattern}: {len(pattern_trades)} trades, {pattern_wr:.1f}% WR, {pattern_pnl:+.2f}% PnL{boost_indicator}")

    print("\n" + "="*80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Hybrid: SHORT Optimized + Pattern Filtering')
    parser.add_argument('--file', type=str, required=True, help='CSV file with OHLCV data')
    args = parser.parse_args()

    # Load data
    print(f"\n📂 Loading data from {args.file}...")
    df = pd.read_csv(args.file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')

    # Add active sessions if not present
    if 'is_active' not in df.columns:
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_active'] = df['is_london'] | df['is_ny']

    # Add timestamp column for backtest
    df['timestamp'] = df.index

    print(f"   Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")

    # Run backtest
    backtest = HybridBacktestV3()
    results_df, signals_df = backtest.run_backtest(df)

    # Print results
    print_results(results_df)

    # Save results
    results_df.to_csv('backtest_v3_hybrid_results.csv', index=False)
    print(f"\n💾 Results saved to: backtest_v3_hybrid_results.csv")


if __name__ == "__main__":
    main()
