"""
Simplified SMC Strategy - Pure SMC без retail индикаторов
Фокус на: Market Structure + Order Blocks + FVG + Volume Analysis
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smc_indicators import SMCIndicators
from volume_analysis import VolumeAnalyzer
from typing import Dict


class SimplifiedSMCStrategy:
    """
    Упрощённая SMC стратегия без избыточных фильтров

    Правила:
    1. Market Structure (BOS/ChoCh) для определения тренда
    2. Order Block или FVG для зоны входа
    3. Volume confirmation на текущей свече
    4. Проверка 1-2 предыдущих свечей на импульс
    """

    def __init__(
        self,
        risk_reward_ratio: float = 2.0,
        risk_per_trade: float = 0.02,
        swing_length: int = 10,
        volume_lookback: int = 2,
        min_candle_quality: int = 50
    ):
        """
        Initialize Simplified SMC Strategy

        Args:
            risk_reward_ratio: Risk/Reward ratio
            risk_per_trade: Risk per trade as fraction
            swing_length: Swing detection length
            volume_lookback: Candles to check for volume confirmation
            min_candle_quality: Minimum candle quality score (0-100)
        """
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade = risk_per_trade
        self.swing_length = swing_length
        self.volume_lookback = volume_lookback
        self.min_candle_quality = min_candle_quality

        # Initialize components
        self.smc = SMCIndicators(swing_length=swing_length)
        self.volume_analyzer = VolumeAnalyzer(volume_ma_period=20)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on pure SMC + Volume

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with signals
        """
        df = df.copy()

        # Apply SMC indicators
        df = self.smc.apply_all_indicators(df)

        # Apply volume metrics
        df = self.volume_analyzer.calculate_volume_metrics(df)

        # Initialize signal columns
        df['signal'] = 0
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['candle_quality'] = 0
        df['signal_reason'] = ''

        # Generate signals
        for i in range(self.swing_length + 20, len(df)):
            # Get current trend from market structure
            current_trend = df['trend'].iloc[i]

            if current_trend == 0:
                continue

            # === LONG SIGNAL ===
            if current_trend == 1:
                long_signal, long_details = self._check_long_entry(df, i)

                if long_signal:
                    entry_price = df['close'].iloc[i]
                    stop_loss = self._calculate_stop_loss(df, i, direction=1)
                    take_profit = entry_price + (entry_price - stop_loss) * self.risk_reward_ratio

                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = entry_price
                    df.loc[df.index[i], 'stop_loss'] = stop_loss
                    df.loc[df.index[i], 'take_profit'] = take_profit
                    df.loc[df.index[i], 'candle_quality'] = long_details['candle_quality']
                    df.loc[df.index[i], 'signal_reason'] = long_details['reason']

            # === SHORT SIGNAL ===
            elif current_trend == -1:
                short_signal, short_details = self._check_short_entry(df, i)

                if short_signal:
                    entry_price = df['close'].iloc[i]
                    stop_loss = self._calculate_stop_loss(df, i, direction=-1)
                    take_profit = entry_price - (stop_loss - entry_price) * self.risk_reward_ratio

                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = entry_price
                    df.loc[df.index[i], 'stop_loss'] = stop_loss
                    df.loc[df.index[i], 'take_profit'] = take_profit
                    df.loc[df.index[i], 'candle_quality'] = short_details['candle_quality']
                    df.loc[df.index[i], 'signal_reason'] = short_details['reason']

        return df

    def _check_long_entry(self, df: pd.DataFrame, idx: int) -> tuple:
        """
        Check for long entry conditions

        Returns:
            (signal, details_dict)
        """
        conditions = []
        details = {'candle_quality': 0, 'reason': ''}

        # 1. Check for Order Block or FVG
        has_ob = False
        has_fvg = False

        # Recent bullish OB
        recent_obs = df['bullish_ob'].iloc[max(0, idx-10):idx+1]
        if recent_obs.any():
            has_ob = True
            conditions.append('Bullish_OB')

        # Recent bullish FVG
        recent_fvg = df['bullish_fvg'].iloc[max(0, idx-10):idx+1]
        if recent_fvg.any():
            has_fvg = True
            conditions.append('Bullish_FVG')

        if not (has_ob or has_fvg):
            return False, details

        # 2. Volume confirmation
        volume_confirmed, vol_details = self.volume_analyzer.check_volume_confirmation(
            df, idx, 'long', self.volume_lookback
        )

        if not volume_confirmed:
            return False, details

        conditions.append(f"Volume_OK({vol_details['volume_strength']})")
        details['candle_quality'] = vol_details['current_quality']

        # 3. Check candle quality
        if vol_details['current_quality'] < self.min_candle_quality:
            return False, details

        conditions.append(f"Quality_{vol_details['current_quality']}")

        # 4. Optional: Check for liquidity sweep
        if df['sell_side_liquidity'].iloc[max(0, idx-5):idx].any():
            conditions.append('Liquidity_Sweep')

        # 5. Check BOS (Break of Structure) - подтверждение продолжения
        if df['bos'].iloc[idx]:
            conditions.append('BOS')

        # Signal confirmed
        details['reason'] = ' + '.join(conditions)
        return True, details

    def _check_short_entry(self, df: pd.DataFrame, idx: int) -> tuple:
        """
        Check for short entry conditions

        Returns:
            (signal, details_dict)
        """
        conditions = []
        details = {'candle_quality': 0, 'reason': ''}

        # 1. Check for Order Block or FVG
        has_ob = False
        has_fvg = False

        # Recent bearish OB
        recent_obs = df['bearish_ob'].iloc[max(0, idx-10):idx+1]
        if recent_obs.any():
            has_ob = True
            conditions.append('Bearish_OB')

        # Recent bearish FVG
        recent_fvg = df['bearish_fvg'].iloc[max(0, idx-10):idx+1]
        if recent_fvg.any():
            has_fvg = True
            conditions.append('Bearish_FVG')

        if not (has_ob or has_fvg):
            return False, details

        # 2. Volume confirmation
        volume_confirmed, vol_details = self.volume_analyzer.check_volume_confirmation(
            df, idx, 'short', self.volume_lookback
        )

        if not volume_confirmed:
            return False, details

        conditions.append(f"Volume_OK({vol_details['volume_strength']})")
        details['candle_quality'] = vol_details['current_quality']

        # 3. Check candle quality
        if vol_details['current_quality'] < self.min_candle_quality:
            return False, details

        conditions.append(f"Quality_{vol_details['current_quality']}")

        # 4. Optional: Check for liquidity sweep
        if df['buy_side_liquidity'].iloc[max(0, idx-5):idx].any():
            conditions.append('Liquidity_Sweep')

        # 5. Check BOS
        if df['bos'].iloc[idx]:
            conditions.append('BOS')

        # Signal confirmed
        details['reason'] = ' + '.join(conditions)
        return True, details

    def _calculate_stop_loss(self, df: pd.DataFrame, idx: int, direction: int) -> float:
        """
        Calculate stop loss based on recent swing points

        Args:
            df: DataFrame
            idx: Current index
            direction: 1 for long, -1 for short

        Returns:
            Stop loss price
        """
        if direction == 1:  # Long
            # Stop below recent swing low
            recent_swings = df[df['swing_low']].iloc[max(0, idx-20):idx]
            if len(recent_swings) > 0:
                stop = recent_swings['low'].min()
            else:
                # Fallback: lowest low in last 10 candles
                stop = df['low'].iloc[max(0, idx-10):idx].min()

            # Add small buffer
            return stop * 0.998

        else:  # Short
            # Stop above recent swing high
            recent_swings = df[df['swing_high']].iloc[max(0, idx-20):idx]
            if len(recent_swings) > 0:
                stop = recent_swings['high'].max()
            else:
                # Fallback: highest high in last 10 candles
                stop = df['high'].iloc[max(0, idx-10):idx].max()

            # Add small buffer
            return stop * 1.002

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run complete simplified SMC strategy

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with signals
        """
        return self.generate_signals(df)
