"""
Optimized Intraday Gold Strategy
Balanced approach: 1-2 signals per day with good win rate

Target: 1+ signals/day with 40-50% win rate and positive returns
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import IntradayGoldStrategy
from smc_indicators import SMCIndicators


class OptimizedIntradayGold(IntradayGoldStrategy):
    """
    Optimized balance between signal frequency and quality

    Features:
    - Min quality: 18 (low but not too low)
    - Multiple signal types (OB, FVG, Breakout, Engulfing)
    - Smart filtering (volume, trend confirmation)
    - Target: 1-2 signals/day with 40-50% WR
    """

    def __init__(self):
        super().__init__(
            risk_reward_ratio=1.7,
            swing_length=4,
            volume_lookback=0,
            min_candle_quality=18,       # Low but reasonable
            trade_active_sessions_only=True,   # Only active hours
            avoid_round_numbers=False,
            use_adaptive_rr=True,
            min_range_quality=0.1,
            best_hours_only=False        # All active hours
        )

        self.smc = SMCIndicators()
        print(f"   Mode: OPTIMIZED INTRADAY (1-2 signals/day, 40-50% WR)")
        print(f"   Quality: {self.min_candle_quality} (balanced)")
        print(f"   Patterns: OB+FVG+Breakout+Engulfing (filtered)")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run optimized strategy with smart filtering
        """
        print(f"\n⚡ Running Optimized Intraday Strategy...")

        # Base SMC signals
        df = super().run_strategy(df)

        # Add high-quality breakout signals
        df = self._add_quality_breakouts(df)

        # Add engulfing patterns
        df = self._add_quality_engulfing(df)

        # Apply smart volume filter
        df = self._apply_volume_filter(df)

        final_signals = len(df[df['signal'] != 0])
        print(f"\n✅ Total signals: {final_signals}")

        return df

    def _add_quality_breakouts(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add breakouts but with better filtering
        Only strong breakouts with volume confirmation
        """
        df = df.copy()
        breakout_signals = 0

        lookback = 12  # Longer lookback for stronger levels

        for i in range(lookback + 5, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            # Bullish breakout
            recent_high = df['high'].iloc[i-lookback:i-1].max()
            breakout_strength = (df['close'].iloc[i] - recent_high) / recent_high

            # Strong breakout (>0.15% above high)
            if breakout_strength > 0.0015:
                # Volume must be significantly higher
                avg_volume = df['volume'].iloc[i-10:i].mean()
                if df['volume'].iloc[i] > avg_volume * 1.3:
                    # Bullish close
                    if df['close'].iloc[i] > df['open'].iloc[i]:
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                        df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i-3:i].min() * 0.9997
                        df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.0035
                        df.loc[df.index[i], 'signal_type'] = 'quality_breakout_long'
                        breakout_signals += 1

            # Bearish breakout
            recent_low = df['low'].iloc[i-lookback:i-1].min()
            breakout_strength = (recent_low - df['close'].iloc[i]) / recent_low

            if breakout_strength > 0.0015:
                avg_volume = df['volume'].iloc[i-10:i].mean()
                if df['volume'].iloc[i] > avg_volume * 1.3:
                    if df['close'].iloc[i] < df['open'].iloc[i]:
                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                        df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i-3:i].max() * 1.0003
                        df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.9965
                        df.loc[df.index[i], 'signal_type'] = 'quality_breakout_short'
                        breakout_signals += 1

        if breakout_signals > 0:
            print(f"   Added {breakout_signals} quality breakout signals")

        return df

    def _add_quality_engulfing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add engulfing patterns with stricter filtering
        """
        df = df.copy()
        engulfing_signals = 0

        for i in range(10, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            curr_open = df['open'].iloc[i]
            curr_close = df['close'].iloc[i]
            curr_body = abs(curr_close - curr_open)

            prev_open = df['open'].iloc[i-1]
            prev_close = df['close'].iloc[i-1]
            prev_body = abs(prev_close - prev_open)

            # Require significant body (>0.1% of price)
            if curr_body / curr_close < 0.001:
                continue

            # Bullish engulfing
            if (curr_close > curr_open and
                prev_close < prev_open and
                curr_close > prev_open and
                curr_open < prev_close):

                # Body size check (current >> previous)
                if curr_body > prev_body * 1.3:
                    # Volume confirmation (current > previous)
                    if df['volume'].iloc[i] > df['volume'].iloc[i-1] * 1.1:
                        # Check trend (not in strong downtrend)
                        recent_trend = (df['close'].iloc[i-5:i].mean() - df['close'].iloc[i-10:i-5].mean()) / df['close'].iloc[i-10:i-5].mean()

                        if recent_trend > -0.01:  # Not strong downtrend
                            df.loc[df.index[i], 'signal'] = 1
                            df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                            df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i] * 0.9995
                            df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.004
                            df.loc[df.index[i], 'signal_type'] = 'quality_engulfing_long'
                            engulfing_signals += 1

            # Bearish engulfing
            if (curr_close < curr_open and
                prev_close > prev_open and
                curr_close < prev_open and
                curr_open > prev_close):

                if curr_body > prev_body * 1.3:
                    if df['volume'].iloc[i] > df['volume'].iloc[i-1] * 1.1:
                        recent_trend = (df['close'].iloc[i-5:i].mean() - df['close'].iloc[i-10:i-5].mean()) / df['close'].iloc[i-10:i-5].mean()

                        if recent_trend < 0.01:  # Not strong uptrend
                            df.loc[df.index[i], 'signal'] = -1
                            df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                            df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i] * 1.0005
                            df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.996
                            df.loc[df.index[i], 'signal_type'] = 'quality_engulfing_short'
                            engulfing_signals += 1

        if engulfing_signals > 0:
            print(f"   Added {engulfing_signals} quality engulfing signals")

        return df

    def _apply_volume_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter out signals with weak volume
        Keep only signals with decent volume
        """
        df = df.copy()

        initial_signals = len(df[df['signal'] != 0])
        filtered = 0

        for i in range(20, len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            # Calculate volume percentile
            recent_volumes = df['volume'].iloc[i-20:i+1]
            volume_percentile = (df['volume'].iloc[i] >= recent_volumes).sum() / len(recent_volumes)

            # Require at least 30th percentile (not bottom 30%)
            if volume_percentile < 0.30:
                df.loc[df.index[i], 'signal'] = 0
                df.loc[df.index[i], 'filter_reason'] = 'low_volume'
                filtered += 1

        final_signals = len(df[df['signal'] != 0])

        if filtered > 0:
            print(f"   Volume filter: removed {filtered} weak signals ({initial_signals} → {final_signals})")

        return df

    def _apply_gold_entry_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply moderate filtering for optimized strategy
        """
        df = df.copy()

        initial_signals = len(df[df['signal'] != 0])

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            # Filter 1: Active session only
            if self.trade_active_sessions_only:
                if not df['is_active_session'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = 0
                    df.loc[df.index[i], 'filter_reason'] = 'inactive_session'
                    continue

            # Filter 2: Weekend
            if df.index[i].weekday() >= 5:
                df.loc[df.index[i], 'signal'] = 0
                df.loc[df.index[i], 'filter_reason'] = 'weekend'
                continue

        final_signals = len(df[df['signal'] != 0])
        filtered_out = initial_signals - final_signals

        print(f"   Entry filters: removed {filtered_out} signals ({initial_signals} → {final_signals})")

        return df

    def get_strategy_info(self) -> dict:
        """Get strategy info"""
        return {
            'strategy_type': 'Optimized Intraday',
            'timeframe': '1H',
            'min_quality': self.min_candle_quality,
            'swing_length': self.swing_length,
            'target_signals_per_day': '1-2',
            'target_win_rate': '40-50%',
            'pattern_types': ['OB', 'FVG', 'Quality Breakout', 'Quality Engulfing'],
            'filters': ['Volume', 'Active Session', 'Weekend']
        }
