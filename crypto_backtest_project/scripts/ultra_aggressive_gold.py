"""
Ultra-Aggressive Intraday Gold Strategy
Target: 1-3+ signals per day

Approach:
- Very low quality thresholds (10-15)
- Multiple signal types (OB, FVG, Breakouts, Pin Bars, Engulfing)
- Minimal filtering
- All active hours (not just best)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import IntradayGoldStrategy
from smc_indicators import SMCIndicators


class UltraAggressiveGoldStrategy(IntradayGoldStrategy):
    """
    Ultra-aggressive intraday strategy
    Target: 1-3 signals per day minimum

    Features:
    - Min quality: 10 (very low)
    - Swing length: 3 (very short)
    - No best hours filter
    - Multiple pattern recognition
    - Minimal filters
    """

    def __init__(self):
        super().__init__(
            risk_reward_ratio=1.5,
            swing_length=3,
            volume_lookback=0,          # No volume history check
            min_candle_quality=10,      # Very low threshold
            trade_active_sessions_only=False,  # Trade all hours
            avoid_round_numbers=False,
            use_adaptive_rr=False,
            min_range_quality=0.05,     # Almost no filter
            best_hours_only=False
        )

        self.smc = SMCIndicators()
        print(f"   Mode: ULTRA-AGGRESSIVE (Target 1-3+ signals/day)")
        print(f"   Quality Threshold: {self.min_candle_quality} (very low)")
        print(f"   All Hours: True")
        print(f"   Pattern Types: OB, FVG, Breakout, PinBar, Engulfing, BOS")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run ultra-aggressive strategy with all signal types
        """
        print(f"\n🚀 Running Ultra-Aggressive Intraday Strategy...")

        # Apply base strategy
        df = super().run_strategy(df)

        # Add more signal types
        df = self._add_breakout_signals(df)
        df = self._add_pin_bar_signals(df)
        df = self._add_engulfing_signals(df)
        df = self._add_momentum_signals(df)

        final_signals = len(df[df['signal'] != 0])
        print(f"\n✅ Total signals generated: {final_signals}")

        return df

    def _add_breakout_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add simple breakout signals
        Price breaks above/below recent high/low with volume
        """
        df = df.copy()
        breakout_signals = 0

        lookback = 10  # 10 hours

        for i in range(lookback, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            # Bullish breakout
            recent_high = df['high'].iloc[i-lookback:i-1].max()
            if df['close'].iloc[i] > recent_high:
                # Minimal volume check
                if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 0.8:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i-3:i].min() * 0.9998
                    df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.003
                    df.loc[df.index[i], 'signal_type'] = 'breakout_long'
                    breakout_signals += 1

            # Bearish breakout
            recent_low = df['low'].iloc[i-lookback:i-1].min()
            if df['close'].iloc[i] < recent_low:
                if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 0.8:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i-3:i].max() * 1.0002
                    df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.997
                    df.loc[df.index[i], 'signal_type'] = 'breakout_short'
                    breakout_signals += 1

        if breakout_signals > 0:
            print(f"   Added {breakout_signals} breakout signals")

        return df

    def _add_pin_bar_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add pin bar (rejection candle) signals
        Long upper/lower wicks indicating rejection
        """
        df = df.copy()
        pinbar_signals = 0

        for i in range(5, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            close = df['close'].iloc[i]
            open_price = df['open'].iloc[i]

            candle_range = high - low
            if candle_range == 0:
                continue

            body = abs(close - open_price)
            upper_wick = high - max(close, open_price)
            lower_wick = min(close, open_price) - low

            # Bullish pin bar (long lower wick)
            if lower_wick > candle_range * 0.6 and body < candle_range * 0.3:
                # Close in upper 40% of range
                if (close - low) / candle_range > 0.6:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = low * 0.9995
                    df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.003
                    df.loc[df.index[i], 'signal_type'] = 'pinbar_long'
                    pinbar_signals += 1

            # Bearish pin bar (long upper wick)
            if upper_wick > candle_range * 0.6 and body < candle_range * 0.3:
                # Close in lower 40% of range
                if (high - close) / candle_range > 0.6:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = high * 1.0005
                    df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.997
                    df.loc[df.index[i], 'signal_type'] = 'pinbar_short'
                    pinbar_signals += 1

        if pinbar_signals > 0:
            print(f"   Added {pinbar_signals} pin bar signals")

        return df

    def _add_engulfing_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add engulfing candle signals
        Current candle engulfs previous candle
        """
        df = df.copy()
        engulfing_signals = 0

        for i in range(5, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            # Current candle
            curr_open = df['open'].iloc[i]
            curr_close = df['close'].iloc[i]
            curr_high = df['high'].iloc[i]
            curr_low = df['low'].iloc[i]

            # Previous candle
            prev_open = df['open'].iloc[i-1]
            prev_close = df['close'].iloc[i-1]
            prev_high = df['high'].iloc[i-1]
            prev_low = df['low'].iloc[i-1]

            # Bullish engulfing
            if (curr_close > curr_open and  # Current bullish
                prev_close < prev_open and  # Previous bearish
                curr_close > prev_open and  # Engulfs prev open
                curr_open < prev_close):    # Engulfs prev close

                # Volume confirmation (minimal)
                if df['volume'].iloc[i] > df['volume'].iloc[i-1] * 0.8:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = curr_low * 0.9995
                    df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.0035
                    df.loc[df.index[i], 'signal_type'] = 'engulfing_long'
                    engulfing_signals += 1

            # Bearish engulfing
            if (curr_close < curr_open and  # Current bearish
                prev_close > prev_open and  # Previous bullish
                curr_close < prev_open and  # Engulfs prev open
                curr_open > prev_close):    # Engulfs prev close

                if df['volume'].iloc[i] > df['volume'].iloc[i-1] * 0.8:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = curr_high * 1.0005
                    df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.9965
                    df.loc[df.index[i], 'signal_type'] = 'engulfing_short'
                    engulfing_signals += 1

        if engulfing_signals > 0:
            print(f"   Added {engulfing_signals} engulfing signals")

        return df

    def _add_momentum_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add simple momentum signals
        3 consecutive candles in same direction with increasing volume
        """
        df = df.copy()
        momentum_signals = 0

        for i in range(5, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            # Check last 3 candles
            candles = df.iloc[i-2:i+1]

            # Bullish momentum
            all_bullish = all(candles['close'] > candles['open'])
            increasing = all(
                candles['close'].iloc[j] > candles['close'].iloc[j-1]
                for j in range(1, len(candles))
            )

            if all_bullish and increasing:
                # Volume trending up
                vol_increasing = df['volume'].iloc[i] > df['volume'].iloc[i-2]

                if vol_increasing:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i-2:i+1].min() * 0.9995
                    df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.004
                    df.loc[df.index[i], 'signal_type'] = 'momentum_long'
                    momentum_signals += 1

            # Bearish momentum
            all_bearish = all(candles['close'] < candles['open'])
            decreasing = all(
                candles['close'].iloc[j] < candles['close'].iloc[j-1]
                for j in range(1, len(candles))
            )

            if all_bearish and decreasing:
                vol_increasing = df['volume'].iloc[i] > df['volume'].iloc[i-2]

                if vol_increasing:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i-2:i+1].max() * 1.0005
                    df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.996
                    df.loc[df.index[i], 'signal_type'] = 'momentum_short'
                    momentum_signals += 1

        if momentum_signals > 0:
            print(f"   Added {momentum_signals} momentum signals")

        return df

    def _apply_gold_entry_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Minimal filtering for ultra-aggressive strategy
        """
        df = df.copy()

        initial_signals = len(df[df['signal'] != 0])

        # Only filter out weekend (if needed)
        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            # Weekend filter only
            if df.index[i].weekday() >= 5:
                df.loc[df.index[i], 'signal'] = 0
                df.loc[df.index[i], 'filter_reason'] = 'weekend'

        final_signals = len(df[df['signal'] != 0])
        filtered_out = initial_signals - final_signals

        print(f"   Filtered out {filtered_out} signals ({initial_signals} → {final_signals})")

        return df

    def get_strategy_info(self) -> dict:
        """Get strategy info"""
        return {
            'strategy_type': 'Ultra-Aggressive Intraday',
            'timeframe': '1H',
            'min_quality': self.min_candle_quality,
            'swing_length': self.swing_length,
            'target_signals_per_day': '1-3+',
            'pattern_types': ['OB', 'FVG', 'Breakout', 'PinBar', 'Engulfing', 'Momentum', 'BOS'],
            'filters': 'Minimal (weekend only)'
        }
