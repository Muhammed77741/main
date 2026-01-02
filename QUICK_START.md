# 🚀 Quick Start - Pattern Recognition V7 HYBRID

## Быстрый старт для использования стратегии

---

## 📊 Что это?

**V7 HYBRID** - финальная версия торговой стратегии для XAUUSD (Gold) на 1H timeframe.

**Результаты** (backtest 1 год):
- 💰 PnL: **+382%**
- 🎯 Win Rate: **66.2%**
- 📉 Max Drawdown: **-7.67%**
- 📈 Сделок: **450** (~1.23 в день)

---

## 🎯 Суть стратегии

### Два источника сигналов:

1. **BASELINE (320 сделок, +374%)**
   - Pattern Recognition (1.618 Fib patterns)
   - БЕЗ breakeven (максимальная прибыль)
   - WR: 63.4%

2. **30-PIP (130 сделок, +8%)**
   - Детектор сильных движений 30+ pips
   - С breakeven @ 25 pips (защита)
   - WR: 73.1%

---

## 💻 Как использовать

### 1. Установка

```python
# Убедитесь что у вас есть все файлы:
# - pattern_recognition_optimized_v2.py
# - thirty_pip_detector_final_v2.py
# - pattern_recognition_v7_hybrid.py
```

### 2. Импорт

```python
import pandas as pd
from pattern_recognition_v7_hybrid import PatternRecognitionV7Hybrid

# Загрузите данные
df = pd.read_csv('XAUUSD_1H.csv')
df['timestamp'] = pd.to_datetime(df['datetime'])
df = df.set_index('timestamp')
df = df[['open', 'high', 'low', 'close', 'volume']]
```

### 3. Инициализация стратегии

```python
strategy = PatternRecognitionV7Hybrid(
    fib_mode='standard',           # Fibonacci mode
    tp_multiplier=1.4,             # TP = 1.4 × SL distance
    enable_30pip_patterns=True,    # Включить 30-pip detector
    high_confidence_only=True,     # Только HIGH confidence
    pip_breakeven_trigger=25,      # Breakeven для 30-pip @ 25 pips
    pip_trailing_trigger=40        # Trailing для 30-pip @ 40 pips
)
```

### 4. Получить сигналы

```python
# Получить все сигналы
signals_df = strategy.run_strategy(df)

# signals_df содержит:
# - time: Время входа
# - type: 'LONG' или 'SELL'
# - entry_price: Цена входа
# - stop_loss: Стоп-лосс
# - take_profit: Тейк-профит
# - source: 'BASELINE' или '30PIP'
# - pattern: Название паттерна
# - detector_pattern: Тип детектора (для 30PIP)

print(f"Total signals: {len(signals_df)}")
print(signals_df.head())
```

### 5. Backtest (опционально)

```python
# Полный backtest с расчётом PnL
results_df = strategy.backtest(df)

# results_df содержит:
# - entry_time: Время входа
# - pnl_pct: Прибыль/убыток в %
# - exit_type: Как закрылась сделка
# - breakeven_used: Был ли использован breakeven
# - source, pattern, etc.

print(f"Total PnL: {results_df['pnl_pct'].sum():.2f}%")
```

---

## 📋 Пример использования в боте

```python
import pandas as pd
from pattern_recognition_v7_hybrid import PatternRecognitionV7Hybrid
import MetaTrader5 as mt5

# Инициализация
mt5.initialize()
strategy = PatternRecognitionV7Hybrid()

# Получить последние данные
def get_latest_data():
    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 100)
    df = pd.DataFrame(rates)
    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'tick_volume']]
    df = df.rename(columns={'tick_volume': 'volume'})
    return df

# Проверка сигналов каждый час
while True:
    df = get_latest_data()
    
    # Получить сигналы
    signals = strategy.run_strategy(df)
    
    # Проверить последний сигнал
    if len(signals) > 0:
        latest_signal = signals.iloc[-1]
        
        # Если сигнал новый (в текущий час)
        if latest_signal['time'] == df.index[-1]:
            print(f"🎯 NEW SIGNAL!")
            print(f"   Type: {latest_signal['type']}")
            print(f"   Entry: {latest_signal['entry_price']:.2f}")
            print(f"   SL: {latest_signal['stop_loss']:.2f}")
            print(f"   TP: {latest_signal['take_profit']:.2f}")
            print(f"   Source: {latest_signal['source']}")
            print(f"   Pattern: {latest_signal['pattern']}")
            
            # Отправить ордер в MT5
            # ... ваш код для отправки ордера
    
    # Ждать 1 час
    time.sleep(3600)
```

---

## ⚙️ Настройки

### Агрессивный режим (max PnL):
```python
strategy = PatternRecognitionV7Hybrid(
    enable_30pip_patterns=False,  # Только baseline
    # Результат: +374% PnL, WR 63.4%
)
```

### Консервативный режим (high WR):
```python
strategy = PatternRecognitionV7Hybrid(
    enable_30pip_patterns=True,
    pip_breakeven_trigger=20,     # Более ранний breakeven
    pip_trailing_trigger=30       # Более ранний trailing
    # Результат: выше WR, ниже PnL
)
```

### Баланс (рекомендуется):
```python
strategy = PatternRecognitionV7Hybrid(
    enable_30pip_patterns=True,
    pip_breakeven_trigger=25,     # По умолчанию
    pip_trailing_trigger=40       # По умолчанию
    # Результат: +382% PnL, WR 66.2%
)
```

