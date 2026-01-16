# Testing Guide: 3-Position Multi-TP Feature

## Quick Test Steps

### Prerequisites
- Trading app with Signal Analysis dialog installed
- Access to BTC/ETH data (Binance) or XAUUSD data (MT5)

### Test 1: Basic 3-Position Display
1. Open Signal Analysis dialog from any bot
2. Select symbol (BTC/USDT or XAUUSD)
3. ✅ **Enable "Use Multiple TP Levels (Live Bot Mode)"**
4. Set date range (e.g., last 7 days)
5. Click "Analyze Signals"

**Expected Results:**
- Table shows 3 rows per signal
- "Pos" column displays: 1, 2, 3
- Groups alternate between white and gray backgrounds
- Each position has independent outcome and profit %

### Test 2: Different Outcomes
Look for signals where positions have different outcomes:
- **Scenario A**: Pos 1 closes at TP1, Pos 2 & 3 hit trailing stop
  - "TP Hit" column: TP1, Trailing, Trailing
- **Scenario B**: All positions hit their TPs
  - "TP Hit" column: TP1, TP2, TP3
- **Scenario C**: All positions hit SL
  - "TP Hit" column: SL, SL, SL

### Test 3: CSV Export
1. After running analysis, click "Export CSV"
2. Open CSV in Excel
3. Look for columns:
   - `position_group_id` (UUID)
   - `position_num` (1, 2, or 3)
   - All standard columns (outcome, profit_pct, etc.)
4. Filter by `position_group_id` to see all 3 positions for one signal

### Test 4: Visual Grouping
1. Scroll through results table
2. Verify alternating gray/white backgrounds for position groups
3. Each group of 3 should be visually distinct from next group

### Test 5: Regime Detection
1. Check "Regime" column shows TREND or RANGE
2. Verify TP levels in "Take Profit" column match regime:
   - TREND: Higher TPs (1.5%/2.75%/4.5% for crypto)
   - RANGE: Lower TPs (1.0%/1.75%/2.5% for crypto)

### Test 6: Trailing Stop Behavior
1. Find a signal where TP1 hit but TP2/TP3 did not
2. Positions 2 & 3 should show "Trailing" in "TP Hit" column
3. Profit % should be between 0% and TP2/TP3 target
4. Position 1 should always show "TP1" (no trailing)

### Test 7: Compare with Single-Position Mode
1. Run analysis with Multi-TP **disabled**
2. Note: Single row per signal, different outcome calculation
3. Run same date range with Multi-TP **enabled**
4. Compare: 3 positions show more detailed breakdown

## Expected Visual Example

```
Date/Time       | Pos | Type  | Price   | Result   | Profit % | TP Hit  | Bars
----------------|-----|-------|---------|----------|----------|---------|------
2025-01-15 10:00| 1   | BUY 📈| $50000  | Win ✅   | +1.50%   | TP1     | 12
2025-01-15 10:00| 2   | BUY 📈| $50000  | Win ✅   | +2.10%   | Trailing| 18
2025-01-15 10:00| 3   | BUY 📈| $50000  | Win ✅   | +1.80%   | Trailing| 18
----------------|-----|-------|---------|----------|----------|---------|------
2025-01-15 14:00| 1   | SELL 📉| $51000 | Win ✅   | +1.00%   | TP1     | 8
2025-01-15 14:00| 2   | SELL 📉| $51000 | Win ✅   | +1.75%   | TP2     | 14
2025-01-15 14:00| 3   | SELL 📉| $51000 | Loss ❌  | -0.60%   | SL      | 20
```

(Note: Gray background on alternating groups in actual UI)

## Common Issues to Check

### Issue 1: No position column showing
- **Cause**: Multi-TP not enabled
- **Fix**: Check "Use Multiple TP Levels" checkbox

### Issue 2: Only 1 row per signal instead of 3
- **Cause**: Old cached data or not using 3-position mode
- **Fix**: Re-run analysis with Multi-TP enabled

### Issue 3: All 3 positions have identical outcomes
- **Likely**: Price moved very quickly to TP3 or SL
- **Normal**: In fast-moving markets, all positions close together

### Issue 4: CSV missing position columns
- **Cause**: Running on old analysis results
- **Fix**: Re-run analysis before exporting

## Performance Notes

- 3-position mode is 3× slower than single-position (expected)
- For 100 signals: ~300 rows in results
- CSV file size: ~3× larger
- UI remains responsive during analysis

## Success Criteria

✅ Table shows 3 rows per signal when Multi-TP enabled
✅ Position column (1, 2, 3) displays correctly
✅ Visual grouping visible (alternating backgrounds)
✅ Each position has independent outcome
✅ Trailing stop works for positions 2 & 3 after TP1
✅ Position 1 never uses trailing
✅ CSV export includes position_group_id
✅ No duplicate or missing position rows

## Reporting Bugs

If you find issues, report:
1. Symbol tested (BTC/ETH/XAUUSD)
2. Date range used
3. Number of signals found
4. Screenshot of table
5. Sample CSV export (first few rows)
6. Expected vs actual behavior
