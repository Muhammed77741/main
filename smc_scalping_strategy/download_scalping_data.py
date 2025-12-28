"""
Скачивание M5/M15 данных для скальпинг бэктеста
"""

import sys
sys.path.append('../smc_trading_strategy')

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd


def download_scalping_data(symbol='XAUUSD', timeframe=mt5.TIMEFRAME_M15, days=30):
    """
    Скачать M5/M15 данные для скальпинг тестов

    Args:
        symbol: Символ (XAUUSD, EURUSD, etc.)
        timeframe: mt5.TIMEFRAME_M5 или mt5.TIMEFRAME_M15
        days: Количество дней
    """

    print("\n" + "="*80)
    print(f"📥 СКАЧИВАНИЕ ДАННЫХ ДЛЯ СКАЛЬПИНГА")
    print("="*80)
    print(f"   Символ: {symbol}")
    print(f"   Таймфрейм: {'M5' if timeframe == mt5.TIMEFRAME_M5 else 'M15'}")
    print(f"   Период: {days} дней")

    # Подключение к MT5
    print("\n🔌 Подключение к MT5...")
    if not mt5.initialize():
        print(f"❌ Ошибка: {mt5.last_error()}")
        return False

    print("✅ Подключено")

    # Проверка символа
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"❌ Символ {symbol} не найден")
        mt5.shutdown()
        return False

    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)

    # Даты
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)

    print(f"\n📅 Период:")
    print(f"   От: {from_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"   До: {to_date.strftime('%Y-%m-%d %H:%M')}")

    # Скачивание
    print(f"\n📥 Скачивание...")

    import pytz
    utc_from = from_date.replace(tzinfo=pytz.UTC)
    utc_to = to_date.replace(tzinfo=pytz.UTC)

    rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)

    if rates is None or len(rates) == 0:
        print(f"❌ Не удалось скачать: {mt5.last_error()}")
        mt5.shutdown()
        return False

    # Конвертация в DataFrame
    df = pd.DataFrame(rates)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df = df.set_index('datetime')

    df = df.rename(columns={
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'tick_volume': 'volume'
    })

    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Добавляем market hours
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    print(f"✅ Скачано {len(df)} свечей")

    # Сохранение
    tf_str = 'M5' if timeframe == mt5.TIMEFRAME_M5 else 'M15'
    filename = f"{symbol}_{tf_str}_{days}days.csv"

    df_save = df.copy()
    df_save['datetime'] = df_save.index
    df_save = df_save[['datetime', 'open', 'high', 'low', 'close', 'volume']]
    df_save.to_csv(filename, index=False)

    print(f"💾 Сохранено: {filename}")

    # Статистика
    print(f"\n📊 Статистика:")
    print(f"   Период: {df.index[0]} - {df.index[-1]}")
    print(f"   Свечей: {len(df)}")
    print(f"   Первая цена: {df['close'].iloc[0]:.2f}")
    print(f"   Последняя цена: {df['close'].iloc[-1]:.2f}")
    print(f"   Min: {df['low'].min():.2f}")
    print(f"   Max: {df['high'].max():.2f}")

    # Распределение по часам
    print(f"\n⏰ Распределение по часам:")
    hourly = df.groupby(df.index.hour).size()
    for hour, count in hourly.items():
        bar = "█" * int(count / hourly.max() * 30)
        print(f"   {hour:02d}:00 {bar} {count}")

    mt5.shutdown()

    print(f"\n✅ Готово! Теперь запустите:")
    print(f"   python scalping_backtest.py --file {filename} --tp1 5 --tp2 10 --tp3 15")

    return True


def download_multiple_timeframes(symbol='XAUUSD', days=30):
    """Скачать и M5 и M15 одновременно"""

    print("\n" + "="*80)
    print(f"📥 СКАЧИВАНИЕ M5 И M15 ДЛЯ {symbol}")
    print("="*80)

    # M5
    print("\n1️⃣ Скачивание M5 данных...")
    download_scalping_data(symbol=symbol, timeframe=mt5.TIMEFRAME_M5, days=days)

    # M15
    print("\n2️⃣ Скачивание M15 данных...")
    download_scalping_data(symbol=symbol, timeframe=mt5.TIMEFRAME_M15, days=days)

    print("\n" + "="*80)
    print("✅ ОБА ТАЙМФРЕЙМА СКАЧАНЫ!")
    print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Download M5/M15 data for scalping')

    parser.add_argument('--symbol', type=str, default='XAUUSD',
                        help='Symbol (default: XAUUSD)')

    parser.add_argument('--days', type=int, default=30,
                        help='Number of days (default: 30)')

    parser.add_argument('--timeframe', type=str, default='M15',
                        choices=['M5', 'M15', 'both'],
                        help='Timeframe: M5, M15, or both (default: M15)')

    args = parser.parse_args()

    # Determine timeframe
    if args.timeframe == 'both':
        download_multiple_timeframes(symbol=args.symbol, days=args.days)
    elif args.timeframe == 'M5':
        download_scalping_data(symbol=args.symbol, timeframe=mt5.TIMEFRAME_M5, days=args.days)
    else:  # M15
        download_scalping_data(symbol=args.symbol, timeframe=mt5.TIMEFRAME_M15, days=args.days)
