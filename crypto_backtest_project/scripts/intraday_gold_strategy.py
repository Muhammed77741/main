"""
Intraday Gold Strategy
Optimized for 1H timeframe to generate 1+ signals per day
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gold_optimized_smc_strategy import GoldOptimizedSMCStrategy
from smc_indicators import SMCIndicators


class IntradayGoldStrategy(GoldOptimizedSMCStrategy):
    """
    Intraday gold strategy for 1H timeframe

    Target: 1+ signals per day (30+ signals per month)

    Key differences from daily strategy:
    - Much lower quality threshold (25 vs 40)
    - Shorter swing length (5 vs 12)
    - No round number avoidance (too restrictive)
    - Faster entry/exit (1.5-2.0 R:R vs 2.5)
    - Trade during best hours only (London/NY overlap)
    """

    def __init__(
        self,
        risk_reward_ratio=1.8,       # Lower R:R for intraday
        swing_length=5,               # Much shorter swings
        volume_lookback=1,            # Less strict
        min_candle_quality=25,        # Much lower threshold
        trade_active_sessions_only=True,
        avoid_round_numbers=False,    # Too restrictive for intraday
        use_adaptive_rr=True,
        min_range_quality=0.15,       # Lower quality threshold
        use_sr_levels=True,
        best_hours_only=True          # Only 8-10, 13-15 GMT
    ):
        # Initialize parent
        super().__init__(
            risk_reward_ratio=risk_reward_ratio,
            swing_length=swing_length,
            volume_lookback=volume_lookback,
            min_candle_quality=min_candle_quality,
            trade_active_sessions_only=trade_active_sessions_only,
            avoid_round_numbers=avoid_round_numbers,
            use_adaptive_rr=use_adaptive_rr,
            min_range_quality=min_range_quality,
            use_sr_levels=use_sr_levels
        )

        self.best_hours_only = best_hours_only

        print(f"\n⚡ Intraday Gold Strategy Initialized")
        print(f"   Target: 1+ signals per day")
        print(f"   Timeframe: 1H")
        print(f"   Min Quality: {min_candle_quality} (aggressive)")
        print(f"   Swing Length: {swing_length} (fast)")
        print(f"   R:R: {risk_reward_ratio} (intraday)")
        print(f"   Best Hours Only: {best_hours_only}")

    def _apply_gold_entry_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply intraday-specific entry filters
        Less restrictive than daily strategy
        """
        df = df.copy()

        initial_signals = len(df[df['signal'] != 0])

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            # Filter 1: Best hours only (if enabled)
            if self.best_hours_only:
                hour = df.index[i].hour
                # Best hours: 8-10 (London), 13-15 (Overlap)
                best_hours = [8, 9, 10, 13, 14, 15]
                if hour not in best_hours:
                    df.loc[df.index[i], 'signal'] = 0
                    df.loc[df.index[i], 'filter_reason'] = 'outside_best_hours'
                    continue

            # Filter 2: Active session (less strict than daily)
            if self.trade_active_sessions_only:
                if not df['is_active_session'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = 0
                    df.loc[df.index[i], 'filter_reason'] = 'inactive_session'
                    continue

            # Filter 3: Range quality (much lower threshold)
            if df['in_range'].iloc[i]:
                range_quality = df['range_quality'].iloc[i]
                if range_quality < self.min_range_quality:
                    df.loc[df.index[i], 'signal'] = 0
                    df.loc[df.index[i], 'filter_reason'] = 'poor_range_quality'
                    continue

        final_signals = len(df[df['signal'] != 0])
        filtered_out = initial_signals - final_signals

        print(f"   Filtered out {filtered_out} signals ({initial_signals} → {final_signals})")

        return df

    def _adjust_gold_exits(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adjust SL/TP for intraday trading
        Tighter stops, faster targets
        """
        df = df.copy()

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            entry_price = df['entry_price'].iloc[i]
            stop_loss = df['stop_loss'].iloc[i]

            if pd.isna(entry_price) or pd.isna(stop_loss):
                continue

            # Calculate risk
            risk = abs(entry_price - stop_loss)

            # Intraday adaptive R:R (lower than daily)
            if self.use_adaptive_rr:
                volatility_state = df['volatility_state'].iloc[i] if 'volatility_state' in df.columns else 'medium'

                if volatility_state == 'low':
                    rr_ratio = 2.0  # Higher for intraday low vol
                elif volatility_state == 'high':
                    rr_ratio = 1.5  # Lower for intraday high vol
                else:
                    rr_ratio = 1.8  # Standard intraday
            else:
                rr_ratio = self.risk_reward_ratio

            # Calculate TP
            if df['signal'].iloc[i] == 1:  # Long
                take_profit = entry_price + (risk * rr_ratio)

                # S/R awareness (less strict)
                if self.use_sr_levels and 'recent_resistance' in df.columns:
                    if not pd.isna(df['recent_resistance'].iloc[i]):
                        resistance = df['recent_resistance'].iloc[i]
                        if resistance < take_profit and resistance > entry_price:
                            take_profit = resistance * 0.998  # 0.2% before
            else:  # Short
                take_profit = entry_price - (risk * rr_ratio)

                if self.use_sr_levels and 'recent_support' in df.columns:
                    if not pd.isna(df['recent_support'].iloc[i]):
                        support = df['recent_support'].iloc[i]
                        if support > take_profit and support < entry_price:
                            take_profit = support * 1.002  # 0.2% before

            df.loc[df.index[i], 'take_profit'] = take_profit
            df.loc[df.index[i], 'rr_ratio'] = rr_ratio

        return df

    def get_strategy_info(self) -> dict:
        """Get strategy info"""
        info = super().get_strategy_info()

        info.update({
            'strategy_type': 'Intraday Gold (1H)',
            'target_signals_per_day': '1-3',
            'timeframe': '1H',
            'best_hours_only': self.best_hours_only
        })

        return info


class IntradayGoldScalper(IntradayGoldStrategy):
    """
    Ultra-aggressive scalping version
    Target: 2-5 signals per day
    """

    def __init__(self):
        super().__init__(
            risk_reward_ratio=1.5,      # Even lower R:R
            swing_length=3,             # Very short swings
            volume_lookback=1,
            min_candle_quality=20,      # Very low threshold
            trade_active_sessions_only=True,
            avoid_round_numbers=False,
            use_adaptive_rr=False,      # Fixed R:R for speed
            min_range_quality=0.1,
            best_hours_only=False       # All active hours
        )

        print(f"   Mode: SCALPER (2-5 signals/day)")


class IntradayGoldConservative(IntradayGoldStrategy):
    """
    Conservative intraday version
    Target: 0.5-1 signals per day (best setups only)
    """

    def __init__(self):
        super().__init__(
            risk_reward_ratio=2.2,      # Higher R:R
            swing_length=7,             # Longer swings
            volume_lookback=2,          # More strict
            min_candle_quality=35,      # Higher threshold
            trade_active_sessions_only=True,
            avoid_round_numbers=True,   # Avoid round numbers
            use_adaptive_rr=True,
            min_range_quality=0.25,
            best_hours_only=True        # Only best hours
        )

        print(f"   Mode: CONSERVATIVE (0.5-1 signals/day)")


class MultiSignalGoldStrategy(IntradayGoldStrategy):
    """
    Enhanced intraday strategy with multiple signal types
    Combines OB, FVG, Liquidity Sweeps, and BOS
    """

    def __init__(self):
        super().__init__(
            risk_reward_ratio=1.8,
            swing_length=5,
            volume_lookback=1,
            min_candle_quality=25,
            best_hours_only=True
        )

        self.smc = SMCIndicators()
        print(f"   Mode: MULTI-SIGNAL (OB+FVG+Liquidity+BOS)")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run strategy with multiple signal types
        """
        # Run base strategy first
        df = super().run_strategy(df)

        # Add additional signals from liquidity sweeps
        df = self._add_liquidity_sweep_signals(df)

        # Add BOS-based signals
        df = self._add_bos_signals(df)

        return df

    def _add_liquidity_sweep_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add signals based on liquidity sweeps
        When price sweeps liquidity zones and reverses
        """
        df = df.copy()

        liquidity_signals = 0

        for i in range(10, len(df)):
            # Skip if already have signal
            if df['signal'].iloc[i] != 0:
                continue

            # Check for bullish liquidity sweep
            if 'liquidity_low' in df.columns and df['liquidity_low'].iloc[i]:
                # Price swept low and closed higher
                if df['close'].iloc[i] > df['open'].iloc[i]:
                    # Confirm with volume
                    if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.2:
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                        df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i] * 0.9995
                        df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.003
                        df.loc[df.index[i], 'signal_type'] = 'liquidity_sweep_long'
                        liquidity_signals += 1

            # Check for bearish liquidity sweep
            if 'liquidity_high' in df.columns and df['liquidity_high'].iloc[i]:
                if df['close'].iloc[i] < df['open'].iloc[i]:
                    if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.2:
                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                        df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i] * 1.0005
                        df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.997
                        df.loc[df.index[i], 'signal_type'] = 'liquidity_sweep_short'
                        liquidity_signals += 1

        if liquidity_signals > 0:
            print(f"   Added {liquidity_signals} liquidity sweep signals")

        return df

    def _add_bos_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add signals based on Break of Structure (BOS)
        """
        df = df.copy()

        bos_signals = 0

        for i in range(20, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            # Bullish BOS: price breaks above recent high
            recent_high = df['high'].iloc[i-20:i-1].max()
            if df['close'].iloc[i] > recent_high:
                # Confirm structure break
                if df['close'].iloc[i] > df['open'].iloc[i]:  # Bullish close
                    # Check volume confirmation
                    if df['volume'].iloc[i] > df['volume'].iloc[i-10:i].mean() * 1.3:
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                        df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i-3:i].min() * 0.9995
                        df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.004
                        df.loc[df.index[i], 'signal_type'] = 'bos_long'
                        bos_signals += 1

            # Bearish BOS: price breaks below recent low
            recent_low = df['low'].iloc[i-20:i-1].min()
            if df['close'].iloc[i] < recent_low:
                if df['close'].iloc[i] < df['open'].iloc[i]:  # Bearish close
                    if df['volume'].iloc[i] > df['volume'].iloc[i-10:i].mean() * 1.3:
                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                        df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i-3:i].max() * 1.0005
                        df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.996
                        df.loc[df.index[i], 'signal_type'] = 'bos_short'
                        bos_signals += 1

        if bos_signals > 0:
            print(f"   Added {bos_signals} BOS signals")

        return df
