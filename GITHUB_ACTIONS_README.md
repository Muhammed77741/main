# 🤖 Paper Trading Bot - GitHub Actions Automation

## 📋 Обзор проекта

Полностью автоматизированная система paper trading для стратегии Pattern Recognition с поддержкой:
- ✅ Автоматический запуск по расписанию
- ✅ Telegram уведомления в реальном времени
- ✅ Сохранение состояния между запусками
- ✅ Статистика и отчетность
- ✅ Два режима: MT5 и Yahoo Finance

---

## 🎯 Быстрый старт

### Для нетерпеливых (5 минут)

См. **[GITHUB_ACTIONS_QUICKSTART.md](GITHUB_ACTIONS_QUICKSTART.md)** - быстрая настройка за 5 минут!

### Для тех кто хочет понять детали

См. **[.github/GITHUB_ACTIONS_SETUP.md](.github/GITHUB_ACTIONS_SETUP.md)** - полная документация.

---

## 📁 Структура проекта

```
/
├── .github/
│   ├── workflows/
│   │   └── paper-trading.yml          # GitHub Actions workflow
│   └── GITHUB_ACTIONS_SETUP.md        # Полная документация
│
├── smc_trading_strategy/
│   ├── paper_trading_improved.py      # Основной бот (infinite loop)
│   ├── paper_trading_github_action.py # Бот для GitHub Actions (one-shot)
│   ├── paper_trading.py               # Yahoo Finance версия
│   ├── pattern_recognition_strategy.py # Торговая стратегия
│   ├── mt5_data_downloader.py         # MT5 данные
│   ├── telegram_notifier.py           # Telegram уведомления
│   ├── requirements.txt               # Зависимости
│   └── .env.example                   # Пример конфигурации
│
├── .env.github_actions.example        # Пример для GitHub Secrets
├── GITHUB_ACTIONS_QUICKSTART.md       # Быстрый старт (5 мин)
├── GITHUB_ACTIONS_README.md           # Этот файл
└── .gitignore                         # Игнорируемые файлы
```

---

## 🔧 Файлы и их назначение

### GitHub Actions

| Файл | Описание |
|------|----------|
| `.github/workflows/paper-trading.yml` | Основной workflow файл с расписанием и настройками |
| `.github/GITHUB_ACTIONS_SETUP.md` | Подробная документация по настройке |
| `GITHUB_ACTIONS_QUICKSTART.md` | Быстрый старт за 5 минут |
| `.env.github_actions.example` | Пример переменных окружения для Secrets |

### Trading Bots

| Файл | Описание | Режим работы |
|------|----------|--------------|
| `paper_trading_improved.py` | Основной бот | Infinite loop (для локального запуска) |
| `paper_trading_github_action.py` | GitHub Actions бот | One-shot (для scheduled runs) |
| `paper_trading.py` | Yahoo Finance бот | Infinite loop или one-shot |

**Ключевое отличие:**
- `paper_trading_improved.py` - работает бесконечно, проверяет сигналы/позиции по таймеру
- `paper_trading_github_action.py` - запускается один раз, проверяет сигналы/позиции, сохраняет состояние, завершается

### Supporting Files

| Файл | Описание |
|------|----------|
| `pattern_recognition_strategy.py` | Торговая стратегия Pattern Recognition (1.618) |
| `mt5_data_downloader.py` | Скачивание данных с MetaTrader5 |
| `telegram_notifier.py` | Отправка уведомлений в Telegram |
| `trading_state.json` | Сохраненное состояние (позиции, история) |

---

## ⚙️ Режимы работы

### 🟢 Режим 1: Yahoo Finance (Linux runner)

**Workflow job:** `paper-trading-yahoo`

**Характеристики:**
- ✅ Работает на Ubuntu (быстрее, дешевле)
- ✅ Не требует MT5
- ✅ Проще в настройке
- ⚠️ Задержка данных ~15-20 минут
- ⚠️ Использует Gold Futures (GC=F) вместо XAUUSD

