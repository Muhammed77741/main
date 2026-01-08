"""
SMC (Smart Money Concepts) Indicators
Includes: Order Blocks, Fair Value Gaps, Break of Structure, Change of Character, Liquidity Zones
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict


class SMCIndicators:
    """Class for calculating Smart Money Concepts indicators"""

    def __init__(self, swing_length: int = 10):
        """
        Initialize SMC Indicators

        Args:
            swing_length: Number of candles to identify swing highs/lows
        """
        self.swing_length = swing_length

    def detect_swing_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect swing highs and swing lows

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with swing_high and swing_low columns
        """
        df = df.copy()
        df['swing_high'] = False
        df['swing_low'] = False

        for i in range(self.swing_length, len(df) - self.swing_length):
            # Swing High: highest high in the window
            if df['high'].iloc[i] == df['high'].iloc[i-self.swing_length:i+self.swing_length+1].max():
                df.loc[df.index[i], 'swing_high'] = True

            # Swing Low: lowest low in the window
            if df['low'].iloc[i] == df['low'].iloc[i-self.swing_length:i+self.swing_length+1].min():
                df.loc[df.index[i], 'swing_low'] = True

        return df

    def detect_market_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect market structure (Higher Highs, Higher Lows, Lower Highs, Lower Lows)

        Args:
            df: DataFrame with swing points

        Returns:
            DataFrame with market structure
        """
        df = df.copy()
        df['trend'] = 0  # 1 = bullish, -1 = bearish, 0 = neutral
        df['bos'] = False  # Break of Structure
        df['choch'] = False  # Change of Character

        swing_highs = df[df['swing_high']].copy()
        swing_lows = df[df['swing_low']].copy()

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return df

        current_trend = 0
        last_high = None
        last_low = None

        for i in range(len(df)):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            # Update last swing points
            if df['swing_high'].iloc[i]:
                if last_high is not None:
                    if current_high > last_high:
                        # Higher High
                        if current_trend == 1:
                            df.loc[df.index[i], 'bos'] = True  # BOS in uptrend
                        else:
                            df.loc[df.index[i], 'choch'] = True  # ChoCh to uptrend
                            current_trend = 1
                    else:
                        # Lower High
                        if current_trend == 1:
                            df.loc[df.index[i], 'choch'] = True  # ChoCh to downtrend
                            current_trend = -1
                last_high = current_high

            if df['swing_low'].iloc[i]:
                if last_low is not None:
                    if current_low < last_low:
                        # Lower Low
                        if current_trend == -1:
                            df.loc[df.index[i], 'bos'] = True  # BOS in downtrend
                        else:
                            df.loc[df.index[i], 'choch'] = True  # ChoCh to downtrend
                            current_trend = -1
                    else:
                        # Higher Low
                        if current_trend == -1:
                            df.loc[df.index[i], 'choch'] = True  # ChoCh to uptrend
                            current_trend = 1
                last_low = current_low

            df.loc[df.index[i], 'trend'] = current_trend

        return df

    def detect_order_blocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Order Blocks (OB)
        Order Block = Last bullish/bearish candle before strong move

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with order block zones
        """
        df = df.copy()
        df['bullish_ob'] = False
        df['bearish_ob'] = False
        df['ob_top'] = np.nan
        df['ob_bottom'] = np.nan

        threshold = 0.002  # 0.2% move threshold

        for i in range(1, len(df) - 1):
            # Bullish Order Block: bearish candle before bullish move
            if df['close'].iloc[i] < df['open'].iloc[i]:  # Bearish candle
                # Check if next candle makes strong bullish move
                next_move = (df['close'].iloc[i+1] - df['open'].iloc[i+1]) / df['open'].iloc[i+1]
                if next_move > threshold:
                    df.loc[df.index[i], 'bullish_ob'] = True
                    df.loc[df.index[i], 'ob_top'] = df['high'].iloc[i]
                    df.loc[df.index[i], 'ob_bottom'] = df['low'].iloc[i]

            # Bearish Order Block: bullish candle before bearish move
            if df['close'].iloc[i] > df['open'].iloc[i]:  # Bullish candle
                # Check if next candle makes strong bearish move
                next_move = (df['close'].iloc[i+1] - df['open'].iloc[i+1]) / df['open'].iloc[i+1]
                if next_move < -threshold:
                    df.loc[df.index[i], 'bearish_ob'] = True
                    df.loc[df.index[i], 'ob_top'] = df['high'].iloc[i]
                    df.loc[df.index[i], 'ob_bottom'] = df['low'].iloc[i]

        return df

    def detect_fair_value_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Fair Value Gaps (FVG)
        FVG = Gap between candle 1 high and candle 3 low (or vice versa)

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with FVG zones
        """
        df = df.copy()
        df['bullish_fvg'] = False
        df['bearish_fvg'] = False
        df['fvg_top'] = np.nan
        df['fvg_bottom'] = np.nan

        for i in range(2, len(df)):
            # Bullish FVG: gap up
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                gap_size = df['low'].iloc[i] - df['high'].iloc[i-2]
                if gap_size > 0:
                    df.loc[df.index[i], 'bullish_fvg'] = True
                    df.loc[df.index[i], 'fvg_top'] = df['low'].iloc[i]
                    df.loc[df.index[i], 'fvg_bottom'] = df['high'].iloc[i-2]

            # Bearish FVG: gap down
            if df['high'].iloc[i] < df['low'].iloc[i-2]:
                gap_size = df['low'].iloc[i-2] - df['high'].iloc[i]
                if gap_size > 0:
                    df.loc[df.index[i], 'bearish_fvg'] = True
                    df.loc[df.index[i], 'fvg_top'] = df['low'].iloc[i-2]
                    df.loc[df.index[i], 'fvg_bottom'] = df['high'].iloc[i]

        return df

    def detect_liquidity_zones(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect liquidity zones (equal highs/lows where stop losses accumulate)

        Args:
            df: DataFrame with swing points

        Returns:
            DataFrame with liquidity zones
        """
        df = df.copy()
        df['buy_side_liquidity'] = False
        df['sell_side_liquidity'] = False

        tolerance = 0.001  # 0.1% tolerance for "equal" levels

        swing_highs = df[df['swing_high']]['high'].values
        swing_lows = df[df['swing_low']]['low'].values

        # Buy-side liquidity: equal highs
        for i in range(len(df)):
            if df['swing_high'].iloc[i]:
                current_high = df['high'].iloc[i]
                # Check for equal highs within tolerance
                equal_highs = np.abs(swing_highs - current_high) / current_high < tolerance
                if np.sum(equal_highs) >= 2:  # At least 2 equal highs
                    df.loc[df.index[i], 'buy_side_liquidity'] = True

        # Sell-side liquidity: equal lows
        for i in range(len(df)):
            if df['swing_low'].iloc[i]:
                current_low = df['low'].iloc[i]
                # Check for equal lows within tolerance
                equal_lows = np.abs(swing_lows - current_low) / current_low < tolerance
                if np.sum(equal_lows) >= 2:  # At least 2 equal lows
                    df.loc[df.index[i], 'sell_side_liquidity'] = True

        return df

    def apply_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all SMC indicators to the dataframe

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with all SMC indicators
        """
        df = self.detect_swing_points(df)
        df = self.detect_market_structure(df)
        df = self.detect_order_blocks(df)
        df = self.detect_fair_value_gaps(df)
        df = self.detect_liquidity_zones(df)

        return df
