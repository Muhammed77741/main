"""
Debug script to trace SL/TP swap bug
"""
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Patch all the strategies to print when they set SL/TP
from simplified_smc_strategy import SimplifiedSMCStrategy
from intraday_gold_strategy import IntradayGoldStrategy  
from fibonacci_1618_strategy import Fibonacci1618Strategy
from pattern_recognition_strategy import PatternRecognitionStrategy

original_simplified_run = SimplifiedSMCStrategy.run_strategy

def debug_simplified_run(self, df):
    print("\n=== SimplifiedSMCStrategy.run_strategy CALLED ===")
    result = original_simplified_run(self, df)
    
    # Check first signal
    signals = result[result['signal'] != 0]
    if len(signals) > 0:
        sig_time = signals.index[0]
        sig = signals.iloc[0]
        print(f"SimplifiedSMC created signal at {sig_time}:")
        print(f"  Entry: {sig['entry_price']}")
        print(f"  SL: {sig['stop_loss']}")
        print(f"  TP: {sig['take_profit']}")
    
    return result

SimplifiedSMCStrategy.run_strategy = debug_simplified_run

# Load data
df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.set_index('datetime')
df['is_london'] = df.index.hour.isin(range(7, 12))
df['is_ny'] = df.index.hour.isin(range(13, 20))
df['is_overlap'] = df.index.hour.isin(range(13, 16))
df['is_active'] = df['is_london'] | df['is_ny']
df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

# Run just to first signal
df_small = df[df.index <= pd.Timestamp('2025-01-08')].copy()

print("\nRunning PatternRecognitionStrategy on small dataset...")
strategy = PatternRecognitionStrategy(fib_mode='standard')
result = strategy.run_strategy(df_small)

# Check first signal
signals = result[result['signal'] != 0]
print(f"\n=== FINAL RESULT: {len(signals)} signals ===")
if len(signals) > 0:
    sig_time = signals.index[0]
    sig = signals.iloc[0]
    print(f"First signal at {sig_time}:")
    print(f"  Entry: {sig['entry_price']}")
    print(f"  SL: {sig['stop_loss']}")
    print(f"  TP: {sig['take_profit']}")
    print(f"\n  Expected for LONG: SL < Entry < TP")
    print(f"  Actual: SL={sig['stop_loss']} {'<' if sig['stop_loss'] < sig['entry_price'] else '>'} Entry={sig['entry_price']} {'<' if sig['entry_price'] < sig['take_profit'] else '>'} TP={sig['take_profit']}")
