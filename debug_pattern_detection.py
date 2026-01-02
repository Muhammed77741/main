"""
Debug: Проверить детекцию паттернов на SMC сигналах

Цель: Понять почему паттерны не детектируются
"""

import pandas as pd
import numpy as np
from pattern_recognition_strategy import PatternRecognitionStrategy


def detect_pattern(df, idx):
    """
    Detect chart pattern at index
    """
    if idx < 40:
        return None

    swing_lookback = 20
    recent_data = df.iloc[max(0, idx-swing_lookback):idx]

    if len(recent_data) < 10:
        return None

    # Find swing points
    swing_highs = []
    swing_lows = []

    for i in range(5, len(recent_data)-5):
        window_highs = recent_data['high'].iloc[i-5:i+6]
        if recent_data['high'].iloc[i] == window_highs.max():
            swing_highs.append({
                'idx': i,
                'high': recent_data['high'].iloc[i]
            })

        window_lows = recent_data['low'].iloc[i-5:i+6]
        if recent_data['low'].iloc[i] == window_lows.min():
            swing_lows.append({
                'idx': i,
                'low': recent_data['low'].iloc[i]
            })

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return None

    high1 = swing_highs[-2]['high']
    high2 = swing_highs[-1]['high']
    low1 = swing_lows[-2]['low']
    low2 = swing_lows[-1]['low']

    tolerance = high1 * 0.02
    current_close = df['close'].iloc[idx]

    # Ascending Triangle
    if abs(high1 - high2) <= tolerance and low2 > low1:
        if current_close > max(high1, high2):
            return 'asc_triangle'

    # Descending Triangle
    if abs(low1 - low2) <= tolerance and high2 < high1:
        if current_close < min(low1, low2):
            return 'desc_triangle'

    # Falling Wedge
    if high2 < high1 and low2 < low1:
        high_slope = (high1 - high2) / high1
        low_slope = (low1 - low2) / low1
        if high_slope > low_slope:
            if current_close > high2:
                return 'falling_wedge'

    # Rising Wedge
    if high2 > high1 and low2 > low1:
        high_slope = (high2 - high1) / high1
        low_slope = (low2 - low1) / low1
        if low_slope > high_slope:
            if current_close < low2:
                return 'rising_wedge'

    # Symmetrical Triangle
    if high2 < high1 and low2 > low1:
        if current_close > high2:
            return 'sym_triangle'

    return None


def main():
    print("\n" + "="*80)
    print("🔍 DEBUG: Детекция паттернов на SMC сигналах")
    print("="*80)

    # Load data
    df = pd.read_csv('XAUUSD_1H_MT5_20241227_20251227.csv')
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')

    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_active'] = df['is_london'] | df['is_ny']

    # Run SMC strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    df_signals = strategy.run_strategy(df.copy())

    # Check patterns on all signals
    pattern_counts = {}
    signal_indices = df_signals[df_signals['signal'] != 0].index

    print(f"\n📊 Проверка {len(signal_indices)} SMC сигналов...")

    for idx_pos, signal_time in enumerate(signal_indices):
        idx = df_signals.index.get_loc(signal_time)
        pattern = detect_pattern(df_signals, idx)

        pattern_key = pattern if pattern else 'none'
        pattern_counts[pattern_key] = pattern_counts.get(pattern_key, 0) + 1

    print(f"\n📊 РЕЗУЛЬТАТЫ ДЕТЕКЦИИ:")
    print(f"{'='*80}")

    total_signals = len(signal_indices)
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / total_signals * 100
        print(f"   {pattern}: {count} ({pct:.1f}%)")

    # Check if patterns exist at all
    print(f"\n{'='*80}")
    print(f"🔍 ПРОВЕРКА: Есть ли паттерны в данных вообще?")
    print(f"{'='*80}")

    all_pattern_counts = {}
    check_every = 10  # Check every 10th candle

    print(f"\n   Проверка каждой {check_every}-й свечи...")

    for i in range(0, len(df_signals), check_every):
        pattern = detect_pattern(df_signals, i)
        if pattern:
            pattern_key = pattern
            all_pattern_counts[pattern_key] = all_pattern_counts.get(pattern_key, 0) + 1

    if len(all_pattern_counts) > 0:
        print(f"\n   ✅ Паттерны НАЙДЕНЫ в данных:")
        for pattern, count in sorted(all_pattern_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      {pattern}: {count} раз")
    else:
        print(f"\n   ❌ Паттерны НЕ НАЙДЕНЫ (функция detect_pattern() не работает)")

    print(f"\n{'='*80}")
    print(f"💡 ВЫВОДЫ")
    print(f"{'='*80}")

    if pattern_counts.get('none', 0) == total_signals:
        print(f"\n   ❌ НИ ОДИН SMC сигнал не совпал с паттерном!")
        print(f"\n   Причины:")
        print(f"   1. SMC сигналы и паттерны формируются в разное время")
        print(f"   2. Условия детекции слишком строгие")
        print(f"   3. Паттерны формируются позже/раньше чем SMC сигналы")
        print(f"\n   Решение:")
        print(f"   - Проверять паттерн не в момент сигнала, а в окне до/после")
        print(f"   - Ослабить условия детекции (tolerance, lookback)")
        print(f"   - Использовать другой подход (pattern confirmation)")
    else:
        found_patterns = total_signals - pattern_counts.get('none', 0)
        print(f"\n   ✅ Найдено {found_patterns} SMC сигналов с паттернами!")
        print(f"\n   Паттерны на сигналах:")
        for pattern, count in pattern_counts.items():
            if pattern != 'none':
                print(f"      {pattern}: {count}")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
