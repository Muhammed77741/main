# 📊 MT5 Integration Guide

## Обзор

Эта система включает две версии live бота:

1. **paper_trading.py** - использует yfinance (Yahoo Finance) - работает на любой ОС
2. **paper_trading_mt5.py** - использует MetaTrader 5 - только для Windows

## 🔧 Установка MT5 версии

### Требования

- ✅ **Windows OS** (MetaTrader5 API работает только на Windows)
- ✅ **MetaTrader 5 терминал** установлен и запущен
- ✅ **Python 3.8+**

### Установка зависимостей

```bash
pip install MetaTrader5
pip install pandas numpy python-telegram-bot python-dotenv
```

Или установите все из requirements.txt:

```bash
pip install -r requirements.txt
```

## 📁 Файлы

### 1. `mt5_data_downloader.py`

Класс для загрузки данных из MT5:

```python
from mt5_data_downloader import MT5DataDownloader

# Создание загрузчика
downloader = MT5DataDownloader(symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1)

# Подключение к MT5 (использует открытый терминал)
downloader.connect()

# Загрузка исторических данных
df = downloader.download_history(bars=1000)

# Загрузка real-time данных (последние 120 часов)
df_realtime = downloader.get_realtime_data(period_hours=120)

# Получение текущей цены
price = downloader.get_current_price()
print(f"Bid: {price['bid']}, Ask: {price['ask']}")

# Сохранение в CSV
downloader.save_to_csv(df)

# Отключение
downloader.disconnect()
```

### 2. `paper_trading_mt5.py`

Live bot с MT5 источником данных - работает так же, как paper_trading.py, но использует MT5 вместо yfinance.

## 🚀 Быстрый старт

### Вариант 1: Без авторизации (использует открытый терминал)

1. Откройте MT5 терминал
2. Убедитесь что XAUUSD виден в Market Watch
3. Создайте `.env` файл (см. ниже)
4. Запустите бот:

```bash
python paper_trading_mt5.py
```

### Вариант 2: С авторизацией

Добавьте в `.env` файл:

```env
# Telegram (обязательно)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# MT5 (опционально - если хотите автоматическую авторизацию)
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Server

# Настройки
MT5_SYMBOL=XAUUSD
CHECK_INTERVAL=3600
```

Затем запустите:

```bash
python paper_trading_mt5.py
```

## 🔍 Пример использования MT5 загрузчика

### Простой пример

```python
import MetaTrader5 as mt5
from mt5_data_downloader import MT5DataDownloader

# Создаем загрузчик для XAUUSD на H1
downloader = MT5DataDownloader(symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1)

# Подключаемся
if downloader.connect():
    # Загружаем последние 1000 свечей
    df = downloader.download_history(bars=1000)

    if df is not None:
        print(f"Загружено {len(df)} свечей")
        print(f"Последняя цена: {df['close'].iloc[-1]:.2f}")

        # Сохраняем в CSV
        downloader.save_to_csv(df)

    # Отключаемся
    downloader.disconnect()
```

### Загрузка по диапазону дат

```python
from datetime import datetime, timedelta
import MetaTrader5 as mt5
from mt5_data_downloader import MT5DataDownloader

downloader = MT5DataDownloader(symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1)

if downloader.connect():
    # Загружаем данные за последние 30 дней
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)

    df = downloader.download_history(from_date=from_date, to_date=to_date)

    if df is not None:
        print(f"Загружено {len(df)} свечей")
        print(f"Период: {df.index[0]} - {df.index[-1]}")
        downloader.save_to_csv(df, 'XAUUSD_30days.csv')

    downloader.disconnect()
```

### Мониторинг цены в реальном времени

```python
import time
from mt5_data_downloader import MT5DataDownloader

downloader = MT5DataDownloader(symbol='XAUUSD')

if downloader.connect():
    try:
        while True:
            # Получаем текущую цену
            price = downloader.get_current_price()

            if price:
                print(f"{price['time']} | Bid: {price['bid']:.2f} | Ask: {price['ask']:.2f}")

            time.sleep(1)  # Проверяем каждую секунду

    except KeyboardInterrupt:
        print("\nОстановлено")
        downloader.disconnect()
```

## 📊 Timeframes

Доступные таймфреймы:

```python
import MetaTrader5 as mt5

mt5.TIMEFRAME_M1   # 1 минута
mt5.TIMEFRAME_M5   # 5 минут
mt5.TIMEFRAME_M15  # 15 минут
mt5.TIMEFRAME_M30  # 30 минут
mt5.TIMEFRAME_H1   # 1 час (рекомендуется для стратегии)
mt5.TIMEFRAME_H4   # 4 часа
mt5.TIMEFRAME_D1   # 1 день
mt5.TIMEFRAME_W1   # 1 неделя
mt5.TIMEFRAME_MN1  # 1 месяц
```

## ⚙️ Настройка .env файла

Создайте файл `.env` в папке `smc_trading_strategy/`:

```env
# Telegram (обязательно для уведомлений)
TELEGRAM_BOT_TOKEN=6851850308:AAEw96lCqeT4W7RINj_iPEkttgNobi9cmNU
TELEGRAM_CHAT_ID=-1002029944880

# MT5 (опционально - если не указать, использует открытый терминал)
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Demo

# Настройки
MT5_SYMBOL=XAUUSD
CHECK_INTERVAL=3600
```

