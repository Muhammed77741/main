"""
Тест: SHORT с закрытием при смене тренда + меньший TP
Идея: оставить все SHORT входы, но закрывать при цена > EMA20
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
    
    return df


def backtest_with_smart_exit(df, strategy, config='original'):
    """
    Backtest with different SHORT exit strategies
    
    config options:
    - 'original': Обычный SL/TP
    - 'trend_exit': Закрывать SHORT когда цена > EMA20
    - 'smaller_tp': TP для SHORT = 1.2x вместо 1.618x
    - 'both': Trend exit + smaller TP
    """
    
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
        
        # Adjust TP for SHORT if needed
        if direction == -1 and config in ['smaller_tp', 'both']:
            # Smaller TP for SHORT
            risk = abs(entry_price - stop_loss)
            take_profit = entry_price - (risk * 1.2)  # 1.2R instead of 1.618R
        
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
            future_time = df_future.index[j]
            
            if direction == 1:  # LONG
                if df_future['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = future_time
                    break
                elif df_future['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = future_time
                    break
            
            else:  # SHORT
                # Check regular SL/TP
                if df_future['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = future_time
                    break
                elif df_future['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = future_time
                    break
                
                # TREND EXIT for SHORT (если включено)
                if config in ['trend_exit', 'both']:
                    # Закрыть SHORT если цена пересекла EMA20 вверх
                    if future_time in df.index:
                        close_price = df_future['close'].iloc[j]
                        ema_20 = df.loc[future_time, 'ema_20']
                        
                        # Цена выше EMA20 = тренд меняется, закрыть SHORT
                        if close_price > ema_20:
                            exit_price = close_price
                            exit_type = 'TREND_EXIT'
                            exit_time = future_time
                            break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'
            exit_time = df_future.index[-1]
        
        # Calculate PnL
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        trades.append({
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'exit_type': exit_type,
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
            'short_wr': 0,
            'short_tp': 0,
            'short_trend_exit': 0,
            'short_sl': 0,
            'total_pnl': 0
        }
    
    long_trades = df_trades[df_trades['direction'] == 'LONG']
    short_trades = df_trades[df_trades['direction'] == 'SHORT']
    
    wins = df_trades[df_trades['pnl_pct'] > 0]
    short_wins = short_trades[short_trades['pnl_pct'] > 0]
    
    # SHORT exit types
    short_tp = len(short_trades[short_trades['exit_type'] == 'TP'])
    short_trend_exit = len(short_trades[short_trades['exit_type'] == 'TREND_EXIT'])
    short_sl = len(short_trades[short_trades['exit_type'] == 'SL'])
    
    return {
        'name': name,
        'trades': len(df_trades),
        'long': len(long_trades),
        'short': len(short_trades),
        'win_rate': len(wins) / len(df_trades) * 100,
        'short_wr': len(short_wins) / len(short_trades) * 100 if len(short_trades) > 0 else 0,
        'short_tp': short_tp,
        'short_trend_exit': short_trend_exit,
        'short_sl': short_sl,
        'total_pnl': df_trades['pnl_pct'].sum()
    }


def main():
    print("\n" + "="*100)
    print("🎯 ТЕСТ: SHORT С УМНЫМ ВЫХОДОМ")
    print("Идея: Закрывать SHORT при смене тренда + меньший TP")
    print("="*100)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df = load_data()
    print(f"   ✅ {len(df)} H1 свечей")
    
    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Test configurations
    configs = [
        ('Оригинал', 'original'),
        ('Trend Exit (цена > EMA20)', 'trend_exit'),
        ('Меньший TP (1.2R)', 'smaller_tp'),
        ('Trend Exit + Меньший TP', 'both'),
    ]
    
    results = []
    
    for name, config in configs:
        print(f"\n🔄 Тестирование: {name}...")
        
        df_trades = backtest_with_smart_exit(df, strategy, config)
        stats = calculate_stats(df_trades, name)
        results.append(stats)
        
        print(f"   Всего: {stats['trades']} (SHORT: {stats['short']})")
        if stats['short'] > 0:
            print(f"   SHORT Win Rate: {stats['short_wr']:.1f}%")
            if config != 'original':
                print(f"   SHORT выходы: TP={stats['short_tp']}, Trend Exit={stats['short_trend_exit']}, SL={stats['short_sl']}")
        print(f"   Total PnL: {stats['total_pnl']:+.2f}%")
    
    # Comparison table
    print("\n" + "="*100)
    print("📊 СРАВНИТЕЛЬНАЯ ТАБЛИЦА")
    print("="*100)
    
    header = f"{'Конфигурация':<35} | {'SHORT':<8} | {'SHORT WR':<10} | {'TP':<6} | {'Trend':<6} | {'SL':<6} | {'Total PnL':<12} | {'Улучшение':<12}"
    print(f"\n{header}")
    print("-" * 115)
    
    baseline_pnl = results[0]['total_pnl']
    
    for stats in results:
        improvement = stats['total_pnl'] - baseline_pnl
        emoji = "✅" if stats['win_rate'] >= 60 else "⚠️" if stats['win_rate'] >= 55 else "❌"
        
        short_wr_str = f"{stats['short_wr']:.1f}%" if stats['short'] > 0 else "N/A"
        
        print(f"{stats['name']:<35} {emoji} | {stats['short']:<8} | {short_wr_str:<10} | {stats['short_tp']:<6} | {stats['short_trend_exit']:<6} | {stats['short_sl']:<6} | {stats['total_pnl']:<+12.2f}% | {improvement:<+12.2f}%")
    
    # Analysis
    print("\n" + "="*100)
    print("🎓 ДЕТАЛЬНЫЙ АНАЛИЗ")
    print("="*100)
    
    original = results[0]
    trend_exit = results[1]
    smaller_tp = results[2]
    both = results[3]
    
    print(f"\n📊 SHORT Win Rate:")
    print(f"   Оригинал: {original['short_wr']:.1f}%")
    print(f"   + Trend Exit: {trend_exit['short_wr']:.1f}% ({trend_exit['short_wr'] - original['short_wr']:+.1f}%)")
    print(f"   + Меньший TP: {smaller_tp['short_wr']:.1f}% ({smaller_tp['short_wr'] - original['short_wr']:+.1f}%)")
    print(f"   + Оба: {both['short_wr']:.1f}% ({both['short_wr'] - original['short_wr']:+.1f}%)")
    
    print(f"\n💰 Total PnL:")
    print(f"   Оригинал: {original['total_pnl']:+.2f}%")
    print(f"   + Trend Exit: {trend_exit['total_pnl']:+.2f}% ({trend_exit['total_pnl'] - original['total_pnl']:+.2f}%)")
    print(f"   + Меньший TP: {smaller_tp['total_pnl']:+.2f}% ({smaller_tp['total_pnl'] - original['total_pnl']:+.2f}%)")
    print(f"   + Оба: {both['total_pnl']:+.2f}% ({both['total_pnl'] - original['total_pnl']:+.2f}%)")
    
    print(f"\n🚪 SHORT выходы (с Trend Exit + Меньший TP):")
    print(f"   TP: {both['short_tp']} ({both['short_tp']/both['short']*100:.1f}%)")
    print(f"   Trend Exit: {both['short_trend_exit']} ({both['short_trend_exit']/both['short']*100:.1f}%)")
    print(f"   SL: {both['short_sl']} ({both['short_sl']/both['short']*100:.1f}%)")
    
    # Recommendation
    print("\n" + "="*100)
    print("🏆 ИТОГОВАЯ РЕКОМЕНДАЦИЯ")
    print("="*100)
    
    best = max(results[1:], key=lambda x: x['total_pnl'])
    
    print(f"\n✅ Лучшая конфигурация: {best['name']}")
    print(f"   SHORT Win Rate: {best['short_wr']:.1f}%")
    print(f"   Total PnL: {best['total_pnl']:+.2f}%")
    print(f"   Улучшение: {best['total_pnl'] - baseline_pnl:+.2f}%")
    
    if best['total_pnl'] > 386:  # Better than disabling SHORT
        print(f"\n🎯 ЭТО ЛУЧШЕ ЧЕМ ОТКЛЮЧИТЬ SHORT!")
        print(f"   Отключить SHORT: +386%")
        print(f"   {best['name']}: {best['total_pnl']:+.2f}%")
        print(f"   Разница: {best['total_pnl'] - 386:+.2f}%")
        
        print(f"\n💡 ПРИМЕНИТЬ:")
        print(f"   1. Закрывать SHORT когда цена > EMA20")
        print(f"   2. TP для SHORT = 1.2R (вместо 1.618R)")
    else:
        print(f"\n⚠️  Все равно хуже чем отключить SHORT")
        print(f"   Лучший результат: {best['total_pnl']:+.2f}%")
        print(f"   Отключить SHORT: +386%")
    
    print("\n✅ Тест завершен!")


if __name__ == "__main__":
    main()
