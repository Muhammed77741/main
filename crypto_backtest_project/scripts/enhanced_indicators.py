"""
Enhanced SMC Indicators with additional filters
Includes: MA filters, ATR, Premium/Discount zones, Confirmation patterns
"""

import pandas as pd
import numpy as np
from typing import Tuple


class EnhancedIndicators:
    """Enhanced technical indicators for SMC strategy"""

    def __init__(self):
        pass

    def calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate moving averages for trend filtering

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with MA columns
        """
        df = df.copy()

        # Exponential Moving Averages
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # MA Trend: 1 = bullish, -1 = bearish, 0 = neutral
        df['ma_trend'] = 0
        df.loc[df['ema_50'] > df['ema_200'], 'ma_trend'] = 1
        df.loc[df['ema_50'] < df['ema_200'], 'ma_trend'] = -1

        # Strong trend: price above/below all MAs
        df['strong_bullish'] = (df['close'] > df['ema_20']) & (df['ema_20'] > df['ema_50']) & (df['ema_50'] > df['ema_200'])
        df['strong_bearish'] = (df['close'] < df['ema_20']) & (df['ema_20'] < df['ema_50']) & (df['ema_50'] < df['ema_200'])

        return df

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Average True Range for volatility measurement

        Args:
            df: DataFrame with OHLC data
            period: ATR period

        Returns:
            DataFrame with ATR column
        """
        df = df.copy()

        # True Range
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

        # ATR
        df['atr'] = df['true_range'].rolling(window=period).mean()

        # ATR-based volatility state
        df['atr_ma'] = df['atr'].rolling(window=20).mean()
        df['high_volatility'] = df['atr'] > df['atr_ma'] * 1.2
        df['low_volatility'] = df['atr'] < df['atr_ma'] * 0.8

        # Clean up temporary columns
        df.drop(['tr1', 'tr2', 'tr3', 'true_range'], axis=1, inplace=True)

        return df

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Relative Strength Index

        Args:
            df: DataFrame with OHLC data
            period: RSI period

        Returns:
            DataFrame with RSI column
        """
        df = df.copy()

        # Calculate price changes
        delta = df['close'].diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gains and losses
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # RSI conditions
        df['rsi_overbought'] = df['rsi'] > 70
        df['rsi_oversold'] = df['rsi'] < 30
        df['rsi_bullish'] = (df['rsi'] > 50) & (df['rsi'] < 70)
        df['rsi_bearish'] = (df['rsi'] < 50) & (df['rsi'] > 30)

        return df

    def calculate_premium_discount_zones(self, df: pd.DataFrame, lookback: int = 50) -> pd.DataFrame:
        """
        Calculate Premium and Discount zones using Fibonacci

        Args:
            df: DataFrame with OHLC data
            lookback: Lookback period for swing high/low

        Returns:
            DataFrame with premium/discount zones
        """
        df = df.copy()

        # Calculate swing high and low over lookback period
        df['swing_high_price'] = df['high'].rolling(window=lookback).max()
        df['swing_low_price'] = df['low'].rolling(window=lookback).min()

        # Calculate range
        df['range'] = df['swing_high_price'] - df['swing_low_price']

        # Fibonacci levels
        df['fib_0'] = df['swing_low_price']  # 0% (support)
        df['fib_236'] = df['swing_low_price'] + (df['range'] * 0.236)
        df['fib_382'] = df['swing_low_price'] + (df['range'] * 0.382)
        df['fib_50'] = df['swing_low_price'] + (df['range'] * 0.5)  # Equilibrium
        df['fib_618'] = df['swing_low_price'] + (df['range'] * 0.618)
        df['fib_786'] = df['swing_low_price'] + (df['range'] * 0.786)
        df['fib_100'] = df['swing_high_price']  # 100% (resistance)

        # Determine if in premium or discount zone
        # Discount: Below 50% (good for longs)
        # Premium: Above 50% (good for shorts)
        # Equilibrium: Around 50% (avoid trading)

        df['in_discount'] = df['close'] < df['fib_50']
        df['in_premium'] = df['close'] > df['fib_50']
        df['in_equilibrium'] = (df['close'] >= df['fib_382']) & (df['close'] <= df['fib_618'])

        # Deep discount/premium (best zones)
        df['deep_discount'] = df['close'] < df['fib_382']
        df['deep_premium'] = df['close'] > df['fib_618']

        return df

    def detect_volume_confirmation(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        Detect volume confirmation for entries

        Args:
            df: DataFrame with OHLC and volume data
            period: Period for volume average

        Returns:
            DataFrame with volume confirmation
        """
        df = df.copy()

        # Volume moving average
        df['volume_ma'] = df['volume'].rolling(window=period).mean()

        # High volume (confirmation)
        df['high_volume'] = df['volume'] > df['volume_ma'] * 1.5

        # Volume trend (increasing = bullish, decreasing = bearish)
        df['volume_increasing'] = df['volume'] > df['volume'].shift(1)

        return df

    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD for trend confirmation

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with MACD columns
        """
        df = df.copy()

        # MACD calculation
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        # MACD signals
        df['macd_bullish'] = (df['macd'] > df['macd_signal']) & (df['macd'] > 0)
        df['macd_bearish'] = (df['macd'] < df['macd_signal']) & (df['macd'] < 0)

        # MACD crossovers
        df['macd_cross_up'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        df['macd_cross_down'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))

        return df

    def apply_all_enhanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all enhanced indicators to dataframe

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with all enhanced indicators
        """
        df = self.calculate_moving_averages(df)
        df = self.calculate_atr(df)
        df = self.calculate_rsi(df)
        df = self.calculate_premium_discount_zones(df)
        df = self.detect_volume_confirmation(df)
        df = self.calculate_macd(df)

        return df


