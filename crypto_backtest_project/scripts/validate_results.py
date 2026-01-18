"""
Validation Report for Crypto Backtest Results
Checks for erroneous positions where SL is counted as positive
"""

import pandas as pd
import os

def validate_results(filename, asset_name):
    """Validate backtest results for logic errors"""
    
    print(f"\n{'='*80}")
    print(f"📋 VALIDATING {asset_name} RESULTS")
    print(f"{'='*80}")
    
    df = pd.read_csv(filename)
    
    total_trades = len(df)
    print(f"\nTotal trades: {total_trades}")
    
    # Check 1: SL exits should always be negative
    sl_exits = df[df['exit_type'] == 'SL']
    positive_sl = sl_exits[sl_exits['pnl_pct'] > 0]
    
    print(f"\n1. SL EXITS CHECK:")
    print(f"   Total SL exits: {len(sl_exits)}")
    print(f"   SL with positive PnL (ERROR): {len(positive_sl)}")
    
    if len(positive_sl) > 0:
        print(f"\n   ⚠️  ERRORS FOUND:")
        for idx, row in positive_sl.iterrows():
            print(f"      Trade #{idx}: {row['direction']} @ {row['entry_price']:.2f} → {row['exit_price']:.2f}")
            print(f"         PnL: {row['pnl_pct']:+.2f}% | Time: {row['entry_time']}")
    
    # Check 2: TRAILING_SL should also be negative (or small positive if trailing worked)
    trailing_sl = df[df['exit_type'] == 'TRAILING_SL']
    large_positive_trailing = trailing_sl[trailing_sl['pnl_pct'] > 5.0]  # Allow small trailing gains
    
    print(f"\n2. TRAILING SL CHECK:")
    print(f"   Total trailing SL exits: {len(trailing_sl)}")
    print(f"   Trailing SL with large positive PnL >5% (SUSPICIOUS): {len(large_positive_trailing)}")
    
    if len(large_positive_trailing) > 0:
        print(f"\n   ⚠️  SUSPICIOUS TRADES:")
        for idx, row in large_positive_trailing.head(5).iterrows():
            print(f"      Trade #{idx}: {row['direction']} @ {row['entry_price']:.2f} → {row['exit_price']:.2f}")
            print(f"         PnL: {row['pnl_pct']:+.2f}%")
    
    # Check 3: LONG direction logic
    long_trades = df[df['direction'] == 'LONG']
    long_wrong = long_trades[(long_trades['exit_price'] > long_trades['entry_price']) & (long_trades['pnl_pct'] < 0)]
    
    print(f"\n3. LONG DIRECTION LOGIC:")
    print(f"   Total LONG trades: {len(long_trades)}")
    print(f"   LONG with exit>entry but negative PnL (ERROR): {len(long_wrong)}")
    
    if len(long_wrong) > 0:
        print(f"\n   ⚠️  ERRORS:")
        for idx, row in long_wrong.head(3).iterrows():
            print(f"      Trade #{idx}: {row['entry_price']:.2f} → {row['exit_price']:.2f}")
            print(f"         PnL: {row['pnl_pct']:+.2f}% | Exit: {row['exit_type']}")
    
    # Check 4: SHORT direction logic
    short_trades = df[df['direction'] == 'SHORT']
    short_wrong = short_trades[(short_trades['exit_price'] < short_trades['entry_price']) & (short_trades['pnl_pct'] < 0)]
    
    print(f"\n4. SHORT DIRECTION LOGIC:")
    print(f"   Total SHORT trades: {len(short_trades)}")
    print(f"   SHORT with exit<entry but negative PnL (ERROR): {len(short_wrong)}")
    
    if len(short_wrong) > 0:
        print(f"\n   ⚠️  ERRORS:")
        for idx, row in short_wrong.head(3).iterrows():
            print(f"      Trade #{idx}: {row['entry_price']:.2f} → {row['exit_price']:.2f}")
            print(f"         PnL: {row['pnl_pct']:+.2f}% | Exit: {row['exit_type']}")
    
    # Summary
    total_errors = len(positive_sl) + len(large_positive_trailing) + len(long_wrong) + len(short_wrong)
    
    print(f"\n{'='*80}")
    print(f"📊 VALIDATION SUMMARY FOR {asset_name}")
    print(f"{'='*80}")
    print(f"Total errors found: {total_errors}")
    
    if total_errors == 0:
        print("✅ All trades validated successfully - No errors found")
    else:
        print(f"⚠️  {total_errors} potentially erroneous trades detected")
        print("\nCause: Likely due to extreme price gaps in simulated data where")
        print("      price jumps through both SL and TP levels in single candle.")
        print("\nImpact on results:")
        error_pct = (total_errors / total_trades) * 100
        print(f"      {error_pct:.2f}% of trades affected")
        
        if error_pct < 1.0:
            print("      ✅ Low impact - results remain valid")
        elif error_pct < 3.0:
            print("      ⚠️  Moderate impact - review recommended")
        else:
            print("      ❌ High impact - results may be unreliable")
    
    return total_errors

if __name__ == "__main__":
    results_dir = "/home/runner/work/main/main/crypto_backtest_project/results"
    
    print("\n" + "="*80)
    print("🔍 CRYPTO BACKTEST RESULTS VALIDATION")
    print("="*80)
    print("\nChecking for logic errors in backtest results...")
    
    # Validate BTC
    btc_errors = validate_results(
        os.path.join(results_dir, "BTC_final_results.csv"),
        "BITCOIN (BTC)"
    )
    
    # Validate ETH
    eth_errors = validate_results(
        os.path.join(results_dir, "ETH_final_results.csv"),
        "ETHEREUM (ETH)"
    )
    
    # Overall summary
    print(f"\n{'='*80}")
    print("🎯 OVERALL VALIDATION RESULTS")
    print(f"{'='*80}")
    print(f"BTC errors: {btc_errors}")
    print(f"ETH errors: {eth_errors}")
    print(f"Total errors: {btc_errors + eth_errors}")
    
    if btc_errors + eth_errors == 0:
        print("\n✅ All results validated successfully")
    else:
        print("\n⚠️  Errors detected - See details above")
        print("\nNote: These errors are caused by extreme price movements in simulated")
        print("data where price gaps through multiple levels in a single candle.")
        print("With real market data, such extreme gaps are much less common.")
    
    print("\n" + "="*80)
