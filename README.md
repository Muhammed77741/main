# Trading Strategies Repository

## 📊 Проекты

### 🥇 SMC Trading Strategy (Gold - 1H)
Внутридневная торговля золотом с использованием Smart Money Concepts.
- **Папка:** `smc_trading_strategy/`
- **Таймфрейм:** 1 час
- **Лучшая стратегия:** Pattern Recognition (Continuation) - +186.91%
- **Документация:** [smc_trading_strategy/README.md](smc_trading_strategy/README.md)

### 📈 Stock Long-Term Strategy (NEW!)
**Ветка:** `cursor/stock-trading-long-term-9d4a`  
**Папка:** `main/stock_smc_trading/` ⭐

Долгосрочная торговля акциями на дневных и недельных таймфреймах.
- **Таймфреймы:** 1 день (1D) и 1 неделя (1W)
- **Scoring System:** Гибкая система подсчета баллов
- **Тестировано:** ✅ 37 сделок, 43% Win Rate, 0.97 Profit Factor
- **Документация:** 
  - [README.md](main/stock_smc_trading/README.md) - Главная документация
  - [STOCK_QUICK_START.md](main/stock_smc_trading/STOCK_QUICK_START.md) - Быстрый старт
  - [STOCK_LONGTERM_README.md](main/stock_smc_trading/STOCK_LONGTERM_README.md) - Полное руководство
  - [STOCK_STRATEGY_RESULTS.md](main/stock_smc_trading/STOCK_STRATEGY_RESULTS.md) - Результаты
  - [STOCK_TRADING_SUMMARY.md](main/stock_smc_trading/STOCK_TRADING_SUMMARY.md) - Сводка

#### 🚀 Быстрый старт:
```bash
cd main/stock_smc_trading

# Установка зависимостей
pip install -r requirements.txt

# Простой тест (5 минут)
python3 test_stock_simple.py

# Полный бэктест с графиками
python3 run_stock_backtest.py
```

#### 📁 Структура проекта:
```
main/stock_smc_trading/
├── README.md                      # Главная документация
├── requirements.txt               # Зависимости
├── __init__.py                    # Package init
│
├── stock_long_term_strategy.py    # Основная стратегия (630 строк)
├── stock_data_loader.py           # Генератор данных (276 строк)
├── run_stock_backtest.py          # Полный бэктест (417 строк)
├── test_stock_simple.py           # Простые тесты (126 строк)
│
├── smc_indicators.py              # SMC индикаторы
├── volume_analysis.py             # Анализ объема
├── backtester.py                  # Бэктестер
│
└── Документация (4 файла)
```

**Всего:** 1449 строк кода + 30KB документации

## 🎯 Особенности Stock Strategy

### Scoring System
Вместо жесткого AND logic используется система баллов (минимум 5 из 15+):
- Trend filters (SMA 50/200, Golden/Death Cross)
- SMC patterns (Order Blocks, FVG, BOS)
- Volume confirmation
- Candle quality
- Price action

### Multi-Timeframe
- **Daily (1D):** 5-10 сделок/месяц, средняя длительность ~11 дней
- **Weekly (1W):** 1-3 сделки/месяц, долгосрочные позиции

### Risk Management
- 2% риска на сделку
- ATR-based stops
- Fixed R:R (2.0-3.0) или Fibonacci TP (1.618)
- Cooldown между сделками

## 📊 Сравнение Стратегий

| Параметр | Gold 1H | Stocks 1D |
|----------|---------|-----------|
| Timeframe | 1 час | 1 день |
| Trades/Year | 200-400 | 30-50 |
| Win Rate | 65-70% | 40-50% |
| Holding | 2-12h | 5-30 дней |
| Stress | Высокий | Средний |
| Best For | Активный трейдинг | Долгосрочные инвестиции |

## 🔧 Установка

```bash
# Зависимости
pip install pandas numpy matplotlib

# Опционально
pip install yfinance  # для реальных данных
```

## 📝 TODO

### Stock Strategy v1.1
- [ ] Улучшить Win Rate (43% → 50%+)
- [ ] Trailing stops
- [ ] ML-based scoring weights
- [ ] Multi-timeframe confirmation

### Stock Strategy v2.0
- [ ] Интеграция с yfinance (реальные данные)
- [ ] Portfolio management
- [ ] Sector rotation
- [ ] Real-time alerts

## 📚 Документация

### Stock Trading:
- [README.md](main/stock_smc_trading/README.md) - Главная документация
- [STOCK_QUICK_START.md](main/stock_smc_trading/STOCK_QUICK_START.md) - Быстрый старт
- [STOCK_LONGTERM_README.md](main/stock_smc_trading/STOCK_LONGTERM_README.md) - Полное руководство
- [STOCK_STRATEGY_RESULTS.md](main/stock_smc_trading/STOCK_STRATEGY_RESULTS.md) - Анализ результатов
- [STOCK_TRADING_SUMMARY.md](main/stock_smc_trading/STOCK_TRADING_SUMMARY.md) - Краткая сводка

### Gold Trading:
- [smc_trading_strategy/README.md](smc_trading_strategy/README.md) - Основная документация
- [smc_trading_strategy/FINAL_RESULTS.md](smc_trading_strategy/FINAL_RESULTS.md) - Детальные результаты

## 🤝 Contributing

Идеи и улучшения приветствуются!

## 📄 License

MIT

---

**Последнее обновление:** 2 января 2026  
**Статус:** ✅ Stock Strategy - Production Ready для оптимизации
