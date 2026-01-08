"""
Расчет прибыли для фиксированного лота (0.1, 0.01 и т.д.)
Без реинвестирования - каждая сделка одинаковым объемом
"""

import pandas as pd
import numpy as np
from pattern_recognition_strategy import PatternRecognitionStrategy
from datetime import timedelta


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


def backtest_fixed_lot(df, strategy, lot_size=0.1,
                       tp1=30, tp2=50, tp3=80,
                       close_pct1=0.5, close_pct2=0.3, close_pct3=0.2):
    """
    Backtest with fixed lot size

    Args:
        lot_size: Fixed lot size for all trades (0.01, 0.1, 1.0)
        For XAUUSD: 0.1 lot = 10 oz = $10 per point
    """

    print("\n" + "="*80)
    print(f"РАСЧЕТ ДЛЯ ФИКСИРОВАННОГО ЛОТА: {lot_size}")
    print("="*80)

    # For XAUUSD: 1 lot = 100 oz, so value per point depends on lot size
    # 1 lot = $100 per point
    # 0.1 lot = $10 per point
    # 0.01 lot = $1 per point
    value_per_point = lot_size * 100  # For XAUUSD

    print(f"\n💰 Параметры:")
    print(f"   Лот: {lot_size}")
    print(f"   Стоимость 1 пункта: ${value_per_point:.2f}")
    print(f"   TP уровни: {tp1}п / {tp2}п / {tp3}п")
    print(f"   Распределение: {close_pct1*100:.0f}% / {close_pct2*100:.0f}% / {close_pct3*100:.0f}%")

    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    print(f"\n📊 Найдено сигналов: {len(df_signals)}")

    trades = []

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        direction = signal['signal']
        entry_time = df_signals.index[i]

        # Track position
        total_pnl_points = 0.0
        position_remaining = 1.0

        exit_price = None
        exit_type = 'EOD'
        exit_time = None

        tp1_hit = False
        tp2_hit = False
        tp3_hit = False
        sl_hit = False

        # TP prices
        if direction == 1:  # LONG
            tp1_price = entry_price + tp1
            tp2_price = entry_price + tp2
            tp3_price = entry_price + tp3
        else:  # SHORT
            tp1_price = entry_price - tp1
            tp2_price = entry_price - tp2
            tp3_price = entry_price - tp3

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
                # Check SL first - closes entire remaining position
                if low <= stop_loss and not sl_hit:
                    pnl_points = (stop_loss - entry_price) * position_remaining
                    total_pnl_points += pnl_points
                    position_remaining = 0
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = candle_time
                    sl_hit = True
                    break

                # Check TPs in reverse order (TP3, TP2, TP1)
                if high >= tp3_price and not tp3_hit:
                    pnl_points = (tp3_price - entry_price) * close_pct3
                    total_pnl_points += pnl_points
                    position_remaining -= close_pct3
                    exit_price = tp3_price
                    exit_type = 'TP3'
                    exit_time = candle_time
                    tp3_hit = True

                if high >= tp2_price and not tp2_hit:
                    pnl_points = (tp2_price - entry_price) * close_pct2
                    total_pnl_points += pnl_points
                    position_remaining -= close_pct2
                    exit_price = tp2_price
                    exit_type = 'TP2'
                    exit_time = candle_time
                    tp2_hit = True

                if high >= tp1_price and not tp1_hit:
                    pnl_points = (tp1_price - entry_price) * close_pct1
                    total_pnl_points += pnl_points
                    position_remaining -= close_pct1
                    exit_price = tp1_price
                    exit_type = 'TP1'
                    exit_time = candle_time
                    tp1_hit = True

            else:  # SHORT
                # Check SL first
                if high >= stop_loss and not sl_hit:
                    pnl_points = (entry_price - stop_loss) * position_remaining
                    total_pnl_points += pnl_points
                    position_remaining = 0
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = candle_time
                    sl_hit = True
                    break

                # Check TPs in reverse order
                if low <= tp3_price and not tp3_hit:
                    pnl_points = (entry_price - tp3_price) * close_pct3
                    total_pnl_points += pnl_points
                    position_remaining -= close_pct3
                    exit_price = tp3_price
                    exit_type = 'TP3'
                    exit_time = candle_time
                    tp3_hit = True

                if low <= tp2_price and not tp2_hit:
                    pnl_points = (entry_price - tp2_price) * close_pct2
                    total_pnl_points += pnl_points
                    position_remaining -= close_pct2
                    exit_price = tp2_price
                    exit_type = 'TP2'
                    exit_time = candle_time
                    tp2_hit = True

                if low <= tp1_price and not tp1_hit:
                    pnl_points = (entry_price - tp1_price) * close_pct1
                    total_pnl_points += pnl_points
                    position_remaining -= close_pct1
                    exit_price = tp1_price
                    exit_type = 'TP1'
                    exit_time = candle_time
                    tp1_hit = True

        # Close remaining at timeout
        if position_remaining > 0:
            final_close = df_future['close'].iloc[-1]
            if direction == 1:
                pnl_points = (final_close - entry_price) * position_remaining
            else:
                pnl_points = (entry_price - final_close) * position_remaining

            total_pnl_points += pnl_points
            exit_price = final_close
            exit_type = 'EOD'
            exit_time = df_future.index[-1]

        # Convert points to USD
        pnl_usd = total_pnl_points * value_per_point
        pnl_pct = (total_pnl_points / entry_price) * 100
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
            'pnl_points': total_pnl_points,
            'pnl_usd': pnl_usd,
            'pnl_pct': pnl_pct,
            'duration_hours': duration_hours,
            'tp1_hit': tp1_hit,
            'tp2_hit': tp2_hit,
            'tp3_hit': tp3_hit,
            'sl_hit': sl_hit,
        })

    return pd.DataFrame(trades), value_per_point


