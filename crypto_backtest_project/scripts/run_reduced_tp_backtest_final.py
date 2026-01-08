"""
Run Crypto Backtests with REDUCED TP levels
Modified version of run_with_smc_backtest.py with 30-35% lower TPs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest_v3_adaptive import AdaptiveBacktestV3
from pattern_recognition_strategy import PatternRecognitionStrategy
import pandas as pd
from datetime import datetime

def run_backtest_reduced_tp(data_file, asset_name, output_file):
    """Run backtest on crypto data with REDUCED TP levels"""
    print(f"\n{'='*80}")
    print(f"🔄 {asset_name} - REDUCED TP BACKTEST")
    print(f"{'='*80}\n")
    
    # Load data
    df = pd.read_csv(data_file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    print(f"✅ Loaded {len(df)} candles from {df.index.min()} to {df.index.max()}")
    
    # Add session info if missing (required by strategy)
    if 'is_active' not in df.columns:
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_active'] = df['is_london'] | df['is_ny']
    
    # Create strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Initialize backtest with REDUCED TPs
    backtest = AdaptiveBacktestV3(
        spread_points=2.0,
        commission_points=0.5,
        swap_per_day=-0.3
    )
    
    # REDUCE TP LEVELS by ~30-35%
    print(f"\n🎯 Applying REDUCED TP levels:")
    print(f"   TREND: TP1 {backtest.trend_tp1}→20, TP2 {backtest.trend_tp2}→35, TP3 {backtest.trend_tp3}→55, Trail {backtest.trend_trailing}→12")
    backtest.trend_tp1 = 20      # was 30
    backtest.trend_tp2 = 35      # was 55  
    backtest.trend_tp3 = 55      # was 90
    backtest.trend_trailing = 12  # was 18
    
    print(f"   RANGE: TP1 {backtest.range_tp1}→15, TP2 {backtest.range_tp2}→25, TP3 {backtest.range_tp3}→35, Trail {backtest.range_trailing}→10")
    backtest.range_tp1 = 15      # was 20
    backtest.range_tp2 = 25      # was 35
    backtest.range_tp3 = 35      # was 50
    backtest.range_trailing = 10  # was 15
    
    # Run backtest
    print(f"\n🚀 Running backtest...")
    results = backtest.backtest(df, strategy)
    
    # Process results
    if results is None or (isinstance(results, tuple) and results[0] is None):
        print(f"\n⚠️  Backtest returned no results for {asset_name}")
        return None
    
    # Handle tuple return (trades, metrics, monthly)
    if isinstance(results, tuple):
        trades_df = results[0]
        metrics = results[1] if len(results) > 1 else None
        monthly = results[2] if len(results) > 2 else None
    else:
        trades_df = results
        metrics = None
        monthly = None
    
    # Save results
    if trades_df is not None and len(trades_df) > 0:
        trades_df.to_csv(output_file, index=False)
        print(f"\n✅ Results saved to: {output_file}")
        
        # Calculate metrics
        pnl_col = 'total_pnl_%' if 'total_pnl_%' in trades_df.columns else 'pnl_pct'
        total_pnl = trades_df[pnl_col].sum()
        win_rate = (trades_df[pnl_col] > 0).sum() / len(trades_df) * 100
        
        # Drawdown
        cumulative_pnl = trades_df[pnl_col].cumsum()
        peak = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - peak
        max_dd = drawdown.min()
        
        # Profit factor
        wins = trades_df[trades_df[pnl_col] > 0][pnl_col].sum()
        losses = abs(trades_df[trades_df[pnl_col] < 0][pnl_col].sum())
        profit_factor = wins / losses if losses > 0 else 0
        
        # By regime
        if 'regime' in trades_df.columns:
            trend_trades = len(trades_df[trades_df['regime'] == 'TREND'])
            range_trades = len(trades_df[trades_df['regime'] == 'RANGE'])
            trend_pnl = trades_df[trades_df['regime'] == 'TREND'][pnl_col].sum()
            range_pnl = trades_df[trades_df['regime'] == 'RANGE'][pnl_col].sum()
        else:
            trend_trades = range_trades = 0
            trend_pnl = range_pnl = 0
        
        print(f"\n📊 {asset_name} Summary (REDUCED TP):")
        print(f"   Trades: {len(trades_df)}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Total P&L: {total_pnl:+.2f}%")
        print(f"   Max DD: {max_dd:.2f}%")
        print(f"   Profit Factor: {profit_factor:.2f}")
        if trend_trades > 0 or range_trades > 0:
            print(f"   TREND: {trend_trades} trades ({trend_pnl:+.1f}%)")
            print(f"   RANGE: {range_trades} trades ({range_pnl:+.1f}%)")
        
        # Validate for erroneous trades
        erroneous = trades_df[(trades_df['exit_type'].str.contains('SL', na=False)) & (trades_df[pnl_col] > 0)]
        if len(erroneous) > 0:
            print(f"   ⚠️  Erroneous: {len(erroneous)} ({len(erroneous)/len(trades_df)*100:.1f}%)")
            err_file = output_file.replace('_results.csv', '_erroneous.csv')
            erroneous.to_csv(err_file, index=False)
        
        return trades_df
    else:
        print(f"\n⚠️  No trades generated for {asset_name}")
        return None

def main():
    print("\n" + "="*80)
    print("📊 CRYPTO BACKTEST WITH REDUCED TP LEVELS")
    print("="*80)
    print("\nTP Reduction: ~30-35% lower than original")
    print("  TREND: TP1 30→20, TP2 55→35, TP3 90→55, Trail 18→12")
    print("  RANGE: TP1 20→15, TP2 35→25, TP3 50→35, Trail 15→10")
    print("\nData: Real Binance exchange data (2 years)")
    print("="*80)
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    results_dir = os.path.join(script_dir, '..', 'results')
    
    # Data files
    btc_data = os.path.join(data_dir, 'BTC_1h_20240107_20260106_real.csv')
    eth_data = os.path.join(data_dir, 'ETH_1h_20240107_20260106_real.csv')
    
    if not os.path.exists(btc_data):
        print(f"\n❌ BTC data not found: {btc_data}")
        return 1
    if not os.path.exists(eth_data):
        print(f"\n❌ ETH data not found: {eth_data}")
        return 1
    
    # Run backtests
    btc_results = run_backtest_reduced_tp(
        btc_data, 
        "Bitcoin (BTC)", 
        os.path.join(results_dir, 'BTC_reduced_tp_results.csv')
    )
    
    eth_results = run_backtest_reduced_tp(
        eth_data, 
        "Ethereum (ETH)", 
        os.path.join(results_dir, 'ETH_reduced_tp_results.csv')
    )
    
    # Combined analysis
    if btc_results is not None and eth_results is not None:
        print(f"\n{'='*80}")
        print("📈 COMBINED ANALYSIS - REDUCED TP")
        print(f"{'='*80}\n")
        
        pnl_col = 'total_pnl_%' if 'total_pnl_%' in btc_results.columns else 'pnl_pct'
        btc_pnl = btc_results[pnl_col].sum()
        eth_pnl = eth_results[pnl_col].sum()
        total_pnl = btc_pnl + eth_pnl
        total_trades = len(btc_results) + len(eth_results)
        
        btc_wr = (btc_results[pnl_col] > 0).sum() / len(btc_results) * 100
        eth_wr = (eth_results[pnl_col] > 0).sum() / len(eth_results) * 100
        
        print(f"🪙 BTC: {len(btc_results)} trades, {btc_wr:.1f}% WR, {btc_pnl:+.2f}% P&L")
        print(f"💎 ETH: {len(eth_results)} trades, {eth_wr:.1f}% WR, {eth_pnl:+.2f}% P&L")
        print(f"🎯 COMBINED: {total_trades} trades, {total_pnl:+.2f}% P&L")
        
        # Comparison
        print(f"\n{'='*80}")
        print("📊 COMPARISON WITH ORIGINAL TP")
        print(f"{'='*80}\n")
        print("Original TP levels:")
        print("  BTC: 1,122 trades, +1,335% P&L, 98.0% WR")
        print("  ETH: 1,028 trades, +646% P&L, 86.6% WR")
        print("  Combined: 2,150 trades, +1,981% P&L")
        
        print("\nReduced TP levels (~30-35% lower):")
        print(f"  BTC: {len(btc_results)} trades, {btc_pnl:+.1f}% P&L, {btc_wr:.1f}% WR")
        print(f"  ETH: {len(eth_results)} trades, {eth_pnl:+.1f}% P&L, {eth_wr:.1f}% WR")
        print(f"  Combined: {total_trades} trades, {total_pnl:+.1f}% P&L")
        
        # Difference
        btc_diff = btc_pnl - 1335
        eth_diff = eth_pnl - 646
        total_diff = total_pnl - 1981
        
        print(f"\n💹 Difference from Original:")
        print(f"  BTC: {btc_diff:+.1f}% ({btc_diff/1335*100:+.1f}%)")
        print(f"  ETH: {eth_diff:+.1f}% ({eth_diff/646*100:+.1f}%)")
        print(f"  Combined: {total_diff:+.1f}% ({total_diff/1981*100:+.1f}%)")
        
        if total_diff > 0:
            print(f"\n✅ RESULT: Reduced TP performed BETTER! (+{total_diff/1981*100:.1f}%)")
        elif total_diff > -100:
            print("\n≈ RESULT: Similar performance")
        else:
            print("\n❌ RESULT: Original TP performed better")
        
        # Save combined
        combined = pd.concat([
            btc_results.assign(asset='BTC'),
            eth_results.assign(asset='ETH')
        ], ignore_index=True)
        combined_file = os.path.join(results_dir, 'combined_reduced_tp_results.csv')
        combined.to_csv(combined_file, index=False)
        print(f"\n💾 Combined results saved: {combined_file}")
        
    print(f"\n{'='*80}")
    print("✅ BACKTEST COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
