"""
SMC + ICT + Price Action Combined Strategy
Combines Smart Money Concepts, Inner Circle Trader methodology, and Price Action

Key Components:
1. SMC: Order Blocks, FVG, BOS, Liquidity Sweeps
2. ICT: Killzones, Premium/Discount, Market Structure Shifts, Power of 3
3. Price Action: Market Structure, S/R, Volume, Candlestick Confluence
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy


class SMC_ICT_PA_Strategy(MultiSignalGoldStrategy):
    """
    Advanced combined strategy using SMC + ICT + Price Action

    ICT Killzones (GMT):
    - London Killzone: 02:00-05:00 (high probability)
    - New York Killzone: 07:00-10:00 (best)
    - Asian Killzone: 20:00-00:00 (lower quality)

    Premium/Discount:
    - Premium zone: Top 25% of range (sell bias)
    - Discount zone: Bottom 25% of range (buy bias)
    - Equilibrium: 40-60% (avoid)

    Market Structure:
    - HH, HL = Uptrend (buy bias)
    - LH, LL = Downtrend (sell bias)
    - Shift = Potential reversal
    """

    def __init__(self):
        super().__init__()

        # ICT Killzones (GMT)
        self.killzones = {
            'london': [2, 3, 4, 5],      # 02:00-05:00
            'ny': [7, 8, 9, 10],          # 07:00-10:00 (BEST)
            'asian': [20, 21, 22, 23, 0]  # 20:00-00:00
        }

        # Premium/Discount levels
        self.premium_threshold = 0.75   # Top 25%
        self.discount_threshold = 0.25  # Bottom 25%

        # Market structure
        self.structure_lookback = 20

        # Confluence requirements
        self.min_confluence_score = 3   # Need 3+ factors

        print(f"   Mode: SMC + ICT + PRICE ACTION")
        print(f"   Killzones: London (2-5), NY (7-10), Asian (20-0)")
        print(f"   Premium/Discount: 75%/25% of range")
        print(f"   Min Confluence: {self.min_confluence_score} factors")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run combined SMC + ICT + PA strategy
        """
        # Run base multi-signal strategy first
        df = super().run_strategy(df)

        # Add ICT indicators
        df = self._add_ict_indicators(df)

        # Add Price Action indicators
        df = self._add_price_action_indicators(df)

        # Calculate confluence scores
        df = self._calculate_confluence(df)

        # Apply advanced filters
        df = self._apply_advanced_filters(df)

        return df

    def _add_ict_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add ICT-specific indicators
        """
        df = df.copy()

        # 1. Killzone identification
        df['killzone'] = 'none'
        for i in range(len(df)):
            hour = df.index[i].hour
            if hour in self.killzones['ny']:
                df.loc[df.index[i], 'killzone'] = 'ny'
            elif hour in self.killzones['london']:
                df.loc[df.index[i], 'killzone'] = 'london'
            elif hour in self.killzones['asian']:
                df.loc[df.index[i], 'killzone'] = 'asian'

        # 2. Premium/Discount zones (last 20 candles range)
        df['premium_discount'] = 'equilibrium'

        for i in range(20, len(df)):
            recent_high = df['high'].iloc[i-20:i].max()
            recent_low = df['low'].iloc[i-20:i].min()
            range_size = recent_high - recent_low

            if range_size > 0:
                current_position = (df['close'].iloc[i] - recent_low) / range_size

                if current_position >= self.premium_threshold:
                    df.loc[df.index[i], 'premium_discount'] = 'premium'
                elif current_position <= self.discount_threshold:
                    df.loc[df.index[i], 'premium_discount'] = 'discount'

        # 3. Fair Value Gaps (already in base strategy, enhance it)
        df['fvg_strength'] = 0
        for i in range(2, len(df)):
            # Bullish FVG: gap between candle[i-2] high and candle[i] low
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                gap_size = df['low'].iloc[i] - df['high'].iloc[i-2]
                df.loc[df.index[i], 'fvg_strength'] = gap_size / df['close'].iloc[i] * 100
            # Bearish FVG
            elif df['high'].iloc[i] < df['low'].iloc[i-2]:
                gap_size = df['low'].iloc[i-2] - df['high'].iloc[i]
                df.loc[df.index[i], 'fvg_strength'] = -gap_size / df['close'].iloc[i] * 100

        return df

    def _add_price_action_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Price Action indicators
        """
        df = df.copy()

        # 1. Market Structure (HH, HL, LH, LL)
        df['market_structure'] = 'neutral'

        for i in range(self.structure_lookback * 2, len(df)):
            # Find recent swing highs and lows
            recent_highs = []
            recent_lows = []

            for j in range(i - self.structure_lookback * 2, i, self.structure_lookback):
                if j >= self.structure_lookback and j < len(df) - self.structure_lookback:
                    window = df['high'].iloc[j-self.structure_lookback:j+self.structure_lookback]
                    if df['high'].iloc[j] == window.max():
                        recent_highs.append(df['high'].iloc[j])

                    window = df['low'].iloc[j-self.structure_lookback:j+self.structure_lookback]
                    if df['low'].iloc[j] == window.min():
                        recent_lows.append(df['low'].iloc[j])

            # Determine structure
            if len(recent_highs) >= 2 and len(recent_lows) >= 2:
                # Higher Highs and Higher Lows = Uptrend
                if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
                    df.loc[df.index[i], 'market_structure'] = 'uptrend'
                # Lower Highs and Lower Lows = Downtrend
                elif recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
                    df.loc[df.index[i], 'market_structure'] = 'downtrend'

        # 2. Volume Profile (relative volume)
        df['volume_profile'] = 'average'
        for i in range(20, len(df)):
            avg_volume = df['volume'].iloc[i-20:i].mean()
            current_volume = df['volume'].iloc[i]

            if current_volume > avg_volume * 1.5:
                df.loc[df.index[i], 'volume_profile'] = 'high'
            elif current_volume < avg_volume * 0.7:
                df.loc[df.index[i], 'volume_profile'] = 'low'

        # 3. Candlestick patterns (simple but effective)
        df['candle_pattern'] = 'none'

        for i in range(1, len(df)):
            open_p = df['open'].iloc[i]
            close = df['close'].iloc[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]

            body = abs(close - open_p)
            full_range = high - low

            if full_range == 0:
                continue

            # Strong bullish candle
            if close > open_p and body > full_range * 0.7:
                df.loc[df.index[i], 'candle_pattern'] = 'strong_bull'
            # Strong bearish candle
            elif close < open_p and body > full_range * 0.7:
                df.loc[df.index[i], 'candle_pattern'] = 'strong_bear'

        return df

    def _calculate_confluence(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate confluence score for each signal
        Combines SMC + ICT + PA factors
        """
        df = df.copy()
        df['confluence_score'] = 0

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            score = 0
            signal_direction = df['signal'].iloc[i]  # 1 = long, -1 = short

            # Factor 1: Killzone (NY best, London good, Asian weak)
            killzone = df['killzone'].iloc[i]
            if killzone == 'ny':
                score += 2  # Best killzone
            elif killzone == 'london':
                score += 1

            # Factor 2: Premium/Discount alignment
            pd_zone = df['premium_discount'].iloc[i]
            if signal_direction == 1 and pd_zone == 'discount':  # Buy in discount
                score += 2
            elif signal_direction == -1 and pd_zone == 'premium':  # Sell in premium
                score += 2

            # Factor 3: Market Structure alignment
            structure = df['market_structure'].iloc[i]
            if signal_direction == 1 and structure == 'uptrend':
                score += 2
            elif signal_direction == -1 and structure == 'downtrend':
                score += 2

            # Factor 4: Volume confirmation
            volume = df['volume_profile'].iloc[i]
            if volume == 'high':
                score += 1

            # Factor 5: Candlestick pattern
            pattern = df['candle_pattern'].iloc[i]
            if signal_direction == 1 and pattern == 'strong_bull':
                score += 1
            elif signal_direction == -1 and pattern == 'strong_bear':
                score += 1

            # Factor 6: FVG strength
            fvg = df['fvg_strength'].iloc[i] if 'fvg_strength' in df.columns else 0
            if abs(fvg) > 0.1:  # Significant gap
                if (signal_direction == 1 and fvg > 0) or (signal_direction == -1 and fvg < 0):
                    score += 1

            df.loc[df.index[i], 'confluence_score'] = score

        return df

    def _apply_advanced_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply advanced filters based on confluence
        """
        df = df.copy()

        initial_signals = len(df[df['signal'] != 0])

        filtered_reasons = {
            'low_confluence': 0,
            'wrong_killzone': 0,
            'equilibrium': 0,
            'against_structure': 0
        }

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            # Filter 1: Minimum confluence score
            if df['confluence_score'].iloc[i] < self.min_confluence_score:
                df.loc[df.index[i], 'signal'] = 0
                filtered_reasons['low_confluence'] += 1
                continue

            # Filter 2: Avoid Asian killzone (lower quality)
            if df['killzone'].iloc[i] == 'asian':
                df.loc[df.index[i], 'signal'] = 0
                filtered_reasons['wrong_killzone'] += 1
                continue

            # Filter 3: Avoid equilibrium (no clear bias)
            if df['premium_discount'].iloc[i] == 'equilibrium':
                if df['confluence_score'].iloc[i] < 5:  # Unless very strong confluence
                    df.loc[df.index[i], 'signal'] = 0
                    filtered_reasons['equilibrium'] += 1
                    continue

            # Filter 4: Strong structure alignment required
            structure = df['market_structure'].iloc[i]
            signal_dir = df['signal'].iloc[i]

            if structure == 'uptrend' and signal_dir == -1:  # Short in uptrend
                if df['confluence_score'].iloc[i] < 6:  # Unless very strong
                    df.loc[df.index[i], 'signal'] = 0
                    filtered_reasons['against_structure'] += 1
                    continue
            elif structure == 'downtrend' and signal_dir == 1:  # Long in downtrend
                if df['confluence_score'].iloc[i] < 6:
                    df.loc[df.index[i], 'signal'] = 0
                    filtered_reasons['against_structure'] += 1
                    continue

        final_signals = len(df[df['signal'] != 0])
        total_filtered = initial_signals - final_signals

        print(f"\n   📊 SMC+ICT+PA Filters Applied:")
        print(f"   Total filtered: {total_filtered} signals ({initial_signals} → {final_signals})")
        print(f"   - Low confluence (<{self.min_confluence_score}): {filtered_reasons['low_confluence']}")
        print(f"   - Asian killzone: {filtered_reasons['wrong_killzone']}")
        print(f"   - Equilibrium zone: {filtered_reasons['equilibrium']}")
        print(f"   - Against structure: {filtered_reasons['against_structure']}")

        return df

    def get_strategy_info(self) -> dict:
        """Get strategy info"""
        return {
            'strategy_type': 'SMC + ICT + Price Action',
            'components': 'Smart Money + Inner Circle Trader + Price Action',
            'killzones': 'London (2-5), NY (7-10)',
            'min_confluence': self.min_confluence_score,
            'timeframe': '1H'
        }