**Использует:**
- `paper_trading.py` (Yahoo Finance версия)
- Базовые зависимости: pandas, numpy, yfinance

**Secrets:**
```
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
CHECK_INTERVAL
```

### 🔵 Режим 2: MetaTrader5 (Windows runner)

**Workflow job:** `paper-trading`

**Характеристики:**
- ✅ Реальные данные XAUUSD с Forex
- ✅ Минимальная задержка
- ✅ Точные цены
- ❌ Требует Windows runner
- ❌ Требует установленный MT5 терминал
- ❌ Требует self-hosted runner (GitHub Actions не может установить MT5)

**Использует:**
- `paper_trading_github_action.py` (специальная версия для CI/CD)
- MT5 зависимости: MetaTrader5 package

**Secrets:**
```
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
MT5_LOGIN
MT5_PASSWORD
MT5_SERVER
MT5_SYMBOL
SIGNAL_CHECK_INTERVAL
POSITION_CHECK_INTERVAL
```

**⚠️ Важно:** Для MT5 режима нужен **self-hosted runner** на Windows с установленным MT5!

---

## 🔄 Как работает автоматизация

### Жизненный цикл запуска

```
┌─────────────────────────────────────────────────────────────┐
│ GitHub Actions Trigger (cron или manual)                    │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Checkout repository                                       │
│    - Скачивает код из GitHub                                 │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Download previous state (trading_state.json)             │
│    - Восстанавливает открытые позиции                        │
│    - Восстанавливает историю сделок                          │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Setup Python + Install dependencies                       │
│    - Python 3.11                                             │
│    - pandas, numpy, MetaTrader5/yfinance, etc.              │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Create .env from GitHub Secrets                           │
│    - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, etc.             │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Run Paper Trading Bot (one-shot mode)                    │
│    ├── Load previous state                                   │
│    ├── Check for NEW signals                                 │
│    │   └── Open positions if signal found                    │
│    ├── Check OPEN positions                                  │
│    │   ├── Check TP/SL                                       │
│    │   ├── Check timeout                                     │
│    │   └── Close positions if needed                         │
│    └── Save new state                                        │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Upload artifacts                                          │
│    ├── trading_state.json (сохраняется для следующего раза) │
│    ├── live_bot_statistics_*.csv (статистика)               │
│    └── *.log (логи выполнения)                              │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Send Telegram notifications                               │
│    - Новые сигналы                                           │
│    - Частичные закрытия (TP1/TP2/TP3)                       │
│    - Полные закрытия                                         │
└─────────────────────────────────────────────────────────────┘

        Ждем следующего запуска по расписанию ⏰
```

### Сохранение состояния

**Проблема:** GitHub Actions - это stateless окружение. Каждый запуск начинается "с нуля".

**Решение:** Используем artifacts для сохранения состояния между запусками.

```python
# trading_state.json содержит:
{
  "open_positions": [
    {
      "entry_time": "2025-01-01T10:00:00",
      "direction": "LONG",
      "entry_price": 4500.0,
      "stop_loss": 4450.0,
      "tp1_price": 4530.0,
      "tp2_price": 4555.0,
      "tp3_price": 4590.0,
      "tp1_hit": true,
      "tp2_hit": false,
      "trailing_active": true,
      "position_remaining": 0.5,
      ...
    }
  ],
  "closed_trades": [...],
  "last_processed_signal_time": "2025-01-01T09:00:00",
  "saved_at": "2025-01-01T10:05:00"
}
```

**Workflow:**
1. **Download artifact** - загружаем `trading_state.json` из предыдущего запуска
2. **Run bot** - бот загружает состояние, проверяет сигналы/позиции, обновляет состояние
3. **Upload artifact** - сохраняем обновленный `trading_state.json` для следующего запуска

---

## 📊 Мониторинг и отчетность

