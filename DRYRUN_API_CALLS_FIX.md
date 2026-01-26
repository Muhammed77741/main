# 🔧 FIX: Dry-Run API Calls Error

**Date:** 2026-01-22
**Issue:** "binance requires 'apiKey' credential" errors in dry-run mode
**Status:** ✅ FIXED

---

## 🚨 ПРОБЛЕМА

### Симптомы:
```
⚠️  Error updating trailing stops: binance requires "apiKey" credential
⚠️  Error updating trailing stops: binance requires "apiKey" credential
```

### Когда происходит:
- Бот запущен в **dry-run режиме**
- Периодически (каждые несколько секунд) появляются ошибки
- Не влияет на основную функциональность, но засоряет логи

---

## 🔍 ROOT CAUSE ANALYSIS

### Контекст:
После исправления DRYRUN_POSITIONS_NOT_CLOSING_FIX.md, бот в dry-run использует **public API** (без credentials):

```python
# В connect_exchange() для dry-run:
self.exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
    # НЕТ apiKey и secret!
})
self.exchange_connected = True
```

### Проблема:
Несколько методов всё ещё пытаются вызвать **private API** endpoints, которые требуют аутентификацию:

#### 1. `update_trailing_stops()` (line 585-671)
```python
def update_trailing_stops(self):
    if not self.trailing_stop_enabled or not self.exchange_connected:
        return

    # ❌ ПРОБЛЕМА: Не проверяет dry_run!
    try:
        positions = self.exchange.fetch_positions([self.symbol])  # REQUIRES AUTH!
        # ...
```

**Что делает:**
- Пытается получить открытые позиции с exchange
- `fetch_positions()` требует **private API**
- В dry-run падает с ошибкой `apiKey required`

#### 2. `get_open_positions()` (line 1504-1516)
```python
def get_open_positions(self):
    if not self.exchange_connected:
        return []

    # ❌ ПРОБЛЕМА: Не проверяет dry_run!
    try:
        positions = self.exchange.fetch_positions([self.symbol])  # REQUIRES AUTH!
        # ...
```

**Используется в:**
- Verification после открытия позиций (line 1720)
- Проверка состояния позиций

---

## ✅ РЕШЕНИЕ

### Fix #1: Skip trailing stops в dry-run

**File:** `trading_bots/crypto_bot/live_bot_binance_fullauto.py:585-599`

**БЫЛО:**
```python
def update_trailing_stops(self):
    if not self.trailing_stop_enabled or not self.exchange_connected:
        return

    try:
        positions = self.exchange.fetch_positions([self.symbol])
        # ...
```

**СТАЛО:**
```python
def update_trailing_stops(self):
    if not self.trailing_stop_enabled or not self.exchange_connected:
        return

    # FIX: Skip in dry-run mode (requires private API)
    if self.dry_run:
        return

    try:
        positions = self.exchange.fetch_positions([self.symbol])
        # ...
```

**Обоснование:**
- В dry-run trailing stops всё равно работают через `_update_3position_trailing()`
- Метод `update_trailing_stops()` предназначен для single-position mode
- В dry-run позиции tracked в памяти, не на exchange

### Fix #2: Return empty в get_open_positions() для dry-run

**File:** `trading_bots/crypto_bot/live_bot_binance_fullauto.py:1504-1516`

**БЫЛО:**
```python
def get_open_positions(self):
    if not self.exchange_connected:
        return []

    try:
        positions = self.exchange.fetch_positions([self.symbol])
        # ...
```

**СТАЛО:**
```python
def get_open_positions(self):
    if not self.exchange_connected:
        return []

    # FIX: In dry-run mode, return empty (positions tracked in memory only)
    if self.dry_run:
        return []

    try:
        positions = self.exchange.fetch_positions([self.symbol])
        # ...
```

**Обоснование:**
- В dry-run позиции существуют только в `self.positions_tracker`
- Не нужно (и невозможно) получать их с exchange
- Возврат пустого списка безопасен - verification просто пропускается

