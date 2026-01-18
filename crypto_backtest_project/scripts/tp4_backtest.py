"""
Backtest with 4 TP levels - добавляем TP4 для 10-20% капитала
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from pattern_recognition_strategy import PatternRecognitionStrategy


def load_mt5_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load MT5 XAUUSD data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Add market hours
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def backtest_4tp(df, strategy, tp1, tp2, tp3, tp4,
                 close_pct1, close_pct2, close_pct3, close_pct4,
                 variant_name):
    """
    Backtest with 4 TP levels

    Args:
        tp1, tp2, tp3, tp4: TP levels in points
        close_pct1, close_pct2, close_pct3, close_pct4: % to close at each TP
    """

    print(f"\n{'='*80}")
    print(f"ТЕСТ: {variant_name}")
    print(f"{'='*80}")

    print(f"\n🎯 Уровни TP:")
    print(f"   TP1: {tp1}п → закрыть {close_pct1*100:.0f}% позиции")
    print(f"   TP2: {tp2}п → закрыть {close_pct2*100:.0f}% позиции")
    print(f"   TP3: {tp3}п → закрыть {close_pct3*100:.0f}% позиции")
    print(f"   TP4: {tp4}п → закрыть {close_pct4*100:.0f}% позиции (дальняя цель!)")
    print(f"   Таймаут: 48 часов")

    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    print(f"\n🔍 Найдено сигналов: {len(df_signals)}")

    trades = []

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        direction = signal['signal']
        entry_time = df_signals.index[i]

        # Track position
        position_remaining = 1.0
        total_pnl_pct = 0.0

        exit_price = None
        exit_type = 'EOD'
        exit_time = None

        tp1_hit = False
        tp2_hit = False
        tp3_hit = False
        tp4_hit = False
        sl_hit = False

        # TP prices
        if direction == 1:  # LONG
            tp1_price = entry_price + tp1
            tp2_price = entry_price + tp2
            tp3_price = entry_price + tp3
            tp4_price = entry_price + tp4
        else:  # SHORT
            tp1_price = entry_price - tp1
            tp2_price = entry_price - tp2
            tp3_price = entry_price - tp3
            tp4_price = entry_price - tp4

        # Look ahead 48 hours
        search_end = entry_time + timedelta(hours=48)
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]

        if len(df_future) == 0:
            continue

        # Check each candle
        for j in range(len(df_future)):
            candle_time = df_future.index[j]
            high = df_future['high'].iloc[j]
            low = df_future['low'].iloc[j]
            close_price = df_future['close'].iloc[j]

            if position_remaining <= 0:
                break

            if direction == 1:  # LONG
                # Check SL first
                if low <= stop_loss and not sl_hit:
                    sl_pnl_pct = ((stop_loss - entry_price) / entry_price) * 100 * position_remaining
                    total_pnl_pct += sl_pnl_pct
                    position_remaining = 0
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = candle_time
                    sl_hit = True
                    break

                # Check TPs in order
                if high >= tp4_price and not tp4_hit and position_remaining > 0:
                    tp4_pnl_pct = ((tp4_price - entry_price) / entry_price) * 100 * close_pct4
                    total_pnl_pct += tp4_pnl_pct
                    position_remaining -= close_pct4
                    exit_price = tp4_price
                    exit_type = 'TP4'
                    exit_time = candle_time
                    tp4_hit = True

                if high >= tp3_price and not tp3_hit and position_remaining > 0:
                    tp3_pnl_pct = ((tp3_price - entry_price) / entry_price) * 100 * close_pct3
                    total_pnl_pct += tp3_pnl_pct
                    position_remaining -= close_pct3
                    exit_price = tp3_price
                    exit_type = 'TP3'
                    exit_time = candle_time
                    tp3_hit = True

                if high >= tp2_price and not tp2_hit and position_remaining > 0:
                    tp2_pnl_pct = ((tp2_price - entry_price) / entry_price) * 100 * close_pct2
                    total_pnl_pct += tp2_pnl_pct
                    position_remaining -= close_pct2
                    exit_price = tp2_price
                    exit_type = 'TP2'
                    exit_time = candle_time
                    tp2_hit = True

                if high >= tp1_price and not tp1_hit and position_remaining > 0:
                    tp1_pnl_pct = ((tp1_price - entry_price) / entry_price) * 100 * close_pct1
                    total_pnl_pct += tp1_pnl_pct
                    position_remaining -= close_pct1
                    exit_price = tp1_price
                    exit_type = 'TP1'
                    exit_time = candle_time
                    tp1_hit = True

            else:  # SHORT
                # Check SL first
                if high >= stop_loss and not sl_hit:
                    sl_pnl_pct = ((entry_price - stop_loss) / entry_price) * 100 * position_remaining
                    total_pnl_pct += sl_pnl_pct
                    position_remaining = 0
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = candle_time
                    sl_hit = True
                    break

                # Check TPs in order
                if low <= tp4_price and not tp4_hit and position_remaining > 0:
                    tp4_pnl_pct = ((entry_price - tp4_price) / entry_price) * 100 * close_pct4
                    total_pnl_pct += tp4_pnl_pct
                    position_remaining -= close_pct4
                    exit_price = tp4_price
                    exit_type = 'TP4'
                    exit_time = candle_time
                    tp4_hit = True

                if low <= tp3_price and not tp3_hit and position_remaining > 0:
                    tp3_pnl_pct = ((entry_price - tp3_price) / entry_price) * 100 * close_pct3
                    total_pnl_pct += tp3_pnl_pct
                    position_remaining -= close_pct3
                    exit_price = tp3_price
                    exit_type = 'TP3'
                    exit_time = candle_time
                    tp3_hit = True

                if low <= tp2_price and not tp2_hit and position_remaining > 0:
                    tp2_pnl_pct = ((entry_price - tp2_price) / entry_price) * 100 * close_pct2
                    total_pnl_pct += tp2_pnl_pct
                    position_remaining -= close_pct2
                    exit_price = tp2_price
                    exit_type = 'TP2'
                    exit_time = candle_time
                    tp2_hit = True

                if low <= tp1_price and not tp1_hit and position_remaining > 0:
                    tp1_pnl_pct = ((entry_price - tp1_price) / entry_price) * 100 * close_pct1
                    total_pnl_pct += tp1_pnl_pct
                    position_remaining -= close_pct1
                    exit_price = tp1_price
                    exit_type = 'TP1'
                    exit_time = candle_time
                    tp1_hit = True

        # Close remaining at timeout
        if position_remaining > 0:
            final_close = df_future['close'].iloc[-1]
            if direction == 1:
                eod_pnl_pct = ((final_close - entry_price) / entry_price) * 100 * position_remaining
            else:
                eod_pnl_pct = ((entry_price - final_close) / entry_price) * 100 * position_remaining

            total_pnl_pct += eod_pnl_pct
            exit_price = final_close
            exit_type = 'EOD'
            exit_time = df_future.index[-1]

        duration_hours = (exit_time - entry_time).total_seconds() / 3600

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'month': entry_time.strftime('%Y-%m'),
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': total_pnl_pct,
            'duration_hours': duration_hours,
            'tp1_hit': tp1_hit,
            'tp2_hit': tp2_hit,
            'tp3_hit': tp3_hit,
            'tp4_hit': tp4_hit,
            'sl_hit': sl_hit,
        })

    return pd.DataFrame(trades)


def analyze_results(trades_df, variant_name):
    """Analyze and display results"""

    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ: {variant_name}")
    print(f"{'='*80}")

    # Overall stats
    total_trades = len(trades_df)
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    losses = len(trades_df[trades_df['pnl_pct'] <= 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    total_pnl = trades_df['pnl_pct'].sum()
    avg_pnl = trades_df['pnl_pct'].mean()

    print(f"\n📊 Общая статистика:")
    print(f"   Всего сделок: {total_trades}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Total PnL: {total_pnl:+.2f}%")

    # TP hit rates
    tp1_count = trades_df['tp1_hit'].sum()
    tp2_count = trades_df['tp2_hit'].sum()
    tp3_count = trades_df['tp3_hit'].sum()
    tp4_count = trades_df['tp4_hit'].sum()
    sl_count = trades_df['sl_hit'].sum()

    print(f"\n🎯 Достижение уровней:")
    print(f"   TP1: {tp1_count} ({tp1_count/total_trades*100:.1f}%)")
    print(f"   TP2: {tp2_count} ({tp2_count/total_trades*100:.1f}%)")
    print(f"   TP3: {tp3_count} ({tp3_count/total_trades*100:.1f}%)")
    print(f"   TP4: {tp4_count} ({tp4_count/total_trades*100:.1f}%) 🎯 НОВЫЙ!")
    print(f"   SL:  {sl_count} ({sl_count/total_trades*100:.1f}%)")

    # Monthly breakdown
    print(f"\n📅 По месяцам:")
    for month in sorted(trades_df['month'].unique()):
        month_data = trades_df[trades_df['month'] == month]
        month_pnl = month_data['pnl_pct'].sum()
        month_trades = len(month_data)
        month_wins = len(month_data[month_data['pnl_pct'] > 0])
        month_wr = (month_wins / month_trades * 100) if month_trades > 0 else 0

        emoji = "✅" if month_pnl > 0 else "❌"
        print(f"   {emoji} {month}: {month_pnl:+8.2f}% ({month_trades} сделок, WR {month_wr:.1f}%)")

    return {
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'avg_pnl': avg_pnl,
        'total_trades': total_trades,
        'tp4_hit_rate': (tp4_count/total_trades*100) if total_trades > 0 else 0,
    }


def calculate_optimal_tp4(df, strategy):
    """Calculate optimal TP4 level based on price movements"""

    print("\n" + "="*80)
    print("РАСЧЕТ ОПТИМАЛЬНОГО TP4")
    print("="*80)

    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    movements = []

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        direction = signal['signal']
        entry_time = df_signals.index[i]

        search_end = entry_time + timedelta(hours=48)
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]

        if len(df_future) == 0:
            continue

        if direction == 1:  # LONG
            max_price = df_future['high'].max()
            movement = max_price - entry_price
        else:  # SHORT
            min_price = df_future['low'].min()
            movement = entry_price - min_price

        movements.append(movement)

    movements = pd.Series(movements)

    print(f"\n📊 Статистика движений цены за 48 часов:")
    print(f"   Среднее: {movements.mean():.1f} пунктов")
    print(f"   Медиана: {movements.median():.1f} пунктов")
    print(f"   50% достигают: {movements.quantile(0.50):.1f} пунктов")
    print(f"   75% достигают: {movements.quantile(0.75):.1f} пунктов")
    print(f"   90% достигают: {movements.quantile(0.90):.1f} пунктов")
    print(f"   95% достигают: {movements.quantile(0.95):.1f} пунктов")
    print(f"   98% достигают: {movements.quantile(0.98):.1f} пунктов")

    print(f"\n💡 Текущие уровни:")
    print(f"   TP1: 30п (50% квантиль)")
    print(f"   TP2: 50п (75% квантиль)")
    print(f"   TP3: 80п (90% квантиль)")

    q95 = movements.quantile(0.95)
    q98 = movements.quantile(0.98)

    print(f"\n🎯 Рекомендации для TP4:")
    print(f"   Консервативный: {q95:.0f}п (95% квантиль) - достигается в ~5% сделок")
    print(f"   Агрессивный: {q98:.0f}п (98% квантиль) - достигается в ~2% сделок")

    return int(q95), int(q98)


def compare_strategies(results_dict):
    """Compare all strategies"""

    print(f"\n{'='*80}")
    print("СРАВНЕНИЕ ВСЕХ ВАРИАНТОВ")
    print(f"{'='*80}")

    print(f"\n{'Вариант':<50}{'Total PnL':<15}{'Win Rate':<12}{'TP4 Hit':<12}")
    print("-" * 90)

    # Sort by total PnL
    sorted_results = sorted(results_dict.items(), key=lambda x: x[1]['total_pnl'], reverse=True)

    for i, (name, stats) in enumerate(sorted_results, 1):
        emoji = "🏆" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{emoji} {i}. {name:<46}{stats['total_pnl']:>+12.2f}%  "
              f"{stats['win_rate']:>9.1f}%  {stats.get('tp4_hit_rate', 0):>9.1f}%")


def main():
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ 4 УРОВНЕЙ TP")
    print("="*80)

    # Load data
    df = load_mt5_data()
    print(f"\n📊 Загружено {len(df)} свечей")
    print(f"   Период: {df.index[0]} до {df.index[-1]}")

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Calculate optimal TP4
    tp4_conservative, tp4_aggressive = calculate_optimal_tp4(df, strategy)

    results = {}

    # Test 1: Baseline (3 TP) - для сравнения
    print("\n" + "="*80)
    print("BASELINE: 3 TP (текущий подход)")
    print("="*80)
    trades_baseline = backtest_4tp(df, strategy,
                                   tp1=30, tp2=50, tp3=80, tp4=999999,  # TP4 недостижимый
                                   close_pct1=0.5, close_pct2=0.3, close_pct3=0.2, close_pct4=0.0,
                                   variant_name="Baseline (3 TP)")
    results['Baseline (3 TP)'] = analyze_results(trades_baseline, 'Baseline')

    # Test 2: 4 TP - Conservative (95% квантиль)
    # Распределение: 45% / 25% / 15% / 15%
    print("\n" + "="*80)
    print(f"ВАРИАНТ 1: 4 TP - Консервативный (TP4 = {tp4_conservative}п)")
    print("="*80)
    trades_1 = backtest_4tp(df, strategy,
                           tp1=30, tp2=50, tp3=80, tp4=tp4_conservative,
                           close_pct1=0.45, close_pct2=0.25, close_pct3=0.15, close_pct4=0.15,
                           variant_name=f"4 TP Conservative (TP4={tp4_conservative}п, 15%)")
    results[f'4 TP Conservative (TP4={tp4_conservative}п, 15%)'] = analyze_results(trades_1, 'Вариант 1')

    # Test 3: 4 TP - Conservative with 20%
    # Распределение: 40% / 25% / 15% / 20%
    print("\n" + "="*80)
    print(f"ВАРИАНТ 2: 4 TP - Консервативный (TP4 = {tp4_conservative}п, 20%)")
    print("="*80)
    trades_2 = backtest_4tp(df, strategy,
                           tp1=30, tp2=50, tp3=80, tp4=tp4_conservative,
                           close_pct1=0.40, close_pct2=0.25, close_pct3=0.15, close_pct4=0.20,
                           variant_name=f"4 TP Conservative (TP4={tp4_conservative}п, 20%)")
    results[f'4 TP Conservative (TP4={tp4_conservative}п, 20%)'] = analyze_results(trades_2, 'Вариант 2')

    # Test 4: 4 TP - Aggressive (98% квантиль)
    # Распределение: 45% / 25% / 15% / 15%
    print("\n" + "="*80)
    print(f"ВАРИАНТ 3: 4 TP - Агрессивный (TP4 = {tp4_aggressive}п)")
    print("="*80)
    trades_3 = backtest_4tp(df, strategy,
                           tp1=30, tp2=50, tp3=80, tp4=tp4_aggressive,
                           close_pct1=0.45, close_pct2=0.25, close_pct3=0.15, close_pct4=0.15,
                           variant_name=f"4 TP Aggressive (TP4={tp4_aggressive}п, 15%)")
    results[f'4 TP Aggressive (TP4={tp4_aggressive}п, 15%)'] = analyze_results(trades_3, 'Вариант 3')

    # Test 5: 4 TP - Balanced
    # Распределение: 40% / 30% / 20% / 10%
    print("\n" + "="*80)
    print(f"ВАРИАНТ 4: 4 TP - Сбалансированный (TP4 = {tp4_conservative}п, 10%)")
    print("="*80)
    trades_4 = backtest_4tp(df, strategy,
                           tp1=30, tp2=50, tp3=80, tp4=tp4_conservative,
                           close_pct1=0.40, close_pct2=0.30, close_pct3=0.20, close_pct4=0.10,
                           variant_name=f"4 TP Balanced (TP4={tp4_conservative}п, 10%)")
    results[f'4 TP Balanced (TP4={tp4_conservative}п, 10%)'] = analyze_results(trades_4, 'Вариант 4')

    # Test 6: Custom - фиксированный TP4 = 120п
    print("\n" + "="*80)
    print("ВАРИАНТ 5: 4 TP - Фиксированный TP4=120п")
    print("="*80)
    trades_5 = backtest_4tp(df, strategy,
                           tp1=30, tp2=50, tp3=80, tp4=120,
                           close_pct1=0.40, close_pct2=0.30, close_pct3=0.15, close_pct4=0.15,
                           variant_name="4 TP Fixed (TP4=120п, 15%)")
    results['4 TP Fixed (TP4=120п, 15%)'] = analyze_results(trades_5, 'Вариант 5')

    # Compare all
    compare_strategies(results)

    print("\n" + "="*80)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("="*80)

    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("   Выберите вариант с лучшим Total PnL")
    print("   Учитывайте:")
    print("   • TP4 должен достигаться достаточно часто (>3-5%)")
    print("   • Не забирать слишком много из ранних TP")
    print("   • Баланс между частой фиксацией и дальними целями")


if __name__ == "__main__":
    main()
