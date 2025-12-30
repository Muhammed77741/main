"""
Честное сравнение H1 vs H4+H1 с одинаковой методологией
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from pattern_recognition_strategy import PatternRecognitionStrategy
from multi_timeframe import MultiTimeframeData


def load_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load H1 data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    return df


def create_h4_from_h1(df_h1):
    """Create H4 from H1"""
    df_h4 = df_h1.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    return df_h4


def detect_h4_trend(df_h4, lookback=20):
    """Detect H4 trend"""
    if len(df_h4) < lookback:
        return 'SIDEWAYS'
    
    recent = df_h4.iloc[-lookback:]
    ema_fast = recent['close'].ewm(span=10, adjust=False).mean()
    ema_slow = recent['close'].ewm(span=20, adjust=False).mean()
    
    current_fast = ema_fast.iloc[-1]
    current_slow = ema_slow.iloc[-1]
    diff_pct = ((current_fast - current_slow) / current_slow) * 100
    
    price_start = recent['close'].iloc[0]
    price_end = recent['close'].iloc[-1]
    price_change_pct = ((price_end - price_start) / price_start) * 100
    
    if diff_pct > 0.2 and price_change_pct > 1.0:
        return 'UP'
    elif diff_pct < -0.2 and price_change_pct < -1.0:
        return 'DOWN'
    else:
        return 'SIDEWAYS'


def backtest_with_details(df, strategy):
    """Run backtest like monthly_analysis - simple % summation"""
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    print(f"   Найдено сигналов: {len(df_signals)}")
    
    trades = []
    
    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']
        
        entry_time = df_signals.index[i]
        search_end = entry_time + timedelta(hours=48)
        
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        exit_price = None
        exit_type = None
        exit_time = None
        
        # Find exit
        for j in range(len(df_future)):
            if direction == 1:  # LONG
                if df_future['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break
            else:  # SHORT
                if df_future['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'
            exit_time = df_future.index[-1]
        
        # Calculate PnL %
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct
        })
    
    return trades


def main():
    print("\n" + "="*80)
    print("🔄 ЧЕСТНОЕ СРАВНЕНИЕ H1 vs H4+H1 (одинаковая методология)")
    print("="*80)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df_h1 = load_data()
    print(f"   ✅ {len(df_h1)} H1 свечей")
    
    # Create H4
    df_h4 = create_h4_from_h1(df_h1)
    print(f"   ✅ {len(df_h4)} H4 свечей (создано из H1)")
    
    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # ==========================================
    # TEST 1: H1 ONLY
    # ==========================================
    print("\n" + "="*80)
    print("📈 БЭКТЕСТ #1: H1 ТОЛЬКО (без фильтра)")
    print("="*80)
    
    trades_h1 = backtest_with_details(df_h1, strategy)
    
    print(f"\n📊 Результаты H1:")
    print(f"   Всего сделок: {len(trades_h1)}")
    
    if len(trades_h1) > 0:
        wins_h1 = [t for t in trades_h1 if t['pnl_pct'] > 0]
        losses_h1 = [t for t in trades_h1 if t['pnl_pct'] <= 0]
        
        total_pnl_h1 = sum([t['pnl_pct'] for t in trades_h1])
        win_rate_h1 = len(wins_h1) / len(trades_h1) * 100
        
        print(f"   Win Rate: {win_rate_h1:.1f}%")
        print(f"   Прибыльных: {len(wins_h1)}")
        print(f"   Убыточных: {len(losses_h1)}")
        print(f"   Общий PnL: {total_pnl_h1:+.2f}%")
        print(f"   Средний PnL: {total_pnl_h1/len(trades_h1):+.2f}%")
    
    # ==========================================
    # TEST 2: H4 + H1 (with filter)
    # ==========================================
    print("\n" + "="*80)
    print("📈 БЭКТЕСТ #2: H4+H1 (с фильтром по тренду)")
    print("="*80)
    
    # Run strategy
    df_strategy = strategy.run_strategy(df_h1.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    print(f"   Сигналов до фильтра: {len(df_signals)}")
    
    # Apply H4 filter
    filtered_signals = []
    filtered_count = 0
    
    for idx in df_signals.index:
        signal = df_signals.loc[idx]
        
        # Find H4 trend
        h4_candles = df_h4[df_h4.index <= idx]
        
        if len(h4_candles) >= 20:
            h4_trend = detect_h4_trend(h4_candles, lookback=20)
            
            # Filter logic
            if signal['signal'] == 1 and h4_trend == 'DOWN':
                filtered_count += 1
                continue  # Skip LONG against DOWN
            elif signal['signal'] == -1 and h4_trend == 'UP':
                filtered_count += 1
                continue  # Skip SHORT against UP
        
        filtered_signals.append(idx)
    
    print(f"   Отфильтровано сигналов: {filtered_count}")
    print(f"   Сигналов после фильтра: {len(filtered_signals)}")
    
    # Create filtered dataframe
    df_signals_filtered = df_signals.loc[filtered_signals]
    
    # Run backtest on filtered signals
    trades_h4h1 = []
    
    for i in range(len(df_signals_filtered)):
        signal = df_signals_filtered.iloc[i]
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']
        
        entry_time = df_signals_filtered.index[i]
        search_end = entry_time + timedelta(hours=48)
        
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        exit_price = None
        exit_type = None
        exit_time = None
        
        for j in range(len(df_future)):
            if direction == 1:  # LONG
                if df_future['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break
            else:  # SHORT
                if df_future['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'
            exit_time = df_future.index[-1]
        
        # Calculate PnL %
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        trades_h4h1.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct
        })
    
    print(f"\n📊 Результаты H4+H1:")
    print(f"   Всего сделок: {len(trades_h4h1)}")
    
    if len(trades_h4h1) > 0:
        wins_h4h1 = [t for t in trades_h4h1 if t['pnl_pct'] > 0]
        losses_h4h1 = [t for t in trades_h4h1 if t['pnl_pct'] <= 0]
        
        total_pnl_h4h1 = sum([t['pnl_pct'] for t in trades_h4h1])
        win_rate_h4h1 = len(wins_h4h1) / len(trades_h4h1) * 100
        
        print(f"   Win Rate: {win_rate_h4h1:.1f}%")
        print(f"   Прибыльных: {len(wins_h4h1)}")
        print(f"   Убыточных: {len(losses_h4h1)}")
        print(f"   Общий PnL: {total_pnl_h4h1:+.2f}%")
        print(f"   Средний PnL: {total_pnl_h4h1/len(trades_h4h1):+.2f}%")
    
    # ==========================================
    # COMPARISON
    # ==========================================
    print("\n" + "="*80)
    print("📊 СРАВНЕНИЕ (одинаковая методология)")
    print("="*80)
    
    print(f"\n{'Метрика':<25} | {'H1 только':<15} | {'H4+H1':<15} | {'Разница':<15}")
    print("-" * 80)
    
    print(f"{'Всего сделок':<25} | {len(trades_h1):<15} | {len(trades_h4h1):<15} | {len(trades_h4h1)-len(trades_h1):<15}")
    print(f"{'Win Rate':<25} | {win_rate_h1:<15.1f} | {win_rate_h4h1:<15.1f} | {win_rate_h4h1-win_rate_h1:+<15.1f}")
    print(f"{'Общий PnL %':<25} | {total_pnl_h1:<+15.2f} | {total_pnl_h4h1:<+15.2f} | {total_pnl_h4h1-total_pnl_h1:+<15.2f}")
    print(f"{'Средний PnL %':<25} | {total_pnl_h1/len(trades_h1):<+15.2f} | {total_pnl_h4h1/len(trades_h4h1):<+15.2f} | {(total_pnl_h4h1/len(trades_h4h1))-(total_pnl_h1/len(trades_h1)):+<15.2f}")
    print(f"{'Отфильтровано':<25} | {0:<15} | {filtered_count:<15} | {filtered_count:<15}")
    
    print("\n" + "="*80)
    print("🎯 ВЫВОДЫ")
    print("="*80)
    
    improvement = total_pnl_h4h1 - total_pnl_h1
    
    if improvement > 0:
        print(f"\n✅ H4 фильтр УЛУЧШИЛ результаты на {improvement:+.2f}%!")
        print(f"   Отфильтровано {filtered_count} плохих сигналов")
    else:
        print(f"\n❌ H4 фильтр УХУДШИЛ результаты на {improvement:+.2f}%")
        print(f"   Отфильтровал {filtered_count} сигналов, включая прибыльные")
    
    print(f"\n📊 Детали:")
    print(f"   H1: {len(trades_h1)} сделок, {total_pnl_h1:+.2f}% общий PnL")
    print(f"   H4+H1: {len(trades_h4h1)} сделок, {total_pnl_h4h1:+.2f}% общий PnL")
    print(f"   Улучшение: {improvement:+.2f}%")
    
    print("\n✅ Сравнение завершено!")


if __name__ == "__main__":
    main()
