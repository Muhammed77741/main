"""
Volume Analysis для SMC стратегии
Детальный анализ объёма свечей для определения силы движения
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict


class VolumeAnalyzer:
    """Анализ объёма для SMC торговли"""

    def __init__(self, volume_ma_period: int = 20):
        """
        Initialize Volume Analyzer

        Args:
            volume_ma_period: Period for volume moving average
        """
        self.volume_ma_period = volume_ma_period

    def calculate_volume_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume metrics for the dataframe

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with volume metrics
        """
        df = df.copy()

        # Volume moving average
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()

        # Volume strength ratio
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # High/Low volume flags
        df['high_volume'] = df['volume_ratio'] > 1.5
        df['very_high_volume'] = df['volume_ratio'] > 2.0
        df['low_volume'] = df['volume_ratio'] < 0.7

        # Volume trend (increasing/decreasing)
        df['volume_increasing'] = df['volume'] > df['volume'].shift(1)
        df['volume_spike'] = df['volume_ratio'] > 2.5  # Spike = unusual activity

        return df

    def analyze_candle_strength(
        self,
        candle: pd.Series,
        volume_ma: float
    ) -> Dict:
        """
        Детальный анализ силы свечи на основе объёма и структуры

        Args:
            candle: Series с данными свечи (open, high, low, close, volume)
            volume_ma: Средний объём

        Returns:
            Словарь с метриками анализа
        """
        # Базовые расчёты
        body = abs(candle['close'] - candle['open'])
        candle_range = candle['high'] - candle['low']
        body_ratio = body / candle_range if candle_range > 0 else 0

        # Направление
        is_bullish = candle['close'] > candle['open']

        # Wicks
        if is_bullish:
            upper_wick = candle['high'] - candle['close']
            lower_wick = candle['open'] - candle['low']
        else:
            upper_wick = candle['high'] - candle['open']
            lower_wick = candle['close'] - candle['low']

        upper_wick_ratio = upper_wick / candle_range if candle_range > 0 else 0
        lower_wick_ratio = lower_wick / candle_range if candle_range > 0 else 0

        # Volume metrics
        volume_ratio = candle['volume'] / volume_ma if volume_ma > 0 else 1
        volume_strength = 'very_high' if volume_ratio > 2.0 else \
                         'high' if volume_ratio > 1.5 else \
                         'medium' if volume_ratio > 1.0 else 'low'

        # Candle type classification
        candle_type = self._classify_candle_type(
            body_ratio, upper_wick_ratio, lower_wick_ratio, is_bullish
        )

        # Quality score (0-100)
        quality_score = self._calculate_quality_score(
            volume_ratio, body_ratio, upper_wick_ratio, lower_wick_ratio,
            is_bullish, candle_type
        )

        return {
            'is_bullish': is_bullish,
            'body': body,
            'body_ratio': body_ratio,
            'candle_range': candle_range,
            'upper_wick': upper_wick,
            'lower_wick': lower_wick,
            'upper_wick_ratio': upper_wick_ratio,
            'lower_wick_ratio': lower_wick_ratio,
            'volume_ratio': volume_ratio,
            'volume_strength': volume_strength,
            'candle_type': candle_type,
            'quality_score': quality_score
        }

    def _classify_candle_type(
        self,
        body_ratio: float,
        upper_wick_ratio: float,
        lower_wick_ratio: float,
        is_bullish: bool
    ) -> str:
        """
        Классификация типа свечи

        Returns:
            Тип свечи: 'strong_impulse', 'impulse', 'rejection', 'doji', 'weak'
        """
        # Strong impulse: большое тело, минимальные хвосты
        if body_ratio > 0.7 and (upper_wick_ratio + lower_wick_ratio) < 0.3:
            return 'strong_impulse'

        # Impulse: хорошее тело
        if body_ratio > 0.5:
            return 'impulse'

        # Rejection: большой хвост в одну сторону
        if is_bullish and lower_wick_ratio > 0.4 and body_ratio > 0.2:
            return 'bullish_rejection'  # Отбой от низа
        if not is_bullish and upper_wick_ratio > 0.4 and body_ratio > 0.2:
            return 'bearish_rejection'  # Отбой от верха

        # Doji: маленькое тело
        if body_ratio < 0.1:
            return 'doji'

        # Weak: всё остальное
        return 'weak'

    def _calculate_quality_score(
        self,
        volume_ratio: float,
        body_ratio: float,
        upper_wick_ratio: float,
        lower_wick_ratio: float,
        is_bullish: bool,
        candle_type: str
    ) -> int:
        """
        Рассчитать качество свечи (0-100)

        Компоненты:
        - Volume: 0-35 points
        - Body strength: 0-40 points
        - Wick quality: 0-25 points
        """
        score = 0

        # 1. Volume score (0-35)
        if volume_ratio > 2.5:
            score += 35
        elif volume_ratio > 2.0:
            score += 30
        elif volume_ratio > 1.5:
            score += 20
        elif volume_ratio > 1.2:
            score += 10
        elif volume_ratio > 1.0:
            score += 5

        # 2. Body strength score (0-40)
        if body_ratio > 0.8:
            score += 40
        elif body_ratio > 0.7:
            score += 35
        elif body_ratio > 0.6:
            score += 30
        elif body_ratio > 0.5:
            score += 20
        elif body_ratio > 0.3:
            score += 10

        # 3. Wick quality score (0-25)
        # Минимальные wicks = clean move = high score
        total_wick = upper_wick_ratio + lower_wick_ratio
        if total_wick < 0.2:
            score += 25
        elif total_wick < 0.3:
            score += 20
        elif total_wick < 0.4:
            score += 15
        elif total_wick < 0.5:
            score += 10

        # Bonus for candle type
        if candle_type == 'strong_impulse':
            score += 0  # Already counted in components
        elif candle_type in ['bullish_rejection', 'bearish_rejection']:
            score += 5  # Rejection is good for entry

        return min(100, score)

    def check_volume_confirmation(
        self,
        df: pd.DataFrame,
        idx: int,
        direction: str,
        lookback: int = 3
    ) -> Tuple[bool, Dict]:
        """
        Проверить подтверждение по объёму для входа

        Args:
            df: DataFrame with OHLCV and volume metrics
            idx: Current index
            direction: 'long' or 'short'
            lookback: Number of candles to check

        Returns:
            (confirmed, details_dict)
        """
        if idx < lookback:
            return False, {}

        # Analyze current candle
        current_candle = df.iloc[idx]
        volume_ma = df['volume_ma'].iloc[idx]

        current_analysis = self.analyze_candle_strength(current_candle, volume_ma)

        # Check previous candles
        prev_candles = []
        for i in range(1, lookback + 1):
            prev = df.iloc[idx - i]
            prev_analysis = self.analyze_candle_strength(prev, volume_ma)
            prev_candles.append(prev_analysis)

        # Confirmation logic
        confirmed = False
        details = {
            'current_quality': current_analysis['quality_score'],
            'current_type': current_analysis['candle_type'],
            'volume_strength': current_analysis['volume_strength'],
            'avg_prev_quality': np.mean([c['quality_score'] for c in prev_candles])
        }

        # For Long
        if direction == 'long':
            # Current candle must be bullish with good volume
            if (current_analysis['is_bullish'] and
                current_analysis['volume_ratio'] > 1.2 and
                current_analysis['quality_score'] >= 50):

                # Check if previous candles show building momentum
                bullish_prev = sum(1 for c in prev_candles if c['is_bullish'])

                if bullish_prev >= lookback // 2:  # At least half bullish
                    confirmed = True
                    details['confirmation_reason'] = f'Bullish momentum: {bullish_prev}/{lookback} bullish candles'

        # For Short
        elif direction == 'short':
            # Current candle must be bearish with good volume
            if (not current_analysis['is_bullish'] and
                current_analysis['volume_ratio'] > 1.2 and
                current_analysis['quality_score'] >= 50):

                # Check if previous candles show building momentum
                bearish_prev = sum(1 for c in prev_candles if not c['is_bullish'])

                if bearish_prev >= lookback // 2:  # At least half bearish
                    confirmed = True
                    details['confirmation_reason'] = f'Bearish momentum: {bearish_prev}/{lookback} bearish candles'

        details['confirmed'] = confirmed
        return confirmed, details

    def detect_volume_climax(self, df: pd.DataFrame, idx: int, lookback: int = 10) -> bool:
        """
        Detect volume climax (exhaustion signal)

        Args:
            df: DataFrame with volume data
            idx: Current index
            lookback: Lookback period

        Returns:
            True if volume climax detected
        """
        if idx < lookback:
            return False

        recent_volumes = df['volume'].iloc[idx-lookback:idx+1]
        current_volume = df['volume'].iloc[idx]

        # Climax = current volume >> recent average
        avg_recent = recent_volumes.mean()

        return current_volume > avg_recent * 3.0  # 3x spike = climax
