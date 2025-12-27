"""
SMC Trading Strategy
Entry rules based on Smart Money Concepts
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from smc_indicators import SMCIndicators


class SMCStrategy:
    """SMC Trading Strategy with improved entry and exit logic"""

    def __init__(
        self,
        risk_reward_ratio: float = 2.0,
        risk_per_trade: float = 0.02,  # 2% risk per trade
        use_order_blocks: bool = True,
        use_fvg: bool = True,
        use_liquidity: bool = True,
        swing_length: int = 10
    ):
        """
        Initialize SMC Strategy

        Args:
            risk_reward_ratio: Target reward to risk ratio
            risk_per_trade: Risk per trade as fraction of capital
            use_order_blocks: Use Order Blocks for entries
            use_fvg: Use Fair Value Gaps for entries
            use_liquidity: Use Liquidity zones for filtering
            swing_length: Swing detection length
        """
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade = risk_per_trade
        self.use_order_blocks = use_order_blocks
        self.use_fvg = use_fvg
        self.use_liquidity = use_liquidity

        self.smc = SMCIndicators(swing_length=swing_length)
        self.position = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on SMC concepts

        Args:
            df: DataFrame with SMC indicators

        Returns:
            DataFrame with signals
        """
        df = df.copy()
        df['signal'] = 0  # 1 = buy, -1 = sell, 0 = no signal
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan

        for i in range(20, len(df)):
            current_trend = df['trend'].iloc[i]

            # Long signal conditions
            if current_trend == 1:  # Bullish trend
                long_signal = False
                entry_price = df['close'].iloc[i]
                stop_loss = 0

                # Entry on Order Block
                if self.use_order_blocks and df['bullish_ob'].iloc[i-1:i].any():
                    long_signal = True
                    # Find most recent bullish OB
                    recent_obs = df[df['bullish_ob']].iloc[-5:]
                    if len(recent_obs) > 0 and not pd.isna(recent_obs['ob_bottom'].iloc[-1]):
                        stop_loss = recent_obs['ob_bottom'].iloc[-1]

                # Entry on FVG retest
                if self.use_fvg and not long_signal:
                    # Check if price retested bullish FVG
                    recent_fvg = df[df['bullish_fvg']].iloc[-10:]
                    if len(recent_fvg) > 0:
                        last_fvg_bottom = recent_fvg['fvg_bottom'].iloc[-1]
                        if df['low'].iloc[i] <= last_fvg_bottom <= df['high'].iloc[i]:
                            long_signal = True
                            stop_loss = last_fvg_bottom * 0.999

                # Check liquidity sweep (optional confirmation, not requirement)
                # Removed strict liquidity requirement to allow more signals

                # Calculate stop loss and take profit
                if long_signal and stop_loss == 0:
                    # Default stop loss: recent swing low
                    recent_lows = df[df['swing_low']].iloc[-5:]
                    if len(recent_lows) > 0:
                        stop_loss = recent_lows['low'].min()
                    else:
                        stop_loss = df['low'].iloc[i-10:i].min()

                if long_signal and stop_loss > 0:
                    risk = entry_price - stop_loss
                    if risk > 0:
                        take_profit = entry_price + (risk * self.risk_reward_ratio)

                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'entry_price'] = entry_price
                        df.loc[df.index[i], 'stop_loss'] = stop_loss
                        df.loc[df.index[i], 'take_profit'] = take_profit

            # Short signal conditions
            elif current_trend == -1:  # Bearish trend
                short_signal = False
                entry_price = df['close'].iloc[i]
                stop_loss = 0

                # Entry on Order Block
                if self.use_order_blocks and df['bearish_ob'].iloc[i-1:i].any():
                    short_signal = True
                    # Find most recent bearish OB
                    recent_obs = df[df['bearish_ob']].iloc[-5:]
                    if len(recent_obs) > 0 and not pd.isna(recent_obs['ob_top'].iloc[-1]):
                        stop_loss = recent_obs['ob_top'].iloc[-1]

                # Entry on FVG retest
                if self.use_fvg and not short_signal:
                    # Check if price retested bearish FVG
                    recent_fvg = df[df['bearish_fvg']].iloc[-10:]
                    if len(recent_fvg) > 0:
                        last_fvg_top = recent_fvg['fvg_top'].iloc[-1]
                        if df['low'].iloc[i] <= last_fvg_top <= df['high'].iloc[i]:
                            short_signal = True
                            stop_loss = last_fvg_top * 1.001

                # Check liquidity sweep (optional confirmation, not requirement)
                # Removed strict liquidity requirement to allow more signals

                # Calculate stop loss and take profit
                if short_signal and stop_loss == 0:
                    # Default stop loss: recent swing high
                    recent_highs = df[df['swing_high']].iloc[-5:]
                    if len(recent_highs) > 0:
                        stop_loss = recent_highs['high'].max()
                    else:
                        stop_loss = df['high'].iloc[i-10:i].max()

                if short_signal and stop_loss > 0:
                    risk = stop_loss - entry_price
                    if risk > 0:
                        take_profit = entry_price - (risk * self.risk_reward_ratio)

                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'entry_price'] = entry_price
                        df.loc[df.index[i], 'stop_loss'] = stop_loss
                        df.loc[df.index[i], 'take_profit'] = take_profit

        return df

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run complete SMC strategy

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with all indicators and signals
        """
        # Apply all SMC indicators
        df = self.smc.apply_all_indicators(df)

        # Generate trading signals
        df = self.generate_signals(df)

        return df
