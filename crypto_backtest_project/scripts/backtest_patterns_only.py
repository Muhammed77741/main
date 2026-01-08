"""
Pure Pattern Recognition Backtest
Tests ONLY classic chart patterns without SMC signals:
- Ascending Triangle
- Descending Triangle
- Falling Wedge
- Rising Wedge
- Bullish Flag
- Bearish Flag
- Symmetrical Triangle
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse


class PurePatternStrategy:
    """Pure pattern recognition without SMC/BOS signals"""

    def __init__(self, pattern_tolerance=0.02, swing_lookback=20, best_hours_only=True):
        self.pattern_tolerance = pattern_tolerance
        self.swing_lookback = swing_lookback
        self.best_hours_only = best_hours_only

        print(f"\n📐 PURE PATTERN RECOGNITION STRATEGY")
        print(f"   Pattern Tolerance: {pattern_tolerance*100}%")
        print(f"   Swing Lookback: {swing_lookback}")
        print(f"   Best Hours Only: {best_hours_only}")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run pure pattern recognition"""
        df = df.copy()

        # Add required columns
        df['signal'] = 0
        df['entry_price'] = 0.0
        df['stop_loss'] = 0.0
        df['take_profit'] = 0.0
        df['pattern'] = ''
        df['is_active_session'] = df['is_active']

        # Find swing points
        df = self._find_swing_points(df)

        # Detect patterns
        df = self._detect_patterns(df)

        return df

    def _find_swing_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """Find swing highs and lows"""
        df = df.copy()

        df['swing_high'] = False
        df['swing_low'] = False

        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            # Swing high
            window_highs = df['high'].iloc[i-self.swing_lookback:i+self.swing_lookback+1]
            if df['high'].iloc[i] == window_highs.max():
                df.loc[df.index[i], 'swing_high'] = True

            # Swing low
            window_lows = df['low'].iloc[i-self.swing_lookback:i+self.swing_lookback+1]
            if df['low'].iloc[i] == window_lows.min():
                df.loc[df.index[i], 'swing_low'] = True

        return df

    def _detect_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect all chart patterns"""
        df = df.copy()

        swing_highs = df[df['swing_high'] == True].copy()
        swing_lows = df[df['swing_low'] == True].copy()

        patterns_found = 0

        for i in range(len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            # Get recent swings
            recent_highs = swing_highs[swing_highs.index < df.index[i]].tail(5)
            recent_lows = swing_lows[swing_lows.index < df.index[i]].tail(5)

            if len(recent_highs) < 2 or len(recent_lows) < 2:
                continue

            # Try all patterns in order
            patterns_to_try = [
                ('asc_triangle', self._detect_ascending_triangle),
                ('desc_triangle', self._detect_descending_triangle),
                ('sym_triangle', self._detect_symmetrical_triangle),
                ('bull_flag', self._detect_bull_flag),
                ('bear_flag', self._detect_bear_flag),
                ('falling_wedge', self._detect_falling_wedge),
                ('rising_wedge', self._detect_rising_wedge),
            ]

            for pattern_name, pattern_func in patterns_to_try:
                pattern = pattern_func(df, i, recent_highs, recent_lows)
                if pattern:
                    df, added = self._add_pattern_signal(df, i, pattern, pattern_name)
                    if added:
                        patterns_found += 1
                        break

        print(f"\n   ✅ Detected {patterns_found} chart patterns")
        return df

    def _detect_ascending_triangle(self, df, idx, recent_highs, recent_lows):
        """Ascending Triangle: flat resistance + rising support"""
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']

        tolerance = high1 * self.pattern_tolerance
        if abs(high1 - high2) <= tolerance:
            low1 = recent_lows.iloc[-2]['low']
            low2 = recent_lows.iloc[-1]['low']

            if low2 > low1:  # Rising lows
                resistance = max(high1, high2)

                if df['close'].iloc[idx] > resistance:
                    return {
                        'type': 'asc_triangle',
                        'direction': 1,
                        'entry': df['close'].iloc[idx],
                        'resistance': resistance,
                        'support': low2
                    }

        return None

    def _detect_descending_triangle(self, df, idx, recent_highs, recent_lows):
        """Descending Triangle: flat support + falling resistance"""
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        tolerance = low1 * self.pattern_tolerance
        if abs(low1 - low2) <= tolerance:
            high1 = recent_highs.iloc[-2]['high']
            high2 = recent_highs.iloc[-1]['high']

            if high2 < high1:  # Falling highs
                support = min(low1, low2)

                if df['close'].iloc[idx] < support:
                    return {
                        'type': 'desc_triangle',
                        'direction': -1,
                        'entry': df['close'].iloc[idx],
                        'resistance': high2,
                        'support': support
                    }

        return None

    def _detect_symmetrical_triangle(self, df, idx, recent_highs, recent_lows):
        """Symmetrical Triangle: converging trendlines"""
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        if high2 < high1 and low2 > low1:  # Converging
            resistance = high2
            support = low2

            if df['close'].iloc[idx] > resistance:
                return {
                    'type': 'sym_triangle',
                    'direction': 1,
                    'entry': df['close'].iloc[idx],
                    'resistance': resistance,
                    'support': support
                }
            elif df['close'].iloc[idx] < support:
                return {
                    'type': 'sym_triangle',
                    'direction': -1,
                    'entry': df['close'].iloc[idx],
                    'resistance': resistance,
                    'support': support
                }

        return None

    def _detect_bull_flag(self, df, idx, recent_highs, recent_lows):
        """Bullish Flag: uptrend + consolidation + breakout up"""
        if len(recent_highs) < 3 or len(recent_lows) < 3:
            return None

        lookback = min(idx, 10)
        flagpole_data = df.iloc[max(0, idx-lookback):idx]
        if len(flagpole_data) < 5:
            return None

        if flagpole_data['close'].iloc[-1] <= flagpole_data['close'].iloc[0] * 1.01:
            return None  # No uptrend

        flag_highs = recent_highs.tail(2)
        flag_lows = recent_lows.tail(2)

        if len(flag_highs) == 2 and len(flag_lows) == 2:
            resistance = flag_highs['high'].max()

            if df['close'].iloc[idx] > resistance:
                return {
                    'type': 'bull_flag',
                    'direction': 1,
                    'entry': df['close'].iloc[idx],
                    'resistance': resistance,
                    'support': flag_lows['low'].min()
                }

        return None

    def _detect_bear_flag(self, df, idx, recent_highs, recent_lows):
        """Bearish Flag: downtrend + consolidation + breakout down"""
        if len(recent_highs) < 3 or len(recent_lows) < 3:
            return None

        lookback = min(idx, 10)
        flagpole_data = df.iloc[max(0, idx-lookback):idx]
        if len(flagpole_data) < 5:
            return None

        if flagpole_data['close'].iloc[-1] >= flagpole_data['close'].iloc[0] * 0.99:
            return None  # No downtrend

        flag_highs = recent_highs.tail(2)
        flag_lows = recent_lows.tail(2)

        if len(flag_highs) == 2 and len(flag_lows) == 2:
            support = flag_lows['low'].min()

            if df['close'].iloc[idx] < support:
                return {
                    'type': 'bear_flag',
                    'direction': -1,
                    'entry': df['close'].iloc[idx],
                    'resistance': flag_highs['high'].max(),
                    'support': support
                }

        return None

    def _detect_falling_wedge(self, df, idx, recent_highs, recent_lows):
        """Falling Wedge: both trendlines falling but converging (bullish)"""
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        if high2 < high1 and low2 < low1:  # Both falling
            high_slope = (high1 - high2) / high1
            low_slope = (low1 - low2) / low1

            if high_slope > low_slope:  # Converging
                resistance = high2

                if df['close'].iloc[idx] > resistance:
                    return {
                        'type': 'falling_wedge',
                        'direction': 1,
                        'entry': df['close'].iloc[idx],
                        'resistance': resistance,
                        'support': low2
                    }

        return None

    def _detect_rising_wedge(self, df, idx, recent_highs, recent_lows):
        """Rising Wedge: both trendlines rising but converging (bearish)"""
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        if high2 > high1 and low2 > low1:  # Both rising
            high_slope = (high2 - high1) / high1
            low_slope = (low2 - low1) / low1

            if low_slope > high_slope:  # Converging
                support = low2

                if df['close'].iloc[idx] < support:
                    return {
                        'type': 'rising_wedge',
                        'direction': -1,
                        'entry': df['close'].iloc[idx],
                        'resistance': high2,
                        'support': support
                    }

        return None

    def _add_pattern_signal(self, df, idx, pattern, pattern_name):
        """Add trading signal based on pattern"""
        if pattern is None:
            return df, False

        # Time filter
        if self.best_hours_only:
            hour = df.index[idx].hour
            if hour not in [8, 9, 10, 13, 14, 15]:
                return df, False

        # Session filter
        if not df['is_active_session'].iloc[idx]:
            return df, False

        direction = pattern['direction']
        entry = pattern['entry']

        # Calculate SL and TP
        if direction == 1:  # Long
            if 'support' in pattern:
                sl = pattern['support'] * 0.999
            else:
                sl = entry * 0.99

            risk = entry - sl
            tp = entry + (risk * 1.618)  # Fibonacci 1.618
        else:  # Short
            if 'resistance' in pattern:
                sl = pattern['resistance'] * 1.001
            else:
                sl = entry * 1.01

            risk = sl - entry
            tp = entry - (risk * 1.618)

        # Min risk check
        risk_pct = abs(entry - sl) / entry
        if risk_pct < 0.003:  # Min 0.3% risk
            return df, False

        # Add signal
        df.loc[df.index[idx], 'signal'] = direction
        df.loc[df.index[idx], 'entry_price'] = entry
        df.loc[df.index[idx], 'stop_loss'] = sl
        df.loc[df.index[idx], 'take_profit'] = tp
        df.loc[df.index[idx], 'pattern'] = pattern_name

        return df, True


class PatternBacktest:
    """Backtest for pure pattern recognition"""

    def __init__(self, spread_points=2.0, commission_points=0.5, swap_per_day=-0.3):
        self.spread = spread_points
        self.commission = commission_points
        self.swap_per_day = swap_per_day

        # Simple fixed parameters (no adaptive)
        self.tp1 = 20
        self.tp2 = 35
        self.tp3 = 50
        self.trailing = 15
        self.timeout = 48

        self.max_positions = 5

    def backtest(self, df, strategy, close_pct1=0.5, close_pct2=0.3, close_pct3=0.2):
        """Run backtest"""

        print(f"\n{'='*80}")
        print(f"📊 PURE PATTERN BACKTEST")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")
        print(f"\n   Parameters:")
        print(f"   TP: {self.tp1}п / {self.tp2}п / {self.tp3}п")
        print(f"   Trailing: {self.trailing}п")
        print(f"   Timeout: {self.timeout}h")
        print(f"   Max positions: {self.max_positions}")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())

        trades = []
        open_positions = []

        # Track by pattern type
        pattern_stats = {}

        for i in range(len(df_strategy)):
            candle = df_strategy.iloc[i]
            candle_time = df_strategy.index[i]
            high = candle['high']
            low = candle['low']
            close = candle['close']
            signal = candle.get('signal', 0)

            if signal != 0:
                if len(open_positions) >= self.max_positions:
                    continue

                direction = 'LONG' if signal == 1 else 'SHORT'
                signal_sl = candle.get('stop_loss', close)
                pattern_name = candle.get('pattern', 'unknown')

                if direction == 'LONG':
                    entry_price = close + self.spread / 2
                    sl_distance = close - signal_sl
                    sl_price = entry_price - sl_distance
                    tp1_price = entry_price + self.tp1
                    tp2_price = entry_price + self.tp2
                    tp3_price = entry_price + self.tp3
                else:
                    entry_price = close - self.spread / 2
                    sl_distance = signal_sl - close
                    sl_price = entry_price + sl_distance
                    tp1_price = entry_price - self.tp1
                    tp2_price = entry_price - self.tp2
                    tp3_price = entry_price - self.tp3

                new_pos = {
                    'entry_time': candle_time,
                    'entry_price': entry_price,
                    'direction': direction,
                    'sl_price': sl_price,
                    'tp1_price': tp1_price,
                    'tp2_price': tp2_price,
                    'tp3_price': tp3_price,
                    'tp1_hit': False,
                    'tp2_hit': False,
                    'tp3_hit': False,
                    'trailing_active': False,
                    'trailing_high': entry_price if direction == 'LONG' else 0,
                    'trailing_low': entry_price if direction == 'SHORT' else 999999,
                    'position_remaining': 1.0,
                    'total_pnl_pct': 0.0,
                    'pattern': pattern_name,
                }

                open_positions.append(new_pos)

                # Track pattern
                if pattern_name not in pattern_stats:
                    pattern_stats[pattern_name] = {'count': 0, 'wins': 0, 'pnl': 0.0}
                pattern_stats[pattern_name]['count'] += 1

            # Update positions (simplified version)
            positions_to_close = []

            for pos_idx, pos in enumerate(open_positions):
                if pos['entry_time'] == candle_time:
                    continue

                hours_in_trade = (candle_time - pos['entry_time']).total_seconds() / 3600

                if hours_in_trade >= self.timeout:
                    if pos['direction'] == 'LONG':
                        exit_price = close - self.spread / 2
                    else:
                        exit_price = close + self.spread / 2

                    pnl_points = self._calculate_pnl(pos, exit_price, hours_in_trade)
                    pos['total_pnl_pct'] += (pnl_points / pos['entry_price']) * 100

                    trade = self._create_trade(pos, exit_price, 'TIMEOUT', candle_time)
                    trades.append(trade)
                    positions_to_close.append(pos_idx)
                    continue

                # Check SL/TP
                if pos['direction'] == 'LONG':
                    if high > pos['trailing_high']:
                        pos['trailing_high'] = high

                    if pos['trailing_active']:
                        new_sl = pos['trailing_high'] - self.trailing
                        if new_sl > pos['sl_price']:
                            pos['sl_price'] = new_sl

                    if low <= pos['sl_price']:
                        pnl_points = self._calculate_pnl(pos, pos['sl_price'], hours_in_trade)
                        pos['total_pnl_pct'] += (pnl_points / pos['entry_price']) * 100
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._create_trade(pos, pos['sl_price'], exit_type, candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                    if high >= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_partial(pos, exit_price, close_pct1, hours_in_trade)
                        pos['total_pnl_pct'] += (pnl_points / pos['entry_price']) * 100
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = high - self.trailing

                    if high >= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_partial(pos, exit_price, close_pct2, hours_in_trade)
                        pos['total_pnl_pct'] += (pnl_points / pos['entry_price']) * 100
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    if high >= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_partial(pos, exit_price, close_pct3, hours_in_trade)
                        pos['total_pnl_pct'] += (pnl_points / pos['entry_price']) * 100
                        pos['position_remaining'] -= close_pct3
                        pos['tp3_hit'] = True

                    if pos['position_remaining'] <= 0.01:
                        trade = self._create_trade(pos, pos['tp3_price'], 'TP3', candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)

                else:  # SHORT
                    if low < pos['trailing_low']:
                        pos['trailing_low'] = low

                    if pos['trailing_active']:
                        new_sl = pos['trailing_low'] + self.trailing
                        if new_sl < pos['sl_price']:
                            pos['sl_price'] = new_sl

                    if high >= pos['sl_price']:
                        pnl_points = self._calculate_pnl(pos, pos['sl_price'], hours_in_trade)
                        pos['total_pnl_pct'] += (pnl_points / pos['entry_price']) * 100
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._create_trade(pos, pos['sl_price'], exit_type, candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                    if low <= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_partial(pos, exit_price, close_pct1, hours_in_trade)
                        pos['total_pnl_pct'] += (pnl_points / pos['entry_price']) * 100
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = low + self.trailing

                    if low <= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_partial(pos, exit_price, close_pct2, hours_in_trade)
                        pos['total_pnl_pct'] += (pnl_points / pos['entry_price']) * 100
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    if low <= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_partial(pos, exit_price, close_pct3, hours_in_trade)
                        pos['total_pnl_pct'] += (pnl_points / pos['entry_price']) * 100
                        pos['position_remaining'] -= close_pct3
                        pos['tp3_hit'] = True

                    if pos['position_remaining'] <= 0.01:
                        trade = self._create_trade(pos, pos['tp3_price'], 'TP3', candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)

            for idx in sorted(positions_to_close, reverse=True):
                del open_positions[idx]

        if len(trades) == 0:
            print("❌ No completed trades")
            return None

        trades_df = pd.DataFrame(trades)

        # Update pattern stats
        for trade in trades:
            pattern = trade['pattern']
            if pattern in pattern_stats:
                if trade['pnl_pct'] > 0:
                    pattern_stats[pattern]['wins'] += 1
                pattern_stats[pattern]['pnl'] += trade['pnl_pct']

        # Print pattern statistics
        print(f"\n{'='*80}")
        print(f"📊 PATTERN STATISTICS")
        print(f"{'='*80}")

        for pattern, stats in sorted(pattern_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            print(f"\n   {pattern}:")
            print(f"   Trades: {stats['count']}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Total PnL: {stats['pnl']:+.2f}%")

        self._print_results(trades_df)

        return trades_df

    def _calculate_pnl(self, pos, exit_price, hours):
        """Calculate PnL"""
        if pos['direction'] == 'LONG':
            pnl = exit_price - pos['entry_price']
        else:
            pnl = pos['entry_price'] - exit_price

        pnl *= pos['position_remaining']
        pnl -= self.commission * pos['position_remaining']

        if hours > 24:
            days = hours / 24
            pnl += self.swap_per_day * days * pos['position_remaining']

        return pnl

    def _calculate_pnl_partial(self, pos, exit_price, size, hours):
        """Calculate partial PnL"""
        if pos['direction'] == 'LONG':
            pnl = exit_price - pos['entry_price']
        else:
            pnl = pos['entry_price'] - exit_price

        pnl *= size
        pnl -= self.commission * size

        if hours > 24:
            days = hours / 24
            pnl += self.swap_per_day * days * size

        return pnl

    def _create_trade(self, pos, exit_price, exit_type, exit_time):
        """Create trade record"""
        duration_hours = (exit_time - pos['entry_time']).total_seconds() / 3600
        pnl_pct = pos['total_pnl_pct']
        pnl_points = (pnl_pct / 100) * pos['entry_price']

        return {
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'direction': pos['direction'],
            'pattern': pos['pattern'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
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
    parser = argparse.ArgumentParser(description='Pure Pattern Backtest')
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
    strategy = PurePatternStrategy(
        pattern_tolerance=0.02,
        swing_lookback=20,
        best_hours_only=True
    )

    # Run backtest
    backtest = PatternBacktest()
    trades_df = backtest.backtest(df, strategy)

    if trades_df is not None:
        trades_df.to_csv('backtest_patterns_only_results.csv', index=False)
        print(f"\n💾 Results saved to backtest_patterns_only_results.csv")


if __name__ == "__main__":
    main()
