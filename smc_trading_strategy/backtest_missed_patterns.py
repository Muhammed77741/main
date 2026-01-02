"""
Бэктест дополнительных паттернов
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2
from missed_patterns_detector import MissedPatternsDetector


def backtest_signals(df, signals_df):
    """
    Простой бэктест сигналов
    """
    
    print(f"\n🔍 Backtesting {len(signals_df)} signals...")
    
    trades = []
    
    for idx, signal in signals_df.iterrows():
        entry_time = signal['time']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        # Find entry in df
        try:
            entry_idx = df.index.get_loc(entry_time)
        except:
            continue
        
        # Look forward
        search_end = entry_time + timedelta(hours=48)
        df_future = df[(df.index > entry_time) & (df.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Find exit
        exit_price = None
        exit_type = None
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            # Check SL
            if candle['low'] <= stop_loss:
                exit_price = stop_loss
                exit_type = 'SL'
                break
            
            # Check TP
            if candle['high'] >= take_profit:
                exit_price = take_profit
                exit_type = 'TP'
                break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'TIMEOUT'
        
        # Calculate PnL
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        
        trades.append({
            'entry_time': entry_time,
            'pattern': signal['pattern'],
            'type': signal['type'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'confidence': signal['confidence']
        })
    
    return pd.DataFrame(trades)


def analyze_results(trades_df):
    """
    Анализ результатов
    """
    
    print(f"\n" + "="*100)
    print("📊 BACKTEST RESULTS")
    print("="*100)
    
    if len(trades_df) == 0:
        print("No trades!")
        return
    
    # Overall stats
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    losses = len(trades_df[trades_df['pnl_pct'] <= 0])
    win_rate = wins / len(trades_df) * 100
    
    total_pnl = trades_df['pnl_pct'].sum()
    avg_pnl = trades_df['pnl_pct'].mean()
    
    wins_pnl = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].sum()
    losses_pnl = abs(trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].sum())
    profit_factor = wins_pnl / losses_pnl if losses_pnl > 0 else 0
    
    print(f"\n📈 Overall Performance:")
    print(f"   Total Trades:    {len(trades_df)}")
    print(f"   Wins:            {wins} ({win_rate:.1f}%)")
    print(f"   Losses:          {losses} ({100-win_rate:.1f}%)")
    print(f"   Total PnL:       {total_pnl:+.2f}%")
    print(f"   Avg PnL:         {avg_pnl:+.2f}%")
    print(f"   Profit Factor:   {profit_factor:.2f}")
    
    # By pattern type
    print(f"\n📊 Performance by Pattern Type:")
    print(f"{'Type':<15} {'Trades':<10} {'Win Rate':<12} {'Total PnL':<15} {'Avg PnL':<12} {'PF':<10}")
    print("-"*80)
    
    for pattern_type in trades_df['type'].unique():
        type_trades = trades_df[trades_df['type'] == pattern_type]
        
        type_wins = len(type_trades[type_trades['pnl_pct'] > 0])
        type_wr = type_wins / len(type_trades) * 100
        type_total_pnl = type_trades['pnl_pct'].sum()
        type_avg_pnl = type_trades['pnl_pct'].mean()
        
        type_wins_pnl = type_trades[type_trades['pnl_pct'] > 0]['pnl_pct'].sum()
        type_losses_pnl = abs(type_trades[type_trades['pnl_pct'] < 0]['pnl_pct'].sum())
        type_pf = type_wins_pnl / type_losses_pnl if type_losses_pnl > 0 else 0
        
        print(f"{pattern_type:<15} {len(type_trades):<10} {type_wr:>10.1f}% {type_total_pnl:>+13.2f}% {type_avg_pnl:>+10.2f}% {type_pf:>9.2f}")
    
    # By confidence
    print(f"\n📊 Performance by Confidence:")
    print(f"{'Confidence':<15} {'Trades':<10} {'Win Rate':<12} {'Total PnL':<15} {'Avg PnL':<12}")
    print("-"*70)
    
    for confidence in ['HIGH', 'MEDIUM', 'LOW']:
        conf_trades = trades_df[trades_df['confidence'] == confidence]
        
        if len(conf_trades) > 0:
            conf_wins = len(conf_trades[conf_trades['pnl_pct'] > 0])
            conf_wr = conf_wins / len(conf_trades) * 100
            conf_total_pnl = conf_trades['pnl_pct'].sum()
            conf_avg_pnl = conf_trades['pnl_pct'].mean()
            
            print(f"{confidence:<15} {len(conf_trades):<10} {conf_wr:>10.1f}% {conf_total_pnl:>+13.2f}% {conf_avg_pnl:>+10.2f}%")


def compare_with_baseline(df):
    """
    Сравнение с baseline стратегией
    """
    
    print(f"\n" + "="*100)
    print("🔄 COMPARISON: BASELINE vs BASELINE + MISSED PATTERNS")
    print("="*100)
    
    # 1. Baseline strategy
    print(f"\n1️⃣  Running Baseline Strategy...")
    baseline_strategy = PatternRecognitionOptimizedV2(
        fib_mode='standard',
        tp_multiplier=1.4,
        long_only=True
    )
    
    # Backtest baseline (simple)
    df_baseline = baseline_strategy.run_strategy(df.copy())
    baseline_signals = df_baseline[df_baseline['signal'] != 0].copy()
    
    print(f"   Baseline signals: {len(baseline_signals)}")
    
    # Quick backtest baseline
    baseline_trades = []
    for i in range(len(baseline_signals)):
        signal = baseline_signals.iloc[i]
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        entry_time = baseline_signals.index[i]
        
        search_end = entry_time + timedelta(hours=48)
        df_future = df_baseline[(df_baseline.index > entry_time) & (df_baseline.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        exit_price = None
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            if candle['low'] <= stop_loss:
                exit_price = stop_loss
                break
            elif candle['high'] >= take_profit:
                exit_price = take_profit
                break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
        
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        baseline_trades.append({'pnl_pct': pnl_pct})
    
    baseline_trades_df = pd.DataFrame(baseline_trades)
    
    # 2. Missed patterns
    print(f"\n2️⃣  Running Missed Patterns Detector...")
    detector = MissedPatternsDetector(
        enable_continuation=True,
        enable_oversold_bounce=True,
        enable_rsi_pullback=True,
        enable_volume_breakout=True
    )
    
    patterns_signals = detector.detect_all_patterns(df.copy())
    
    # Backtest patterns
    patterns_trades = backtest_signals(df, patterns_signals)
    
    # 3. Compare
    print(f"\n" + "="*100)
    print("📊 COMPARISON TABLE")
    print("="*100)
    
    baseline_wr = len(baseline_trades_df[baseline_trades_df['pnl_pct'] > 0]) / len(baseline_trades_df) * 100
    baseline_pnl = baseline_trades_df['pnl_pct'].sum()
    baseline_avg = baseline_trades_df['pnl_pct'].mean()
    
    patterns_wr = len(patterns_trades[patterns_trades['pnl_pct'] > 0]) / len(patterns_trades) * 100 if len(patterns_trades) > 0 else 0
    patterns_pnl = patterns_trades['pnl_pct'].sum() if len(patterns_trades) > 0 else 0
    patterns_avg = patterns_trades['pnl_pct'].mean() if len(patterns_trades) > 0 else 0
    
    print(f"\n{'Strategy':<30} {'Trades':<10} {'Win Rate':<12} {'Total PnL':<15} {'Avg PnL':<12}")
    print("-"*80)
    print(f"{'Baseline (Optimized V2)':<30} {len(baseline_trades_df):<10} {baseline_wr:>10.1f}% {baseline_pnl:>+13.2f}% {baseline_avg:>+10.2f}%")
    print(f"{'Missed Patterns':<30} {len(patterns_trades):<10} {patterns_wr:>10.1f}% {patterns_pnl:>+13.2f}% {patterns_avg:>+10.2f}%")
    print("-"*80)
    
    # Combined
    combined_pnl = baseline_pnl + patterns_pnl
    combined_trades = len(baseline_trades_df) + len(patterns_trades)
    combined_avg = (baseline_pnl + patterns_pnl) / combined_trades if combined_trades > 0 else 0
    
    print(f"{'COMBINED':<30} {combined_trades:<10} {'N/A':<12} {combined_pnl:>+13.2f}% {combined_avg:>+10.2f}%")
    
    improvement = combined_pnl - baseline_pnl
    improvement_pct = (improvement / baseline_pnl) * 100 if baseline_pnl != 0 else 0
    
    print(f"\n💰 Improvement:")
    print(f"   Additional PnL: {improvement:+.2f}%")
    print(f"   Improvement: {improvement_pct:+.1f}%")
    
    if improvement_pct > 10:
        print(f"\n✅ SIGNIFICANT IMPROVEMENT! (+{improvement_pct:.1f}%)")
    elif improvement_pct > 5:
        print(f"\n✅ Good improvement (+{improvement_pct:.1f}%)")
    elif improvement_pct > 0:
        print(f"\n⚠️ Small improvement (+{improvement_pct:.1f}%)")
    else:
        print(f"\n❌ No improvement ({improvement_pct:.1f}%)")
    
    return {
        'baseline_pnl': baseline_pnl,
        'patterns_pnl': patterns_pnl,
        'combined_pnl': combined_pnl,
        'improvement': improvement,
        'improvement_pct': improvement_pct
    }


def main():
    print("\n" + "="*100)
    print("BACKTEST: MISSED PATTERNS")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Initialize detector
    detector = MissedPatternsDetector(
        enable_continuation=True,
        enable_oversold_bounce=True,
        enable_rsi_pullback=True,
        enable_volume_breakout=True
    )
    
    # Detect patterns
    signals_df = detector.detect_all_patterns(df)
    
    # Backtest
    trades_df = backtest_signals(df, signals_df)
    
    # Analyze
    analyze_results(trades_df)
    
    # Compare with baseline
    comparison = compare_with_baseline(df)
    
    # Save
    trades_df.to_csv('missed_patterns_backtest_results.csv', index=False)
    print(f"\n💾 Results saved to: missed_patterns_backtest_results.csv")
    
    return trades_df, comparison


if __name__ == "__main__":
    trades_df, comparison = main()