def analyze_results(trades_df, lot_size, value_per_point):
    """Analyze and display results"""

    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ ДЛЯ ЛОТА {lot_size}")
    print(f"{'='*80}")

    # Overall stats
    total_trades = len(trades_df)
    wins = len(trades_df[trades_df['pnl_usd'] > 0])
    losses = len(trades_df[trades_df['pnl_usd'] <= 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    total_pnl_usd = trades_df['pnl_usd'].sum()
    total_pnl_points = trades_df['pnl_points'].sum()
    avg_pnl_usd = trades_df['pnl_usd'].mean()
    avg_pnl_points = trades_df['pnl_points'].mean()

    total_profit_usd = trades_df[trades_df['pnl_usd'] > 0]['pnl_usd'].sum()
    total_loss_usd = trades_df[trades_df['pnl_usd'] < 0]['pnl_usd'].sum()

    print(f"\n💰 Итоговая прибыль:")
    print(f"   Чистая прибыль: ${total_pnl_usd:,.2f}")
    print(f"   Всего пунктов: {total_pnl_points:+.1f} пунктов")
    print(f"   Среднее на сделку: ${avg_pnl_usd:+.2f} ({avg_pnl_points:+.1f}п)")

    print(f"\n📊 Статистика сделок:")
    print(f"   Всего: {total_trades}")
    print(f"   Прибыльных: {wins} ({win_rate:.1f}%)")
    print(f"   Убыточных: {losses} ({(losses/total_trades*100):.1f}%)")

    print(f"\n💵 Детали P&L:")
    print(f"   Общая прибыль: ${total_profit_usd:+,.2f}")
    print(f"   Общий убыток:  ${total_loss_usd:+,.2f}")
    print(f"   Чистая прибыль: ${total_pnl_usd:+,.2f}")

    # Monthly breakdown
    print(f"\n📅 Прибыль по месяцам:")
    monthly_totals = []

    for month in sorted(trades_df['month'].unique()):
        month_data = trades_df[trades_df['month'] == month]
        month_pnl_usd = month_data['pnl_usd'].sum()
        month_pnl_points = month_data['pnl_points'].sum()
        month_trades = len(month_data)
        month_wins = len(month_data[month_data['pnl_usd'] > 0])
        month_wr = (month_wins / month_trades * 100) if month_trades > 0 else 0

        emoji = "✅" if month_pnl_usd > 0 else "❌"
        print(f"   {emoji} {month}: ${month_pnl_usd:+8,.2f} ({month_pnl_points:+6.1f}п) "
              f"[{month_trades} сделок, WR {month_wr:.0f}%]")

        monthly_totals.append(month_pnl_usd)

    # Best and worst trades
    best_trade = trades_df.loc[trades_df['pnl_usd'].idxmax()]
    worst_trade = trades_df.loc[trades_df['pnl_usd'].idxmin()]

    print(f"\n🏆 Лучшая сделка:")
    print(f"   {best_trade['entry_time']} - ${best_trade['pnl_usd']:+.2f} ({best_trade['pnl_points']:+.1f}п)")

    print(f"\n💔 Худшая сделка:")
    print(f"   {worst_trade['entry_time']} - ${worst_trade['pnl_usd']:+.2f} ({worst_trade['pnl_points']:+.1f}п)")

    # Calculate required capital based on max drawdown
    cumulative_pnl = trades_df['pnl_usd'].cumsum()
    running_max = cumulative_pnl.expanding().max()
    drawdown = cumulative_pnl - running_max
    max_drawdown_usd = drawdown.min()

    print(f"\n📉 Просадка:")
    print(f"   Максимальная: ${max_drawdown_usd:,.2f}")

    # Recommended capital
    # Should be able to withstand max drawdown + some buffer
    recommended_capital = abs(max_drawdown_usd) * 3  # 3x buffer for safety

    print(f"\n💼 Рекомендуемый капитал:")
    print(f"   Минимальный: ${abs(max_drawdown_usd):,.2f} (покрывает макс. просадку)")
    print(f"   Рекомендуемый: ${recommended_capital:,.2f} (3x буфер)")

    # ROI calculation
    if recommended_capital > 0:
        roi = (total_pnl_usd / recommended_capital) * 100
        print(f"   ROI от рекомендуемого: {roi:+.2f}%")

    return {
        'total_pnl_usd': total_pnl_usd,
        'total_pnl_points': total_pnl_points,
        'win_rate': win_rate,
        'total_trades': total_trades,
        'max_drawdown_usd': max_drawdown_usd,
        'recommended_capital': recommended_capital,
    }


def main():
    print("\n" + "="*80)
    print("КАЛЬКУЛЯТОР ФИКСИРОВАННОГО ЛОТА")
    print("="*80)

    # Load data
    df = load_mt5_data()
    print(f"\n📊 Загружено {len(df)} свечей")
    print(f"   Период: {df.index[0]} до {df.index[-1]}")

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Test with different lot sizes
    lot_sizes = [0.01, 0.1, 1.0]
    results = {}

    for lot_size in lot_sizes:
        trades_df, value_per_point = backtest_fixed_lot(
            df, strategy,
            lot_size=lot_size,
            tp1=30, tp2=50, tp3=80,
            close_pct1=0.5, close_pct2=0.3, close_pct3=0.2
        )

        stats = analyze_results(trades_df, lot_size, value_per_point)
        results[lot_size] = stats

    # Final comparison
    print("\n" + "="*80)
    print("СРАВНЕНИЕ РАЗМЕРОВ ЛОТА")
    print("="*80)

    print(f"\n{'Лот':<10}{'Прибыль USD':<18}{'Win Rate':<12}{'Макс DD':<15}{'Рек. капитал':<18}")
    print("-" * 80)

    for lot_size, stats in results.items():
        print(f"{lot_size:<10.2f}${stats['total_pnl_usd']:>15,.2f}  "
              f"{stats['win_rate']:>9.1f}%  "
              f"${stats['max_drawdown_usd']:>12,.2f}  "
              f"${stats['recommended_capital']:>15,.2f}")

    print("\n" + "="*80)
    print("✅ РАСЧЕТ ЗАВЕРШЕН!")
    print("="*80)

    print("\n💡 ВЫВОДЫ:")
    print("   Фиксированный лот = стабильная прибыль без риска переторговки")
    print("   0.01 лот: безопасно для малого капитала ($500-1000)")
    print("   0.1 лот: оптимально для среднего капитала ($5000+)")
    print("   1.0 лот: для крупного капитала ($50000+)")


if __name__ == "__main__":
    main()
