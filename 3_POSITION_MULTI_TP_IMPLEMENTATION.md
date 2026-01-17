# 3-Position Multi-TP Trading Feature Implementation

## Overview
Implemented a 3-position multi-TP trading feature in the Signal Analysis dialog that creates 3 independent positions per signal, each with different TP targets and trailing stop behavior.

## Implementation Details

### 1. New Methods Added

#### `_calculate_3_position_outcome()` 
Added to both `SignalAnalysisWorker` and `SignalAnalysisWorkerMT5` classes.

**Parameters:**
- `signal_type`: 1 (BUY) or -1 (SELL)
- `entry_price`: Entry price
- `stop_loss`: Stop loss price
- `tp1`, `tp2`, `tp3`: Three take profit levels
- `future_candles`: DataFrame of future price data
- `trailing_pct`: Trailing stop percentage (default 0.5 = 50%)

**Logic:**
- **Position 1**: Targets TP1 only, no trailing stop
- **Position 2**: Targets TP2, trailing activates after TP1 hits
- **Position 3**: Targets TP3, trailing activates after TP1 hits

**Trailing Stop Calculation:**
- **For BUY signals:** 
  - Trailing stop = max_price_since_tp1 - (max_price_since_tp1 - entry_price) × trailing_pct
- **For SELL signals:**
  - Trailing stop = min_price_since_tp1 + (entry_price - min_price_since_tp1) × trailing_pct

**Returns:** List of 3 position dictionaries:
```python
[
    {
        'position_num': 1,
        'outcome': 'Win ✅' | 'Loss ❌' | 'Timeout',
        'profit_pct': float,
        'bars': int,
        'tp_level_hit': 'TP1' | 'SL' | 'None' | 'Trailing',
        'close_reason': 'TP1' | 'SL' | 'Timeout' | 'Trailing Stop'
    },
    # ... positions 2 and 3
]
```

### 2. Modified `_calculate_signal_outcomes()`
Updated in both worker classes to support 3-position mode.

**Changes:**
- Added `position_group_id` and `position_num` columns when `use_multi_tp=True`
- When multi-TP enabled:
  - Calls `_calculate_3_position_outcome()` instead of old method
  - Creates 3 separate rows per signal
  - Assigns unique UUID as `position_group_id` to group positions
  - Each row contains full signal data + position-specific outcome
  - Replaces original single row with 3 position rows
- Returns modified DataFrame with 3× rows when multi-TP enabled

### 3. Updated Table Display (`populate_results_table()`)

**New Features:**
- Detects 3-position mode via `position_group_id` column
- Adds "Pos" column showing position number (1, 2, or 3)
- Visual grouping: Alternating gray background for position groups
- Column layout in 3-position mode:
  ```
  Date/Time | Pos | Type | Price | Stop Loss | Take Profit | Result | Profit % | TP Hit | Bars | Entry Reason | Regime
  ```
- "TP Hit" column shows individual TP level hit per position (TP1, TP2, TP3, SL, or Trailing)

**Visual Grouping:**
- Groups of 3 positions alternate between white and light gray background
- Makes it easy to see which 3 positions belong to the same signal

### 4. CSV Export
- All columns including `position_group_id` and `position_num` are exported
- Users can filter/group by `position_group_id` in Excel
- Each position row includes full signal data plus outcome

### 5. Import Added
Added `import uuid` at top of file for generating unique position group IDs.

## Usage

### For Users:
1. Enable "Use Multiple TP Levels (Live Bot Mode)" checkbox
2. Run signal analysis
3. Results show 3 rows per signal:
   - Position 1: Closes at TP1 only
   - Position 2: Aims for TP2, trails after TP1
   - Position 3: Aims for TP3, trails after TP1
4. Visual grouping (alternating gray rows) shows which positions belong together
5. Export to CSV to analyze in Excel

### Configuration:
- Trailing percentage: Uses existing `self.trailing_pct` (default 50%)
- TP levels: Uses regime-based defaults or custom values
- All configured via existing GUI controls

## Testing Scenarios

### Scenario 1: All TPs Hit
- Price: Entry → TP1 → TP2 → TP3
- Expected:
  - Pos 1: Closes at TP1 ✅
  - Pos 2: Closes at TP2 ✅
  - Pos 3: Closes at TP3 ✅

### Scenario 2: TP1 Hit, Then Reversal
- Price: Entry → TP1 → Reverses
- Expected:
  - Pos 1: Closes at TP1 ✅
  - Pos 2: Hits trailing stop (above breakeven) ✅
  - Pos 3: Hits trailing stop (above breakeven) ✅

### Scenario 3: SL Hit Before TP1
- Price: Entry → SL
- Expected:
  - Pos 1: Loss at SL ❌
  - Pos 2: Loss at SL ❌
  - Pos 3: Loss at SL ❌

### Scenario 4: Timeout
- Price: No TP or SL hit within 100 bars
- Expected: All positions close at timeout price

## Key Features

✅ **Independent Positions**: Each position has its own outcome and P&L
✅ **Smart Trailing**: Only positions 2 and 3 use trailing, only after TP1 hits
✅ **Visual Grouping**: Easy to see which 3 positions belong to same signal
✅ **Excel-Friendly**: CSV export with group_id for filtering
✅ **Consistent with Live Bot**: Uses same TP/SL levels and regime detection
✅ **Backward Compatible**: Single-position mode unchanged

## Files Modified

- `/home/runner/work/main/main/trading_app/gui/signal_analysis_dialog.py`
  - Added `import uuid`
  - Added `_calculate_3_position_outcome()` to `SignalAnalysisWorker` (line ~370)
  - Added `_calculate_3_position_outcome()` to `SignalAnalysisWorkerMT5` (line ~1288)
  - Modified `_calculate_signal_outcomes()` in `SignalAnalysisWorker` (line ~215)
  - Modified `_calculate_signal_outcomes()` in `SignalAnalysisWorkerMT5` (line ~1032)
  - Updated `run()` methods to return modified DataFrame
  - Updated `populate_results_table()` (line ~2608) with position column and visual grouping

## Technical Notes

- **UUID Generation**: Uses `uuid.uuid4()` for unique group IDs
- **DataFrame Manipulation**: Replaces original single row with 3 position rows
- **Memory Efficient**: Only creates additional rows for multi-TP mode
- **Type Safety**: All position data properly typed and validated
- **Color Coding**: Uses Qt.lightGray for alternating groups

## Future Enhancements

Possible improvements:
- Configurable position sizes (currently all equal)
- Different trailing percentages per position
- Additional position targets (4+ positions)
- Performance metrics aggregated by position group
- Position-level charts/visualization
