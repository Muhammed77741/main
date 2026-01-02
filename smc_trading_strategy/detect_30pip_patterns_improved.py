"""
Улучшенная версия детектора с Partial TP на 30 пипсах

Ключевое улучшение:
- Когда цена достигает 30 пипсов, закрываем 50% позиции
- Остальные 50% оставляем до full TP или trailing SL
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from detect_30pip_patterns import ThirtyPipMoveDetector


def backtest_with_partial_tp(df, detector, partial_tp_pips=30, partial_close=0.5):
    """
    Бэктест с Partial TP на 30 пипсах
    
    Args:
        df: DataFrame с данными
        detector: Детектор паттернов
        partial_tp_pips: Пипсов для partial TP (default: 30)
        partial_close: Какую часть закрывать (default: 0.5 = 50%)
    """
    
    print(f"\n🔍 Backtesting with Partial TP ({partial_tp_pips} pips, {partial_close*100:.0f}% close)...")
    
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
        
        # Partial TP price
        partial_tp_price = entry_price + (partial_tp_pips * 0.10)
        
        # Look forward
        search_end = entry_time + timedelta(hours=24)
        df_future = df[(df.index > entry_time) & (df.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Track position
        position_size = 1.0
        total_pnl_pips = 0
        exits = []
        max_profit_pips = 0
        
        # Trailing SL после partial TP
        trailing_sl = stop_loss
        trailing_active = False
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            if position_size <= 0:
                break
            
            # Track max profit
            current_profit_dollars = candle['high'] - entry_price
            current_profit_pips = current_profit_dollars / 0.10
            max_profit_pips = max(max_profit_pips, current_profit_pips)
            
            # Partial TP
            if position_size == 1.0 and candle['high'] >= partial_tp_price:
                exit_pips = partial_tp_pips
                exit_size = partial_close
                total_pnl_pips += exit_pips * exit_size
                position_size -= exit_size
                
                exits.append({
                    'type': f'Partial TP ({partial_tp_pips}p)',
                    'size': exit_size,
                    'pips': exit_pips * exit_size
                })
                
                # Activate trailing SL (move to breakeven)
                trailing_sl = entry_price
                trailing_active = True
                continue
            
            # Update trailing SL
            if trailing_active and position_size > 0:
                # Trail at 50% of profit
                current_high = candle['high']
                potential_profit = (current_high - entry_price) / 0.10
                
                if potential_profit > partial_tp_pips:
                    new_trailing = entry_price + ((potential_profit - partial_tp_pips) * 0.5 * 0.10)
                    trailing_sl = max(trailing_sl, new_trailing)
            
            # Check SL (or trailing SL)
            active_sl = trailing_sl if trailing_active else stop_loss
            
            if candle['low'] <= active_sl:
                exit_dollars = active_sl - entry_price
                exit_pips = exit_dollars / 0.10
                total_pnl_pips += exit_pips * position_size
                
                exits.append({
                    'type': 'SL' if not trailing_active else 'Trailing SL',
                    'size': position_size,
                    'pips': exit_pips * position_size
                })
                
                position_size = 0
                break
            
            # Check full TP
            if candle['high'] >= take_profit:
                exit_pips = (take_profit - entry_price) / 0.10
                total_pnl_pips += exit_pips * position_size
                
                exits.append({
                    'type': 'Full TP',
                    'size': position_size,
                    'pips': exit_pips * position_size
                })
                
                position_size = 0
                break
        
        # Timeout
        if position_size > 0:
            exit_price = df_future['close'].iloc[-1]
            exit_pips = (exit_price - entry_price) / 0.10
            total_pnl_pips += exit_pips * position_size
            
            exits.append({
                'type': 'TIMEOUT',
                'size': position_size,
                'pips': exit_pips * position_size
            })
        
        # Save trade
        partial_tp_hit = any(e['type'].startswith('Partial TP') for e in exits)
        
        trades.append({
            'entry_time': entry_time,
            'pattern': signal['pattern'],
            'type': signal['type'],
            'confidence': signal['confidence'],
            'entry_price': entry_price,
            'pnl_pips': total_pnl_pips,
            'max_profit_pips': max_profit_pips,
            'reached_30pips': max_profit_pips >= 30,
            'partial_tp_hit': partial_tp_hit,
            'exits': exits
        })
    
    trades_df = pd.DataFrame(trades)
    
    # Results
    print(f"\n✅ Backtest Complete:")
    print(f"   {'='*80}")
    print(f"   Total Trades:        {len(trades_df)}")
    
    if len(trades_df) > 0:
        wins = len(trades_df[trades_df['pnl_pips'] > 0])
        win_rate = wins / len(trades_df) * 100
        
        reached_30 = len(trades_df[trades_df['reached_30pips'] == True])
        reach_rate = reached_30 / len(trades_df) * 100
        
        partial_hit = len(trades_df[trades_df['partial_tp_hit'] == True])
        partial_rate = partial_hit / len(trades_df) * 100
        
        avg_pnl = trades_df['pnl_pips'].mean()
        total_pnl = trades_df['pnl_pips'].sum()
        
        print(f"   Win Rate:            {win_rate:.1f}%")
        print(f"   Reached 30+ pips:    {reached_30} ({reach_rate:.1f}%)")
        print(f"   Partial TP hit:      {partial_hit} ({partial_rate:.1f}%) ⭐")
        print(f"   Avg PnL:             {avg_pnl:+.1f} pips")
        print(f"   Total PnL:           {total_pnl:+.0f} pips")
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
        
        # By confidence
        print(f"\n   By Confidence:")
        for conf in ['HIGH', 'MEDIUM']:
            conf_trades = trades_df[trades_df['confidence'] == conf]
            if len(conf_trades) > 0:
                conf_wr = len(conf_trades[conf_trades['pnl_pips'] > 0]) / len(conf_trades) * 100
                conf_avg = conf_trades['pnl_pips'].mean()
                conf_total = conf_trades['pnl_pips'].sum()
                
                print(f"      {conf:10s}: {len(conf_trades):3d} trades | "
                      f"WR {conf_wr:5.1f}% | Avg {conf_avg:+6.1f}p | Total {conf_total:+8.0f}p")
    
    return trades_df


def compare_strategies(df, detector):
    """Сравнение: без partial TP vs с partial TP"""
    
    print(f"\n" + "="*100)
    print("СРАВНЕНИЕ: БЕЗ PARTIAL TP vs С PARTIAL TP")
    print("="*100)
    
    # 1. Without partial TP (original)
    print(f"\n1️⃣  WITHOUT Partial TP:")
    from detect_30pip_patterns import backtest_30pip_detector
    trades_no_partial = backtest_30pip_detector(df, detector)
    
    # 2. With partial TP
    print(f"\n2️⃣  WITH Partial TP (30 pips, 50% close):")
    trades_with_partial = backtest_with_partial_tp(df, detector, partial_tp_pips=30, partial_close=0.5)
    
    # Compare
    print(f"\n" + "="*100)
    print("📊 COMPARISON TABLE")
    print("="*100)
    
    if len(trades_no_partial) > 0 and len(trades_with_partial) > 0:
        no_wr = len(trades_no_partial[trades_no_partial['pnl_pips'] > 0]) / len(trades_no_partial) * 100
        no_pnl = trades_no_partial['pnl_pips'].sum()
        no_avg = trades_no_partial['pnl_pips'].mean()
        
        with_wr = len(trades_with_partial[trades_with_partial['pnl_pips'] > 0]) / len(trades_with_partial) * 100
        with_pnl = trades_with_partial['pnl_pips'].sum()
        with_avg = trades_with_partial['pnl_pips'].mean()
        
        print(f"\n{'Strategy':<30} {'Trades':<10} {'Win Rate':<12} {'Total PnL':<15} {'Avg PnL':<12}")
        print("-"*80)
        print(f"{'Without Partial TP':<30} {len(trades_no_partial):<10} {no_wr:>10.1f}% {no_pnl:>+13.0f}p {no_avg:>+10.1f}p")
        print(f"{'With Partial TP (30p)':<30} {len(trades_with_partial):<10} {with_wr:>10.1f}% {with_pnl:>+13.0f}p {with_avg:>+10.1f}p")
        print("-"*80)
        
        improvement = with_pnl - no_pnl
        improvement_pct = (improvement / abs(no_pnl)) * 100 if no_pnl != 0 else 0
        
        print(f"{'IMPROVEMENT':<30} {'':10s} {with_wr - no_wr:>+10.1f}% {improvement:>+13.0f}p {with_avg - no_avg:>+10.1f}p")
        
        print(f"\n💰 Improvement:")
        print(f"   Total PnL:  {improvement:+.0f} pips ({improvement_pct:+.1f}%)")
        print(f"   Win Rate:   {with_wr - no_wr:+.1f}%")
        
        if improvement > 0:
            print(f"\n✅ Partial TP улучшает результаты на {improvement:+.0f} пипсов!")
        else:
            print(f"\n⚠️ Partial TP ухудшает результаты на {improvement:.0f} пипсов")
    
    return trades_no_partial, trades_with_partial


def main():
    print("\n" + "="*100)
    print("УЛУЧШЕННЫЙ ДЕТЕКТОР С PARTIAL TP НА 30 ПИПСАХ")
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
    
    # Compare strategies
    trades_no_partial, trades_with_partial = compare_strategies(df, detector)
    
    # Save
    if len(trades_with_partial) > 0:
        trades_with_partial.to_csv('30pip_patterns_partial_tp.csv', index=False)
        print(f"\n💾 Results saved: 30pip_patterns_partial_tp.csv")
    
    return detector, trades_with_partial


if __name__ == "__main__":
    detector, trades_df = main()
