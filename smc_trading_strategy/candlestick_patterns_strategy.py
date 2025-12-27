"""
Candlestick Patterns Strategy
Focus on classic reversal patterns: Hammer, Shooting Star, Engulfing, etc.
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import IntradayGoldStrategy


class CandlestickPatternsStrategy(IntradayGoldStrategy):
    """
    Pure candlestick pattern recognition strategy

    Patterns:
    - Hammer (бычий молот)
    - Shooting Star (падающая звезда)
    - Engulfing (поглощение)
    - Morning Star / Evening Star
    - Doji at support/resistance
    """

    def __init__(self):
        super().__init__(
            risk_reward_ratio=2.0,  # Higher R:R for pattern trades
            swing_length=10,        # Look for swing points
            volume_lookback=2,
            min_candle_quality=30,
            best_hours_only=True
        )

        self.min_body_to_shadow_ratio = 0.3  # Body должно быть минимум 30% от всей свечи
        self.hammer_shadow_ratio = 2.5       # Нижняя тень в 2.5x больше тела
        self.star_shadow_ratio = 2.5         # Верхняя тень в 2.5x больше тела

        print(f"   Mode: CANDLESTICK PATTERNS")
        print(f"   Patterns: Hammer, Shooting Star, Engulfing, Morning/Evening Star, Doji")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run candlestick pattern strategy
        """
        df = df.copy()

        # Initialize signal columns
        df['signal'] = 0
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['signal_type'] = ''

        print(f"\n🕯️  Detecting Candlestick Patterns...")

        # Detect all patterns
        df = self._detect_hammer(df)
        df = self._detect_shooting_star(df)
        df = self._detect_engulfing(df)
        df = self._detect_morning_evening_star(df)
        df = self._detect_doji_reversal(df)

        # Apply filters
        df = self._apply_pattern_filters(df)

        total_signals = len(df[df['signal'] != 0])
        long_signals = len(df[df['signal'] == 1])
        short_signals = len(df[df['signal'] == -1])

        print(f"   Total Pattern Signals: {total_signals} (Long: {long_signals}, Short: {short_signals})")

        return df

    def _detect_hammer(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Hammer pattern (бычий молот)
        - Small body at top
        - Long lower shadow (2.5x+ body)
        - Little/no upper shadow
        - Forms at support/downtrend
        """
        df = df.copy()
        hammers = 0

        for i in range(20, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            open_price = df['open'].iloc[i]
            close = df['close'].iloc[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]

            body = abs(close - open_price)
            full_range = high - low
            lower_shadow = min(open_price, close) - low
            upper_shadow = high - max(open_price, close)

            # Hammer criteria
            if full_range == 0:
                continue

            body_ratio = body / full_range

            # Body should be small (< 30% of range)
            if body_ratio > 0.3:
                continue

            # Lower shadow should be long (> 2.5x body)
            if lower_shadow < body * self.hammer_shadow_ratio:
                continue

            # Upper shadow should be small
            if upper_shadow > body * 0.5:
                continue

            # Check if at support or downtrend
            recent_low = df['low'].iloc[i-20:i].min()
            if low > recent_low * 1.01:  # Not near support
                continue

            # Volume confirmation
            if df['volume'].iloc[i] < df['volume'].iloc[i-10:i].mean() * 0.8:
                continue

            # Set signal
            df.loc[df.index[i], 'signal'] = 1  # Long
            df.loc[df.index[i], 'entry_price'] = close
            df.loc[df.index[i], 'stop_loss'] = low * 0.9995
            df.loc[df.index[i], 'take_profit'] = close + (close - low) * 2.0
            df.loc[df.index[i], 'signal_type'] = 'hammer'
            hammers += 1

        if hammers > 0:
            print(f"   Found {hammers} Hammer patterns")

        return df

    def _detect_shooting_star(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Shooting Star (падающая звезда)
        - Small body at bottom
        - Long upper shadow (2.5x+ body)
        - Little/no lower shadow
        - Forms at resistance/uptrend
        """
        df = df.copy()
        stars = 0

        for i in range(20, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            open_price = df['open'].iloc[i]
            close = df['close'].iloc[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]

            body = abs(close - open_price)
            full_range = high - low
            lower_shadow = min(open_price, close) - low
            upper_shadow = high - max(open_price, close)

            if full_range == 0:
                continue

            body_ratio = body / full_range

            # Body should be small
            if body_ratio > 0.3:
                continue

            # Upper shadow should be long
            if upper_shadow < body * self.star_shadow_ratio:
                continue

            # Lower shadow should be small
            if lower_shadow > body * 0.5:
                continue

            # Check if at resistance or uptrend
            recent_high = df['high'].iloc[i-20:i].max()
            if high < recent_high * 0.99:  # Not near resistance
                continue

            # Volume confirmation
            if df['volume'].iloc[i] < df['volume'].iloc[i-10:i].mean() * 0.8:
                continue

            # Set signal
            df.loc[df.index[i], 'signal'] = -1  # Short
            df.loc[df.index[i], 'entry_price'] = close
            df.loc[df.index[i], 'stop_loss'] = high * 1.0005
            df.loc[df.index[i], 'take_profit'] = close - (high - close) * 2.0
            df.loc[df.index[i], 'signal_type'] = 'shooting_star'
            stars += 1

        if stars > 0:
            print(f"   Found {stars} Shooting Star patterns")

        return df

    def _detect_engulfing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Bullish/Bearish Engulfing patterns
        - Current candle completely engulfs previous candle
        """
        df = df.copy()
        engulfing = 0

        for i in range(20, len(df)-1):
            if df['signal'].iloc[i+1] != 0:
                continue

            # Previous candle
            prev_open = df['open'].iloc[i]
            prev_close = df['close'].iloc[i]
            prev_body = abs(prev_close - prev_open)

            # Current candle
            curr_open = df['open'].iloc[i+1]
            curr_close = df['close'].iloc[i+1]
            curr_body = abs(curr_close - curr_open)

            # Bullish Engulfing
            if prev_close < prev_open and curr_close > curr_open:  # Prev red, curr green
                if curr_open <= prev_close and curr_close >= prev_open:  # Engulfs
                    if curr_body > prev_body * 1.2:  # Significantly larger
                        # Volume confirmation
                        if df['volume'].iloc[i+1] > df['volume'].iloc[i] * 1.1:
                            df.loc[df.index[i+1], 'signal'] = 1
                            df.loc[df.index[i+1], 'entry_price'] = curr_close
                            df.loc[df.index[i+1], 'stop_loss'] = df['low'].iloc[i:i+2].min() * 0.9995
                            df.loc[df.index[i+1], 'take_profit'] = curr_close + curr_body * 2.0
                            df.loc[df.index[i+1], 'signal_type'] = 'bullish_engulfing'
                            engulfing += 1

            # Bearish Engulfing
            elif prev_close > prev_open and curr_close < curr_open:  # Prev green, curr red
                if curr_open >= prev_close and curr_close <= prev_open:  # Engulfs
                    if curr_body > prev_body * 1.2:
                        if df['volume'].iloc[i+1] > df['volume'].iloc[i] * 1.1:
                            df.loc[df.index[i+1], 'signal'] = -1
                            df.loc[df.index[i+1], 'entry_price'] = curr_close
                            df.loc[df.index[i+1], 'stop_loss'] = df['high'].iloc[i:i+2].max() * 1.0005
                            df.loc[df.index[i+1], 'take_profit'] = curr_close - curr_body * 2.0
                            df.loc[df.index[i+1], 'signal_type'] = 'bearish_engulfing'
                            engulfing += 1

        if engulfing > 0:
            print(f"   Found {engulfing} Engulfing patterns")

        return df

    def _detect_morning_evening_star(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Morning Star (bullish) and Evening Star (bearish)
        Three candle pattern
        """
        df = df.copy()
        stars = 0

        for i in range(20, len(df)-2):
            if df['signal'].iloc[i+2] != 0:
                continue

            # Three candles
            c1_open = df['open'].iloc[i]
            c1_close = df['close'].iloc[i]
            c1_body = abs(c1_close - c1_open)

            c2_open = df['open'].iloc[i+1]
            c2_close = df['close'].iloc[i+1]
            c2_body = abs(c2_close - c2_open)

            c3_open = df['open'].iloc[i+2]
            c3_close = df['close'].iloc[i+2]
            c3_body = abs(c3_close - c3_open)

            # Morning Star: Down, small, Up
            if c1_close < c1_open and c3_close > c3_open:  # C1 red, C3 green
                if c2_body < c1_body * 0.5:  # C2 is small
                    if c3_close > (c1_open + c1_close) / 2:  # C3 closes in upper half of C1
                        if df['volume'].iloc[i+2] > df['volume'].iloc[i:i+2].mean() * 1.1:
                            df.loc[df.index[i+2], 'signal'] = 1
                            df.loc[df.index[i+2], 'entry_price'] = c3_close
                            df.loc[df.index[i+2], 'stop_loss'] = df['low'].iloc[i:i+3].min() * 0.9995
                            df.loc[df.index[i+2], 'take_profit'] = c3_close + (c3_close - df['low'].iloc[i:i+3].min()) * 1.5
                            df.loc[df.index[i+2], 'signal_type'] = 'morning_star'
                            stars += 1

            # Evening Star: Up, small, Down
            elif c1_close > c1_open and c3_close < c3_open:  # C1 green, C3 red
                if c2_body < c1_body * 0.5:  # C2 is small
                    if c3_close < (c1_open + c1_close) / 2:  # C3 closes in lower half of C1
                        if df['volume'].iloc[i+2] > df['volume'].iloc[i:i+2].mean() * 1.1:
                            df.loc[df.index[i+2], 'signal'] = -1
                            df.loc[df.index[i+2], 'entry_price'] = c3_close
                            df.loc[df.index[i+2], 'stop_loss'] = df['high'].iloc[i:i+3].max() * 1.0005
                            df.loc[df.index[i+2], 'take_profit'] = c3_close - (df['high'].iloc[i:i+3].max() - c3_close) * 1.5
                            df.loc[df.index[i+2], 'signal_type'] = 'evening_star'
                            stars += 1

        if stars > 0:
            print(f"   Found {stars} Morning/Evening Star patterns")

        return df

    def _detect_doji_reversal(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Doji at support/resistance
        - Very small body (< 10% of range)
        - Forms at key levels
        """
        df = df.copy()
        dojis = 0

        for i in range(20, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            open_price = df['open'].iloc[i]
            close = df['close'].iloc[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]

            body = abs(close - open_price)
            full_range = high - low

            if full_range == 0:
                continue

            # Doji: body < 10% of range
            if body / full_range > 0.1:
                continue

            # Check if at support (for long)
            recent_low = df['low'].iloc[i-20:i].min()
            at_support = abs(low - recent_low) / recent_low < 0.005  # Within 0.5%

            # Check if at resistance (for short)
            recent_high = df['high'].iloc[i-20:i].max()
            at_resistance = abs(high - recent_high) / recent_high < 0.005

            # Long signal at support
            if at_support:
                # Confirm with next candle
                if i < len(df) - 1:
                    next_close = df['close'].iloc[i+1]
                    if next_close > close:  # Bullish confirmation
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'entry_price'] = close
                        df.loc[df.index[i], 'stop_loss'] = low * 0.9995
                        df.loc[df.index[i], 'take_profit'] = close + (close - low) * 3.0
                        df.loc[df.index[i], 'signal_type'] = 'doji_support'
                        dojis += 1

            # Short signal at resistance
            elif at_resistance:
                if i < len(df) - 1:
                    next_close = df['close'].iloc[i+1]
                    if next_close < close:  # Bearish confirmation
                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'entry_price'] = close
                        df.loc[df.index[i], 'stop_loss'] = high * 1.0005
                        df.loc[df.index[i], 'take_profit'] = close - (high - close) * 3.0
                        df.loc[df.index[i], 'signal_type'] = 'doji_resistance'
                        dojis += 1

        if dojis > 0:
            print(f"   Found {dojis} Doji Reversal patterns")

        return df

    def _apply_pattern_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply filters to pattern signals
        """
        df = df.copy()

        initial_signals = len(df[df['signal'] != 0])

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            # Filter 1: Best hours only
            hour = df.index[i].hour
            best_hours = [8, 9, 10, 13, 14, 15]  # London/NY overlap
            if hour not in best_hours:
                df.loc[df.index[i], 'signal'] = 0
                continue

            # Filter 2: Avoid low volume
            if df['volume'].iloc[i] < df['volume'].iloc[max(0, i-20):i].mean() * 0.7:
                df.loc[df.index[i], 'signal'] = 0
                continue

        final_signals = len(df[df['signal'] != 0])
        filtered = initial_signals - final_signals

        print(f"   Filtered out {filtered} weak patterns ({initial_signals} → {final_signals})")

        return df

    def get_strategy_info(self) -> dict:
        """Get strategy info"""
        return {
            'strategy_type': 'Candlestick Patterns',
            'patterns': 'Hammer, Shooting Star, Engulfing, Morning/Evening Star, Doji',
            'timeframe': '1H',
            'risk_reward': 2.0
        }