### В реальном времени (Telegram)

Бот отправляет уведомления о:

**🟢 Новый сигнал:**
```
🟢 НОВЫЙ СИГНАЛ - PAPER TRADING

📊 Стратегия: Pattern Recognition (1.618)
⏰ Время: 2025-01-01 14:00:00

🟢 Направление: LONG
💰 Вход: 4520.50
🛑 Stop Loss: 4450.00
🎯 TP1: 4550.50 (50%)
🎯 TP2: 4575.50 (30%)
🎯 TP3: 4610.50 (20%)

📐 Режим: TREND
🔄 Trailing: 18п (после TP1)
⏱️ Timeout: 60h
```

**🎯 Частичное закрытие:**
```
🎯 ЧАСТИЧНОЕ ЗАКРЫТИЕ - TP1

💰 LONG: 4520.50 → 4550.50
📊 Закрыто: 50% позиции
💎 PnL: +0.66% (+30.00п)

🔄 TRAILING STOP АКТИВИРОВАН
   Дистанция: 18п

Осталось: 50% позиции
```

**✅ Полное закрытие:**
```
✅ ПРИБЫЛЬ - ЗАКРЫТИЕ ПОЗИЦИИ

💰 LONG: 4520.50 → 4580.25
🎯 Выход: TRAILING_SL

TPs: TP1✅ TP2✅ TP3❌
📈 Итого PnL: +1.98% (+89.75п)
⏱️ Длительность: 8.5h
```

### Исторические данные (CSV)

Скачайте artifacts после каждого запуска:

**`live_bot_statistics_XAUUSD.csv`:**
```csv
entry_time,exit_time,direction,regime,entry_price,exit_price,stop_loss,exit_type,pnl_pct,pnl_points,duration_hours,pattern,trailing_used
2025-01-01 10:00:00,2025-01-01 18:30:00,LONG,TREND,4520.5,4580.25,4532.5,TRAILING_SL,1.98,89.75,8.5,Bullish_Flag,True
2025-01-02 14:00:00,2025-01-03 02:15:00,SHORT,TREND,4625.0,4595.0,4640.0,TP2,0.89,30.0,12.25,Bearish_Pennant,False
...
```

Анализируйте в Excel/Python:
- Win rate
- Average PnL
- Best/worst trades
- Performance by regime (TREND vs RANGE)
- TP hit rates
- Average duration

### В GitHub Actions

**Actions tab:**
- История всех запусков
- Успешные/неудачные запуски
- Время выполнения
- Используемые минуты

**Logs:**
- Подробные логи каждого шага
- Вывод бота (print statements)
- Ошибки и warnings

**Artifacts:**
- `trading-state` - текущее состояние (обновляется каждый запуск)
- `trading-stats-XXX` - архив со статистикой и логами каждого запуска

---

## 🎛️ Настройка расписания

Workflow запускается по cron расписанию в `.github/workflows/paper-trading.yml`:

```yaml
on:
  schedule:
    - cron: '0 * * * *'  # Каждый час
```

### Примеры расписаний

```yaml
# Каждый час
- cron: '0 * * * *'

# Каждые 30 минут
- cron: '*/30 * * * *'

# Каждые 4 часа
- cron: '0 */4 * * *'

# Каждый день в 9:00 UTC
- cron: '0 9 * * *'

# В рабочие дни (пн-пт) каждый час с 9:00 до 17:00 UTC
- cron: '0 9-17 * * 1-5'

# Каждые 15 минут в рабочие часы
- cron: '*/15 9-17 * * 1-5'
```

**Инструмент для создания cron:** https://crontab.guru/

**⚠️ Важно:** GitHub Actions использует **UTC время**!

### Расчет использования минут

GitHub Actions лимиты (бесплатный план):
- **Публичные репозитории:** неограниченно
- **Приватные репозитории:** 2000 минут/месяц

