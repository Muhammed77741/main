"""
Run backtest with REDUCED TP levels for BTC and ETH
Testing lower TP targets to see if performance improves
"""

import pandas as pd
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_v3_adaptive import AdaptiveBacktestV3

def run_reduced_tp_backtest():
    """Run backtest with reduced TP levels"""
    
    print("=" * 80)
    print("BACKTEST WITH REDUCED TP LEVELS")
    print("=" * 80)
    print("\nReduced TP Configuration:")
    print("TREND MODE:")
    print("  - TP1: 30 → 20 points (-33%)")
    print("  - TP2: 55 → 35 points (-36%)")
    print("  - TP3: 90 → 55 points (-39%)")
    print("  - Trailing: 18 → 12 points (-33%)")
    print("\nRANGE MODE:")
    print("  - TP1: 20 → 15 points (-25%)")
    print("  - TP2: 35 → 25 points (-29%)")
    print("  - TP3: 50 → 35 points (-30%)")
    print("  - Trailing: 15 → 10 points (-33%)")
    print("=" * 80)
    
    # Data paths
    btc_data = '../data/BTC_1h_20240107_20260106_real.csv'
    eth_data = '../data/ETH_1h_20240107_20260106_real.csv'
    
    results = {}
    
    for symbol, data_file in [('BTC', btc_data), ('ETH', eth_data)]:
        print(f"\n{'='*80}")
        print(f"Running backtest for {symbol}")
        print(f"{'='*80}")
        
        # Load data
        df = pd.read_csv(data_file)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        print(f"Data loaded: {len(df)} candles from {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
        
        # Create backtest with REDUCED TP levels
        backtest = AdaptiveBacktestV3(
            spread_points=2.0,
            commission_points=0.5,
            swap_per_day=-0.3
        )
        
        # Modify TP levels - REDUCE by ~30-35%
        backtest.trend_tp1 = 20      # was 30
        backtest.trend_tp2 = 35      # was 55  
        backtest.trend_tp3 = 55      # was 90
        backtest.trend_trailing = 12  # was 18
        
        backtest.range_tp1 = 15      # was 20
        backtest.range_tp2 = 25      # was 35
        backtest.range_tp3 = 35      # was 50
        backtest.range_trailing = 10  # was 15
        
        # Create strategy
        from pattern_recognition_strategy import PatternRecognitionStrategy
        strategy = PatternRecognitionStrategy()
        
        # Run backtest
        trades, metrics, monthly_stats = backtest.backtest(df, strategy)
        
        # Save results
        results[symbol] = {
            'trades': trades,
            'metrics': metrics,
            'monthly': monthly_stats
        }
        
        # Print summary
        print(f"\n{symbol} Results Summary:")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  Total P&L: {metrics['total_pnl']:.2f}%")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  TREND trades: {metrics.get('trend_trades', 0)} ({metrics.get('trend_pnl', 0):.1f}%)")
        print(f"  RANGE trades: {metrics.get('range_trades', 0)} ({metrics.get('range_pnl', 0):.1f}%)")
        
        # Save files
        trades_file = f'../results/{symbol}_reduced_tp_results.csv'
        monthly_file = f'../results/{symbol}_reduced_tp_monthly.csv'
        
        trades.to_csv(trades_file, index=False)
        monthly_stats.to_csv(monthly_file, index=False)
        
        print(f"\nFiles saved:")
        print(f"  - {trades_file}")
        print(f"  - {monthly_file}")
    
    # Combined summary
    print(f"\n{'='*80}")
    print("COMBINED RESULTS - REDUCED TP LEVELS")
    print(f"{'='*80}")
    
    btc_metrics = results['BTC']['metrics']
    eth_metrics = results['ETH']['metrics']
    
    total_trades = btc_metrics['total_trades'] + eth_metrics['total_trades']
    total_pnl = btc_metrics['total_pnl'] + eth_metrics['total_pnl']
    
    print(f"\nBTC:")
    print(f"  {btc_metrics['total_trades']} trades, {btc_metrics['win_rate']:.1f}% WR, {btc_metrics['total_pnl']:.2f}% P&L")
    print(f"  Max DD: {btc_metrics['max_drawdown']:.2f}%, PF: {btc_metrics['profit_factor']:.2f}")
    
    print(f"\nETH:")
    print(f"  {eth_metrics['total_trades']} trades, {eth_metrics['win_rate']:.1f}% WR, {eth_metrics['total_pnl']:.2f}% P&L")
    print(f"  Max DD: {eth_metrics['max_drawdown']:.2f}%, PF: {eth_metrics['profit_factor']:.2f}")
    
    print(f"\nCOMBINED:")
    print(f"  Total trades: {total_trades}")
    print(f"  Total P&L: {total_pnl:.2f}%")
    
    # Save combined results
    all_trades = pd.concat([
        results['BTC']['trades'].assign(symbol='BTC'),
        results['ETH']['trades'].assign(symbol='ETH')
    ]).sort_values('entry_time').reset_index(drop=True)
    
    all_trades.to_csv('../results/combined_reduced_tp_results.csv', index=False)
    
    # Compare with original
    print(f"\n{'='*80}")
    print("COMPARISON WITH ORIGINAL TP LEVELS")
    print(f"{'='*80}")
    print("\nOriginal TP levels results:")
    print("  BTC: 1,122 trades, +1,335% P&L, 98.0% WR")
    print("  ETH: 1,028 trades, +646% P&L, 86.6% WR")
    print("  Combined: 2,150 trades, +1,981% P&L")
    print("\nReduced TP levels results:")
    print(f"  BTC: {btc_metrics['total_trades']} trades, {btc_metrics['total_pnl']:+.1f}% P&L, {btc_metrics['win_rate']:.1f}% WR")
    print(f"  ETH: {eth_metrics['total_trades']} trades, {eth_metrics['total_pnl']:+.1f}% P&L, {eth_metrics['win_rate']:.1f}% WR")
    print(f"  Combined: {total_trades} trades, {total_pnl:+.1f}% P&L")
    
    # Analysis
    print(f"\n{'='*80}")
    print("ANALYSIS")
    print(f"{'='*80}")
    
    btc_diff = btc_metrics['total_pnl'] - 1335
    eth_diff = eth_metrics['total_pnl'] - 646
    combined_diff = total_pnl - 1981
    
    print(f"\nP&L Difference vs Original:")
    print(f"  BTC: {btc_diff:+.1f}% ({btc_diff/1335*100:+.1f}%)")
    print(f"  ETH: {eth_diff:+.1f}% ({eth_diff/646*100:+.1f}%)")
    print(f"  Combined: {combined_diff:+.1f}% ({combined_diff/1981*100:+.1f}%)")
    
    if combined_diff > 0:
        print("\n✅ IMPROVED: Reduced TP levels performed BETTER")
    elif combined_diff > -100:
        print("\n≈ SIMILAR: Reduced TP levels performed comparably")
    else:
        print("\n❌ WORSE: Reduced TP levels performed worse")
    
    print(f"\n{'='*80}")
    print("Backtest complete!")
    print(f"{'='*80}\n")
    
    return results

if __name__ == '__main__':
    try:
        results = run_reduced_tp_backtest()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
