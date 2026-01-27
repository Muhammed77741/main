# Profit Calculation Fix - Statistics Dialog

## Issue Reported
@orkenpunkitbay01-spec reported: "gui в statistics неправильно показывает profit usd profit %"
(The statistics GUI incorrectly shows profit USD and profit %)

## Root Causes Found

### 1. Profit Percentage Calculation (WRONG)

**Location:** `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`, line 456

**Old Code (Incorrect):**
```python
# Calculate pips
if pos['type'] == 'BUY':
    pips = (close_price - pos['entry_price']) * 10  # For XAUUSD
else:
    pips = (pos['entry_price'] - close_price) * 10
pos['pips'] = round(pips, 1)

# Calculate profit percentage (approximate) - WRONG!
profit_pct = (pips / pos['entry_price']) * 100 if pos['entry_price'] > 0 else 0
```

**Problem:** The formula `(pips / entry_price) * 100` is mathematically incorrect:
- `pips` = price_difference * 10
- Dividing `pips` by `entry_price` (e.g., 100 / 2000) gives a nonsensical ratio
- Results in profit % being **10x too high**

**Example:**
- Entry: $2000, Close: $2010 (BUY)
- pips = 100
- Old formula: `(100 / 2000) * 100 = 5.00%` ❌ WRONG
- Actual profit: 0.5% (10/2000 = 0.005 = 0.5%)

**New Code (Correct):**
```python
# Calculate profit percentage - fixed formula
if pos['entry_price'] > 0:
    if pos['type'] == 'BUY':
        profit_pct = ((close_price - pos['entry_price']) / pos['entry_price']) * 100
    else:
        profit_pct = ((pos['entry_price'] - close_price) / pos['entry_price']) * 100
else:
    profit_pct = 0.0
```

**Formula:** `(price_change / entry_price) * 100`
- This is the standard percentage change formula
- Matches the correct calculation used in other parts of the code (lines 3236-3238)
- Matches the crypto bot implementation

---

### 2. Profit USD Calculation (WRONG)

**Location:** `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`, lines 676-678

**Old Code (Incorrect):**
```python
# Calculate profit
if trade.trade_type == 'BUY':
    profit = (close_price - trade.entry_price) * trade.amount
else:
    profit = (trade.entry_price - close_price) * trade.amount
```

**Problem:** Missing XAUUSD contract size multiplier
- For XAUUSD: 1 lot = 100 troy ounces
- Point value = $100 per lot for 1 point ($1) movement
- Formula was missing the `* 100` multiplier
- Results in profit USD being **100x too small**

**Example:**
- Entry: $2000, Close: $2010 (BUY)
- Lot size: 0.1
- Old formula: `10 * 0.1 = $1.00` ❌ WRONG
- Correct: `10 * 0.1 * 100 = $100.00` ✅

**New Code (Correct):**
```python
# Calculate profit for XAUUSD (1 lot = 100 oz, point value = $100)
if trade.trade_type == 'BUY':
    profit = (close_price - trade.entry_price) * trade.amount * 100
else:
    profit = (trade.entry_price - close_price) * trade.amount * 100
```

**Formula:** `price_change * lot_size * 100`
- Accounts for XAUUSD contract size (100 oz per lot)
- Matches calculations elsewhere in the code (e.g., line with `point_value = 100.0`)

---

## Impact of Errors

### Before Fix (Examples):

| Scenario | Entry | Close | Lot | Old Profit % | Old Profit USD | Correct Profit % | Correct Profit USD |
|----------|-------|-------|-----|--------------|----------------|------------------|---------------------|
| BUY +$10 | $2000 | $2010 | 0.1 | **5.00%** ❌ | **$1.00** ❌ | 0.50% ✅ | $100.00 ✅ |
| BUY +$5  | $2000 | $2005 | 0.5 | **2.50%** ❌ | **$2.50** ❌ | 0.25% ✅ | $250.00 ✅ |
| SELL +$20| $2000 | $1980 | 1.0 | **10.00%** ❌| **$20.00** ❌| 1.00% ✅ | $2000.00 ✅|

**Errors:**
- Profit % was **10x too high**
- Profit USD was **100x too small**

---

## When Does This Bug Occur?

**Affected:** Only positions closed during database sync (manually closed on MT5)

**Not Affected:** Positions closed normally by the bot via TP/SL (these use `deal.profit` from MT5 which is correct)

**Code Path:**
1. User manually closes position in MT5
2. Bot syncs database (line 666: "Position manually closed on MT5 - syncing database")
3. Bot calculates profit using the wrong formulas (lines 676-678)
4. Bot logs position closed with wrong profit values (line 684)
5. Wrong values saved to database and shown in statistics

---

## Fix Verification

### Test Results:
```
Testing profit percentage calculation...
✅ BUY position profit %: 0.50% (correct)
✅ BUY position loss %: -0.50% (correct)
✅ SELL position profit %: 0.50% (correct)
✅ SELL position loss %: -0.50% (correct)

Testing profit USD calculation for XAUUSD...
✅ BUY position (0.1 lot, $10 gain): $100.00 profit (correct)
✅ BUY position (1 lot, $1 gain): $100.00 profit (correct)
✅ SELL position (0.1 lot, $10 gain): $100.00 profit (correct)
✅ BUY position (0.5 lot, $5 loss): $-250.00 profit (correct)

Comparing OLD (wrong) vs NEW (correct) formulas...
Profit Percentage:
  Entry: $2000.00, Close: $2010.00
  OLD (wrong): 5.00%
  NEW (correct): 0.50%
  Difference: 4.50%

Profit USD:
  Lot size: 0.1
  Price change: $10.00
  OLD (wrong): $1.00
  NEW (correct): $100.00
  Difference: $99.00
```

---

## Files Modified

1. **trading_bots/xauusd_bot/live_bot_mt5_fullauto.py**
   - Line 456: Fixed profit_percent calculation
   - Line 676: Fixed profit USD calculation (added * 100)

2. **test_profit_calculation_fix.py** (NEW)
   - Comprehensive tests for both calculations
   - Demonstrates old vs new formulas

---

## Recommendation

**Existing Database Records:** 
- Trades closed before this fix will still have incorrect profit values in the database
- These can be identified by the large discrepancies (profit % 10x too high, profit USD 100x too small)
- Consider running a migration script to recalculate affected trades if historical accuracy is important

**New Trades:**
- All new manually closed positions will now have correct profit calculations
- Statistics will display accurate values

---

## Summary

✅ Fixed profit percentage calculation (was 10x too high)
✅ Fixed profit USD calculation (was 100x too small)
✅ Added comprehensive tests
✅ Formulas now match MT5 calculations and crypto bot logic
✅ Statistics dialog will now show correct profit values
