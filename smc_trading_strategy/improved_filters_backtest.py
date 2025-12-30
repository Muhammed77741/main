"""
Бэктест с улучшенными фильтрами
Цель: улучшить прибыль БЕЗ сильного уменьшения количества сигналов
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
    
    # Add ATR
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    
    return df


def backtest_original(df, strategy):
    """Original backtest (no filters)"""
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
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


def backtest_improved(df, strategy, filters):
    """
    Improved backtest with filters
    
    filters = {
        'disable_short': True/False,
        'best_hours_only': True/False,
        'best_hours': [8, 13, 14],
        'min_atr': None or value
    }
    """
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    # Add hour and ATR info
    df_signals['hour'] = df_signals.index.hour
    
    # Get ATR values
    atr_values = []
    for idx in df_signals.index:
        if idx in df.index:
            atr_values.append(df.loc[idx, 'atr'])
        else:
            atr_values.append(np.nan)
    df_signals['atr'] = atr_values
    
    # Apply filters
    filtered_signals = df_signals.copy()
    
    # Filter 1: Disable SHORT
    if filters.get('disable_short', False):
        filtered_signals = filtered_signals[filtered_signals['signal'] == 1]
    
    # Filter 2: Best hours only
    if filters.get('best_hours_only', False):
        best_hours = filters.get('best_hours', [8, 9, 10, 13, 14, 15])
        filtered_signals = filtered_signals[filtered_signals['hour'].isin(best_hours)]
    
    # Filter 3: Min ATR
    if filters.get('min_atr') is not None:
        filtered_signals = filtered_signals[filtered_signals['atr'] >= filters['min_atr']]
    
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
    """Calculate backtest stats"""
    
    if len(df_trades) == 0:
        return {
            'name': name,
            'trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_win': 0,
            'avg_loss': 0
        }
    
    wins = df_trades[df_trades['pnl_pct'] > 0]
    losses = df_trades[df_trades['pnl_pct'] <= 0]
    
    return {
        'name': name,
        'trades': len(df_trades),
        'win_rate': len(wins) / len(df_trades) * 100,
        'total_pnl': df_trades['pnl_pct'].sum(),
        'avg_win': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['pnl_pct'].mean() if len(losses) > 0 else 0
    }


def main():
    print("\n" + "="*80)
    print("🚀 ТЕСТИРОВАНИЕ УЛУЧШЕННЫХ ФИЛЬТРОВ")
    print("Цель: увеличить прибыль БЕЗ сильного уменьшения сигналов")
    print("="*80)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df = load_data()
    print(f"   ✅ {len(df)} H1 свечей")
    
    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Test configurations
    configs = [
        {
            'name': 'Оригинал (без фильтров)',
            'filters': {}
        },
        {
            'name': 'LONG только',
            'filters': {'disable_short': True}
        },
        {
            'name': 'Лучшие часы (8-10, 13-15)',
            'filters': {'best_hours_only': True, 'best_hours': [8, 9, 10, 13, 14, 15]}
        },
        {
            'name': 'LONG + Лучшие часы',
            'filters': {
                'disable_short': True,
                'best_hours_only': True,
                'best_hours': [8, 9, 10, 13, 14, 15]
            }
        },
        {
            'name': 'LONG + Топ часы (8, 13)',
            'filters': {
                'disable_short': True,
                'best_hours_only': True,
                'best_hours': [8, 13]
            }
        },
        {
            'name': 'LONG + Расширенные часы (8-15)',
            'filters': {
                'disable_short': True,
                'best_hours_only': True,
                'best_hours': [8, 9, 10, 11, 12, 13, 14, 15]
            }
        }
    ]
    
    results = []
    
    for config in configs:
        print(f"\n🔄 Тестирование: {config['name']}...")
        
        if len(config['filters']) == 0:
            # Original
            df_trades = backtest_original(df, strategy)
        else:
            # Improved with filters
            df_trades = backtest_improved(df, strategy, config['filters'])
        
        stats = calculate_stats(df_trades, config['name'])
        results.append(stats)
        
        print(f"   Сделок: {stats['trades']}")
        print(f"   Win Rate: {stats['win_rate']:.1f}%")
        print(f"   Total PnL: {stats['total_pnl']:+.2f}%")
    
    # Display comparison table
    print("\n" + "="*80)
    print("📊 СРАВНИТЕЛЬНАЯ ТАБЛИЦА")
    print("="*80)
    
    print(f"\n{'Конфигурация':<35} | {'Сделок':<8} | {'Win Rate':<10} | {'Total PnL':<12} | {'Улучшение':<12}")
    print("-" * 100)
    
    baseline_pnl = results[0]['total_pnl']
    
    for stats in results:
        improvement = stats['total_pnl'] - baseline_pnl
        emoji = "✅" if stats['win_rate'] >= 65 else "⚠️" if stats['win_rate'] >= 55 else "❌"
        
        print(f"{stats['name']:<35} {emoji} | {stats['trades']:<8} | {stats['win_rate']:<10.1f}% | {stats['total_pnl']:<+12.2f}% | {improvement:<+12.2f}%")
    
    # Find best config
    best = max(results, key=lambda x: x['total_pnl'])
    
    print("\n" + "="*80)
    print("🏆 ЛУЧШАЯ КОНФИГУРАЦИЯ")
    print("="*80)
    
    print(f"\n✅ {best['name']}")
    print(f"   Сделок: {best['trades']}")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Total PnL: {best['total_pnl']:+.2f}%")
    print(f"   Улучшение vs базовая: {best['total_pnl'] - baseline_pnl:+.2f}% (+{(best['total_pnl'] / baseline_pnl - 1) * 100:.1f}%)")
    
    print("\n" + "="*80)
    print("💡 РЕКОМЕНДАЦИИ ДЛЯ paper_trading_improved.py")
    print("="*80)
    
    print("\n1️⃣  Отключить SHORT сделки ✅")
    print("   Код: if signal['direction'] == 'SHORT': continue")
    
    print("\n2️⃣  Добавить фильтр по времени ✅")
    print("   Лучшие часы: [8, 9, 10, 13, 14, 15]")
    print("   Код: if current_hour not in [8,9,10,13,14,15]: skip_signal")
    
    print("\n3️⃣  Динамический trailing stop (зависит от ATR) 💡")
    print("   Низкая волатильность: trailing = 12 пунктов")
    print("   Высокая волатильность: trailing = 20 пунктов")
    
    print("\n✅ Готово! Хотите, чтобы я применил эти фильтры к paper_trading_improved.py?")


if __name__ == "__main__":
    main()
