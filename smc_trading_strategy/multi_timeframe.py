"""
Multi-Timeframe Analysis for SMC Strategy
HTF (Higher TimeFrame) for signals, LTF (Lower TimeFrame) for entries
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict


class MultiTimeframeData:
    """Handle multiple timeframe data"""

    def __init__(self, htf_multiplier: int = 4):
        """
        Initialize multi-timeframe handler

        Args:
            htf_multiplier: Multiplier for higher timeframe (e.g., 4 means 4x the base timeframe)
        """
        self.htf_multiplier = htf_multiplier

    def resample_to_htf(self, df_ltf: pd.DataFrame) -> pd.DataFrame:
        """
        Resample LTF data to HTF

        Args:
            df_ltf: Lower timeframe DataFrame

        Returns:
            Higher timeframe DataFrame
        """
        # Create a resample rule based on multiplier
        # Assuming the base is hourly data
        resample_rule = f'{self.htf_multiplier}h'

        df_htf = df_ltf.resample(resample_rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        return df_htf

    def align_htf_to_ltf(self, df_ltf: pd.DataFrame, df_htf: pd.DataFrame, column: str) -> pd.Series:
        """
        Align HTF data to LTF by forward filling

        Args:
            df_ltf: Lower timeframe DataFrame
            df_htf: Higher timeframe DataFrame
            column: Column name to align

        Returns:
            Series with HTF data aligned to LTF index
        """
        # Reindex HTF to LTF and forward fill
        htf_aligned = df_htf[column].reindex(df_ltf.index, method='ffill')
        return htf_aligned

    def get_htf_context(self, df_ltf: pd.DataFrame, df_htf: pd.DataFrame) -> pd.DataFrame:
        """
        Add HTF context to LTF dataframe

        Args:
            df_ltf: Lower timeframe DataFrame
            df_htf: Higher timeframe DataFrame with signals

        Returns:
            LTF DataFrame with HTF context columns
        """
        df_ltf = df_ltf.copy()

        # Align important HTF columns to LTF
        htf_columns = ['trend', 'signal', 'bos', 'choch', 'bullish_ob', 'bearish_ob',
                      'bullish_fvg', 'bearish_fvg', 'swing_high', 'swing_low']

        for col in htf_columns:
            if col in df_htf.columns:
                df_ltf[f'htf_{col}'] = self.align_htf_to_ltf(df_ltf, df_htf, col)

        return df_ltf


class LTFEntryConfirmation:
    """Confirm entries on LTF based on HTF signals"""

    def __init__(self, confirmation_candles: int = 3):
        """
        Initialize LTF confirmation

        Args:
            confirmation_candles: Number of LTF candles to check for confirmation
        """
        self.confirmation_candles = confirmation_candles

    def check_bullish_confirmation_candle(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check if current candle is bullish confirmation

        Args:
            df: DataFrame with OHLC data
            idx: Current index

        Returns:
            True if bullish confirmation
        """
        if idx < 1:
            return False

        current = df.iloc[idx]
        previous = df.iloc[idx - 1]

        # Bullish confirmation candle criteria:
        # 1. Close > Open (bullish candle)
        # 2. Close > previous high (breaking above)
        # 3. Strong body (close - open > 50% of high - low)

        is_bullish = current['close'] > current['open']
        breaks_high = current['close'] > previous['high']

        body_size = abs(current['close'] - current['open'])
        candle_size = current['high'] - current['low']
        strong_body = body_size > (candle_size * 0.5) if candle_size > 0 else False

        return is_bullish and breaks_high and strong_body

    def check_bearish_confirmation_candle(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check if current candle is bearish confirmation

        Args:
            df: DataFrame with OHLC data
            idx: Current index

        Returns:
            True if bearish confirmation
        """
        if idx < 1:
            return False

        current = df.iloc[idx]
        previous = df.iloc[idx - 1]

        # Bearish confirmation candle criteria:
        # 1. Close < Open (bearish candle)
        # 2. Close < previous low (breaking below)
        # 3. Strong body (open - close > 50% of high - low)

        is_bearish = current['close'] < current['open']
        breaks_low = current['close'] < previous['low']

        body_size = abs(current['close'] - current['open'])
        candle_size = current['high'] - current['low']
        strong_body = body_size > (candle_size * 0.5) if candle_size > 0 else False

        return is_bearish and breaks_low and strong_body

    def check_ltf_bullish_structure(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check if recent LTF candles show bullish structure

        Args:
            df: DataFrame with OHLC data
            idx: Current index

        Returns:
            True if bullish structure confirmed
        """
        if idx < self.confirmation_candles:
            return False

        # Check last N candles
        recent_candles = df.iloc[idx - self.confirmation_candles + 1:idx + 1]

        # Count bullish vs bearish candles
        bullish_count = (recent_candles['close'] > recent_candles['open']).sum()

        # Check if making higher lows
        lows = recent_candles['low'].values
        higher_lows = all(lows[i] >= lows[i-1] * 0.998 for i in range(1, len(lows)))

        # Majority bullish candles + higher lows
        return (bullish_count >= self.confirmation_candles * 0.6) and higher_lows

    def check_ltf_bearish_structure(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check if recent LTF candles show bearish structure

        Args:
            df: DataFrame with OHLC data
            idx: Current index

        Returns:
            True if bearish structure confirmed
        """
        if idx < self.confirmation_candles:
            return False

        # Check last N candles
        recent_candles = df.iloc[idx - self.confirmation_candles + 1:idx + 1]

        # Count bearish vs bullish candles
        bearish_count = (recent_candles['close'] < recent_candles['open']).sum()

        # Check if making lower highs
        highs = recent_candles['high'].values
        lower_highs = all(highs[i] <= highs[i-1] * 1.002 for i in range(1, len(highs)))

        # Majority bearish candles + lower highs
        return (bearish_count >= self.confirmation_candles * 0.6) and lower_highs

    def confirm_ltf_entry(
        self,
        df: pd.DataFrame,
        idx: int,
        direction: str
    ) -> Tuple[bool, Dict]:
        """
        Confirm entry on LTF based on HTF signal

        Args:
            df: LTF DataFrame with HTF context
            idx: Current index
            direction: 'long' or 'short'

        Returns:
            (confirmed, details_dict)
        """
        details = {
            'confirmation_candle': False,
            'structure_confirmed': False,
            'entry_quality': 0  # 0-100 score
        }

        if direction == 'long':
            # Check for bullish confirmation
            details['confirmation_candle'] = self.check_bullish_confirmation_candle(df, idx)
            details['structure_confirmed'] = self.check_ltf_bullish_structure(df, idx)

        elif direction == 'short':
            # Check for bearish confirmation
            details['confirmation_candle'] = self.check_bearish_confirmation_candle(df, idx)
            details['structure_confirmed'] = self.check_ltf_bearish_structure(df, idx)

        # Calculate entry quality score
        score = 0
        if details['confirmation_candle']:
            score += 60
        if details['structure_confirmed']:
            score += 40

        details['entry_quality'] = score

        # Confirmed if score >= 60 (at least confirmation candle)
        confirmed = score >= 60

        return confirmed, details
