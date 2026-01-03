# 🚀 Stock Long-Term Strategy - Quick Start Guide

## ⚡ 5-минутный старт

### 1. Простой тест (1 команда)
```bash
cd /workspace/smc_trading_strategy && python3 test_stock_simple.py
```

**Что произойдет:**
- Генерация данных AAPL (365 дней)
- Запуск стратегии
- Показ результатов
- Примеры сигналов

**Ожидаемый результат:**
```
✅ Generated 102 signals
📊 Total Trades: 37
📈 Win Rate: 43.24%
💰 Total Return: -1.38%
```

### 2. Полный бэктест с графиками
```bash
cd /workspace/smc_trading_strategy && python3 run_stock_backtest.py
```

**Что произойдет:**
- Тесты на Daily (1D)
- Тесты на Weekly (1W)
- Сравнение таймфреймов
- Тесты Fibonacci уровней
- Генерация графиков PNG

## 📝 Основные команды

### Генерация данных
```python
from stock_data_loader import generate_stock_data

# Дневные данные
df = generate_stock_data(
    ticker="AAPL",
    timeframe='1D',
    periods=365
)

# Недельные данные
df = generate_stock_data(
    ticker="MSFT",
    timeframe='1W',
    periods=104  # 2 года
)
```

### Запуск стратегии
```python
from stock_long_term_strategy import StockLongTermStrategy

# Создание стратегии
strategy = StockLongTermStrategy(
    timeframe='1D',
    risk_reward_ratio=2.0,
    use_fibonacci_tp=False
)

# Генерация сигналов
df_signals = strategy.run_strategy(df)

# Посмотреть сигналы
signals = df_signals[df_signals['signal'] != 0]
print(signals[['signal', 'entry_price', 'stop_loss', 'take_profit', 'signal_reason']])
```

### Бэктест
```python
from backtester import Backtester

backtester = Backtester(
    initial_capital=10000,
    commission=0.001,
    slippage=0.0005
)

results = backtester.run(df_signals)
backtester.print_results(results)
```

## 🎯 Настройка под себя

### Агрессивная торговля (больше сигналов)
```python
strategy = StockLongTermStrategy(
    timeframe='1D',
    risk_reward_ratio=1.8,         # Меньший R:R
    swing_length=10,                # Короче свинги
    min_candle_quality=20,          # Ниже порог
    min_volume_ratio=0.7,           # Мягче фильтр объема
    cooldown_candles=1              # Меньше кулдаун
)
```

### Консервативная торговля (качество > количество)
```python
strategy = StockLongTermStrategy(
    timeframe='1D',
    risk_reward_ratio=3.0,          # Больший R:R
    swing_length=20,                # Длиннее свинги
    min_candle_quality=50,          # Выше порог
    min_volume_ratio=1.5,           # Строже фильтр объема
    cooldown_candles=5,             # Больше кулдаун
    use_fibonacci_tp=True,          # Fibonacci TP
    fib_extension=1.618
)
```

### Только Short (лучший Win Rate: 57%)
```python
strategy = StockLongTermStrategy(
    timeframe='1D',
    risk_reward_ratio=2.5
)

# После генерации сигналов, оставить только Short
df_signals_short = df_signals.copy()
df_signals_short.loc[df_signals_short['signal'] == 1, 'signal'] = 0
```

## 📊 Параметры по умолчанию

### Daily (1D)
```python
timeframe = '1D'
risk_reward_ratio = 2.5
risk_per_trade = 0.02
swing_length = 15
volume_lookback = 3
min_candle_quality = 30
use_fibonacci_tp = True
fib_extension = 1.618
min_volume_ratio = 1.0
cooldown_candles = 3
```

### Weekly (1W)
```python
timeframe = '1W'
risk_reward_ratio = 3.0
risk_per_trade = 0.02
swing_length = 8
volume_lookback = 2
min_candle_quality = 25
use_fibonacci_tp = True
fib_extension = 1.618
min_volume_ratio = 1.0
cooldown_candles = 1
```

## 🔍 Анализ результатов

### Показать все сигналы
```python
signals = df_signals[df_signals['signal'] != 0]
print(f"Total signals: {len(signals)}")
print(f"Long: {(signals['signal'] == 1).sum()}")
print(f"Short: {(signals['signal'] == -1).sum()}")
```

