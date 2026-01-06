"""
Backtest with Multiple TP Levels - Using Fixed SimplifiedSMCStrategy
Tests partial position closing at different TP levels
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from simplified_smc_strategy import SimplifiedSMCStrategy


def load_mt5_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load MT5 XAUUSD data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    # Add market hours
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])
    
    return df


def backtest_multi_tp(df, strategy, tp_config, variant_name):
    """
    Backtest with multiple TP levels
    
    Args:
        tp_config: dict with 'tp_levels' (points) and 'close_pcts' (%)
        Example: {'tp_levels': [20, 35, 50], 'close_pcts': [0.5, 0.3, 0.2]}
    """
    
    print(f"\n{'='*80}")
    print(f"ВАРИАНТ: {variant_name}")
    print(f"{'='*80}")
    
    tp_levels = tp_config['tp_levels']
    close_pcts = tp_config['close_pcts']
    
    print(f"\n🎯 Конфигурация TP:")
    for i, (tp, pct) in enumerate(zip(tp_levels, close_pcts), 1):
        print(f"   TP{i}: {tp}п → закрыть {pct*100:.0f}% позиции")
    print(f"   Таймаут: 48 часов")
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    print(f"\n🔍 Найдено сигналов: {len(df_signals)}")
    
    trades = []
    tp_stats = {f'tp{i+1}_hits': 0 for i in range(len(tp_levels))}
    tp_stats['sl_hits'] = 0
    tp_stats['timeout'] = 0
    
    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        direction = signal['signal']
        entry_time = df_signals.index[i]
        
        # Track position
        position_remaining = 1.0
        total_pnl_pct = 0.0
        
        exit_type = 'TIMEOUT'
        exit_time = None
        tp_hits = []
        
        # Calculate TP prices
        if direction == 1:  # LONG
            tp_prices = [entry_price + tp for tp in tp_levels]
        else:  # SHORT
            tp_prices = [entry_price - tp for tp in tp_levels]
        
        # Look ahead 48 hours
        search_end = entry_time + timedelta(hours=48)
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Check each candle
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            candle_time = df_future.index[j]
            
            if position_remaining <= 0:
                break
            
            # Check SL first
            if direction == 1:  # LONG
                if candle['low'] <= stop_loss:
                    # SL hit - close remaining position
                    pnl_pct = ((stop_loss - entry_price) / entry_price) * 100 * position_remaining
                    total_pnl_pct += pnl_pct
                    exit_type = 'SL'
                    exit_time = candle_time
                    tp_stats['sl_hits'] += 1
                    position_remaining = 0
                    break
            else:  # SHORT
                if candle['high'] >= stop_loss:
                    # SL hit - close remaining position
                    pnl_pct = ((entry_price - stop_loss) / entry_price) * 100 * position_remaining
                    total_pnl_pct += pnl_pct
                    exit_type = 'SL'
                    exit_time = candle_time
                    tp_stats['sl_hits'] += 1
                    position_remaining = 0
                    break
            
            # Check TPs
            for tp_idx, (tp_price, close_pct) in enumerate(zip(tp_prices, close_pcts)):
                if tp_idx in tp_hits:
                    continue  # Already hit
                
                tp_hit = False
                if direction == 1:  # LONG
                    if candle['high'] >= tp_price:
                        tp_hit = True
                else:  # SHORT
                    if candle['low'] <= tp_price:
                        tp_hit = True
                
                if tp_hit:
                    # Close this portion
                    close_amount = close_pct
                    if close_amount > position_remaining:
                        close_amount = position_remaining
                    
                    if direction == 1:
                        pnl_pct = ((tp_price - entry_price) / entry_price) * 100 * close_amount
                    else:
                        pnl_pct = ((entry_price - tp_price) / entry_price) * 100 * close_amount
                    
                    total_pnl_pct += pnl_pct
                    position_remaining -= close_amount
                    tp_hits.append(tp_idx)
                    tp_stats[f'tp{tp_idx+1}_hits'] += 1
                    
                    if not exit_time:
                        exit_time = candle_time
                    
                    if position_remaining <= 0.01:  # All closed
                        exit_type = f'TP1-{len(tp_hits)}'
                        position_remaining = 0
                        break
        
        # If position still open after timeout
        if position_remaining > 0:
            # Close at last price
            last_candle = df_future.iloc[-1]
            last_price = last_candle['close']
            
            if direction == 1:
                pnl_pct = ((last_price - entry_price) / entry_price) * 100 * position_remaining
            else:
                pnl_pct = ((entry_price - last_price) / entry_price) * 100 * position_remaining
            
            total_pnl_pct += pnl_pct
            exit_type = 'TIMEOUT'
            exit_time = df_future.index[-1]
            tp_stats['timeout'] += 1
        
        # Save trade
        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'pnl_pct': total_pnl_pct,
            'exit_type': exit_type,
            'tp_hits': len(tp_hits),
            'tp_levels_hit': ','.join([f'TP{i+1}' for i in tp_hits])
        })
    
    # Calculate stats
    if not trades:
        print("\n❌ Нет сделок!")
        return None
    
    df_trades = pd.DataFrame(trades)
    
    # Basic stats
    total_pnl = df_trades['pnl_pct'].sum()
    wins = df_trades[df_trades['pnl_pct'] > 0]
    losses = df_trades[df_trades['pnl_pct'] <= 0]
    
    win_rate = (len(wins) / len(df_trades)) * 100 if len(df_trades) > 0 else 0
    
    avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
    
    profit_factor = abs(wins['pnl_pct'].sum() / losses['pnl_pct'].sum()) if len(losses) > 0 and losses['pnl_pct'].sum() != 0 else float('inf')
    
    # Print results
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"   Сделок: {len(df_trades)}")
    print(f"   Выигрышей: {len(wins)} ({win_rate:.1f}%)")
    print(f"   Проигрышей: {len(losses)} ({100-win_rate:.1f}%)")
    print(f"   Total P&L: {total_pnl:+.2f}%")
    print(f"   Средний выигрыш: +{avg_win:.2f}%")
    print(f"   Средний проигрыш: {avg_loss:.2f}%")
    print(f"   Profit Factor: {profit_factor:.2f}")
    
    print(f"\n🎯 Статистика по TP:")
    for i in range(len(tp_levels)):
        hits = tp_stats[f'tp{i+1}_hits']
        pct = (hits / len(df_trades)) * 100 if len(df_trades) > 0 else 0
        print(f"   TP{i+1} ({tp_levels[i]}п): {hits} раз ({pct:.1f}% сделок)")
    print(f"   Stop Loss: {tp_stats['sl_hits']} раз ({tp_stats['sl_hits']/len(df_trades)*100:.1f}%)")
    print(f"   Timeout: {tp_stats['timeout']} раз ({tp_stats['timeout']/len(df_trades)*100:.1f}%)")
    
    # TP combination stats
    print(f"\n💎 Комбинации TP:")
    tp_combos = df_trades['tp_levels_hit'].value_counts()
    for combo, count in tp_combos.head(5).items():
        pct = (count / len(df_trades)) * 100
        print(f"   {combo if combo else 'Нет TP'}: {count} раз ({pct:.1f}%)")
    
    return {
        'variant': variant_name,
        'total_pnl': total_pnl,
        'trades': len(df_trades),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'tp_stats': tp_stats,
        'df_trades': df_trades
    }


def main():
    print("\n" + "=" * 80)
    print("БЭКТЕСТ С МУЛЬТИТП - ИСПРАВЛЕННАЯ СТРАТЕГИЯ")
    print("=" * 80)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df = load_mt5_data()
    print(f"   Загружено {len(df)} свечей")
    print(f"   Период: {df.index[0]} - {df.index[-1]}")
    
    # Initialize strategy (with fixed SL/TP bug)
    strategy = SimplifiedSMCStrategy()
    
    # Test configurations
    configs = [
        {
            'name': 'Консервативный (50-30-20)',
            'tp_levels': [20, 35, 50],
            'close_pcts': [0.5, 0.3, 0.2]
        },
        {
            'name': 'Сбалансированный (40-30-30)',
            'tp_levels': [25, 40, 60],
            'close_pcts': [0.4, 0.3, 0.3]
        },
        {
            'name': 'Агрессивный (30-30-40)',
            'tp_levels': [30, 50, 80],
            'close_pcts': [0.3, 0.3, 0.4]
        }
    ]
    
    results = []
    
    for config in configs:
        result = backtest_multi_tp(
            df, 
            strategy, 
            {'tp_levels': config['tp_levels'], 'close_pcts': config['close_pcts']},
            config['name']
        )
        if result:
            results.append(result)
    
    # Compare results
    if results:
        print("\n" + "=" * 80)
        print("СРАВНЕНИЕ ВАРИАНТОВ")
        print("=" * 80)
        
        for result in results:
            print(f"\n{result['variant']}:")
            print(f"   Total P&L: {result['total_pnl']:+.2f}%")
            print(f"   Win Rate: {result['win_rate']:.1f}%")
            print(f"   Profit Factor: {result['profit_factor']:.2f}")
            print(f"   Trades: {result['trades']}")
        
        # Best variant
        best = max(results, key=lambda x: x['total_pnl'])
        print(f"\n🏆 ЛУЧШИЙ ВАРИАНТ: {best['variant']}")
        print(f"   P&L: {best['total_pnl']:+.2f}%")
    
    print("\n" + "=" * 80)
    print("✅ Анализ завершён!")
    print("=" * 80)


if __name__ == '__main__':
    main()
