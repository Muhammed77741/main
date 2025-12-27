"""
Monthly performance analysis and lot size calculation for Pattern Recognition (1.618)
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

    # Add market hours info
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def backtest_with_details(df, strategy):
    """Run backtest and return detailed trade information"""

    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())

    # Get signals
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    trades = []

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]

        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']

        entry_time = df_signals.index[i]
        search_end = entry_time + timedelta(hours=48)

        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]

        if len(df_future) == 0:
            continue

        exit_price = None
        exit_type = None
        exit_time = None

        # Find exit
        for j in range(len(df_future)):
            if direction == 1:  # LONG
                if df_future['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break
            else:  # SHORT
                if df_future['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break

        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'
            exit_time = df_future.index[-1]

        # Calculate PnL
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl_points = exit_price - entry_price
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            pnl_points = entry_price - exit_price

        # Calculate SL in points
        sl_points = abs(entry_price - stop_loss)

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'month': entry_time.strftime('%Y-%m'),
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'sl_points': sl_points,
        })

    return pd.DataFrame(trades)


def analyze_monthly(trades_df):
    """Analyze performance by month"""

    print("=" * 100)
    print("СТАТИСТИКА ПО МЕСЯЦАМ - PATTERN RECOGNITION (1.618)")
    print("=" * 100)

    monthly_stats = []

    for month in sorted(trades_df['month'].unique()):
        month_trades = trades_df[trades_df['month'] == month]

        wins = len(month_trades[month_trades['pnl_pct'] > 0])
        losses = len(month_trades[month_trades['pnl_pct'] <= 0])
        total_trades = len(month_trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = month_trades['pnl_pct'].sum()
        avg_pnl = month_trades['pnl_pct'].mean()

        wins_df = month_trades[month_trades['pnl_pct'] > 0]
        losses_df = month_trades[month_trades['pnl_pct'] <= 0]

        avg_win = wins_df['pnl_pct'].mean() if len(wins_df) > 0 else 0
        avg_loss = losses_df['pnl_pct'].mean() if len(losses_df) > 0 else 0

        best_trade = month_trades['pnl_pct'].max()
        worst_trade = month_trades['pnl_pct'].min()

        # Exit types
        tp_count = len(month_trades[month_trades['exit_type'] == 'TP'])
        sl_count = len(month_trades[month_trades['exit_type'] == 'SL'])
        eod_count = len(month_trades[month_trades['exit_type'] == 'EOD'])

        monthly_stats.append({
            'month': month,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'tp_count': tp_count,
            'sl_count': sl_count,
            'eod_count': eod_count,
        })

    monthly_df = pd.DataFrame(monthly_stats)

    # Display monthly stats
    print(f"\n{'Месяц':<12}{'Сделок':<8}{'Wins':<6}{'Loss':<6}{'WinRate':<10}{'PnL':<12}{'Avg':<10}{'Best':<10}{'Worst':<10}{'TP':<5}{'SL':<5}{'EOD':<5}")
    print("-" * 100)

    for _, row in monthly_df.iterrows():
        emoji = "✅" if row['total_pnl'] > 0 else "❌"
        print(f"{emoji} {row['month']:<10}{row['total_trades']:<8}{row['wins']:<6}{row['losses']:<6}"
              f"{row['win_rate']:>7.1f}%  {row['total_pnl']:>+9.2f}%  {row['avg_pnl']:>+7.2f}%  "
              f"{row['best_trade']:>+7.2f}%  {row['worst_trade']:>+7.2f}%  "
              f"{row['tp_count']:<5}{row['sl_count']:<5}{row['eod_count']:<5}")

    # Summary
    print("\n" + "=" * 100)
    print("ИТОГОВАЯ СТАТИСТИКА ЗА ВСЕ МЕСЯЦЫ")
    print("=" * 100)

    profitable_months = len(monthly_df[monthly_df['total_pnl'] > 0])
    total_months = len(monthly_df)

    print(f"\n📊 Общие показатели:")
    print(f"   Всего месяцев: {total_months}")
    print(f"   Прибыльных: {profitable_months} ({profitable_months/total_months*100:.1f}%)")
    print(f"   Убыточных: {total_months - profitable_months} ({(total_months-profitable_months)/total_months*100:.1f}%)")
    print(f"   Общий PnL: {monthly_df['total_pnl'].sum():+.2f}%")
    print(f"   Средний месячный PnL: {monthly_df['total_pnl'].mean():+.2f}%")
    print(f"   Лучший месяц: {monthly_df['total_pnl'].max():+.2f}% ({monthly_df.loc[monthly_df['total_pnl'].idxmax(), 'month']})")
    print(f"   Худший месяц: {monthly_df['total_pnl'].min():+.2f}% ({monthly_df.loc[monthly_df['total_pnl'].idxmin(), 'month']})")

    print(f"\n📈 Средние показатели:")
    print(f"   Сделок в месяц: {monthly_df['total_trades'].mean():.1f}")
    print(f"   Win Rate: {monthly_df['win_rate'].mean():.1f}%")
    print(f"   Средняя прибыль: {monthly_df['avg_win'].mean():+.2f}%")
    print(f"   Средний убыток: {monthly_df['avg_loss'].mean():+.2f}%")

    return monthly_df


def calculate_lot_size(trades_df, account_balance=500, risk_percent=2.0):
    """Calculate recommended lot size for given account balance"""

    print("\n" + "=" * 100)
    print(f"РАСЧЕТ ОПТИМАЛЬНОГО ЛОТА ДЛЯ КАПИТАЛА ${account_balance:.2f}")
    print("=" * 100)

    # Calculate average SL in points
    avg_sl_points = trades_df['sl_points'].mean()
    median_sl_points = trades_df['sl_points'].median()
    max_sl_points = trades_df['sl_points'].max()
    min_sl_points = trades_df['sl_points'].min()

    print(f"\n📊 Анализ стоп-лоссов:")
    print(f"   Средний SL: {avg_sl_points:.2f} пунктов (${avg_sl_points:.2f})")
    print(f"   Медианный SL: {median_sl_points:.2f} пунктов")
    print(f"   Минимальный SL: {min_sl_points:.2f} пунктов")
    print(f"   Максимальный SL: {max_sl_points:.2f} пунктов")

    # XAUUSD lot sizes
    print(f"\n💰 Стоимость пункта для XAUUSD:")
    print(f"   1 стандартный лот (100 oz): $1.00 за пункт")
    print(f"   1 мини-лот (10 oz):         $0.10 за пункт")
    print(f"   1 микро-лот (1 oz):         $0.01 за пункт")
    print(f"   0.01 лота (0.01 oz):        $0.0001 за пункт")

    # Calculate risk amount
    risk_amount = account_balance * (risk_percent / 100)

    print(f"\n🎯 Параметры риска:")
    print(f"   Баланс счета: ${account_balance:.2f}")
    print(f"   Риск на сделку: {risk_percent}%")
    print(f"   Сумма риска: ${risk_amount:.2f}")

    # Calculate lot sizes for different scenarios
    print(f"\n📐 Расчет размера лота:")
    print(f"   Формула: Лот = Риск($) / (SL в пунктах × Стоимость пункта)")
    print()

    scenarios = [
        ("Средний SL", avg_sl_points),
        ("Медианный SL", median_sl_points),
        ("Максимальный SL (консервативно)", max_sl_points),
    ]

    for scenario_name, sl_points in scenarios:
        print(f"\n   {scenario_name}: {sl_points:.2f} пунктов")

        # For different lot sizes
        for lot_size, point_value in [(1.0, 1.0), (0.1, 0.1), (0.01, 0.01)]:
            lot_needed = risk_amount / (sl_points * point_value)

            if lot_needed >= 0.01:  # Minimum lot size
                actual_risk = sl_points * point_value * lot_needed
                lot_name = "стандартный лот" if lot_size == 1.0 else "мини-лот" if lot_size == 0.1 else "микро-лот"

                print(f"      • Лот {lot_needed:.4f} ({lot_name})")
                print(f"        Риск: ${actual_risk:.2f} ({actual_risk/account_balance*100:.2f}%)")

    # Recommendation
    print(f"\n" + "=" * 100)
    print("💡 РЕКОМЕНДАЦИИ ПО ЛОТУ")
    print("=" * 100)

    # Use median SL for calculation (more realistic than average)
    recommended_lot_2pct = risk_amount / (median_sl_points * 0.01)  # Using 0.01 lot base
    recommended_lot_1pct = (account_balance * 0.01) / (median_sl_points * 0.01)

    print(f"\n✅ Для капитала ${account_balance}:")
    print(f"\n   1️⃣  КОНСЕРВАТИВНЫЙ подход (1% риск на сделку):")
    print(f"      Рекомендуемый лот: 0.01 (микро-лот)")
    print(f"      Риск на сделку: ${account_balance * 0.01:.2f}")
    print(f"      Максимальная потеря: ~{median_sl_points * 0.01 * 0.01:.2f}$ на сделку")

    print(f"\n   2️⃣  УМЕРЕННЫЙ подход (2% риск на сделку):")
    print(f"      Рекомендуемый лот: 0.01-0.02 (микро-лот)")
    print(f"      Риск на сделку: ${risk_amount:.2f}")
    print(f"      Максимальная потеря: ~{median_sl_points * 0.01 * 0.02:.2f}$ на сделку")

    print(f"\n   3️⃣  АГРЕССИВНЫЙ подход (5% риск на сделку):")
    print(f"      Рекомендуемый лот: 0.03-0.05 (микро-лот)")
    print(f"      Риск на сделку: ${account_balance * 0.05:.2f}")
    print(f"      ⚠️  ВЫСОКИЙ РИСК!")

    print(f"\n⚠️  ВАЖНО:")
    print(f"   • Не рекомендуется рисковать более 2% на одну сделку")
    print(f"   • При капитале $500 оптимальный лот: 0.01 (1% риск)")
    print(f"   • Убедитесь, что брокер поддерживает микро-лоты (0.01)")
    print(f"   • Начните с минимального лота и увеличивайте по мере роста депозита")

    # Calculate potential monthly return
    avg_monthly_pnl = trades_df.groupby('month')['pnl_pct'].sum().mean()

    print(f"\n📈 ПРОГНОЗ ДОХОДНОСТИ при лоте 0.01:")
    print(f"   Средний месячный PnL стратегии: {avg_monthly_pnl:+.2f}%")
    print(f"   При капитале $500 и лоте 0.01:")

    # Simplified calculation assuming proportional returns
    # This is rough estimate - actual returns depend on many factors
    monthly_return_estimate = avg_monthly_pnl * 0.1  # Very conservative estimate for micro lot
    print(f"   Ожидаемая месячная доходность: ~${account_balance * monthly_return_estimate / 100:.2f}")
    print(f"   Годовая доходность (если реинвестировать): ~${account_balance * (1 + monthly_return_estimate/100)**12 - account_balance:.2f}")

    print(f"\n   ⚠️  Это приблизительная оценка! Реальные результаты могут отличаться.")
    print(f"   ⚠️  Прошлые результаты не гарантируют будущую доходность!")


def main():
    print("\n" + "=" * 100)
    print("МЕСЯЧНЫЙ АНАЛИЗ И РАСЧЕТ ЛОТА - PATTERN RECOGNITION (1.618)")
    print("=" * 100 + "\n")

    # Load data
    df = load_mt5_data()
    print(f"📊 Загружено {len(df)} свечей")
    print(f"   Период: {df.index[0]} до {df.index[-1]}\n")

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Run backtest
    print("🔄 Запуск бэктеста...\n")
    trades_df = backtest_with_details(df, strategy)

    print(f"✅ Найдено {len(trades_df)} сделок\n")

    # Analyze by month
    monthly_df = analyze_monthly(trades_df)

    # Calculate lot size
    calculate_lot_size(trades_df, account_balance=500, risk_percent=2.0)

    print("\n" + "=" * 100)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("=" * 100)


if __name__ == "__main__":
    main()
