"""
Генератор синтетических M5/M15 данных для тестирования скальпинг стратегии
Создает реалистичные движения с трендами, консолидациями и разворотами
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_realistic_scalping_data(
    start_price=2650.0,
    num_candles=5000,
    timeframe_minutes=15,
    volatility=0.0005,  # Меньше чем для H1
    trend_strength=0.3,
    noise_level=0.4
):
    """
    Генерация реалистичных M5/M15 данных для скальпинга

    Args:
        start_price: Начальная цена (например, XAUUSD ~2650)
        num_candles: Количество свечей (5000 для ~52 дней M15)
        timeframe_minutes: Таймфрейм в минутах (5, 15, 30)
        volatility: Волатильность (меньше для скальпинга)
        trend_strength: Сила тренда (0.3 = умеренный)
        noise_level: Уровень шума (0.4 = средний)
    """

    print(f"\n{'='*80}")
    print(f"🎲 ГЕНЕРАЦИЯ СИНТЕТИЧЕСКИХ ДАННЫХ ДЛЯ СКАЛЬПИНГА")
    print(f"{'='*80}")
    print(f"   Начальная цена: {start_price:.2f}")
    print(f"   Свечей: {num_candles}")
    print(f"   Таймфрейм: M{timeframe_minutes}")
    print(f"   Волатильность: {volatility:.4f}")
    print(f"   Сила тренда: {trend_strength}")
    print(f"   Шум: {noise_level}")

    # Создаем временную шкалу (пропускаем выходные)
    dates = []
    current_date = datetime(2024, 1, 1, 0, 0)

    while len(dates) < num_candles:
        # Пропускаем выходные (суббота=5, воскресенье=6)
        if current_date.weekday() < 5:
            dates.append(current_date)
        current_date += timedelta(minutes=timeframe_minutes)

    # Генерация базового тренда
    trend = np.zeros(num_candles)
    current_trend = 0
    trend_duration = 0

    for i in range(num_candles):
        if trend_duration <= 0:
            # Новый тренд
            current_trend = np.random.choice([-1, 0, 1], p=[0.3, 0.2, 0.5])  # Чаще вверх
            trend_duration = np.random.randint(20, 100)  # Короче для скальпинга

        trend[i] = current_trend * trend_strength
        trend_duration -= 1

    # Добавляем циклические паттерны (типа London/NY сессий)
    cycle = np.sin(np.arange(num_candles) * 2 * np.pi / (24 * 60 / timeframe_minutes)) * 0.2

    # Генерация цен
    prices = np.zeros(num_candles)
    prices[0] = start_price

    for i in range(1, num_candles):
        # Базовое движение = тренд + цикл + шум
        base_move = (trend[i] + cycle[i] + np.random.randn() * noise_level) * volatility
        prices[i] = prices[i-1] * (1 + base_move)

    # Генерация OHLC из цен
    data = []

    for i in range(num_candles):
        close_price = prices[i]

        # Волатильность для свечи
        candle_volatility = start_price * volatility * (1 + np.random.rand() * 0.5)

        # Open: около предыдущего close
        if i == 0:
            open_price = close_price
        else:
            open_price = prices[i-1] + np.random.randn() * candle_volatility * 0.3

        # High/Low с учетом направления свечи
        if close_price >= open_price:
            # Бычья свеча
            high = max(open_price, close_price) + abs(np.random.randn()) * candle_volatility * 0.5
            low = min(open_price, close_price) - abs(np.random.randn()) * candle_volatility * 0.3
        else:
            # Медвежья свеча
            high = max(open_price, close_price) + abs(np.random.randn()) * candle_volatility * 0.3
            low = min(open_price, close_price) - abs(np.random.randn()) * candle_volatility * 0.5

        # Volume (выше в активные часы)
        hour = dates[i].hour
        if hour in [8, 9, 10, 13, 14, 15]:  # London/NY overlap
            base_volume = np.random.randint(8000, 15000)
        elif hour in [7, 11, 12, 16, 17, 18, 19, 20]:  # Active sessions
            base_volume = np.random.randint(5000, 10000)
        else:  # Quiet hours
            base_volume = np.random.randint(1000, 5000)

        data.append({
            'datetime': dates[i],
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': base_volume
        })

    # Создаем DataFrame
    df = pd.DataFrame(data)
    df = df.set_index('datetime')

    # Добавляем рыночные часы (важно для скальпинга)
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    print(f"\n✅ Сгенерировано {len(df)} свечей")
    print(f"   Период: {df.index[0]} - {df.index[-1]}")
    print(f"   Цена: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f}")
    print(f"   Min/Max: {df['low'].min():.2f} / {df['high'].max():.2f}")
    print(f"   Изменение: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:+.2f}%")

    # Статистика по часам
    print(f"\n⏰ Распределение свечей по часам:")
    hourly = df.groupby(df.index.hour).size()
    for hour in sorted(hourly.index):
        count = hourly[hour]
        is_active = "🔥" if hour in [8, 9, 10, 13, 14, 15] else "  "
        bar = "█" * int(count / hourly.max() * 20)
        print(f"   {hour:02d}:00 {is_active} {bar} {count}")

    return df


def add_scalping_patterns(df, pattern_frequency=0.15):
    """
    Добавляет паттерны идеальные для скальпинга

    Args:
        df: DataFrame с OHLC
        pattern_frequency: Частота паттернов (0.15 = 15% свечей)
    """

    print(f"\n🎯 Добавление скальпинг паттернов...")

    df_modified = df.copy()
    num_patterns = int(len(df) * pattern_frequency)
    pattern_indices = np.random.choice(df.index[50:-50], size=num_patterns, replace=False)

    patterns_added = {
        'bull_flag': 0,
        'bear_flag': 0,
        'bull_pennant': 0,
        'bear_pennant': 0,
        'liquidity_sweep': 0
    }

    for idx in pattern_indices:
        pattern_type = np.random.choice([
            'bull_flag', 'bear_flag', 'bull_pennant', 'bear_pennant', 'liquidity_sweep'
        ])

        i = df.index.get_loc(idx)

        if pattern_type == 'bull_flag':
            # Бычий флаг: сильное движение вверх + консолидация
            for j in range(i-5, i):
                df_modified.loc[df.index[j], 'close'] = df.iloc[j]['close'] * 1.002  # +0.2%
            for j in range(i, i+3):
                df_modified.loc[df.index[j], 'close'] = df.iloc[i-1]['close'] * (1 + np.random.randn() * 0.0003)
            patterns_added['bull_flag'] += 1

        elif pattern_type == 'bear_flag':
            # Медвежий флаг
            for j in range(i-5, i):
                df_modified.loc[df.index[j], 'close'] = df.iloc[j]['close'] * 0.998  # -0.2%
            for j in range(i, i+3):
                df_modified.loc[df.index[j], 'close'] = df.iloc[i-1]['close'] * (1 + np.random.randn() * 0.0003)
            patterns_added['bear_flag'] += 1

        elif pattern_type == 'liquidity_sweep':
            # Sweep: ложный пробой + разворот
            if np.random.rand() > 0.5:
                # Бычий sweep
                df_modified.loc[df.index[i], 'low'] = df.iloc[i-10:i]['low'].min() * 0.999
                df_modified.loc[df.index[i], 'close'] = df.iloc[i]['open'] * 1.001
            else:
                # Медвежий sweep
                df_modified.loc[df.index[i], 'high'] = df.iloc[i-10:i]['high'].max() * 1.001
                df_modified.loc[df.index[i], 'close'] = df.iloc[i]['open'] * 0.999
            patterns_added['liquidity_sweep'] += 1

    print(f"   Добавлено паттернов:")
    for pattern, count in patterns_added.items():
        if count > 0:
            print(f"      - {pattern}: {count}")

    return df_modified


def save_synthetic_data(df, filename=None):
    """Сохранить синтетические данные в CSV"""

    if filename is None:
        tf = "M15"  # По умолчанию
        filename = f"XAUUSD_SYNTHETIC_{tf}_{len(df)}candles.csv"

    # Подготовка для сохранения
    df_save = df.copy()
    df_save['datetime'] = df_save.index
    df_save = df_save[['datetime', 'open', 'high', 'low', 'close', 'volume']]
    df_save.to_csv(filename, index=False)

    print(f"\n💾 Данные сохранены: {filename}")
    return filename


def main():
    """Генерация синтетических данных для скальпинга"""

    # Генерируем базовые данные
    df = generate_realistic_scalping_data(
        start_price=2650.0,
        num_candles=5000,  # ~52 дня для M15
        timeframe_minutes=15,
        volatility=0.0005,  # Умеренная волатильность
        trend_strength=0.3,
        noise_level=0.4
    )

    # Добавляем паттерны для скальпинга
    df = add_scalping_patterns(df, pattern_frequency=0.15)

    # Сохраняем
    filename = save_synthetic_data(df)

    print(f"\n{'='*80}")
    print(f"✅ ГОТОВО!")
    print(f"{'='*80}")
    print(f"\n💡 Теперь запустите backtest:")
    print(f"   python scalping_backtest.py --file {filename} --tp1 5 --tp2 10 --tp3 15")
    print(f"\n   Или с агрессивными настройками:")
    print(f"   python scalping_backtest.py --file {filename} --tp1 3 --tp2 7 --tp3 12")

    return df, filename


if __name__ == "__main__":
    df, filename = main()
