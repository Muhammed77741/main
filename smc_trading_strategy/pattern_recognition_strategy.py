"""
Pattern Recognition Strategy - Wrapper for SimplifiedSMCStrategy with Fibonacci mode support
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simplified_smc_strategy import SimplifiedSMCStrategy


class PatternRecognitionStrategy:
    """
    Pattern Recognition Strategy that wraps SimplifiedSMCStrategy
    Supports different Fibonacci modes for entry/exit calculations
    """

    def __init__(
        self,
        fib_mode='standard',
        risk_reward_ratio: float = 2.0,
        risk_per_trade: float = 0.02,
        swing_length: int = 10,
        volume_lookback: int = 2,
        min_candle_quality: int = 50
    ):
        """
        Initialize Pattern Recognition Strategy

        Args:
            fib_mode: Fibonacci mode ('standard', '1.618', etc.)
            risk_reward_ratio: Risk/Reward ratio
            risk_per_trade: Risk per trade as fraction
            swing_length: Swing detection length
            volume_lookback: Candles to check for volume confirmation
            min_candle_quality: Minimum candle quality score (0-100)
        """
        self.fib_mode = fib_mode
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade = risk_per_trade
        self.swing_length = swing_length
        self.volume_lookback = volume_lookback
        self.min_candle_quality = min_candle_quality

        # Initialize underlying SMC strategy
        self.smc_strategy = SimplifiedSMCStrategy(
            risk_reward_ratio=risk_reward_ratio,
            risk_per_trade=risk_per_trade,
            swing_length=swing_length,
            volume_lookback=volume_lookback,
            min_candle_quality=min_candle_quality
        )

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run pattern recognition strategy

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with signals and trading levels
        """
        # Use the underlying SMC strategy to generate signals
        df_result = self.smc_strategy.generate_signals(df.copy())

        # Apply Fibonacci-based adjustments if needed
        if self.fib_mode == '1.618':
            df_result = self._apply_fibonacci_adjustments(df_result)

        return df_result

    def _apply_fibonacci_adjustments(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply Fibonacci-based adjustments to TP levels

        Args:
            df: DataFrame with signals

        Returns:
            DataFrame with adjusted TP levels
        """
        # Adjust TP levels based on Fibonacci ratios
        for i in range(len(df)):
            if df['signal'].iloc[i] != 0:
                entry_price = df['entry_price'].iloc[i]
                stop_loss = df['stop_loss'].iloc[i]
                
                if pd.notna(entry_price) and pd.notna(stop_loss):
                    # Calculate distance
                    distance = abs(entry_price - stop_loss)
                    
                    # Apply 1.618 Fibonacci extension
                    if df['signal'].iloc[i] == 1:  # LONG
                        df.loc[df.index[i], 'take_profit'] = entry_price + distance * 1.618
                    else:  # SHORT
                        df.loc[df.index[i], 'take_profit'] = entry_price - distance * 1.618

        return df
