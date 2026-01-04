"""
Расчет прибыли V9 с компаундингом (реинвестирование)
Сравнение: фиксированный лот vs увеличение позиции после каждой прибыльной сделки
"""

import pandas as pd
import numpy as np

# Параметры пользователя
INITIAL_DEPOSIT = 500  # Начальный депозит $500
LEVERAGE = 50  # Плечо 50x
MARGIN_USAGE = 0.5  # Используем 50% от доступной маржи (безопасно)

# Параметры золота (XAUUSD)
OUNCES_PER_LOT = 100  # 1 лот = 100 унций золота
POINT_VALUE_PER_LOT = 1.0  # 1 пункт при 1 лоте = $1

def calculate_lot_size(balance, current_price, leverage, margin_usage=0.5):
    """
    Рассчитать размер лота на основе баланса

    Args:
        balance: Текущий баланс счета
        current_price: Текущая цена золота
        leverage: Плечо
        margin_usage: Процент использования маржи (0.5 = 50%)

    Returns:
        Размер лота
    """
    # Стоимость 1 лота = цена × 100 унций
    contract_size = current_price * OUNCES_PER_LOT

    # Необходимая маржа для 1 лота
    margin_per_lot = contract_size / leverage

    # Доступная маржа для использования
    available_margin = balance * margin_usage

    # Максимальный размер лота
    lot_size = available_margin / margin_per_lot

    return lot_size

def calculate_profit_in_dollars(pnl_points, lot_size):
    """
    Конвертировать прибыль в пунктах в доллары

    Args:
        pnl_points: Прибыль в пунктах (из бэктеста)
        lot_size: Размер лота

    Returns:
        Прибыль в долларах
    """
    # Для золота: 1 пункт = $1 при 1 лоте
    # Для 0.01 лота: 1 пункт = $0.01
    profit_usd = pnl_points * lot_size
    return profit_usd

def simulate_with_compounding(trades_df, initial_balance, leverage, margin_usage):
    """
    Симуляция торговли с компаундингом
    """
    balance = initial_balance
    balance_history = [balance]
    lot_sizes = []
    profits_usd = []

    print(f"\n{'='*100}")
    print(f"💰 СИМУЛЯЦИЯ С КОМПАУНДИНГОМ (Реинвестирование прибыли)")
    print(f"{'='*100}")
    print(f"   Начальный депозит: ${initial_balance:,.2f}")
    print(f"   Leverage: {leverage}x")
    print(f"   Использование маржи: {margin_usage*100:.0f}%")
    print(f"\n{'='*100}")

    for idx, trade in trades_df.iterrows():
        entry_price = trade['entry_price']
        pnl_points = trade['pnl_points']
        pnl_pct = trade['pnl_pct']

        # Рассчитать текущий размер лота на основе баланса
        lot_size = calculate_lot_size(balance, entry_price, leverage, margin_usage)

        # Рассчитать прибыль в долларах
        profit_usd = calculate_profit_in_dollars(pnl_points, lot_size)

        # Обновить баланс
        balance += profit_usd

        # Сохранить историю
        balance_history.append(balance)
        lot_sizes.append(lot_size)
        profits_usd.append(profit_usd)

        # Показывать каждую 10-ю сделку
        if (idx + 1) % 10 == 0 or idx < 5:
            print(f"   Сделка #{idx+1}: Лот {lot_size:.3f} | "
                  f"Пункты {pnl_points:+.1f}п | "
                  f"Прибыль ${profit_usd:+.2f} | "
                  f"Баланс: ${balance:,.2f}")

    return {
        'final_balance': balance,
        'balance_history': balance_history,
        'lot_sizes': lot_sizes,
        'profits_usd': profits_usd,
        'total_trades': len(trades_df)
    }

