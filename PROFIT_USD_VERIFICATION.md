# Проверка расчета Profit USD в Signal Analysis

## Краткий ответ / Short Answer
✅ **Profit USD рассчитывается ПРАВИЛЬНО** / **Profit USD is calculated CORRECTLY**

## Детальный анализ / Detailed Analysis

### 1. Как рассчитывается profit_pct
В коде на строках 510, 541, 587, 618 и т.д.:
```python
# Для BUY сигналов при достижении TP:
pnl = ((pos['target_tp'] - entry_price) / entry_price) * 100

# Для SELL сигналов при достижении TP:
pnl = ((entry_price - pos['target_tp']) / entry_price) * 100
```

**Пример:**
- Entry price: $100
- TP price: $101.50
- PNL: ((101.50 - 100) / 100) * 100 = 1.5%

**Результат:** profit_pct хранится как **1.5** (не 0.015)

### 2. Как рассчитывается profit_usd
На строке 2862 в `signal_analysis_dialog.py`:
```python
signals_df['profit_usd'] = (signals_df['profit_pct'] / 100.0) * starting_balance
```

**Пример:**
- profit_pct: 1.5 (означает 1.5%)
- starting_balance: $10,000
- profit_usd: (1.5 / 100.0) * 10000 = 0.015 * 10000 = **$150.00**

### 3. Проверка расчета / Calculation Verification

| Profit % | Balance | Formula | Profit USD | Expected | Status |
|----------|---------|---------|------------|----------|--------|
| 1.5% | $10,000 | (1.5/100)*10000 | $150.00 | $150.00 | ✅ |
| -0.8% | $10,000 | (-0.8/100)*10000 | -$80.00 | -$80.00 | ✅ |
| 4.5% | $5,000 | (4.5/100)*5000 | $225.00 | $225.00 | ✅ |
| 2.75% | $10,000 | (2.75/100)*10000 | $275.00 | $275.00 | ✅ |

### 4. Важное замечание / Important Note

**Формат отображения зависит от типа актива:**

#### Для крипто (BTC, ETH, SOL):
- Отображается: `+1.5%` и `$+150.00`
- Оба значения показываются

#### Для Forex (XAUUSD, EURUSD):
- Отображается: `$+150.00` (только USD)
- Процент не показывается в summary (но считается правильно)

**Код (строки 2906-2910):**
```python
if is_crypto:
    pnl_display = f"{total_profit_pct:+.2f}%"
else:
    pnl_display = f"${total_profit_usd:+.2f}"
```

### 5. Где используется profit_usd

**В таблице результатов (строка 3155-3167):**
```python
profit_usd = row.get('profit_usd', 0)
profit_usd_item = QTableWidgetItem(f"${profit_usd:+.2f}")
```

**В summary (строка 2893):**
```python
total_profit_usd = signals_df['profit_usd'].sum()
```

**В расчете средних значений (строка 2928-2936):**
```python
avg_win_usd = signals_df[signals_df['outcome'].str.contains('Win', na=False)]['profit_usd'].mean()
avg_loss_usd = signals_df[signals_df['outcome'].str.contains('Loss', na=False)]['profit_usd'].mean()
```

## Вывод / Conclusion

✅ **Расчет profit_usd математически правильный**
- Формула: `(profit_pct / 100.0) * starting_balance`
- profit_pct корректно хранится как процент (1.5 = 1.5%)
- Деление на 100 правильно конвертирует в десятичное (1.5 → 0.015)
- Умножение на баланс дает правильный USD profit

✅ **Все тесты проходят успешно**
- Проверены разные сценарии (wins, losses, разные балансы)
- Математика корректна
- Отображение корректно для крипто и forex

## Файлы для проверки / Files to Review

1. `trading_app/gui/signal_analysis_dialog.py` - основной код
   - Строка 2862: расчет profit_usd
   - Строки 510, 541, 587, 618: расчет profit_pct
   - Строки 2906-2943: отображение в summary
   - Строки 3155-3167: отображение в таблице

2. `test_profit_usd_calculation.py` - тест для проверки расчета
