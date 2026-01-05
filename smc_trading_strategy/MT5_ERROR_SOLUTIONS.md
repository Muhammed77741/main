# MT5 Error Solutions / Решения ошибок MT5

## Основные ошибки и их решения

## ⚠️ ВАЖНО: Различие между order_check и order_send

**order_check()** - проверка параметров ордера:
- ✅ Успех: `result.retcode == 0`
- ❌ Ошибка: `result.retcode != 0`

**order_send()** - отправка ордера на сервер:
- ✅ Успех: `result.retcode == 10009` (TRADE_RETCODE_DONE)
- ❌ Ошибка: `result.retcode != 10009`

**НЕ путайте эти коды!** Если вы видите "Order check failed - Return code: 0" - это на самом деле УСПЕХ для order_check!

---

### ❌ Error: "Order send failed: No result"

**Причина:** `mt5.order_send()` возвращает `None` вместо результата

**Решения:**

1. **Включите AutoTrading (Автоматическую торговлю)**
   - В MT5: `Tools > Options > Expert Advisors`
   - Поставьте галочку: `✓ Allow automated trading`
   - Поставьте галочку: `✓ Allow DLL imports`
   - Нажмите `OK` и перезапустите MT5

2. **Проверьте подключение к серверу**
   ```bash
   python test_mt5_connection.py
   ```
   - Терминал должен быть залогинен
   - Должно быть подключение к интернету
   - Сервер брокера должен быть доступен

3. **Проверьте Market Watch**
   - Откройте Market Watch: `Ctrl+M`
   - Найдите `XAUUSD` в списке
   - Если нет - добавьте: правый клик > `Show All` > найдите XAUUSD

4. **Проверьте время торговли**
   - Рынок должен быть открыт
   - Золото торгуется: Пн-Пт (кроме выходных)

### ❌ Error 10027: "Autotrading disabled"

**Решение:**
```
MT5 → Tools → Options → Expert Advisors → Allow automated trading ✓
```

### ❌ Error 10014: "Invalid volume"

**Причины:**
- Лот слишком маленький или большой
- Неправильный шаг лота

**Решение:**
```python
# Проверьте параметры символа
symbol_info = mt5.symbol_info('XAUUSD')
print(f"Min volume: {symbol_info.volume_min}")     # Обычно 0.01
print(f"Max volume: {symbol_info.volume_max}")     # Обычно 100
print(f"Volume step: {symbol_info.volume_step}")   # Обычно 0.01
```

Используйте лот между `volume_min` и `volume_max` с шагом `volume_step`.

### ❌ Error 10015: "Invalid price"

**Причины:**
- Цена слишком далека от рыночной
- Неверное количество знаков после запятой

**Решение:**
```python
# Округлите цену до правильного количества знаков
symbol_info = mt5.symbol_info('XAUUSD')
digits = symbol_info.digits  # Обычно 2 для XAUUSD
price = round(price, digits)
```

### ❌ Error 10016: "Invalid stops"

**Причины:**
- SL/TP слишком близко к цене входа
- Минимальное расстояние не соблюдено

**Решение:**
```python
symbol_info = mt5.symbol_info('XAUUSD')
stops_level = symbol_info.trade_stops_level  # Мин. расстояние в пунктах
point = symbol_info.point

# Для LONG
sl = entry_price - (stops_level + 10) * point  # +10 для запаса
tp = entry_price + (stops_level + 10) * point

# Для SHORT
sl = entry_price + (stops_level + 10) * point
tp = entry_price - (stops_level + 10) * point
```

### ❌ Error 10018: "Market is closed"

**Решение:**
- Дождитесь открытия рынка
- Для золота (XAUUSD): торговля Пн-Пт, 23:00-22:00 GMT
- Проверьте расписание вашего брокера

### ❌ Error 10019: "Not enough money"

**Решения:**
1. Уменьшите размер лота
2. Пополните счет
3. Закройте другие позиции для освобождения маржи

### ❌ Error: "Symbol XAUUSD not found"

**Решения:**
1. Откройте Market Watch (`Ctrl+M`)
2. Правый клик → `Show All`
3. Найдите XAUUSD и добавьте двойным кликом

Или попробуйте альтернативные названия:
- `GOLD`
- `XAU/USD`
- `XAUUSD.m`
- `XAUUSD.raw`

## Использование test_open_position.py

```bash
# Открыть LONG позицию
python test_open_position.py --action v9-long --lot 0.01

# Открыть SHORT позицию
python test_open_position.py --action v9-short --lot 0.01

# С кастомными параметрами
python test_open_position.py --action v9-long --lot 0.02 --sl 150 --tp 450
```

**Параметры:**
- `--action`: Тип сделки (v9-long, v9-short, v8-long, etc.)
- `--lot`: Размер лота (по умолчанию 0.01)
- `--sl`: Stop Loss в пунктах (по умолчанию 100)
- `--tp`: Take Profit в пунктах (по умолчанию 300)
- `--symbol`: Символ для торговли (по умолчанию XAUUSD)

## Проверка перед торговлей

**Шаг 1: Проверьте подключение**
```bash
python test_mt5_connection.py
```
Должно показать:
- ✅ MT5 инициализирован
- ✅ Информация об аккаунте
- ✅ Символ XAUUSD найден
- ✅ Цена получена успешно

**Шаг 2: Включите AutoTrading**
```
MT5 → Tools → Options → Expert Advisors
✓ Allow automated trading
✓ Allow DLL imports
```

**Шаг 3: Проверьте открытие позиции**
```bash
python test_open_position.py --action v9-long --lot 0.01
```

Должно показать:
- ✅ MT5 initialized successfully
- ✅ Symbol ready
- ✅ Order check passed
- ✅ Position opened successfully!

## Отладка проблем

### Если order_check возвращает ошибку:
```python
import MetaTrader5 as mt5

mt5.initialize()
result = mt5.order_check(request)

if result:
    print(f"Return code: {result.retcode}")
    print(f"Comment: {result.comment}")
else:
    print(f"Error: {mt5.last_error()}")
```

### Если order_send возвращает None:
1. Проверьте AutoTrading
2. Проверьте логин в MT5
3. Проверьте подключение к серверу
4. Проверьте права на торговлю (Demo/Real)

### Включение логов MT5:
```python
import MetaTrader5 as mt5
import logging

logging.basicConfig(level=logging.DEBUG)

# Все операции будут логироваться
```

## Полезные команды

**Проверить открытые позиции:**
```python
positions = mt5.positions_get(symbol='XAUUSD')
for pos in positions:
    print(f"Ticket: {pos.ticket}, Type: {pos.type}, Profit: {pos.profit}")
```

**Закрыть все позиции:**
```python
positions = mt5.positions_get(symbol='XAUUSD')
for pos in positions:
    close_request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'position': pos.ticket,
        'symbol': pos.symbol,
        'volume': pos.volume,
        'type': mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY,
        'price': mt5.symbol_info_tick(pos.symbol).bid if pos.type == 0 else mt5.symbol_info_tick(pos.symbol).ask,
    }
    mt5.order_send(close_request)
```

## Контакты и поддержка

Если проблема не решена:
1. Проверьте версию MT5 (должна быть последняя)
2. Проверьте версию Python (3.8+)
3. Проверьте версию MetaTrader5 пакета: `pip show MetaTrader5`
4. Обратитесь к брокеру за поддержкой

---

**📚 Дополнительно:**
- [MT5 Python Documentation](https://www.mql5.com/en/docs/python_metatrader5)
- [MT5 Error Codes](https://www.mql5.com/en/docs/constants/errorswarnings/enum_trade_return_codes)
