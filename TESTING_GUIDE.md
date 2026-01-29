# 🧪 Testing Guide - Bug Fixes Verification

## Quick Test Checklist

### ✅ Pre-Test Setup

1. **Backup Current Data** (if needed)
   ```bash
   # Backup existing logs
   cp bot_tp_hits_log*.csv bot_tp_hits_log_backup.csv 2>/dev/null || true
   cp bot_trades_log*.csv bot_trades_log_backup.csv 2>/dev/null || true
   ```

2. **Check Current State**
   ```bash
   # List existing TP hits files
   ls -la | grep tp_hits

   # List existing trades files
   ls -la | grep trades_log
   ```

---

## 🔬 Test Scenarios

### Test 1: Filename Generation (CRITICAL)

**What to test:** Verify bot creates files with symbol in name

**Steps:**
1. Start XAUUSD bot (dry-run recommended)
   ```bash
   python run_xauusd_bot.py
   ```

2. Wait for bot to initialize

3. **Expected Output:**
   ```
   📝 Created trade log file: bot_trades_log_XAUUSD.csv
   📝 Created TP hits log file: bot_tp_hits_log_XAUUSD.csv
   ```

4. **Verify Files:**
   ```bash
   ls -la | grep XAUUSD
   # Should see:
   # bot_trades_log_XAUUSD.csv
   # bot_tp_hits_log_XAUUSD.csv
   ```

**✅ PASS:** Files created with `_XAUUSD` suffix
**❌ FAIL:** Files created without symbol (old bug)

---

### Test 2: Order ID Consistency

**What to test:** Dry-run positions have DRY- prefix

**Steps:**
1. Start bot in dry-run mode
2. Wait for position to open
3. Check database

**Using GUI:**
- Open Positions Monitor
- Click on a position
- Order ID should start with `DRY-`

**Using Python:**
```python
from trading_app.database.db_manager import DatabaseManager

db = DatabaseManager()
trades = db.get_trades('xauusd_bot_XAUUSD', limit=5)

for t in trades:
    print(f"Order ID: {t.order_id}, Status: {t.status}")
    # Should print: Order ID: DRY-12345..., Status: OPEN
```

**✅ PASS:** All dry-run order_ids start with `DRY-`
**❌ FAIL:** Order_ids are plain numbers

---

### Test 3: Database Update Logging

**What to test:** Update failures are logged

**Steps:**
1. Watch console output when position closes
2. Look for update confirmation

**Expected Output (SUCCESS):**
```
✅ Updated 1 trade(s): order_id=DRY-12345, status=CLOSED
```

**Expected Output (FAILURE - should not happen):**
```
⚠️  WARNING: update_trade() affected 0 rows for order_id=12345
   Recent order_ids in DB: ['DRY-67890', 'DRY-54321']
```

**✅ PASS:** See "Updated 1 trade(s)" messages
**❌ FAIL:** See "affected 0 rows" warnings

---

### Test 4: Statistics CSV Fallback

**What to test:** Statistics loads from CSV if DB empty

**Steps:**
1. Create a test scenario:
   - Have CSV file with trades
   - Empty database OR different bot_id

2. Open Statistics dialog in GUI

3. Check console output:
   ```
   ℹ️  No trades in database for bot_xyz, trying CSV fallback...
   ✅ Loaded 15 trades from CSV
   ```

**Manual Test:**
```python
# Delete trades from DB temporarily
db.conn.execute("DELETE FROM trades WHERE bot_id = 'test_bot'")
db.conn.commit()

# GUI should still show statistics from CSV
```

**✅ PASS:** Statistics loads from CSV
**❌ FAIL:** Statistics shows "0 trades"

---

### Test 5: TP Hits Viewer File Search

**What to test:** Viewer finds files with various naming

**Steps:**
1. Create test files with different names:
   ```bash
   # Create dummy test files
   touch bot_tp_hits_log_XAUUSD.csv
   touch bot_tp_hits_log.csv
   ```

2. Open TP Hits Viewer in GUI

3. Check console output:
   ```
   ✅ Found TP hits file: C:\...\bot_tp_hits_log_XAUUSD.csv
   ```

**✅ PASS:** File found (shows path in console)
**❌ FAIL:** "No TP hits file found" error

---

### Test 6: End-to-End TP Hit Flow

**What to test:** Complete flow from position open to TP hit

**Steps:**
1. Start bot in dry-run mode
2. Wait for position to open (monitor console)
3. Simulate price reaching TP (or wait naturally)
4. Watch for TP hit

**Expected Console Output:**
```
🎯 TP HIT LOGGED: Ticket=12345, Level=TP1, Price=2650.00
📊 EVENT LOGGED: TP1 hit for ticket=12345, price=2650.00
   Total events in DB: 5 (TP: 3, SL: 2)
✅ Position #12345 closed successfully
   Profit: $150.00, Pips: 15.0
   Reason: TP1, Price: $2650.00
✅ Updated 1 trade(s): order_id=DRY-12345, status=CLOSED
```

