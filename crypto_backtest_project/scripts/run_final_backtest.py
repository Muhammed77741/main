"""
Final Backtest Run Script
Runs backtests with optimal parameters:
- BTC: Adapted (percentage-based) parameters
- ETH: Original (point-based) parameters

NOTE: Due to network restrictions, using simulated data.
For production use, replace with real data from exchanges.
"""

import subprocess
import os
import sys

def run_command(cmd, description):
    """Run a shell command and print output"""
    print(f"\n{'='*80}")
    print(f"🔄 {description}")
    print(f"{'='*80}\n")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode

def main():
    print("\n" + "="*80)
    print("📊 FINAL BACKTEST RUN - OPTIMAL PARAMETERS")
    print("="*80)
    print("\nConfiguration:")
    print("   BTC: Adapted (percentage-based) parameters")
    print("   ETH: Original (point-based) parameters")
    print("\nData: Simulated (Yahoo Finance unavailable due to network restrictions)")
    print("="*80)
    
    # Ensure data exists
    data_dir = "../data"
    btc_data = f"{data_dir}/BTC_1h_20240107_20260106_real.csv"
    eth_data = f"{data_dir}/ETH_1h_20240107_20260106_real.csv"
    
    if not os.path.exists(btc_data) or not os.path.exists(eth_data):
        print("\n⚠️  Data files not found. Generating simulated data...")
        ret = run_command("python generate_crypto_data.py --years 2", "Generating crypto data")
        if ret != 0:
            print("❌ Failed to generate data")
            return 1
        # Move files
        run_command(f"mv BTC_1h_*.csv {data_dir}/", "Moving BTC data")
        run_command(f"mv ETH_1h_*.csv {data_dir}/", "Moving ETH data")
    
    # Run BTC with adapted parameters
    print("\n" + "="*80)
    print("🪙 BITCOIN - Running with ADAPTED parameters")
    print("="*80)
    ret = run_command(
        f"python adapted_crypto_backtest.py --file {btc_data} --output ../results/BTC_final_results.csv",
        "BTC Adapted Backtest"
    )
    if ret != 0:
        print("❌ BTC backtest failed")
        return 1
    
    # Run ETH with original parameters
    print("\n" + "="*80)
    print("🪙 ETHEREUM - Running with ORIGINAL parameters")
    print("="*80)
    ret = run_command(
        f"python ../../smc_trading_strategy/backtest_v3_adaptive.py --file {eth_data}",
        "ETH Original Backtest"
    )
    if ret != 0:
        print("❌ ETH backtest failed")
        return 1
    
    # Move ETH results
    run_command("mv ../../backtest_v3_adaptive_results.csv ../results/ETH_final_results.csv", "Moving ETH results")
    
    # Create final comparison
    print("\n" + "="*80)
    print("📊 CREATING FINAL COMPARISON")
    print("="*80)
    
    # Create comparison script on the fly
    comparison_code = '''
import pandas as pd
import os

results_dir = "../results"
btc_file = os.path.join(results_dir, "BTC_final_results.csv")
eth_file = os.path.join(results_dir, "ETH_final_results.csv")

print("\\n" + "="*80)
print("📊 FINAL RESULTS - OPTIMAL PARAMETERS")
print("="*80)

# BTC Analysis
btc = pd.read_csv(btc_file)
print("\\n🪙 BITCOIN (Adapted Parameters - Percentage-based)")
print("-"*80)
print(f"Total Trades: {len(btc)}")
print(f"Win Rate: {(btc['pnl_pct'] > 0).sum() / len(btc) * 100:.1f}%")
print(f"Total PnL: {btc['pnl_pct'].sum():+.2f}%")
cumulative = btc['pnl_pct'].cumsum()
dd = (cumulative - cumulative.cummax()).min()
print(f"Max Drawdown: {dd:.2f}%")

# ETH Analysis
eth = pd.read_csv(eth_file)
print("\\n🪙 ETHEREUM (Original Parameters - Point-based)")
print("-"*80)
print(f"Total Trades: {len(eth)}")
print(f"Win Rate: {(eth['pnl_pct'] > 0).sum() / len(eth) * 100:.1f}%")
print(f"Total PnL: {eth['pnl_pct'].sum():+.2f}%")
cumulative = eth['pnl_pct'].cumsum()
dd = (cumulative - cumulative.cummax()).min()
print(f"Max Drawdown: {dd:.2f}%")

# Export monthly
btc['exit_time'] = pd.to_datetime(btc['exit_time'])
btc['month'] = btc['exit_time'].dt.to_period('M')
btc['asset'] = 'BTC'

eth['exit_time'] = pd.to_datetime(eth['exit_time'])
eth['month'] = eth['exit_time'].dt.to_period('M')
eth['asset'] = 'ETH'

btc_monthly = btc.groupby('month').agg({'pnl_pct': ['sum', 'count']})
btc_monthly.columns = ['Total_PnL_%', 'Trades']
btc_monthly['Asset'] = 'BTC_Adapted'

eth_monthly = eth.groupby('month').agg({'pnl_pct': ['sum', 'count']})
eth_monthly.columns = ['Total_PnL_%', 'Trades']
eth_monthly['Asset'] = 'ETH_Original'

final_monthly = pd.concat([btc_monthly, eth_monthly]).reset_index()
final_monthly.to_csv(os.path.join(results_dir, "final_monthly_results.csv"), index=False)

# Export all orders
all_orders = pd.concat([btc, eth], ignore_index=True)
all_orders.to_csv(os.path.join(results_dir, "final_all_orders.csv"), index=False)

print("\\n" + "="*80)
print("✅ FILES EXPORTED")
print("="*80)
print(f"📁 final_monthly_results.csv - Monthly breakdown")
print(f"📁 final_all_orders.csv - All {len(all_orders)} orders")
print(f"📁 BTC_final_results.csv - {len(btc)} BTC trades")
print(f"📁 ETH_final_results.csv - {len(eth)} ETH trades")
'''
    
    with open('/tmp/final_comparison.py', 'w') as f:
        f.write(comparison_code)
    
    run_command("python /tmp/final_comparison.py", "Final comparison")
    
    print("\n" + "="*80)
    print("✅ ALL BACKTESTS COMPLETE")
    print("="*80)
    print("\nOptimal Configuration:")
    print("   ✅ BTC: Adapted (percentage-based) parameters")
    print("   ✅ ETH: Original (point-based) parameters")
    print("\nResults saved in: crypto_backtest_project/results/")
    print("="*80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
