"""
Analyze losing trades from backtest results
Find patterns and suggest improvements
"""

import pandas as pd
import numpy as np

def analyze_losses():
    """Analyze losing trades in detail"""

    print("\n" + "="*80)
    print("📉 АНАЛИЗ УБЫТОЧНЫХ ПОЗИЦИЙ")
    print("="*80)

    # Load results
    df = pd.read_csv('smc_trading_strategy/backtest_v3_adaptive_results.csv')
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])

    total_trades = len(df)
    losses = df[df['pnl_pct'] < 0].copy()
    wins = df[df['pnl_pct'] > 0].copy()

    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   Всего сделок: {total_trades}")
    print(f"   Прибыльные: {len(wins)} ({len(wins)/total_trades*100:.1f}%)")
    print(f"   Убыточные: {len(losses)} ({len(losses)/total_trades*100:.1f}%)")
    print(f"   Общая прибыль: {df['pnl_pct'].sum():+.2f}%")
    print(f"   Средний убыток: {losses['pnl_pct'].mean():.2f}%")
    print(f"   Максимальный убыток: {losses['pnl_pct'].min():.2f}%")

    # 1. АНАЛИЗ ПО РЕЖИМУ РЫНКА
    print(f"\n{'='*80}")
    print(f"1️⃣  АНАЛИЗ ПО РЕЖИМУ РЫНКА (TREND vs RANGE)")
    print(f"{'='*80}")

    for regime in ['TREND', 'RANGE']:
        regime_losses = losses[losses['regime'] == regime]
        regime_all = df[df['regime'] == regime]

        if len(regime_all) > 0:
            loss_rate = len(regime_losses) / len(regime_all) * 100
            avg_loss = regime_losses['pnl_pct'].mean() if len(regime_losses) > 0 else 0
            total_loss = regime_losses['pnl_pct'].sum() if len(regime_losses) > 0 else 0

            print(f"\n   {regime}:")
            print(f"   Всего сделок: {len(regime_all)}")
            print(f"   Убыточных: {len(regime_losses)} ({loss_rate:.1f}%)")
            print(f"   Средний убыток: {avg_loss:.2f}%")
            print(f"   Общий убыток: {total_loss:.2f}%")

    # 2. АНАЛИЗ ПО НАПРАВЛЕНИЮ
    print(f"\n{'='*80}")
    print(f"2️⃣  АНАЛИЗ ПО НАПРАВЛЕНИЮ (LONG vs SHORT)")
    print(f"{'='*80}")

    for direction in ['LONG', 'SHORT']:
        dir_losses = losses[losses['direction'] == direction]
        dir_all = df[df['direction'] == direction]

        if len(dir_all) > 0:
            loss_rate = len(dir_losses) / len(dir_all) * 100
            avg_loss = dir_losses['pnl_pct'].mean() if len(dir_losses) > 0 else 0
            total_loss = dir_losses['pnl_pct'].sum() if len(dir_losses) > 0 else 0

            print(f"\n   {direction}:")
            print(f"   Всего сделок: {len(dir_all)}")
            print(f"   Убыточных: {len(dir_losses)} ({loss_rate:.1f}%)")
            print(f"   Средний убыток: {avg_loss:.2f}%")
            print(f"   Общий убыток: {total_loss:.2f}%")

    # 3. АНАЛИЗ ПО ТИПУ ВЫХОДА
    print(f"\n{'='*80}")
    print(f"3️⃣  АНАЛИЗ ПО ТИПУ ВЫХОДА")
    print(f"{'='*80}")

    for exit_type in losses['exit_type'].unique():
        et_losses = losses[losses['exit_type'] == exit_type]
        et_all = df[df['exit_type'] == exit_type]

        if len(et_all) > 0:
            loss_rate = len(et_losses) / len(et_all) * 100
            avg_loss = et_losses['pnl_pct'].mean()
            total_loss = et_losses['pnl_pct'].sum()

            print(f"\n   {exit_type}:")
            print(f"   Всего сделок: {len(et_all)}")
            print(f"   Убыточных: {len(et_losses)} ({loss_rate:.1f}%)")
            print(f"   Средний убыток: {avg_loss:.2f}%")
            print(f"   Общий убыток: {total_loss:.2f}%")

    # 4. АНАЛИЗ ПО ПРОДОЛЖИТЕЛЬНОСТИ
    print(f"\n{'='*80}")
    print(f"4️⃣  АНАЛИЗ ПО ПРОДОЛЖИТЕЛЬНОСТИ")
    print(f"{'='*80}")

    # Разбивка по времени в позиции
    bins = [0, 2, 12, 24, 48, 1000]
    labels = ['<2h', '2-12h', '12-24h', '24-48h', '>48h']
    losses['duration_group'] = pd.cut(losses['duration_hours'], bins=bins, labels=labels)

    print(f"\n   Убыточные сделки по продолжительности:")
    for group in labels:
        group_losses = losses[losses['duration_group'] == group]
        if len(group_losses) > 0:
            avg_loss = group_losses['pnl_pct'].mean()
            total_loss = group_losses['pnl_pct'].sum()
            print(f"   {group}: {len(group_losses)} сделок, avg {avg_loss:.2f}%, total {total_loss:.2f}%")

    # 5. КОМБИНИРОВАННЫЙ АНАЛИЗ
    print(f"\n{'='*80}")
    print(f"5️⃣  ПРОБЛЕМНЫЕ КОМБИНАЦИИ")
    print(f"{'='*80}")

    # Найдем худшие комбинации
    print(f"\n   Худшие комбинации (Режим + Направление + Выход):")

    grouped = losses.groupby(['regime', 'direction', 'exit_type']).agg({
        'pnl_pct': ['count', 'mean', 'sum']
    }).round(2)

    grouped.columns = ['Count', 'Avg_Loss_%', 'Total_Loss_%']
    grouped = grouped.sort_values('Total_Loss_%')

    print(grouped.head(10))

    # 6. АНАЛИЗ TP HIT PATTERN
    print(f"\n{'='*80}")
    print(f"6️⃣  АНАЛИЗ ДОСТИЖЕНИЯ TP ПЕРЕД УБЫТКОМ")
    print(f"{'='*80}")

    # Сколько TP достигнуто перед убытком
    losses['tp_count'] = losses['tp1_hit'].astype(int) + losses['tp2_hit'].astype(int) + losses['tp3_hit'].astype(int)

    print(f"\n   TP достигнуто перед убытком:")
    for tp_count in [0, 1, 2, 3]:
        tp_losses = losses[losses['tp_count'] == tp_count]
        if len(tp_losses) > 0:
            avg_loss = tp_losses['pnl_pct'].mean()
            total_loss = tp_losses['pnl_pct'].sum()
            print(f"   {tp_count} TP: {len(tp_losses)} сделок, avg {avg_loss:.2f}%, total {total_loss:.2f}%")

    # 7. САМЫЕ ХУДШИЕ СДЕЛКИ
    print(f"\n{'='*80}")
    print(f"7️⃣  ТОП-10 ХУДШИХ СДЕЛОК")
    print(f"{'='*80}")

    worst = losses.nsmallest(10, 'pnl_pct')
    print(f"\n   Worst trades:")
    for idx, row in worst.iterrows():
        print(f"\n   {row['entry_time']} → {row['exit_time']}")
        print(f"   {row['direction']} | {row['regime']} | Exit: {row['exit_type']}")
        print(f"   PnL: {row['pnl_pct']:.2f}% ({row['pnl_points']:.2f}п)")
        print(f"   Duration: {row['duration_hours']:.1f}h")
        print(f"   TP hit: TP1={row['tp1_hit']}, TP2={row['tp2_hit']}, TP3={row['tp3_hit']}")

    # 8. РЕКОМЕНДАЦИИ
    print(f"\n{'='*80}")
    print(f"8️⃣  РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ")
    print(f"{'='*80}")

    recommendations = []

    # Анализ TIMEOUT
    timeout_losses = losses[losses['exit_type'] == 'TIMEOUT']
    timeout_all = df[df['exit_type'] == 'TIMEOUT']
    if len(timeout_all) > 0:
        timeout_loss_rate = len(timeout_losses) / len(timeout_all) * 100
        timeout_total_loss = timeout_losses['pnl_pct'].sum()

        if timeout_loss_rate > 40:
            recommendations.append({
                'problem': 'TIMEOUT УБЫТКИ',
                'stats': f'{len(timeout_losses)} сделок ({timeout_loss_rate:.1f}% от всех timeout), {timeout_total_loss:.2f}% убытка',
                'suggestion': f'Уменьшить timeout с 48/60ч до 36/48ч или добавить проверку на движение против позиции'
            })

    # Анализ SL
    sl_losses = losses[losses['exit_type'] == 'SL']
    sl_all = df[df['exit_type'] == 'SL']
    if len(sl_all) > 0:
        sl_loss_rate = len(sl_losses) / len(sl_all) * 100
        sl_total_loss = sl_losses['pnl_pct'].sum()
        sl_avg_loss = sl_losses['pnl_pct'].mean()

        if sl_avg_loss < -1.0:
            recommendations.append({
                'problem': 'БОЛЬШИЕ SL УБЫТКИ',
                'stats': f'{len(sl_losses)} сделок, средний убыток {sl_avg_loss:.2f}%',
                'suggestion': 'SL слишком далеко. Рассмотреть уменьшение SL или добавить ранний выход при движении против позиции'
            })

    # Анализ SHORT
    short_losses = losses[losses['direction'] == 'SHORT']
    short_all = df[df['direction'] == 'SHORT']
    long_all = df[df['direction'] == 'LONG']

    if len(short_all) > 0 and len(long_all) > 0:
        short_loss_rate = len(short_losses) / len(short_all) * 100
        long_losses = losses[losses['direction'] == 'LONG']
        long_loss_rate = len(long_losses) / len(long_all) * 100

        if abs(short_loss_rate - long_loss_rate) > 10:
            worse_direction = 'SHORT' if short_loss_rate > long_loss_rate else 'LONG'
            recommendations.append({
                'problem': f'{worse_direction} СДЕЛКИ ХУЖЕ',
                'stats': f'SHORT: {short_loss_rate:.1f}% убытков, LONG: {long_loss_rate:.1f}% убытков',
                'suggestion': f'Рассмотреть более строгие фильтры для {worse_direction} сделок или торговать только в тренде'
            })

    # Анализ по режиму
    trend_losses = losses[losses['regime'] == 'TREND']
    trend_all = df[df['regime'] == 'TREND']
    range_losses = losses[losses['regime'] == 'RANGE']
    range_all = df[df['regime'] == 'RANGE']

    if len(trend_all) > 0 and len(range_all) > 0:
        trend_loss_rate = len(trend_losses) / len(trend_all) * 100
        range_loss_rate = len(range_losses) / len(range_all) * 100

        trend_total_loss = trend_losses['pnl_pct'].sum() if len(trend_losses) > 0 else 0
        range_total_loss = range_losses['pnl_pct'].sum() if len(range_losses) > 0 else 0

        if abs(trend_loss_rate - range_loss_rate) > 10:
            worse_regime = 'TREND' if trend_loss_rate > range_loss_rate else 'RANGE'
            recommendations.append({
                'problem': f'{worse_regime} РЕЖИМ ХУЖЕ',
                'stats': f'TREND: {trend_loss_rate:.1f}% убытков ({trend_total_loss:.2f}%), RANGE: {range_loss_rate:.1f}% убытков ({range_total_loss:.2f}%)',
                'suggestion': f'Улучшить детекцию {worse_regime} режима или настроить параметры (TP/SL/Trailing)'
            })

    if len(recommendations) > 0:
        print(f"\n   Найдено {len(recommendations)} рекомендаций:\n")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec['problem']}")
            print(f"      📊 Статистика: {rec['stats']}")
            print(f"      💡 Рекомендация: {rec['suggestion']}")
            print()
    else:
        print(f"\n   ✅ Стратегия работает хорошо, критичных проблем не найдено")

    # 9. МЕСЯЧНАЯ СТАТИСТИКА
    print(f"\n{'='*80}")
    print(f"9️⃣  УБЫТКИ ПО МЕСЯЦАМ")
    print(f"{'='*80}")

    losses['month'] = pd.to_datetime(losses['exit_time']).dt.to_period('M')
    monthly_losses = losses.groupby('month').agg({
        'pnl_pct': ['count', 'sum', 'mean']
    }).round(2)
    monthly_losses.columns = ['Loss_Count', 'Total_Loss_%', 'Avg_Loss_%']

    print(f"\n   Убытки по месяцам:")
    print(monthly_losses)

    # Сравнение с общими результатами
    df['month'] = pd.to_datetime(df['exit_time']).dt.to_period('M')
    monthly_all = df.groupby('month').agg({
        'pnl_pct': ['count', 'sum']
    })
    monthly_all.columns = ['Total_Trades', 'Total_PnL_%']

    print(f"\n   Месяцы с наибольшими убытками:")
    worst_months = monthly_losses.nsmallest(5, 'Total_Loss_%')
    print(worst_months)

if __name__ == "__main__":
    analyze_losses()
