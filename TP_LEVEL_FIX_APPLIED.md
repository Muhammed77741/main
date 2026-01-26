# ✅ FIX APPLIED: TP Level Detection (TP1/TP2/TP3)

**Date:** 2026-01-22
**Issue:** All positions closing as TP1 instead of TP2/TP3
**Status:** ✅ FIXED

---

## 🎯 ЧТО БЫЛО ИСПРАВЛЕНО

### Проблема:
При открытии 3-х позиций для одного сигнала (TP1, TP2, TP3), все позиции закрывались и логировались как **TP1**, даже когда достигался TP2 или TP3.

### Root Cause:
Поля `position_num` и `position_group_id` сохранялись в базу данных, но **НЕ** добавлялись в in-memory `positions_tracker`. При проверке TP level, код не мог найти `position_num` и использовал default значение 'TP1'.

### Решение:
Добавлены 2 поля в `positions_tracker` при открытии позиций + улучшен fallback парсинг comment.

---

## 📝 ИЗМЕНЁННЫЕ ФАЙЛЫ

### 1. `trading_bots/crypto_bot/live_bot_binance_fullauto.py`

#### Change #1: Add fields to positions_tracker (lines ~198-216)
```python
# БЫЛО:
self.positions_tracker[order_id] = {
    'order_id': order_id,
    'open_time': open_time,
    'close_time': None,
    'type': position_type,
    'amount': amount,
    'entry_price': entry_price,
    'sl': sl,
    'tp': tp,
    'close_price': None,
    'profit': None,
    'profit_pct': None,
    'regime': regime,
    'duration': None,
    'status': 'OPEN',
    'comment': comment
}

# СТАЛО:
self.positions_tracker[order_id] = {
    'order_id': order_id,
    'open_time': open_time,
    'close_time': None,
    'type': position_type,
    'amount': amount,
    'entry_price': entry_price,
    'sl': sl,
    'tp': tp,
    'close_price': None,
    'profit': None,
    'profit_pct': None,
    'regime': regime,
    'duration': None,
    'status': 'OPEN',
    'comment': comment,
    'position_group_id': position_group_id,  # ✅ ADDED
    'position_num': position_num              # ✅ ADDED
}
```

#### Change #2: Improve comment fallback (lines ~1076-1093)
```python
# БЫЛО:
tp_level = 'TP1'
position_num = tracked_pos.get('position_num', 0)
if position_num == 1:
    tp_level = 'TP1'
elif position_num == 2:
    tp_level = 'TP2'
elif position_num == 3:
    tp_level = 'TP3'
elif 'TP1' in tracked_pos.get('comment', ''):
    tp_level = 'TP1'
elif 'TP2' in tracked_pos.get('comment', ''):
    tp_level = 'TP2'
elif 'TP3' in tracked_pos.get('comment', ''):
    tp_level = 'TP3'

# СТАЛО:
tp_level = 'TP1'
position_num = tracked_pos.get('position_num', 0)
if position_num == 1:
    tp_level = 'TP1'
elif position_num == 2:
    tp_level = 'TP2'
elif position_num == 3:
    tp_level = 'TP3'
elif 'P1/3' in tracked_pos.get('comment', ''):  # ✅ NEW
    tp_level = 'TP1'
elif 'P2/3' in tracked_pos.get('comment', ''):  # ✅ NEW
    tp_level = 'TP2'
elif 'P3/3' in tracked_pos.get('comment', ''):  # ✅ NEW
    tp_level = 'TP3'
elif 'TP1' in tracked_pos.get('comment', ''):
    tp_level = 'TP1'
elif 'TP2' in tracked_pos.get('comment', ''):
    tp_level = 'TP2'
elif 'TP3' in tracked_pos.get('comment', ''):
    tp_level = 'TP3'
```

### 2. `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`

#### Change #1: Add fields to positions_tracker (lines ~257-275)
```python
# БЫЛО:
self.positions_tracker[ticket] = {
    'ticket': ticket,
    'open_time': open_time,
    'close_time': None,
    'type': position_type,
    'volume': volume,
    'entry_price': entry_price,
    'sl': sl,
    'tp': tp,
    'close_price': None,
    'profit': None,
    'pips': None,
    'regime': regime,
    'duration': None,
    'status': 'OPEN',
    'comment': comment
}

# СТАЛО:
self.positions_tracker[ticket] = {
    'ticket': ticket,
    'open_time': open_time,
    'close_time': None,
    'type': position_type,
    'volume': volume,
    'entry_price': entry_price,
    'sl': sl,
    'tp': tp,
    'close_price': None,
    'profit': None,
    'pips': None,
    'regime': regime,
    'duration': None,
    'status': 'OPEN',
    'comment': comment,
    'position_group_id': position_group_id,  # ✅ ADDED
    'position_num': position_num              # ✅ ADDED
}
```

#### Change #2: Improve comment fallback (lines ~1060-1077)
```python
# Same changes as crypto bot (see above)
```

---

## 📊 СТАТИСТИКА

| File | Lines Added | Lines Modified | Net Change |
|------|-------------|----------------|------------|
| `live_bot_binance_fullauto.py` | +8 | ~4 | +8 lines |
| `live_bot_mt5_fullauto.py` | +8 | ~4 | +8 lines |
| **TOTAL** | **+16** | **~8** | **+16 lines** |

