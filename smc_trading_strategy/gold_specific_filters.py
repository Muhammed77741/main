"""
Gold-Specific Filters and Analysis
Учитывает уникальные характеристики XAUUSD
"""

import pandas as pd
import numpy as np
from datetime import time
from typing import Tuple, Dict


class GoldSpecificFilters:
    """Фильтры специфичные для золота"""

    def __init__(self):
        # Психологические уровни для золота
        self.round_numbers = [1700, 1750, 1800, 1850, 1900, 1950, 2000, 2050, 2100, 2150, 2200]
        self.major_levels = [1800, 1900, 2000, 2100]  # Особо важные

    def detect_session(self, timestamp) -> str:
        """
        Определить торговую сессию

        Args:
            timestamp: Timestamp

        Returns:
            'asian', 'london', 'ny', 'overlap', 'inactive'
        """
        hour = timestamp.hour

        # Simplified session times (UTC)
        if 0 <= hour < 7:
            return 'asian'  # Тихая сессия
        elif 7 <= hour < 12:
            return 'london'  # Активная
        elif 12 <= hour < 16:
            return 'overlap'  # London/NY overlap - САМАЯ активная
        elif 16 <= hour < 20:
            return 'ny'  # Активная
        else:
            return 'inactive'  # После закрытия NY

    def is_active_session(self, timestamp) -> bool:
        """
        Проверить активную сессию (London или NY overlap)

        Args:
            timestamp: Timestamp

        Returns:
            True если активная сессия
        """
        session = self.detect_session(timestamp)
        return session in ['london', 'overlap', 'ny']

    def add_session_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить фильтры по торговым сессиям

        Args:
            df: DataFrame с timestamp index

        Returns:
            DataFrame с session columns
        """
        df = df.copy()

        df['session'] = df.index.map(self.detect_session)
        df['is_active_session'] = df['session'].isin(['london', 'overlap', 'ny'])
        df['is_best_session'] = df['session'] == 'overlap'  # London/NY overlap

        return df

    def detect_round_number_proximity(self, price: float, threshold: float = 10.0) -> Dict:
        """
        Проверить близость к круглым числам (психологические уровни)

        Args:
            price: Текущая цена
            threshold: Порог близости (в долларах)

        Returns:
            Dict с информацией о близости
        """
        details = {
            'near_round': False,
            'near_major': False,
            'closest_level': None,
            'distance': None,
            'level_type': None
        }

        # Найти ближайший уровень
        distances = [(level, abs(price - level)) for level in self.round_numbers]
        closest_level, min_distance = min(distances, key=lambda x: x[1])

        if min_distance <= threshold:
            details['near_round'] = True
            details['closest_level'] = closest_level
            details['distance'] = min_distance

            if closest_level in self.major_levels:
                details['near_major'] = True
                details['level_type'] = 'major'
            else:
                details['level_type'] = 'minor'

        return details

    def add_round_number_zones(self, df: pd.DataFrame, threshold: float = 10.0) -> pd.DataFrame:
        """
        Добавить зоны круглых чисел

        Args:
            df: DataFrame с ценами
            threshold: Порог близости

        Returns:
            DataFrame с зонами
        """
        df = df.copy()

        df['near_round_number'] = False
        df['near_major_level'] = False
        df['closest_round'] = np.nan
        df['round_distance'] = np.nan

        for i in range(len(df)):
            price = df['close'].iloc[i]
            proximity = self.detect_round_number_proximity(price, threshold)

            df.loc[df.index[i], 'near_round_number'] = proximity['near_round']
            df.loc[df.index[i], 'near_major_level'] = proximity['near_major']

            if proximity['near_round']:
                df.loc[df.index[i], 'closest_round'] = proximity['closest_level']
                df.loc[df.index[i], 'round_distance'] = proximity['distance']

        return df

    def detect_range_market(self, df: pd.DataFrame, idx: int, lookback: int = 20) -> Dict:
        """
        Определить range (боковик) или trending market

        Золото часто в range - важно знать когда

        Args:
            df: DataFrame с ценами
            idx: Текущий индекс
            lookback: Период анализа

        Returns:
            Dict с информацией о рынке
        """
        if idx < lookback:
            return {'market_type': 'unknown', 'range_quality': 0}

        recent = df.iloc[idx-lookback:idx+1]

        # Calculate range metrics
        high_high = recent['high'].max()
        low_low = recent['low'].min()
        range_size = high_high - low_low
        avg_price = recent['close'].mean()

        # Range percentage
        range_pct = (range_size / avg_price) * 100

        # Price position in range
        current_price = df['close'].iloc[idx]
        position_in_range = (current_price - low_low) / range_size if range_size > 0 else 0.5

        # Trend strength (linear regression slope)
        x = np.arange(len(recent))
        y = recent['close'].values
        if len(x) > 1:
            slope, _ = np.polyfit(x, y, 1)
            trend_strength = abs(slope) / avg_price * 100  # % per day
        else:
            trend_strength = 0

        # Classification
        if range_pct < 2.0 and trend_strength < 0.5:
            market_type = 'tight_range'
            range_quality = 0.8
        elif range_pct < 3.5 and trend_strength < 0.8:
            market_type = 'range'
            range_quality = 0.6
        elif trend_strength > 1.5:
            market_type = 'strong_trend'
            range_quality = 0.2
        elif trend_strength > 0.8:
            market_type = 'weak_trend'
            range_quality = 0.4
        else:
            market_type = 'unclear'
            range_quality = 0.5

        return {
            'market_type': market_type,
            'range_quality': range_quality,
            'range_pct': range_pct,
            'trend_strength': trend_strength,
            'position_in_range': position_in_range,
            'range_top': high_high,
            'range_bottom': low_low
        }

    def add_range_detection(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        """
        Добавить определение range/trend

        Args:
            df: DataFrame
            lookback: Период анализа

        Returns:
            DataFrame с range detection
        """
        df = df.copy()

        df['market_type'] = 'unknown'
        df['in_range'] = False
        df['range_quality'] = 0.0
        df['position_in_range'] = 0.5

        for i in range(lookback, len(df)):
            analysis = self.detect_range_market(df, i, lookback)

            df.loc[df.index[i], 'market_type'] = analysis['market_type']
            df.loc[df.index[i], 'in_range'] = analysis['market_type'] in ['range', 'tight_range']
            df.loc[df.index[i], 'range_quality'] = analysis['range_quality']
            df.loc[df.index[i], 'position_in_range'] = analysis['position_in_range']

        return df

    def detect_support_resistance(self, df: pd.DataFrame, window: int = 50) -> pd.DataFrame:
        """
        Определить Support/Resistance зоны

        Золото хорошо уважает S/R уровни

        Args:
            df: DataFrame с ценами
            window: Окно для поиска

        Returns:
            DataFrame с S/R зонами
        """
        df = df.copy()

        # Find swing highs and lows for S/R
        df['is_resistance'] = False
        df['is_support'] = False
        df['resistance_level'] = np.nan
        df['support_level'] = np.nan

        for i in range(window, len(df) - window):
            # Resistance: local high
            local_window = df['high'].iloc[i-window:i+window+1]
            if df['high'].iloc[i] == local_window.max():
                df.loc[df.index[i], 'is_resistance'] = True
                df.loc[df.index[i], 'resistance_level'] = df['high'].iloc[i]

            # Support: local low
            local_window = df['low'].iloc[i-window:i+window+1]
            if df['low'].iloc[i] == local_window.min():
                df.loc[df.index[i], 'is_support'] = True
                df.loc[df.index[i], 'support_level'] = df['low'].iloc[i]

        # Forward fill recent levels
        df['recent_resistance'] = df['resistance_level'].ffill()
        df['recent_support'] = df['support_level'].ffill()

        return df

    def check_near_sr_level(self, df: pd.DataFrame, idx: int, threshold: float = 15.0) -> Dict:
        """
        Проверить близость к Support/Resistance

        Args:
            df: DataFrame с S/R
            idx: Индекс
            threshold: Порог близости

        Returns:
            Dict с информацией
        """
        current_price = df['close'].iloc[idx]

        details = {
            'near_resistance': False,
            'near_support': False,
            'distance_to_resistance': None,
            'distance_to_support': None
        }

        if 'recent_resistance' in df.columns and not pd.isna(df['recent_resistance'].iloc[idx]):
            res_level = df['recent_resistance'].iloc[idx]
            distance = abs(current_price - res_level)

            if distance <= threshold:
                details['near_resistance'] = True
                details['distance_to_resistance'] = distance

        if 'recent_support' in df.columns and not pd.isna(df['recent_support'].iloc[idx]):
            sup_level = df['recent_support'].iloc[idx]
            distance = abs(current_price - sup_level)

            if distance <= threshold:
                details['near_support'] = True
                details['distance_to_support'] = distance

        return details

    def apply_all_gold_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Применить все фильтры для золота

        Args:
            df: DataFrame с OHLCV

        Returns:
            DataFrame со всеми фильтрами
        """
        # Session filters
        df = self.add_session_filters(df)

        # Round numbers
        df = self.add_round_number_zones(df, threshold=10.0)

        # Range detection
        df = self.add_range_detection(df, lookback=20)

        # Support/Resistance
        df = self.detect_support_resistance(df, window=30)

        return df


