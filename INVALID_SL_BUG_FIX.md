# Fix: Invalid SL Error (Negative Stop Loss)

## Problem

Bot was showing error:
```
[18:45:11] ❌ Invalid SL: $-77.51 (must be positive)
```

## Root Cause

The `PatternRecognitionStrategy` had a bug in `_add_pattern_signal()` method:

**Lines 551 and 564:**
```python
else:
    sl = pattern['head'] * 0.999  # or * 1.001 for SHORT
```

**Issue:** The code tried to access `pattern['head']`, but **none of the pattern detection methods** (ascending triangle, descending triangle, bull flag, etc.) actually return a `'head'` key in their pattern dictionary.

All patterns only return:
- `'entry'`
- `'direction'`
- `'resistance'`
- `'support'`
- `'type'`

When `pattern['head']` was accessed:
1. Python raised `KeyError` (if using `pattern['head']`)
2. Or returned `None` (if using `pattern.get('head')`)
3. This caused `None * 0.999 = TypeError` or negative/zero SL values

## Solution

### 1. Added Validation in Strategy (pattern_recognition_strategy.py:570-595)

```python
# Validate SL/TP values before proceeding
if sl <= 0:
    # Invalid SL - must be positive price
    return df, False

if tp <= 0:
    # Invalid TP - must be positive price
    return df, False

# Validate SL/TP are on correct side of entry
if direction == 1:  # LONG
    if sl >= entry:
        # SL must be below entry for LONG
        return df, False
    if tp <= entry:
        # TP must be above entry for LONG
        return df, False
else:  # SHORT
    if sl <= entry:
        # SL must be above entry for SHORT
        return df, False
    if tp >= entry:
        # TP must be below entry for SHORT
        return df, False
```

This prevents ANY signal with invalid SL/TP from being added to the dataframe.

### 2. Fixed SL Calculation with Fallback (pattern_recognition_strategy.py:543-568)

Changed from:
```python
if 'support' in pattern:
    sl = pattern['support'] * 0.999
elif 'neckline' in pattern:
    sl = pattern['neckline'] * 0.999
else:
    sl = pattern['head'] * 0.999  # ❌ BUG: 'head' doesn't exist!
```

To:
```python
if 'support' in pattern and pattern['support'] is not None:
    sl = pattern['support'] * 0.999
elif 'neckline' in pattern and pattern['neckline'] is not None:
    sl = pattern['neckline'] * 0.999
elif 'head' in pattern and pattern['head'] is not None:
    sl = pattern['head'] * 0.999
else:
    # Fallback: 0.5% below entry for LONG
    sl = entry * 0.995
```

Same for SHORT positions with `sl = entry * 1.005` as fallback.

### 3. Improved Error Messages in Bot (live_bot_mt5_fullauto.py:1957-1966)

Added more diagnostic information:
```python
print(f"      Pattern: {last_signal.get('pattern', 'UNKNOWN')}")
print(f"      Signal type: {last_signal.get('signal_type', 'UNKNOWN')}")
print(f"\n   ⚠️  This signal was rejected by validation")
print(f"      The strategy may have a bug in SL calculation")
```

## Result

Now the strategy will:
1. **Never generate signals with negative or zero SL/TP**
2. **Always have a valid SL** using fallback if pattern keys are missing
3. **Validate SL/TP are on correct side of entry** before adding signal
4. **Provide detailed error messages** if invalid signal somehow gets through

## Testing

After this fix:
- Bot should no longer show "Invalid SL: $-77.51" errors
- All pattern-based signals will have valid SL/TP values
- If a pattern is missing required keys, fallback SL (0.5% from entry) will be used

## Files Modified

1. `trading_bots/shared/pattern_recognition_strategy.py`
   - Lines 543-568: Fixed SL calculation with None checks and fallback
   - Lines 570-595: Added comprehensive SL/TP validation

2. `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`
   - Lines 1957-1966: Enhanced error diagnostics

## Prevention

To prevent similar issues in the future:
- Always check if dictionary keys exist before accessing them
- Add validation immediately after calculations
- Use fallback values for critical parameters
- Test with all pattern types to ensure they return consistent keys
