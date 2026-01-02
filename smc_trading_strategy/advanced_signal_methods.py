"""
Продвинутые методы идентификации торговых сигналов

Включает:
1. Volume Profile Analysis
2. Liquidity Sweep Detection
3. Order Flow Imbalance (FVG)
4. Market Structure Breaks (MSB)
5. Momentum Divergences
6. Multi-Timeframe Confirmation
7. Volatility-Based Filters
8. Supply/Demand Zones
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class AdvancedSignalDetector:
    """Продвинутые методы идентификации сигналов"""
    
    def __init__(self):
        self.signals = []
    
    # ========================================================================
    # 1. VOLUME PROFILE ANALYSIS
    # ========================================================================
    
    def detect_volume_profile_signals(self, df, lookback=50, threshold=1.5):
        """
        Анализ Volume Profile - поиск областей высокого объема (POC)
        и low volume nodes (LVN) для входов
        
        Концепция: цена стремится вернуться к POC или пробить LVN
        """
        signals = []
        
        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback:i]
            
            # Разбиваем цены на уровни
            price_levels = np.linspace(window['low'].min(), window['high'].max(), 20)
            volume_at_price = np.zeros(len(price_levels))
            
            # Накапливаем объем на каждом уровне
            for idx, row in window.iterrows():
                for p_idx, price in enumerate(price_levels):
                    if row['low'] <= price <= row['high']:
                        volume_at_price[p_idx] += row['volume']
            
            # Point of Control (POC) - уровень с максимальным объемом
            poc_idx = np.argmax(volume_at_price)
            poc_price = price_levels[poc_idx]
            
            # Value Area High/Low (70% объема)
            total_volume = volume_at_price.sum()
            target_volume = total_volume * 0.7
            
            # Low Volume Nodes (LVN) - области с низким объемом
            avg_volume = volume_at_price.mean()
            lvn_indices = np.where(volume_at_price < avg_volume * 0.5)[0]
            
            current_price = df['close'].iloc[i]
            
            # СИГНАЛ 1: Цена отскакивает от POC (support/resistance)
            if abs(current_price - poc_price) < (df['high'].iloc[i] - df['low'].iloc[i]):
                if current_price < poc_price:  # Ниже POC
                    signals.append({
                        'index': i,
                        'type': 'volume_profile',
                        'signal': 'LONG',
                        'reason': 'Price bounced from POC support',
                        'poc_price': poc_price,
                        'confidence': 0.7
                    })
                else:  # Выше POC
                    signals.append({
                        'index': i,
                        'type': 'volume_profile',
                        'signal': 'SHORT',
                        'reason': 'Price rejected from POC resistance',
                        'poc_price': poc_price,
                        'confidence': 0.7
                    })
        
        return signals
    
    # ========================================================================
    # 2. LIQUIDITY SWEEP DETECTION
    # ========================================================================
    
    def detect_liquidity_sweeps(self, df, lookback=20):
        """
        Обнаружение Liquidity Sweeps - когда цена пробивает очевидный
        уровень (забирает ликвидность), а затем разворачивается
        
        Это классический Smart Money прием
        """
        signals = []
        
        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback:i]
            current = df.iloc[i]
            
            # Находим предыдущие high/low (потенциальная ликвидность)
            prev_high = window['high'].max()
            prev_low = window['low'].min()
            
            # BULLISH LIQUIDITY SWEEP
            # 1. Цена пробила предыдущий low (sweep)
            # 2. Затем закрылась выше него (rejection)
            if current['low'] < prev_low and current['close'] > prev_low:
                # Проверяем что это не просто волатильность
                if (current['close'] - current['low']) > (current['high'] - current['low']) * 0.6:
                    signals.append({
                        'index': i,
                        'type': 'liquidity_sweep',
                        'signal': 'LONG',
                        'reason': 'Bullish liquidity sweep detected',
                        'swept_level': prev_low,
                        'confidence': 0.8
                    })
            
            # BEARISH LIQUIDITY SWEEP
            # 1. Цена пробила предыдущий high (sweep)
            # 2. Затем закрылась ниже него (rejection)
            if current['high'] > prev_high and current['close'] < prev_high:
                if (current['high'] - current['close']) > (current['high'] - current['low']) * 0.6:
                    signals.append({
                        'index': i,
                        'type': 'liquidity_sweep',
                        'signal': 'SHORT',
                        'reason': 'Bearish liquidity sweep detected',
                        'swept_level': prev_high,
                        'confidence': 0.8
                    })
        
        return signals
    
    # ========================================================================
    # 3. ORDER FLOW IMBALANCE (Fair Value Gaps)
    # ========================================================================
    
    def detect_order_flow_imbalances(self, df, min_gap_size=10):
        """
        Fair Value Gaps (FVG) - дисбалансы order flow
        
        Когда между 3 свечами есть GAP = область inefficiency,
        которую цена стремится заполнить
        """
        signals = []
        
        for i in range(2, len(df)):
            candle1 = df.iloc[i-2]
            candle2 = df.iloc[i-1]
            candle3 = df.iloc[i]
            
            # BULLISH FVG
            # Gap между high свечи 1 и low свечи 3
            bullish_gap = candle3['low'] - candle1['high']
            if bullish_gap > min_gap_size:
                # Цена должна быть выше FVG
                if candle3['close'] > candle3['low'] + bullish_gap * 0.5:
                    signals.append({
                        'index': i,
                        'type': 'fvg',
                        'signal': 'LONG',
                        'reason': 'Bullish Fair Value Gap',
                        'gap_size': bullish_gap,
                        'fvg_low': candle1['high'],
                        'fvg_high': candle3['low'],
                        'confidence': 0.75
                    })
            
            # BEARISH FVG
            # Gap между low свечи 1 и high свечи 3
            bearish_gap = candle1['low'] - candle3['high']
            if bearish_gap > min_gap_size:
                if candle3['close'] < candle3['high'] - bearish_gap * 0.5:
                    signals.append({
                        'index': i,
                        'type': 'fvg',
                        'signal': 'SHORT',
                        'reason': 'Bearish Fair Value Gap',
                        'gap_size': bearish_gap,
                        'fvg_low': candle3['high'],
                        'fvg_high': candle1['low'],
                        'confidence': 0.75
                    })
        
        return signals
    
    # ========================================================================
    # 4. MARKET STRUCTURE BREAKS (Advanced)
    # ========================================================================
    
    def detect_market_structure_breaks(self, df, swing_length=5):
        """
        Продвинутое обнаружение Market Structure Breaks
        
        BOS (Break of Structure) - пробой структуры в сторону тренда
        CHoCH (Change of Character) - смена характера рынка
        """
        signals = []
        
        # Находим swing points
        for i in range(swing_length * 2, len(df) - swing_length):
            # Проверяем на swing high
            window_before = df['high'].iloc[i-swing_length:i]
            window_after = df['high'].iloc[i+1:i+swing_length+1]
            current_high = df['high'].iloc[i]
            
            is_swing_high = (current_high >= window_before.max() and 
                           current_high >= window_after.max())
            
            # Проверяем на swing low
            window_before_low = df['low'].iloc[i-swing_length:i]
            window_after_low = df['low'].iloc[i+1:i+swing_length+1]
            current_low = df['low'].iloc[i]
            
            is_swing_low = (current_low <= window_before_low.min() and 
                          current_low <= window_after_low.min())
            
            # Анализируем последующее движение для BOS/CHoCH
            if i < len(df) - swing_length * 2:
                future_window = df.iloc[i:i+swing_length*2]
                
                # BOS - Bullish (пробой предыдущего swing high)
                if is_swing_high:
                    if future_window['high'].max() > current_high * 1.001:  # 0.1% буфер
                        signals.append({
                            'index': i + swing_length,
                            'type': 'bos',
                            'signal': 'LONG',
                            'reason': 'Bullish Break of Structure',
                            'broken_level': current_high,
                            'confidence': 0.85
                        })
                
                # BOS - Bearish (пробой предыдущего swing low)
                if is_swing_low:
                    if future_window['low'].min() < current_low * 0.999:
                        signals.append({
                            'index': i + swing_length,
                            'type': 'bos',
                            'signal': 'SHORT',
                            'reason': 'Bearish Break of Structure',
                            'broken_level': current_low,
                            'confidence': 0.85
                        })
        
        return signals
    
    # ========================================================================
    # 5. MOMENTUM DIVERGENCES
    # ========================================================================
    
    def detect_momentum_divergences(self, df, rsi_period=14, lookback=20):
        """
        RSI дивергенции - расхождение между ценой и моментумом
        
        Bullish: price makes lower low, RSI makes higher low
        Bearish: price makes higher high, RSI makes lower high
        """
        signals = []
        
        # Рассчитываем RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        for i in range(lookback * 2, len(df)):
            window = df.iloc[i-lookback:i]
            rsi_window = rsi.iloc[i-lookback:i]
            
            # BULLISH DIVERGENCE
            # Price: lower low, RSI: higher low
            price_lows = window['low'].values
            rsi_lows = rsi_window.values
            
            if len(price_lows) > 10:
                # Находим последние два минимума
                price_min_idx = np.argmin(price_lows[-10:]) + len(price_lows) - 10
                price_prev_min_idx = np.argmin(price_lows[:price_min_idx]) if price_min_idx > 0 else 0
                
                if price_prev_min_idx < price_min_idx:
                    price_low1 = price_lows[price_prev_min_idx]
                    price_low2 = price_lows[price_min_idx]
                    rsi_low1 = rsi_lows[price_prev_min_idx]
                    rsi_low2 = rsi_lows[price_min_idx]
                    
                    # Bullish divergence: price lower, RSI higher
                    if price_low2 < price_low1 and rsi_low2 > rsi_low1:
                        if rsi.iloc[i] < 40:  # Oversold area
                            signals.append({
                                'index': i,
                                'type': 'divergence',
                                'signal': 'LONG',
                                'reason': 'Bullish RSI divergence',
                                'rsi': rsi.iloc[i],
                                'confidence': 0.7
                            })
            
            # BEARISH DIVERGENCE
            # Price: higher high, RSI: lower high
            price_highs = window['high'].values
            rsi_highs = rsi_window.values
            
            if len(price_highs) > 10:
                price_max_idx = np.argmax(price_highs[-10:]) + len(price_highs) - 10
                price_prev_max_idx = np.argmax(price_highs[:price_max_idx]) if price_max_idx > 0 else 0
                
                if price_prev_max_idx < price_max_idx:
                    price_high1 = price_highs[price_prev_max_idx]
                    price_high2 = price_highs[price_max_idx]
                    rsi_high1 = rsi_highs[price_prev_max_idx]
                    rsi_high2 = rsi_highs[price_max_idx]
                    
                    # Bearish divergence: price higher, RSI lower
                    if price_high2 > price_high1 and rsi_high2 < rsi_high1:
                        if rsi.iloc[i] > 60:  # Overbought area
                            signals.append({
                                'index': i,
                                'type': 'divergence',
                                'signal': 'SHORT',
                                'reason': 'Bearish RSI divergence',
                                'rsi': rsi.iloc[i],
                                'confidence': 0.7
                            })
        
        return signals
    
    # ========================================================================
    # 6. SUPPLY/DEMAND ZONES (Volume-Based)
    # ========================================================================
    
    def detect_supply_demand_zones(self, df, zone_strength_threshold=2):
        """
        Supply/Demand зоны на основе объема и price action
        
        Demand Zone: область где был сильный buy pressure
        Supply Zone: область где был сильный sell pressure
        """
        signals = []
        
        for i in range(20, len(df)):
            window = df.iloc[i-20:i]
            current = df.iloc[i]
            
            # Находим свечи с высоким объемом
            avg_volume = window['volume'].mean()
            high_volume_candles = window[window['volume'] > avg_volume * 1.5]
            
            if len(high_volume_candles) > 0:
                # DEMAND ZONE - bullish candles с высоким объемом
                bullish_hv = high_volume_candles[
                    high_volume_candles['close'] > high_volume_candles['open']
                ]
                
                if len(bullish_hv) > 0:
                    # Зона demand = low последней bullish HV свечи
                    demand_zone_low = bullish_hv['low'].min()
                    demand_zone_high = bullish_hv['high'].max()
                    
                    # Цена возвращается в зону demand
                    if demand_zone_low <= current['low'] <= demand_zone_high:
                        if current['close'] > current['open']:  # Bullish reaction
                            signals.append({
                                'index': i,
                                'type': 'supply_demand',
                                'signal': 'LONG',
                                'reason': 'Price reacted to demand zone',
                                'zone_low': demand_zone_low,
                                'zone_high': demand_zone_high,
                                'confidence': 0.75
                            })
                
                # SUPPLY ZONE - bearish candles с высоким объемом
                bearish_hv = high_volume_candles[
                    high_volume_candles['close'] < high_volume_candles['open']
                ]
                
                if len(bearish_hv) > 0:
                    supply_zone_low = bearish_hv['low'].min()
                    supply_zone_high = bearish_hv['high'].max()
                    
                    # Цена возвращается в зону supply
                    if supply_zone_low <= current['high'] <= supply_zone_high:
                        if current['close'] < current['open']:  # Bearish reaction
                            signals.append({
                                'index': i,
                                'type': 'supply_demand',
                                'signal': 'SHORT',
                                'reason': 'Price reacted to supply zone',
                                'zone_low': supply_zone_low,
                                'zone_high': supply_zone_high,
                                'confidence': 0.75
                            })
        
        return signals
    
    # ========================================================================
    # 7. VOLATILITY BREAKOUT
    # ========================================================================
    
    def detect_volatility_breakouts(self, df, atr_period=14, atr_multiplier=2.0):
        """
        Прорывы волатильности - когда цена выходит за пределы ATR
        
        Часто предшествуют сильным движениям
        """
        signals = []
        
        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=atr_period).mean()
        
        for i in range(atr_period + 1, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            current_atr = atr.iloc[i]
            
            # BULLISH BREAKOUT
            # Цена пробила верхнюю границу (close + ATR * multiplier)
            upper_band = prev['close'] + current_atr * atr_multiplier
            if current['close'] > upper_band:
                signals.append({
                    'index': i,
                    'type': 'volatility_breakout',
                    'signal': 'LONG',
                    'reason': 'Bullish volatility breakout',
                    'atr': current_atr,
                    'breakout_level': upper_band,
                    'confidence': 0.7
                })
            
            # BEARISH BREAKOUT
            lower_band = prev['close'] - current_atr * atr_multiplier
            if current['close'] < lower_band:
                signals.append({
                    'index': i,
                    'type': 'volatility_breakout',
                    'signal': 'SHORT',
                    'reason': 'Bearish volatility breakout',
                    'atr': current_atr,
                    'breakout_level': lower_band,
                    'confidence': 0.7
                })
        
        return signals
    
    # ========================================================================
    # ГЛАВНАЯ ФУНКЦИЯ - КОМБИНАЦИЯ ВСЕХ МЕТОДОВ
    # ========================================================================
    
    def detect_all_signals(self, df, methods=['all']):
        """
        Обнаружение сигналов всеми доступными методами
        
        Args:
            df: DataFrame с OHLCV данными
            methods: список методов или ['all'] для всех
        
        Returns:
            DataFrame с сигналами и их уверенностью
        """
        all_signals = []
        
        available_methods = {
            'volume_profile': self.detect_volume_profile_signals,
            'liquidity_sweep': self.detect_liquidity_sweeps,
            'fvg': self.detect_order_flow_imbalances,
            'bos': self.detect_market_structure_breaks,
            'divergence': self.detect_momentum_divergences,
            'supply_demand': self.detect_supply_demand_zones,
            'volatility': self.detect_volatility_breakouts
        }
        
        if 'all' in methods:
            methods = list(available_methods.keys())
        
        print(f"🔍 Detecting signals using methods: {', '.join(methods)}")
        
        for method_name in methods:
            if method_name in available_methods:
                print(f"   Running {method_name}...")
                method_signals = available_methods[method_name](df)
                all_signals.extend(method_signals)
        
        # Конвертируем в DataFrame
        if len(all_signals) > 0:
            signals_df = pd.DataFrame(all_signals)
            
            # Добавляем информацию о свечах
            signals_df['timestamp'] = signals_df['index'].apply(lambda x: df.index[x])
            signals_df['price'] = signals_df['index'].apply(lambda x: df['close'].iloc[x])
            
            # Сортируем по времени
            signals_df = signals_df.sort_values('timestamp')
            
            return signals_df
        else:
            return pd.DataFrame()
    
    # ========================================================================
    # ENSEMBLE METHOD - Комбинация сигналов
    # ========================================================================
    
    def ensemble_signals(self, signals_df, min_confidence=0.7, min_confirmations=2):
        """
        Ensemble подход - берем только сигналы с подтверждением от нескольких методов
        
        Args:
            signals_df: DataFrame с сигналами от всех методов
            min_confidence: минимальная уверенность сигнала
            min_confirmations: минимальное число подтверждений
        
        Returns:
            Filtered signals с высокой уверенностью
        """
        if len(signals_df) == 0:
            return pd.DataFrame()
        
        # Группируем близкие по времени сигналы (в пределах 3 свечей)
        ensembled = []
        
        for i in range(len(signals_df)):
            signal = signals_df.iloc[i]
            
            # Находим близкие сигналы того же направления
            close_signals = signals_df[
                (abs(signals_df['index'] - signal['index']) <= 3) &
                (signals_df['signal'] == signal['signal'])
            ]
            
            if len(close_signals) >= min_confirmations:
                # Берем средние значения
                avg_confidence = close_signals['confidence'].mean()
                
                if avg_confidence >= min_confidence:
                    ensembled.append({
                        'index': signal['index'],
                        'timestamp': signal['timestamp'],
                        'signal': signal['signal'],
                        'price': signal['price'],
                        'confidence': avg_confidence,
                        'confirmations': len(close_signals),
                        'methods': ', '.join(close_signals['type'].unique()),
                        'reasons': ' | '.join(close_signals['reason'].unique())
                    })
        
        # Удаляем дубликаты
        if len(ensembled) > 0:
            ensemble_df = pd.DataFrame(ensembled)
            ensemble_df = ensemble_df.drop_duplicates(subset=['index'])
            return ensemble_df
        else:
            return pd.DataFrame()


def main():
    """Тестирование всех методов"""
    print("\n" + "="*100)
    print("ПРОДВИНУТЫЕ МЕТОДЫ ИДЕНТИФИКАЦИИ СИГНАЛОВ")
    print("="*100 + "\n")
    
    # Загружаем данные
    print("📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}\n")
    
    # Инициализируем детектор
    detector = AdvancedSignalDetector()
    
    # Детектируем все сигналы
    all_signals = detector.detect_all_signals(df, methods=['all'])
    
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"   Всего сигналов найдено: {len(all_signals)}")
    
    if len(all_signals) > 0:
        print(f"\n   По типам:")
        for method_type in all_signals['type'].unique():
            count = len(all_signals[all_signals['type'] == method_type])
            print(f"   • {method_type}: {count}")
        
        print(f"\n   По направлению:")
        long_count = len(all_signals[all_signals['signal'] == 'LONG'])
        short_count = len(all_signals[all_signals['signal'] == 'SHORT'])
        print(f"   • LONG: {long_count}")
        print(f"   • SHORT: {short_count}")
        
        print(f"\n   Средняя уверенность: {all_signals['confidence'].mean():.2%}")
        
        # Ensemble подход
        print(f"\n🎯 ENSEMBLE FILTERING:")
        ensemble_signals = detector.ensemble_signals(all_signals, min_confidence=0.75, min_confirmations=2)
        
        print(f"   Сигналов после фильтрации: {len(ensemble_signals)}")
        
        if len(ensemble_signals) > 0:
            print(f"   Средняя уверенность: {ensemble_signals['confidence'].mean():.2%}")
            print(f"   Среднее число подтверждений: {ensemble_signals['confirmations'].mean():.1f}")
            
            # Примеры лучших сигналов
            print(f"\n📝 TOP 5 СИГНАЛОВ:")
            top_signals = ensemble_signals.nlargest(5, 'confidence')
            for idx, signal in top_signals.iterrows():
                print(f"\n   {signal['signal']} @ {signal['timestamp']}")
                print(f"   Price: {signal['price']:.2f}")
                print(f"   Confidence: {signal['confidence']:.1%}")
                print(f"   Confirmations: {int(signal['confirmations'])}")
                print(f"   Methods: {signal['methods']}")
    
    print("\n" + "="*100)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("="*100)


if __name__ == "__main__":
    main()