---

## ✅ ЧТО ТЕПЕРЬ РАБОТАЕТ

### До фикса:
```
Signal SELL → Open 3 positions
Position 1: TP1 $3060 → Closes as TP1 ✅
Position 2: TP2 $3042 → Closes as TP1 ❌ (WRONG!)
Position 3: TP3 $3020 → Closes as TP1 ❌ (WRONG!)

Логи:
🎯 TP1 HIT for position #xxx
🎯 TP1 HIT for position #yyy  ← Should be TP2!
🎯 TP1 HIT for position #zzz  ← Should be TP3!
```

### После фикса:
```
Signal SELL → Open 3 positions
Position 1: TP1 $3060 → Closes as TP1 ✅
Position 2: TP2 $3042 → Closes as TP2 ✅
Position 3: TP3 $3020 → Closes as TP3 ✅

Логи:
🎯 TP1 HIT for position #xxx
🎯 TP2 HIT for position #yyy  ✅
🎯 TP3 HIT for position #zzz  ✅
```

---

## 🧪 ТЕСТИРОВАНИЕ

### Test 1: Check positions_tracker
```python
# После открытия позиций:
for order_id, pos in bot.positions_tracker.items():
    print(f"Order {order_id}: position_num={pos.get('position_num')}, group_id={pos.get('position_group_id')}")

# Ожидаемый вывод:
# Order 12345: position_num=1, group_id=abc123...
# Order 12346: position_num=2, group_id=abc123...
# Order 12347: position_num=3, group_id=abc123...
```

### Test 2: Verify TP level detection
```python
# В консоли при закрытии:
🎯 TP1 HIT for position #12345 at $3060.65
🎯 TP2 HIT for position #12346 at $3042.06  ← NOT TP1!
🎯 TP3 HIT for position #12347 at $3020.37  ← NOT TP1!
```

### Test 3: Check database events
```python
from trading_app.database.db_manager import DatabaseManager

db = DatabaseManager()
events = db.get_trade_events(bot_id='crypto_bot_ETHUSDT', event_type='TP_HIT')

for e in events:
    print(f"{e['event_type']} @ ${e['price']:.2f}")

# Должно показывать:
# TP1 @ $3060.65
# TP2 @ $3042.06
# TP3 @ $3020.37
```

### Test 4: Check TP Hits Viewer (GUI)
1. Open TP Hits Viewer
2. Filter by symbol
3. Should see separate rows for TP1, TP2, TP3

### Test 5: Check Statistics
1. Open Statistics dialog
2. Check "TP Hit Distribution" section
3. Should show counts for TP1, TP2, TP3 separately

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

### 1. Обратная совместимость
- ✅ Single-position mode не затронут (position_num=0 → default TP1)
- ✅ Старые позиции без position_num будут использовать comment fallback
- ✅ Новый comment parsing `'P1/3'` проверяется **перед** старым `'TP1'`

### 2. Влияние на существующие данные
- Позиции, открытые ДО фикса, могут иметь неправильный TP level в БД
- Новые позиции будут логироваться правильно
- Если важна точность истории, можно пересчитать:
  ```sql
  -- Найти все TP events с неправильным level
  SELECT * FROM trade_events
  WHERE event_type = 'TP_HIT'
    AND order_id IN (
      SELECT order_id FROM trades WHERE position_num = 2
    )
    AND event_type = 'TP1';  -- Should be TP2
  ```

### 3. Dry-run vs Live
- Фикс работает в **обоих режимах**
- Dry-run: position_num сохраняется в tracker при открытии
- Live: position_num сохраняется в tracker при открытии

### 4. Multi-bot support
- Исправлено для **обоих** ботов:
  - Crypto bot (Binance)
  - XAUUSD bot (MT5)
- Одинаковая логика в обоих

---

## 🚀 СЛЕДУЮЩИЕ ШАГИ

### Immediate (сегодня):
1. ✅ Применить фикс (DONE)
2. ⏳ Запустить бота в dry-run mode
3. ⏳ Дождаться открытия 3-х позиций
4. ⏳ Проверить логи при закрытии

### Short-term (эта неделя):
5. ⏳ Верифицировать TP2 и TP3 закрываются с правильным level
6. ⏳ Проверить GUI Statistics и TP Hits Viewer
7. ⏳ Протестировать в live mode (если уверены)

### Optional (если важна история):
8. ⏳ Пересчитать TP level для старых позиций в БД
9. ⏳ Обновить trade_events для консистентности

---

## 📝 КРИТЕРИИ УСПЕХА

- [x] position_num добавлен в positions_tracker
- [x] position_group_id добавлен в positions_tracker
- [x] Comment fallback улучшен (P1/3, P2/3, P3/3)
- [ ] TP2 hits логируются как "TP2", не "TP1"
- [ ] TP3 hits логируются как "TP3", не "TP1"
- [ ] GUI показывает правильную статистику
- [ ] Database events имеют правильный event_type

---

**Фикс применён и готов к тестированию! 🎉**

**Что дальше:**
Запустить бота и проверить, что при достижении TP2 и TP3, они правильно логируются.
