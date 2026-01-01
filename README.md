# 🤖 SMC Trading Strategy - Paper Trading Bot

Автоматическая система paper trading на базе стратегии Pattern Recognition с полной интеграцией GitHub Actions.

---

## 📋 Что это?

Полностью автоматизированная система виртуальной торговли для тестирования торговой стратегии Pattern Recognition (Smart Money Concepts) на рынке золота (XAUUSD).

### ✨ Основные возможности

- 🤖 **Автоматическое обнаружение сигналов** - Pattern Recognition Strategy (1.618 Fibonacci)
- 📊 **Два режима данных** - MetaTrader5 или Yahoo Finance
- 💰 **Частичное закрытие позиций** - TP1/TP2/TP3 с trailing stop
- 📱 **Telegram уведомления** - real-time notifications о сделках
- ☁️ **GitHub Actions** - автоматический запуск по расписанию
- 💾 **Сохранение состояния** - позиции и история между запусками
- 📈 **Статистика и отчетность** - CSV файлы с детальной статистикой

---

## 🚀 Быстрый старт

### Вариант 1: GitHub Actions (Рекомендуется)

Запуск бота в облаке с автоматическим расписанием:

1. **[5-минутная настройка](GITHUB_ACTIONS_QUICKSTART.md)** - быстрый старт
2. **[Полная документация](.github/GITHUB_ACTIONS_SETUP.md)** - детальное руководство
3. **[Обзор системы](GITHUB_ACTIONS_README.md)** - как всё работает

```bash
# 1. Настройте GitHub Secrets (2 минуты)
# 2. Запустите workflow вручную (1 минута)
# 3. Получайте уведомления в Telegram! ✅
```

### Вариант 2: Локальный запуск

Запуск бота на вашем компьютере:

```bash
# 1. Установите зависимости
cd smc_trading_strategy
pip install -r requirements.txt

# 2. Настройте .env файл
cp .env.example .env
# Отредактируйте .env (добавьте Telegram credentials)

# 3. Запустите бота
python paper_trading_improved.py
```

Документация:
- **[Paper Trading Setup](smc_trading_strategy/PAPER_TRADING_SETUP.md)** - локальная настройка
- **[MT5 Setup](smc_trading_strategy/README_MT5.md)** - настройка MetaTrader5
- **[Run Live Bot](smc_trading_strategy/README_RUN_LIVE_BOT.md)** - запуск live бота

---

## 📁 Структура проекта

```
/
├── .github/workflows/          # GitHub Actions workflows
│   └── paper-trading.yml       # Автоматический запуск бота
│
├── smc_trading_strategy/       # Основной код
│   ├── paper_trading_improved.py         # Бот с улучшенной частотой проверок
│   ├── paper_trading_github_action.py    # Версия для GitHub Actions
│   ├── pattern_recognition_strategy.py   # Торговая стратегия
│   ├── mt5_data_downloader.py           # MT5 данные
│   ├── telegram_notifier.py             # Telegram уведомления
│   └── requirements.txt                 # Зависимости Python
│
├── GITHUB_ACTIONS_QUICKSTART.md  # Быстрый старт (5 минут)
├── GITHUB_ACTIONS_README.md      # Полный обзор GitHub Actions
└── README.md                     # Этот файл
```

---

## 🎯 Возможности

### 🔍 Pattern Recognition Strategy

- **Fibonacci уровни** - 1.618 (стандартный) или 2.618 (агрессивный)
- **Swing points** - автоматическое обнаружение локальных максимумов/минимумов
- **Order blocks** - идентификация зон интереса
- **Fair Value Gaps** - обнаружение дисбалансов
- **Pattern matching** - флаги, вымпелы, треугольники

### 💰 Управление позициями

**Частичное закрытие:**
- **TP1** (30п) → закрыть 50% → активировать trailing stop
- **TP2** (55п) → закрыть 30%
- **TP3** (90п) → закрыть 20%

**Trailing Stop:**
- Активируется после TP1
- Дистанция: 18п (LONG TREND), 10п (SHORT TREND)
- Автоматическое подтягивание за ценой

**Timeout:**
- LONG: 60ч (TREND), 48ч (RANGE)
- SHORT: 24ч (TREND), RANGE отключен

### 📊 Адаптивные параметры

