"""
Backtest with partial close at multiple TP levels
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


def analyze_optimal_tp_levels(df, strategy):
    """Analyze historical price movements to determine optimal TP levels"""

    print("=" * 80)
    print("АНАЛИЗ ОПТИМАЛЬНЫХ УРОВНЕЙ ТЕЙК-ПРОФИТА")
    print("=" * 80)

    # Run strategy to get signals
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    print(f"\n📊 Анализирую {len(df_signals)} сигналов...")

    # Analyze maximum favorable excursion (MFE) for each signal
    movements = []

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        direction = signal['signal']
        entry_time = df_signals.index[i]

        # Look 48 hours ahead
        search_end = entry_time + timedelta(hours=48)
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]

        if len(df_future) == 0:
            continue

        # Find maximum favorable movement
        if direction == 1:  # LONG
            max_profit_points = (df_future['high'].max() - entry_price)
        else:  # SHORT
            max_profit_points = (entry_price - df_future['low'].min())

        movements.append(max_profit_points)

    movements = pd.Series(movements)

    # Calculate statistics
    print(f"\n📈 Статистика движений цены в нашу сторону (48 часов):")
    print(f"   Среднее движение: {movements.mean():.2f} пунктов")
    print(f"   Медиана: {movements.median():.2f} пунктов")
    print(f"   25-й перцентиль: {movements.quantile(0.25):.2f} пунктов")
    print(f"   50-й перцентиль: {movements.quantile(0.50):.2f} пунктов")
    print(f"   75-й перцентиль: {movements.quantile(0.75):.2f} пунктов")
    print(f"   90-й перцентиль: {movements.quantile(0.90):.2f} пунктов")
    print(f"   Максимум: {movements.max():.2f} пунктов")

    # Recommend TP levels
    tp1 = movements.quantile(0.50)  # 50% сделок достигают
    tp2 = movements.quantile(0.75)  # 75% сделок достигают
    tp3 = movements.quantile(0.90)  # 90% сделок достигают

    print(f"\n🎯 Рекомендуемые уровни тейк-профита:")
    print(f"   TP1: {tp1:.0f} пунктов (достигают 50% сделок)")
    print(f"   TP2: {tp2:.0f} пунктов (достигают 25% сделок)")
    print(f"   TP3: {tp3:.0f} пунктов (достигают 10% сделок)")

    return tp1, tp2, tp3


def backtest_with_partial_close(df, strategy, tp1, tp2, tp3, close_percents=(0.5, 0.3, 0.2)):
    """
    Backtest with partial close at multiple TP levels

    Args:
        tp1, tp2, tp3: TP levels in points
        close_percents: Percentage of position to close at each TP (must sum to 1.0)
    """

    print("\n" + "=" * 80)
    print("БЭКТЕСТ С ЧАСТИЧНЫМ ЗАКРЫТИЕМ")
    print("=" * 80)

    print(f"\n📊 Параметры:")
    print(f"   TP1: {tp1:.0f} пунктов → закрыть {close_percents[0]*100:.0f}% позиции")
    print(f"   TP2: {tp2:.0f} пунктов → закрыть {close_percents[1]*100:.0f}% позиции")
    print(f"   TP3: {tp3:.0f} пунктов → закрыть {close_percents[2]*100:.0f}% позиции")
    print(f"   SL: по сигналу стратегии")
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

        # Calculate TP levels
        if direction == 1:  # LONG
            tp1_price = entry_price + tp1
            tp2_price = entry_price + tp2
            tp3_price = entry_price + tp3
        else:  # SHORT
            tp1_price = entry_price - tp1
            tp2_price = entry_price - tp2
            tp3_price = entry_price - tp3

        # Track partial closes
        position_remaining = 1.0
        total_pnl_points = 0
        total_pnl_pct = 0

        tp1_hit = False
        tp2_hit = False
        tp3_hit = False
        sl_hit = False

        exit_time = None
        exit_type = 'EOD'

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

            if position_remaining <= 0:
                break

            # Check SL first (most important)
            if direction == 1:  # LONG
                if low <= stop_loss:
                    # Full SL hit - close remaining position
                    pnl_points = (stop_loss - entry_price) * position_remaining
                    total_pnl_points += pnl_points
                    sl_hit = True
                    exit_time = candle_time
                    exit_type = 'SL' if position_remaining == 1.0 else 'SL_PARTIAL'
                    position_remaining = 0
                    break
            else:  # SHORT
                if high >= stop_loss:
                    pnl_points = (entry_price - stop_loss) * position_remaining
                    total_pnl_points += pnl_points
                    sl_hit = True
                    exit_time = candle_time
                    exit_type = 'SL' if position_remaining == 1.0 else 'SL_PARTIAL'
                    position_remaining = 0
                    break

            # Check TP levels (in order)
            if direction == 1:  # LONG
                if not tp1_hit and high >= tp1_price:
                    # Close first part
                    pnl_points = tp1 * close_percents[0]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[0]
                    tp1_hit = True
                    exit_time = candle_time

                if tp1_hit and not tp2_hit and high >= tp2_price:
                    # Close second part
                    pnl_points = tp2 * close_percents[1]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[1]
                    tp2_hit = True
                    exit_time = candle_time

                if tp2_hit and not tp3_hit and high >= tp3_price:
                    # Close third part
                    pnl_points = tp3 * close_percents[2]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[2]
                    tp3_hit = True
                    exit_time = candle_time

            else:  # SHORT
                if not tp1_hit and low <= tp1_price:
                    pnl_points = tp1 * close_percents[0]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[0]
                    tp1_hit = True
                    exit_time = candle_time

                if tp1_hit and not tp2_hit and low <= tp2_price:
                    pnl_points = tp2 * close_percents[1]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[1]
                    tp2_hit = True
                    exit_time = candle_time

                if tp2_hit and not tp3_hit and low <= tp3_price:
                    pnl_points = tp3 * close_percents[2]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[2]
                    tp3_hit = True
                    exit_time = candle_time

        # Close any remaining position at end (timeout)
        if position_remaining > 0:
            final_price = df_future['close'].iloc[-1]
            if direction == 1:
                pnl_points = (final_price - entry_price) * position_remaining
            else:
                pnl_points = (entry_price - final_price) * position_remaining

            total_pnl_points += pnl_points

            if exit_time is None:
                exit_time = df_future.index[-1]

            # Determine exit type
            if tp3_hit:
                exit_type = 'TP3_FULL'
            elif tp2_hit:
                exit_type = 'TP2_PARTIAL'
            elif tp1_hit:
                exit_type = 'TP1_PARTIAL'
            else:
                exit_type = 'EOD'
        else:
            # All position closed
            if tp3_hit:
                exit_type = 'TP3_FULL'
            elif tp2_hit:
                exit_type = 'TP2_FULL'
            elif tp1_hit:
                exit_type = 'TP1_FULL'

        # Calculate PnL percentage
        total_pnl_pct = (total_pnl_points / entry_price) * 100

        duration_hours = (exit_time - entry_time).total_seconds() / 3600

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'month': entry_time.strftime('%Y-%m'),
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'exit_type': exit_type,
            'pnl_pct': total_pnl_pct,
            'pnl_points': total_pnl_points,
            'duration_hours': duration_hours,
            'tp1_hit': tp1_hit,
            'tp2_hit': tp2_hit,
            'tp3_hit': tp3_hit,
            'sl_hit': sl_hit,
        })

    return pd.DataFrame(trades)


def analyze_monthly_results(trades_df):
    """Analyze results by month"""

    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТЫ ПО МЕСЯЦАМ - ЧАСТИЧНОЕ ЗАКРЫТИЕ")
    print("=" * 80)

    monthly_stats = []

    for month in sorted(trades_df['month'].unique()):
        month_trades = trades_df[trades_df['month'] == month]

        wins = len(month_trades[month_trades['pnl_pct'] > 0])
        losses = len(month_trades[month_trades['pnl_pct'] <= 0])
        total_trades = len(month_trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = month_trades['pnl_pct'].sum()
        avg_pnl = month_trades['pnl_pct'].mean()

        # TP hit statistics
        tp1_hits = month_trades['tp1_hit'].sum()
        tp2_hits = month_trades['tp2_hit'].sum()
        tp3_hits = month_trades['tp3_hit'].sum()
        sl_hits = month_trades['sl_hit'].sum()

        monthly_stats.append({
            'month': month,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'tp1_hits': tp1_hits,
            'tp2_hits': tp2_hits,
            'tp3_hits': tp3_hits,
            'sl_hits': sl_hits,
        })

    monthly_df = pd.DataFrame(monthly_stats)

    # Display table
    print(f"\n{'Месяц':<12}{'Сделок':<8}{'W/L':<10}{'WR%':<8}{'PnL%':<12}{'Avg%':<10}{'TP1':<6}{'TP2':<6}{'TP3':<6}{'SL':<6}")
    print("-" * 90)

    for _, row in monthly_df.iterrows():
        emoji = "✅" if row['total_pnl'] > 0 else "❌"
        print(f"{emoji} {row['month']:<10}{row['total_trades']:<8}"
              f"{row['wins']}/{row['losses']:<7}"
              f"{row['win_rate']:>6.1f}%  "
              f"{row['total_pnl']:>+9.2f}%  "
              f"{row['avg_pnl']:>+7.2f}%  "
              f"{row['tp1_hits']:<6}{row['tp2_hits']:<6}{row['tp3_hits']:<6}{row['sl_hits']:<6}")

    # Summary
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 80)

    profitable_months = len(monthly_df[monthly_df['total_pnl'] > 0])
    total_months = len(monthly_df)

    print(f"\n📊 Общие показатели:")
    print(f"   Всего месяцев: {total_months}")
    print(f"   Прибыльных: {profitable_months} ({profitable_months/total_months*100:.1f}%)")
    print(f"   Общий PnL: {monthly_df['total_pnl'].sum():+.2f}%")
    print(f"   Средний месячный PnL: {monthly_df['total_pnl'].mean():+.2f}%")
    print(f"   Лучший месяц: {monthly_df['total_pnl'].max():+.2f}%")
    print(f"   Худший месяц: {monthly_df['total_pnl'].min():+.2f}%")

    print(f"\n🎯 Эффективность тейк-профитов:")
    print(f"   TP1 достигнут: {monthly_df['tp1_hits'].sum()} раз ({monthly_df['tp1_hits'].sum()/trades_df.shape[0]*100:.1f}%)")
    print(f"   TP2 достигнут: {monthly_df['tp2_hits'].sum()} раз ({monthly_df['tp2_hits'].sum()/trades_df.shape[0]*100:.1f}%)")
    print(f"   TP3 достигнут: {monthly_df['tp3_hits'].sum()} раз ({monthly_df['tp3_hits'].sum()/trades_df.shape[0]*100:.1f}%)")
    print(f"   SL сработал: {monthly_df['sl_hits'].sum()} раз ({monthly_df['sl_hits'].sum()/trades_df.shape[0]*100:.1f}%)")

    print(f"\n📈 Средние показатели:")
    print(f"   Сделок в месяц: {monthly_df['total_trades'].mean():.1f}")
    print(f"   Win Rate: {monthly_df['win_rate'].mean():.1f}%")

    return monthly_df


def main():
    print("\n" + "=" * 80)
    print("БЭКТЕСТ С ЧАСТИЧНЫМ ЗАКРЫТИЕМ НА НЕСКОЛЬКИХ УРОВНЯХ TP")
    print("=" * 80)

    # Load data
    df = load_mt5_data()
    print(f"\n📊 Загружено {len(df)} свечей")
    print(f"   Период: {df.index[0]} до {df.index[-1]}")

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Analyze optimal TP levels
    tp1, tp2, tp3 = analyze_optimal_tp_levels(df, strategy)

    # Round to nice numbers
    tp1 = round(tp1 / 10) * 10  # Round to nearest 10
    tp2 = round(tp2 / 10) * 10
    tp3 = round(tp3 / 10) * 10

    print(f"\n✅ Использую уровни:")
    print(f"   TP1: {tp1:.0f} пунктов")
    print(f"   TP2: {tp2:.0f} пунктов")
    print(f"   TP3: {tp3:.0f} пунктов")

    # Run backtest with partial close
    # Close 50% at TP1, 30% at TP2, 20% at TP3
    trades_df = backtest_with_partial_close(df, strategy, tp1, tp2, tp3,
                                            close_percents=(0.5, 0.3, 0.2))

    print(f"\n✅ Выполнено {len(trades_df)} сделок")

    # Analyze by month
    monthly_df = analyze_monthly_results(trades_df)

    print("\n" + "=" * 80)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("=" * 80)

    return trades_df, monthly_df


if __name__ == "__main__":
    main()
