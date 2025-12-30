"""
Тест MEAN REVERSION SHORT стратегии
SHORT только когда цена ВЫШЕ EMA (перегрета)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from pattern_recognition_strategy import PatternRecognitionStrategy


def load_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load H1 data with indicators"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    # Add EMAs
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    
    # Distance from EMA
    df['dist_from_ema_20'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100
    
    return df


def backtest_with_mean_reversion_filter(df, strategy, filter_type='none'):
    """
    Backtest with different SHORT filters
    
    filter_type:
    - 'none': No filter
    - 'above_ema20': SHORT only when price ABOVE EMA20
    - 'above_ema50': SHORT only when price ABOVE EMA50
    - 'mean_reversion': Full mean reversion filter
    - 'disabled': No SHORT
    """
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    # Apply filter
    filtered_signals = []
    
    for idx in df_signals.index:
        signal = df_signals.loc[idx]
        direction = signal['signal']
        
        # LONG always pass
        if direction == 1:
            filtered_signals.append(idx)
            continue
        
        # SHORT filters
        if filter_type == 'disabled':
            continue  # Skip all SHORT
        
        elif filter_type == 'above_ema20':
            # SHORT only when price ABOVE EMA20
            if idx in df.index:
                if df.loc[idx, 'close'] > df.loc[idx, 'ema_20']:
                    filtered_signals.append(idx)
        
        elif filter_type == 'above_ema50':
            # SHORT only when price ABOVE EMA50
            if idx in df.index:
                if df.loc[idx, 'close'] > df.loc[idx, 'ema_50']:
                    filtered_signals.append(idx)
        
        elif filter_type == 'mean_reversion':
            # Full mean reversion filter
            if idx in df.index:
                close = df.loc[idx, 'close']
                ema_20 = df.loc[idx, 'ema_20']
                dist = (close - ema_20) / ema_20 * 100
                
                # Price ABOVE EMA20 but not too far (0% to +1%)
                if close > ema_20 and dist <= 1.0:
                    filtered_signals.append(idx)
        
        else:  # 'none'
            filtered_signals.append(idx)
    
    # Filter signals
    df_filtered = df_signals.loc[filtered_signals]
    
    # Backtest
    trades = []
    
    for i in range(len(df_filtered)):
        signal = df_filtered.iloc[i]
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']
        
        entry_time = df_filtered.index[i]
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
        
        # Calculate PnL
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
            'long': 0,
            'short': 0,
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
        'long': len(long_trades),
        'short': len(short_trades),
        'win_rate': len(wins) / len(df_trades) * 100,
        'long_wr': len(long_wins) / len(long_trades) * 100 if len(long_trades) > 0 else 0,
        'short_wr': len(short_wins) / len(short_trades) * 100 if len(short_trades) > 0 else 0,
        'total_pnl': df_trades['pnl_pct'].sum()
    }


def main():
    print("\n" + "="*100)
    print("🎯 ТЕСТ: MEAN REVERSION SHORT")
    print("SHORT только когда цена ВЫШЕ EMA (перегрета)")
    print("="*100)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df = load_data()
    print(f"   ✅ {len(df)} H1 свечей")
    
    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Test configurations
    configs = [
        ('Оригинал (без фильтра)', 'none'),
        ('SHORT выше EMA20', 'above_ema20'),
        ('SHORT выше EMA50', 'above_ema50'),
        ('MEAN REVERSION (выше EMA20, dist 0-1%)', 'mean_reversion'),
        ('SHORT отключен', 'disabled'),
    ]
    
    results = []
    
    for name, filter_type in configs:
        print(f"\n🔄 Тестирование: {name}...")
        
        df_trades = backtest_with_mean_reversion_filter(df, strategy, filter_type)
        stats = calculate_stats(df_trades, name)
        results.append(stats)
        
        print(f"   Всего: {stats['trades']} (LONG: {stats['long']}, SHORT: {stats['short']})")
        if stats['short'] > 0:
            print(f"   SHORT Win Rate: {stats['short_wr']:.1f}%")
        print(f"   Total PnL: {stats['total_pnl']:+.2f}%")
    
    # Comparison table
    print("\n" + "="*100)
    print("📊 СРАВНИТЕЛЬНАЯ ТАБЛИЦА")
    print("="*100)
    
    print(f"\n{'Конфигурация':<45} | {'Всего':<8} | {'SHORT':<8} | {'SHORT WR':<10} | {'Total PnL':<12} | {'Улучшение':<12}")
    print("-" * 110)
    
    baseline_pnl = results[0]['total_pnl']
    
    for stats in results:
        improvement = stats['total_pnl'] - baseline_pnl
        emoji = "✅" if stats['win_rate'] >= 60 else "⚠️" if stats['win_rate'] >= 55 else "❌"
        
        short_wr_str = f"{stats['short_wr']:.1f}%" if stats['short'] > 0 else "N/A"
        
        print(f"{stats['name']:<45} {emoji} | {stats['trades']:<8} | {stats['short']:<8} | {short_wr_str:<10} | {stats['total_pnl']:<+12.2f}% | {improvement:<+12.2f}%")
    
    # Analysis
    print("\n" + "="*100)
    print("🎓 АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("="*100)
    
    original = results[0]
    above_ema20 = results[1]
    mean_reversion = results[3]
    disabled = results[4]
    
    print(f"\n📊 Качество SHORT:")
    print(f"   Оригинал: {original['short']} сделок, WR {original['short_wr']:.1f}%")
    
    if above_ema20['short'] > 0:
        print(f"   Выше EMA20: {above_ema20['short']} сделок, WR {above_ema20['short_wr']:.1f}%")
        print(f"      Улучшение WR: {above_ema20['short_wr'] - original['short_wr']:+.1f}%")
    
    if mean_reversion['short'] > 0:
        print(f"   Mean Reversion: {mean_reversion['short']} сделок, WR {mean_reversion['short_wr']:.1f}%")
        print(f"      Улучшение WR: {mean_reversion['short_wr'] - original['short_wr']:+.1f}%")
    
    print(f"\n💰 Прибыльность:")
    print(f"   Оригинал: {original['total_pnl']:+.2f}%")
    print(f"   SHORT выше EMA20: {above_ema20['total_pnl']:+.2f}% ({above_ema20['total_pnl'] - original['total_pnl']:+.2f}%)")
    print(f"   Mean Reversion: {mean_reversion['total_pnl']:+.2f}% ({mean_reversion['total_pnl'] - original['total_pnl']:+.2f}%)")
    print(f"   SHORT отключен: {disabled['total_pnl']:+.2f}% ({disabled['total_pnl'] - original['total_pnl']:+.2f}%)")
    
    # Recommendation
    print("\n" + "="*100)
    print("🏆 ИТОГОВАЯ РЕКОМЕНДАЦИЯ")
    print("="*100)
    
    best = max(results, key=lambda x: x['total_pnl'])
    
    print(f"\n✅ Лучшая конфигурация: {best['name']}")
    print(f"   Total PnL: {best['total_pnl']:+.2f}%")
    print(f"   Улучшение: {best['total_pnl'] - baseline_pnl:+.2f}%")
    
    if mean_reversion['short'] > 0 and mean_reversion['short_wr'] >= 50:
        print(f"\n✅ MEAN REVERSION SHORT РАБОТАЕТ!")
        print(f"   SHORT WR улучшился: {original['short_wr']:.1f}% → {mean_reversion['short_wr']:.1f}%")
        print(f"   Прибыль: {mean_reversion['total_pnl']:+.2f}%")
        print(f"\n   💡 РЕКОМЕНДУЮ: Применить Mean Reversion фильтр")
    
    elif above_ema20['short'] > 0 and above_ema20['short_wr'] >= 50:
        print(f"\n✅ SHORT ВЫШЕ EMA20 РАБОТАЕТ!")
        print(f"   SHORT WR: {above_ema20['short_wr']:.1f}%")
        print(f"   Прибыль: {above_ema20['total_pnl']:+.2f}%")
        print(f"\n   💡 РЕКОМЕНДУЮ: Использовать фильтр 'выше EMA20'")
    
    else:
        print(f"\n⚠️  Даже с Mean Reversion фильтром SHORT слабый")
        print(f"   💡 РЕКОМЕНДУЮ: Отключить SHORT ({disabled['total_pnl']:+.2f}%)")
    
    print("\n✅ Тест завершен!")


if __name__ == "__main__":
    main()
