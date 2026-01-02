# ⚡ Quick Access - V8 Strategy

## 🚀 Главный файл стратегии:

```bash
smc_trading_strategy/pattern_recognition_v8_final.py
```

---

## 📊 Быстрый старт:

```python
from smc_trading_strategy.pattern_recognition_v8_final import PatternRecognitionV8Final

# Создать стратегию
strategy = PatternRecognitionV8Final()

# Получить сигналы
signals = strategy.run_strategy(df)

# Backtest
results = strategy.backtest(df)
```

---

## 📚 Документация:

1. **README_V8_FINAL.md** - Полная инструкция
2. **QUICK_START.md** - Быстрый старт
3. **FINAL_STRATEGY_REPORT.md** - Детальный отчет

---

## 📈 Результаты V8:

```
Total PnL:    +381.77%
Win Rate:     65.3%
Trades:       450
Drawdown:     -7.68%
Signals/Day:  ~1.23
```

---

## 🎯 Компоненты:

1. **BASELINE** (320 trades, +374%)
   - LONG only
   - Без breakeven

2. **30-PIP** (130 trades, +7.71%)
   - MOMENTUM, PULLBACK, VOLATILITY
   - Breakeven @ 20 pips

---

## 📁 Важные файлы:

### Результаты:
- `smc_trading_strategy/pattern_recognition_v8_final_backtest.csv`

### Зависимости:
- `pattern_recognition_optimized_v2.py` (Baseline)
- `thirty_pip_detector_final_v2.py` (30-Pip)
- `detect_30pip_patterns.py` (Patterns)

---

**Все готово к использованию!** 🎉
