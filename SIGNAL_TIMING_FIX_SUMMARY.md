# Signal Timing Fix and Telegram Error Resolution

## Summary of Changes

This PR addresses two critical issues in the live trading system:

### 1. Signal Timing Alignment with Candle Close ✅

**Problem**: In backtesting, positions opened exactly after candle close, but in live GUI trading_app, signals were checked immediately when the bot started, causing inconsistent behavior between backtesting and live trading.

**Solution**: Modified `bot_thread.py` to wait until the next candle close before checking for signals, ensuring signals are only analyzed at exact candle boundaries (01:00, 02:00, etc. for 1-hour timeframe).

**Key Changes**:
- Added `_calculate_seconds_until_next_candle_close()` to calculate time until next candle boundary
- Added `_wait_for_next_candle_close()` to wait for candle close before first signal check
- Modified main bot loop to align with candle timing
- Changed position monitoring interval from 10 seconds to 5 seconds

### 2. Telegram Event Loop Error Fix ✅

**Problem**: Telegram notifications were failing with `RuntimeError('Event loop is closed')` error.

**Root Cause**: The async `send_telegram()` method was being called with `asyncio.run()` repeatedly, which creates and closes a new event loop each time. In threaded environments (like the bot's QThread), this causes the "Event loop is closed" error.

**Solution**: Converted `send_telegram()` to a synchronous wrapper that properly handles event loop states:
- Checks if event loop is closed and creates a new one if needed
- Detects if loop is already running (threaded environment) and skips gracefully
- Proper error handling and cleanup

## Files Modified

### 1. `trading_app/core/bot_thread.py`
- **Line 1-13**: Added `time` and `datetime` imports to top of file
- **Line 265-276**: Added `_get_timeframe_seconds()` method
- **Line 278-302**: Added `_calculate_seconds_until_next_candle_close()` method
- **Line 304-329**: Added `_wait_for_next_candle_close()` method
- **Line 331-368**: Added `_wait_for_next_candle_with_monitoring()` method
- **Line 160-166**: Modified `_run_bot_loop()` to wait for candle close before starting
- **Line 191**: Changed from waiting fixed 3600s to waiting for next candle close
- **Line 195, 198, 202, 205, 209, 212, 217**: Changed interval from 10s to 5s

### 2. `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`
- **Line 972-1008**: Converted `send_telegram()` from async to sync wrapper
  - Proper event loop state handling
  - Graceful handling of running loops
  - Better error recovery and cleanup
- **All occurrences**: Removed `asyncio.run()` wrapper calls (10 locations)

### 3. `trading_bots/crypto_bot/live_bot_binance_fullauto.py`
- **Line 1642-1678**: Converted `send_telegram()` from async to sync wrapper
  - Proper event loop state handling
  - Graceful handling of running loops
  - Better error recovery and cleanup
- **All occurrences**: Removed `asyncio.run()` wrapper calls (14 locations)

## Testing

### Timing Logic Verification ✅
Created `test_candle_timing.py` to verify the candle close calculation logic:
```
Current Time: 2026-01-20 11:40:04
Next candle close (1h): 2026-01-20 12:00:05
Time until close: 20m 1s (1201 seconds)

✅ SUCCESS: Timing logic is correct!
```

### Code Quality ✅
- No syntax errors
- No security vulnerabilities (CodeQL scan passed)
- Code review completed and addressed

## Impact

### Positive Impacts
1. **Consistent Behavior**: Live trading now matches backtest behavior for signal timing
2. **More Responsive**: Position monitoring now happens every 5 seconds instead of 10
3. **Reliable Notifications**: Telegram errors eliminated
4. **Better Code Quality**: Eliminated code duplication, moved imports to top

### Potential Considerations
1. **Startup Delay**: Bot now waits for next candle close before first signal check (acceptable tradeoff for consistency)
2. **Telegram Skip**: If event loop is already running in thread, Telegram notifications are skipped (acceptable as they're non-critical)

## How It Works

### Signal Timing Flow
```
Bot Start
    ↓
Wait for Next Candle Close (with status updates every 5s)
    ↓
[LOOP START]
    ↓
Check Signal at Candle Close
    ↓
Open Position (if signal exists)
    ↓
Wait for Next Candle Close
    ├─> Monitor Positions (every 5s)
    ├─> Check TP/SL Levels (every 5s)
    ├─> Sync with Exchange (every 5s)
    └─> Update Trailing Stops (every 60s)
    ↓
[LOOP END - Next Candle Close]
```

### Event Loop Handling Flow
```
send_telegram(message)
    ↓
Check Event Loop State
    ├─> Closed? → Create New Loop
    ├─> Running? → Skip (non-critical)
    └─> Available? → Run Async Send
         ↓
    Success or Error (logged)
```

## Deployment Notes

1. **No Breaking Changes**: Existing configurations will work without modification
2. **Backward Compatible**: All existing bot settings are preserved
3. **Immediate Effect**: Changes take effect on next bot start/restart

## Future Improvements

1. Could make the 5-second buffer configurable
2. Could add metrics for tracking signal timing accuracy
3. Could implement background thread for Telegram to avoid skipping in threaded environments
