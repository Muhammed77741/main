"""
Improved Original Strategy
Based on loss analysis - filters out weak signals
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy


class ImprovedOriginalStrategy(MultiSignalGoldStrategy):
    """
    Original Multi-Signal strategy with improvements from loss analysis

    Key Improvements:
    1. Avoid worst hours (20:00, 04:00, 12:00) - 50%+ loss rate
    2. Filter out signals without signal_type
    3. Stronger volume confirmation (>1.0x average)
    4. Trend alignment filter (SMA20)
    5. Avoid Tuesday if possible (highest loss rate)
    """

    def __init__(self):
        super().__init__()

        self.avoid_hours = [20, 4, 12]  # Worst hours from analysis
        self.min_volume_ratio = 1.0     # Require average+ volume
        self.use_trend_filter = True
        self.trend_sma_period = 20

        print(f"   Mode: IMPROVED ORIGINAL")
        print(f"   Improvements:")
        print(f"   - Avoid bad hours: {self.avoid_hours}")
        print(f"   - Min volume ratio: {self.min_volume_ratio}")
        print(f"   - Trend filter: {self.use_trend_filter}")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run improved strategy with additional filters
        """
        # Run base strategy
        df = super().run_strategy(df)

        # Add trend indicator
        df = self._add_trend_filter(df)

        # Apply improved filters
        df = self._apply_improved_filters(df)

        return df

    def _add_trend_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add trend indicator based on SMA
        """
        df = df.copy()

        # Calculate SMA20
        df['sma20'] = df['close'].rolling(window=self.trend_sma_period).mean()

        # Determine trend
        df['trend'] = 'neutral'
        df.loc[df['close'] > df['sma20'] * 1.002, 'trend'] = 'up'      # 0.2% above
        df.loc[df['close'] < df['sma20'] * 0.998, 'trend'] = 'down'    # 0.2% below

        return df

    def _apply_improved_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply improved filters based on loss analysis
        """
        df = df.copy()

        initial_signals = len(df[df['signal'] != 0])
        filtered_reasons = {
            'bad_hour': 0,
            'no_signal_type': 0,
            'low_volume': 0,
            'against_trend': 0,
            'tuesday': 0
        }

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            # Filter 1: Avoid worst hours
            hour = df.index[i].hour
            if hour in self.avoid_hours:
                df.loc[df.index[i], 'signal'] = 0
                filtered_reasons['bad_hour'] += 1
                continue

            # Filter 2: Require valid signal type (not NaN)
            signal_type = df['signal_type'].iloc[i] if 'signal_type' in df.columns else None
            if pd.isna(signal_type) or signal_type == '' or signal_type == 'nan':
                df.loc[df.index[i], 'signal'] = 0
                filtered_reasons['no_signal_type'] += 1
                continue

            # Filter 3: Volume confirmation
            if i >= 10:
                recent_volume = df['volume'].iloc[i-10:i].mean()
                current_volume = df['volume'].iloc[i]
                volume_ratio = current_volume / recent_volume if recent_volume > 0 else 1.0

                if volume_ratio < self.min_volume_ratio:
                    df.loc[df.index[i], 'signal'] = 0
                    filtered_reasons['low_volume'] += 1
                    continue

            # Filter 4: Trend alignment (if enabled)
            if self.use_trend_filter and 'trend' in df.columns:
                trend = df['trend'].iloc[i]
                signal = df['signal'].iloc[i]

                # Long should be in uptrend, short in downtrend
                if signal == 1 and trend == 'down':  # Long against downtrend
                    df.loc[df.index[i], 'signal'] = 0
                    filtered_reasons['against_trend'] += 1
                    continue
                elif signal == -1 and trend == 'up':  # Short against uptrend
                    df.loc[df.index[i], 'signal'] = 0
                    filtered_reasons['against_trend'] += 1
                    continue

            # Filter 5: Be cautious on Tuesday (optional - less strict)
            # Skip this for now, as it might filter too much

        final_signals = len(df[df['signal'] != 0])
        total_filtered = initial_signals - final_signals

        print(f"\n   📊 Improved Filters Applied:")
        print(f"   Total filtered: {total_filtered} signals ({initial_signals} → {final_signals})")
        print(f"   - Bad hours (20,04,12): {filtered_reasons['bad_hour']}")
        print(f"   - No signal type: {filtered_reasons['no_signal_type']}")
        print(f"   - Low volume: {filtered_reasons['low_volume']}")
        print(f"   - Against trend: {filtered_reasons['against_trend']}")

        return df

    def get_strategy_info(self) -> dict:
        """Get strategy info"""
        info = super().get_strategy_info()

        info.update({
            'strategy_type': 'Improved Original Multi-Signal',
            'improvements': [
                f'Avoid hours: {self.avoid_hours}',
                f'Min volume ratio: {self.min_volume_ratio}',
                'Trend filter enabled',
                'Filter out invalid signal types'
            ]
        })

        return info
