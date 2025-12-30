"""
Тест SHORT с фильтром по тренду
Проверяем улучшается ли SHORT с фильтром
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from pattern_recognition_strategy import PatternRecognitionStrategy


def load_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load H1 data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    # Add trend indicators
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['ema_200'] = df['close'].ewm(span=200).mean()
    
    # Trend conditions
    df['is_uptrend'] = (df['ema_20'] > df['ema_50']) & (df['ema_50'] > df['ema_200'])
    df['is_downtrend'] = (df['ema_20'] < df['ema_50']) & (df['ema_50'] < df['ema_200'])
    
    # Strong downtrend (additional conditions)
    df['ema_200_falling'] = df['ema_200'].diff(5) < 0
    df['below_ema_200'] = df['close'] < df['ema_200']
    df['strong_downtrend'] = df['is_downtrend'] & df['ema_200_falling'] & df['below_ema_200']
    
    return df


def backtest_with_trend_filter(df, strategy, short_filter='none'):
    """
    Backtest with SHORT filter
    
    short_filter options:
    - 'none': No filter (original)
    - 'downtrend': SHORT only in downtrend
    - 'strong_downtrend': SHORT only in STRONG downtrend
    - 'disabled': No SHORT at all
    """
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    # Apply SHORT filter
    filtered_signals = df_signals.copy()
    
    if short_filter == 'disabled':
        # Remove all SHORT
        filtered_signals = filtered_signals[filtered_signals['signal'] == 1]
        
    elif short_filter == 'downtrend':
        # SHORT only in downtrend
        short_mask = (filtered_signals['signal'] == -1)
        for idx in filtered_signals[short_mask].index:
            if idx in df.index:
                if not df.loc[idx, 'is_downtrend']:
                    filtered_signals = filtered_signals.drop(idx)
    
    elif short_filter == 'strong_downtrend':
        # SHORT only in STRONG downtrend
        short_mask = (filtered_signals['signal'] == -1)
        for idx in filtered_signals[short_mask].index:
            if idx in df.index:
                if not df.loc[idx, 'strong_downtrend']:
                    filtered_signals = filtered_signals.drop(idx)
    
    trades = []
    
    for i in range(len(filtered_signals)):
        signal = filtered_signals.iloc[i]
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']
        
        entry_time = filtered_signals.index[i]
        search_end = entry_time + timedelta(hours=48)
        
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        exit_price = None
        exit_type = None
        
        # Find exit
        for j in range(len(df_future)):
            if direction == 1:  # LONG
                if df_future['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif df_future['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break
            else:  # SHORT
                if df_future['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif df_future['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'
        
        # Calculate PnL %
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        trades.append({
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'pnl_pct': pnl_pct
        })
    
    return pd.DataFrame(trades)


def calculate_stats(df_trades, name):
    """Calculate stats"""
    
    if len(df_trades) == 0:
        return {
            'name': name,
            'trades': 0,
            'long_trades': 0,
            'short_trades': 0,
            'win_rate': 0,
            'long_wr': 0,
            'short_wr': 0,
            'total_pnl': 0
        }
    
    long_trades = df_trades[df_trades['direction'] == 'LONG']
    short_trades = df_trades[df_trades['direction'] == 'SHORT']
    
    wins = df_trades[df_trades['pnl_pct'] > 0]
    long_wins = long_trades[long_trades['pnl_pct'] > 0]
    short_wins = short_trades[short_trades['pnl_pct'] > 0]
    
    return {
        'name': name,
        'trades': len(df_trades),
        'long_trades': len(long_trades),
        'short_trades': len(short_trades),
        'win_rate': len(wins) / len(df_trades) * 100,
        'long_wr': len(long_wins) / len(long_trades) * 100 if len(long_trades) > 0 else 0,
        'short_wr': len(short_wins) / len(short_trades) * 100 if len(short_trades) > 0 else 0,
        'total_pnl': df_trades['pnl_pct'].sum()
    }


def main():
    print("\n" + "="*80)
    print("🔍 ТЕСТ: SHORT С ФИЛЬТРОМ ПО ТРЕНДУ")
    print("="*80)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df = load_data()
    print(f"   ✅ {len(df)} H1 свечей")
    
    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Test configurations
    configs = [
        ('Оригинал (без фильтра)', 'none'),
        ('SHORT только в downtrend', 'downtrend'),
        ('SHORT только в STRONG downtrend', 'strong_downtrend'),
        ('SHORT отключен', 'disabled')
    ]
    
    results = []
    
    for name, filter_type in configs:
        print(f"\n🔄 Тестирование: {name}...")
        
        df_trades = backtest_with_trend_filter(df, strategy, filter_type)
        stats = calculate_stats(df_trades, name)
        results.append(stats)
        
        print(f"   Всего: {stats['trades']} (LONG: {stats['long_trades']}, SHORT: {stats['short_trades']})")
        print(f"   Win Rate: {stats['win_rate']:.1f}%")
        print(f"   Total PnL: {stats['total_pnl']:+.2f}%")
    
    # Display comparison table
    print("\n" + "="*80)
    print("📊 СРАВНИТЕЛЬНАЯ ТАБЛИЦА")
    print("="*80)
    
    print(f"\n{'Конфигурация':<40} | {'Всего':<8} | {'SHORT':<8} | {'SHORT WR':<10} | {'Total PnL':<12} | {'Улучшение':<12}")
    print("-" * 110)
    
    baseline_pnl = results[0]['total_pnl']
    
    for stats in results:
        improvement = stats['total_pnl'] - baseline_pnl
        emoji = "✅" if stats['win_rate'] >= 60 else "⚠️" if stats['win_rate'] >= 55 else "❌"
        
        print(f"{stats['name']:<40} {emoji} | {stats['trades']:<8} | {stats['short_trades']:<8} | {stats['short_wr']:<10.1f}% | {stats['total_pnl']:<+12.2f}% | {improvement:<+12.2f}%")
    
    # Detailed SHORT analysis
    print("\n" + "="*80)
    print("📉 ДЕТАЛЬНЫЙ АНАЛИЗ SHORT")
    print("="*80)
    
    print(f"\n{'Конфигурация':<40} | {'SHORT сделок':<15} | {'SHORT WR':<12} | {'SHORT PnL':<12}")
    print("-" * 90)
    
    for stats in results:
        if stats['short_trades'] > 0:
            print(f"{stats['name']:<40} | {stats['short_trades']:<15} | {stats['short_wr']:<12.1f}% | {'N/A':<12}")
    
    # Final recommendation
    print("\n" + "="*80)
    print("🏆 ИТОГОВАЯ РЕКОМЕНДАЦИЯ")
    print("="*80)
    
    best = max(results, key=lambda x: x['total_pnl'])
    
    print(f"\n✅ Лучшая конфигурация: {best['name']}")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Total PnL: {best['total_pnl']:+.2f}%")
    print(f"   Улучшение: {best['total_pnl'] - baseline_pnl:+.2f}%")
    
    # Compare SHORT quality
    original_short_wr = results[0]['short_wr']
    downtrend_short_wr = results[1]['short_wr']
    strong_downtrend_short_wr = results[2]['short_wr']
    
    print(f"\n📊 Качество SHORT:")
    print(f"   Оригинал: {original_short_wr:.1f}%")
    print(f"   С downtrend filter: {downtrend_short_wr:.1f}%")
    print(f"   С STRONG downtrend filter: {strong_downtrend_short_wr:.1f}%")
    
    if downtrend_short_wr > original_short_wr:
        improvement = downtrend_short_wr - original_short_wr
        print(f"\n✅ Фильтр по тренду улучшает SHORT на {improvement:.1f}%")
        
        if downtrend_short_wr >= 50:
            print(f"   ✅ РЕКОМЕНДУЮ: Оставить SHORT с downtrend фильтром")
        else:
            print(f"   ⚠️  Даже с фильтром SHORT WR < 50%")
            print(f"   ✅ РЕКОМЕНДУЮ: Отключить SHORT полностью")
    else:
        print(f"\n❌ Фильтр НЕ улучшает SHORT")
        print(f"   ✅ РЕКОМЕНДУЮ: Отключить SHORT полностью")
    
    print("\n✅ Тест завершен!")


if __name__ == "__main__":
    main()