def simulate_fixed_lot(trades_df, initial_balance, leverage, margin_usage):
    """
    Симуляция торговли с фиксированным размером лота
    """
    # Рассчитать фиксированный размер лота на основе начального баланса
    avg_price = trades_df['entry_price'].mean()
    fixed_lot = calculate_lot_size(initial_balance, avg_price, leverage, margin_usage)

    balance = initial_balance
    balance_history = [balance]
    profits_usd = []

    print(f"\n{'='*100}")
    print(f"📊 СИМУЛЯЦИЯ С ФИКСИРОВАННЫМ ЛОТОМ (Без реинвестирования)")
    print(f"{'='*100}")
    print(f"   Начальный депозит: ${initial_balance:,.2f}")
    print(f"   Фиксированный лот: {fixed_lot:.3f}")
    print(f"   Leverage: {leverage}x")
    print(f"\n{'='*100}")

    for idx, trade in trades_df.iterrows():
        pnl_points = trade['pnl_points']

        # Прибыль с фиксированным лотом
        profit_usd = calculate_profit_in_dollars(pnl_points, fixed_lot)

        # Обновить баланс
        balance += profit_usd

        # Сохранить историю
        balance_history.append(balance)
        profits_usd.append(profit_usd)

        # Показывать каждую 10-ю сделку
        if (idx + 1) % 10 == 0 or idx < 5:
            print(f"   Сделка #{idx+1}: Лот {fixed_lot:.3f} | "
                  f"Пункты {pnl_points:+.1f}п | "
                  f"Прибыль ${profit_usd:+.2f} | "
                  f"Баланс: ${balance:,.2f}")

    return {
        'final_balance': balance,
        'balance_history': balance_history,
        'fixed_lot': fixed_lot,
        'profits_usd': profits_usd,
        'total_trades': len(trades_df)
    }