**LONG параметры:**
```
TREND:  TP 30/55/90п  Trailing 18п  Timeout 60h
RANGE:  TP 20/35/50п  Trailing 15п  Timeout 48h
```

**SHORT параметры (оптимизированные):**
```
TREND:  TP 15/25/35п  Trailing 10п  Timeout 24h
RANGE:  ОТКЛЮЧЕН (анализ показал -14% PnL)
```

### 📱 Telegram Notifications

**Типы уведомлений:**
- 🟢 Новый сигнал (вход в позицию)
- 🎯 Частичное закрытие (TP1/TP2/TP3)
- ✅/❌ Полное закрытие (SL/TP/TIMEOUT/TRAILING_SL)
- 📊 Статистика торговли

**Пример уведомления:**
```
🟢 НОВЫЙ СИГНАЛ - PAPER TRADING

📊 Стратегия: Pattern Recognition (1.618)
⏰ Время: 2025-01-01 14:00:00

🟢 Направление: LONG
💰 Вход: 4520.50
🛑 Stop Loss: 4450.00
🎯 TP1: 4550.50 (50%)
   TP2: 4575.50 (30%)
   TP3: 4610.50 (20%)

📐 Режим: TREND
🔄 Trailing: 18п (после TP1)
```

---

## 🌐 Режимы работы

### 🟢 Yahoo Finance (простой)

**Преимущества:**
- ✅ Работает "из коробки"
- ✅ Не требует MT5
- ✅ Бесплатные данные
- ✅ Подходит для GitHub Actions

**Недостатки:**
- ⚠️ Задержка ~15-20 минут
- ⚠️ Gold Futures (GC=F) вместо XAUUSD

**Использование:**
```python
python paper_trading.py
```

### 🔵 MetaTrader5 (продвинутый)

**Преимущества:**
- ✅ Реальные цены XAUUSD
- ✅ Минимальная задержка
- ✅ Точные Forex данные

**Требования:**
- ❌ Windows OS
- ❌ Установленный MT5 терминал
- ❌ Demo/Real MT5 счет

**Использование:**
```python
python paper_trading_improved.py
# или
python paper_trading_github_action.py
```

---

## ☁️ GitHub Actions

### Автоматический запуск в облаке

**Особенности:**
- ⏰ Запуск по расписанию (по умолчанию: каждый час)
- 💾 Сохранение состояния между запусками
- 📊 Автоматическая статистика и отчеты
- 📱 Telegram уведомления
- 🆓 Бесплатно для публичных репозиториев

**Быстрая настройка:**

1. **Настройте GitHub Secrets:**
   ```
   Settings → Secrets and variables → Actions
   
   Добавьте:
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
   - (опционально) MT5 credentials
   ```

2. **Запустите workflow:**
   ```
   Actions → Paper Trading Bot → Run workflow
   ```

3. **Мониторьте результаты:**
   - Telegram уведомления
   - GitHub Actions logs
   - Artifacts (CSV статистика)

**Документация:**
- **[Быстрый старт за 5 минут](GITHUB_ACTIONS_QUICKSTART.md)**
- **[Полная настройка](.github/GITHUB_ACTIONS_SETUP.md)**
- **[Обзор системы](GITHUB_ACTIONS_README.md)**

---

## 📈 Результаты бэктеста

Backtests проведены на исторических данных XAUUSD:

### Baseline 3TP Strategy (1 год)

```
Total PnL:      +387.46%
Win Rate:       67%
Total Trades:   156
Winning:        105
Losing:         51

Monthly Performance:
- Прибыльных месяцев: 12/13 (92%)
- Средняя прибыль: +29.8% в месяц

Estimated profit (лот 0.1): ~$114,381/год
Estimated profit (лот 0.01): ~$11,438/год
```

### Оптимизация SHORT сделок

После анализа SHORT trades выявлено:
- SHORT в TREND режиме: 65% WR, +45% PnL ✅
- SHORT в RANGE режиме: 46% WR, -14% PnL ❌

**Решение:** SHORT trades только в TREND режиме с уменьшенными TP.

Подробные отчеты:
- [BACKTEST_COMPARISON_V1_VS_V2.md](BACKTEST_COMPARISON_V1_VS_V2.md)
- [CRITICAL_ISSUES_ANALYSIS.md](CRITICAL_ISSUES_ANALYSIS.md)

---

## 🛠️ Технологии

