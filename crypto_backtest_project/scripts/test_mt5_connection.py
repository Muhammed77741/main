"""
Тест подключения к MetaTrader 5
Простой скрипт для проверки что MT5 работает
"""

import MetaTrader5 as mt5
from datetime import datetime


def test_mt5_connection():
    """Тестирование подключения к MT5"""

    print("\n" + "="*80)
    print("🔍 ТЕСТ ПОДКЛЮЧЕНИЯ К MT5")
    print("="*80)

    # 1. Инициализация
    print("\n1️⃣ Инициализация MT5...")
    if not mt5.initialize():
        print(f"   ❌ Ошибка инициализации: {mt5.last_error()}")
        print("\n   💡 Возможные причины:")
        print("      - MT5 терминал не запущен")
        print("      - Вы не на Windows")
        print("      - Модуль не установлен: pip install MetaTrader5")
        return False

    print("   ✅ MT5 инициализирован")

    # 2. Информация о терминале
    print("\n2️⃣ Информация о терминале:")
    terminal_info = mt5.terminal_info()
    if terminal_info:
        print(f"   Компания: {terminal_info.company}")
        print(f"   Название: {terminal_info.name}")
        print(f"   Путь: {terminal_info.path}")
        print(f"   Build: {terminal_info.build}")
        print(f"   Язык: {terminal_info.language}")
    else:
        print("   ⚠️  Не удалось получить информацию о терминале")

    # 3. Информация об аккаунте
    print("\n3️⃣ Информация об аккаунте:")
    account_info = mt5.account_info()
    if account_info:
        print(f"   Логин: {account_info.login}")
        print(f"   Сервер: {account_info.server}")
        print(f"   Баланс: {account_info.balance}")
        print(f"   Валюта: {account_info.currency}")
        print(f"   Тип: {'Demo' if account_info.trade_mode == 1 else 'Real'}")
    else:
        print("   ⚠️  Не авторизован (это нормально)")
        print("   💡 Бот может работать без авторизации, используя открытый терминал")

    # 4. Проверка символа XAUUSD
    print("\n4️⃣ Проверка символа XAUUSD:")
    symbol = 'XAUUSD'

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"   ❌ Символ {symbol} не найден")
        print("\n   💡 Попробуйте другие варианты:")
        print("      - GOLD")
        print("      - XAU/USD")
        print("      - XAUUSD.m")
        print("      - Добавьте XAUUSD в Market Watch в MT5 терминале")

        # Попробуем найти альтернативы
        print("\n   🔍 Поиск альтернативных символов...")
        symbols = mt5.symbols_get()
        gold_symbols = [s.name for s in symbols if 'XAU' in s.name or 'GOLD' in s.name]
        if gold_symbols:
            print(f"   Найдено {len(gold_symbols)} символов с золотом:")
            for sym in gold_symbols[:5]:  # Показываем первые 5
                print(f"      - {sym}")
        else:
            print("   ❌ Символы с золотом не найдены")

        mt5.shutdown()
        return False

    print(f"   ✅ Символ {symbol} найден")
    print(f"   Описание: {symbol_info.description}")
    print(f"   Digits: {symbol_info.digits}")
    print(f"   Point: {symbol_info.point}")
    print(f"   Visible: {symbol_info.visible}")

    # Если не виден - добавляем
    if not symbol_info.visible:
        print(f"\n   ⚠️  Символ не виден в Market Watch, добавляем...")
        if mt5.symbol_select(symbol, True):
            print(f"   ✅ Символ добавлен в Market Watch")
        else:
            print(f"   ❌ Не удалось добавить символ")

    # 5. Получение текущей цены
    print("\n5️⃣ Получение текущей цены:")
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        print(f"   Bid: {tick.bid:.2f}")
        print(f"   Ask: {tick.ask:.2f}")
        print(f"   Last: {tick.last:.2f}")
        print(f"   Time: {datetime.fromtimestamp(tick.time)}")
        print(f"   ✅ Цена получена успешно")
    else:
        print(f"   ❌ Не удалось получить цену: {mt5.last_error()}")

    # 6. Загрузка исторических данных
    print("\n6️⃣ Загрузка исторических данных (последние 10 свечей H1):")
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10)

    if rates is None or len(rates) == 0:
        print(f"   ❌ Не удалось загрузить данные: {mt5.last_error()}")
        mt5.shutdown()
        return False

    print(f"   ✅ Загружено {len(rates)} свечей")
    print("\n   Последние 3 свечи:")
    print(f"   {'Time':<20} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10}")
    print("   " + "-"*62)
    for i in range(min(3, len(rates))):
        r = rates[-(i+1)]
        time_str = datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"   {time_str:<20} {r['open']:>10.2f} {r['high']:>10.2f} {r['low']:>10.2f} {r['close']:>10.2f}")

    # 7. Все тесты пройдены
    print("\n" + "="*80)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*80)
    print("\n💡 MT5 готов к использованию:")
    print("   - Запустите: python paper_trading_mt5.py")
    print("   - Или используйте: python mt5_data_downloader.py")

    # Отключение
    mt5.shutdown()
    return True


def main():
    """Main entry point"""
    try:
        success = test_mt5_connection()

        if not success:
            print("\n" + "="*80)
            print("❌ ТЕСТ НЕ ПРОЙДЕН")
            print("="*80)
            print("\n💡 Рекомендации:")
            print("   1. Убедитесь что MT5 терминал запущен")
            print("   2. Откройте Market Watch (Ctrl+M) и добавьте XAUUSD")
            print("   3. Если используете не Windows - используйте paper_trading.py (yfinance)")
            print("   4. Проверьте установку: pip install MetaTrader5")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
