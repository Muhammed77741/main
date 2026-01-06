#!/usr/bin/env python3
"""
Test to compare V3 Adaptive backtest performance with different swing lookback periods.
Tests 20, 10, and 5 candles lookback to optimize SL placement.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
from pattern_recognition_strategy import PatternRecognitionStrategy
from backtest_v3_adaptive import AdaptiveBacktestV3


def monkey_patch_swing_lookback(lookback_period):
    """Monkey-patch the _calculate_stop_loss method to use custom lookback period."""
    original_method = PatternRecognitionStrategy._calculate_stop_loss
    
    def patched_calculate_stop_loss(self, df, idx, direction):
        """Modified version with custom swing lookback period."""
        if direction == 1:  # Long
            # Stop below recent swing low (modified lookback)
            recent_data = df.iloc[max(0, idx-lookback_period):idx]
            recent_swings = recent_data[recent_data['swing_low']]
            if len(recent_swings) > 0:
                stop = recent_swings['low'].min()
            else:
                # Fallback: lowest low in last lookback candles
                stop = df.iloc[max(0, idx-lookback_period):idx]['low'].min()
            return stop - 0.5  # Small buffer
        
        else:  # Short (direction == -1)
            # Stop above recent swing high (modified lookback)
            recent_data = df.iloc[max(0, idx-lookback_period):idx]
            recent_swings = recent_data[recent_data['swing_high']]
            if len(recent_swings) > 0:
                stop = recent_swings['high'].max()
            else:
                # Fallback: highest high in last lookback candles
                stop = df.iloc[max(0, idx-lookback_period):idx]['high'].max()
            return stop + 0.5  # Small buffer
    
    # Apply monkey patch
    PatternRecognitionStrategy._calculate_stop_loss = patched_calculate_stop_loss
    
    return original_method


def restore_original_method(original_method):
    """Restore original _calculate_stop_loss method."""
    PatternRecognitionStrategy._calculate_stop_loss = original_method


def run_backtest_with_lookback(lookback):
    """Run V3 Adaptive backtest with specified swing lookback period."""
    print(f"\n{'='*80}")
    print(f"TESTING SWING LOOKBACK: {lookback} CANDLES")
    print(f"{'='*80}\n")
    
    # Load data
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_file = os.path.join(base_dir, 'XAUUSD_1H_MT5_20241227_20251227.csv')
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return None
    
    df = pd.read_csv(data_file, parse_dates=['datetime'])
    df = df.rename(columns={'datetime': 'time'})
    df = df.set_index('time')
    print(f"✅ Loaded {len(df)} candles from {df.index.min()} to {df.index.max()}")
    
    # Apply monkey patch
    original_method = monkey_patch_swing_lookback(lookback)
    
    try:
        # Initialize strategy
        strategy = PatternRecognitionStrategy(fib_mode='standard')
        
        # Run adaptive backtest
        backtest = AdaptiveBacktestV3()
        trades_df = backtest.backtest(df, strategy)
        
        if trades_df is None or len(trades_df) == 0:
            print("❌ No trades generated")
            return None
        
        # Calculate metrics
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['profit'] > 0])
        losses = len(trades_df[trades_df['profit'] < 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = trades_df['profit'].sum()
        gross_profit = trades_df[trades_df['profit'] > 0]['profit'].sum()
        gross_loss = abs(trades_df[trades_df['profit'] < 0]['profit'].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        # Calculate average SL distance
        avg_sl_distance = abs(trades_df['entry_price'] - trades_df['sl']).mean()
        
        # Calculate max drawdown
        cumulative_pnl = trades_df['profit'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        max_dd = drawdown.min()
        
        results = {
            'lookback': lookback,
            'trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl': total_profit,
            'profit_factor': profit_factor,
            'max_dd': max_dd,
            'avg_sl_distance': avg_sl_distance
        }
        
        print(f"✅ Backtest complete:")
        print(f"   Trades: {total_trades}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Total P&L: {total_profit:.2f}%")
        print(f"   Profit Factor: {profit_factor:.2f}")
        print(f"   Max DD: {max_dd:.2f}%")
        print(f"   Avg SL Distance: {avg_sl_distance:.2f} points")
        
        return results
        
    finally:
        # Restore original method
        restore_original_method(original_method)


def main():
    print("="*80)
    print("V3 ADAPTIVE BACKTEST - SWING LOOKBACK COMPARISON")
    print("="*80)
    print("\nTesting swing lookback periods: 20, 10, and 5 candles")
    print("This affects how far back the strategy looks for swing points to place SL\n")
    
    lookback_periods = [20, 10, 5]
    all_results = []
    
    for lookback in lookback_periods:
        results = run_backtest_with_lookback(lookback)
        if results:
            all_results.append(results)
    
    # Print comparison table
    if len(all_results) > 0:
        print(f"\n{'='*80}")
        print("COMPARISON RESULTS")
        print(f"{'='*80}\n")
        
        print(f"{'Lookback':<12} {'Trades':<8} {'P&L %':<10} {'Win Rate':<10} {'PF':<8} {'Max DD %':<10} {'Avg SL':<10}")
        print("-" * 80)
        
        for r in all_results:
            print(f"{r['lookback']:<12} {r['trades']:<8} {r['total_pnl']:<10.2f} {r['win_rate']:<10.1f} {r['profit_factor']:<8.2f} {r['max_dd']:<10.2f} {r['avg_sl_distance']:<10.2f}")
        
        # Recommendation
        best_pnl = max(all_results, key=lambda x: x['total_pnl'])
        best_pf = max(all_results, key=lambda x: x['profit_factor'])
        smallest_sl = min(all_results, key=lambda x: x['avg_sl_distance'])
        
        print(f"\n{'='*80}")
        print("RECOMMENDATIONS")
        print(f"{'='*80}")
        print(f"✅ Best P&L: {best_pnl['lookback']} candles ({best_pnl['total_pnl']:.2f}%)")
        print(f"✅ Best Profit Factor: {best_pf['lookback']} candles (PF: {best_pf['profit_factor']:.2f})")
        print(f"✅ Smallest SL: {smallest_sl['lookback']} candles ({smallest_sl['avg_sl_distance']:.2f} points)")
        print(f"\n💡 Smaller lookback = tighter SL = better risk/reward ratio")
        print(f"💡 Choose lookback that balances performance with risk management")


if __name__ == '__main__':
    main()