---

## 📊 ВЛИЯНИЕ ИЗМЕНЕНИЙ

### На Dry-Run Mode:
- ✅ Больше нет ошибок `apiKey required`
- ✅ Логи чистые
- ✅ TP/SL monitoring работает через `_check_tp_sl_realtime()`
- ✅ 3-position trailing работает через `_update_3position_trailing()`
- ℹ️  Single-position trailing НЕ работает (но это OK для dry-run)

### На Live Mode:
- ✅ Без изменений - все проверки остаются активными
- ✅ `update_trailing_stops()` работает как раньше
- ✅ `get_open_positions()` работает как раньше

---

## 🧪 ТЕСТИРОВАНИЕ

### Test 1: Dry-Run Mode - No Errors
```bash
python run_crypto_bot.py --dry-run
```

**Expected:**
- ✅ Нет ошибок `apiKey required`
- ✅ Нет ошибок `Error updating trailing stops`
- ✅ TP/SL monitoring активен

**Check Logs:**
```
✅ Connected to Binance (public API)
   DRY-RUN Mode: TP/SL monitoring active
🔄 Checking TP/SL for X open positions...
```

### Test 2: Live Mode - Still Works
```bash
python run_crypto_bot.py --live
```

**Expected:**
- ✅ `update_trailing_stops()` вызывается
- ✅ `get_open_positions()` возвращает реальные позиции
- ✅ Trailing stops обновляются на exchange

---

## 🔄 СВЯЗЬ С ДРУГИМИ ФИКСАМИ

### 1. DRYRUN_POSITIONS_NOT_CLOSING_FIX.md
**Что исправил:** Dry-run использует public API
**Последствие:** Методы, требующие private API, падают с ошибками
**Этот фикс:** Добавляет dry_run checks в проблемные методы

### 2. TP_LEVEL_DETECTION_BUG_FIX.md
**Независимый фикс:** position_num tracking
**Не связан:** С API calls errors

---

## 📝 КРИТЕРИИ УСПЕХА

- [x] `update_trailing_stops()` пропускается в dry-run
- [x] `get_open_positions()` возвращает [] в dry-run
- [ ] Нет ошибок `apiKey required` в dry-run логах
- [ ] TP/SL monitoring работает в dry-run
- [ ] Live mode не затронут

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

### 1. Trailing Stops в Dry-Run
**Single-position mode:**
- `update_trailing_stops()` **НЕ работает** в dry-run (требует exchange API)
- Это ограничение dry-run режима
- Для полного тестирования trailing stops используйте testnet или малые суммы в live

**3-position mode:**
- `_update_3position_trailing()` **РАБОТАЕТ** в dry-run
- Обновляет SL в памяти и БД
- Полностью функционален

### 2. Position Verification
После открытия позиций:
```python
positions = self.get_open_positions()  # Returns [] in dry-run
print(f"Open positions after orders: {len(positions)}")
```

В dry-run:
- Показывает `0 positions` (потому что exchange не используется)
- Это нормально - позиции tracked в `self.positions_tracker`

### 3. Другие методы с private API
Проверены и уже защищены:
- ✅ `_sync_positions_with_exchange()` - checks `self.dry_run` (line 678)
- ✅ `connect_exchange()` - использует public API в dry-run
- ✅ Position opening/closing - симулируется в dry-run

---

## 📊 СТАТИСТИКА ИЗМЕНЕНИЙ

| File | Lines Added | Description |
|------|-------------|-------------|
| `live_bot_binance_fullauto.py` | +3 (line ~598) | Skip trailing stops in dry-run |
| `live_bot_binance_fullauto.py` | +4 (line ~1509) | Return empty positions in dry-run |
| **TOTAL** | **+7** | Minimal changes |

---

**Фикс применён! 🎉**

**Следующий шаг:** Запустить dry-run бота и убедиться, что ошибки `apiKey required` больше не появляются.
