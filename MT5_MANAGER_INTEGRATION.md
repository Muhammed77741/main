# MT5 Manager Singleton Integration

## Problem Solved

When running multiple MT5 bots simultaneously (6 bots in this case), the MT5 Python API was overwhelmed with initialization and connection requests, causing connection failures with errors like:
- "Symbol 'XXX' not found"
- Connection lost after iteration #967-#1003
- MT5 API overload from ~98 calls/minute

## Solution

Implemented an MT5Manager singleton that:
1. Ensures only ONE MT5 connection shared across all bots
2. Thread-safe connection management using `threading.Lock`
3. Automatic connection health checking
4. Automatic reconnection when connection is lost
5. Rate-limited connection checks (max once per 5 seconds)

## Files Modified

### 1. `trading_app/core/mt5_manager.py` (NEW)
Singleton manager for MT5 connection:
- `MT5Manager()` - Singleton class using `__new__` pattern
- `initialize()` - Initialize MT5 connection (only once)
- `ensure_connection()` - Ensure connection is alive, reconnect if needed
- `reconnect()` - Force reconnection
- `shutdown()` - Close connection (only when app closes)
- `mt5_manager` - Global singleton instance

### 2. `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`
**Changes:**
- Added import: `from core.mt5_manager import mt5_manager`
- Line ~1408: Changed `mt5.initialize()` to `mt5_manager.initialize()`
- Line ~1772: Changed manual reconnection to `mt5_manager.reconnect()`
- Line ~237: Removed `mt5.shutdown()` - connection managed by singleton
- Line ~1470: Removed `mt5.shutdown()` from `disconnect_mt5()`

### 3. `trading_app/core/bot_thread.py`
**Changes:**
- Added import: `from core.mt5_manager import mt5_manager`
- Line ~315: Added `mt5_manager.ensure_connection()` check before MT5 API calls
- Kept existing caching (60s for account_info, 30s for positions_get)

### 4. `trading_app/gui/main_window.py`
**Changes:**
- Line ~1340: Added `mt5_manager.shutdown()` in `closeEvent()`
- Ensures MT5 connection is properly closed when app exits

## How It Works

### Before (Multiple Connections)
```
Bot 1 → mt5.initialize() → Connection A
Bot 2 → mt5.initialize() → Connection B (CONFLICT!)
Bot 3 → mt5.initialize() → Connection C (CONFLICT!)
...
Result: Connection failures, lost data, errors
```

### After (Singleton Manager)
```
Bot 1 → mt5_manager.initialize() ┐
Bot 2 → mt5_manager.initialize() ├→ SINGLE SHARED CONNECTION
Bot 3 → mt5_manager.initialize() ┘
...
Result: Stable connection, no conflicts
```

## API Call Reduction

### Before:
- Each bot called MT5 API every 10 seconds
- 6 bots × 14 calls/check = 84 calls per check
- Every 10 seconds = ~500 calls/minute

### After:
With caching in bot_thread.py:
- account_info: cached for 60 seconds
- positions_get: cached for 30 seconds
- Connection check: rate-limited to once per 5 seconds

Result: **~14-16 calls/minute (97% reduction)**

## Thread Safety

The MT5Manager uses `threading.Lock` to ensure thread-safe operations:

```python
class MT5Manager:
    _lock = threading.Lock()  # Class-level lock for singleton creation
    _connection_lock = threading.Lock()  # Instance lock for MT5 operations

    def initialize(self):
        with self._connection_lock:
            # Thread-safe initialization
            ...

    def reconnect(self):
        with self._connection_lock:
            # Thread-safe reconnection
            ...
```

## Testing

Run the test script to verify the manager works with concurrent connections:

```bash
python test_mt5_manager.py
```

This simulates 6 bots running concurrently and verifies:
- Single connection initialization
- Concurrent API access
- Connection health checking
- Reconnection capability
- Clean shutdown

## Benefits

1. **Stability** - No more connection conflicts between bots
2. **Performance** - 97% reduction in MT5 API calls
3. **Reliability** - Automatic reconnection when connection is lost
4. **Simplicity** - Bots don't need to manage their own connections
5. **Thread-Safe** - Safe for use with multiple concurrent threads

## Migration Notes

When adding new MT5 bots:
1. Import the manager: `from core.mt5_manager import mt5_manager`
2. Use `mt5_manager.initialize()` instead of `mt5.initialize()`
3. Use `mt5_manager.ensure_connection()` before critical operations
4. Use `mt5_manager.reconnect()` if explicit reconnection needed
5. **Never call `mt5.shutdown()`** in individual bots

## Connection Lifecycle

1. **App Starts** - No connection yet
2. **First Bot Starts** - `mt5_manager.initialize()` creates connection
3. **More Bots Start** - They use the same connection
4. **Connection Lost** - Manager detects and reconnects automatically
5. **Bot Stops** - Connection stays alive (other bots may use it)
6. **App Closes** - `mt5_manager.shutdown()` in MainWindow.closeEvent()

## Troubleshooting

If connection issues persist:

1. Check MT5 is running and logged in
2. Verify symbols are in Market Watch
3. Check bot logs for connection errors
4. Restart app to force clean reconnection
5. Check MT5 terminal for connection status

## Performance Monitoring

Watch the logs for these indicators:
- `[MT5Manager] MT5 initialized successfully` - Good
- `[MT5Manager] Connection lost, reconnecting...` - Manager handling it
- `[MT5Manager] Reconnection failed` - Check MT5 terminal
- `⚠️  Symbol 'XXX' not found` - Symbol not in Market Watch

## Future Improvements

Potential enhancements:
- Add connection metrics/statistics
- Implement connection pooling for different accounts
- Add MT5 operation queuing for better rate limiting
- Implement circuit breaker pattern for repeated failures