Пример расчета:
```
Расписание: каждый час (24 раза в день)
Время выполнения: ~2 минуты на запуск

24 запуска × 30 дней × 2 минуты = 1440 минут/месяц

1440 < 2000 ✅ В пределах лимита!
```

---

## 🔐 Безопасность

### ✅ Best Practices

1. **Используйте GitHub Secrets**
   - Никогда не коммитьте `.env` с реальными данными
   - Все чувствительные данные через Secrets
   - `.env` добавлен в `.gitignore`

2. **Demo счета для тестирования**
   - Используйте MT5 demo счета
   - Не используйте реальные счета в автоматизации
   - Тестируйте минимум 1-2 месяца

3. **Ограничьте доступ**
   - Private repository для реальной торговли
   - Минимум collaborators
   - Two-factor authentication

4. **Регулярная ротация паролей**
   - MT5 пароль: раз в месяц
   - Telegram bot token: при необходимости
   - GitHub personal access token: раз в 90 дней

5. **Мониторинг активности**
   - Проверяйте логи каждую неделю
   - Анализируйте статистику
   - Telegram уведомления для всех событий

### 🚨 Что НЕ делать

❌ Не коммитьте secrets в код  
❌ Не используйте реальные счета в автоматизации (пока не протестируете)  
❌ Не делитесь repository с secrets  
❌ Не запускайте на незнакомых self-hosted runners  
❌ Не игнорируйте Telegram уведомления  

---

## 🛠️ Troubleshooting

### Проблема: Workflow не запускается

**Возможные причины:**
1. Workflow файл не на main/master ветке
2. Неправильный cron синтаксис
3. GitHub Actions отключены в настройках репозитория

**Решение:**
```bash
# 1. Проверьте что файл закоммичен
git add .github/workflows/paper-trading.yml
git commit -m "Add paper trading workflow"
git push origin main

# 2. Проверьте Settings → Actions → General
# Убедитесь что Actions включены

# 3. Попробуйте запустить вручную
# Actions → Paper Trading Bot → Run workflow
```

### Проблема: "Secret not found"

**Причина:** Секреты не настроены или неправильное имя

**Решение:**
1. `Settings` → `Secrets and variables` → `Actions`
2. Проверьте что все необходимые секреты созданы
3. Проверьте правильность имен (точное совпадение, UPPERCASE)
4. Пересоздайте секрет если нужно

### Проблема: MT5 не подключается

**Причина:** MT5 не может быть установлен на GitHub-hosted runner

**Решение:**
- **Вариант 1:** Используйте Yahoo Finance режим (job: paper-trading-yahoo)
- **Вариант 2:** Настройте self-hosted runner на Windows с MT5

### Проблема: State не сохраняется между запусками

**Причина:** Artifact не создается или не загружается

**Решение:**
1. Проверьте что шаг "Upload trading state" выполнился
2. Проверьте что artifact появился в разделе Artifacts
3. Проверьте `if: always()` в workflow (должно быть)
4. Retention days должны быть > 1 (по умолчанию 90)

### Проблема: Telegram не отправляет уведомления

**Причина:** Бот не запущен или неверные credentials

**Решение:**
1. Найдите бота в Telegram и отправьте `/start`
2. Проверьте TELEGRAM_BOT_TOKEN в Secrets
3. Проверьте TELEGRAM_CHAT_ID в Secrets
4. Для каналов: убедитесь что бот добавлен как администратор
5. Проверьте логи в GitHub Actions на наличие ошибок Telegram API

---

## 📈 Оптимизация и best practices

### 1. Расписание

**Для H1 таймфрейма:**
- ✅ Проверять каждый час: `0 * * * *`
- ❌ Не проверять каждые 5 минут (перегрузка API)

**Для M15 таймфрейма:**
- ✅ Проверять каждые 15 минут: `*/15 * * * *`

