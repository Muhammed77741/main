"""
Gold-Optimized SMC Strategy
Combines Simplified SMC with Gold-Specific Filters
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simplified_smc_strategy import SimplifiedSMCStrategy
from gold_specific_filters import GoldSpecificFilters, GoldVolatilityAnalyzer


class GoldOptimizedSMCStrategy(SimplifiedSMCStrategy):
    """
    Gold-optimized SMC strategy with:
    - Session time filtering (London/NY overlap best)
    - Round number proximity awareness
    - Range vs Trend detection
    - Support/Resistance levels
    - Adaptive R:R based on gold volatility
    - Volume analysis from Simplified SMC
    """

    def __init__(
        self,
        risk_reward_ratio=2.5,  # Higher R:R for gold (lower volatility)
        swing_length=12,         # Longer swings for gold
        volume_lookback=1,       # Less strict volume
        min_candle_quality=40,   # Lower threshold for gold
        trade_active_sessions_only=True,  # Only London/NY/Overlap
        avoid_round_numbers=True,          # Don't enter near psychological levels
        round_number_threshold=10.0,       # Distance from round numbers (USD)
        use_adaptive_rr=True,              # Adaptive R:R based on volatility
        min_range_quality=0.3,             # Minimum quality for range trading
        use_sr_levels=True                 # Use Support/Resistance
    ):
        # Initialize parent Simplified SMC
        super().__init__(
            risk_reward_ratio=risk_reward_ratio,
            swing_length=swing_length,
            volume_lookback=volume_lookback,
            min_candle_quality=min_candle_quality
        )

        # Gold-specific parameters
        self.trade_active_sessions_only = trade_active_sessions_only
        self.avoid_round_numbers = avoid_round_numbers
        self.round_number_threshold = round_number_threshold
        self.use_adaptive_rr = use_adaptive_rr
        self.min_range_quality = min_range_quality
        self.use_sr_levels = use_sr_levels

        # Initialize gold-specific analyzers
        self.gold_filters = GoldSpecificFilters()
        self.gold_volatility = GoldVolatilityAnalyzer()

        print(f"\n🏅 Gold-Optimized SMC Strategy Initialized")
        print(f"   Session Filter: {trade_active_sessions_only}")
        print(f"   Round Numbers: Avoid within {round_number_threshold}$")
        print(f"   Adaptive R:R: {use_adaptive_rr}")
        print(f"   Min Candle Quality: {min_candle_quality}")
        print(f"   Swing Length: {swing_length}")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run gold-optimized strategy

        Args:
            df: DataFrame with OHLCV

        Returns:
            DataFrame with signals and gold-specific filters
        """
        print(f"\n🔍 Running Gold-Optimized SMC Strategy...")
        print(f"   Data: {len(df)} candles")

        # Step 1: Apply gold-specific filters first
        print(f"\n1️⃣  Applying gold-specific filters...")
        df = self.gold_filters.apply_all_gold_filters(df)
        df = self.gold_volatility.calculate_gold_atr(df, period=14)

        # Step 2: Run base Simplified SMC strategy
        print(f"\n2️⃣  Running Simplified SMC core logic...")
        df = super().run_strategy(df)

        # Step 3: Apply gold-specific entry filters
        print(f"\n3️⃣  Applying gold entry filters...")
        df = self._apply_gold_entry_filters(df)

        # Step 4: Adjust stop loss and take profit for gold
        print(f"\n4️⃣  Adjusting SL/TP for gold characteristics...")
        df = self._adjust_gold_exits(df)

        # Count final signals
        buy_signals = len(df[df['signal'] == 1])
        sell_signals = len(df[df['signal'] == -1])
        total_signals = buy_signals + sell_signals

        print(f"\n✅ Gold-Optimized Strategy Complete")
        print(f"   Total Signals: {total_signals} (Buy: {buy_signals}, Sell: {sell_signals})")

        return df

    def _apply_gold_entry_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply gold-specific entry filters to existing signals

        Filters:
        1. Session time (only active sessions)
        2. Round number proximity (avoid entries near psychological levels)
        3. Range quality (avoid choppy markets)
        4. S/R proximity (bonus for entries near S/R)
        """
        df = df.copy()

        initial_signals = len(df[df['signal'] != 0])

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            # Filter 1: Session time
            if self.trade_active_sessions_only:
                if not df['is_active_session'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = 0
                    df.loc[df.index[i], 'filter_reason'] = 'inactive_session'
                    continue

            # Filter 2: Round number proximity
            if self.avoid_round_numbers:
                if df['near_round_number'].iloc[i]:
                    # Check if we're too close to a round number
                    distance = df['round_distance'].iloc[i]
                    if distance < self.round_number_threshold:
                        df.loc[df.index[i], 'signal'] = 0
                        df.loc[df.index[i], 'filter_reason'] = 'near_round_number'
                        continue

            # Filter 3: Range quality
            if df['in_range'].iloc[i]:
                range_quality = df['range_quality'].iloc[i]
                if range_quality < self.min_range_quality:
                    # Market is ranging but quality is poor (choppy)
                    df.loc[df.index[i], 'signal'] = 0
                    df.loc[df.index[i], 'filter_reason'] = 'poor_range_quality'
                    continue

        final_signals = len(df[df['signal'] != 0])
        filtered_out = initial_signals - final_signals

        print(f"   Filtered out {filtered_out} signals ({initial_signals} → {final_signals})")

        return df

    def _adjust_gold_exits(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adjust stop loss and take profit based on gold characteristics

        Adjustments:
        1. Adaptive R:R based on volatility state
        2. ATR-based stop loss (tighter for gold)
        3. Support/Resistance aware exits
        """
        df = df.copy()

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            entry_price = df['entry_price'].iloc[i]
            stop_loss = df['stop_loss'].iloc[i]

            if pd.isna(entry_price) or pd.isna(stop_loss):
                continue

            # Calculate risk per trade
            risk = abs(entry_price - stop_loss)

            # Adaptive R:R for gold
            if self.use_adaptive_rr:
                rr_ratio = self.gold_volatility.adaptive_rr_for_gold(df, i)
            else:
                rr_ratio = self.risk_reward_ratio

            # Calculate new take profit
            if df['signal'].iloc[i] == 1:  # Long
                take_profit = entry_price + (risk * rr_ratio)

                # Check if there's resistance above
                if self.use_sr_levels and 'recent_resistance' in df.columns:
                    if not pd.isna(df['recent_resistance'].iloc[i]):
                        resistance = df['recent_resistance'].iloc[i]
                        # Don't place TP beyond resistance
                        if resistance < take_profit and resistance > entry_price:
                            take_profit = resistance * 0.995  # 0.5% before resistance

            else:  # Short
                take_profit = entry_price - (risk * rr_ratio)

                # Check if there's support below
                if self.use_sr_levels and 'recent_support' in df.columns:
                    if not pd.isna(df['recent_support'].iloc[i]):
                        support = df['recent_support'].iloc[i]
                        # Don't place TP beyond support
                        if support > take_profit and support < entry_price:
                            take_profit = support * 1.005  # 0.5% before support

            df.loc[df.index[i], 'take_profit'] = take_profit
            df.loc[df.index[i], 'rr_ratio'] = rr_ratio

        return df

    def get_strategy_info(self) -> dict:
        """Get strategy configuration info"""
        info = super().get_strategy_info()

        info.update({
            'strategy_type': 'Gold-Optimized SMC',
            'session_filter': self.trade_active_sessions_only,
            'avoid_round_numbers': self.avoid_round_numbers,
            'round_threshold': self.round_number_threshold,
            'adaptive_rr': self.use_adaptive_rr,
            'min_range_quality': self.min_range_quality,
            'use_sr_levels': self.use_sr_levels
        })

        return info


