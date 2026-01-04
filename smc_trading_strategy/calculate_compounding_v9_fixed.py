"""
Расчет прибыли V9 с компаундингом (ИСПРАВЛЕННАЯ ВЕРСИЯ)
Правильный расчет: лот растет пропорционально балансу, не зависит от цены
"""

import pandas as pd
import numpy as np

# Параметры
INITIAL_DEPOSIT = 500  # $500
LEVERAGE = 50  # 50x
MARGIN_USAGE = 0.5  # 50% маржи (безопасно)

# Золото XAUUSD
# 1 лот = 100 унций
# 1 пункт при 1 лоте = $1
# Средняя цена ~2400, контракт = 240,000
# Маржа с 50x = 240,000 / 50 = $4,800 на 1 лот

AVG_PRICE = 2400  # Средняя цена золота
CONTRACT_SIZE = AVG_PRICE * 100  # $240,000
MARGIN_PER_LOT = CONTRACT_SIZE / LEVERAGE  # $4,800 на 1 лот

def calculate_lot_from_balance(balance, margin_usage=0.5):
    """
    Рассчитать размер лота на основе баланса
    Лот растет пропорционально балансу!

    Args:
        balance: Текущий баланс
        margin_usage: Процент использования маржи

    Returns:
        Размер лота
    """
    available_margin = balance * margin_usage
    lot_size = available_margin / MARGIN_PER_LOT
    return lot_size

