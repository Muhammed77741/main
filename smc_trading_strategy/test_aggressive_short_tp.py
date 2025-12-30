"""
Тест: SHORT с очень агрессивным TP + Trend Exit
Цель: быстро фиксировать прибыль до разворота
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
    
    # Add EMA20
    df['ema_20'] = df['close'].ewm(span=20).mean()
    
    return df


def backtest_aggressive_tp(df, strategy, short_tp_multiplier=1.618):
    """
    Backtest with aggressive TP for SHORT
    
    short_tp_multiplier: 0.8, 1.0, 1.2, 1.618, etc.
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
        
        # Adjust TP for SHORT
        if direction == -1:
            risk = abs(entry_price - stop_loss)
            take_profit = entry_price - (risk * short_tp_multiplier)
        
        entry_time = df_signals.index[i]
        search_end = entry_time + timedelta(hours=48)
        
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        exit_price = None
        exit_type = None
        
        # Find exit
        for j in range(len(df_future)):
            future_time = df_future.index[j]
            
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
                # Regular SL/TP
                if df_future['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif df_future['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break
                
                # Trend Exit (цена > EMA20)
                if future_time in df.index:
                    close_price = df_future['close'].iloc[j]
                    ema_20 = df.loc[future_time, 'ema_20']
                    
                    if close_price > ema_20:
                        exit_price = close_price
                        exit_type = 'TREND_EXIT'
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
            'short': 0,
            'win_rate': 0,
            'short_wr': 0,
            'short_tp': 0,
            'short_trend': 0,
            'short_sl': 0,
            'total_pnl': 0
        }
    
    short_trades = df_trades[df_trades['direction'] == 'SHORT']
    
    wins = df_trades[df_trades['pnl_pct'] > 0]
    short_wins = short_trades[short_trades['pnl_pct'] > 0]
    
    short_tp = len(short_trades[short_trades['exit_type'] == 'TP'])
    short_trend = len(short_trades[short_trades['exit_type'] == 'TREND_EXIT'])
    short_sl = len(short_trades[short_trades['exit_type'] == 'SL'])
    
    return {
        'name': name,
        'trades': len(df_trades),
        'short': len(short_trades),
        'win_rate': len(wins) / len(df_trades) * 100,
        'short_wr': len(short_wins) / len(short_trades) * 100 if len(short_trades) > 0 else 0,
        'short_tp': short_tp,
        'short_trend': short_trend,
        'short_sl': short_sl,
        'total_pnl': df_trades['pnl_pct'].sum()
    }


