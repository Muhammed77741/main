"""
Детектор упущенных паттернов

Дополнительные сигналы для поиска continuation и mean reversion возможностей
"""

import pandas as pd
import numpy as np
from datetime import timedelta


class MissedPatternsDetector:
    """
    Детектор паттернов которые упускает baseline стратегия
    
    Паттерны:
    1. Strong Uptrend Continuation - продолжение сильного восходящего тренда
    2. Oversold Bounce - отскок от перепроданности
    3. RSI Pullback in Uptrend - откат RSI в восходящем тренде
    4. Volume Breakout - пробой с объемом
    """
    
    def __init__(self, 
                 enable_continuation=True,
                 enable_oversold_bounce=True,
                 enable_rsi_pullback=True,
                 enable_volume_breakout=True):
        """
        Args:
            enable_continuation: Искать continuation паттерны
            enable_oversold_bounce: Искать oversold bounce
            enable_rsi_pullback: Искать RSI pullback
            enable_volume_breakout: Искать volume breakout
        """
        self.enable_continuation = enable_continuation
        self.enable_oversold_bounce = enable_oversold_bounce
        self.enable_rsi_pullback = enable_rsi_pullback
        self.enable_volume_breakout = enable_volume_breakout
        
        print(f"\n🔍 Missed Patterns Detector Initialized")
        print(f"   Patterns enabled:")
        if enable_continuation:
            print(f"      ✅ Strong Uptrend Continuation")
        if enable_oversold_bounce:
            print(f"      ✅ Oversold Bounce")
        if enable_rsi_pullback:
            print(f"      ✅ RSI Pullback in Uptrend")
        if enable_volume_breakout:
            print(f"      ✅ Volume Breakout")
    
    def calculate_indicators(self, df):
        """Вычисляем необходимые индикаторы"""
        
        df = df.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        df['atr'] = high_low.rolling(window=14).mean()
        
        # Moving Averages
        df['ma_5'] = df['close'].rolling(window=5).mean()
        df['ma_20'] = df['close'].rolling(window=20).mean()
        df['ma_50'] = df['close'].rolling(window=50).mean()
        
        # Volume
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        # Price momentum
        df['price_change_1h'] = df['close'].pct_change(1) * 100
        df['price_change_3h'] = df['close'].pct_change(3) * 100
        
        # Trend identification
        df['trend'] = 'sideways'
        df.loc[(df['ma_5'] > df['ma_20']) & (df['ma_20'] > df['ma_50']), 'trend'] = 'strong_up'
        df.loc[(df['ma_5'] > df['ma_20']) & (df['ma_20'] <= df['ma_50']), 'trend'] = 'up'
        df.loc[(df['ma_5'] < df['ma_20']) & (df['ma_20'] < df['ma_50']), 'trend'] = 'strong_down'
        df.loc[(df['ma_5'] < df['ma_20']) & (df['ma_20'] >= df['ma_50']), 'trend'] = 'down'
        
        # Price position vs MA
        df['price_vs_ma5'] = (df['close'] / df['ma_5'] - 1) * 100
        df['price_vs_ma20'] = (df['close'] / df['ma_20'] - 1) * 100
        
        return df
    
    def detect_continuation(self, df, idx):
        """
        Детектор Strong Uptrend Continuation
        
        Условия:
        - Сильный восходящий тренд (MA5 > MA20 > MA50)
        - RSI в диапазоне 40-65 (не перекуплено)
        - Цена близко к MA5 (в пределах 1%)
        - Недавний положительный моментум
        """
        
        if idx < 50:  # Need history
            return False, None
        
        row = df.iloc[idx]
        
        # Check trend
        if row['trend'] != 'strong_up':
            return False, None
        
        # Check RSI
        if row['rsi'] < 40 or row['rsi'] > 65:
            return False, None
        
        # Check price near MA5
        if abs(row['price_vs_ma5']) > 1.0:
            return False, None
        
        # Check positive momentum
        if row['price_change_1h'] < -0.5:
            return False, None
        
        # Signal detected!
        entry_price = row['close']
        atr = row['atr']
        
        # Conservative SL (below MA20)
        stop_loss = row['ma_20'] - atr * 0.5
        
        # TP based on ATR (1.5 R:R)
        sl_distance = entry_price - stop_loss
        take_profit = entry_price + (sl_distance * 1.5)
        
        signal_info = {
            'pattern': 'Uptrend Continuation',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'rsi': row['rsi'],
            'trend': row['trend'],
            'confidence': 'HIGH' if row['rsi'] > 50 else 'MEDIUM'
        }
        
        return True, signal_info
    
    def detect_oversold_bounce(self, df, idx):
        """
        Детектор Oversold Bounce
        
        Условия:
        - RSI < 35 (перепродано)
        - Цена ниже MA20 (>1%)
        - НЕ в сильном нисходящем тренде
        - Признаки разворота (bullish candle)
        """
        
        if idx < 50:
            return False, None
        
        row = df.iloc[idx]
        prev_row = df.iloc[idx-1]
        
        # Check RSI oversold
        if row['rsi'] >= 35:
            return False, None
        
        # Check price below MA20
        if row['price_vs_ma20'] >= -1.0:
            return False, None
        
        # NOT in strong downtrend
        if row['trend'] == 'strong_down':
            return False, None
        
        # Bullish candle (close > open)
        if row['close'] <= row['open']:
            return False, None
        
        # RSI starting to turn up
        if idx >= 51:
            prev_rsi = df.iloc[idx-2]['rsi']
            if row['rsi'] <= prev_rsi:  # RSI должен расти
                return False, None
        
        # Signal detected!
        entry_price = row['close']
        atr = row['atr']
        
        # Tight SL (recent low)
        stop_loss = row['low'] - atr * 0.3
        
        # TP to MA20 (mean reversion)
        take_profit = row['ma_20']
        
        # Ensure minimum R:R
        sl_distance = entry_price - stop_loss
        if (take_profit - entry_price) < sl_distance * 1.2:
            take_profit = entry_price + (sl_distance * 1.2)
        
        signal_info = {
            'pattern': 'Oversold Bounce',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'rsi': row['rsi'],
            'trend': row['trend'],
            'confidence': 'MEDIUM' if row['rsi'] < 25 else 'LOW'
        }
        
        return True, signal_info
    
    def detect_rsi_pullback(self, df, idx):
        """
        Детектор RSI Pullback in Uptrend
        
        Условия:
        - Восходящий тренд (MA5 > MA20 или strong_up)
        - RSI откатил < 50 (но не oversold)
        - Цена близко к MA20 (в пределах 2%)
        - Положительный 3h momentum
        """
        
        if idx < 50:
            return False, None
        
        row = df.iloc[idx]
        
        # Check trend
        if row['trend'] not in ['up', 'strong_up']:
            return False, None
        
        # Check RSI pullback
        if row['rsi'] >= 50 or row['rsi'] < 30:
            return False, None
        
        # Check price near MA20
        if abs(row['price_vs_ma20']) > 2.0:
            return False, None
        
        # Check 3h momentum positive
        if row['price_change_3h'] < 0:
            return False, None
        
        # Signal detected!
        entry_price = row['close']
        atr = row['atr']
        
        # SL below MA20
        stop_loss = row['ma_20'] - atr * 0.5
        
        # TP based on R:R
        sl_distance = entry_price - stop_loss
        take_profit = entry_price + (sl_distance * 1.6)
        
        signal_info = {
            'pattern': 'RSI Pullback',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'rsi': row['rsi'],
            'trend': row['trend'],
            'confidence': 'MEDIUM'
        }
        
        return True, signal_info
    
    def detect_volume_breakout(self, df, idx):
        """
        Детектор Volume Breakout
        
        Условия:
        - Высокий объем (>1.5x средний)
        - Сильный положительный momentum (>0.3% за 1h)
        - RSI > 50 (momentum)
        - Bullish candle
        """
        
        if idx < 50:
            return False, None
        
        row = df.iloc[idx]
        
        # Check volume
        if row['volume_ratio'] <= 1.5:
            return False, None
        
        # Check momentum
        if row['price_change_1h'] <= 0.3:
            return False, None
        
        # Check RSI
        if row['rsi'] <= 50:
            return False, None
        
        # Bullish candle
        if row['close'] <= row['open']:
            return False, None
        
        # Signal detected!
        entry_price = row['close']
        atr = row['atr']
        
        # Tight SL (momentum trade)
        stop_loss = entry_price - atr * 1.0
        
        # Quick TP (momentum fades fast)
        sl_distance = entry_price - stop_loss
        take_profit = entry_price + (sl_distance * 1.3)
        
        signal_info = {
            'pattern': 'Volume Breakout',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'rsi': row['rsi'],
            'volume_ratio': row['volume_ratio'],
            'confidence': 'MEDIUM'
        }
        
        return True, signal_info
    
    def detect_all_patterns(self, df):
        """
        Детектируем все паттерны
        """
        
        print(f"\n🔍 Detecting missed patterns...")
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        signals = []
        
        for idx in range(50, len(df)):
            
            # Try each pattern
            if self.enable_continuation:
                detected, info = self.detect_continuation(df, idx)
                if detected:
                    info['time'] = df.index[idx]
                    info['type'] = 'CONTINUATION'
                    signals.append(info)
            
            if self.enable_oversold_bounce:
                detected, info = self.detect_oversold_bounce(df, idx)
                if detected:
                    info['time'] = df.index[idx]
                    info['type'] = 'BOUNCE'
                    signals.append(info)
            
            if self.enable_rsi_pullback:
                detected, info = self.detect_rsi_pullback(df, idx)
                if detected:
                    info['time'] = df.index[idx]
                    info['type'] = 'PULLBACK'
                    signals.append(info)
            
            if self.enable_volume_breakout:
                detected, info = self.detect_volume_breakout(df, idx)
                if detected:
                    info['time'] = df.index[idx]
                    info['type'] = 'BREAKOUT'
                    signals.append(info)
        
        signals_df = pd.DataFrame(signals)
        
        if len(signals_df) > 0:
            print(f"\n✅ Detected {len(signals_df)} additional signals:")
            
            type_counts = signals_df['type'].value_counts()
            for signal_type, count in type_counts.items():
                print(f"   {signal_type:15s}: {count} signals")
        else:
            print(f"\n⚠️ No additional signals detected")
        
        return signals_df


def main():
    """Test the detector"""
    
    print("\n" + "="*100)
    print("MISSED PATTERNS DETECTOR - TEST")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Initialize detector
    detector = MissedPatternsDetector(
        enable_continuation=True,
        enable_oversold_bounce=True,
        enable_rsi_pullback=True,
        enable_volume_breakout=True
    )
    
    # Detect patterns
    signals_df = detector.detect_all_patterns(df)
    
    if len(signals_df) > 0:
        # Save
        signals_df.to_csv('missed_patterns_signals.csv', index=False)
        print(f"\n💾 Signals saved to: missed_patterns_signals.csv")
        
        # Show some examples
        print(f"\n📊 Sample signals:")
        print(signals_df.head(10).to_string())
    
    return detector, signals_df


if __name__ == "__main__":
    detector, signals_df = main()
