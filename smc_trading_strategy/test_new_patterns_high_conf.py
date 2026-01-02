"""
Тест новых паттернов: только HIGH confidence
"""

import pandas as pd
from new_patterns_detector import NewPatternsDetector, backtest_new_patterns


def compare_all_vs_high_confidence(df):
    """
    Сравнение: все сигналы vs только HIGH confidence
    """
    
    print("\n" + "="*100)
    print("📊 СРАВНЕНИЕ: ALL vs HIGH CONFIDENCE")
    print("="*100)
    
    detector = NewPatternsDetector(
        enable_volume_breakout=True,
        enable_atr_expansion=True,
        enable_momentum_candle=True,
        focus_long_only=True
    )
    
    # Get all signals
    signals_all = detector.detect_all_patterns(df.copy())
    
    # Filter HIGH confidence only
    signals_high = signals_all[signals_all['confidence'] == 'HIGH'].copy()
    
    print(f"\n1️⃣  ALL SIGNALS: {len(signals_all)}")
    print(f"2️⃣  HIGH CONFIDENCE: {len(signals_high)}")
    print(f"   Filtered out: {len(signals_all) - len(signals_high)} ({(len(signals_all) - len(signals_high))/len(signals_all)*100:.1f}%)")
    
    # Backtest HIGH confidence
    print(f"\n" + "="*100)
    print("🔍 BACKTEST: HIGH CONFIDENCE ONLY")
    print("="*100)
    
    from new_patterns_detector import backtest_new_patterns
    
    # Temporary backtest for HIGH only
    from datetime import timedelta
    
    trades = []
    
    for idx, signal in signals_high.iterrows():
        entry_time = signal['time']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        search_end = entry_time + timedelta(hours=24)
        df_future = df[(df.index > entry_time) & (df.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        hit_tp = False
        hit_sl = False
        exit_price = None
        exit_type = 'TIMEOUT'
        max_profit_pips = 0
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            current_profit = (candle['high'] - entry_price) / 0.10
            max_profit_pips = max(max_profit_pips, current_profit)
            
            if candle['low'] <= stop_loss:
                hit_sl = True
                exit_price = stop_loss
                exit_type = 'SL'
                break
            
            if candle['high'] >= take_profit:
                hit_tp = True
                exit_price = take_profit
                exit_type = 'TP'
                break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'TIMEOUT'
        
        pnl_dollars = exit_price - entry_price
        pnl_pct = (pnl_dollars / entry_price) * 100
        pnl_pips = pnl_dollars / 0.10
        
        trades.append({
            'entry_time': entry_time,
            'pattern': signal['pattern'],
            'type': signal['type'],
            'confidence': signal['confidence'],
            'pnl_pct': pnl_pct,
            'pnl_pips': pnl_pips,
            'max_profit_pips': max_profit_pips,
            'exit_type': exit_type,
            'hit_tp': hit_tp,
            'hit_sl': hit_sl
        })
    
    trades_high = pd.DataFrame(trades)
    
    # Load ALL results
    trades_all = pd.read_csv('new_patterns_backtest.csv')
    
    # Compare
    print(f"\n📊 COMPARISON:")
    print(f"{'Metric':<25} {'ALL':<15} {'HIGH Only':<15} {'Difference':<15}")
    print("-"*70)
    
    all_pnl = trades_all['pnl_pct'].sum()
    high_pnl = trades_high['pnl_pct'].sum()
    
    all_wr = len(trades_all[trades_all['pnl_pct'] > 0]) / len(trades_all) * 100
    high_wr = len(trades_high[trades_high['pnl_pct'] > 0]) / len(trades_high) * 100
    
    all_avg = trades_all['pnl_pct'].mean()
    high_avg = trades_high['pnl_pct'].mean()
    
    print(f"{'Total PnL':<25} {all_pnl:>+13.2f}% {high_pnl:>+13.2f}% {high_pnl-all_pnl:>+13.2f}%")
    print(f"{'Win Rate':<25} {all_wr:>12.1f}% {high_wr:>12.1f}% {high_wr-all_wr:>+12.1f}%")
    print(f"{'Avg PnL':<25} {all_avg:>+13.3f}% {high_avg:>+13.3f}% {high_avg-all_avg:>+13.3f}%")
    print(f"{'Total Trades':<25} {len(trades_all):>13} {len(trades_high):>13} {len(trades_high)-len(trades_all):>+13}")
    
    # By pattern (HIGH only)
    print(f"\n📊 HIGH CONFIDENCE By Pattern:")
    for pattern_type in sorted(trades_high['type'].unique()):
        type_trades = trades_high[trades_high['type'] == pattern_type]
        type_wins = len(type_trades[type_trades['pnl_pct'] > 0])
        type_wr = type_wins / len(type_trades) * 100
        type_pnl = type_trades['pnl_pct'].sum()
        type_pips = type_trades['pnl_pips'].sum()
        
        print(f"   {pattern_type:20s}: {len(type_trades):3d} | "
              f"WR {type_wr:5.1f}% | PnL {type_pnl:+7.2f}% ({type_pips:+6.0f}p)")
    
    # Recommendation
    print(f"\n💡 Recommendation:")
    if high_wr > all_wr + 2:
        print(f"   ✅ Use HIGH confidence only:")
        print(f"      • Better WR: {high_wr:.1f}% vs {all_wr:.1f}%")
        print(f"      • Better quality signals")
    else:
        print(f"   ⚖️  Marginal difference in WR")
        print(f"   Consider: ALL signals for more trades, HIGH for quality")
    
    # Save HIGH confidence results
    trades_high.to_csv('new_patterns_high_conf_backtest.csv', index=False)
    print(f"\n💾 Saved: new_patterns_high_conf_backtest.csv")
    
    return trades_all, trades_high


def identify_best_pattern(trades_high):
    """
    Identify which new pattern is best
    """
    
    print(f"\n" + "="*100)
    print("🏆 BEST NEW PATTERN")
    print("="*100)
    
    results = []
    
    for pattern_type in trades_high['type'].unique():
        type_trades = trades_high[trades_high['type'] == pattern_type]
        
        wins = len(type_trades[type_trades['pnl_pct'] > 0])
        wr = wins / len(type_trades) * 100
        total_pnl = type_trades['pnl_pct'].sum()
        avg_pnl = type_trades['pnl_pct'].mean()
        
        results.append({
            'pattern': pattern_type,
            'trades': len(type_trades),
            'wr': wr,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'score': wr * avg_pnl  # Simple quality score
        })
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('score', ascending=False)
    
    print(f"\n{'Pattern':<20} {'Trades':<10} {'WR':<10} {'Total PnL':<12} {'Avg PnL':<12} {'Score':<10}")
    print("-"*80)
    
    for _, row in results_df.iterrows():
        print(f"{row['pattern']:<20} {row['trades']:<10} {row['wr']:>8.1f}% "
              f"{row['total_pnl']:>+10.2f}% {row['avg_pnl']:>+10.3f}% {row['score']:>8.1f}")
    
    best = results_df.iloc[0]
    
    print(f"\n🏆 WINNER: {best['pattern']}")
    print(f"   Trades:    {best['trades']}")
    print(f"   Win Rate:  {best['wr']:.1f}%")
    print(f"   Total PnL: {best['total_pnl']:+.2f}%")
    print(f"   Avg PnL:   {best['avg_pnl']:+.3f}%")
    
    return best['pattern']


def main():
    print("\n" + "="*100)
    print("🔬 TESTING: HIGH CONFIDENCE ONLY")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Compare ALL vs HIGH
    trades_all, trades_high = compare_all_vs_high_confidence(df)
    
    # Identify best pattern
    best_pattern = identify_best_pattern(trades_high)
    
    print(f"\n" + "="*100)
    print("✅ ANALYSIS COMPLETE")
    print("="*100)


if __name__ == "__main__":
    main()
