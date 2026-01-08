"""
Run fixed backtest with corrected SL logic and generate comprehensive reports
"""

import pandas as pd
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../smc_trading_strategy'))

from backtest_v3_adaptive_fixed import AdaptiveBacktestV3
from pattern_recognition_strategy import PatternRecognitionStrategy


def run_fixed_backtest(data_file, output_prefix, use_adapted=False):
    """Run backtest with fixed SL logic"""
    
    print(f"\n{'='*80}")
    print(f"🔧 RUNNING FIXED BACKTEST: {output_prefix}")
    print(f"{'='*80}")
    print(f"   Data: {data_file}")
    print(f"   Parameters: {'ADAPTED (percentage-based)' if use_adapted else 'ORIGINAL (point-based)'}")
    
    # Load data
    df = pd.read_csv(data_file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    
    # Create strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Run backtest with appropriate parameters
    if use_adapted:
        # Adapted percentage-based parameters for crypto
        backtest = AdaptiveBacktestV3(spread_points=0.05, commission_points=0.1, swap_per_day=-0.01)
        
        # Convert to percentage-based by adjusting for price level
        # For crypto, use percentage targets
        avg_price = df['close'].mean()
        backtest.trend_tp1 = int(avg_price * 0.02)  # 2%
        backtest.trend_tp2 = int(avg_price * 0.04)  # 4%
        backtest.trend_tp3 = int(avg_price * 0.07)  # 7%
        backtest.trend_trailing = int(avg_price * 0.015)  # 1.5%
        backtest.trend_timeout = 72
        
        backtest.range_tp1 = int(avg_price * 0.015)  # 1.5%
        backtest.range_tp2 = int(avg_price * 0.025)  # 2.5%
        backtest.range_tp3 = int(avg_price * 0.04)  # 4%
        backtest.range_trailing = int(avg_price * 0.01)  # 1%
        backtest.range_timeout = 48
    else:
        # Original point-based parameters
        backtest = AdaptiveBacktestV3(spread_points=2.0, commission_points=0.5, swap_per_day=-0.3)
    
    # Run backtest
    trades_df = backtest.backtest(df, strategy)
    
    if trades_df is None or len(trades_df) == 0:
        print("❌ No trades generated")
        return None
    
    # Save all trades
    output_file = f"../results/{output_prefix}_fixed_results.csv"
    trades_df.to_csv(output_file, index=False)
    print(f"\n💾 All trades saved to: {output_file}")
    
    # Generate monthly P&L report
    trades_df['exit_month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
    
    monthly_pnl = trades_df.groupby('exit_month').agg({
        'pnl_pct': ['sum', 'count'],
        'pnl_points': 'sum'
    }).reset_index()
    
    monthly_pnl.columns = ['Month', 'Total_PnL_%', 'Trades', 'Total_Points']
    monthly_pnl['Month'] = monthly_pnl['Month'].astype(str)
    
    # Save monthly results
    monthly_file = f"../results/{output_prefix}_fixed_monthly.csv"
    monthly_pnl.to_csv(monthly_file, index=False)
    print(f"📅 Monthly results saved to: {monthly_file}")
    
    # Print monthly summary
    print(f"\n{'='*80}")
    print(f"📅 MONTHLY P&L SUMMARY")
    print(f"{'='*80}")
    for _, row in monthly_pnl.iterrows():
        print(f"   {row['Month']}: {int(row['Trades'])} trades, {row['Total_PnL_%']:+.2f}% ({row['Total_Points']:+.1f}п)")
    
    # Check for erroneous positions
    print(f"\n{'='*80}")
    print(f"🔍 ERRONEOUS POSITION CHECK")
    print(f"{'='*80}")
    
    # Find SL exits with positive PnL (should not exist after fix)
    sl_exits = trades_df[trades_df['exit_type'].isin(['SL', 'TRAILING_SL'])]
    positive_sl = sl_exits[sl_exits['pnl_pct'] > 0]
    
    if len(positive_sl) > 0:
        print(f"   ⚠️  Found {len(positive_sl)} SL exits with positive PnL (still erroneous!)")
        print(f"\n   Top 5 erroneous trades:")
        for idx, trade in positive_sl.nlargest(5, 'pnl_pct').iterrows():
            print(f"      {trade['exit_time']}: {trade['direction']} @ {trade['entry_price']:.2f} → {trade['exit_price']:.2f}")
            print(f"         PnL: {trade['pnl_pct']:+.2f}% (marked as {trade['exit_type']})")
    else:
        print(f"   ✅ No erroneous SL exits found! Fix successful!")
    
    # Export erroneous trades if any
    if len(positive_sl) > 0:
        error_file = f"../results/{output_prefix}_erroneous_trades.csv"
        positive_sl.to_csv(error_file, index=False)
        print(f"\n   📄 Erroneous trades saved to: {error_file}")
    
    return trades_df


def main():
    """Main entry point"""
    
    # BTC with adapted parameters
    print("\n" + "="*80)
    print("🪙 BITCOIN - ADAPTED PARAMETERS (PERCENTAGE-BASED)")
    print("="*80)
    
    btc_trades = run_fixed_backtest(
        "../data/BTC_1h_20240107_20260106_real.csv",
        "BTC",
        use_adapted=True
    )
    
    # ETH with original parameters
    print("\n" + "="*80)
    print("💎 ETHEREUM - ORIGINAL PARAMETERS (POINT-BASED)")
    print("="*80)
    
    eth_trades = run_fixed_backtest(
        "../data/ETH_1h_20240107_20260106_real.csv",
        "ETH",
        use_adapted=False
    )
    
    # Combined summary
    if btc_trades is not None and eth_trades is not None:
        print(f"\n{'='*80}")
        print(f"📊 COMBINED SUMMARY (FIXED BACKTEST)")
        print(f"{'='*80}")
        
        btc_pnl = btc_trades['pnl_pct'].sum()
        eth_pnl = eth_trades['pnl_pct'].sum()
        
        print(f"\n   BTC: {len(btc_trades)} trades, {btc_pnl:+.2f}% PnL")
        print(f"   ETH: {len(eth_trades)} trades, {eth_pnl:+.2f}% PnL")
        print(f"   TOTAL: {len(btc_trades) + len(eth_trades)} trades, {btc_pnl + eth_pnl:+.2f}% PnL")
        
        # Export combined all orders
        all_orders = pd.concat([
            btc_trades.assign(Asset='BTC'),
            eth_trades.assign(Asset='ETH')
        ], ignore_index=True)
        
        all_orders_file = "../results/all_orders_fixed.csv"
        all_orders.to_csv(all_orders_file, index=False)
        print(f"\n   💾 All orders saved to: {all_orders_file}")
        
        # Export combined monthly
        btc_monthly = pd.read_csv("../results/BTC_fixed_monthly.csv")
        eth_monthly = pd.read_csv("../results/ETH_fixed_monthly.csv")
        
        combined_monthly = pd.concat([
            btc_monthly.assign(Asset='BTC'),
            eth_monthly.assign(Asset='ETH')
        ], ignore_index=True)
        
        combined_monthly_file = "../results/combined_monthly_fixed.csv"
        combined_monthly.to_csv(combined_monthly_file, index=False)
        print(f"   📅 Combined monthly saved to: {combined_monthly_file}")


if __name__ == "__main__":
    # Change to scripts directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    main()
