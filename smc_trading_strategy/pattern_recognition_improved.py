"""
Улучшенная версия Pattern Recognition Strategy

Основные улучшения:
1. Фильтр SHORT сделок по RSI (избегаем SHORT при RSI < 35)
2. Partial Take Profit на 50% пути
3. Улучшенный Trailing Stop (более агрессивный)
4. Фильтр LOW волатильности (торгуем только medium+ ATR)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pattern_recognition_strategy import PatternRecognitionStrategy


class PatternRecognitionImproved(PatternRecognitionStrategy):
    """
    Улучшенная версия baseline стратегии
    """
    
    def __init__(self, fib_mode='standard', min_atr_percentile=25):
        super().__init__(fib_mode=fib_mode)
        self.min_atr_percentile = min_atr_percentile
        self.name = "Pattern Recognition IMPROVED"
        
        print(f"\n🚀 IMPROVED Pattern Recognition Initialized")
        print(f"   📊 Min ATR Percentile: {min_atr_percentile}")
        print(f"   🎯 Partial TP: 50% на половине пути")
        print(f"   📉 Улучшенный trailing stop")
        print(f"   ⚡ RSI фильтры для SHORT")
    
    def run_strategy(self, df):
        """Run improved strategy with additional filters"""
        
        # 1. Запускаем базовую стратегию
        df_strategy = super().run_strategy(df.copy())
        
        # 2. Применяем улучшения
        df_strategy = self._apply_improvements(df_strategy)
        
        return df_strategy
    
    def _apply_improvements(self, df):
        """Apply improvement filters"""
        
        signals_before = len(df[df['signal'] != 0])
        
        # Calculate ATR
        high_low = df['high'] - df['low']
        atr = high_low.rolling(window=14).mean()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        df['atr'] = atr
        df['rsi'] = rsi
        
        # ATR filter threshold
        atr_threshold = df['atr'].quantile(self.min_atr_percentile / 100)
        
        filtered_signals = 0
        
        for idx in df[df['signal'] != 0].index:
            signal = df.loc[idx, 'signal']
            current_rsi = df.loc[idx, 'rsi']
            current_atr = df.loc[idx, 'atr']
            
            should_filter = False
            
            # Filter 1: SHORT при RSI < 35 (расширенный от 30)
            if signal == -1 and current_rsi < 35:
                should_filter = True
                # print(f"❌ Filtered SHORT at {idx}: RSI={current_rsi:.1f}")
            
            # Filter 2: Низкая волатильность
            if current_atr < atr_threshold:
                should_filter = True
                # print(f"❌ Filtered signal at {idx}: Low ATR={current_atr:.2f}")
            
            if should_filter:
                df.loc[idx, 'signal'] = 0
                df.loc[idx, 'entry_price'] = np.nan
                df.loc[idx, 'stop_loss'] = np.nan
                df.loc[idx, 'take_profit'] = np.nan
                filtered_signals += 1
        
        signals_after = len(df[df['signal'] != 0])
        
        print(f"\n✨ Improvement Filters Applied:")
        print(f"   Signals: {signals_before} → {signals_after} (filtered {filtered_signals})")
        
        return df


def backtest_improved_with_partial_tp(df, strategy):
    """
    Backtest с Partial TP и улучшенным trailing stop
    """
    
    print("\n🔍 Running IMPROVED backtest...")
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    trades = []
    total_pnl = 0
    
    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']
        
        entry_time = df_signals.index[i]
        entry_idx = df_strategy.index.get_loc(entry_time)
        search_end = entry_time + timedelta(hours=48)
        
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Partial TP level (50% пути до TP)
        if direction == 1:
            partial_tp = entry_price + (take_profit - entry_price) * 0.5
        else:
            partial_tp = entry_price - (entry_price - take_profit) * 0.5
        
        position_size = 1.0  # 100%
        pnl = 0
        exits = []
        
        # Trailing stop (более агрессивный - 12 пипсов вместо 18)
        sl_distance = abs(entry_price - stop_loss)
        trailing_distance = sl_distance * 0.4  # 40% от SL distance вместо 60%
        
        trailing_sl = stop_loss
        max_price = entry_price if direction == 1 else entry_price
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            if position_size <= 0:
                break
            
            # Update max price and trailing SL
            if direction == 1:
                if candle['high'] > max_price:
                    max_price = candle['high']
                    new_trailing_sl = max_price - trailing_distance
                    if new_trailing_sl > trailing_sl:
                        trailing_sl = new_trailing_sl
            else:
                if candle['low'] < max_price:
                    max_price = candle['low']
                    new_trailing_sl = max_price + trailing_distance
                    if new_trailing_sl < trailing_sl:
                        trailing_sl = new_trailing_sl
            
            # Check exits
            if direction == 1:  # LONG
                # Partial TP
                if position_size == 1.0 and candle['high'] >= partial_tp:
                    exit_size = 0.5
                    exit_price = partial_tp
                    pnl += ((exit_price - entry_price) / entry_price) * 100 * exit_size
                    position_size -= exit_size
                    exits.append({
                        'type': 'Partial TP',
                        'price': exit_price,
                        'size': exit_size,
                        'pnl': ((exit_price - entry_price) / entry_price) * 100 * exit_size
                    })
                    continue
                
                # SL (Trailing)
                if candle['low'] <= trailing_sl:
                    exit_price = trailing_sl
                    pnl += ((exit_price - entry_price) / entry_price) * 100 * position_size
                    exits.append({
                        'type': 'SL',
                        'price': exit_price,
                        'size': position_size,
                        'pnl': ((exit_price - entry_price) / entry_price) * 100 * position_size
                    })
                    position_size = 0
                    break
                
                # Full TP
                if candle['high'] >= take_profit:
                    exit_price = take_profit
                    pnl += ((exit_price - entry_price) / entry_price) * 100 * position_size
                    exits.append({
                        'type': 'TP',
                        'price': exit_price,
                        'size': position_size,
                        'pnl': ((exit_price - entry_price) / entry_price) * 100 * position_size
                    })
                    position_size = 0
                    break
            
            else:  # SHORT
                # Partial TP
                if position_size == 1.0 and candle['low'] <= partial_tp:
                    exit_size = 0.5
                    exit_price = partial_tp
                    pnl += ((entry_price - exit_price) / entry_price) * 100 * exit_size
                    position_size -= exit_size
                    exits.append({
                        'type': 'Partial TP',
                        'price': exit_price,
                        'size': exit_size,
                        'pnl': ((entry_price - exit_price) / entry_price) * 100 * exit_size
                    })
                    continue
                
                # SL (Trailing)
                if candle['high'] >= trailing_sl:
                    exit_price = trailing_sl
                    pnl += ((entry_price - exit_price) / entry_price) * 100 * position_size
                    exits.append({
                        'type': 'SL',
                        'price': exit_price,
                        'size': position_size,
                        'pnl': ((entry_price - exit_price) / entry_price) * 100 * position_size
                    })
                    position_size = 0
                    break
                
                # Full TP
                if candle['low'] <= take_profit:
                    exit_price = take_profit
                    pnl += ((entry_price - exit_price) / entry_price) * 100 * position_size
                    exits.append({
                        'type': 'TP',
                        'price': exit_price,
                        'size': position_size,
                        'pnl': ((entry_price - exit_price) / entry_price) * 100 * position_size
                    })
                    position_size = 0
                    break
        
        # Timeout
        if position_size > 0:
            exit_price = df_future['close'].iloc[-1]
            if direction == 1:
                pnl += ((exit_price - entry_price) / entry_price) * 100 * position_size
            else:
                pnl += ((entry_price - exit_price) / entry_price) * 100 * position_size
            
            exits.append({
                'type': 'TIMEOUT',
                'price': exit_price,
                'size': position_size,
                'pnl': pnl - sum(e['pnl'] for e in exits)
            })
        
        total_pnl += pnl
        
        trades.append({
            'entry_time': entry_time,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'pnl': pnl,
            'exits': exits,
            'partial_tp_hit': any(e['type'] == 'Partial TP' for e in exits)
        })
    
    wins = len([t for t in trades if t['pnl'] > 0])
    
    print(f"\n✅ IMPROVED Backtest Complete:")
    print(f"   Signals: {len(df_signals)}")
    print(f"   Trades: {len(trades)}")
    print(f"   Win Rate: {wins/len(trades)*100:.1f}%")
    print(f"   Total PnL: {total_pnl:+.2f}%")
    print(f"   Partial TPs hit: {len([t for t in trades if t['partial_tp_hit']])}")
    
    return trades, total_pnl


def compare_baseline_vs_improved(df):
    """Сравнение baseline vs improved"""
    
    print("\n" + "="*100)
    print("СРАВНЕНИЕ: BASELINE vs IMPROVED")
    print("="*100)
    
    # Baseline
    print("\n1️⃣  BASELINE (оригинальная стратегия)")
    baseline = PatternRecognitionStrategy(fib_mode='standard')
    baseline_trades, baseline_pnl = backtest_improved_with_partial_tp(df, baseline)
    
    # Improved
    print("\n2️⃣  IMPROVED (с фильтрами и partial TP)")
    improved = PatternRecognitionImproved(fib_mode='standard', min_atr_percentile=25)
    improved_trades, improved_pnl = backtest_improved_with_partial_tp(df, improved)
    
    # Comparison
    print("\n" + "="*100)
    print("📊 ИТОГОВОЕ СРАВНЕНИЕ")
    print("="*100)
    
    print(f"\n{'Метрика':<30} {'Baseline':<20} {'Improved':<20} {'Разница':<20}")
    print("-" * 90)
    
    baseline_trades_count = len(baseline_trades)
    improved_trades_count = len(improved_trades)
    
    baseline_wr = len([t for t in baseline_trades if t['pnl'] > 0]) / baseline_trades_count * 100
    improved_wr = len([t for t in improved_trades if t['pnl'] > 0]) / improved_trades_count * 100
    
    print(f"{'Сделок':<30} {baseline_trades_count:<20} {improved_trades_count:<20} {improved_trades_count - baseline_trades_count:+}")
    print(f"{'Win Rate':<30} {baseline_wr:<19.1f}% {improved_wr:<19.1f}% {improved_wr - baseline_wr:+.1f}%")
    print(f"{'Total PnL':<30} {baseline_pnl:<19.2f}% {improved_pnl:<19.2f}% {improved_pnl - baseline_pnl:+.2f}%")
    
    baseline_avg = baseline_pnl / baseline_trades_count
    improved_avg = improved_pnl / improved_trades_count
    print(f"{'Avg PnL per trade':<30} {baseline_avg:<19.2f}% {improved_avg:<19.2f}% {improved_avg - baseline_avg:+.2f}%")
    
    # Profit Factor
    baseline_wins_pnl = sum(t['pnl'] for t in baseline_trades if t['pnl'] > 0)
    baseline_losses_pnl = abs(sum(t['pnl'] for t in baseline_trades if t['pnl'] < 0))
    baseline_pf = baseline_wins_pnl / baseline_losses_pnl if baseline_losses_pnl > 0 else 0
    
    improved_wins_pnl = sum(t['pnl'] for t in improved_trades if t['pnl'] > 0)
    improved_losses_pnl = abs(sum(t['pnl'] for t in improved_trades if t['pnl'] < 0))
    improved_pf = improved_wins_pnl / improved_losses_pnl if improved_losses_pnl > 0 else 0
    
    print(f"{'Profit Factor':<30} {baseline_pf:<19.2f} {improved_pf:<19.2f} {improved_pf - baseline_pf:+.2f}")
    
    # Partial TP stats
    baseline_partial = len([t for t in baseline_trades if t['partial_tp_hit']])
    improved_partial = len([t for t in improved_trades if t['partial_tp_hit']])
    
    print(f"{'Partial TPs hit':<30} {baseline_partial:<20} {improved_partial:<20} {improved_partial - baseline_partial:+}")
    
    print("\n" + "="*100)
    
    improvement_pct = (improved_pnl - baseline_pnl) / baseline_pnl * 100
    
    if improvement_pct > 5:
        print(f"✅ УЛУЧШЕНИЕ: +{improvement_pct:.1f}% по PnL!")
    elif improvement_pct > 0:
        print(f"⚠️ Небольшое улучшение: +{improvement_pct:.1f}%")
    else:
        print(f"❌ Ухудшение: {improvement_pct:.1f}%")
    
    print("="*100)
    
    return {
        'baseline': {
            'trades': baseline_trades_count,
            'win_rate': baseline_wr,
            'pnl': baseline_pnl,
            'pf': baseline_pf
        },
        'improved': {
            'trades': improved_trades_count,
            'win_rate': improved_wr,
            'pnl': improved_pnl,
            'pf': improved_pf
        }
    }


def main():
    print("\n" + "="*100)
    print("ТЕСТИРОВАНИЕ УЛУЧШЕННОЙ СТРАТЕГИИ")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Compare
    results = compare_baseline_vs_improved(df)
    
    return results


if __name__ == "__main__":
    results = main()
