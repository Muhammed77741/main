"""
MT5 Data Downloader - загрузка данных напрямую из MetaTrader 5
ВАЖНО: Работает только на Windows с установленным MT5
"""

import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz


class MT5DataDownloader:
    """Загрузчик данных из MetaTrader 5"""

    def __init__(self, symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1):
        """
        Инициализация MT5 подключения

        Args:
            symbol: Торговый инструмент (например, 'XAUUSD', 'EURUSD')
            timeframe: Таймфрейм (mt5.TIMEFRAME_H1, mt5.TIMEFRAME_M15, и т.д.)
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.connected = False

        print("🔌 Подключение к MetaTrader 5...")

    def connect(self, login=None, password=None, server=None):
        """
        Подключение к MT5 терминалу

        Args:
            login: Номер счета (опционально)
            password: Пароль (опционально)
            server: Сервер брокера (опционально)

        Returns:
            bool: True если подключение успешно
        """
        # Инициализация MT5
        if not mt5.initialize():
            print(f"❌ Ошибка инициализации MT5: {mt5.last_error()}")
            return False

        # Если указаны логин/пароль/сервер - авторизуемся
        if login and password and server:
            authorized = mt5.login(login, password=password, server=server)
            if not authorized:
                print(f"❌ Ошибка авторизации: {mt5.last_error()}")
                mt5.shutdown()
                return False
            print(f"✅ Авторизован: счет {login}")
        else:
            print("✅ Подключено к MT5 (без авторизации)")

        # Проверка символа
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Символ {self.symbol} не найден")
            mt5.shutdown()
            return False

        # Включаем символ в Market Watch
        if not symbol_info.visible:
            if not mt5.symbol_select(self.symbol, True):
                print(f"❌ Не удалось добавить {self.symbol} в Market Watch")
                mt5.shutdown()
                return False

        self.connected = True
        print(f"✅ Символ {self.symbol} готов к работе")

        # Показываем информацию о терминале
        terminal_info = mt5.terminal_info()
        if terminal_info:
            print(f"\n📊 Информация о терминале:")
            print(f"   Компания: {terminal_info.company}")
            print(f"   Путь: {terminal_info.path}")
            print(f"   Build: {terminal_info.build}")

        return True

    def download_history(self, bars=1000, from_date=None, to_date=None):
        """
        Загрузка исторических данных

        Args:
            bars: Количество баров (если from_date не указана)
            from_date: Дата начала (datetime object)
            to_date: Дата окончания (datetime object)

        Returns:
            pd.DataFrame: DataFrame с OHLCV данными
        """
        if not self.connected:
            print("❌ Не подключено к MT5. Вызовите connect() сначала")
            return None

        try:
            print(f"\n📥 Загрузка данных {self.symbol}...")

            # Загрузка данных
            if from_date and to_date:
                # Загрузка по диапазону дат
                utc_from = from_date.replace(tzinfo=pytz.UTC)
                utc_to = to_date.replace(tzinfo=pytz.UTC)

                rates = mt5.copy_rates_range(self.symbol, self.timeframe, utc_from, utc_to)
                print(f"   Период: {from_date} - {to_date}")
            else:
                # Загрузка последних N баров
                rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, bars)
                print(f"   Баров: {bars}")

            if rates is None or len(rates) == 0:
                print(f"❌ Не удалось загрузить данные: {mt5.last_error()}")
                return None

            # Конвертация в DataFrame
            df = pd.DataFrame(rates)

            # Конвертация времени
            df['datetime'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('datetime')

            # Переименование колонок
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            })

            # Оставляем только OHLCV
            df = df[['open', 'high', 'low', 'close', 'volume']]

            # Добавляем часы торговых сессий
            df['is_london'] = df.index.hour.isin(range(7, 12))
            df['is_ny'] = df.index.hour.isin(range(13, 20))
            df['is_overlap'] = df.index.hour.isin(range(13, 16))
            df['is_active'] = df['is_london'] | df['is_ny']
            df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

            print(f"✅ Загружено {len(df)} свечей")
            print(f"   Период: {df.index[0]} до {df.index[-1]}")
            print(f"   Последняя цена: {df['close'].iloc[-1]:.2f}")

            return df

        except Exception as e:
            print(f"❌ Ошибка загрузки данных: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_realtime_data(self, period_hours=120):
        """
        Загрузка данных для real-time торговли

        Args:
            period_hours: Количество часов истории

        Returns:
            pd.DataFrame: DataFrame с последними данными
        """
        if not self.connected:
            print("❌ Не подключено к MT5. Вызовите connect() сначала")
            return None

        # Рассчитываем диапазон дат
        to_date = datetime.now()
        from_date = to_date - timedelta(hours=period_hours)

        return self.download_history(from_date=from_date, to_date=to_date)

    def get_current_price(self):
        """
        Получение текущей цены

        Returns:
            dict: {'bid': float, 'ask': float, 'last': float, 'time': datetime}
        """
        if not self.connected:
            print("❌ Не подключено к MT5")
            return None

        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"❌ Не удалось получить тик: {mt5.last_error()}")
            return None

        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last,
            'time': datetime.fromtimestamp(tick.time)
        }

    def save_to_csv(self, df, filename=None):
        """
        Сохранение данных в CSV файл

        Args:
            df: DataFrame с данными
            filename: Имя файла (опционально)
        """
        if df is None or len(df) == 0:
            print("❌ Нет данных для сохранения")
            return

        if filename is None:
            # Генерируем имя файла
            start_date = df.index[0].strftime('%Y%m%d')
            end_date = df.index[-1].strftime('%Y%m%d')
            filename = f"{self.symbol}_MT5_{start_date}_{end_date}.csv"

        # Сохраняем
        df_to_save = df.copy()
        df_to_save['datetime'] = df_to_save.index
        df_to_save = df_to_save[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        df_to_save.to_csv(filename, index=False)

        print(f"✅ Данные сохранены в {filename}")

    def disconnect(self):
        """Отключение от MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("✅ Отключено от MT5")


