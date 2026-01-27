# Position Size Format Unification - Implementation Summary

## Задача / Task
Привести размер позиций в Live Trading GUI и Backtest (Signal Analysis GUI) к единому формату:
- для криптовалют использовать проценты от текущей цены (например, 0.5%, 1%, 2%);
- для Forex использовать пункты / pips (например, 10 пунктов, 20 пунктов и т.д.);

Bring position sizes in Live Trading GUI and Backtest (Signal Analysis GUI) to a unified format:
- for cryptocurrencies use percentages of current price (e.g., 0.5%, 1%, 2%);
- for Forex use pips (e.g., 10 pips, 20 pips, etc.);

**ВАЖНО / IMPORTANT:** Формат определяется по символу (BTC, ETH, SOL = крипто), а не по бирже (MT5 vs Binance).
Format is determined by SYMBOL (BTC, ETH, SOL = crypto), not by EXCHANGE (MT5 vs Binance).

## Реализация / Implementation

### 1. Live Trading GUI (settings_dialog.py)

**Изменения:**
- Добавлена функция `is_crypto_symbol()` для определения типа актива по символу
- Добавлена динамическая установка суффикса для всех полей TP/SL
- Для криптовалют (BTC, ETH, SOL и т.д.): используется суффикс `"%"`
- Для Forex/Commodities (XAUUSD, EURUSD и т.д.): используется суффикс `" pips"`
- Обновлена метка единиц измерения с "points" на "pips"

**Changes:**
- Added `is_crypto_symbol()` function to determine asset type by symbol
- Added dynamic suffix setting for all TP/SL fields
- For crypto (BTC, ETH, SOL, etc.): uses `"%"` suffix
- For Forex/Commodities (XAUUSD, EURUSD, etc.): uses `" pips"` suffix
- Updated unit label from "points" to "pips"

**Код / Code:**
```python
def is_crypto_symbol(symbol: str) -> bool:
    """Check if symbol is cryptocurrency (BTC, ETH, SOL, etc.)"""
    if not symbol:
        return False
    symbol_upper = symbol.upper()
    crypto_keywords = ['BTC', 'ETH', 'XRP', 'LTC', 'ADA', 'DOT', 'DOGE', 'SOL', 'AVAX', 'MATIC']
    return any(keyword in symbol_upper for keyword in crypto_keywords)

# Set suffix based on symbol type, not exchange
is_crypto = is_crypto_symbol(self.original_config.symbol)
suffix = "%" if is_crypto else " pips"
self.trend_tp1_spin.setSuffix(suffix)
```

### 2. Backtest GUI (signal_analysis_dialog.py)

**Изменения:**
- Изменен формат для криптовалют с базисных пунктов (150) на проценты (1.5)
- Добавлен суффикс `"%"` для криптовалют, `" pips"` для Forex
- Удалено деление на 100 при использовании кастомных TP уровней для криптовалют
- Добавлена логика миграции для старых сохраненных настроек
- Обновлены подсказки для консистентности

**Changes:**
- Changed crypto format from basis points (150) to percentage (1.5)
- Added `"%"` suffix for crypto, `" pips"` suffix for Forex
- Removed division by 100 when using crypto custom TP levels
- Added migration logic for old saved settings
- Updated tooltips for consistency

**Функция обновления меток / Label update function:**
```python
def update_tp_sl_labels(self):
    symbol = self.symbol_combo.currentText()
    is_crypto = is_crypto_symbol(symbol)
    
    if not is_crypto:
        # Forex/Commodities - show pips
        self.trend_tp1_spin.setSuffix(" pips")
        self.trend_tp1_spin.setValue(MT5_TREND_TP['tp1'])  # e.g., 30
    else:
        # Crypto - show percentages
        self.trend_tp1_spin.setSuffix("%")
        self.trend_tp1_spin.setValue(CRYPTO_TREND_TP['tp1'])  # e.g., 1.5
```

**Логика миграции / Migration logic:**
```python
# Migrate old format to new format for crypto symbols
if is_crypto and settings.get('trend_tp1', 0) > 10:
    # Convert old basis points to percentage
    settings['trend_tp1'] = settings.get('trend_tp1', 150) / 100.0  # 150 → 1.5
    # Save migrated values
    with open(config_file, 'w') as f:
        json.dump(settings, f, indent=2)
```

## Формат значений / Value Format

### Криптовалюты / Cryptocurrencies (BTC/ETH)

**TREND Mode:**
- TP1: 1.5% (отображается как "1.5%" / displayed as "1.5%")
- TP2: 2.75% (отображается как "2.75%" / displayed as "2.75%")
- TP3: 4.5% (отображается как "4.5%" / displayed as "4.5%")
- SL: 0.8% (отображается как "0.8%" / displayed as "0.8%")

