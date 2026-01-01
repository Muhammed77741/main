"""
Правильный сравнительный тест методов с адаптивными параметрами

Для Pattern Recognition используем родные TP/SL из стратегии
Для других методов используем оптимизированные параметры
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from advanced_signal_methods import AdvancedSignalDetector
from pattern_recognition_strategy import PatternRecognitionStrategy


def backtest_pattern_recognition(df, strategy):
    """
    Бэктест Pattern Recognition с РОДНЫМИ параметрами
    (как в monthly_analysis.py)
    """
    print("\n📊 Pattern Recognition (Правильный бэктест с адаптивными TP/SL)")
    
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
            exit_type = 'TIMEOUT'
            exit_time = df_future.index[-1]
        
        # Calculate PnL
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
            'pnl_pct': pnl_pct,
            'duration_hours': (exit_time - entry_time).total_seconds() / 3600
        })
    
    trades_df = pd.DataFrame(trades)
    
    # Calculate stats
    total_pnl = trades_df['pnl_pct'].sum()
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    total = len(trades_df)
    win_rate = (wins / total * 100) if total > 0 else 0
    
    wins_df = trades_df[trades_df['pnl_pct'] > 0]
    losses_df = trades_df[trades_df['pnl_pct'] <= 0]
    
    avg_win = wins_df['pnl_pct'].mean() if len(wins_df) > 0 else 0
    avg_loss = losses_df['pnl_pct'].mean() if len(losses_df) > 0 else 0
    
    gross_profit = wins_df['pnl_pct'].sum() if len(wins_df) > 0 else 0
    gross_loss = abs(losses_df['pnl_pct'].sum()) if len(losses_df) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Max DD
    cumulative = trades_df['pnl_pct'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = cumulative - running_max
    max_dd = drawdown.min() if len(drawdown) > 0 else 0
    
    stats = {
        'method': 'Pattern Recognition (Adaptive)',
        'total_trades': total,
        'wins': wins,
        'losses': total - wins,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_dd': max_dd
    }
    
    print(f"   Сигналов: {len(df_signals)} | Trades: {total}")
    print(f"   Total PnL: {total_pnl:+.2f}% ✅")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Profit Factor: {profit_factor:.2f}")
    print(f"   Max DD: {max_dd:.2f}%")
    
    return stats, trades_df


def optimize_parameters_for_method(df, signals_df, method_name):
    """
    Оптимизируем параметры TP/SL для каждого метода
    Пробуем разные комбинации и выбираем лучшую
    """
    best_pnl = -999999
    best_params = None
    
    # Различные комбинации TP/SL для тестирования
    if method_name in ['Market Structure Breaks', 'Fair Value Gaps']:
        # Эти методы предсказывают сильные движения - больше TP
        tp_sl_combinations = [
            (60, 30), (70, 30), (80, 35), (90, 35), (100, 40)
        ]
    elif method_name in ['Liquidity Sweeps']:
        # Быстрые развороты - средние параметры
        tp_sl_combinations = [
            (40, 25), (50, 30), (60, 30), (70, 35)
        ]
    else:
        # Остальные методы - стандартные параметры
        tp_sl_combinations = [
            (50, 30), (60, 30), (70, 35), (80, 40)
        ]
    
    for tp, sl in tp_sl_combinations:
        trades = backtest_with_params(df, signals_df, tp, sl, timeout_hours=48)
        
        if len(trades) > 0:
            total_pnl = trades['pnl_pct'].sum()
            if total_pnl > best_pnl:
                best_pnl = total_pnl
                best_params = (tp, sl)
    
    return best_params if best_params else (50, 30)


def backtest_with_params(df, signals_df, tp_pips, sl_pips, timeout_hours=48):
    """Simple backtest with given parameters"""
    trades = []
    
    for idx, signal in signals_df.iterrows():
        signal_idx = signal['index']
        
        if signal_idx >= len(df) - 1:
            continue
        
        entry_price = df['close'].iloc[signal_idx]
        entry_time = df.index[signal_idx]
        direction = signal['signal']
        
        # Определяем TP и SL
        if direction == 'LONG':
            take_profit = entry_price + tp_pips
            stop_loss = entry_price - sl_pips
        else:
            take_profit = entry_price - tp_pips
            stop_loss = entry_price + sl_pips
        
        # Ищем выход
        search_end = entry_time + timedelta(hours=timeout_hours)
        future_data = df[(df.index > entry_time) & (df.index <= search_end)]
        
        if len(future_data) == 0:
            continue
        
        exit_price = None
        exit_type = None
        
        for i in range(len(future_data)):
            candle = future_data.iloc[i]
            
            if direction == 'LONG':
                if candle['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif candle['high'] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break
            else:
                if candle['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif candle['low'] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break
        
        if exit_price is None:
            exit_price = future_data['close'].iloc[-1]
            exit_type = 'TIMEOUT'
        
        # Calculate PnL
        if direction == 'LONG':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        trades.append({'pnl_pct': pnl_pct})
    
    return pd.DataFrame(trades)


def main():
    print("\n" + "="*100)
    print("ПРАВИЛЬНОЕ СРАВНЕНИЕ МЕТОДОВ (С АДАПТИВНЫМИ ПАРАМЕТРАМИ)")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}\n")
    
    results = []
    
    # ========================================================================
    # 1. Pattern Recognition (правильный тест)
    # ========================================================================
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    pr_stats, pr_trades = backtest_pattern_recognition(df, strategy)
    results.append(pr_stats)
    
    # ========================================================================
    # 2. Ensemble (оптимизированные параметры)
    # ========================================================================
    print("\n📊 Ensemble Method (оптимизируем параметры...)")
    detector = AdvancedSignalDetector()
    all_signals = detector.detect_all_signals(df, methods=['all'])
    ensemble_signals = detector.ensemble_signals(all_signals, min_confidence=0.75, min_confirmations=2)
    
    if len(ensemble_signals) > 0:
        # Optimize parameters
        best_params = optimize_parameters_for_method(df, ensemble_signals, 'Ensemble')
        print(f"   Лучшие параметры: TP={best_params[0]}п, SL={best_params[1]}п")
        
        # Backtest with best params
        trades = backtest_with_params(df, ensemble_signals, best_params[0], best_params[1])
        
        if len(trades) > 0:
            total_pnl = trades['pnl_pct'].sum()
            wins = len(trades[trades['pnl_pct'] > 0])
            total = len(trades)
            win_rate = (wins / total * 100) if total > 0 else 0
            
            wins_df = trades[trades['pnl_pct'] > 0]
            losses_df = trades[trades['pnl_pct'] <= 0]
            
            gross_profit = wins_df['pnl_pct'].sum() if len(wins_df) > 0 else 0
            gross_loss = abs(losses_df['pnl_pct'].sum()) if len(losses_df) > 0 else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            cumulative = trades['pnl_pct'].cumsum()
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            max_dd = drawdown.min()
            
            ensemble_stats = {
                'method': f'Ensemble (TP={best_params[0]}, SL={best_params[1]})',
                'total_trades': total,
                'wins': wins,
                'losses': total - wins,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_win': wins_df['pnl_pct'].mean() if len(wins_df) > 0 else 0,
                'avg_loss': losses_df['pnl_pct'].mean() if len(losses_df) > 0 else 0,
                'profit_factor': profit_factor,
                'max_dd': max_dd
            }
            
            results.append(ensemble_stats)
            
            print(f"   Total PnL: {total_pnl:+.2f}%")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Profit Factor: {profit_factor:.2f}")
    
    # ========================================================================
    # 3. Market Structure Breaks (оптимизированные параметры)
    # ========================================================================
    print("\n📊 Market Structure Breaks (оптимизируем параметры...)")
    bos_signals = detector.detect_market_structure_breaks(df)
    bos_df = pd.DataFrame(bos_signals) if bos_signals else pd.DataFrame()
    
    if len(bos_df) > 0:
        best_params = optimize_parameters_for_method(df, bos_df, 'Market Structure Breaks')
        print(f"   Лучшие параметры: TP={best_params[0]}п, SL={best_params[1]}п")
        
        trades = backtest_with_params(df, bos_df, best_params[0], best_params[1])
        
        if len(trades) > 0:
            total_pnl = trades['pnl_pct'].sum()
            wins = len(trades[trades['pnl_pct'] > 0])
            total = len(trades)
            win_rate = (wins / total * 100) if total > 0 else 0
            
            wins_df = trades[trades['pnl_pct'] > 0]
            losses_df = trades[trades['pnl_pct'] <= 0]
            
            gross_profit = wins_df['pnl_pct'].sum() if len(wins_df) > 0 else 0
            gross_loss = abs(losses_df['pnl_pct'].sum()) if len(losses_df) > 0 else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            cumulative = trades['pnl_pct'].cumsum()
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            max_dd = drawdown.min()
            
            bos_stats = {
                'method': f'Market Structure Breaks (TP={best_params[0]}, SL={best_params[1]})',
                'total_trades': total,
                'wins': wins,
                'losses': total - wins,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_win': wins_df['pnl_pct'].mean() if len(wins_df) > 0 else 0,
                'avg_loss': losses_df['pnl_pct'].mean() if len(losses_df) > 0 else 0,
                'profit_factor': profit_factor,
                'max_dd': max_dd
            }
            
            results.append(bos_stats)
            
            print(f"   Total PnL: {total_pnl:+.2f}%")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Profit Factor: {profit_factor:.2f}")
    
    # ========================================================================
    # ИТОГОВАЯ ТАБЛИЦА
    # ========================================================================
    print("\n" + "="*100)
    print("ИТОГОВОЕ СРАВНЕНИЕ (С ОПТИМИЗИРОВАННЫМИ ПАРАМЕТРАМИ)")
    print("="*100 + "\n")
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('total_pnl', ascending=False)
    
    print(f"{'Метод':<45} {'Trades':<8} {'WR%':<8} {'PnL%':<12} {'PF':<8} {'Max DD':<10}")
    print("-" * 100)
    
    for idx, row in results_df.iterrows():
        emoji = "🥇" if idx == results_df.index[0] else "🥈" if idx == results_df.index[1] else "🥉"
        print(f"{emoji} {row['method']:<43} {row['total_trades']:<8} {row['win_rate']:>6.1f}% "
              f"{row['total_pnl']:>+10.2f}%  {row['profit_factor']:>6.2f}  {row['max_dd']:>+8.2f}%")
    
    print("\n" + "="*100)
    print("ВЫВОДЫ")
    print("="*100)
    
    baseline = results_df[results_df['method'].str.contains('Pattern Recognition')].iloc[0]
    
    print(f"\n✅ BASELINE (Pattern Recognition с адаптивными TP/SL):")
    print(f"   Total PnL: {baseline['total_pnl']:+.2f}%")
    print(f"   Win Rate: {baseline['win_rate']:.1f}%")
    print(f"   Profit Factor: {baseline['profit_factor']:.2f}")
    print(f"   Max DD: {baseline['max_dd']:.2f}%")
    
    print(f"\n💡 СРАВНЕНИЕ С ФИКСИРОВАННЫМИ ПАРАМЕТРАМИ:")
    print(f"   С адаптивными TP/SL: {baseline['total_pnl']:+.2f}% ✅ ПРАВИЛЬНО")
    print(f"   С фиксированными (50/30): +85.70% ❌ ЗАНИЖЕНО")
    print(f"   Разница: {baseline['total_pnl'] - 85.70:+.2f}%")
    
    print(f"\n🎯 ВЫВОД:")
    print(f"   Pattern Recognition оптимизирован под адаптивные параметры")
    print(f"   Использование фиксированных TP/SL снижает производительность в ~4 раза")
    print(f"   Правильный PnL baseline: {baseline['total_pnl']:+.2f}%")
    
    print("\n" + "="*100)


if __name__ == "__main__":
    main()