def main():
    """Пример использования"""

    print("\n" + "="*80)
    print("📊 MT5 DATA DOWNLOADER")
    print("="*80)

    # Создаем загрузчик
    downloader = MT5DataDownloader(symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1)

    # Подключаемся (без авторизации - использует открытый терминал)
    if not downloader.connect():
        print("\n❌ Не удалось подключиться к MT5")
        print("\n💡 Убедитесь что:")
        print("   1. MT5 терминал запущен")
        print("   2. Вы используете Windows")
        print("   3. Установлен модуль: pip install MetaTrader5")
        return

    # Загружаем последние 1000 свечей
    print("\n" + "="*80)
    print("📥 Загрузка исторических данных")
    print("="*80)

    df = downloader.download_history(bars=1000)

    if df is not None:
        # Показываем последние 5 свечей
        print("\n📊 Последние 5 свечей:")
        print(df[['open', 'high', 'low', 'close', 'volume']].tail())

        # Сохраняем в CSV
        print("\n" + "="*80)
        print("💾 Сохранение данных")
        print("="*80)
        downloader.save_to_csv(df)

    # Получаем текущую цену
    print("\n" + "="*80)
    print("💰 Текущая цена")
    print("="*80)

    current_price = downloader.get_current_price()
    if current_price:
        print(f"   Bid: {current_price['bid']:.2f}")
        print(f"   Ask: {current_price['ask']:.2f}")
        print(f"   Last: {current_price['last']:.2f}")
        print(f"   Time: {current_price['time']}")

    # Загружаем real-time данные (последние 5 дней = 120 часов)
    print("\n" + "="*80)
    print("🔄 Real-time данные (последние 120 часов)")
    print("="*80)

    df_realtime = downloader.get_realtime_data(period_hours=120)
    if df_realtime is not None:
        print(f"\n✅ Загружено {len(df_realtime)} свечей для real-time торговли")

    # Отключаемся
    print("\n" + "="*80)
    downloader.disconnect()
    print("="*80)


if __name__ == "__main__":
    main()
