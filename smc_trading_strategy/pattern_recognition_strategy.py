"""
"""
Pattern Recognition Strategy with Fibonacci Extensions
Recognizes chart patterns: Double Top/Bottom, Head & Shoulders, Triangles, Wedges, Flags
Uses Fibonacci 1.618 or 2.618 for dynamic TP (switchable mode)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fibonacci_1618_strategy import Fibonacci1618Strategy


class PatternRecognitionStrategy(Fibonacci1618Strategy):
    """
    Pattern Recognition Strategy

    Recognizes classic chart patterns and trades breakouts/reversals
    with Fibonacci extensions for TP
    """

    def __init__(
        self,
        fib_mode='standard',        # 'standard' (1.618) or 'aggressive' (2.618)
        pattern_tolerance=0.02,     # 2% tolerance for pattern matching (учет теней)
        min_pattern_swings=3,       # Minimum swings for pattern
        swing_lookback=15,          # Lookback for swing detection
        best_hours_only=True
    ):
        # Fibonacci level based on mode
        if fib_mode == 'aggressive':
            fib_extension = 2.618
            use_aggressive_tp = True
        else:
            fib_extension = 1.618
            use_aggressive_tp = False

        # Initialize parent
        super().__init__(
            fib_extension=fib_extension,
            use_aggressive_tp=use_aggressive_tp,
            swing_length=5,
            min_candle_quality=25,
            best_hours_only=best_hours_only
        )

        self.fib_mode = fib_mode
        self.pattern_tolerance = pattern_tolerance
        self.min_pattern_swings = min_pattern_swings
        self.swing_lookback = swing_lookback

        print(f"   Mode: PATTERN RECOGNITION")
        print(f"   Fibonacci Mode: {fib_mode.upper()} ({fib_extension})")
        print(f"   Pattern Tolerance: {pattern_tolerance*100}% (включая тени)")
        print(f"   Swing Lookback: {swing_lookback}")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run pattern recognition strategy
        """
        # Run parent strategy first (gets base signals)
        df = super().run_strategy(df)

        # Find swing points for pattern recognition
        df = self._find_swing_points(df)

        # Detect patterns
        df = self._detect_patterns(df)

        return df

    def _find_swing_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Find swing highs and lows for pattern recognition
        """
        df = df.copy()

        df['swing_high'] = False
        df['swing_low'] = False

        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            # Swing high - учитываем тени (high)
            window_highs = df['high'].iloc[i-self.swing_lookback:i+self.swing_lookback+1]
            if df['high'].iloc[i] == window_highs.max():
                df.loc[df.index[i], 'swing_high'] = True

            # Swing low - учитываем тени (low)
            window_lows = df['low'].iloc[i-self.swing_lookback:i+self.swing_lookback+1]
            if df['low'].iloc[i] == window_lows.min():
                df.loc[df.index[i], 'swing_low'] = True

        return df

    def _detect_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect CONTINUATION chart patterns only
        (Flags, Pennants, Wedges, Triangles)
        """
        df = df.copy()

        # Get swing points
        swing_highs = df[df['swing_high'] == True].copy()
        swing_lows = df[df['swing_low'] == True].copy()

        patterns_found = 0

        # Detect patterns (sliding window approach)
        for i in range(len(df)):
            if df['signal'].iloc[i] != 0:
                continue  # Already has signal

            # Get recent swings
            recent_highs = swing_highs[swing_highs.index < df.index[i]].tail(5)
            recent_lows = swing_lows[swing_lows.index < df.index[i]].tail(5)

            if len(recent_highs) < 2 or len(recent_lows) < 2:
                continue

            # 1. ASCENDING TRIANGLE (Bullish Continuation)
            pattern = self._detect_ascending_triangle(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'asc_triangle')
                if added:
                    patterns_found += 1
                    continue

            # 2. DESCENDING TRIANGLE (Bearish Continuation)
            pattern = self._detect_descending_triangle(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'desc_triangle')
                if added:
                    patterns_found += 1
                    continue

            # 3. SYMMETRICAL TRIANGLE
            pattern = self._detect_symmetrical_triangle(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'sym_triangle')
                if added:
                    patterns_found += 1
                    continue

            # 4. BULLISH FLAG
            pattern = self._detect_bull_flag(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'bull_flag')
                if added:
                    patterns_found += 1
                    continue

            # 5. BEARISH FLAG
            pattern = self._detect_bear_flag(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'bear_flag')
                if added:
                    patterns_found += 1
                    continue

            # 6. BULLISH PENNANT
            pattern = self._detect_bull_pennant(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'bull_pennant')
                if added:
                    patterns_found += 1
                    continue

            # 7. BEARISH PENNANT
            pattern = self._detect_bear_pennant(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'bear_pennant')
                if added:
                    patterns_found += 1
                    continue

            # 8. FALLING WEDGE (Bullish)
            pattern = self._detect_falling_wedge(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'falling_wedge')
                if added:
                    patterns_found += 1
                    continue

            # 9. RISING WEDGE (Bearish)
            pattern = self._detect_rising_wedge(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'rising_wedge')
                if added:
                    patterns_found += 1
                    continue

        print(f"   Detected {patterns_found} continuation patterns")

        return df

    def _detect_symmetrical_triangle(self, df, idx, recent_highs, recent_lows):
        """
        Detect Symmetrical Triangle (Continuation - direction depends on breakout)
        Rising lows + Falling highs converging
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        # Highs: falling
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']

        # Lows: rising
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        if high2 < high1 and low2 > low1:  # Converging
            resistance = high2
            support = low2

            # Breakout above (bullish)
            if df['close'].iloc[idx] > resistance:
                return {
                    'type': 'sym_triangle',
                    'direction': 1,
                    'entry': df['close'].iloc[idx],
                    'resistance': resistance,
                    'support': support
                }
            # Breakout below (bearish)
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
        """
        Detect Bullish Flag (Continuation)
        Strong uptrend + consolidation channel (slight down) + breakout up
        """
        if len(recent_highs) < 3 or len(recent_lows) < 3:
            return None

        # Check for uptrend before flag (flagpole)
        lookback = min(idx, 10)
        flagpole_data = df.iloc[max(0, idx-lookback):idx]
        if len(flagpole_data) < 5:
            return None

        # Uptrend check
        if flagpole_data['close'].iloc[-1] <= flagpole_data['close'].iloc[0] * 1.01:
            return None  # No uptrend

        # Flag: parallel channel sloping slightly down
        flag_highs = recent_highs.tail(2)
        flag_lows = recent_lows.tail(2)

        if len(flag_highs) == 2 and len(flag_lows) == 2:
            # Channel resistance
            resistance = flag_highs['high'].max()

            # Breakout above
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
        """
        Detect Bearish Flag (Continuation)
        Strong downtrend + consolidation channel (slight up) + breakout down
        """
        if len(recent_highs) < 3 or len(recent_lows) < 3:
            return None

        # Check for downtrend before flag
        lookback = min(idx, 10)
        flagpole_data = df.iloc[max(0, idx-lookback):idx]
        if len(flagpole_data) < 5:
            return None

        # Downtrend check
        if flagpole_data['close'].iloc[-1] >= flagpole_data['close'].iloc[0] * 0.99:
            return None  # No downtrend

        # Flag channel
        flag_highs = recent_highs.tail(2)
        flag_lows = recent_lows.tail(2)

        if len(flag_highs) == 2 and len(flag_lows) == 2:
            support = flag_lows['low'].min()

            # Breakout below
            if df['close'].iloc[idx] < support:
                return {
                    'type': 'bear_flag',
                    'direction': -1,
                    'entry': df['close'].iloc[idx],
                    'resistance': flag_highs['high'].max(),
                    'support': support
                }

        return None

    def _detect_bull_pennant(self, df, idx, recent_highs, recent_lows):
        """
        Detect Bullish Pennant (Continuation)
        Like flag but converging (symmetrical triangle after uptrend)
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        # Check for uptrend before pennant
        lookback = min(idx, 10)
        pole_data = df.iloc[max(0, idx-lookback):idx]
        if len(pole_data) < 5:
            return None

        if pole_data['close'].iloc[-1] <= pole_data['close'].iloc[0] * 1.01:
            return None  # No uptrend

        # Converging highs and lows
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        if high2 < high1 and low2 > low1:  # Converging
            resistance = high2

            # Breakout above
            if df['close'].iloc[idx] > resistance:
                return {
                    'type': 'bull_pennant',
                    'direction': 1,
                    'entry': df['close'].iloc[idx],
                    'resistance': resistance,
                    'support': low2
                }

        return None

    def _detect_bear_pennant(self, df, idx, recent_highs, recent_lows):
        """
        Detect Bearish Pennant (Continuation)
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        # Check for downtrend before pennant
        lookback = min(idx, 10)
        pole_data = df.iloc[max(0, idx-lookback):idx]
        if len(pole_data) < 5:
            return None

        if pole_data['close'].iloc[-1] >= pole_data['close'].iloc[0] * 0.99:
            return None  # No downtrend

        # Converging
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        if high2 < high1 and low2 > low1:  # Converging
            support = low2

            # Breakout below
            if df['close'].iloc[idx] < support:
                return {
                    'type': 'bear_pennant',
                    'direction': -1,
                    'entry': df['close'].iloc[idx],
                    'resistance': high2,
                    'support': support
                }

        return None

    def _detect_falling_wedge(self, df, idx, recent_highs, recent_lows):
        """
        Detect Falling Wedge (Bullish Continuation)
        Both highs and lows falling but converging (lows fall slower)
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        # Both falling
        if high2 < high1 and low2 < low1:
            # Converging (lows fall slower than highs)
            high_slope = (high1 - high2) / high1
            low_slope = (low1 - low2) / low1

            if high_slope > low_slope:  # Converging
                resistance = high2

                # Bullish breakout above
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
        """
        Detect Rising Wedge (Bearish Continuation)
        Both highs and lows rising but converging (highs rise slower)
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        # Both rising
        if high2 > high1 and low2 > low1:
            # Converging (highs rise slower than lows)
            high_slope = (high2 - high1) / high1
            low_slope = (low2 - low1) / low1

            if low_slope > high_slope:  # Converging
                support = low2

                # Bearish breakout below
                if df['close'].iloc[idx] < support:
                    return {
                        'type': 'rising_wedge',
                        'direction': -1,
                        'entry': df['close'].iloc[idx],
                        'resistance': high2,
                        'support': support
                    }

        return None

    def _detect_ascending_triangle(self, df, idx, recent_highs, recent_lows):
        """
        Detect Ascending Triangle (Bullish Continuation)
        Flat resistance + rising support
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        # Resistance: highs at similar level
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']

        tolerance = high1 * self.pattern_tolerance
        if abs(high1 - high2) <= tolerance:
            # Support: rising lows
            low1 = recent_lows.iloc[-2]['low']
            low2 = recent_lows.iloc[-1]['low']

            if low2 > low1:  # Rising lows
                resistance = max(high1, high2)

                # Breakout above resistance
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
        """
        Detect Descending Triangle (Bearish Continuation)
        Flat support + falling resistance
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        # Support: lows at similar level
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']

        tolerance = low1 * self.pattern_tolerance
        if abs(low1 - low2) <= tolerance:
            # Resistance: falling highs
            high1 = recent_highs.iloc[-2]['high']
            high2 = recent_highs.iloc[-1]['high']

            if high2 < high1:  # Falling highs
                support = min(low1, low2)

                # Breakout below support
                if df['close'].iloc[idx] < support:
                    return {
                        'type': 'desc_triangle',
                        'direction': -1,
                        'entry': df['close'].iloc[idx],
                        'resistance': high2,
                        'support': support
                    }

        return None

    def _add_pattern_signal(self, df, idx, pattern, pattern_name):
        """
        Add trading signal based on detected pattern
        """
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

        # Calculate SL and TP based on pattern
        if direction == 1:  # Long
            # SL below support/neckline
            if 'support' in pattern:
                sl = pattern['support'] * 0.999
            elif 'neckline' in pattern:
                sl = pattern['neckline'] * 0.999
            else:
                sl = pattern['head'] * 0.999

            # Fibonacci TP
            risk = entry - sl
            tp = entry + (risk * self.fib_extension)

        else:  # Short
            # SL above resistance/neckline
            if 'resistance' in pattern:
                sl = pattern['resistance'] * 1.001
            elif 'neckline' in pattern:
                sl = pattern['neckline'] * 1.001
            else:
                sl = pattern['head'] * 1.001

            # Fibonacci TP
            risk = sl - entry
            tp = entry - (risk * self.fib_extension)

        # Min risk check
        risk_pct = abs(entry - sl) / entry
        if risk_pct < 0.003:  # Min 0.3% risk
            return df, False

        # Add signal
        df.loc[df.index[idx], 'signal'] = direction
        df.loc[df.index[idx], 'entry_price'] = entry
        df.loc[df.index[idx], 'stop_loss'] = sl
        df.loc[df.index[idx], 'take_profit'] = tp
        df.loc[df.index[idx], 'signal_type'] = f"pattern_{pattern_name}"

        return df, True


class MultiSignalPatternStrategy(PatternRecognitionStrategy):
    """
    Multi-Signal Strategy with Pattern Recognition
    Combines BOS + Patterns + Fibonacci
    """

    def __init__(self, fib_mode='standard'):
        super().__init__(
            fib_mode=fib_mode,
            pattern_tolerance=0.02,
            swing_lookback=20,
            best_hours_only=True
        )

        print(f"   Mode: MULTI-SIGNAL + PATTERNS")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Combine pattern recognition with BOS signals
        """
        # Run pattern recognition
        df = super().run_strategy(df)

        # Note: BOS signals already added by parent class

        return df


if __name__ == "__main__":
    print("Pattern Recognition Strategy Module")
    print("Fibonacci Modes: 'standard' (1.618) or 'aggressive' (2.618)")
    print("Use MultiSignalPatternStrategy for trading")