**Verify in GUI:**
1. **Positions Monitor:** Position should disappear (closed)
2. **Statistics Dialog:** Should show the closed trade
3. **TP Hits Viewer:** Should show the TP hit entry

**✅ PASS:** All three views updated correctly
**❌ FAIL:** Any view missing data

---

### Test 7: Mode Filtering (Dry-Run vs Live)

**What to test:** Statistics correctly filters by mode

**Steps:**
1. Have both dry-run and live trades in database
2. Open Statistics dialog
3. Test mode selector:
   - **All Trades:** Shows everything
   - **Live Only:** Only live trades (no DRY- prefix)
   - **Dry-Run Only:** Only dry-run (DRY- prefix)

**Verify:**
```python
# Manually check
db = DatabaseManager()
all_trades = db.get_trades('xauusd_bot_XAUUSD')
dry_run = [t for t in all_trades if t.order_id.startswith('DRY-')]
live = [t for t in all_trades if not t.order_id.startswith('DRY-')]

print(f"Total: {len(all_trades)}")
print(f"Dry-Run: {len(dry_run)}")
print(f"Live: {len(live)}")
```

**✅ PASS:** Filter shows correct count
**❌ FAIL:** Filter shows wrong trades or zero

---

## 🚨 Common Issues & Solutions

### Issue: "No TP hits file found"

**Cause:** Bot created old filename format
**Solution:** Restart bot (should create new format)
**Verify:**
```bash
ls -la | grep tp_hits
# Should see: bot_tp_hits_log_XAUUSD.csv
```

### Issue: "updated 0 rows" warning

**Cause:** order_id mismatch between open and close
**Check:** Look for pattern in logs:
```
Position saved: Ticket=123, OrderID=DRY-123   # Open
Position updated: Ticket=123, OrderID=123     # Close (WRONG!)
```
**Solution:** This should not happen with fixes; report if it does

### Issue: Statistics shows 0 trades

**Debug Steps:**
1. Check database:
   ```python
   trades = db.get_trades('xauusd_bot_XAUUSD')
   print(f"DB has {len(trades)} trades")
   ```

2. Check CSV fallback:
   ```bash
   ls -la bot_trades_log_XAUUSD.csv
   wc -l bot_trades_log_XAUUSD.csv
   ```

3. Check bot_id matches:
   - GUI config: `self.config.bot_id`
   - Database: `SELECT DISTINCT bot_id FROM trades`

### Issue: TP hits not appearing in viewer

**Debug Steps:**
1. Verify file exists:
   ```bash
   ls -la bot_tp_hits_log_XAUUSD.csv
   ```

2. Check file has data:
   ```bash
   head bot_tp_hits_log_XAUUSD.csv
   ```

3. Check viewer search paths (console output):
   ```
   ✅ Found TP hits file: /path/to/file.csv
   ```

---

## 📊 Success Criteria

### Minimum Requirements (Must Pass):
- ✅ Files created with symbol in name
- ✅ Order IDs have DRY- prefix in dry-run
- ✅ Database updates succeed (no "0 rows" warnings)
- ✅ Statistics shows trades (from DB or CSV)
- ✅ TP Hits viewer finds and displays data

### Full Success (All Tests):
- ✅ All 7 test scenarios pass
- ✅ No console warnings/errors
- ✅ GUI updates in real-time
- ✅ Data consistent across all views

---

## 🔄 Regression Testing

**After confirming fixes work, test these don't break:**

1. **Existing Functionality:**
   - Position opening/closing
   - Trailing stops
   - Multi-position mode
   - Telegram notifications

2. **Other Symbol Support:**
   - Test with BTC/USDT (crypto bot)
   - Verify both MT5 and Binance exchanges

3. **Performance:**
   - GUI remains responsive
   - No memory leaks
   - Database queries fast

---

## 📝 Test Report Template

```
# Bug Fix Test Report

**Date:** [Date]
**Tester:** [Name]
**Branch:** wizardly-morse

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| Test 1: Filename Generation | ✅ PASS | Files created correctly |
| Test 2: Order ID Consistency | ✅ PASS | DRY- prefix working |
| Test 3: DB Update Logging | ✅ PASS | Updates confirmed |
| Test 4: CSV Fallback | ✅ PASS | Loads from CSV |
| Test 5: File Search | ✅ PASS | Finds all variants |
| Test 6: E2E TP Hit | ✅ PASS | Full flow works |
| Test 7: Mode Filtering | ✅ PASS | Filters correctly |

## Issues Found

[None / List any issues]

## Overall Status

✅ All tests passed - Ready for production
❌ [X] tests failed - Needs fixes

## Additional Notes

[Any observations, suggestions, or concerns]
```

---

**Good luck with testing! 🚀**