class DynamicRiskManagement:
    """Dynamic risk management based on market conditions"""

    def __init__(self):
        pass

    def calculate_dynamic_rr_ratio(self, df: pd.DataFrame, idx: int, base_rr: float = 2.0) -> float:
        """
        Calculate dynamic Risk:Reward ratio based on volatility

        Args:
            df: DataFrame with indicators
            idx: Current index
            base_rr: Base risk:reward ratio

        Returns:
            Adjusted risk:reward ratio
        """
        if idx < 20:
            return base_rr

        # Adjust based on volatility
        if df['high_volatility'].iloc[idx]:
            # Lower R:R in high volatility (take profits faster)
            return base_rr * 0.75
        elif df['low_volatility'].iloc[idx]:
            # Higher R:R in low volatility (let winners run)
            return base_rr * 1.25
        else:
            return base_rr

    def calculate_atr_stop_loss(
        self,
        df: pd.DataFrame,
        idx: int,
        direction: int,
        atr_multiplier: float = 1.5
    ) -> float:
        """
        Calculate ATR-based stop loss

        Args:
            df: DataFrame with ATR
            idx: Current index
            direction: 1 for long, -1 for short
            atr_multiplier: ATR multiplier for stop distance

        Returns:
            Stop loss price
        """
        current_price = df['close'].iloc[idx]
        atr = df['atr'].iloc[idx]

        if pd.isna(atr) or atr == 0:
            # Fallback to percentage-based stop
            if direction == 1:
                return current_price * 0.98
            else:
                return current_price * 1.02

        # ATR-based stop
        if direction == 1:  # Long
            stop_loss = current_price - (atr * atr_multiplier)
        else:  # Short
            stop_loss = current_price + (atr * atr_multiplier)

        return stop_loss

    def calculate_position_size_with_atr(
        self,
        capital: float,
        entry_price: float,
        stop_loss: float,
        atr: float,
        risk_per_trade: float = 0.02
    ) -> float:
        """
        Calculate position size considering ATR volatility

        Args:
            capital: Available capital
            entry_price: Entry price
            stop_loss: Stop loss price
            atr: Current ATR
            risk_per_trade: Risk per trade as fraction

        Returns:
            Position size
        """
        risk_amount = capital * risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 0

        # Base position size
        position_size = risk_amount / risk_per_unit

        # Adjust for volatility (reduce size in high volatility)
        if entry_price > 0:
            volatility_pct = atr / entry_price
            if volatility_pct > 0.03:  # High volatility (>3%)
                position_size *= 0.7
            elif volatility_pct < 0.01:  # Low volatility (<1%)
                position_size *= 1.3

        return position_size