def main():
    """Main calculation"""

    # Загрузить результаты V9
    print(f"\n📂 Загрузка результатов V9...")
    trades_df = pd.read_csv('backtest_v9_bigger_targets_results.csv')
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
    trades_df = trades_df.sort_values('entry_time')

    total_pnl_pct = trades_df['pnl_pct'].sum()
    total_points = trades_df['pnl_points'].sum()
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    win_rate = wins / len(trades_df) * 100

    print(f"   Всего сделок: {len(trades_df)}")
    print(f"   Период: {trades_df['entry_time'].min().strftime('%Y-%m-%d')} - {trades_df['exit_time'].max().strftime('%Y-%m-%d')}")
    print(f"   V9 PnL: {total_pnl_pct:+.2f}% | Points: {total_points:+.1f}п | WR: {win_rate:.1f}%")

    # 1. ФИКСИРОВАННЫЙ ЛОТ
    print(f"\n{'='*100}")
    print(f"💵 СИМУЛЯЦИЯ #1: ФИКСИРОВАННЫЙ ЛОТ (без реинвестирования)")
    print(f"{'='*100}")

    initial_lot = calculate_lot_from_balance(INITIAL_DEPOSIT, MARGIN_USAGE)
    print(f"   Начальный депозит: ${INITIAL_DEPOSIT:,.2f}")
    print(f"   Фиксированный лот: {initial_lot:.4f}")
    print(f"   Leverage: {LEVERAGE}x | Использование маржи: {MARGIN_USAGE*100:.0f}%\n")

    balance_fixed = INITIAL_DEPOSIT
    balance_history_fixed = [balance_fixed]

    for idx, trade in trades_df.iterrows():
        pnl_points = trade['pnl_points']

        # 1 пункт = $1 при 1 лоте
        # При 0.052 лота: 1 пункт = $0.052
        profit_usd = pnl_points * initial_lot
        balance_fixed += profit_usd
        balance_history_fixed.append(balance_fixed)

        if (idx + 1) <= 5 or (idx + 1) % 50 == 0:
            print(f"   Сделка #{idx+1}: Лот {initial_lot:.4f} | "
                  f"{pnl_points:+.1f}п → ${profit_usd:+.2f} | "
                  f"Баланс: ${balance_fixed:,.2f}")

    profit_fixed = balance_fixed - INITIAL_DEPOSIT
    roi_fixed = (profit_fixed / INITIAL_DEPOSIT) * 100

    print(f"\n   ✅ РЕЗУЛЬТАТ:")
    print(f"   Финальный баланс: ${balance_fixed:,.2f}")
    print(f"   Прибыль: ${profit_fixed:+,.2f}")
    print(f"   ROI: {roi_fixed:+.2f}%")

    # 2. КОМПАУНДИНГ
    print(f"\n{'='*100}")
    print(f"🚀 СИМУЛЯЦИЯ #2: КОМПАУНДИНГ (реинвестирование прибыли)")
    print(f"{'='*100}")
    print(f"   Начальный депозит: ${INITIAL_DEPOSIT:,.2f}")
    print(f"   Начальный лот: {initial_lot:.4f}")
    print(f"   Leverage: {LEVERAGE}x | Использование маржи: {MARGIN_USAGE*100:.0f}%")
    print(f"   📈 Лот РАСТЕТ пропорционально балансу!\n")

    balance_compound = INITIAL_DEPOSIT
    balance_history_compound = [balance_compound]
    lot_history = []

    for idx, trade in trades_df.iterrows():
        pnl_points = trade['pnl_points']

        # Рассчитать лот на основе ТЕКУЩЕГО баланса
        current_lot = calculate_lot_from_balance(balance_compound, MARGIN_USAGE)
        lot_history.append(current_lot)

        # Прибыль в долларах
        profit_usd = pnl_points * current_lot

        # Обновить баланс
        balance_compound += profit_usd
        balance_history_compound.append(balance_compound)

        if (idx + 1) <= 5 or (idx + 1) % 50 == 0:
            print(f"   Сделка #{idx+1}: Лот {current_lot:.4f} | "
                  f"{pnl_points:+.1f}п → ${profit_usd:+.2f} | "
                  f"Баланс: ${balance_compound:,.2f}")

    profit_compound = balance_compound - INITIAL_DEPOSIT
    roi_compound = (profit_compound / INITIAL_DEPOSIT) * 100

    print(f"\n   ✅ РЕЗУЛЬТАТ:")
    print(f"   Финальный баланс: ${balance_compound:,.2f}")
    print(f"   Финальный лот: {lot_history[-1]:.4f}")
    print(f"   Прибыль: ${profit_compound:+,.2f}")
    print(f"   ROI: {roi_compound:+.2f}%")

    # 3. СРАВНЕНИЕ
    print(f"\n{'='*100}")
    print(f"📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print(f"{'='*100}")

    print(f"\n   ФИКСИРОВАННЫЙ ЛОТ:")
    print(f"   └─ Лот: {initial_lot:.4f} (не меняется)")
    print(f"   └─ Финальный баланс: ${balance_fixed:,.2f}")
    print(f"   └─ ROI: {roi_fixed:+.2f}%")

    print(f"\n   КОМПАУНДИНГ:")
    print(f"   └─ Начальный лот: {initial_lot:.4f}")
    print(f"   └─ Финальный лот: {lot_history[-1]:.4f} ({lot_history[-1]/initial_lot:.2f}x)")
    print(f"   └─ Финальный баланс: ${balance_compound:,.2f}")
    print(f"   └─ ROI: {roi_compound:+.2f}%")

    difference = profit_compound - profit_fixed
    multiplier = balance_compound / balance_fixed

    print(f"\n   💎 ПРЕИМУЩЕСТВО КОМПАУНДИНГА:")
    print(f"   └─ Дополнительная прибыль: ${difference:+,.2f}")
    print(f"   └─ Увеличение баланса в {multiplier:.2f}x раз")
    print(f"   └─ Разница в ROI: {roi_compound - roi_fixed:+.2f}%")

    # 4. РОСТ ЛОТА
    print(f"\n{'='*100}")
    print(f"📈 ДИНАМИКА РОСТА ПОЗИЦИИ (Компаундинг)")
    print(f"{'='*100}")

    milestones = [0, len(trades_df) // 4, len(trades_df) // 2, 3 * len(trades_df) // 4, len(trades_df) - 1]
    for i, milestone in enumerate(milestones):
        if milestone < len(lot_history):
            balance = balance_history_compound[milestone + 1]
            lot = lot_history[milestone]
            trade = trades_df.iloc[milestone]
            pct_progress = (milestone + 1) / len(trades_df) * 100

            print(f"   [{pct_progress:5.1f}%] Сделка #{milestone+1:3d}: "
                  f"Баланс ${balance:8,.2f} | "
                  f"Лот {lot:.4f} ({lot/initial_lot:4.2f}x) | "
                  f"{trade['entry_time'].strftime('%Y-%m-%d')}")

    # 5. MAX DRAWDOWN
    balance_series = pd.Series(balance_history_compound)
    running_max = balance_series.cummax()
    drawdown = balance_series - running_max
    max_dd = drawdown.min()
    max_dd_pct = (max_dd / running_max[drawdown.idxmin()]) * 100 if running_max[drawdown.idxmin()] > 0 else 0
    max_dd_idx = drawdown.idxmin()

    print(f"\n{'='*100}")
    print(f"⚠️  РИСКИ И ПРОСАДКИ")
    print(f"{'='*100}")
    print(f"   Max Drawdown: ${max_dd:.2f} ({max_dd_pct:.2f}%)")
    print(f"   Порог ликвидации (50% потеря с {LEVERAGE}x): ~${INITIAL_DEPOSIT * 0.5:.2f}")

    if max_dd_idx > 0 and max_dd_idx < len(trades_df):
        dd_trade = trades_df.iloc[max_dd_idx - 1]
        print(f"   Худшая просадка на сделке #{max_dd_idx} ({dd_trade['exit_time'].strftime('%Y-%m-%d')})")

    # 6. ВРЕМЕННЫЕ МЕТРИКИ
    duration_days = (trades_df['exit_time'].max() - trades_df['entry_time'].min()).days
    duration_months = duration_days / 30.44

    monthly_profit_fixed = profit_fixed / duration_months
    monthly_profit_compound = profit_compound / duration_months
    monthly_roi_fixed = (roi_fixed / duration_months)
    monthly_roi_compound = (roi_compound / duration_months)

    print(f"\n{'='*100}")
    print(f"📅 ВРЕМЕННЫЕ МЕТРИКИ")
    print(f"{'='*100}")
    print(f"   Период тестирования: {duration_days} дней ({duration_months:.1f} месяцев)")
    print(f"   Всего сделок: {len(trades_df)} (в среднем {len(trades_df)/duration_months:.1f} сделок/месяц)")

    print(f"\n   ФИКСИРОВАННЫЙ ЛОТ:")
    print(f"   └─ Прибыль в месяц: ${monthly_profit_fixed:+.2f}/мес")
    print(f"   └─ ROI в месяц: {monthly_roi_fixed:+.2f}%/мес")

    print(f"\n   КОМПАУНДИНГ:")
    print(f"   └─ Прибыль в месяц: ${monthly_profit_compound:+.2f}/мес")
    print(f"   └─ ROI в месяц: {monthly_roi_compound:+.2f}%/мес")

    # 7. ЭКСТРАПОЛЯЦИЯ НА 1 ГОД
    if duration_months > 0:
        yearly_multiplier_fixed = (1 + monthly_roi_fixed / 100) ** 12
        yearly_balance_fixed = INITIAL_DEPOSIT * yearly_multiplier_fixed

        # Компаундинг - используем экспоненциальный рост
        monthly_growth_compound = (balance_compound / INITIAL_DEPOSIT) ** (1 / duration_months)
        yearly_balance_compound = INITIAL_DEPOSIT * (monthly_growth_compound ** 12)

        print(f"\n{'='*100}")
        print(f"📊 ПРОГНОЗ НА 1 ГОД (экстраполяция)")
        print(f"{'='*100}")
        print(f"   ⚠️  ВНИМАНИЕ: Прогноз основан на бэктесте, реальная торговля может отличаться!")

        print(f"\n   ФИКСИРОВАННЫЙ ЛОТ (12 месяцев):")
        print(f"   └─ Ожидаемый баланс: ${yearly_balance_fixed:,.2f}")
        print(f"   └─ Прибыль: ${yearly_balance_fixed - INITIAL_DEPOSIT:+,.2f}")
        print(f"   └─ ROI: {(yearly_balance_fixed / INITIAL_DEPOSIT - 1) * 100:+.2f}%")

        print(f"\n   КОМПАУНДИНГ (12 месяцев):")
        print(f"   └─ Ожидаемый баланс: ${yearly_balance_compound:,.2f}")
        print(f"   └─ Прибыль: ${yearly_balance_compound - INITIAL_DEPOSIT:+,.2f}")
        print(f"   └─ ROI: {(yearly_balance_compound / INITIAL_DEPOSIT - 1) * 100:+.2f}%")

        print(f"\n   💎 Преимущество компаундинга за год: ${yearly_balance_compound - yearly_balance_fixed:+,.2f}")

    # ИТОГО
    print(f"\n{'='*100}")
    print(f"✅ ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print(f"{'='*100}")
    print(f"   Начальный депозит: ${INITIAL_DEPOSIT:,.2f}")
    print(f"   Leverage: {LEVERAGE}x | Margin usage: {MARGIN_USAGE*100:.0f}%")
    print(f"   Период: {duration_months:.1f} месяцев | Сделок: {len(trades_df)}")
    print(f"\n   С КОМПАУНДИНГОМ:")
    print(f"   └─ Финальный баланс: ${balance_compound:,.2f}")
    print(f"   └─ Прибыль: ${profit_compound:+,.2f}")
    print(f"   └─ ROI: {roi_compound:+.2f}%")
    print(f"   └─ Это в {balance_compound/INITIAL_DEPOSIT:.2f}x раз больше начального депозита!")
    print(f"\n   💡 Лот вырос с {initial_lot:.4f} до {lot_history[-1]:.4f} ({lot_history[-1]/initial_lot:.2f}x)")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    main()
