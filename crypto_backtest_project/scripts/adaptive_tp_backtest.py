"""
Backtest with adaptive TP levels based on SL
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

    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def backtest_adaptive_tp(df, strategy, tp1_ratio=0.8, tp2_ratio=1.2, tp3_ratio=1.8,
                        min_tp1=30, min_tp2=50, min_tp3=80,
                        close_percents=(0.5, 0.3, 0.2),
                        max_sl=None):
    """
    Backtest with adaptive TP levels based on each trade's SL

    Args:
        tp1_ratio: TP1 = max(min_tp1, SL × tp1_ratio)
        tp2_ratio: TP2 = max(min_tp2, SL × tp2_ratio)
        tp3_ratio: TP3 = max(min_tp3, SL × tp3_ratio)
        min_tp1/2/3: Minimum TP levels
        max_sl: Optional maximum SL limit
    """

    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    trades = []

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        direction = signal['signal']
        entry_time = df_signals.index[i]

        # Calculate SL distance
        sl_distance = abs(entry_price - stop_loss)

        # Apply max SL if set
        if max_sl and sl_distance > max_sl:
            if direction == 1:  # LONG
                stop_loss = entry_price - max_sl
            else:  # SHORT
                stop_loss = entry_price + max_sl
            sl_distance = max_sl

        # Calculate adaptive TP levels
        tp1_points = max(min_tp1, sl_distance * tp1_ratio)
        tp2_points = max(min_tp2, sl_distance * tp2_ratio)
        tp3_points = max(min_tp3, sl_distance * tp3_ratio)

        if direction == 1:  # LONG
            tp1_price = entry_price + tp1_points
            tp2_price = entry_price + tp2_points
            tp3_price = entry_price + tp3_points
        else:  # SHORT
            tp1_price = entry_price - tp1_points
            tp2_price = entry_price - tp2_points
            tp3_price = entry_price - tp3_points

        # Track partial closes
        position_remaining = 1.0
        total_pnl_points = 0

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

            if position_remaining <= 0:
                break

            # Check SL first
            if direction == 1:  # LONG
                if low <= stop_loss:
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

            # Check TP levels
            if direction == 1:  # LONG
                if not tp1_hit and high >= tp1_price:
                    pnl_points = tp1_points * close_percents[0]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[0]
                    tp1_hit = True
                    exit_time = candle_time

                if tp1_hit and not tp2_hit and high >= tp2_price:
                    pnl_points = tp2_points * close_percents[1]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[1]
                    tp2_hit = True
                    exit_time = candle_time

                if tp2_hit and not tp3_hit and high >= tp3_price:
                    pnl_points = tp3_points * close_percents[2]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[2]
                    tp3_hit = True
                    exit_time = candle_time

            else:  # SHORT
                if not tp1_hit and low <= tp1_price:
                    pnl_points = tp1_points * close_percents[0]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[0]
                    tp1_hit = True
                    exit_time = candle_time

                if tp1_hit and not tp2_hit and low <= tp2_price:
                    pnl_points = tp2_points * close_percents[1]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[1]
                    tp2_hit = True
                    exit_time = candle_time

                if tp2_hit and not tp3_hit and low <= tp3_price:
                    pnl_points = tp3_points * close_percents[2]
                    total_pnl_points += pnl_points
                    position_remaining -= close_percents[2]
                    tp3_hit = True
                    exit_time = candle_time

        # Close remaining position at timeout
        if position_remaining > 0:
            final_price = df_future['close'].iloc[-1]
            if direction == 1:
                pnl_points = (final_price - entry_price) * position_remaining
            else:
                pnl_points = (entry_price - final_price) * position_remaining

            total_pnl_points += pnl_points

            if exit_time is None:
                exit_time = df_future.index[-1]

            if tp3_hit:
                exit_type = 'TP3_FULL'
            elif tp2_hit:
                exit_type = 'TP2_PARTIAL'
            elif tp1_hit:
                exit_type = 'TP1_PARTIAL'
            else:
                exit_type = 'EOD'
        else:
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
            'sl_distance': sl_distance,
            'tp1_points': tp1_points,
            'tp2_points': tp2_points,
            'tp3_points': tp3_points,
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


def analyze_results(trades_df, strategy_name):
    """Analyze and display results"""

    print(f"\n{'='*90}")
    print(f"РЕЗУЛЬТАТЫ: {strategy_name}")
    print(f"{'='*90}")

    total_trades = len(trades_df)
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    total_pnl = trades_df['pnl_pct'].sum()

    tp1_hits = trades_df['tp1_hit'].sum()
    tp2_hits = trades_df['tp2_hit'].sum()
    tp3_hits = trades_df['tp3_hit'].sum()
    sl_hits = trades_df['sl_hit'].sum()

    # Average TP levels
    avg_tp1 = trades_df['tp1_points'].mean()
    avg_tp2 = trades_df['tp2_points'].mean()
    avg_tp3 = trades_df['tp3_points'].mean()
    avg_sl = trades_df['sl_distance'].mean()

    print(f"\n📊 Общая статистика:")
    print(f"   Всего сделок: {total_trades}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Total PnL: {total_pnl:+.2f}%")

    print(f"\n🎯 Средние уровни:")
    print(f"   SL: {avg_sl:.1f} пунктов")
    print(f"   TP1: {avg_tp1:.1f} пунктов (R:R 1:{avg_tp1/avg_sl:.2f})")
    print(f"   TP2: {avg_tp2:.1f} пунктов (R:R 1:{avg_tp2/avg_sl:.2f})")
    print(f"   TP3: {avg_tp3:.1f} пунктов (R:R 1:{avg_tp3/avg_sl:.2f})")

    print(f"\n🎯 Достижение TP:")
    print(f"   TP1: {tp1_hits} ({tp1_hits/total_trades*100:.1f}%)")
    print(f"   TP2: {tp2_hits} ({tp2_hits/total_trades*100:.1f}%)")
    print(f"   TP3: {tp3_hits} ({tp3_hits/total_trades*100:.1f}%)")
    print(f"   SL: {sl_hits} ({sl_hits/total_trades*100:.1f}%)")

    # Monthly stats
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
        'total_trades': total_trades,
        'avg_sl': avg_sl,
        'avg_tp1': avg_tp1,
        'avg_tp2': avg_tp2,
        'avg_tp3': avg_tp3,
    }


def compare_strategies(results_dict):
    """Compare all strategies"""

    print(f"\n{'='*90}")
    print("ФИНАЛЬНОЕ СРАВНЕНИЕ")
    print(f"{'='*90}")

    print(f"\n{'Стратегия':<40}{'Total PnL':<15}{'Win Rate':<12}{'Avg SL':<10}{'Avg TP1':<10}{'R:R TP1':<10}")
    print("-" * 100)

    sorted_results = sorted(results_dict.items(), key=lambda x: x[1]['total_pnl'], reverse=True)

    for i, (name, stats) in enumerate(sorted_results, 1):
        emoji = "🏆" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        rr = stats['avg_tp1'] / stats['avg_sl'] if stats['avg_sl'] > 0 else 0
        print(f"{emoji} {i}. {name:<37}{stats['total_pnl']:>+12.2f}%  "
              f"{stats['win_rate']:>9.1f}%  {stats['avg_sl']:>7.1f}p  "
              f"{stats['avg_tp1']:>7.1f}p  1:{rr:.2f}")


def main():
    print("\n" + "=" * 90)
    print("ТЕСТИРОВАНИЕ АДАПТИВНЫХ TP")
    print("=" * 90)

    # Load data
    df = load_mt5_data()
    print(f"\n📊 Загружено {len(df)} свечей")
    print(f"   Период: {df.index[0]} до {df.index[-1]}")

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    results = {}

    # Test 1: Fixed TP (baseline)
    print("\n" + "="*90)
    print("TEST 1: ФИКСИРОВАННЫЕ TP (текущий подход)")
    print("="*90)
    print("   TP1: 30п, TP2: 50п, TP3: 80п")

    trades_fixed = backtest_adaptive_tp(df, strategy,
                                       tp1_ratio=0, tp2_ratio=0, tp3_ratio=0,
                                       min_tp1=30, min_tp2=50, min_tp3=80)
    results['Фиксированные (30/50/80)'] = analyze_results(trades_fixed, 'Фиксированные')

    # Test 2: Adaptive TP (conservative)
    print("\n" + "="*90)
    print("TEST 2: АДАПТИВНЫЕ TP (консервативные)")
    print("="*90)
    print("   TP1 = max(30, SL×0.8), TP2 = max(50, SL×1.2), TP3 = max(80, SL×1.8)")

    trades_adaptive = backtest_adaptive_tp(df, strategy,
                                          tp1_ratio=0.8, tp2_ratio=1.2, tp3_ratio=1.8,
                                          min_tp1=30, min_tp2=50, min_tp3=80)
    results['Адаптивные (0.8/1.2/1.8)'] = analyze_results(trades_adaptive, 'Адаптивные')

    # Test 3: Adaptive TP with max SL
    print("\n" + "="*90)
    print("TEST 3: АДАПТИВНЫЕ TP + МАКС SL 80П")
    print("="*90)
    print("   Max SL: 80п")
    print("   TP1 = max(30, SL×0.8), TP2 = max(50, SL×1.2), TP3 = max(80, SL×1.8)")

    trades_adaptive_maxsl = backtest_adaptive_tp(df, strategy,
                                                tp1_ratio=0.8, tp2_ratio=1.2, tp3_ratio=1.8,
                                                min_tp1=30, min_tp2=50, min_tp3=80,
                                                max_sl=80)
    results['Адаптивные + Max SL 80'] = analyze_results(trades_adaptive_maxsl, 'Адаптивные + MaxSL')

    # Test 4: More aggressive adaptive
    print("\n" + "="*90)
    print("TEST 4: АДАПТИВНЫЕ TP (агрессивные)")
    print("="*90)
    print("   TP1 = max(30, SL×1.0), TP2 = max(50, SL×1.5), TP3 = max(80, SL×2.0)")

    trades_aggressive = backtest_adaptive_tp(df, strategy,
                                            tp1_ratio=1.0, tp2_ratio=1.5, tp3_ratio=2.0,
                                            min_tp1=30, min_tp2=50, min_tp3=80)
    results['Адаптивные (1.0/1.5/2.0)'] = analyze_results(trades_aggressive, 'Адаптивные агрессивные')

    # Compare all
    compare_strategies(results)

    print("\n" + "=" * 90)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("=" * 90)


if __name__ == "__main__":
    main()