def main():
    print("\n" + "="*100)
    print("🎯 ТЕСТ: АГРЕССИВНЫЙ TP ДЛЯ SHORT")
    print("Цель: быстро фиксировать прибыль до разворота")
    print("="*100)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df = load_data()
    print(f"   ✅ {len(df)} H1 свечей")
    
    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Test different TP multipliers
    configs = [
        ('Оригинал (1.618R)', 1.618),
        ('TP = 1.2R', 1.2),
        ('TP = 1.0R', 1.0),
        ('TP = 0.8R (агрессивный)', 0.8),
        ('TP = 0.6R (очень агрессивный)', 0.6),
        ('TP = 0.5R (экстремальный)', 0.5),
    ]
    
    results = []
    
    for name, tp_mult in configs:
        print(f"\n🔄 Тестирование: {name}...")
        
        df_trades = backtest_aggressive_tp(df, strategy, tp_mult)
        stats = calculate_stats(df_trades, name)
        results.append(stats)
        
        print(f"   SHORT: {stats['short']} сделок, WR {stats['short_wr']:.1f}%")
        print(f"   SHORT выходы: TP={stats['short_tp']}, Trend={stats['short_trend']}, SL={stats['short_sl']}")
        print(f"   Total PnL: {stats['total_pnl']:+.2f}%")
    
    # Comparison table
    print("\n" + "="*100)
    print("📊 СРАВНИТЕЛЬНАЯ ТАБЛИЦА")
    print("="*100)
    
    print(f"\n{'Конфигурация':<35} | {'SHORT WR':<10} | {'TP':<6} | {'Trend':<6} | {'SL':<6} | {'Total PnL':<12} | {'Улучшение':<12}")
    print("-" * 110)
    
    baseline_pnl = results[0]['total_pnl']
    
    for stats in results:
        improvement = stats['total_pnl'] - baseline_pnl
        
        # Emoji based on PnL
        if stats['total_pnl'] > 386:
            emoji = "🚀"  # Better than disabling SHORT
        elif stats['total_pnl'] > 370:
            emoji = "✅"  # Good
        elif stats['total_pnl'] > 350:
            emoji = "⚠️"  # OK
        else:
            emoji = "❌"  # Bad
        
        print(f"{stats['name']:<35} {emoji} | {stats['short_wr']:<10.1f}% | {stats['short_tp']:<6} | {stats['short_trend']:<6} | {stats['short_sl']:<6} | {stats['total_pnl']:<+12.2f}% | {improvement:<+12.2f}%")
    
    # Analysis
    print("\n" + "="*100)
    print("🎓 ДЕТАЛЬНЫЙ АНАЛИЗ")
    print("="*100)
    
    print(f"\n📊 SHORT Win Rate по TP:")
    for stats in results:
        tp_rate = stats['short_tp'] / stats['short'] * 100 if stats['short'] > 0 else 0
        print(f"   {stats['name']:<35}: WR {stats['short_wr']:>5.1f}%, TP hit {tp_rate:>5.1f}% ({stats['short_tp']}/{stats['short']})")
    
    print(f"\n💰 Total PnL:")
    for stats in results:
        vs_disabled = stats['total_pnl'] - 386
        marker = "🚀" if vs_disabled > 0 else "⚠️"
        print(f"   {stats['name']:<35}: {stats['total_pnl']:>+8.2f}% {marker} (vs disabled SHORT: {vs_disabled:+.2f}%)")
    
    # Find best
    best = max(results, key=lambda x: x['total_pnl'])
    
    print("\n" + "="*100)
    print("🏆 ИТОГОВАЯ РЕКОМЕНДАЦИЯ")
    print("="*100)
    
    print(f"\n✅ Лучшая конфигурация: {best['name']}")
    print(f"   SHORT Win Rate: {best['short_wr']:.1f}%")
    print(f"   SHORT TP hit: {best['short_tp']}/{best['short']} ({best['short_tp']/best['short']*100:.1f}%)")
    print(f"   Total PnL: {best['total_pnl']:+.2f}%")
    print(f"   Улучшение vs оригинал: {best['total_pnl'] - baseline_pnl:+.2f}%")
    
    if best['total_pnl'] > 386:
        print(f"\n🎯 ЭТО ЛУЧШЕ ЧЕМ ОТКЛЮЧИТЬ SHORT!")
        print(f"   Отключить SHORT: +386%")
        print(f"   {best['name']}: {best['total_pnl']:+.2f}%")
        print(f"   Выигрыш: {best['total_pnl'] - 386:+.2f}%")
        
        print(f"\n💡 ПРИМЕНИТЬ В БОТ:")
        print(f"   1. SHORT TP = {configs[[r['name'] for r in results].index(best['name'])][1]}R")
        print(f"   2. Trend Exit когда цена > EMA20")
    elif best['total_pnl'] > 370:
        print(f"\n⚠️  Лучше чем оригинал, но хуже чем отключить SHORT")
        print(f"   {best['name']}: {best['total_pnl']:+.2f}%")
        print(f"   Отключить SHORT: +386%")
        print(f"   Разница: {386 - best['total_pnl']:.2f}%")
    else:
        print(f"\n❌ Не помогает")
        print(f"   РЕКОМЕНДУЮ: Отключить SHORT (+386%)")
    
    print("\n✅ Тест завершен!")


if __name__ == "__main__":
    main()