class GoldOptimizedAggressiveStrategy(GoldOptimizedSMCStrategy):
    """
    More aggressive version for gold (more signals)
    Lower quality threshold, less filtering
    """

    def __init__(self):
        super().__init__(
            risk_reward_ratio=2.0,           # Lower R:R
            swing_length=10,                 # Shorter swings
            volume_lookback=1,               # Less strict
            min_candle_quality=35,           # Lower quality threshold
            trade_active_sessions_only=True,
            avoid_round_numbers=False,       # Don't avoid round numbers
            use_adaptive_rr=True,
            min_range_quality=0.2            # Lower range quality requirement
        )


class GoldOptimizedConservativeStrategy(GoldOptimizedSMCStrategy):
    """
    More conservative version for gold (fewer but higher quality signals)
    Higher quality threshold, more filtering
    """

    def __init__(self):
        super().__init__(
            risk_reward_ratio=3.0,           # Higher R:R
            swing_length=15,                 # Longer swings
            volume_lookback=2,               # More strict
            min_candle_quality=55,           # Higher quality threshold
            trade_active_sessions_only=True,
            avoid_round_numbers=True,        # Avoid round numbers
            round_number_threshold=15.0,     # Wider margin
            use_adaptive_rr=True,
            min_range_quality=0.5            # Higher range quality requirement
        )
