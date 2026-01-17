# TP Levels Fix for Signal Analysis GUI

## Problem
When using multi-TP mode in the Signal Analysis GUI, the exported CSV showed incorrect TP levels. The `take_profit` column contained the original strategy TP value instead of the actual TP1/TP2/TP3 levels used in the backtest.

### Example of the Issue
For XAUUSD with entry price 3397.2 in RANGE mode:
- **Expected TP levels (multi-TP mode):**
  - TP1: 3397.2 + 20 = 3417.2 (RANGE TP1 = 20 points)
  - TP2: 3397.2 + 35 = 3432.2 (RANGE TP2 = 35 points)
  - TP3: 3397.2 + 50 = 3447.2 (RANGE TP3 = 50 points)

- **What was exported:** 3440.71397424 (original strategy TP, not relevant in multi-TP mode)

## Solution
Added new columns to the exported CSV to track the actual TP/SL levels used in multi-TP mode:
- `tp1_used`: The actual TP1 level calculated and used
- `tp2_used`: The actual TP2 level calculated and used
- `tp3_used`: The actual TP3 level calculated and used
- `sl_used`: The actual SL level calculated and used

These columns are only populated when multi-TP mode is enabled.

## Changes Made
1. **Added column initialization** in `_calculate_signal_outcomes()` for both `SignalAnalysisWorker` and `SignalAnalysisWorkerMT5` classes
2. **Stored calculated TP levels** immediately after calculation, before they are used in outcome calculation
3. **Updated table display** to show "TP1/TP2/TP3" format when multi-TP is enabled
4. **CSV export** now includes all columns, giving users access to both:
   - Original `take_profit` column (for reference)
   - New `tp1_used`, `tp2_used`, `tp3_used` columns (actual levels used)

## CSV Export Columns (Multi-TP Mode)
The exported CSV now includes these key columns:
- `close` - Entry price
- `stop_loss` - Original strategy stop loss
- `take_profit` - Original strategy take profit (for reference only)
- `regime` - Market regime (TREND or RANGE)
- `tp1_used` - Actual TP1 level used in backtest
- `tp2_used` - Actual TP2 level used in backtest
- `tp3_used` - Actual TP3 level used in backtest
- `sl_used` - Actual SL level used in backtest
- `tp_levels_hit` - Which TP levels were hit (e.g., "TP1+TP2")
- `outcome` - Trade outcome (Win/Loss/Timeout)
- `profit_pct` - Profit percentage

## Verification
Users can now verify the TP levels are correct by checking:
1. In the GUI table, the "Take Profit" column shows "TP1/TP2/TP3" format
2. In the CSV export, the `tp1_used`, `tp2_used`, `tp3_used` columns show the exact values
3. For XAUUSD RANGE mode (entry=3397.2): tp1_used=3417.2, tp2_used=3432.2, tp3_used=3447.2
4. For XAUUSD TREND mode (entry=3412.03): tp1_used=3442.03, tp2_used=3467.03, tp3_used=3502.03

## TP Level Configuration
### XAUUSD (Gold) - in points
- **TREND mode:** TP1=30p, TP2=55p, TP3=90p, SL=16p
- **RANGE mode:** TP1=20p, TP2=35p, TP3=50p, SL=12p

### Crypto (BTC/ETH) - in percentage
- **TREND mode:** TP1=1.5%, TP2=2.75%, TP3=4.5%, SL=0.8%
- **RANGE mode:** TP1=1.0%, TP2=1.75%, TP3=2.5%, SL=0.6%
