"""
Deep analysis of SHORT trades specifically
Find what conditions make SHORT trades successful vs unsuccessful
"""

import pandas as pd
import numpy as np

def analyze_short_trades():
    """Analyze SHORT trades in detail to find optimal parameters"""

    print("\n" + "="*80)
    print("📉 ДЕТАЛЬНЫЙ АНАЛИЗ SHORT СДЕЛОК")
    print("="*80)

    # Load results
    df = pd.read_csv('smc_trading_strategy/backtest_v3_adaptive_results.csv')
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])

    # Separate LONG and SHORT
    short_trades = df[df['direction'] == 'SHORT'].copy()
    long_trades = df[df['direction'] == 'LONG'].copy()

    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   LONG сделок: {len(long_trades)}")
    print(f"   SHORT сделок: {len(short_trades)}")

    # LONG stats
    long_wins = len(long_trades[long_trades['pnl_pct'] > 0])
    long_win_rate = long_wins / len(long_trades) * 100
    long_pnl = long_trades['pnl_pct'].sum()
    long_avg_win = long_trades[long_trades['pnl_pct'] > 0]['pnl_pct'].mean()
    long_avg_loss = long_trades[long_trades['pnl_pct'] <= 0]['pnl_pct'].mean()

    print(f"\n   LONG:")
    print(f"   Win Rate: {long_win_rate:.1f}%")
    print(f"   Total PnL: {long_pnl:+.2f}%")
    print(f"   Avg Win: {long_avg_win:+.2f}%")
    print(f"   Avg Loss: {long_avg_loss:.2f}%")

    # SHORT stats
    short_wins = len(short_trades[short_trades['pnl_pct'] > 0])
    short_win_rate = short_wins / len(short_trades) * 100
    short_pnl = short_trades['pnl_pct'].sum()
    short_avg_win = short_trades[short_trades['pnl_pct'] > 0]['pnl_pct'].mean()
    short_avg_loss = short_trades[short_trades['pnl_pct'] <= 0]['pnl_pct'].mean()

    print(f"\n   SHORT:")
    print(f"   Win Rate: {short_win_rate:.1f}%")
    print(f"   Total PnL: {short_pnl:+.2f}%")
    print(f"   Avg Win: {short_avg_win:+.2f}%")
    print(f"   Avg Loss: {short_avg_loss:.2f}%")

    # 1. SHORT BY REGIME
    print(f"\n{'='*80}")
    print(f"1️⃣  SHORT ПО РЕЖИМУ РЫНКА")
    print(f"{'='*80}")

    for regime in ['TREND', 'RANGE']:
        regime_short = short_trades[short_trades['regime'] == regime]

        if len(regime_short) > 0:
            wins = len(regime_short[regime_short['pnl_pct'] > 0])
            win_rate = wins / len(regime_short) * 100
            total_pnl = regime_short['pnl_pct'].sum()
            avg_win = regime_short[regime_short['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
            losses = regime_short[regime_short['pnl_pct'] <= 0]
            avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0

            print(f"\n   SHORT в {regime}:")
            print(f"   Сделок: {len(regime_short)}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Total PnL: {total_pnl:+.2f}%")
            print(f"   Avg Win: {avg_win:+.2f}%")
            print(f"   Avg Loss: {avg_loss:.2f}%")

    # 2. SHORT BY EXIT TYPE
    print(f"\n{'='*80}")
    print(f"2️⃣  SHORT ПО ТИПУ ВЫХОДА")
    print(f"{'='*80}")

    for exit_type in short_trades['exit_type'].unique():
        et_short = short_trades[short_trades['exit_type'] == exit_type]

        if len(et_short) > 0:
            wins = len(et_short[et_short['pnl_pct'] > 0])
            win_rate = wins / len(et_short) * 100
            total_pnl = et_short['pnl_pct'].sum()
            avg_pnl = et_short['pnl_pct'].mean()

            print(f"\n   SHORT → {exit_type}:")
            print(f"   Сделок: {len(et_short)}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Total PnL: {total_pnl:+.2f}%")
            print(f"   Avg PnL: {avg_pnl:+.2f}%")

    # 3. SUCCESSFUL SHORT PATTERNS
    print(f"\n{'='*80}")
    print(f"3️⃣  УСПЕШНЫЕ SHORT ПАТТЕРНЫ")
    print(f"{'='*80}")

    successful_short = short_trades[short_trades['pnl_pct'] > 0]
    failed_short = short_trades[short_trades['pnl_pct'] <= 0]

    print(f"\n   Успешные SHORT ({len(successful_short)} сделок):")

    # TP достижение
    print(f"\n   TP достижение:")
    for tp in ['tp1_hit', 'tp2_hit', 'tp3_hit']:
        tp_count = successful_short[successful_short[tp] == True].shape[0]
        tp_pct = tp_count / len(successful_short) * 100 if len(successful_short) > 0 else 0
        print(f"   {tp}: {tp_count} ({tp_pct:.1f}%)")

    # Trailing использование
    trailing_count = successful_short[successful_short['trailing_used'] == True].shape[0]
    trailing_pct = trailing_count / len(successful_short) * 100 if len(successful_short) > 0 else 0
    print(f"   Trailing: {trailing_count} ({trailing_pct:.1f}%)")

    # Режим
    print(f"\n   По режиму:")
    for regime in ['TREND', 'RANGE']:
        regime_count = successful_short[successful_short['regime'] == regime].shape[0]
        regime_pct = regime_count / len(successful_short) * 100 if len(successful_short) > 0 else 0
        print(f"   {regime}: {regime_count} ({regime_pct:.1f}%)")

    # Длительность
    avg_duration = successful_short['duration_hours'].mean()
    print(f"\n   Средняя длительность: {avg_duration:.1f}ч")

    print(f"\n   Убыточные SHORT ({len(failed_short)} сделок):")

    # Режим
    print(f"\n   По режиму:")
    for regime in ['TREND', 'RANGE']:
        regime_count = failed_short[failed_short['regime'] == regime].shape[0]
        regime_pct = regime_count / len(failed_short) * 100 if len(failed_short) > 0 else 0
        print(f"   {regime}: {regime_count} ({regime_pct:.1f}%)")

    # Тип выхода
    print(f"\n   По типу выхода:")
    for exit_type in failed_short['exit_type'].unique():
        exit_count = failed_short[failed_short['exit_type'] == exit_type].shape[0]
        exit_pct = exit_count / len(failed_short) * 100 if len(failed_short) > 0 else 0
        print(f"   {exit_type}: {exit_count} ({exit_pct:.1f}%)")

    # Длительность
    avg_duration = failed_short['duration_hours'].mean()
    print(f"\n   Средняя длительность: {avg_duration:.1f}ч")

    # 4. COMPARISON WITH LONG
    print(f"\n{'='*80}")
    print(f"4️⃣  СРАВНЕНИЕ SHORT vs LONG")
    print(f"{'='*80}")

    metrics = {
        'Win Rate': (short_win_rate, long_win_rate),
        'Total PnL': (short_pnl, long_pnl),
        'Avg Win': (short_avg_win, long_avg_win),
        'Avg Loss': (short_avg_loss, long_avg_loss),
        'Total Trades': (len(short_trades), len(long_trades))
    }

    print(f"\n   {'Метрика':<15} {'SHORT':>10} {'LONG':>10} {'Разница':>15}")
    print(f"   {'-'*50}")
    for metric, (short_val, long_val) in metrics.items():
        diff = short_val - long_val
        diff_sign = '+' if diff > 0 else ''
        if 'Rate' in metric or 'PnL' in metric or 'Win' in metric or 'Loss' in metric:
            print(f"   {metric:<15} {short_val:>9.1f}% {long_val:>9.1f}% {diff_sign}{diff:>13.1f}%")
        else:
            print(f"   {metric:<15} {short_val:>10.0f} {long_val:>10.0f} {diff_sign}{diff:>14.0f}")

    # 5. WORST SHORT TRADES
    print(f"\n{'='*80}")
    print(f"5️⃣  ХУДШИЕ SHORT СДЕЛКИ")
    print(f"{'='*80}")

    worst_short = short_trades.nsmallest(10, 'pnl_pct')
    print(f"\n   Top 10 worst SHORT trades:")
    for idx, row in worst_short.iterrows():
        print(f"\n   {row['entry_time']} → {row['exit_time']}")
        print(f"   {row['regime']} | Exit: {row['exit_type']}")
        print(f"   PnL: {row['pnl_pct']:.2f}% | Duration: {row['duration_hours']:.1f}h")

    # 6. RECOMMENDATIONS
    print(f"\n{'='*80}")
    print(f"6️⃣  РЕКОМЕНДАЦИИ ДЛЯ SHORT СДЕЛОК")
    print(f"{'='*80}")

    recommendations = []

    # Analyze RANGE SHORT
    range_short = short_trades[short_trades['regime'] == 'RANGE']
    range_short_losses = range_short[range_short['pnl_pct'] <= 0]

    if len(range_short) > 0:
        range_short_loss_rate = len(range_short_losses) / len(range_short) * 100
        range_short_pnl = range_short['pnl_pct'].sum()

        if range_short_loss_rate > 50 or range_short_pnl < 0:
            recommendations.append({
                'problem': 'SHORT В RANGE НЕ РАБОТАЕТ',
                'stats': f'{len(range_short)} сделок, {range_short_loss_rate:.1f}% убытков, PnL: {range_short_pnl:+.2f}%',
                'solution': 'ОТКЛЮЧИТЬ SHORT в RANGE режиме, торговать SHORT только в TREND'
            })

    # Analyze TREND SHORT
    trend_short = short_trades[short_trades['regime'] == 'TREND']
    trend_short_losses = trend_short[trend_short['pnl_pct'] <= 0]

    if len(trend_short) > 0:
        trend_short_loss_rate = len(trend_short_losses) / len(trend_short) * 100

        if trend_short_loss_rate > 35:
            recommendations.append({
                'problem': 'ДАЖЕ TREND SHORT ИМЕЕТ МНОГО УБЫТКОВ',
                'stats': f'{trend_short_loss_rate:.1f}% убытков в TREND SHORT',
                'solution': 'Использовать более консервативные параметры для SHORT: меньше TP (15/25/40п), быстрее trailing (12п)'
            })

    # Analyze SHORT SL
    short_sl = short_trades[short_trades['exit_type'] == 'SL']
    short_sl_losses = short_sl[short_sl['pnl_pct'] <= 0]

    if len(short_sl) > 0:
        short_sl_loss_rate = len(short_sl_losses) / len(short_sl) * 100
        short_sl_avg_loss = short_sl_losses['pnl_pct'].mean() if len(short_sl_losses) > 0 else 0

        if short_sl_avg_loss < -1.0:
            recommendations.append({
                'problem': 'SHORT SL СЛИШКОМ ДАЛЕКО',
                'stats': f'Средний убыток SHORT SL: {short_sl_avg_loss:.2f}%',
                'solution': 'Уменьшить SL для SHORT или использовать более жесткий breakeven'
            })

    # Compare SHORT in different market conditions
    trend_short_wr = len(trend_short[trend_short['pnl_pct'] > 0]) / len(trend_short) * 100 if len(trend_short) > 0 else 0
    range_short_wr = len(range_short[range_short['pnl_pct'] > 0]) / len(range_short) * 100 if len(range_short) > 0 else 0

    if abs(trend_short_wr - range_short_wr) > 20:
        better_regime = 'TREND' if trend_short_wr > range_short_wr else 'RANGE'
        worse_regime = 'RANGE' if better_regime == 'TREND' else 'TREND'
        recommendations.append({
            'problem': f'SHORT В {worse_regime} ГОРАЗДО ХУЖЕ',
            'stats': f'TREND SHORT: {trend_short_wr:.1f}% WR, RANGE SHORT: {range_short_wr:.1f}% WR',
            'solution': f'Торговать SHORT только в {better_regime} режиме'
        })

    if len(recommendations) > 0:
        print(f"\n   Найдено {len(recommendations)} критичных проблем:\n")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. ⚠️  {rec['problem']}")
            print(f"      📊 {rec['stats']}")
            print(f"      💡 РЕШЕНИЕ: {rec['solution']}")
            print()
    else:
        print(f"\n   ✅ SHORT сделки работают нормально")

    # 7. OPTIMAL SHORT PARAMETERS
    print(f"\n{'='*80}")
    print(f"7️⃣  ОПТИМАЛЬНЫЕ ПАРАМЕТРЫ ДЛЯ SHORT")
    print(f"{'='*80}")

    # Analyze successful SHORT parameters
    if len(successful_short) > 0:
        print(f"\n   На основе {len(successful_short)} успешных SHORT сделок:")

        # Regime preference
        trend_success = len(successful_short[successful_short['regime'] == 'TREND'])
        range_success = len(successful_short[successful_short['regime'] == 'RANGE'])

        print(f"\n   Лучший режим: {'TREND' if trend_success > range_success else 'RANGE'}")
        print(f"     TREND: {trend_success} успешных")
        print(f"     RANGE: {range_success} успешных")

        # Average duration
        avg_duration = successful_short['duration_hours'].mean()
        print(f"\n   Средняя длительность успешных: {avg_duration:.1f}ч")

        # TP hits
        tp1_hits = len(successful_short[successful_short['tp1_hit'] == True])
        tp2_hits = len(successful_short[successful_short['tp2_hit'] == True])
        tp3_hits = len(successful_short[successful_short['tp3_hit'] == True])

        print(f"\n   TP достижение:")
        print(f"     TP1: {tp1_hits}/{len(successful_short)} ({tp1_hits/len(successful_short)*100:.1f}%)")
        print(f"     TP2: {tp2_hits}/{len(successful_short)} ({tp2_hits/len(successful_short)*100:.1f}%)")
        print(f"     TP3: {tp3_hits}/{len(successful_short)} ({tp3_hits/len(successful_short)*100:.1f}%)")

        if tp3_hits / len(successful_short) < 0.2:  # Less than 20% reach TP3
            print(f"\n   💡 TP3 достигается редко - рассмотреть уменьшение TP3 для SHORT")

if __name__ == "__main__":
    analyze_short_trades()