- **Python 3.8+**
- **pandas, numpy** - обработка данных
- **MetaTrader5** - получение рыночных данных (Windows only)
- **yfinance** - альтернативный источник данных
- **python-telegram-bot** - Telegram уведомления
- **GitHub Actions** - CI/CD автоматизация

---

## 📚 Документация

### Быстрый старт
- **[GitHub Actions - 5 минут](GITHUB_ACTIONS_QUICKSTART.md)** ⭐ Рекомендуется
- **[Локальный запуск](smc_trading_strategy/README_RUN_LIVE_BOT.md)**
- **[Paper Trading Setup](smc_trading_strategy/PAPER_TRADING_SETUP.md)**

### Детальная документация
- **[GitHub Actions - Полная настройка](.github/GITHUB_ACTIONS_SETUP.md)**
- **[GitHub Actions - Обзор системы](GITHUB_ACTIONS_README.md)**
- **[MetaTrader5 Setup](smc_trading_strategy/README_MT5.md)**
- **[Dual Frequency Explained](smc_trading_strategy/DUAL_FREQUENCY_EXPLAINED.md)**

### Анализ и результаты
- **[Backtest Comparison](BACKTEST_COMPARISON_V1_VS_V2.md)**
- **[Critical Issues Analysis](CRITICAL_ISSUES_ANALYSIS.md)**
- **[Final Comparison](smc_trading_strategy/FINAL_COMPARISON.md)**
- **[Optimization Results](smc_trading_strategy/OPTIMIZATION_RESULTS.md)**

---

## 🔒 Безопасность

### ✅ Best Practices

1. **Используйте GitHub Secrets** для чувствительных данных
2. **Demo счета** для тестирования (минимум 1-2 месяца)
3. **Private repository** для реальной торговли
4. **Мониторинг** всех действий бота
5. **Регулярная ротация** паролей и токенов

### ⚠️ Disclaimer

- Это **PAPER TRADING** (виртуальная торговля)
- Прошлые результаты не гарантируют будущую прибыль
- Всегда тестируйте на demo счетах
- Используйте на свой риск
- Автор не несет ответственности за убытки

---

## 🤝 Contributing

Contributions приветствуются! Пожалуйста:

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## 📝 License

Этот проект распространяется под MIT License. См. `LICENSE` файл для деталей.

---

## 📞 Поддержка

Если возникли вопросы:

1. **Проверьте документацию** - большинство вопросов уже освещены
2. **GitHub Issues** - для bug reports и feature requests
3. **Discussions** - для общих вопросов и обсуждений

---

## 🎯 Roadmap

### В разработке
- [ ] Web dashboard для мониторинга
- [ ] Multi-symbol support (не только XAUUSD)
- [ ] Backtesting framework улучшения
- [ ] ML-based signal filtering
- [ ] Risk management optimization

### Completed
- [x] GitHub Actions integration ✅
- [x] Telegram notifications ✅
- [x] State persistence ✅
- [x] Adaptive TP/SL parameters ✅
- [x] SHORT optimization ✅
- [x] Trailing stop ✅

---

## ⭐ Acknowledgments

- MetaTrader5 за API для получения данных
- Telegram за Bot API
- GitHub за бесплатный CI/CD
- Smart Money Concepts сообщество

---

## 📊 Статистика проекта

- **86 файлов** в `smc_trading_strategy/`
- **52 Python scripts**
- **10+ Markdown документов**
- **156 backtested trades**
- **67% win rate**
- **+387% PnL** за год (backtest)

---

## ✅ Начать использовать

### За 5 минут (GitHub Actions)

```bash
# 1. Fork этот репозиторий
# 2. Settings → Secrets → Добавьте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
# 3. Actions → Paper Trading Bot → Run workflow
# 4. ✅ Готово! Проверьте Telegram
```

**Документация:** [GITHUB_ACTIONS_QUICKSTART.md](GITHUB_ACTIONS_QUICKSTART.md)

### Локально (15 минут)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd <repo-name>

# 2. Install dependencies
cd smc_trading_strategy
pip install -r requirements.txt

# 3. Setup .env
cp .env.example .env
# Edit .env with your Telegram credentials

# 4. Run bot
python paper_trading_improved.py
```

**Документация:** [smc_trading_strategy/README_RUN_LIVE_BOT.md](smc_trading_strategy/README_RUN_LIVE_BOT.md)

---

**Удачной торговли! 🚀📈💰**
