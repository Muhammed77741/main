"""
Помесячный анализ результатов бэктеста SHORT Optimized
Показывает результаты по каждому месяцу
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

def analyze_monthly_results(results_file):
    """Анализ результатов по месяцам"""

    print("\n" + "="*80)
    print("📊 ПОМЕСЯЧНЫЙ АНАЛИЗ РЕЗУЛЬТАТОВ БЭКТЕСТА")
    print("="*80)

    # Load results
    df = pd.read_csv(results_file)

    # Convert to datetime
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])

    # Add month column
    df['month'] = df['entry_time'].dt.to_period('M')

    # Overall stats
    total_trades = len(df)
    total_wins = len(df[df['pnl_pct'] > 0])
    total_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    total_pnl = df['pnl_pct'].sum()

    print(f"\n📈 ОБЩИЕ РЕЗУЛЬТАТЫ:")
    print(f"   Всего сделок: {total_trades}")
    print(f"   Win Rate: {total_wr:.1f}%")
    print(f"   Total PnL: {total_pnl:+.2f}%")
    print(f"   Период: {df['entry_time'].min().strftime('%Y-%m-%d')} → {df['exit_time'].max().strftime('%Y-%m-%d')}")

    # Monthly breakdown
    print(f"\n{'='*80}")
    print(f"📅 РЕЗУЛЬТАТЫ ПО МЕСЯЦАМ")
    print(f"{'='*80}")

    monthly_stats = []

    for month in sorted(df['month'].unique()):
        month_df = df[df['month'] == month]

        trades = len(month_df)
        wins = len(month_df[month_df['pnl_pct'] > 0])
        wr = (wins / trades * 100) if trades > 0 else 0
        pnl = month_df['pnl_pct'].sum()

        # By direction
        long_trades = len(month_df[month_df['direction'] == 'LONG'])
        long_wins = len(month_df[(month_df['direction'] == 'LONG') & (month_df['pnl_pct'] > 0)])
        long_wr = (long_wins / long_trades * 100) if long_trades > 0 else 0
        long_pnl = month_df[month_df['direction'] == 'LONG']['pnl_pct'].sum()

        short_trades = len(month_df[month_df['direction'] == 'SHORT'])
        short_wins = len(month_df[(month_df['direction'] == 'SHORT') & (month_df['pnl_pct'] > 0)])
        short_wr = (short_wins / short_trades * 100) if short_trades > 0 else 0
        short_pnl = month_df[month_df['direction'] == 'SHORT']['pnl_pct'].sum()

        monthly_stats.append({
            'month': str(month),
            'trades': trades,
            'wr': wr,
            'pnl': pnl,
            'long_trades': long_trades,
            'long_wr': long_wr,
            'long_pnl': long_pnl,
            'short_trades': short_trades,
            'short_wr': short_wr,
            'short_pnl': short_pnl
        })

        # Print
        print(f"\n📅 {month}")
        print(f"   Всего: {trades} сделок, {wr:.1f}% WR, {pnl:+.2f}% PnL")
        if long_trades > 0:
            print(f"   LONG:  {long_trades} сделок, {long_wr:.1f}% WR, {long_pnl:+.2f}% PnL")
        if short_trades > 0:
            print(f"   SHORT: {short_trades} сделок, {short_wr:.1f}% WR, {short_pnl:+.2f}% PnL")

    # Create summary table
    monthly_df = pd.DataFrame(monthly_stats)

    print(f"\n{'='*80}")
    print(f"📊 СВОДНАЯ ТАБЛИЦА")
    print(f"{'='*80}\n")

    print(f"{'Месяц':<12} {'Сделок':>7} {'WR':>6} {'PnL':>10} {'LONG':>6} {'SHORT':>6}")
    print("-" * 80)

    for _, row in monthly_df.iterrows():
        print(f"{row['month']:<12} {row['trades']:>7} {row['wr']:>5.1f}% {row['pnl']:>9.2f}% "
              f"{row['long_trades']:>6} {row['short_trades']:>6}")

    print("-" * 80)
    print(f"{'ИТОГО':<12} {monthly_df['trades'].sum():>7} {total_wr:>5.1f}% {total_pnl:>9.2f}% "
          f"{monthly_df['long_trades'].sum():>6} {monthly_df['short_trades'].sum():>6}")

    # Best and worst months
    print(f"\n{'='*80}")
    print(f"🏆 ЛУЧШИЕ И ХУДШИЕ МЕСЯЦЫ")
    print(f"{'='*80}")

    best_month = monthly_df.loc[monthly_df['pnl'].idxmax()]
    worst_month = monthly_df.loc[monthly_df['pnl'].idxmin()]
    best_wr_month = monthly_df.loc[monthly_df['wr'].idxmax()]

    print(f"\n✅ Лучший по прибыли: {best_month['month']}")
    print(f"   {best_month['trades']} сделок, {best_month['wr']:.1f}% WR, {best_month['pnl']:+.2f}% PnL")

    print(f"\n❌ Худший по прибыли: {worst_month['month']}")
    print(f"   {worst_month['trades']} сделок, {worst_month['wr']:.1f}% WR, {worst_month['pnl']:+.2f}% PnL")

    print(f"\n🎯 Лучший по винрейту: {best_wr_month['month']}")
    print(f"   {best_wr_month['trades']} сделок, {best_wr_month['wr']:.1f}% WR, {best_wr_month['pnl']:+.2f}% PnL")

    # Cumulative PnL by month
    print(f"\n{'='*80}")
    print(f"📈 НАКОПИТЕЛЬНАЯ ПРИБЫЛЬ")
    print(f"{'='*80}\n")

    cumulative = 0
    for _, row in monthly_df.iterrows():
        cumulative += row['pnl']
        print(f"{row['month']:<12} Месячная: {row['pnl']:>+7.2f}%  |  Накопительная: {cumulative:>+8.2f}%")

    print(f"\n{'='*80}\n")

    # Save monthly stats
    monthly_df.to_csv('monthly_analysis_results.csv', index=False)
    print(f"💾 Помесячная статистика сохранена: monthly_analysis_results.csv\n")

    return monthly_df


if __name__ == "__main__":
    # Check if results file provided
    if len(sys.argv) > 1:
        results_file = sys.argv[1]
    else:
        results_file = 'smc_trading_strategy/backtest_v3_short_optimized_results.csv'

    try:
        analyze_monthly_results(results_file)
    except FileNotFoundError:
        print(f"\n❌ Файл не найден: {results_file}")
        print(f"\nИспользование:")
        print(f"   python analyze_monthly.py [results_file.csv]")
        print(f"\nПо умолчанию: smc_trading_strategy/backtest_v3_short_optimized_results.csv")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
