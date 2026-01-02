"""
Детектор новых паттернов на основе анализа пропущенных возможностей

Новые паттерны:
1. VOLUME_BREAKOUT - High volume breakout in uptrend
2. ATR_EXPANSION - High volatility expansion
3. MOMENTUM_CANDLE - Strong directional candle
"""

import pandas as pd
import numpy as np
from datetime import timedelta


class NewPatternsDetector:
    """
    Детектор новых паттернов для ловли пропущенных возможностей
    """
    
    def __init__(self, 
                 enable_volume_breakout=True,
                 enable_atr_expansion=True,
                 enable_momentum_candle=True,
                 focus_long_only=True):
        
        self.enable_volume_breakout = enable_volume_breakout
        self.enable_atr_expansion = enable_atr_expansion
        self.enable_momentum_candle = enable_momentum_candle
        self.focus_long_only = focus_long_only
        
        print(f"\n🆕 New Patterns Detector Initialized")
        print(f"   Focus: {'LONG ONLY' if focus_long_only else 'LONG & SHORT'}")
        print(f"   Patterns:")
        if enable_volume_breakout:
            print(f"      ✅ VOLUME_BREAKOUT")
        if enable_atr_expansion:
            print(f"      ✅ ATR_EXPANSION")
        if enable_momentum_candle:
            print(f"      ✅ MOMENTUM_CANDLE")
    
    def calculate_indicators(self, df):
        """
        Рассчитать необходимые индикаторы
        """
        
        df = df.copy()
        
        # Moving averages
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma50'] = df['close'].rolling(50).mean()
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # ATR percentile
        df['atr_percentile'] = df['atr'].rolling(100).apply(
            lambda x: (x.iloc[-1] / x.quantile(0.75)) if len(x) > 0 and x.quantile(0.75) > 0 else 0
        )
        
        # Volume
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # Trend
        df['trend_up'] = df['ma5'] > df['ma20']
        df['trend_down'] = df['ma5'] < df['ma20']
        df['strong_trend_up'] = (df['ma5'] > df['ma10']) & (df['ma10'] > df['ma20'])
        df['strong_trend_down'] = (df['ma5'] < df['ma10']) & (df['ma10'] < df['ma20'])
        
        # Candle metrics
        df['body'] = abs(df['close'] - df['open'])
        df['range'] = df['high'] - df['low']
        df['body_ratio'] = df['body'] / df['range']
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        # Price momentum
        df['momentum_5'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100
        
        return df
    
    def detect_volume_breakout(self, df, idx):
        """
        Pattern 1: VOLUME BREAKOUT IN UPTREND
        
        Условия:
        - Strong uptrend (MA5 > MA10 > MA20)
        - Volume > 1.5x average
        - Bullish candle
        - Price above MA20
        - Breaking recent high
        """
        
        if idx < 50:
            return None
        
        current = df.iloc[idx]
        prev_20 = df.iloc[idx-20:idx]
        
        # Check uptrend
        if not current['strong_trend_up']:
            return None
        
        # Check volume
        if current['volume_ratio'] < 1.5:
            return None
        
        # Check bullish candle
        if not current['is_bullish']:
            return None
        
        # Check if breaking recent high
        recent_high = prev_20['high'].max()
        if current['high'] <= recent_high:
            return None
        
        # Check ATR for SL/TP
        atr = current['atr']
        if pd.isna(atr) or atr <= 0:
            return None
        
        # Calculate confidence
        confidence = 'HIGH'
        
        # Lower confidence if volume spike is too extreme (>3x = suspicious)
        if current['volume_ratio'] > 3.0:
            confidence = 'MEDIUM'
        
        # Entry/SL/TP
        entry_price = current['close']
        stop_loss = entry_price - (atr * 1.5)
        take_profit = entry_price + (atr * 3.0)  # 2:1 R/R
        
        return {
            'time': df.index[idx],
            'pattern': 'Volume Breakout in Uptrend',
            'type': 'VOLUME_BREAKOUT',
            'direction': 'LONG',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': confidence,
            'volume_ratio': current['volume_ratio'],
            'trend_strength': 'STRONG'
        }
    
    def detect_atr_expansion(self, df, idx):
        """
        Pattern 2: ATR EXPANSION
        
        Условия:
        - ATR > 75th percentile (высокая волатильность)
        - Price momentum positive
        - In uptrend
        - Strong candle (body > 60%)
        """
        
        if idx < 50:
            return None
        
        current = df.iloc[idx]
        
        # Check ATR expansion
        if current['atr_percentile'] < 1.0:  # ATR not above 75th percentile
            return None
        
        # Check trend
        if not current['trend_up']:
            return None
        
        # Check momentum
        if current['momentum_5'] <= 0:
            return None
        
        # Check candle strength
        if current['body_ratio'] < 0.6:
            return None
        
        # Check bullish
        if not current['is_bullish']:
            return None
        
        atr = current['atr']
        if pd.isna(atr) or atr <= 0:
            return None
        
        # Confidence based on ATR level
        confidence = 'HIGH' if current['atr_percentile'] > 1.2 else 'MEDIUM'
        
        # Entry/SL/TP (wider for high volatility)
        entry_price = current['close']
        stop_loss = entry_price - (atr * 2.0)  # Wider SL
        take_profit = entry_price + (atr * 4.0)  # 2:1 R/R
        
        return {
            'time': df.index[idx],
            'pattern': 'ATR Expansion',
            'type': 'ATR_EXPANSION',
            'direction': 'LONG',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': confidence,
            'atr_percentile': current['atr_percentile'],
            'momentum': current['momentum_5']
        }
    
    def detect_momentum_candle(self, df, idx):
        """
        Pattern 3: STRONG MOMENTUM CANDLE
        
        Условия:
        - Very strong candle (body > 70%)
        - In direction of trend
        - Price above MA20
        - Closing near high
        """
        
        if idx < 50:
            return None
        
        current = df.iloc[idx]
        
        # Check candle strength
        if current['body_ratio'] < 0.7:
            return None
        
        # Check trend
        if not current['trend_up']:
            return None
        
        # Check bullish
        if not current['is_bullish']:
            return None
        
        # Check closing near high (upper 20% of range)
        close_position = (current['close'] - current['low']) / current['range']
        if close_position < 0.8:
            return None
        
        # Check price above MA20
        if current['close'] <= current['ma20']:
            return None
        
        atr = current['atr']
        if pd.isna(atr) or atr <= 0:
            return None
        
        # Confidence
        confidence = 'HIGH' if current['body_ratio'] > 0.8 else 'MEDIUM'
        
        # Entry/SL/TP
        entry_price = current['close']
        stop_loss = max(entry_price - (atr * 1.5), current['low'] - 0.5)  # Below candle low
        take_profit = entry_price + (atr * 3.0)
        
        return {
            'time': df.index[idx],
            'pattern': 'Strong Momentum Candle',
            'type': 'MOMENTUM_CANDLE',
            'direction': 'LONG',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': confidence,
            'body_ratio': current['body_ratio'],
            'close_position': close_position
        }
    
    def detect_all_patterns(self, df):
        """
        Detect all new patterns
        """
        
        print(f"\n🔍 Detecting new patterns...")
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        signals = []
        
        for idx in range(50, len(df)):
            
            # Volume Breakout
            if self.enable_volume_breakout:
                signal = self.detect_volume_breakout(df, idx)
                if signal:
                    signals.append(signal)
            
            # ATR Expansion
            if self.enable_atr_expansion:
                signal = self.detect_atr_expansion(df, idx)
                if signal:
                    signals.append(signal)
            
            # Momentum Candle
            if self.enable_momentum_candle:
                signal = self.detect_momentum_candle(df, idx)
                if signal:
                    signals.append(signal)
        
        signals_df = pd.DataFrame(signals)
        
        if len(signals_df) > 0:
            print(f"\n✅ Detected {len(signals_df)} signals:")
            
            for pattern_type in signals_df['type'].unique():
                count = len(signals_df[signals_df['type'] == pattern_type])
                high_conf = len(signals_df[(signals_df['type'] == pattern_type) & (signals_df['confidence'] == 'HIGH')])
                print(f"   {pattern_type:20s}: {count:3d} ({high_conf} HIGH confidence)")
            
            # By confidence
            if 'confidence' in signals_df.columns:
                print(f"\n   By confidence:")
                for conf in ['HIGH', 'MEDIUM']:
                    count = len(signals_df[signals_df['confidence'] == conf])
                    if count > 0:
                        print(f"      {conf}: {count}")
        else:
            print(f"   No signals detected")
        
        return signals_df


def backtest_new_patterns(df, detector):
    """
    Backtest new patterns
    """
    
    print(f"\n" + "="*100)
    print(f"🔍 BACKTESTING NEW PATTERNS")
    print("="*100)
    
    # Get signals
    signals_df = detector.detect_all_patterns(df.copy())
    
    if len(signals_df) == 0:
        print("No signals to backtest")
        return pd.DataFrame()
    
    trades = []
    
    for idx, signal in signals_df.iterrows():
        entry_time = signal['time']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        # Look forward 24 hours
        search_end = entry_time + timedelta(hours=24)
        df_future = df[(df.index > entry_time) & (df.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Find exit
        hit_tp = False
        hit_sl = False
        exit_price = None
        exit_type = 'TIMEOUT'
        max_profit_pips = 0
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            # Track max profit
            current_profit = (candle['high'] - entry_price) / 0.10
            max_profit_pips = max(max_profit_pips, current_profit)
            
            # Check SL
            if candle['low'] <= stop_loss:
                hit_sl = True
                exit_price = stop_loss
                exit_type = 'SL'
                break
            
            # Check TP
            if candle['high'] >= take_profit:
                hit_tp = True
                exit_price = take_profit
                exit_type = 'TP'
                break
        
        # Timeout
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'TIMEOUT'
        
        # Calculate PnL
        pnl_dollars = exit_price - entry_price
        pnl_pct = (pnl_dollars / entry_price) * 100
        pnl_pips = pnl_dollars / 0.10
        
        trades.append({
            'entry_time': entry_time,
            'pattern': signal['pattern'],
            'type': signal['type'],
            'confidence': signal['confidence'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'pnl_dollars': pnl_dollars,
            'pnl_pct': pnl_pct,
            'pnl_pips': pnl_pips,
            'max_profit_pips': max_profit_pips,
            'exit_type': exit_type,
            'hit_tp': hit_tp,
            'hit_sl': hit_sl
        })
    
    trades_df = pd.DataFrame(trades)
    
    # Print results
    print_backtest_results(trades_df)
    
    return trades_df


def print_backtest_results(trades_df):
    """
    Print backtest results
    """
    
    print(f"\n✅ Backtest Results:")
    print(f"   {'='*80}")
    
    if len(trades_df) == 0:
        print("   No trades")
        return
    
    # Overall
    total_pnl_pct = trades_df['pnl_pct'].sum()
    total_pnl_pips = trades_df['pnl_pips'].sum()
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    win_rate = wins / len(trades_df) * 100
    
    avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
    avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if len(trades_df) - wins > 0 else 0
    
    print(f"   Total Trades:    {len(trades_df)}")
    print(f"   Win Rate:        {win_rate:.1f}%")
    print(f"   Total PnL:       {total_pnl_pct:+.2f}% ({total_pnl_pips:+.0f} pips)")
    print(f"   Avg PnL:         {trades_df['pnl_pct'].mean():+.3f}%")
    print(f"   Avg Win:         {avg_win:+.3f}%")
    print(f"   Avg Loss:        {avg_loss:+.3f}%")
    
    # By pattern type
    print(f"\n   📊 By Pattern:")
    for pattern_type in sorted(trades_df['type'].unique()):
        type_trades = trades_df[trades_df['type'] == pattern_type]
        type_wins = len(type_trades[type_trades['pnl_pct'] > 0])
        type_wr = type_wins / len(type_trades) * 100
        type_pnl = type_trades['pnl_pct'].sum()
        type_pips = type_trades['pnl_pips'].sum()
        
        print(f"      {pattern_type:20s}: {len(type_trades):3d} | "
              f"WR {type_wr:5.1f}% | PnL {type_pnl:+7.2f}% ({type_pips:+6.0f}p)")
    
    # By confidence
    print(f"\n   📊 By Confidence:")
    for conf in ['HIGH', 'MEDIUM']:
        conf_trades = trades_df[trades_df['confidence'] == conf]
        if len(conf_trades) > 0:
            conf_wins = len(conf_trades[conf_trades['pnl_pct'] > 0])
            conf_wr = conf_wins / len(conf_trades) * 100
            conf_pnl = conf_trades['pnl_pct'].sum()
            
            print(f"      {conf:10s}: {len(conf_trades):3d} | WR {conf_wr:5.1f}% | PnL {conf_pnl:+7.2f}%")
    
    # Exit types
    print(f"\n   📊 Exit Types:")
    for exit_type in ['TP', 'SL', 'TIMEOUT']:
        exit_trades = trades_df[trades_df['exit_type'] == exit_type]
        if len(exit_trades) > 0:
            exit_pct = len(exit_trades) / len(trades_df) * 100
            exit_pnl = exit_trades['pnl_pct'].sum()
            
            print(f"      {exit_type:10s}: {len(exit_trades):3d} ({exit_pct:5.1f}%) | PnL {exit_pnl:+7.2f}%")


def main():
    print("\n" + "="*100)
    print("🆕 TESTING NEW PATTERNS")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Initialize detector
    detector = NewPatternsDetector(
        enable_volume_breakout=True,
        enable_atr_expansion=True,
        enable_momentum_candle=True,
        focus_long_only=True
    )
    
    # Backtest
    trades_df = backtest_new_patterns(df, detector)
    
    if len(trades_df) > 0:
        # Save
        trades_df.to_csv('new_patterns_backtest.csv', index=False)
        print(f"\n💾 Saved: new_patterns_backtest.csv")
    
    print(f"\n" + "="*100)
    print("✅ TESTING COMPLETE")
    print("="*100)


if __name__ == "__main__":
    main()
