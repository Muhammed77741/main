"""
Test for repainting in backtest
Проверяет, появляются ли сигналы на старых свечах после добавления новых
"""

import pandas as pd
import numpy as np
from smc_trading_strategy.pattern_recognition_strategy import PatternRecognitionStrategy

def test_repainting():
    """
    Test if signals appear on old candles after new candles are added
    """
    print("\n" + "="*80)
    print("🔍 REPAINTING TEST")
    print("="*80)

    # Load data
    df = pd.read_csv('XAUUSD_1H_MT5_20241227_20251227.csv')
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')

    # Add session filter
    if 'is_active' not in df.columns:
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_active'] = df['is_london'] | df['is_ny']

    # Create strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    print(f"\n📊 Total candles available: {len(df)}")

    # TEST 1: Run strategy on first 1000 candles
    print(f"\n{'='*80}")
    print(f"TEST 1: Running strategy on first 1000 candles")
    print(f"{'='*80}")

    df_subset1 = df.iloc[:1000].copy()
    df_result1 = strategy.run_strategy(df_subset1)
    signals1 = df_result1[df_result1['signal'] != 0]

    print(f"   Candles: {len(df_result1)}")
    print(f"   Signals found: {len(signals1)}")

    if len(signals1) > 0:
        print(f"\n   Last 5 signals:")
        for idx, row in signals1.tail(5).iterrows():
            print(f"   {idx}: {'LONG' if row['signal'] == 1 else 'SHORT'} @ {row['entry_price']:.2f}")

    # TEST 2: Run strategy on first 1500 candles
    print(f"\n{'='*80}")
    print(f"TEST 2: Running strategy on first 1500 candles")
    print(f"{'='*80}")

    df_subset2 = df.iloc[:1500].copy()
    df_result2 = strategy.run_strategy(df_subset2)
    signals2 = df_result2[df_result2['signal'] != 0]

    print(f"   Candles: {len(df_result2)}")
    print(f"   Signals found: {len(signals2)}")

    if len(signals2) > 0:
        print(f"\n   Last 5 signals:")
        for idx, row in signals2.tail(5).iterrows():
            print(f"   {idx}: {'LONG' if row['signal'] == 1 else 'SHORT'} @ {row['entry_price']:.2f}")

    # REPAINTING CHECK: Compare signals in overlapping period
    print(f"\n{'='*80}")
    print(f"🚨 REPAINTING CHECK")
    print(f"{'='*80}")

    # Get signals in first 1000 candles from both runs
    overlap_period = df_subset1.index

    signals1_overlap = signals1[signals1.index.isin(overlap_period)]
    signals2_overlap = signals2[signals2.index.isin(overlap_period)]

    print(f"\n   Signals in first 1000 candles:")
    print(f"   Run 1 (1000 candles): {len(signals1_overlap)} signals")
    print(f"   Run 2 (1500 candles): {len(signals2_overlap)} signals")

    if len(signals2_overlap) > len(signals1_overlap):
        new_signals = len(signals2_overlap) - len(signals1_overlap)
        print(f"\n   ⚠️ REPAINTING DETECTED!")
        print(f"   {new_signals} NEW signals appeared on old candles after adding 500 new candles!")

        # Find the new signals
        signals1_times = set(signals1_overlap.index)
        signals2_times = set(signals2_overlap.index)
        new_signal_times = signals2_times - signals1_times

        print(f"\n   New signals that appeared retroactively:")
        for time in sorted(new_signal_times)[:10]:  # Show first 10
            row = signals2.loc[time]
            print(f"   {time}: {'LONG' if row['signal'] == 1 else 'SHORT'} @ {row['entry_price']:.2f}")

            # How many candles later did this signal appear?
            candle_idx_in_1000 = df_subset1.index.get_loc(time)
            candles_from_end = len(df_subset1) - 1 - candle_idx_in_1000
            print(f"      → Signal appeared {candles_from_end} candles before end of Run 1")
            print(f"      → But only detected in Run 2 (500 candles later)")

    elif len(signals2_overlap) == len(signals1_overlap):
        print(f"\n   ✅ NO REPAINTING - same number of signals")

        # But check if signals are at same times
        signals1_times = set(signals1_overlap.index)
        signals2_times = set(signals2_overlap.index)

        if signals1_times == signals2_times:
            print(f"   ✅ All signals at same timestamps - CONSISTENT")
        else:
            print(f"   ⚠️ REPAINTING - signals at different timestamps!")

    else:
        print(f"\n   ⚠️ UNEXPECTED: Run 2 has FEWER signals than Run 1")

if __name__ == "__main__":
    test_repainting()
