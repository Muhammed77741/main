"""
Rerun backtests with fixed SL/TP logic
Now checks TPs before SL to correctly handle extreme price gaps
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_v3_adaptive import AdaptiveBacktestV3
import pandas as pd
from datetime import datetime

def main():
    print("\n" + "="*80)
    print("🔧 RERUNNING BACKTESTS WITH FIXED SL/TP LOGIC")
    print("="*80)
    print("Fix: TPs are now checked BEFORE SL to handle extreme gaps correctly")
    print("="*80 + "\n")
    
    # Paths
    data_dir = "../data"
    results_dir = "../results"
    
    # BTC backtest
    print("\n📊 Running BTC backtest with fixed logic...")
    btc_data = f"{data_dir}/BTC_1h_20240107_20260106_real.csv"
    btc_df = pd.read_csv(btc_data)
    btc_df['datetime'] = pd.to_datetime(btc_df['datetime'])
    
    # Import strategy
    from pattern_recognition_strategy import PatternRecognitionStrategy
    strategy = PatternRecognitionStrategy()
    
    btc_backtest = AdaptiveBacktestV3(spread_points=2.0, commission_points=0.5, swap_per_day=-0.3)
    btc_results = btc_backtest.backtest(btc_df, strategy)
    
    if btc_results is not None:
        btc_output = f"{results_dir}/BTC_smc_backtest_results_FIXED.csv"
        btc_results.to_csv(btc_output, index=False)
        print(f"✅ BTC results saved: {btc_output}")
        
        # Count erroneous trades (SL with positive PnL)
        btc_errors = btc_results[(btc_results['exit_type'].str.contains('SL')) & 
                                  (btc_results['total_pnl_%'] > 0)]
        print(f"   Erroneous trades: {len(btc_errors)} / {len(btc_results)} ({len(btc_errors)/len(btc_results)*100:.2f}%)")
        
        if len(btc_errors) > 0:
            print(f"   ❌ Still has errors! Showing first 5:")
            for idx, row in btc_errors.head(5).iterrows():
                print(f"      {row['entry_time']}: {row['direction']} @ {row['entry_price']:.2f} → "
                      f"{row['exit_price']:.2f} ({row['total_pnl_%']:+.2f}%) exit={row['exit_type']}")
        else:
            print(f"   ✅ No erroneous trades!")
    
    # ETH backtest
    print("\n📊 Running ETH backtest with fixed logic...")
    eth_data = f"{data_dir}/ETH_1h_20240107_20260106_real.csv"
    eth_df = pd.read_csv(eth_data)
    eth_df['datetime'] = pd.to_datetime(eth_df['datetime'])
    
    eth_backtest = AdaptiveBacktestV3(spread_points=2.0, commission_points=0.5, swap_per_day=-0.3)
    eth_results = eth_backtest.backtest(eth_df, strategy)
    
    if eth_results is not None:
        eth_output = f"{results_dir}/ETH_smc_backtest_results_FIXED.csv"
        eth_results.to_csv(eth_output, index=False)
        print(f"✅ ETH results saved: {eth_output}")
        
        # Count erroneous trades
        eth_errors = eth_results[(eth_results['exit_type'].str.contains('SL')) & 
                                  (eth_results['total_pnl_%'] > 0)]
        print(f"   Erroneous trades: {len(eth_errors)} / {len(eth_results)} ({len(eth_errors)/len(eth_results)*100:.2f}%)")
        
        if len(eth_errors) > 0:
            print(f"   ❌ Still has errors! Showing first 5:")
            for idx, row in eth_errors.head(5).iterrows():
                print(f"      {row['entry_time']}: {row['direction']} @ {row['entry_price']:.2f} → "
                      f"{row['exit_price']:.2f} ({row['total_pnl_%']:+.2f}%) exit={row['exit_type']}")
        else:
            print(f"   ✅ No erroneous trades!")
    
    # Combined stats
    if btc_results is not None and eth_results is not None:
        print("\n" + "="*80)
        print("📈 COMBINED RESULTS WITH FIXED LOGIC")
        print("="*80)
        print(f"Total trades: {len(btc_results) + len(eth_results)}")
        print(f"BTC: {len(btc_results)} trades, +{btc_results['total_pnl_%'].sum():.2f}% total PnL")
        print(f"ETH: {len(eth_results)} trades, +{eth_results['total_pnl_%'].sum():.2f}% total PnL")
        print(f"Combined: +{btc_results['total_pnl_%'].sum() + eth_results['total_pnl_%'].sum():.2f}% total PnL")
        
        total_errors = len(btc_errors) + len(eth_errors)
        total_trades = len(btc_results) + len(eth_results)
        print(f"\nErroneous trades: {total_errors} / {total_trades} ({total_errors/total_trades*100:.2f}%)")
        
        if total_errors == 0:
            print("\n✅✅✅ ALL SL/TP LOGIC ISSUES FIXED! ✅✅✅")
        else:
            print(f"\n⚠️ Still has {total_errors} erroneous trades")
        print("="*80)

if __name__ == "__main__":
    main()
