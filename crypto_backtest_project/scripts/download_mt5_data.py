"""
Автоматическая загрузка данных из MT5
Сохраняет в CSV для использования в backtesting
"""

import MetaTrader5 as mt5
from mt5_data_downloader import MT5DataDownloader
from datetime import datetime, timedelta
import argparse


def download_for_backtest(symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1, days=800):
    """
    Загрузить данные для бэктестинга

    Args:
        symbol: Символ (XAUUSD, EURUSD, и т.д.)
        timeframe: Таймфрейм MT5
        days: Количество дней истории
    """
    print("\n" + "="*80)
    print(f"📥 ЗАГРУЗКА ДАННЫХ ДЛЯ БЭКТЕСТИНГА")
    print("="*80)
    print(f"   Символ: {symbol}")
    print(f"   Период: {days} дней")

    # Создаем загрузчик
    downloader = MT5DataDownloader(symbol=symbol, timeframe=timeframe)

    # Подключаемся
    if not downloader.connect():
        print("\n❌ Не удалось подключиться к MT5")
        return False

    # Рассчитываем даты
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)

    print(f"\n📅 Загрузка данных:")
    print(f"   От: {from_date.strftime('%Y-%m-%d')}")
    print(f"   До: {to_date.strftime('%Y-%m-%d')}")

    # Загружаем
    df = downloader.download_history(from_date=from_date, to_date=to_date)

    if df is None:
        print("\n❌ Не удалось загрузить данные")
        downloader.disconnect()
        return False

    # Генерируем имя файла
    filename = f"../{symbol}_1H_MT5_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv"

    # Сохраняем
    print(f"\n💾 Сохранение данных...")
    downloader.save_to_csv(df, filename)

    # Статистика
    print(f"\n📊 Статистика:")
    print(f"   Всего свечей: {len(df)}")
    print(f"   Период: {df.index[0]} - {df.index[-1]}")
    print(f"   Первая цена: {df['close'].iloc[0]:.2f}")
    print(f"   Последняя цена: {df['close'].iloc[-1]:.2f}")
    print(f"   Min цена: {df['low'].min():.2f}")
    print(f"   Max цена: {df['high'].max():.2f}")

    # Отключаемся
    downloader.disconnect()

    print("\n✅ Готово! Файл сохранен: " + filename)
    print("💡 Теперь можете запустить backtest скрипты")

    return True


def download_multiple_periods(symbol='XAUUSD'):
    """Загрузить несколько периодов"""

    periods = [
        ('1_month', 30),
        ('3_months', 90),
        ('6_months', 180),
        ('1_year', 365),
    ]

    print("\n" + "="*80)
    print(f"📥 ЗАГРУЗКА НЕСКОЛЬКИХ ПЕРИОДОВ ДЛЯ {symbol}")
    print("="*80)

    downloader = MT5DataDownloader(symbol=symbol, timeframe=mt5.TIMEFRAME_H1)

    if not downloader.connect():
        print("\n❌ Не удалось подключиться к MT5")
        return

    for period_name, days in periods:
        print(f"\n{'='*80}")
        print(f"📥 Загрузка: {period_name} ({days} дней)")
        print(f"{'='*80}")

        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        df = downloader.download_history(from_date=from_date, to_date=to_date)

        if df is not None:
            filename = f"./{symbol}_{period_name}_MT5.csv"
            downloader.save_to_csv(df, filename)
            print(f"✅ Сохранено: {filename} ({len(df)} свечей)")
        else:
            print(f"❌ Не удалось загрузить {period_name}")

    downloader.disconnect()

    print("\n" + "="*80)
    print("✅ ВСЕ ПЕРИОДЫ ЗАГРУЖЕНЫ!")
    print("="*80)


def download_custom_range(symbol='XAUUSD', from_str=None, to_str=None):
    """
    Загрузить данные за произвольный период

    Args:
        symbol: Символ
        from_str: Дата начала в формате 'YYYY-MM-DD'
        to_str: Дата окончания в формате 'YYYY-MM-DD'
    """
    print("\n" + "="*80)
    print(f"📥 ЗАГРУЗКА ДАННЫХ ЗА ПРОИЗВОЛЬНЫЙ ПЕРИОД")
    print("="*80)

    # Парсим даты
    if from_str:
        from_date = datetime.strptime(from_str, '%Y-%m-%d')
    else:
        from_date = datetime.now() - timedelta(days=800)

    if to_str:
        to_date = datetime.strptime(to_str, '%Y-%m-%d')
    else:
        to_date = datetime.now()

    print(f"   Символ: {symbol}")
    print(f"   От: {from_date.strftime('%Y-%m-%d')}")
    print(f"   До: {to_date.strftime('%Y-%m-%d')}")

    # Загружаем
    downloader = MT5DataDownloader(symbol=symbol, timeframe=mt5.TIMEFRAME_H1)

    if not downloader.connect():
        print("\n❌ Не удалось подключиться к MT5")
        return

    df = downloader.download_history(from_date=from_date, to_date=to_date)

    if df is not None:
        filename = f"../{symbol}_custom_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv"
        downloader.save_to_csv(df, filename)
        print(f"\n✅ Загружено {len(df)} свечей")
        print(f"✅ Сохранено: {filename}")
    else:
        print("\n❌ Не удалось загрузить данные")

    downloader.disconnect()


def main():
    """Main entry point with command line arguments"""

    parser = argparse.ArgumentParser(description='Download MT5 data for backtesting')

    parser.add_argument('--symbol', type=str, default='XAUUSD',
                        help='Symbol to download (default: XAUUSD)')

    parser.add_argument('--days', type=int, default=365,
                        help='Number of days to download (default: 365)')

    parser.add_argument('--multiple', action='store_true',
                        help='Download multiple periods (1m, 3m, 6m, 1y)')

    parser.add_argument('--from', type=str, dest='from_date',
                        help='Start date (YYYY-MM-DD)')

    parser.add_argument('--to', type=str, dest='to_date',
                        help='End date (YYYY-MM-DD)')

    args = parser.parse_args()

    try:
        if args.multiple:
            # Загрузить несколько периодов
            download_multiple_periods(symbol=args.symbol)

        elif args.from_date or args.to_date:
            # Загрузить произвольный период
            download_custom_range(symbol=args.symbol,
                                  from_str=args.from_date,
                                  to_str=args.to_date)

        else:
            # Загрузить один период
            download_for_backtest(symbol=args.symbol,
                                  timeframe=mt5.TIMEFRAME_H1,
                                  days=args.days)

    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Примеры использования:
    #
    # 1. Загрузить последний год XAUUSD:
    #    python download_mt5_data.py
    #
    # 2. Загрузить последние 30 дней EURUSD:
    #    python download_mt5_data.py --symbol EURUSD --days 30
    #
    # 3. Загрузить несколько периодов:
    #    python download_mt5_data.py --multiple
    #
    # 4. Загрузить с определенной даты:
    #    python download_mt5_data.py --from 2024-01-01 --to 2024-12-31
    #
    main()
