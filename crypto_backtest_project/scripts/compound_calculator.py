"""
Расчет компаундинга (реинвестирование прибыли) для стратегии
Показывает сколько будет капитал через год если увеличивать лот с ростом депозита
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


def backtest_with_compound(df, strategy, initial_capital=500,
                           tp1=30, tp2=50, tp3=80,
                           close_pct1=0.5, close_pct2=0.3, close_pct3=0.2,
                           risk_per_trade=0.02):
    """
    Backtest with compound interest (реинвестирование прибыли)

    Args:
        initial_capital: Начальный капитал ($500)
        risk_per_trade: Риск на сделку (2% от текущего капитала)
    """

    print("\n" + "="*80)
    print("РАСЧЕТ КОМПАУНДИНГА С РЕИНВЕСТИРОВАНИЕМ ПРИБЫЛИ")
    print("="*80)

    print(f"\n💰 Начальные параметры:")
    print(f"   Стартовый капитал: ${initial_capital:.2f}")
    print(f"   Риск на сделку: {risk_per_trade*100:.1f}% от текущего капитала")
    print(f"   TP уровни: {tp1}п / {tp2}п / {tp3}п")
    print(f"   Распределение: {close_pct1*100:.0f}% / {close_pct2*100:.0f}% / {close_pct3*100:.0f}%")

    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    print(f"\n📊 Найдено сигналов: {len(df_signals)}")

    # Track capital through time
    current_capital = initial_capital
    capital_history = []

    trades = []

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        direction = signal['signal']
        entry_time = df_signals.index[i]

        # Calculate position size based on current capital and risk
        sl_distance = abs(entry_price - stop_loss)
        sl_distance_pct = sl_distance / entry_price

        # Position size: risk_amount / sl_distance_pct
        risk_amount = current_capital * risk_per_trade
        position_size_usd = risk_amount / sl_distance_pct

        # Limit position size to not exceed capital
        max_position = current_capital * 10  # Max 10x leverage
        position_size_usd = min(position_size_usd, max_position)

        # Track position
        total_pnl_usd = 0.0
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
                # Check SL first
                if low <= stop_loss and not sl_hit:
                    pnl_pct = ((stop_loss - entry_price) / entry_price) * position_remaining
                    pnl_usd = position_size_usd * pnl_pct
                    total_pnl_usd += pnl_usd
                    position_remaining = 0
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = candle_time
                    sl_hit = True
                    break

                # Check TPs
                if high >= tp3_price and not tp3_hit and position_remaining > 0:
                    pnl_pct = ((tp3_price - entry_price) / entry_price) * close_pct3
                    pnl_usd = position_size_usd * pnl_pct
                    total_pnl_usd += pnl_usd
                    position_remaining -= close_pct3
                    exit_price = tp3_price
                    exit_type = 'TP3'
                    exit_time = candle_time
                    tp3_hit = True

                if high >= tp2_price and not tp2_hit and position_remaining > 0:
                    pnl_pct = ((tp2_price - entry_price) / entry_price) * close_pct2
                    pnl_usd = position_size_usd * pnl_pct
                    total_pnl_usd += pnl_usd
                    position_remaining -= close_pct2
                    exit_price = tp2_price
                    exit_type = 'TP2'
                    exit_time = candle_time
                    tp2_hit = True

                if high >= tp1_price and not tp1_hit and position_remaining > 0:
                    pnl_pct = ((tp1_price - entry_price) / entry_price) * close_pct1
                    pnl_usd = position_size_usd * pnl_pct
                    total_pnl_usd += pnl_usd
                    position_remaining -= close_pct1
                    exit_price = tp1_price
                    exit_type = 'TP1'
                    exit_time = candle_time
                    tp1_hit = True

            else:  # SHORT
                # Check SL first
                if high >= stop_loss and not sl_hit:
                    pnl_pct = ((entry_price - stop_loss) / entry_price) * position_remaining
                    pnl_usd = position_size_usd * pnl_pct
                    total_pnl_usd += pnl_usd
                    position_remaining = 0
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = candle_time
                    sl_hit = True
                    break

                # Check TPs
                if low <= tp3_price and not tp3_hit and position_remaining > 0:
                    pnl_pct = ((entry_price - tp3_price) / entry_price) * close_pct3
                    pnl_usd = position_size_usd * pnl_pct
                    total_pnl_usd += pnl_usd
                    position_remaining -= close_pct3
                    exit_price = tp3_price
                    exit_type = 'TP3'
                    exit_time = candle_time
                    tp3_hit = True

                if low <= tp2_price and not tp2_hit and position_remaining > 0:
                    pnl_pct = ((entry_price - tp2_price) / entry_price) * close_pct2
                    pnl_usd = position_size_usd * pnl_pct
                    total_pnl_usd += pnl_usd
                    position_remaining -= close_pct2
                    exit_price = tp2_price
                    exit_type = 'TP2'
                    exit_time = candle_time
                    tp2_hit = True

                if low <= tp1_price and not tp1_hit and position_remaining > 0:
                    pnl_pct = ((entry_price - tp1_price) / entry_price) * close_pct1
                    pnl_usd = position_size_usd * pnl_pct
                    total_pnl_usd += pnl_usd
                    position_remaining -= close_pct1
                    exit_price = tp1_price
                    exit_type = 'TP1'
                    exit_time = candle_time
                    tp1_hit = True

        # Close remaining at timeout
        if position_remaining > 0:
            final_close = df_future['close'].iloc[-1]
            if direction == 1:
                pnl_pct = ((final_close - entry_price) / entry_price) * position_remaining
            else:
                pnl_pct = ((entry_price - final_close) / entry_price) * position_remaining

            pnl_usd = position_size_usd * pnl_pct
            total_pnl_usd += pnl_usd
            exit_price = final_close
            exit_type = 'EOD'
            exit_time = df_future.index[-1]

        # Update capital with compound effect
        capital_before = current_capital
        current_capital += total_pnl_usd
        capital_change_pct = (total_pnl_usd / capital_before) * 100

        duration_hours = (exit_time - entry_time).total_seconds() / 3600

        # Store capital history
        capital_history.append({
            'trade_num': len(trades) + 1,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'month': entry_time.strftime('%Y-%m'),
            'capital_before': capital_before,
            'capital_after': current_capital,
            'pnl_usd': total_pnl_usd,
            'pnl_pct': capital_change_pct,
            'position_size': position_size_usd,
            'exit_type': exit_type,
        })

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'month': entry_time.strftime('%Y-%m'),
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'capital_before': capital_before,
            'capital_after': current_capital,
            'pnl_usd': total_pnl_usd,
            'pnl_pct': capital_change_pct,
            'position_size': position_size_usd,
            'duration_hours': duration_hours,
            'tp1_hit': tp1_hit,
            'tp2_hit': tp2_hit,
            'tp3_hit': tp3_hit,
            'sl_hit': sl_hit,
        })

    return pd.DataFrame(trades), pd.DataFrame(capital_history), current_capital


def analyze_compound_results(trades_df, capital_history_df, initial_capital, final_capital):
    """Analyze compound results"""

    print(f"\n{'='*80}")
    print("РЕЗУЛЬТАТЫ С КОМПАУНДИНГОМ (РЕИНВЕСТИРОВАНИЕ)")
    print(f"{'='*80}")

    # Overall stats
    total_trades = len(trades_df)
    wins = len(trades_df[trades_df['pnl_usd'] > 0])
    losses = len(trades_df[trades_df['pnl_usd'] <= 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    total_profit_usd = trades_df[trades_df['pnl_usd'] > 0]['pnl_usd'].sum()
    total_loss_usd = trades_df[trades_df['pnl_usd'] < 0]['pnl_usd'].sum()
    net_pnl = final_capital - initial_capital
    net_pnl_pct = ((final_capital / initial_capital) - 1) * 100

    print(f"\n💰 Капитал:")
    print(f"   Начальный: ${initial_capital:.2f}")
    print(f"   Финальный: ${final_capital:.2f}")
    print(f"   Прибыль:   ${net_pnl:+.2f} ({net_pnl_pct:+.2f}%)")

    print(f"\n📊 Статистика сделок:")
    print(f"   Всего: {total_trades}")
    print(f"   Прибыльных: {wins} ({win_rate:.1f}%)")
    print(f"   Убыточных: {losses} ({(losses/total_trades*100):.1f}%)")

    print(f"\n💵 Детали P&L:")
    print(f"   Общая прибыль: ${total_profit_usd:+.2f}")
    print(f"   Общий убыток:  ${total_loss_usd:+.2f}")
    print(f"   Чистая прибыль: ${net_pnl:+.2f}")

    # Monthly breakdown
    print(f"\n📅 Результаты по месяцам (с компаундингом):")
    monthly_stats = []

    for month in sorted(trades_df['month'].unique()):
        month_data = trades_df[trades_df['month'] == month]

        # Capital at start and end of month
        capital_start = month_data['capital_before'].iloc[0]
        capital_end = month_data['capital_after'].iloc[-1]
        month_pnl_usd = capital_end - capital_start
        month_pnl_pct = ((capital_end / capital_start) - 1) * 100

        month_trades = len(month_data)
        month_wins = len(month_data[month_data['pnl_usd'] > 0])
        month_wr = (month_wins / month_trades * 100) if month_trades > 0 else 0

        emoji = "✅" if month_pnl_usd > 0 else "❌"

        print(f"   {emoji} {month}: ${capital_start:>8.2f} → ${capital_end:>8.2f} "
              f"({month_pnl_pct:+7.2f}%, ${month_pnl_usd:+8.2f}) "
              f"[{month_trades} сделок, WR {month_wr:.0f}%]")

        monthly_stats.append({
            'month': month,
            'capital_start': capital_start,
            'capital_end': capital_end,
            'pnl_usd': month_pnl_usd,
            'pnl_pct': month_pnl_pct,
            'trades': month_trades,
            'win_rate': month_wr,
        })

    # Max drawdown
    capital_curve = capital_history_df['capital_after'].values
    running_max = np.maximum.accumulate(capital_curve)
    drawdown = (capital_curve - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    print(f"\n📉 Просадка:")
    print(f"   Максимальная: {max_drawdown:.2f}%")

    # Best and worst trades
    best_trade = trades_df.loc[trades_df['pnl_usd'].idxmax()]
    worst_trade = trades_df.loc[trades_df['pnl_usd'].idxmin()]

    print(f"\n🏆 Лучшая сделка:")
    print(f"   {best_trade['entry_time']} - ${best_trade['pnl_usd']:+.2f} ({best_trade['pnl_pct']:+.2f}%)")

    print(f"\n💔 Худшая сделка:")
    print(f"   {worst_trade['entry_time']} - ${worst_trade['pnl_usd']:+.2f} ({worst_trade['pnl_pct']:+.2f}%)")

    return monthly_stats


def main():
    print("\n" + "="*80)
    print("КАЛЬКУЛЯТОР КОМПАУНДИНГА (РЕИНВЕСТИРОВАНИЕ ПРИБЫЛИ)")
    print("="*80)

    # Load data
    df = load_mt5_data()
    print(f"\n📊 Загружено {len(df)} свечей")
    print(f"   Период: {df.index[0]} до {df.index[-1]}")

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Test with different initial capitals
    initial_capitals = [500, 1000, 5000]

    for initial_capital in initial_capitals:
        print("\n" + "="*80)
        print(f"ТЕСТ С НАЧАЛЬНЫМ КАПИТАЛОМ: ${initial_capital}")
        print("="*80)

        trades_df, capital_history_df, final_capital = backtest_with_compound(
            df, strategy,
            initial_capital=initial_capital,
            tp1=30, tp2=50, tp3=80,
            close_pct1=0.5, close_pct2=0.3, close_pct3=0.2,
            risk_per_trade=0.02  # 2% risk per trade
        )

        monthly_stats = analyze_compound_results(
            trades_df, capital_history_df,
            initial_capital, final_capital
        )

    print("\n" + "="*80)
    print("✅ РАСЧЕТ ЗАВЕРШЕН!")
    print("="*80)

    print("\n💡 ВЫВОДЫ:")
    print("   С компаундингом (реинвестированием) прибыль растет экспоненциально!")
    print("   Начиная с $500 можно вырасти в разы за год")
    print("   ВАЖНО: Соблюдать риск-менеджмент 2% на сделку!")


if __name__ == "__main__":
    main()
