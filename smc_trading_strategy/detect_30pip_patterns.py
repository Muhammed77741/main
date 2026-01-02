"""
Детектор паттернов для предсказания 30+ пип движений

Анализируем что происходит ПЕРЕД сильными движениями и создаем правила
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class ThirtyPipMoveDetector:
    """
    Детектор паттернов которые предшествуют движениям 30+ пипсов
    
    Анализирует:
    - Консолидацию перед движением
    - Momentum buildup
    - Volume patterns
    - Support/Resistance breaks
    """
    
    def __init__(self, focus_long_only=True):
        """
        Args:
            focus_long_only: Фокусироваться только на LONG движениях
        """
        self.focus_long_only = focus_long_only
        
        print(f"\n🎯 30-Pip Move Pattern Detector")
        print(f"   Focus: {'LONG ONLY' if focus_long_only else 'LONG + SHORT'}")
    
    def calculate_indicators(self, df):
        """Вычисляем индикаторы"""
        
        df = df.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        
        # Moving Averages
        df['ma_5'] = df['close'].rolling(window=5).mean()
        df['ma_10'] = df['close'].rolling(window=10).mean()
        df['ma_20'] = df['close'].rolling(window=20).mean()
        df['ma_50'] = df['close'].rolling(window=50).mean()
        
        # Volume
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        # Momentum
        df['momentum_1h'] = df['close'].pct_change(1) * 100
        df['momentum_3h'] = df['close'].pct_change(3) * 100
        df['momentum_5h'] = df['close'].pct_change(5) * 100
        
        # Volatility (ATR/price)
        df['volatility'] = (df['atr'] / df['close']) * 100
        
        # Range compression (последние 3 свечи vs ATR)
        df['candle_range'] = df['high'] - df['low']
        df['range_compression'] = df['candle_range'] / df['atr']
        df['compression_3'] = df['range_compression'].rolling(window=3).mean()
        
        # Support/Resistance proximity
        df['swing_high'] = df['high'].rolling(window=20).max()
        df['swing_low'] = df['low'].rolling(window=20).min()
        df['distance_to_high'] = ((df['swing_high'] - df['close']) / df['close']) * 100
        df['distance_to_low'] = ((df['close'] - df['swing_low']) / df['close']) * 100
        
        # Bollinger Bands squeeze
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
        df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_mid']) * 100
        
        return df
    
    def detect_consolidation_breakout(self, df, idx):
        """
        Паттерн 1: Консолидация + Breakout
        
        Условия:
        - Низкая volatility (сжатие диапазонов)
        - Пробой консолидации с объемом
        - Momentum начинает расти
        """
        
        if idx < 60:
            return False, None
        
        row = df.iloc[idx]
        
        # Check consolidation (range compression)
        if row['compression_3'] > 0.7:  # Диапазон свечей нормальный/широкий
            return False, None
        
        # Check BB squeeze
        avg_bb_width = df['bb_width'].rolling(window=50).mean().iloc[idx]
        if row['bb_width'] > avg_bb_width:  # BB не сжаты
            return False, None
        
        # Check breakout
        prev_high = df['high'].iloc[idx-5:idx].max()
        if row['high'] <= prev_high:  # Нет breakout
            return False, None
        
        # Check volume confirmation
        if row['volume_ratio'] < 1.2:  # Объем недостаточный
            return False, None
        
        # Check momentum starting
        if row['momentum_1h'] < 0.2:  # Momentum слабый
            return False, None
        
        # Signal!
        entry_price = row['close']
        atr = row['atr']
        
        # SL под консолидацию
        consolidation_low = df['low'].iloc[idx-5:idx].min()
        stop_loss = consolidation_low - atr * 0.3
        
        # TP based on ATR
        take_profit = entry_price + (atr * 3.0)  # 3 ATR target
        
        return True, {
            'pattern': 'Consolidation Breakout',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': 'HIGH' if row['volume_ratio'] > 1.5 else 'MEDIUM',
            'expected_pips': 30
        }
    
    def detect_momentum_acceleration(self, df, idx):
        """
        Паттерн 2: Momentum Acceleration
        
        Условия:
        - RSI начинает расти (cross above 50 или в зоне 50-60)
        - Momentum растет последние 3 свечи
        - Цена выше MA20
        - Volume растет
        """
        
        if idx < 60:
            return False, None
        
        row = df.iloc[idx]
        prev_row = df.iloc[idx-1]
        
        # Check RSI rising in sweet spot
        if row['rsi'] < 45 or row['rsi'] > 70:
            return False, None
        
        if row['rsi'] <= prev_row['rsi']:  # RSI должен расти
            return False, None
        
        # Check momentum acceleration
        mom_now = row['momentum_3h']
        mom_prev = df['momentum_3h'].iloc[idx-3]
        
        if mom_now <= mom_prev:  # Momentum не ускоряется
            return False, None
        
        if mom_now < 0.3:  # Momentum слишком слабый
            return False, None
        
        # Check price above MA20
        if row['close'] < row['ma_20']:
            return False, None
        
        # Check volume increasing
        if row['volume_ratio'] < 1.0:
            return False, None
        
        # Signal!
        entry_price = row['close']
        atr = row['atr']
        
        # SL under MA20
        stop_loss = row['ma_20'] - atr * 0.5
        
        # TP aggressive (momentum play)
        take_profit = entry_price + (atr * 2.5)
        
        return True, {
            'pattern': 'Momentum Acceleration',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': 'HIGH' if row['volume_ratio'] > 1.3 else 'MEDIUM',
            'expected_pips': 30
        }
    
    def detect_support_bounce(self, df, idx):
        """
        Паттерн 3: Support Bounce
        
        Условия:
        - Цена близко к support (MA20 или swing low)
        - RSI oversold recovery (25-40)
        - Bullish candle с высоким volume
        - Не в downtrend
        """
        
        if idx < 60:
            return False, None
        
        row = df.iloc[idx]
        prev_row = df.iloc[idx-1]
        
        # Check near support
        distance_to_ma20 = ((row['close'] - row['ma_20']) / row['close']) * 100
        
        if distance_to_ma20 > 0.5:  # Далеко от MA20
            # Check swing low instead
            if row['distance_to_low'] > 1.0:  # Далеко от swing low
                return False, None
        
        # Check RSI recovery from oversold
        if row['rsi'] < 25 or row['rsi'] > 45:
            return False, None
        
        if row['rsi'] <= prev_row['rsi']:  # RSI должен расти
            return False, None
        
        # Check bullish candle
        if row['close'] <= row['open']:
            return False, None
        
        # Check volume
        if row['volume_ratio'] < 1.1:
            return False, None
        
        # Check not in strong downtrend
        if row['ma_5'] < row['ma_20'] < row['ma_50']:
            return False, None
        
        # Signal!
        entry_price = row['close']
        atr = row['atr']
        
        # Tight SL (bounce play)
        stop_loss = min(row['low'], row['ma_20']) - atr * 0.3
        
        # TP to next resistance
        take_profit = entry_price + (atr * 2.0)
        
        return True, {
            'pattern': 'Support Bounce',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': 'MEDIUM',
            'expected_pips': 30
        }
    
    def detect_trending_pullback(self, df, idx):
        """
        Паттерн 4: Trending Pullback Entry
        
        Условия:
        - Strong uptrend (MA5 > MA20 > MA50)
        - Небольшой pullback к MA20
        - RSI 40-55 (не перекуплено)
        - Bullish reversal candle
        """
        
        if idx < 60:
            return False, None
        
        row = df.iloc[idx]
        prev_row = df.iloc[idx-1]
        
        # Check uptrend
        if not (row['ma_5'] > row['ma_20'] > row['ma_50']):
            return False, None
        
        # Check pullback (price near MA20)
        distance_to_ma20 = abs(((row['close'] - row['ma_20']) / row['close']) * 100)
        
        if distance_to_ma20 > 1.0:  # Слишком далеко от MA20
            return False, None
        
        # Check RSI in sweet spot
        if row['rsi'] < 40 or row['rsi'] > 55:
            return False, None
        
        # Check bullish candle
        candle_body = abs(row['close'] - row['open'])
        candle_range = row['high'] - row['low']
        
        if row['close'] <= row['open']:  # Должна быть bullish
            return False, None
        
        if candle_body < candle_range * 0.5:  # Слабая свеча
            return False, None
        
        # Check previous was down/consolidation
        if prev_row['close'] > prev_row['open']:  # Предыдущая тоже bullish
            return False, None
        
        # Signal!
        entry_price = row['close']
        atr = row['atr']
        
        # SL under MA20
        stop_loss = row['ma_20'] - atr * 0.4
        
        # TP based on trend strength
        take_profit = entry_price + (atr * 2.2)
        
        return True, {
            'pattern': 'Trending Pullback',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': 'HIGH',
            'expected_pips': 30
        }
    
    def detect_volatility_expansion(self, df, idx):
        """
        Паттерн 5: Volatility Expansion
        
        Условия:
        - Volatility была низкой, начинает расти
        - Широкая свеча пробивает диапазон
        - Высокий volume
        - Momentum растет
        """
        
        if idx < 60:
            return False, None
        
        row = df.iloc[idx]
        
        # Check volatility was low
        avg_volatility = df['volatility'].rolling(window=20).mean().iloc[idx]
        
        if row['volatility'] < avg_volatility * 1.3:  # Volatility не растет
            return False, None
        
        # Check wide range candle
        avg_range = df['candle_range'].rolling(window=20).mean().iloc[idx]
        
        if row['candle_range'] < avg_range * 1.5:  # Свеча недостаточно широкая
            return False, None
        
        # Check breakout of recent range
        recent_high = df['high'].iloc[idx-10:idx].max()
        
        if row['high'] <= recent_high:  # Нет breakout
            return False, None
        
        # Check volume spike
        if row['volume_ratio'] < 1.3:
            return False, None
        
        # Check momentum
        if row['momentum_1h'] < 0.3:
            return False, None
        
        # Signal!
        entry_price = row['close']
        atr = row['atr']
        
        # SL under recent swing
        recent_low = df['low'].iloc[idx-10:idx].min()
        stop_loss = recent_low - atr * 0.3
        
        # Aggressive TP (volatility play)
        take_profit = entry_price + (atr * 3.5)
        
        return True, {
            'pattern': 'Volatility Expansion',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': 'HIGH',
            'expected_pips': 40
        }
    
    def detect_all_patterns(self, df):
        """Детектируем все паттерны"""
        
        print(f"\n🔍 Detecting 30-pip move patterns...")
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        signals = []
        
        for idx in range(60, len(df)):
            
            # Pattern 1: Consolidation Breakout
            detected, info = self.detect_consolidation_breakout(df, idx)
            if detected:
                info['time'] = df.index[idx]
                info['type'] = 'BREAKOUT'
                signals.append(info)
                continue  # Один паттерн на свечу
            
            # Pattern 2: Momentum Acceleration
            detected, info = self.detect_momentum_acceleration(df, idx)
            if detected:
                info['time'] = df.index[idx]
                info['type'] = 'MOMENTUM'
                signals.append(info)
                continue
            
            # Pattern 3: Support Bounce
            detected, info = self.detect_support_bounce(df, idx)
            if detected:
                info['time'] = df.index[idx]
                info['type'] = 'BOUNCE'
                signals.append(info)
                continue
            
            # Pattern 4: Trending Pullback
            detected, info = self.detect_trending_pullback(df, idx)
            if detected:
                info['time'] = df.index[idx]
                info['type'] = 'PULLBACK'
                signals.append(info)
                continue
            
            # Pattern 5: Volatility Expansion
            detected, info = self.detect_volatility_expansion(df, idx)
            if detected:
                info['time'] = df.index[idx]
                info['type'] = 'VOLATILITY'
                signals.append(info)
        
        signals_df = pd.DataFrame(signals)
        
        if len(signals_df) > 0:
            print(f"\n✅ Detected {len(signals_df)} signals:")
            
            type_counts = signals_df['type'].value_counts()
            for signal_type, count in type_counts.items():
                print(f"   {signal_type:15s}: {count} signals")
            
            # Confidence breakdown
            conf_counts = signals_df['confidence'].value_counts()
            print(f"\n   By confidence:")
            for conf, count in conf_counts.items():
                print(f"      {conf}: {count}")
        else:
            print(f"\n⚠️ No signals detected")
        
        return signals_df


def backtest_30pip_detector(df, detector):
    """Бэктест детектора"""
    
    print(f"\n🔍 Backtesting 30-pip detector...")
    
    # Detect patterns
    signals_df = detector.detect_all_patterns(df.copy())
    
    if len(signals_df) == 0:
        print("No signals to backtest!")
        return pd.DataFrame()
    
    # Backtest
    trades = []
    
    for idx, signal in signals_df.iterrows():
        entry_time = signal['time']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        # Look forward
        search_end = entry_time + timedelta(hours=24)  # 24h max
        df_future = df[(df.index > entry_time) & (df.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Find exit
        exit_price = None
        exit_type = None
        max_profit_pips = 0
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            # Track max profit
            current_profit_dollars = candle['high'] - entry_price
            current_profit_pips = current_profit_dollars / 0.10
            max_profit_pips = max(max_profit_pips, current_profit_pips)
            
            # Check SL
            if candle['low'] <= stop_loss:
                exit_price = stop_loss
                exit_type = 'SL'
                break
            
            # Check TP
            if candle['high'] >= take_profit:
                exit_price = take_profit
                exit_type = 'TP'
                break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'TIMEOUT'
        
        # Calculate PnL
        pnl_dollars = exit_price - entry_price
        pnl_pips = pnl_dollars / 0.10
        pnl_pct = (pnl_dollars / entry_price) * 100
        
        # Check if reached 30 pips
        reached_30pips = max_profit_pips >= 30
        
        trades.append({
            'entry_time': entry_time,
            'pattern': signal['pattern'],
            'type': signal['type'],
            'confidence': signal['confidence'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pips': pnl_pips,
            'pnl_pct': pnl_pct,
            'max_profit_pips': max_profit_pips,
            'reached_30pips': reached_30pips
        })
    
    trades_df = pd.DataFrame(trades)
    
    # Results
    print(f"\n✅ Backtest Complete:")
    print(f"   {'='*80}")
    print(f"   Total Trades:      {len(trades_df)}")
    
    if len(trades_df) > 0:
        wins = len(trades_df[trades_df['pnl_pips'] > 0])
        win_rate = wins / len(trades_df) * 100
        
        reached_30 = len(trades_df[trades_df['reached_30pips'] == True])
        reach_rate = reached_30 / len(trades_df) * 100
        
        avg_pnl = trades_df['pnl_pips'].mean()
        total_pnl = trades_df['pnl_pips'].sum()
        
        print(f"   Win Rate:          {win_rate:.1f}%")
        print(f"   Reached 30+ pips:  {reached_30} ({reach_rate:.1f}%) ⭐")
        print(f"   Avg PnL:           {avg_pnl:+.1f} pips")
        print(f"   Total PnL:         {total_pnl:+.0f} pips")
        print(f"   {'='*80}")
        
        # By pattern
        print(f"\n   By Pattern:")
        for pattern_type in trades_df['type'].unique():
            type_trades = trades_df[trades_df['type'] == pattern_type]
            type_wr = len(type_trades[type_trades['pnl_pips'] > 0]) / len(type_trades) * 100
            type_reach = len(type_trades[type_trades['reached_30pips'] == True]) / len(type_trades) * 100
            type_avg = type_trades['pnl_pips'].mean()
            
            print(f"      {pattern_type:15s}: {len(type_trades):3d} trades | "
                  f"WR {type_wr:5.1f}% | 30+ {type_reach:5.1f}% | Avg {type_avg:+6.1f}p")
    
    return trades_df


def main():
    print("\n" + "="*100)
    print("ДЕТЕКТОР ПАТТЕРНОВ ДЛЯ 30+ ПИП ДВИЖЕНИЙ")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Initialize detector
    detector = ThirtyPipMoveDetector(focus_long_only=True)
    
    # Backtest
    trades_df = backtest_30pip_detector(df, detector)
    
    # Save
    if len(trades_df) > 0:
        trades_df.to_csv('30pip_patterns_backtest.csv', index=False)
        print(f"\n💾 Results saved: 30pip_patterns_backtest.csv")
    
    return detector, trades_df


if __name__ == "__main__":
    detector, trades_df = main()