def main():
    """Main calculation"""

    # Загрузить результаты V9
    print(f"\n📂 Загрузка результатов V9...")
    trades_df = pd.read_csv('backtest_v9_bigger_targets_results.csv')
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])

    # Сортировать по времени входа
    trades_df = trades_df.sort_values('entry_time')

    print(f"   Всего сделок: {len(trades_df)}")
    print(f"   Период: {trades_df['entry_time'].min()} - {trades_df['exit_time'].max()}")

    # Статистика V9
    total_pnl_pct = trades_df['pnl_pct'].sum()
    total_points = trades_df['pnl_points'].sum()
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    win_rate = wins / len(trades_df) * 100

    print(f"\n   V9 Статистика:")
    print(f"   Total PnL: {total_pnl_pct:+.2f}%")
    print(f"   Total Points: {total_points:+.1f}п")
    print(f"   Win Rate: {win_rate:.1f}%")

    # 1. Симуляция с фиксированным лотом
    fixed_result = simulate_fixed_lot(trades_df, INITIAL_DEPOSIT, LEVERAGE, MARGIN_USAGE)

    # 2. Симуляция с компаундингом
    compound_result = simulate_with_compounding(trades_df, INITIAL_DEPOSIT, LEVERAGE, MARGIN_USAGE)

    # Сравнение результатов
    print(f"\n{'='*100}")
    print(f"📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print(f"{'='*100}")

    print(f"\n   💵 ФИКСИРОВАННЫЙ ЛОТ (без реинвестирования):")
    print(f"   Начальный депозит: ${INITIAL_DEPOSIT:,.2f}")
    print(f"   Фиксированный лот: {fixed_result['fixed_lot']:.3f}")
    print(f"   Финальный баланс: ${fixed_result['final_balance']:,.2f}")
    print(f"   Прибыль: ${fixed_result['final_balance'] - INITIAL_DEPOSIT:+,.2f}")
    print(f"   ROI: {((fixed_result['final_balance'] / INITIAL_DEPOSIT) - 1) * 100:+.2f}%")

    print(f"\n   🚀 КОМПАУНДИНГ (реинвестирование прибыли):")
    print(f"   Начальный депозит: ${INITIAL_DEPOSIT:,.2f}")
    print(f"   Начальный лот: {compound_result['lot_sizes'][0]:.3f}")
    print(f"   Финальный лот: {compound_result['lot_sizes'][-1]:.3f}")
    print(f"   Финальный баланс: ${compound_result['final_balance']:,.2f}")
    print(f"   Прибыль: ${compound_result['final_balance'] - INITIAL_DEPOSIT:+,.2f}")
    print(f"   ROI: {((compound_result['final_balance'] / INITIAL_DEPOSIT) - 1) * 100:+.2f}%")

    # Разница
    difference = compound_result['final_balance'] - fixed_result['final_balance']
    print(f"\n   💎 ПРЕИМУЩЕСТВО КОМПАУНДИНГА:")
    print(f"   Дополнительная прибыль: ${difference:+,.2f}")
    print(f"   Увеличение в {compound_result['final_balance'] / fixed_result['final_balance']:.2f}x раз")

    # График роста лота
    print(f"\n{'='*100}")
    print(f"📈 РОСТ РАЗМЕРА ПОЗИЦИИ (Компаундинг)")
    print(f"{'='*100}")

    milestones = [0, len(trades_df) // 4, len(trades_df) // 2, 3 * len(trades_df) // 4, len(trades_df) - 1]
    for milestone in milestones:
        if milestone < len(compound_result['lot_sizes']):
            balance = compound_result['balance_history'][milestone + 1]
            lot = compound_result['lot_sizes'][milestone]
            trade = trades_df.iloc[milestone]
            print(f"   Сделка #{milestone+1}/{len(trades_df)}: "
                  f"Баланс ${balance:,.2f} | "
                  f"Лот {lot:.3f} | "
                  f"Дата {trade['entry_time'].strftime('%Y-%m-%d')}")

    # Max Drawdown
    balance_series = pd.Series(compound_result['balance_history'])
    running_max = balance_series.cummax()
    drawdown = balance_series - running_max
    max_dd = drawdown.min()
    max_dd_pct = (max_dd / running_max[drawdown.idxmin()]) * 100 if running_max[drawdown.idxmin()] > 0 else 0

    print(f"\n{'='*100}")
    print(f"⚠️  РИСКИ")
    print(f"{'='*100}")
    print(f"   Max Drawdown: ${max_dd:.2f} ({max_dd_pct:.2f}%)")
    print(f"   Ликвидация при потере ~50% с leverage {LEVERAGE}x")
    print(f"   Порог ликвидации: ~${INITIAL_DEPOSIT * 0.5:.2f}")

    # Временные метрики
    duration_days = (trades_df['exit_time'].max() - trades_df['entry_time'].min()).days
    duration_months = duration_days / 30.44

    monthly_profit_fixed = (fixed_result['final_balance'] - INITIAL_DEPOSIT) / duration_months
    monthly_profit_compound = (compound_result['final_balance'] - INITIAL_DEPOSIT) / duration_months

    print(f"\n{'='*100}")
    print(f"📅 ВРЕМЕННЫЕ МЕТРИКИ")
    print(f"{'='*100}")
    print(f"   Период: {duration_days} дней ({duration_months:.1f} месяцев)")
    print(f"   Фиксированный лот - прибыль в месяц: ${monthly_profit_fixed:,.2f}")
    print(f"   Компаундинг - прибыль в месяц: ${monthly_profit_compound:,.2f}")

    print(f"\n{'='*100}")
    print(f"✅ ИТОГО")
    print(f"{'='*100}")
    print(f"   С компаундингом ты заработаешь ${compound_result['final_balance']:,.2f}")
    print(f"   Это в {compound_result['final_balance'] / INITIAL_DEPOSIT:.1f}x раз больше начального депозита!")
    print(f"   ROI: {((compound_result['final_balance'] / INITIAL_DEPOSIT) - 1) * 100:+,.0f}%")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    main()
