"""
Run Crypto Backtests with SMC backtest_v3_adaptive.py

Uses the proven backtest_v3_adaptive.py from smc_trading_strategy/
with real Binance data for BTC and ETH.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'smc_trading_strategy'))

from backtest_v3_adaptive import AdaptiveBacktestV3
from pattern_recognition_strategy import PatternRecognitionStrategy
import pandas as pd
import numpy as np
from datetime import datetime

def run_backtest(data_file, asset_name, output_file):
    """Run backtest on crypto data"""
    print(f"\n{'='*80}")
    print(f"🔄 Running backtest for {asset_name}")
    print(f"{'='*80}\n")
    
    # Load data
    df = pd.read_csv(data_file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    print(f"Loaded {len(df)} candles from {df.index.min()} to {df.index.max()}")
    
    # Add session info if missing
    if 'is_active' not in df.columns:
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_active'] = df['is_london'] | df['is_ny']
    
    # Create strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Initialize backtest
    backtest = AdaptiveBacktestV3(
        spread_points=2.0,
        commission_points=0.5,
        swap_per_day=-0.3
    )
    
    # Run backtest
    print(f"\nRunning backtest...")
    results = backtest.backtest(df, strategy)
    
    # Save results
    if results is not None:
        results.to_csv(output_file, index=False)
        print(f"\n✅ Results saved to: {output_file}")
        
        # Print summary
        if len(results) > 0:
            total_pnl = results['pnl_pct'].sum()
            win_rate = (results['pnl_pct'] > 0).sum() / len(results) * 100
            
            # Calculate drawdown from cumulative returns
            cumulative_pnl = (1 + results['pnl_pct'] / 100).cumprod()
            peak = cumulative_pnl.cummax()
            drawdown = (cumulative_pnl / peak - 1) * 100
            max_dd = drawdown.min()
            
            wins = results[results['pnl_pct'] > 0]['pnl_pct'].sum()
            losses = abs(results[results['pnl_pct'] < 0]['pnl_pct'].sum())
            profit_factor = wins / losses if losses > 0 else 0
            
            print(f"\n📊 {asset_name} Summary:")
            print(f"   Total Trades: {len(results)}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Total P&L: {total_pnl:+.2f}%")
            print(f"   Max Drawdown: {max_dd:.2f}%")
            print(f"   Profit Factor: {profit_factor:.2f}")
            
            # Validate for erroneous trades
            erroneous = results[(results['exit_type'] == 'SL') & (results['pnl_pct'] > 0)]
            if len(erroneous) > 0:
                print(f"\n   ⚠️  Erroneous Trades: {len(erroneous)} ({len(erroneous)/len(results)*100:.1f}%)")
                err_file = output_file.replace('_results.csv', '_erroneous.csv')
                erroneous.to_csv(err_file, index=False)
                print(f"   Erroneous trades saved to: {err_file}")
            
            return results
        else:
            print(f"\n⚠️  No trades generated for {asset_name}")
            return None
    else:
        print(f"\n⚠️  Backtest returned no results for {asset_name}")
        return None

def main():
    print("\n" + "="*80)
    print("📊 CRYPTO BACKTEST with SMC backtest_v3_adaptive.py")
    print("="*80)
    print("\nUsing: smc_trading_strategy/backtest_v3_adaptive.py")
    print("Data: Real Binance exchange data (2 years)")
    print("="*80)
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    results_dir = os.path.join(script_dir, '..', 'results')
    
    # Check data files
    btc_data = os.path.join(data_dir, 'BTC_1h_20240107_20260106_real.csv')
    eth_data = os.path.join(data_dir, 'ETH_1h_20240107_20260106_real.csv')
    
    if not os.path.exists(btc_data):
        print(f"\n❌ BTC data not found: {btc_data}")
        return 1
    if not os.path.exists(eth_data):
        print(f"\n❌ ETH data not found: {eth_data}")
        return 1
    
    # Run backtests
    btc_results = run_backtest(
        btc_data, 
        "Bitcoin (BTC)", 
        os.path.join(results_dir, 'BTC_smc_backtest_results.csv')
    )
    
    eth_results = run_backtest(
        eth_data, 
        "Ethereum (ETH)", 
        os.path.join(results_dir, 'ETH_smc_backtest_results.csv')
    )
    
    # Combined analysis
    if btc_results is not None and eth_results is not None:
        print(f"\n{'='*80}")
        print("📈 COMBINED ANALYSIS")
        print(f"{'='*80}\n")
        
        btc_pnl = btc_results['pnl_pct'].sum()
        eth_pnl = eth_results['pnl_pct'].sum()
        total_pnl = btc_pnl + eth_pnl
        total_trades = len(btc_results) + len(eth_results)
        
        print(f"BTC: {len(btc_results)} trades, {btc_pnl:+.2f}% P&L")
        print(f"ETH: {len(eth_results)} trades, {eth_pnl:+.2f}% P&L")
        print(f"\nCOMBINED: {total_trades} trades, {total_pnl:+.2f}% total P&L")
        
        # Save combined
        combined = pd.concat([
            btc_results.assign(asset='BTC'),
            eth_results.assign(asset='ETH')
        ], ignore_index=True)
        combined_file = os.path.join(results_dir, 'combined_smc_results.csv')
        combined.to_csv(combined_file, index=False)
        print(f"\nCombined results saved to: {combined_file}")
        
    print(f"\n{'='*80}")
    print("✅ BACKTEST COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
