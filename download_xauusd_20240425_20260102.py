"""
Скачать XAUUSD данные за период 2024-04-25 до 2026-01-02
Использует MT5 для скачивания реальных исторических данных
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'smc_trading_strategy'))

try:
    import MetaTrader5 as mt5
    from mt5_data_downloader import MT5DataDownloader
    from datetime import datetime

    print("\n" + "="*80)
    print("📥 СКАЧИВАНИЕ ДАННЫХ XAUUSD ЗА ПЕРИОД 2024-04-25 - 2026-01-02")
    print("="*80)

    # Target dates
    from_date = datetime(2024, 4, 25)
    to_date = datetime(2026, 1, 2)

    print(f"\n📅 Период:")
    print(f"   От: {from_date.strftime('%Y-%m-%d')}")
    print(f"   До: {to_date.strftime('%Y-%m-%d')}")
    print(f"   Дней: {(to_date - from_date).days}")

    # Create downloader
    downloader = MT5DataDownloader(symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1)

    # Connect
    if not downloader.connect():
        print("\n❌ Не удалось подключиться к MT5")
        print("\n💡 Убедитесь что:")
        print("   1. MT5 установлен и запущен")
        print("   2. У вас есть доступ к истории XAUUSD")
        print("   3. MT5 авторизован на брокере")
        sys.exit(1)

    # Download
    print(f"\n⏳ Скачивание данных...")
    df = downloader.download_history(from_date=from_date, to_date=to_date)

    if df is None:
        print("\n❌ Не удалось загрузить данные")
        downloader.disconnect()
        sys.exit(1)

    # Save
    filename = "XAUUSD_MT5_20240425_20260102.csv"
    print(f"\n💾 Сохранение в {filename}...")
    downloader.save_to_csv(df, filename)

    # Stats
    print(f"\n📊 Статистика:")
    print(f"   Всего свечей: {len(df)}")
    print(f"   Период: {df.index[0]} - {df.index[-1]}")
    print(f"   Первая цена: {df['close'].iloc[0]:.2f}")
    print(f"   Последняя цена: {df['close'].iloc[-1]:.2f}")
    print(f"   Min цена: {df['low'].min():.2f}")
    print(f"   Max цена: {df['high'].max():.2f}")

    # Disconnect
    downloader.disconnect()

    print("\n" + "="*80)
    print("✅ ДАННЫЕ УСПЕШНО СКАЧАНЫ!")
    print("="*80)
    print(f"\n💡 Теперь можно запустить бэктест:")
    print(f"   cd smc_trading_strategy")
    print(f"   python backtest_v3_short_optimized.py --file ../{filename}")
    print("="*80 + "\n")

except ImportError as e:
    print("\n❌ ОШИБКА: MT5 модуль не установлен")
    print(f"   {e}")
    print("\n💡 Решение:")
    print("   1. Установите MT5: pip install MetaTrader5")
    print("   2. Или используйте имеющиеся файлы данных")
    print("   3. Или скачайте данные вручную из TradingView/Investing.com")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
