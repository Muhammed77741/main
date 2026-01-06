"""
Test V3 Adaptive Backtest with different swing lookback periods
Compares results with 20, 10, and 5 candle lookbacks
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_v3_adaptive import AdaptiveBacktestV3
from pattern_recognition_strategy import PatternRecognitionStrategy
from simplified_smc_strategy import SimplifiedSMCStrategy


def modify_stop_loss_lookback(strategy, lookback):
    """Modify the stop loss lookback period in SimplifiedSMCStrategy"""
    # We need to monkey-patch the _calculate_stop_loss method
    original_method = strategy.smc_strategy._calculate_stop_loss
    
    def new_calculate_stop_loss(df, idx, direction):
        if direction == 1:  # Long
            recent_data = df.iloc[max(0, idx-lookback):idx]
            recent_swings = recent_data[recent_data['swing_low']]
            if len(recent_swings) > 0:
                stop = recent_swings['low'].min()
            else:
                stop = df['low'].iloc[max(0, idx-10):idx].min()
            return stop * 0.998
        else:  # Short
            recent_data = df.iloc[max(0, idx-lookback):idx]
            recent_swings = recent_data[recent_data['swing_high']]
            if len(recent_swings) > 0:
                stop = recent_swings['high'].max()
            else:
                stop = df['high'].iloc[max(0, idx-10):idx].max()
            return stop * 1.002
    
    strategy.smc_strategy._calculate_stop_loss = new_calculate_stop_loss


def run_backtest_with_lookback(lookback_period):
    """Run backtest with specific swing lookback period"""
    
    print(f"\n{'='*80}")
    print(f"TESTING SWING LOOKBACK: {lookback_period} CANDLES")
    print(f"{'='*80}\n")
    
    # Load data
    data_file = "XAUUSD_1H_MT5_20241227_20251227.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return None
    
    df = pd.read_csv(data_file, parse_dates=['time'])
    print(f"✅ Loaded {len(df)} candles from {df['time'].min()} to {df['time'].max()}")
    
    # Initialize strategy with modified swing_lookback
    strategy = PatternRecognitionStrategy(
        risk_reward_ratio=2.0,
        risk_per_trade=0.02,
        swing_lookback=lookback_period,  # KEY PARAMETER
        min_pattern_swings=3
    )
    
    # Modify the underlying SimplifiedSMCStrategy's stop loss calculation
    modify_stop_loss_lookback(strategy, lookback_period)
    
    # Generate signals
    print(f"🔍 Generating signals with swing lookback = {lookback_period}...")
    df_signals = strategy.generate_signals(df)
    
    # Count signals
    long_signals = len(df_signals[df_signals['signal'] == 1])
    short_signals = len(df_signals[df_signals['signal'] == -1])
    total_signals = long_signals + short_signals
    
    print(f"   Total signals: {total_signals} (Long: {long_signals}, Short: {short_signals})")
    
    # Run backtest
    backtest = AdaptiveBacktestV3(spread_points=2.0, commission_points=0.5)
    
    print(f"🔄 Running adaptive backtest...")
    results = backtest.run_backtest(df_signals)
    
    return results


def main():
    """Main function to test different lookback periods"""
    
    print("\n" + "="*80)
    print("V3 ADAPTIVE BACKTEST - SWING LOOKBACK COMPARISON")
    print("="*80)
    print("\nTesting swing lookback periods: 20, 10, and 5 candles")
    print("This affects how far back the strategy looks for swing points to place SL")
    
    lookback_periods = [20, 10, 5]
    all_results = {}
    
    for lookback in lookback_periods:
        results = run_backtest_with_lookback(lookback)
        if results:
            all_results[lookback] = results
    
    # Compare results
    if len(all_results) > 0:
        print("\n" + "="*80)
        print("COMPARISON SUMMARY")
        print("="*80)
        
        print(f"\n{'Lookback':<12} {'Trades':<10} {'P&L %':<12} {'Win Rate':<12} {'PF':<10} {'Max DD':<12} {'Avg SL (p)':<12}")
        print("-" * 90)
        
        for lookback in sorted(all_results.keys(), reverse=True):
            r = all_results[lookback]
            print(f"{lookback:<12} {r['total_trades']:<10} {r['total_pnl_pct']:>10.2f}%  "
                  f"{r['win_rate']:>10.1f}%  {r['profit_factor']:>8.2f}  "
                  f"{r['max_drawdown']:>10.2f}%  {r.get('avg_sl_points', 0):>10.2f}")
        
        print("\n" + "="*80)
        print("KEY INSIGHTS:")
        print("="*80)
        
        # Calculate averageSL for each
        for lookback, r in all_results.items():
            if 'trades' in r and len(r['trades']) > 0:
                trades_df = pd.DataFrame(r['trades'])
                if 'sl_points' in trades_df.columns:
                    avg_sl = trades_df['sl_points'].mean()
                    r['avg_sl_points'] = avg_sl
        
        # Find best
        best_pnl_lookback = max(all_results.keys(), key=lambda x: all_results[x]['total_pnl_pct'])
        best_pf_lookback = max(all_results.keys(), key=lambda x: all_results[x]['profit_factor'])
        
        print(f"\n✅ Best P&L: {best_pnl_lookback} candles ({all_results[best_pnl_lookback]['total_pnl_pct']:.2f}%)")
        print(f"✅ Best Profit Factor: {best_pf_lookback} candles ({all_results[best_pf_lookback]['profit_factor']:.2f})")
        
        # Recommendation
        print("\n📊 RECOMMENDATION:")
        if best_pnl_lookback == 20:
            print("   Current 20-candle lookback is optimal")
        elif best_pnl_lookback == 10:
            print("   ✨ 10-candle lookback shows better results!")
            print("   Tighter SL = better risk management")
        else:
            print("   ⚠️  5-candle lookback may be too aggressive")
            print("   Very tight SL could lead to premature stopouts")


if __name__ == "__main__":
    main()