## 🔧 Troubleshooting

### Ошибка: "Failed to initialize MT5"

**Решение:**
1. Убедитесь что MT5 терминал запущен
2. Проверьте что вы используете Windows
3. Переустановите модуль: `pip uninstall MetaTrader5` → `pip install MetaTrader5`

### Ошибка: "Symbol XAUUSD not found"

**Решение:**
1. Откройте MT5 терминал
2. Нажмите Ctrl+U (Market Watch)
3. Найдите XAUUSD и добавьте в список
4. Или попробуйте другое название: `GOLD`, `XAU/USD`, `XAUUSD.m`

### Ошибка: "Authorization failed"

**Решение:**
1. Проверьте правильность логина/пароля/сервера в `.env`
2. Или не указывайте их - бот будет использовать открытый терминал
3. Убедитесь что в MT5 терминале вы авторизованы

### Нет данных / пустой DataFrame

**Решение:**
1. Проверьте интернет соединение
2. Убедитесь что символ доступен для торговли
3. Попробуйте загрузить меньше баров (например, 100 вместо 1000)
4. Проверьте что выбран правильный timeframe

## 🆚 Сравнение: yfinance vs MT5

| Параметр | yfinance (paper_trading.py) | MT5 (paper_trading_mt5.py) |
|----------|----------------------------|----------------------------|
| **ОС** | Windows, Linux, macOS | ⚠️ Только Windows |
| **Установка** | Простая | Требует MT5 терминал |
| **Данные** | Yahoo Finance (бесплатно) | Брокер MT5 |
| **Точность** | Хорошая | ⭐ Отличная (реальные тики) |
| **Задержка** | ~15 мин (зависит от Yahoo) | ⭐ Real-time |
| **Символы** | GC=F, GLD (прокси для Gold) | ⭐ Прямой XAUUSD |
| **Надежность** | Зависит от Yahoo API | ⭐ Прямое подключение |

## 💡 Рекомендации

### Для тестирования (любая ОС)
👉 Используйте `paper_trading.py` (yfinance)

### Для production (Windows + MT5)
👉 Используйте `paper_trading_mt5.py` (MT5) - более точные данные и меньше задержек

### Для backtesting
👉 Используйте `mt5_data_downloader.py` для загрузки исторических данных в CSV, затем запускайте backtest скрипты

## 📝 Запуск в PyCharm

1. Откройте `paper_trading_mt5.py`
2. Убедитесь что MT5 терминал запущен
3. Создайте `.env` файл с настройками
4. Нажмите зеленую кнопку ▶️ Run

Или через терминал PyCharm:

```bash
python paper_trading_mt5.py
```

## ✅ Checklist перед запуском

- [ ] Windows ОС
- [ ] MT5 терминал установлен
- [ ] MT5 терминал запущен
- [ ] XAUUSD добавлен в Market Watch
- [ ] Установлен модуль: `pip install MetaTrader5`
- [ ] Создан `.env` файл с Telegram credentials
- [ ] (Опционально) Добавлены MT5_LOGIN, MT5_PASSWORD, MT5_SERVER в `.env`

## 🎯 Ожидаемый результат

После запуска вы увидите:

```
================================================================================
🤖 PAPER TRADING BOT STARTED - BASELINE 3TP (MT5)
================================================================================
⏱️  Check interval: 3600.0s (1.0h)
📊 Strategy: Pattern Recognition (1.618)
📈 Asset: XAUUSD
🎯 TP Levels: 30п / 50п / 80п
   Close %: 50% / 30% / 20%
================================================================================

🔌 Подключение к MetaTrader 5...
✅ Подключено к MT5 (без авторизации)
✅ Символ XAUUSD готов к работе

📊 Информация о терминале:
   Компания: MetaQuotes Software Corp.
   Build: 3850

================================================================================
🔍 Checking for signals at 2025-12-28 14:30:00
================================================================================
📥 Downloading XAUUSD data from MT5...
✅ Загружено 120 свечей
   Период: 2025-12-23 14:00:00 до 2025-12-28 13:00:00
   Последняя цена: 2645.80
✅ Downloaded 120 candles from MT5
   Latest: 2025-12-28 13:00:00 | Price: 2645.80

📊 Status:
   Open positions: 0
   Closed trades: 0

💰 Current price:
   Bid: 2645.75
   Ask: 2645.85

⏳ Next check in 3600s...
   Next check: 2025-12-28 15:30:00
```

## 🔄 Автоматическая загрузка исторических данных

Создайте скрипт для ежедневной загрузки данных:

```python
# auto_download_mt5.py
from mt5_data_downloader import MT5DataDownloader
import MetaTrader5 as mt5
from datetime import datetime, timedelta

downloader = MT5DataDownloader(symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1)

if downloader.connect():
    # Загружаем последний год
    to_date = datetime.now()
    from_date = to_date - timedelta(days=365)

    df = downloader.download_history(from_date=from_date, to_date=to_date)

    if df is not None:
        # Сохраняем с датой в имени
        filename = f"XAUUSD_1H_MT5_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv"
        downloader.save_to_csv(df, filename)
        print(f"✅ Данные сохранены в {filename}")

    downloader.disconnect()
```

Запускайте каждый день для обновления данных!