**Умное расписание:**
```yaml
# Активно в рабочие часы, редко ночью
- cron: '*/30 9-17 * * 1-5'  # Каждые 30 мин 9-17 UTC пн-пт
- cron: '0 */2 18-8 * * 1-5'  # Каждые 2 часа остальное время
- cron: '0 */4 * * 0,6'       # Каждые 4 часа в выходные
```

### 2. Timeout и performance

```yaml
# В workflow:
timeout-minutes: 55  # Оставьте буфер (max 60 min для бесплатного плана)
```

```python
# В боте: минимизируйте время выполнения
# - Кэшируйте данные если возможно
# - Оптимизируйте calculations
# - Используйте vectorization (pandas/numpy)
```

### 3. Artifacts retention

```yaml
# Краткосрочные данные (логи)
retention-days: 30

# Долгосрочные данные (state, статистика)
retention-days: 90
```

### 4. Мониторинг затрат

```bash
# Проверяйте использование минут:
# Settings → Billing and plans → Actions minutes

# Оптимизация:
# 1. Используйте cache для dependencies
# 2. Уменьшите частоту запусков в непиковые часы
# 3. Используйте условные запуски (skip на выходных если рынок закрыт)
```

---

## 🎓 Дополнительные материалы

### Документация

- **[GITHUB_ACTIONS_QUICKSTART.md](GITHUB_ACTIONS_QUICKSTART.md)** - Быстрый старт за 5 минут
- **[.github/GITHUB_ACTIONS_SETUP.md](.github/GITHUB_ACTIONS_SETUP.md)** - Полная документация по настройке
- **[.env.github_actions.example](.env.github_actions.example)** - Пример переменных окружения
- **[smc_trading_strategy/PAPER_TRADING_SETUP.md](smc_trading_strategy/PAPER_TRADING_SETUP.md)** - Paper trading setup
- **[smc_trading_strategy/README_MT5.md](smc_trading_strategy/README_MT5.md)** - MT5 documentation

### External Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Cron Expression Generator](https://crontab.guru/)
- [GitHub Actions Status](https://www.githubstatus.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [MetaTrader5 Python Documentation](https://www.mql5.com/en/docs/integration/python_metatrader5)

---

## 🤝 Contributing

Если вы нашли баг или хотите предложить улучшение:

1. Проверьте existing issues
2. Создайте новый issue с подробным описанием
3. Для bug reports: включите логи и воспроизводимые шаги
4. Для feature requests: опишите use case и предполагаемое поведение

---

## 📝 Changelog

### Version 1.0 (2025-01-01)
- ✅ Первый релиз GitHub Actions integration
- ✅ Поддержка MT5 и Yahoo Finance режимов
- ✅ State persistence через artifacts
- ✅ Telegram notifications
- ✅ Comprehensive documentation

---

## ⚖️ Disclaimer

⚠️ **ВАЖНО:**

1. Это **PAPER TRADING** (виртуальная торговля)
2. Не гарантируется прибыль на реальных счетах
3. Прошлые результаты не гарантируют будущие
4. Используйте на свой риск
5. Всегда тестируйте на demo счетах перед реальной торговлей
6. Автор не несет ответственности за убытки

---

## 📞 Поддержка

Если возникли вопросы:

1. Проверьте документацию (QUICKSTART и SETUP)
2. Просмотрите Troubleshooting раздел
3. Проверьте логи в GitHub Actions
4. Создайте issue на GitHub (если баг)

---

## ✅ Готово!

Теперь у вас есть полностью автоматизированная система paper trading на GitHub Actions! 🚀

**Следующие шаги:**
1. ✅ Настройте GitHub Secrets
2. ✅ Запустите workflow вручную для теста
3. ✅ Проверьте логи и Telegram уведомления
4. ✅ Настройте расписание
5. ✅ Мониторьте первую неделю внимательно
6. 📊 Анализируйте статистику через месяц
7. 💼 Рассмотрите реальную торговлю (после 2+ месяцев успешного тестирования)

**Удачной торговли! 💰📈**
