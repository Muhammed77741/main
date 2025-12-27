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
        swing_lookback=20,          # Lookback for swing detection
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
        Detect chart patterns and generate signals
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

            # 1. DOUBLE TOP (Bearish Reversal)
            pattern = self._detect_double_top(df, i, recent_highs)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'double_top')
                if added:
                    patterns_found += 1
                    continue

            # 2. DOUBLE BOTTOM (Bullish Reversal)
            pattern = self._detect_double_bottom(df, i, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'double_bottom')
                if added:
                    patterns_found += 1
                    continue

            # 3. HEAD AND SHOULDERS (Bearish Reversal)
            pattern = self._detect_head_and_shoulders(df, i, recent_highs)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'head_shoulders')
                if added:
                    patterns_found += 1
                    continue

            # 4. INVERSE HEAD AND SHOULDERS (Bullish Reversal)
            pattern = self._detect_inverse_head_shoulders(df, i, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'inv_head_shoulders')
                if added:
                    patterns_found += 1
                    continue

            # 5. ASCENDING TRIANGLE (Bullish Continuation)
            pattern = self._detect_ascending_triangle(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'asc_triangle')
                if added:
                    patterns_found += 1
                    continue

            # 6. DESCENDING TRIANGLE (Bearish Continuation)
            pattern = self._detect_descending_triangle(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'desc_triangle')
                if added:
                    patterns_found += 1
                    continue

        print(f"   Detected {patterns_found} chart patterns")

        return df

    def _detect_double_top(self, df, idx, recent_highs):
        """
        Detect Double Top pattern (Bearish Reversal)
        Two peaks at similar level with a valley between
        """
        if len(recent_highs) < 2:
            return None

        # Get last 2 swing highs
        high1 = recent_highs.iloc[-2]
        high2 = recent_highs.iloc[-1]

        price1 = high1['high']
        price2 = high2['high']

        # Check if peaks are at similar level (с погрешностью)
        tolerance = price1 * self.pattern_tolerance
        if abs(price1 - price2) <= tolerance:
            # Check if current price breaks neckline (valley between peaks)
            valley_data = df[(df.index > high1.name) & (df.index < high2.name)]
            if len(valley_data) > 0:
                neckline = valley_data['low'].min()

                # Breakout below neckline
                if df['close'].iloc[idx] < neckline:
                    return {
                        'type': 'double_top',
                        'direction': -1,
                        'entry': df['close'].iloc[idx],
                        'resistance': max(price1, price2),
                        'neckline': neckline
                    }

        return None

    def _detect_double_bottom(self, df, idx, recent_lows):
        """
        Detect Double Bottom pattern (Bullish Reversal)
        """
        if len(recent_lows) < 2:
            return None

        low1 = recent_lows.iloc[-2]
        low2 = recent_lows.iloc[-1]

        price1 = low1['low']
        price2 = low2['low']

        tolerance = price1 * self.pattern_tolerance
        if abs(price1 - price2) <= tolerance:
            # Neckline (peak between valleys)
            peak_data = df[(df.index > low1.name) & (df.index < low2.name)]
            if len(peak_data) > 0:
                neckline = peak_data['high'].max()

                # Breakout above neckline
                if df['close'].iloc[idx] > neckline:
                    return {
                        'type': 'double_bottom',
                        'direction': 1,
                        'entry': df['close'].iloc[idx],
                        'support': min(price1, price2),
                        'neckline': neckline
                    }

        return None

    def _detect_head_and_shoulders(self, df, idx, recent_highs):
        """
        Detect Head and Shoulders pattern (Bearish Reversal)
        Left shoulder - Head (higher) - Right shoulder
        """
        if len(recent_highs) < 3:
            return None

        left_shoulder = recent_highs.iloc[-3]
        head = recent_highs.iloc[-2]
        right_shoulder = recent_highs.iloc[-1]

        ls_price = left_shoulder['high']
        head_price = head['high']
        rs_price = right_shoulder['high']

        # Head должна быть выше плеч
        if head_price > ls_price and head_price > rs_price:
            # Плечи примерно на одном уровне (с погрешностью)
            tolerance = ls_price * self.pattern_tolerance
            if abs(ls_price - rs_price) <= tolerance:
                # Neckline - lowest point between shoulders
                neckline_data = df[(df.index > left_shoulder.name) & (df.index < right_shoulder.name)]
                if len(neckline_data) > 0:
                    neckline = neckline_data['low'].min()

                    # Breakout below neckline
                    if df['close'].iloc[idx] < neckline:
                        return {
                            'type': 'head_shoulders',
                            'direction': -1,
                            'entry': df['close'].iloc[idx],
                            'head': head_price,
                            'neckline': neckline
                        }

        return None

    def _detect_inverse_head_shoulders(self, df, idx, recent_lows):
        """
        Detect Inverse Head and Shoulders (Bullish Reversal)
        """
        if len(recent_lows) < 3:
            return None

        left_shoulder = recent_lows.iloc[-3]
        head = recent_lows.iloc[-2]
        right_shoulder = recent_lows.iloc[-1]

        ls_price = left_shoulder['low']
        head_price = head['low']
        rs_price = right_shoulder['low']

        # Head должна быть ниже плеч
        if head_price < ls_price and head_price < rs_price:
            tolerance = ls_price * self.pattern_tolerance
            if abs(ls_price - rs_price) <= tolerance:
                neckline_data = df[(df.index > left_shoulder.name) & (df.index < right_shoulder.name)]
                if len(neckline_data) > 0:
                    neckline = neckline_data['high'].max()

                    # Breakout above neckline
                    if df['close'].iloc[idx] > neckline:
                        return {
                            'type': 'inv_head_shoulders',
                            'direction': 1,
                            'entry': df['close'].iloc[idx],
                            'head': head_price,
                            'neckline': neckline
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