class GoldVolatilityAnalyzer:
    """Анализ волатильности специфичный для золота"""

    def __init__(self):
        pass

    def calculate_gold_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        ATR оптимизированный для золота

        Args:
            df: DataFrame
            period: Период ATR

        Returns:
            DataFrame с ATR
        """
        df = df.copy()

        # True Range
        df['h_l'] = df['high'] - df['low']
        df['h_pc'] = abs(df['high'] - df['close'].shift(1))
        df['l_pc'] = abs(df['low'] - df['close'].shift(1))

        df['tr'] = df[['h_l', 'h_pc', 'l_pc']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=period).mean()

        # ATR в процентах от цены
        df['atr_pct'] = (df['atr'] / df['close']) * 100

        # Volatility state для золота
        # Золото: Низкая волатильность <0.8%, Средняя 0.8-1.2%, Высокая >1.2%
        df['volatility_state'] = 'medium'
        df.loc[df['atr_pct'] < 0.8, 'volatility_state'] = 'low'
        df.loc[df['atr_pct'] > 1.2, 'volatility_state'] = 'high'

        # Clean up
        df.drop(['h_l', 'h_pc', 'l_pc', 'tr'], axis=1, inplace=True)

        return df

    def adaptive_rr_for_gold(self, df: pd.DataFrame, idx: int) -> float:
        """
        Адаптивный R:R для золота на основе волатильности

        Args:
            df: DataFrame с ATR
            idx: Индекс

        Returns:
            R:R ratio
        """
        if 'volatility_state' not in df.columns:
            return 2.0

        vol_state = df['volatility_state'].iloc[idx]

        # В низкой волатильности - выше R:R (дольше держим)
        # В высокой волатильности - ниже R:R (быстрее выходим)
        if vol_state == 'low':
            return 2.5
        elif vol_state == 'high':
            return 1.5
        else:
            return 2.0