**RANGE Mode:**
- TP1: 1.0% (отображается как "1.0%" / displayed as "1.0%")
- TP2: 1.75% (отображается как "1.75%" / displayed as "1.75%")
- TP3: 2.5% (отображается как "2.5%" / displayed as "2.5%")
- SL: 0.6% (отображается как "0.6%" / displayed as "0.6%")

### Forex/Commodities (XAUUSD, EURUSD, etc.)

**TREND Mode:**
- TP1: 30 pips (отображается как "30 pips" / displayed as "30 pips")
- TP2: 55 pips (отображается как "55 pips" / displayed as "55 pips")
- TP3: 90 pips (отображается как "90 pips" / displayed as "90 pips")
- SL: 16 pips (отображается как "16 pips" / displayed as "16 pips")

**RANGE Mode:**
- TP1: 20 pips (отображается как "20 pips" / displayed as "20 pips")
- TP2: 35 pips (отображается как "35 pips" / displayed as "35 pips")
- TP3: 50 pips (отображается как "50 pips" / displayed as "50 pips")
- SL: 12 pips (отображается как "12 pips" / displayed as "12 pips")

## Поддерживаемые символы / Supported Symbols

### Криптовалюты (используют %) / Cryptocurrencies (use %)
- **Binance:** BTC/USDT, ETH/USDT (через Binance API)
- **MT5:** BTCUSD, ETHUSD, SOLUSD (через MT5)

### Forex/Commodities (используют pips) / Forex/Commodities (use pips)
- **MT5:** XAUUSD, EURUSD, GBPUSD, USDJPY и т.д. / etc.

## Тестирование / Testing

### Созданные тесты / Created Tests

1. **test_position_size_format.py**
   - Проверяет наличие динамических суффиксов
   - Проверяет формат значений для криптовалют и Forex
   - Проверяет логику миграции

2. **validate_format_consistency.py**
   - Проверяет консистентность форматов между Live Trading и Backtest GUI
   - Проверяет правильность констант
   - Проверяет создание конфигураций

### Результаты тестов / Test Results

```
✓ All tests passed!

Summary of changes:
1. ✓ Live Trading GUI uses % for crypto, pips for Forex
2. ✓ Backtest GUI uses % for crypto, pips for Forex
3. ✓ Format is consistent between both GUIs
4. ✓ Migration logic handles old saved settings
5. ✓ Values are stored correctly (no *100 for crypto)
```

## Обратная совместимость / Backward Compatibility

Для обеспечения обратной совместимости со старыми сохраненными настройками:
- Добавлена проверка: если значения для криптовалют > 10, они автоматически конвертируются
- Старый формат: 150 (базисные пункты) → Новый формат: 1.5 (проценты)
- Миграция происходит автоматически при загрузке настроек

To ensure backward compatibility with old saved settings:
- Added check: if crypto values > 10, they are automatically converted
- Old format: 150 (basis points) → New format: 1.5 (percentage)
- Migration happens automatically when loading settings

## Изменённые файлы / Changed Files

1. **trading_app/gui/settings_dialog.py**
   - Добавлены суффиксы для всех TP/SL полей
   - Обновлена метка единиц измерения

2. **trading_app/gui/signal_analysis_dialog.py**
   - Изменен формат отображения для криптовалют
   - Добавлена логика миграции
   - Обновлены подсказки
   - Удалено деление на 100 для кастомных TP уровней

3. **test_position_size_format.py** (новый / new)
   - Тестирование реализации

4. **validate_format_consistency.py** (новый / new)
   - Проверка консистентности форматов

5. **test_mt5_crypto_symbols.py** (новый / new)
   - Тестирование MT5 криптовалют (BTCUSD, ETHUSD, SOLUSD)

## Выводы / Conclusions

✅ Формат позиций унифицирован между Live Trading GUI и Backtest GUI
✅ Криптовалюты используют проценты (%) - независимо от биржи
✅ MT5 криптовалюты (BTCUSD, ETHUSD, SOLUSD) также используют %
✅ Forex использует пункты (pips)
✅ Обеспечена обратная совместимость
✅ Все тесты проходят успешно

✅ Position format unified between Live Trading GUI and Backtest GUI
✅ Cryptocurrencies use percentages (%) - regardless of exchange
✅ MT5 crypto pairs (BTCUSD, ETHUSD, SOLUSD) also use %
✅ Forex uses pips
✅ Backward compatibility ensured
✅ All tests pass successfully