### Показать сделки
```python
import pandas as pd

trades_df = pd.DataFrame([t.to_dict() for t in backtester.trades])

# Выигрышные сделки
winners = trades_df[trades_df['pnl_pct'] > 0]
print(f"\nWinners: {len(winners)}")
print(winners[['entry_time', 'direction', 'pnl_pct']].head())

# Проигрышные сделки
losers = trades_df[trades_df['pnl_pct'] < 0]
print(f"\nLosers: {len(losers)}")
print(losers[['entry_time', 'direction', 'pnl_pct']].head())
```

### Анализ по месяцам
```python
trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
monthly = trades_df.groupby('month').agg({
    'pnl_pct': ['count', 'sum', 'mean'],
    'direction': lambda x: (x == 'LONG').sum()
})
print(monthly)
```

## 🎓 Понимание сигналов

### Scoring System
Каждый сигнал имеет счет (score). Минимум 5 баллов для входа.

**Пример Long сигнала:**
```
Above_SMA50 (2) + Bullish_OB (2) + Bullish_FVG (2) + 
Bullish_Candle (1) + Score_7
```

**Расшифровка:**
- Цена выше SMA 50 (тренд вверх)
- Найден Bullish Order Block
- Найден Bullish Fair Value Gap
- Текущая свеча бычья
- Общий счет: 7 баллов (хороший сигнал!)

### Signal Reasons
В `signal_reason` видны все условия, которые выполнились:

```python
# Посмотреть самые сильные сигналы
signals['score'] = signals['signal_reason'].str.extract(r'Score_(\d+)').astype(float)
best_signals = signals.nlargest(10, 'score')
print(best_signals[['signal', 'score', 'signal_reason']])
```

## 🐛 Troubleshooting

### Мало сигналов (< 10)
```python
# Понизить минимальный score
# В stock_long_term_strategy.py, строка ~200:
MIN_SCORE = 4  # вместо 5
```

### Много ложных сигналов
```python
# Повысить минимальный score
MIN_SCORE = 6  # вместо 5

# Или добавить дополнительные фильтры
strategy = StockLongTermStrategy(
    min_candle_quality=40,
    min_volume_ratio=1.3,
    require_sma_trend=True  # требовать тренд по SMA
)
```

### Слишком много Stop Loss
```python
# Увеличить буфер стопов
# В stock_long_term_strategy.py, метод _calculate_stop_loss:
# Для Long: stop = swing_stop * 0.995  # вместо 0.998
# Для Short: stop = swing_stop * 1.005  # вместо 1.002
```

## 📁 Структура файлов

```
smc_trading_strategy/
├── stock_long_term_strategy.py    ← Основная стратегия
├── stock_data_loader.py           ← Генератор данных
├── run_stock_backtest.py          ← Полный бэктест
├── test_stock_simple.py           ← Быстрые тесты ⭐ START HERE
├── STOCK_LONGTERM_README.md       ← Полная документация
├── STOCK_STRATEGY_RESULTS.md      ← Результаты
├── STOCK_TRADING_SUMMARY.md       ← Краткая сводка
└── STOCK_QUICK_START.md           ← Этот файл
```

## 🎯 Next Steps

1. **Запустить тест:** `python3 test_stock_simple.py`
2. **Изучить результаты:** Посмотреть Win Rate, сигналы
3. **Настроить параметры:** Поэкспериментировать
4. **Прочитать документацию:** `STOCK_LONGTERM_README.md`
5. **Оптимизировать:** Найти лучшие параметры

## 💡 Tips

1. **Start simple:** Сначала используйте `test_stock_simple.py`
2. **Understand scoring:** Изучите систему баллов
3. **Test parameters:** Экспериментируйте с параметрами
4. **Focus on Short:** Они показывают лучший результат (57% WR)
5. **Use Fibonacci:** Fibonacci TP часто лучше фиксированного R:R

## 🆘 Помощь

- **Полная документация:** `STOCK_LONGTERM_README.md`
- **Результаты тестов:** `STOCK_STRATEGY_RESULTS.md`
- **Сводка проекта:** `STOCK_TRADING_SUMMARY.md`

---

**Начните с:** `python3 test_stock_simple.py`  
**Время:** ~5 минут  
**Результат:** Понимание как работает стратегия
