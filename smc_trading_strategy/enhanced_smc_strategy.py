"""
Enhanced SMC Trading Strategy with Multi-Timeframe Analysis
HTF for signals, LTF for entries with confirmation
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smc_indicators import SMCIndicators
from enhanced_indicators import EnhancedIndicators, DynamicRiskManagement
from multi_timeframe import MultiTimeframeData, LTFEntryConfirmation
from typing import Tuple


class EnhancedSMCStrategy:
    """Enhanced SMC Strategy with multi-timeframe analysis and improved filters"""

    def __init__(
        self,
        htf_multiplier: int = 4,
        risk_reward_ratio: float = 2.0,
        risk_per_trade: float = 0.02,
        swing_length: int = 10,
        use_ma_filter: bool = True,
        use_premium_discount: bool = True,
        use_volume_filter: bool = True,
        use_atr_stops: bool = True,
        confirmation_candles: int = 3
    ):
        """
        Initialize Enhanced SMC Strategy

        Args:
            htf_multiplier: Multiplier for HTF (e.g., 4 = 4x base timeframe)
            risk_reward_ratio: Base risk/reward ratio
            risk_per_trade: Risk per trade as fraction of capital
            swing_length: Length for swing detection
            use_ma_filter: Use MA trend filter
            use_premium_discount: Use premium/discount zones
            use_volume_filter: Use volume confirmation
            use_atr_stops: Use ATR-based stops
            confirmation_candles: Number of LTF candles for confirmation
        """
        self.htf_multiplier = htf_multiplier
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade = risk_per_trade
        self.swing_length = swing_length
        self.use_ma_filter = use_ma_filter
        self.use_premium_discount = use_premium_discount
        self.use_volume_filter = use_volume_filter
        self.use_atr_stops = use_atr_stops

        # Initialize components
        self.smc = SMCIndicators(swing_length=swing_length)
        self.enhanced = EnhancedIndicators()
        self.risk_mgmt = DynamicRiskManagement()
        self.mtf = MultiTimeframeData(htf_multiplier=htf_multiplier)
        self.ltf_confirm = LTFEntryConfirmation(confirmation_candles=confirmation_candles)

    def prepare_htf_data(self, df_ltf: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare HTF data with SMC indicators

        Args:
            df_ltf: LTF DataFrame

        Returns:
            HTF DataFrame with indicators
        """
        # Resample to HTF
        df_htf = self.mtf.resample_to_htf(df_ltf)

        # Apply SMC indicators on HTF
        df_htf = self.smc.apply_all_indicators(df_htf)

        # Apply enhanced indicators on HTF
        df_htf = self.enhanced.apply_all_enhanced_indicators(df_htf)

        return df_htf

    def prepare_ltf_data(self, df_ltf: pd.DataFrame, df_htf: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare LTF data with HTF context

        Args:
            df_ltf: LTF DataFrame
            df_htf: HTF DataFrame with indicators

        Returns:
            LTF DataFrame with HTF context and own indicators
        """
        # Apply enhanced indicators on LTF
        df_ltf = self.enhanced.apply_all_enhanced_indicators(df_ltf)

        # Add HTF context to LTF
        df_ltf = self.mtf.get_htf_context(df_ltf, df_htf)

        return df_ltf

    def check_htf_signal(self, df_htf: pd.DataFrame, idx: int) -> Tuple[int, str]:
        """
        Check for HTF signal

        Args:
            df_htf: HTF DataFrame
            idx: Current index

        Returns:
            (signal, reason) - signal: 1=long, -1=short, 0=none
        """
        if idx < 20:
            return 0, "Insufficient data"

        row = df_htf.iloc[idx]

        # Long conditions on HTF
        long_conditions = []
        if row['trend'] == 1:  # Bullish market structure
            long_conditions.append('bullish_structure')

            # MA filter
            if self.use_ma_filter and row['ma_trend'] == 1:
                long_conditions.append('ma_bullish')

            # Premium/Discount filter (only buy in discount)
            if self.use_premium_discount and row['in_discount']:
                long_conditions.append('discount_zone')

            # Order Block or FVG
            if row['bullish_ob'] or row['bullish_fvg']:
                long_conditions.append('ob_or_fvg')

            # RSI not overbought
            if not row['rsi_overbought']:
                long_conditions.append('rsi_ok')

        # Short conditions on HTF
        short_conditions = []
        if row['trend'] == -1:  # Bearish market structure
            short_conditions.append('bearish_structure')

            # MA filter
            if self.use_ma_filter and row['ma_trend'] == -1:
                short_conditions.append('ma_bearish')

            # Premium/Discount filter (only sell in premium)
            if self.use_premium_discount and row['in_premium']:
                short_conditions.append('premium_zone')

            # Order Block or FVG
            if row['bearish_ob'] or row['bearish_fvg']:
                short_conditions.append('ob_or_fvg')

            # RSI not oversold
            if not row['rsi_oversold']:
                short_conditions.append('rsi_ok')

        # Require minimum conditions (relaxed to 2 for more signals)
        if len(long_conditions) >= 2:
            return 1, f"Long: {', '.join(long_conditions)}"
        elif len(short_conditions) >= 2:
            return -1, f"Short: {', '.join(short_conditions)}"
        else:
            return 0, "Conditions not met"

    def generate_signals(self, df_ltf: pd.DataFrame, df_htf: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals on LTF based on HTF signals

        Args:
            df_ltf: LTF DataFrame with HTF context
            df_htf: HTF DataFrame

        Returns:
            LTF DataFrame with signals
        """
        df_ltf = df_ltf.copy()
        df_ltf['signal'] = 0
        df_ltf['entry_price'] = np.nan
        df_ltf['stop_loss'] = np.nan
        df_ltf['take_profit'] = np.nan
        df_ltf['entry_quality'] = 0
        df_ltf['signal_reason'] = ''

        # Map HTF indices to LTF for checking HTF signals
        htf_idx = 0

        for i in range(50, len(df_ltf)):
            current_time = df_ltf.index[i]

            # Find corresponding HTF candle
            htf_idx = df_htf.index.searchsorted(current_time, side='right') - 1
            if htf_idx < 0 or htf_idx >= len(df_htf):
                continue

            # Check HTF signal
            htf_signal, htf_reason = self.check_htf_signal(df_htf, htf_idx)

            if htf_signal == 0:
                continue

            # HTF signal exists, now check LTF confirmation
            direction = 'long' if htf_signal == 1 else 'short'
            ltf_confirmed, ltf_details = self.ltf_confirm.confirm_ltf_entry(df_ltf, i, direction)

            if not ltf_confirmed:
                continue

            # Volume filter
            if self.use_volume_filter:
                if not df_ltf['high_volume'].iloc[i]:
                    continue

            # Entry confirmed on LTF!
            entry_price = df_ltf['close'].iloc[i]

            # Calculate stop loss
            if self.use_atr_stops:
                stop_loss = self.risk_mgmt.calculate_atr_stop_loss(
                    df_ltf, i, htf_signal, atr_multiplier=1.5
                )
            else:
                # Use traditional SMC stops
                if htf_signal == 1:
                    # Long: stop below recent swing low
                    recent_lows = df_ltf[df_ltf['htf_swing_low']].iloc[max(0, i-20):i]
                    if len(recent_lows) > 0:
                        stop_loss = recent_lows['low'].min()
                    else:
                        stop_loss = df_ltf['low'].iloc[max(0, i-10):i].min()
                else:
                    # Short: stop above recent swing high
                    recent_highs = df_ltf[df_ltf['htf_swing_high']].iloc[max(0, i-20):i]
                    if len(recent_highs) > 0:
                        stop_loss = recent_highs['high'].max()
                    else:
                        stop_loss = df_ltf['high'].iloc[max(0, i-10):i].max()

            # Calculate dynamic R:R ratio
            rr_ratio = self.risk_mgmt.calculate_dynamic_rr_ratio(
                df_ltf, i, self.risk_reward_ratio
            )

            # Calculate take profit
            risk = abs(entry_price - stop_loss)
            if risk > 0:
                if htf_signal == 1:
                    take_profit = entry_price + (risk * rr_ratio)
                else:
                    take_profit = entry_price - (risk * rr_ratio)

                # Record signal
                df_ltf.loc[df_ltf.index[i], 'signal'] = htf_signal
                df_ltf.loc[df_ltf.index[i], 'entry_price'] = entry_price
                df_ltf.loc[df_ltf.index[i], 'stop_loss'] = stop_loss
                df_ltf.loc[df_ltf.index[i], 'take_profit'] = take_profit
                df_ltf.loc[df_ltf.index[i], 'entry_quality'] = ltf_details['entry_quality']
                df_ltf.loc[df_ltf.index[i], 'signal_reason'] = htf_reason

        return df_ltf

    def run_strategy(self, df_ltf: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run complete enhanced SMC strategy

        Args:
            df_ltf: LTF DataFrame with OHLC data

        Returns:
            (df_ltf_with_signals, df_htf)
        """
        # Prepare HTF data
        df_htf = self.prepare_htf_data(df_ltf)

        # Prepare LTF data with HTF context
        df_ltf = self.prepare_ltf_data(df_ltf, df_htf)

        # Generate signals
        df_ltf = self.generate_signals(df_ltf, df_htf)

        return df_ltf, df_htf
