"""
Fibonacci 1.618 Strategy
Uses Fibonacci extension levels (1.618) for take profit targets
Based on Original Multi-Signal Strategy
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import IntradayGoldStrategy
from smc_indicators import SMCIndicators


class Fibonacci1618Strategy(IntradayGoldStrategy):
    """
    Fibonacci 1.618 extension strategy

    Key innovation: Uses Fibonacci 1.618 extension for TP instead of fixed R:R

    Fibonacci logic:
    - Point A: Previous swing high/low (starting point)
    - Point B: Entry point (signal candle)
    - Point C: Stop loss level
    - TP = Entry + (Entry - C) * 1.618 (Fibonacci extension)

    This creates dynamic R:R based on market structure
    """

    def __init__(
        self,
        fib_extension=1.618,         # Fibonacci extension level
        use_aggressive_tp=False,     # Use 2.618 for aggressive TP
        swing_length=5,
        min_candle_quality=25,
        best_hours_only=True
    ):
        # Initialize parent with base R:R (will be overridden by Fibonacci)
        super().__init__(
            risk_reward_ratio=1.8,  # Fallback, but Fib will override
            swing_length=swing_length,
            min_candle_quality=min_candle_quality,
            best_hours_only=best_hours_only
        )

        self.fib_extension = fib_extension
        self.use_aggressive_tp = use_aggressive_tp
        self.aggressive_fib = 2.618

        print(f"   Mode: FIBONACCI 1.618 EXTENSION")
        print(f"   Fib Level: {fib_extension}")
        print(f"   Aggressive TP (2.618): {use_aggressive_tp}")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run strategy with Fibonacci TP calculation
        """
        # Run parent strategy first
        df = super().run_strategy(df)

        # Recalculate TP using Fibonacci extensions
        df = self._apply_fibonacci_tp(df)

        return df

    def _apply_fibonacci_tp(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply Fibonacci 1.618 extension for take profit levels
        """
        df = df.copy()

        signals_modified = 0

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            entry_price = df['entry_price'].iloc[i]
            stop_loss = df['stop_loss'].iloc[i]

            if pd.isna(entry_price) or pd.isna(stop_loss):
                continue

            # Find previous swing point for Fibonacci calculation
            swing_point = self._find_swing_point(df, i, df['signal'].iloc[i])

            # Calculate Fibonacci extension TP
            # Risk = Entry - SL
            risk = abs(entry_price - stop_loss)

            # Fibonacci extension: TP = Entry + Risk * Fib_Level
            if df['signal'].iloc[i] == 1:  # Long
                # Use 1.618 or 2.618 depending on settings
                fib_level = self.aggressive_fib if self.use_aggressive_tp else self.fib_extension
                new_tp = entry_price + (risk * fib_level)
            else:  # Short
                fib_level = self.aggressive_fib if self.use_aggressive_tp else self.fib_extension
                new_tp = entry_price - (risk * fib_level)

            # Update TP
            df.loc[df.index[i], 'take_profit'] = new_tp
            signals_modified += 1

        if signals_modified > 0:
            print(f"   Applied Fibonacci {self.fib_extension} TP to {signals_modified} signals")

        return df

    def _find_swing_point(self, df: pd.DataFrame, signal_idx: int, direction: int) -> float:
        """
        Find previous swing point for Fibonacci calculation
        """
        # Look back for swing high/low
        lookback = min(signal_idx, 20)

        if direction == 1:  # Long - find previous swing low
            recent_data = df['low'].iloc[max(0, signal_idx - lookback):signal_idx]
            if len(recent_data) > 0:
                return recent_data.min()
        else:  # Short - find previous swing high
            recent_data = df['high'].iloc[max(0, signal_idx - lookback):signal_idx]
            if len(recent_data) > 0:
                return recent_data.max()

        # Fallback to current price
        return df['close'].iloc[signal_idx]


class MultiSignalGoldStrategy(Fibonacci1618Strategy):
    """
    Multi-Signal Strategy with Fibonacci 1.618
    Generates signals from multiple sources: OB, FVG, Liquidity Sweeps, BOS
    """

    def __init__(self):
        super().__init__(
            fib_extension=1.618,
            use_aggressive_tp=False,
            swing_length=5,
            min_candle_quality=25,
            best_hours_only=True
        )

        print(f"   Mode: MULTI-SIGNAL (OB+FVG+Liquidity+BOS)")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Multi-signal approach: Combine multiple SMC signals
        """
        df = super().run_strategy(df)

        # Add BOS (Break of Structure) signals
        df = self._add_bos_signals(df)

        return df

    def _add_bos_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add BOS signals - breaks of swing high/low
        WITH QUALITY FILTERS (same as main strategy)
        """
        df = df.copy()

        bos_signals = 0
        lookback_window = 20  # Prevent too frequent signals

        for i in range(self.swing_length + 1, len(df)):
            # Skip if already has signal
            if df['signal'].iloc[i] != 0:
                continue

            # Quality Filter 1: Best hours only
            if self.best_hours_only:
                hour = df.index[i].hour
                best_hours = [8, 9, 10, 13, 14, 15]
                if hour not in best_hours:
                    continue

            # Quality Filter 2: Active session
            if not df['is_active_session'].iloc[i]:
                continue

            # Quality Filter 3: Not too recent from last BOS signal
            # Check if there was a BOS signal in last 6 hours
            if 'signal_type' in df.columns:
                lookback_start = max(0, i - 6)
                recent_signals = df['signal_type'].iloc[lookback_start:i]
                if any('bos' in str(s) for s in recent_signals if pd.notna(s)):
                    continue

            # Find swing high/low
            swing_window = df.iloc[i - self.swing_length:i]

            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_close = df['close'].iloc[i]

            swing_high = swing_window['high'].max()
            swing_low = swing_window['low'].min()

            # Calculate risk for min risk check
            risk_long = current_close - swing_low
            risk_short = swing_high - current_close

            # Bullish BOS: Break above swing high
            if current_high > swing_high and current_close > swing_high:
                # Min risk check (not too tight SL)
                if risk_long > df['close'].iloc[i] * 0.003:  # Min 0.3% risk
                    entry = current_close
                    sl = swing_low
                    risk = entry - sl

                    # Fibonacci TP
                    tp = entry + (risk * self.fib_extension)

                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = entry
                    df.loc[df.index[i], 'stop_loss'] = sl
                    df.loc[df.index[i], 'take_profit'] = tp
                    df.loc[df.index[i], 'signal_type'] = 'bos_long'
                    bos_signals += 1

            # Bearish BOS: Break below swing low
            elif current_low < swing_low and current_close < swing_low:
                # Min risk check
                if risk_short > df['close'].iloc[i] * 0.003:  # Min 0.3% risk
                    entry = current_close
                    sl = swing_high
                    risk = sl - entry

                    # Fibonacci TP
                    tp = entry - (risk * self.fib_extension)

                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = entry
                    df.loc[df.index[i], 'stop_loss'] = sl
                    df.loc[df.index[i], 'take_profit'] = tp
                    df.loc[df.index[i], 'signal_type'] = 'bos_short'
                    bos_signals += 1

        print(f"   Added {bos_signals} BOS signals (with quality filters)")

        return df


if __name__ == "__main__":
    print("Fibonacci 1.618 Strategy Module")
    print("Use MultiSignalGoldStrategy for trading")
