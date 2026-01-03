"""
Test for repainting in LIVE scenario
Simulates live trading where new candles arrive one by one
"""

import pandas as pd
from smc_trading_strategy.pattern_recognition_strategy import PatternRecognitionStrategy

def test_live_repainting():
    """
    Simulate live trading - check if signals appear on old candles
    when new candles arrive
    """
    print("\n" + "="*80)
    print("🔍 LIVE REPAINTING TEST")
    print("="*80)

    # Load data
    df_full = pd.read_csv('XAUUSD_1H_MT5_20241227_20251227.csv')
    df_full['datetime'] = pd.to_datetime(df_full['datetime'])
    df_full = df_full.set_index('datetime')

    # Add session filter
    if 'is_active' not in df_full.columns:
        df_full['is_london'] = df_full.index.hour.isin(range(7, 12))
        df_full['is_ny'] = df_full.index.hour.isin(range(13, 20))
        df_full['is_active'] = df_full['is_london'] | df_full['is_ny']

    # Create strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    print(f"\n📊 Total candles available: {len(df_full)}")
    print(f"\n🔄 SIMULATING LIVE TRADING...")
    print(f"   Starting with 500 candles, then adding 1 candle at a time")

    # Start with 500 candles
    window_size = 500
    df_initial = df_full.iloc[:window_size].copy()

    print(f"\n{'='*80}")
    print(f"INITIAL RUN: {window_size} candles")
    print(f"{'='*80}")

    df_result_initial = strategy.run_strategy(df_initial)
    signals_initial = df_result_initial[df_result_initial['signal'] != 0]

    print(f"   Signals: {len(signals_initial)}")

    # Store initial signals
    initial_signal_times = set(signals_initial.index)

    # Simulate adding new candles one by one
    repainting_detected = []

    print(f"\n{'='*80}")
    print(f"ADDING NEW CANDLES (simulating live trading)")
    print(f"{'='*80}")

    # Add 50 new candles one by one
    for new_size in range(window_size + 1, window_size + 51):
        df_current = df_full.iloc[:new_size].copy()
        df_result_current = strategy.run_strategy(df_current)
        signals_current = df_result_current[df_result_current['signal'] != 0]

        # Get signals in the INITIAL window (first 500 candles)
        initial_window = df_initial.index
        signals_in_initial_window = signals_current[signals_current.index.isin(initial_window)]
        current_signal_times = set(signals_in_initial_window.index)

        # Check for new signals in the initial window
        new_signals = current_signal_times - initial_signal_times

        if len(new_signals) > 0:
            for signal_time in new_signals:
                candles_added = new_size - window_size
                signal_idx = df_initial.index.get_loc(signal_time)
                candles_behind = window_size - 1 - signal_idx

                row = signals_current.loc[signal_time]
                direction = 'LONG' if row['signal'] == 1 else 'SHORT'

                repainting_detected.append({
                    'signal_time': signal_time,
                    'direction': direction,
                    'entry': row['entry_price'],
                    'candles_behind': candles_behind,
                    'appeared_after_candles': candles_added
                })

                print(f"\n⚠️ REPAINTING! New signal appeared on OLD candle:")
                print(f"   Time: {signal_time}")
                print(f"   Direction: {direction} @ {row['entry_price']:.2f}")
                print(f"   Candles behind: {candles_behind}")
                print(f"   Appeared after adding {candles_added} new candles")

            # Update initial_signal_times to include new signals
            initial_signal_times = current_signal_times

    # Summary
    print(f"\n{'='*80}")
    print(f"📊 SUMMARY")
    print(f"{'='*80}")

    if len(repainting_detected) > 0:
        print(f"\n🚨 REPAINTING DETECTED!")
        print(f"   Total repainting signals: {len(repainting_detected)}")
        print(f"\n   Examples:")
        for i, signal in enumerate(repainting_detected[:5]):
            print(f"   {i+1}. {signal['signal_time']}: {signal['direction']} @ {signal['entry']:.2f}")
            print(f"      → Was {signal['candles_behind']} candles behind")
            print(f"      → Appeared after {signal['appeared_after_candles']} new candles added")

        print(f"\n   ⚠️ This is the SAME problem as in live bot:")
        print(f"   - Signals appear on old candles after new data arrives")
        print(f"   - User sees signal from 15:00 but notification comes at 22:05")
        print(f"   - Live bot was correct to reject these signals!")

    else:
        print(f"\n✅ NO REPAINTING DETECTED")
        print(f"   All signals appeared consistently")

if __name__ == "__main__":
    test_live_repainting()
