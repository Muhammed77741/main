"""
Backtest with trailing stop variants
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


def backtest_trailing_stop(df, strategy, trailing_type='fixed', trailing_distance=30,
                           breakeven_points=None, tp_points=None):
    """
    Backtest with trailing stop

    Args:
        trailing_type: 'fixed', 'percent', 'breakeven_then_trail'
        trailing_distance: Distance for trailing (points or percent)
        breakeven_points: Move SL to breakeven after this profit (points)
        tp_points: Optional TP level (if None, let it run with trailing)
    """

    print("\n" + "=" * 80)
    print(f"БЭКТЕСТ С ТРЕЙЛИНГ СТОПОМ: {trailing_type.upper()}")
    print("=" * 80)

    print(f"\n📊 Параметры:")
    print(f"   Тип: {trailing_type}")

    if trailing_type == 'fixed':
        print(f"   Трейлинг: {trailing_distance} пунктов от максимума/минимума")
    elif trailing_type == 'percent':
        print(f"   Трейлинг: {trailing_distance}% от максимума/минимума")
    elif trailing_type == 'breakeven_then_trail':
        print(f"   Безубыток после: {breakeven_points} пунктов прибыли")
        print(f"   Затем трейлинг: {trailing_distance} пунктов")

    if tp_points:
        print(f"   Take Profit: {tp_points} пунктов (опционально)")
    else:
        print(f"   Take Profit: нет (только трейлинг стоп)")

    print(f"   Таймаут: 48 часов")

    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    print(f"\n🔍 Найдено сигналов: {len(df_signals)}")

    trades = []

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        initial_stop_loss = signal['stop_loss']
        direction = signal['signal']
        entry_time = df_signals.index[i]

        # Current trailing stop
        current_stop_loss = initial_stop_loss

        # Track best price
        best_price = entry_price

        # Track if we moved to breakeven
        moved_to_breakeven = False

        # TP price if set
        take_profit = None
        if tp_points:
            if direction == 1:
                take_profit = entry_price + tp_points
            else:
                take_profit = entry_price - tp_points

        exit_price = None
        exit_type = 'EOD'
        exit_time = None
        max_profit_points = 0

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
            close = df_future['close'].iloc[j]

            if direction == 1:  # LONG
                # Update best price
                if high > best_price:
                    best_price = high
                    max_profit_points = best_price - entry_price

                # Update trailing stop
                if trailing_type == 'fixed':
                    # Keep stop at trailing_distance below best price
                    new_stop = best_price - trailing_distance
                    if new_stop > current_stop_loss:
                        current_stop_loss = new_stop

                elif trailing_type == 'percent':
                    # Keep stop at trailing_distance% below best price
                    new_stop = best_price * (1 - trailing_distance / 100)
                    if new_stop > current_stop_loss:
                        current_stop_loss = new_stop

                elif trailing_type == 'breakeven_then_trail':
                    # Move to breakeven first
                    if not moved_to_breakeven and (best_price - entry_price) >= breakeven_points:
                        current_stop_loss = entry_price
                        moved_to_breakeven = True

                    # Then trail
                    if moved_to_breakeven:
                        new_stop = best_price - trailing_distance
                        if new_stop > current_stop_loss:
                            current_stop_loss = new_stop

                # Check TP first
                if take_profit and high >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = candle_time
                    break

                # Check trailing stop
                if low <= current_stop_loss:
                    exit_price = current_stop_loss
                    if current_stop_loss >= entry_price:
                        exit_type = 'TS_BE' if current_stop_loss == entry_price else 'TS_PROFIT'
                    else:
                        exit_type = 'TS_LOSS'
                    exit_time = candle_time
                    break

            else:  # SHORT
                # Update best price (lowest for short)
                if low < best_price:
                    best_price = low
                    max_profit_points = entry_price - best_price

                # Update trailing stop
                if trailing_type == 'fixed':
                    new_stop = best_price + trailing_distance
                    if new_stop < current_stop_loss:
                        current_stop_loss = new_stop

                elif trailing_type == 'percent':
                    new_stop = best_price * (1 + trailing_distance / 100)
                    if new_stop < current_stop_loss:
                        current_stop_loss = new_stop

                elif trailing_type == 'breakeven_then_trail':
                    if not moved_to_breakeven and (entry_price - best_price) >= breakeven_points:
                        current_stop_loss = entry_price
                        moved_to_breakeven = True

                    if moved_to_breakeven:
                        new_stop = best_price + trailing_distance
                        if new_stop < current_stop_loss:
                            current_stop_loss = new_stop

                # Check TP first
                if take_profit and low <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = candle_time
                    break

                # Check trailing stop
                if high >= current_stop_loss:
                    exit_price = current_stop_loss
                    if current_stop_loss <= entry_price:
                        exit_type = 'TS_BE' if current_stop_loss == entry_price else 'TS_PROFIT'
                    else:
                        exit_type = 'TS_LOSS'
                    exit_time = candle_time
                    break

        # Close at timeout if still open
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'
            exit_time = df_future.index[-1]

        # Calculate PnL
        if direction == 1:
            pnl_points = exit_price - entry_price
        else:
            pnl_points = entry_price - exit_price

        pnl_pct = (pnl_points / entry_price) * 100
        duration_hours = (exit_time - entry_time).total_seconds() / 3600

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'month': entry_time.strftime('%Y-%m'),
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'initial_sl': initial_stop_loss,
            'final_sl': current_stop_loss,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'max_profit_points': max_profit_points,
            'duration_hours': duration_hours,
            'moved_to_breakeven': moved_to_breakeven,
        })

    return pd.DataFrame(trades)


def analyze_results(trades_df, strategy_name):
    """Analyze and display results"""

    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ: {strategy_name}")
    print(f"{'='*80}")

    # Overall stats
    total_trades = len(trades_df)
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    losses = len(trades_df[trades_df['pnl_pct'] <= 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    total_pnl = trades_df['pnl_pct'].sum()
    avg_pnl = trades_df['pnl_pct'].mean()

    wins_df = trades_df[trades_df['pnl_pct'] > 0]
    losses_df = trades_df[trades_df['pnl_pct'] <= 0]

    avg_win = wins_df['pnl_pct'].mean() if len(wins_df) > 0 else 0
    avg_loss = losses_df['pnl_pct'].mean() if len(losses_df) > 0 else 0

    print(f"\n📊 Общая статистика:")
    print(f"   Всего сделок: {total_trades}")
    print(f"   Прибыльных: {wins} ({win_rate:.1f}%)")
    print(f"   Убыточных: {losses}")
    print(f"   Total PnL: {total_pnl:+.2f}%")
    print(f"   Средний PnL: {avg_pnl:+.2f}%")
    print(f"   Средняя прибыль: {avg_win:+.2f}%")
    print(f"   Средний убыток: {avg_loss:+.2f}%")

    # Exit type breakdown
    print(f"\n🎯 Типы выходов:")
    exit_counts = trades_df['exit_type'].value_counts()
    for exit_type, count in exit_counts.items():
        pct = (count / total_trades) * 100
        avg_pnl_for_type = trades_df[trades_df['exit_type'] == exit_type]['pnl_pct'].mean()
        print(f"   {exit_type}: {count} ({pct:.1f}%) | Avg PnL: {avg_pnl_for_type:+.2f}%")

    # Breakeven stats
    if 'moved_to_breakeven' in trades_df.columns:
        be_count = trades_df['moved_to_breakeven'].sum()
        print(f"\n🔒 Перемещено в безубыток: {be_count} сделок ({be_count/total_trades*100:.1f}%)")

    # Monthly breakdown
    print(f"\n📅 По месяцам:")
    monthly = trades_df.groupby('month').agg({
        'pnl_pct': ['sum', 'mean', 'count']
    }).round(2)

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
    }


def compare_strategies(results_dict):
    """Compare all strategies"""

    print(f"\n{'='*80}")
    print("СРАВНЕНИЕ ВСЕХ СТРАТЕГИЙ")
    print(f"{'='*80}")

    print(f"\n{'Стратегия':<50}{'Total PnL':<15}{'Win Rate':<12}{'Avg PnL':<12}{'Сделок':<10}")
    print("-" * 100)

    # Sort by total PnL
    sorted_results = sorted(results_dict.items(), key=lambda x: x[1]['total_pnl'], reverse=True)

    for i, (name, stats) in enumerate(sorted_results, 1):
        emoji = "🏆" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{emoji} {i}. {name:<46}{stats['total_pnl']:>+12.2f}%  "
              f"{stats['win_rate']:>9.1f}%  {stats['avg_pnl']:>+9.2f}%  {stats['total_trades']:>7}")


def main():
    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ ТРЕЙЛИНГ СТОПА")
    print("=" * 80)

    # Load data
    df = load_mt5_data()
    print(f"\n📊 Загружено {len(df)} свечей")
    print(f"   Период: {df.index[0]} до {df.index[-1]}")

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    results = {}

    # Test 1: Fixed trailing stop (30 points)
    print("\n" + "="*80)
    print("TEST 1: ФИКСИРОВАННЫЙ ТРЕЙЛИНГ 30 ПУНКТОВ")
    print("="*80)
    trades_1 = backtest_trailing_stop(df, strategy,
                                      trailing_type='fixed',
                                      trailing_distance=30,
                                      tp_points=None)
    results['Фиксированный трейлинг 30п'] = analyze_results(trades_1, 'Фиксированный 30п')

    # Test 2: Fixed trailing stop (20 points) - tighter
    print("\n" + "="*80)
    print("TEST 2: ФИКСИРОВАННЫЙ ТРЕЙЛИНГ 20 ПУНКТОВ (более агрессивный)")
    print("="*80)
    trades_2 = backtest_trailing_stop(df, strategy,
                                      trailing_type='fixed',
                                      trailing_distance=20,
                                      tp_points=None)
    results['Фиксированный трейлинг 20п'] = analyze_results(trades_2, 'Фиксированный 20п')

    # Test 3: Breakeven then trail
    print("\n" + "="*80)
    print("TEST 3: БЕЗУБЫТОК ПОСЛЕ 20П, ЗАТЕМ ТРЕЙЛИНГ 25П")
    print("="*80)
    trades_3 = backtest_trailing_stop(df, strategy,
                                      trailing_type='breakeven_then_trail',
                                      trailing_distance=25,
                                      breakeven_points=20,
                                      tp_points=None)
    results['Безубыток+Трейлинг'] = analyze_results(trades_3, 'Безубыток+Трейлинг')

    # Test 4: Breakeven + trail + TP (hybrid)
    print("\n" + "="*80)
    print("TEST 4: БЕЗУБЫТОК + ТРЕЙЛИНГ + TP80 (гибрид)")
    print("="*80)
    trades_4 = backtest_trailing_stop(df, strategy,
                                      trailing_type='breakeven_then_trail',
                                      trailing_distance=25,
                                      breakeven_points=20,
                                      tp_points=80)
    results['Гибрид (BE+TS+TP80)'] = analyze_results(trades_4, 'Гибрид')

    # Test 5: Percent trailing (1%)
    print("\n" + "="*80)
    print("TEST 5: ПРОЦЕНТНЫЙ ТРЕЙЛИНГ 1%")
    print("="*80)
    trades_5 = backtest_trailing_stop(df, strategy,
                                      trailing_type='percent',
                                      trailing_distance=1.0,
                                      tp_points=None)
    results['Процентный трейлинг 1%'] = analyze_results(trades_5, 'Процентный 1%')

    # Compare all
    compare_strategies(results)

    print("\n" + "=" * 80)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("=" * 80)

    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("   Выберите стратегию с лучшим соотношением:")
    print("   • Total PnL (общая прибыль)")
    print("   • Win Rate (процент выигрышей)")
    print("   • Стабильность по месяцам")


if __name__ == "__main__":
    main()