---

## 📊 Понимание выходов

### BASELINE signals:
- **TP**: Достигнут тейк-профит
- **SL**: Сработал стоп-лосс
- **TIMEOUT**: Закрыто через 24 часа по текущей цене

### 30-PIP signals:
- **Partial_TP**: Закрыто 50% позиции @ 30 pips (только MOMENTUM/BOUNCE)
- **BE@25p**: Активирован breakeven @ 25 pips
- **Trail@40p**: Активирован trailing SL @ 40 pips
- **BE_SL**: Закрыто по breakeven SL (защита сработала!)
- **Trail_SL**: Закрыто по trailing SL
- **TP**: Достигнут полный TP

Пример: `Partial_TP→BE@25p→Trail@40p→Trail_SL` означает:
1. Закрыли 50% @ 30 pips
2. Переместили SL на breakeven @ 25 pips
3. Активировали trailing @ 40 pips
4. Закрыли остаток по trailing SL

---

## 🎯 Что делать с сигналами

### 1. Проверить сигнал:
```python
if signal['source'] == 'BASELINE':
    # Проверенный сигнал, высокая надёжность
    pass
elif signal['source'] == '30PIP':
    # Новый паттерн, защищён breakeven
    print(f"30-Pip pattern: {signal['detector_pattern']}")
```

### 2. Установить ордер:
```python
entry = signal['entry_price']
sl = signal['stop_loss']
tp = signal['take_profit']

# Для 30-PIP: учитывайте что будет Partial TP
if signal['source'] == '30PIP' and signal['detector_pattern'] == 'MOMENTUM':
    # 50% закроется @ entry + 30 pips
    partial_tp = entry + (30 * 0.10)  # 0.10 = 1 pip для XAUUSD
```

### 3. Управление позицией:

**BASELINE**:
- Оставить как есть
- Дождаться TP/SL/Timeout

**30-PIP (MOMENTUM/BOUNCE)**:
- @ +30 pips: Закрыть 50% (Partial TP)
- @ +25 pips: SL → Breakeven
- @ +40 pips: Trailing SL активируется

**30-PIP (PULLBACK/VOLATILITY)**:
- @ +25 pips: SL → Breakeven
- @ +40 pips: Trailing SL активируется
- NO Partial TP (пусть растёт!)

---

## 📈 Ожидаемые результаты

### Месячная прибыль:
```
Annual: +382%
Monthly: +382% / 12 ≈ +31.8% в месяц
```

### Частота сигналов:
```
Total: 450 signals / 365 days ≈ 1.23 signals/day
Baseline: 320 / 365 ≈ 0.88 signals/day
30-Pip: 130 / 365 ≈ 0.36 signals/day
```

### Win Rate по источникам:
```
Baseline: 63.4%
30-Pip: 73.1% (благодаря breakeven!)
Overall: 66.2%
```

---

## ⚠️ Важно!

### 1. Это backtest результаты
- Реальная торговля может отличаться
- Учитывайте спреды, комиссии, проскальзывание
- Используйте risk management!

### 2. Risk Management:
```python
# Рекомендация: Риск 1-2% на сделку
account_balance = 10000  # USD
risk_per_trade = 0.01    # 1%

# Расчёт лота
sl_distance_pips = (entry_price - stop_loss) / 0.10
pip_value = 0.10  # Для XAUUSD 1 pip = $0.10 per micro lot
lot_size = (account_balance * risk_per_trade) / (sl_distance_pips * pip_value)
```

### 3. Мониторинг:
- Следите за Drawdown
- Если DD > -10%: остановитесь и пересмотрите
- Сохраняйте логи всех сделок

---

## 📁 Файлы стратегии

```
smc_trading_strategy/
├── pattern_recognition_v7_hybrid.py        ← MAIN (запускать это!)
├── pattern_recognition_optimized_v2.py     ← Baseline strategy
├── thirty_pip_detector_final_v2.py         ← 30-Pip detector
├── detect_30pip_patterns.py                ← 30-Pip pattern logic
└── pattern_recognition_strategy.py         ← Base classes

FINAL_STRATEGY_REPORT.md                    ← Полный отчёт
QUICK_START.md                              ← Этот файл
```

---

## 🆘 Troubleshooting

### Проблема: "No signals generated"
**Решение**: Убедитесь что данные в правильном формате (timestamp index, колонки: open, high, low, close, volume)

### Проблема: Слишком мало сигналов
**Решение**: Проверьте настройки `high_confidence_only=True` - можно попробовать `False` для большего числа сигналов (но ниже качество)

### Проблема: Drawdown больше чем ожидалось
**Решение**: 
1. Проверьте risk per trade (должен быть 1-2%)
2. Убедитесь что используете TP/SL из сигналов
3. Рассмотрите использование `pip_breakeven_trigger=20` (более ранний breakeven)

---

## 🎓 Дополнительные ресурсы

- **FINAL_STRATEGY_REPORT.md**: Детальный анализ всех версий
- **OPTIMIZATION_REPORT.md**: Процесс оптимизации baseline
- **MISSED_OPPORTUNITIES_REPORT.md**: Анализ 30-pip паттернов

---

**Удачной торговли! 🚀**

**Version**: 7.0 (HYBRID)
**Last Updated**: 2026-01-01
