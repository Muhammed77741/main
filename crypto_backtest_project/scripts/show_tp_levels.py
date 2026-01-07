"""
Show real TP levels on actual prices
"""

import pandas as pd
from datetime import timedelta

from pattern_recognition_strategy import PatternRecognitionStrategy


def load_mt5_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load MT5 XAUUSD data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]

    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def show_tp_examples():
    """Show real examples with TP levels"""

    print("\n" + "=" * 90)
    print("ПРИМЕРЫ УРОВНЕЙ TP НА РЕАЛЬНЫХ ЦЕНАХ")
    print("=" * 90)

    # Load data
    df = load_mt5_data()

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Run strategy
    print("\n🔍 Запуск стратегии...")
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    print(f"✅ Найдено {len(df_signals)} сигналов\n")

    # TP levels (as calculated in partial close backtest)
    TP1_POINTS = 30
    TP2_POINTS = 50
    TP3_POINTS = 80

    # Show last 10 signals with all details
    last_signals = df_signals.tail(10)

    print("=" * 90)
    print("ПОСЛЕДНИЕ 10 СИГНАЛОВ С УРОВНЯМИ TP")
    print("=" * 90)

    for idx, (timestamp, signal) in enumerate(last_signals.iterrows(), 1):
        direction = "LONG" if signal['signal'] == 1 else "SHORT"
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']

        # Calculate TP levels
        if signal['signal'] == 1:  # LONG
            tp1 = entry_price + TP1_POINTS
            tp2 = entry_price + TP2_POINTS
            tp3 = entry_price + TP3_POINTS
            risk = entry_price - stop_loss
        else:  # SHORT
            tp1 = entry_price - TP1_POINTS
            tp2 = entry_price - TP2_POINTS
            tp3 = entry_price - TP3_POINTS
            risk = stop_loss - entry_price

        emoji = "🟢" if direction == "LONG" else "🔴"

        print(f"\n{emoji} Сигнал #{idx} - {direction}")
        print(f"{'─'*90}")
        print(f"   📅 Время: {timestamp.strftime('%Y-%m-%d %H:%M')}")
        print(f"   📊 Цена входа: {entry_price:.2f}")
        print(f"")
        print(f"   🛑 Stop Loss:  {stop_loss:.2f} (риск: {risk:.2f} пунктов)")
        print(f"")
        print(f"   🎯 TP1 ({TP1_POINTS}п):  {tp1:.2f} → закрыть 50% позиции")
        print(f"   🎯 TP2 ({TP2_POINTS}п):  {tp2:.2f} → закрыть 30% позиции")
        print(f"   🎯 TP3 ({TP3_POINTS}п):  {tp3:.2f} → закрыть 20% позиции")
        print(f"")

        # Show what happened
        search_end = timestamp + timedelta(hours=48)
        df_future = df_strategy[(df_strategy.index > timestamp) & (df_strategy.index <= search_end)]

        if len(df_future) > 0:
            if signal['signal'] == 1:  # LONG
                max_reached = df_future['high'].max()
                min_reached = df_future['low'].min()

                tp1_hit = "✅ ДОСТИГ" if max_reached >= tp1 else "❌ НЕ ДОСТИГ"
                tp2_hit = "✅ ДОСТИГ" if max_reached >= tp2 else "❌ НЕ ДОСТИГ"
                tp3_hit = "✅ ДОСТИГ" if max_reached >= tp3 else "❌ НЕ ДОСТИГ"
                sl_hit = "🛑 СРАБОТАЛ" if min_reached <= stop_loss else "✅ НЕ СРАБОТАЛ"

                print(f"   Фактически:")
                print(f"      Макс цена: {max_reached:.2f}")
                print(f"      TP1: {tp1_hit}")
                print(f"      TP2: {tp2_hit}")
                print(f"      TP3: {tp3_hit}")
                print(f"      SL:  {sl_hit}")

            else:  # SHORT
                max_reached = df_future['high'].max()
                min_reached = df_future['low'].min()

                tp1_hit = "✅ ДОСТИГ" if min_reached <= tp1 else "❌ НЕ ДОСТИГ"
                tp2_hit = "✅ ДОСТИГ" if min_reached <= tp2 else "❌ НЕ ДОСТИГ"
                tp3_hit = "✅ ДОСТИГ" if min_reached <= tp3 else "❌ НЕ ДОСТИГ"
                sl_hit = "🛑 СРАБОТАЛ" if max_reached >= stop_loss else "✅ НЕ СРАБОТАЛ"

                print(f"   Фактически:")
                print(f"      Мин цена: {min_reached:.2f}")
                print(f"      TP1: {tp1_hit}")
                print(f"      TP2: {tp2_hit}")
                print(f"      TP3: {tp3_hit}")
                print(f"      SL:  {sl_hit}")

    # Show average prices
    print("\n" + "=" * 90)
    print("СТАТИСТИКА ПО ВСЕМ СИГНАЛАМ")
    print("=" * 90)

    avg_entry = df_signals['entry_price'].mean()
    avg_sl_distance = (df_signals['entry_price'] - df_signals['stop_loss']).abs().mean()

    print(f"\n📊 Средние значения по {len(df_signals)} сигналам:")
    print(f"   Средняя цена входа: {avg_entry:.2f}")
    print(f"   Средний SL (риск): {avg_sl_distance:.2f} пунктов")
    print(f"")
    print(f"   Уровни TP:")
    print(f"   TP1: ~{avg_entry:.2f} ± {TP1_POINTS} = {avg_entry-TP1_POINTS:.2f} / {avg_entry+TP1_POINTS:.2f}")
    print(f"   TP2: ~{avg_entry:.2f} ± {TP2_POINTS} = {avg_entry-TP2_POINTS:.2f} / {avg_entry+TP2_POINTS:.2f}")
    print(f"   TP3: ~{avg_entry:.2f} ± {TP3_POINTS} = {avg_entry-TP3_POINTS:.2f} / {avg_entry+TP3_POINTS:.2f}")

    # Show example for current price
    current_price = df['close'].iloc[-1]
    print(f"\n" + "=" * 90)
    print(f"ПРИМЕР ДЛЯ ТЕКУЩЕЙ ЦЕНЫ: {current_price:.2f}")
    print("=" * 90)

    print(f"\n🟢 Если сейчас LONG сигнал на {current_price:.2f}:")
    print(f"   🛑 SL:  ~{current_price - avg_sl_distance:.2f} (риск {avg_sl_distance:.0f}п)")
    print(f"   🎯 TP1: {current_price + TP1_POINTS:.2f} (+{TP1_POINTS}п) → закрыть 50%")
    print(f"   🎯 TP2: {current_price + TP2_POINTS:.2f} (+{TP2_POINTS}п) → закрыть 30%")
    print(f"   🎯 TP3: {current_price + TP3_POINTS:.2f} (+{TP3_POINTS}п) → закрыть 20%")
    print(f"")
    print(f"   💰 При лоте 0.01:")
    print(f"      TP1: +${TP1_POINTS * 0.01 * 0.5:.2f} (50% позиции)")
    print(f"      TP2: +${TP2_POINTS * 0.01 * 0.3:.2f} (30% позиции)")
    print(f"      TP3: +${TP3_POINTS * 0.01 * 0.2:.2f} (20% позиции)")
    print(f"      ИТОГО: +${(TP1_POINTS * 0.5 + TP2_POINTS * 0.3 + TP3_POINTS * 0.2) * 0.01:.2f}")

    print(f"\n🔴 Если сейчас SHORT сигнал на {current_price:.2f}:")
    print(f"   🛑 SL:  ~{current_price + avg_sl_distance:.2f} (риск {avg_sl_distance:.0f}п)")
    print(f"   🎯 TP1: {current_price - TP1_POINTS:.2f} (-{TP1_POINTS}п) → закрыть 50%")
    print(f"   🎯 TP2: {current_price - TP2_POINTS:.2f} (-{TP2_POINTS}п) → закрыть 30%")
    print(f"   🎯 TP3: {current_price - TP3_POINTS:.2f} (-{TP3_POINTS}п) → закрыть 20%")
    print(f"")
    print(f"   💰 При лоте 0.01:")
    print(f"      TP1: +${TP1_POINTS * 0.01 * 0.5:.2f} (50% позиции)")
    print(f"      TP2: +${TP2_POINTS * 0.01 * 0.3:.2f} (30% позиции)")
    print(f"      TP3: +${TP3_POINTS * 0.01 * 0.2:.2f} (20% позиции)")
    print(f"      ИТОГО: +${(TP1_POINTS * 0.5 + TP2_POINTS * 0.3 + TP3_POINTS * 0.2) * 0.01:.2f}")

    # Show percentage achievement
    print("\n" + "=" * 90)
    print("ПРОЦЕНТ ДОСТИЖЕНИЯ КАЖДОГО УРОВНЯ")
    print("=" * 90)

    tp1_count = 0
    tp2_count = 0
    tp3_count = 0
    sl_count = 0

    for timestamp, signal in df_signals.iterrows():
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        direction = signal['signal']

        search_end = timestamp + timedelta(hours=48)
        df_future = df_strategy[(df_strategy.index > timestamp) & (df_strategy.index <= search_end)]

        if len(df_future) == 0:
            continue

        if direction == 1:  # LONG
            tp1_price = entry_price + TP1_POINTS
            tp2_price = entry_price + TP2_POINTS
            tp3_price = entry_price + TP3_POINTS

            max_price = df_future['high'].max()
            min_price = df_future['low'].min()

            if max_price >= tp1_price:
                tp1_count += 1
            if max_price >= tp2_price:
                tp2_count += 1
            if max_price >= tp3_price:
                tp3_count += 1
            if min_price <= stop_loss:
                sl_count += 1

        else:  # SHORT
            tp1_price = entry_price - TP1_POINTS
            tp2_price = entry_price - TP2_POINTS
            tp3_price = entry_price - TP3_POINTS

            max_price = df_future['high'].max()
            min_price = df_future['low'].min()

            if min_price <= tp1_price:
                tp1_count += 1
            if min_price <= tp2_price:
                tp2_count += 1
            if min_price <= tp3_price:
                tp3_count += 1
            if max_price >= stop_loss:
                sl_count += 1

    total = len(df_signals)

    print(f"\n📊 Из {total} сигналов:")
    print(f"   TP1 ({TP1_POINTS}п): {tp1_count} сигналов ({tp1_count/total*100:.1f}%) 🎯")
    print(f"   TP2 ({TP2_POINTS}п): {tp2_count} сигналов ({tp2_count/total*100:.1f}%) 🎯")
    print(f"   TP3 ({TP3_POINTS}п): {tp3_count} сигналов ({tp3_count/total*100:.1f}%) 🎯")
    print(f"   SL сработал: {sl_count} сигналов ({sl_count/total*100:.1f}%) 🛑")

    print("\n" + "=" * 90)
    print("✅ ГОТОВО!")
    print("=" * 90)


if __name__ == "__main__":
    show_tp_examples()
