# XAUUSD Bot 3-Position Integration TODO

## Status
✅ Crypto bot completed
⏳ XAUUSD bot - apply same changes

## Changes needed for XAUUSD bot

Apply the EXACT same changes as crypto bot to:
`trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`

### 1. Add import
```python
import uuid  # Add after other imports
```

### 2. Update __init__ signature (line ~39)
```python
def __init__(self, telegram_token=None, telegram_chat_id=None,
             symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1,
             check_interval=3600, risk_percent=2.0, max_positions=9,
             dry_run=False, bot_id=None, use_database=True,
             use_3_position_mode=False, total_position_size=None, min_order_size=None):
```

### 3. Add Phase 2 settings in __init__
Find where `self.use_database` is set, add after it:
```python
# Phase 2: 3-Position Mode settings
self.use_3_position_mode = use_3_position_mode
self.total_position_size = total_position_size
self.min_order_size = min_order_size
```

### 4. Add position_groups tracking
Find `self.positions_tracker = {}`, add after:
```python
# Phase 2: 3-Position Mode tracking
self.position_groups = {}  # {group_id: {'tp1_hit': bool, 'max_price': float, 'min_price': float, 'positions': [...]}}
```

### 5. Update _log_position_opened signature
```python
def _log_position_opened(self, ticket, position_type, volume, entry_price,
                         sl, tp, regime, comment='', position_group_id=None, position_num=0):
```

And update the TradeRecord creation to include:
```python
position_group_id=position_group_id,
position_num=position_num
```

### 6. Refactor open_position method
```python
def open_position(self, signal):
    """Open position(s) with TP/SL - supports single and 3-position modes"""
    if self.use_3_position_mode:
        return self._open_3_positions(signal)
    else:
        return self._open_single_position(signal)

def _open_single_position(self, signal):
    # Move existing open_position code here
    ...
```

### 7. Add _open_3_positions method
Copy from crypto bot `_open_3_positions` but adapt for MT5:
- Replace `self.exchange.create_order()` with MT5 order placement
- Replace `self.symbol` with MT5 symbol format
- Adapt amount/size calculation for MT5 (lots vs quantity)
- Replace asyncio Telegram with MT5-compatible version

### 8. Add _update_3position_trailing method
Copy exactly from crypto bot - logic is same for both.

### 9. Update _check_tp_sl_realtime
Add this line before TP/SL check:
```python
# Phase 2: Update trailing stops for 3-position groups
self._update_3position_trailing({ticket: tracked_pos}, current_price)
```

And update database loading to include:
```python
'position_group_id': trade.position_group_id,
'position_num': trade.position_num
```

## Key differences from Crypto bot

### Order placement (MT5-specific):
```python
# Instead of:
order = self.exchange.create_order(...)

# Use MT5:
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": self.symbol,
    "volume": volume,
    "type": mt5.ORDER_TYPE_BUY if signal['direction'] == 1 else mt5.ORDER_TYPE_SELL,
    "price": mt5.symbol_info_tick(self.symbol).ask,
    "sl": sl,
    "tp": tp,
    "deviation": 20,
    "magic": 234000,
    "comment": comment,
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}
result = mt5.order_send(request)
ticket = result.order  # Use ticket instead of order['id']
```

### Position tracking:
- Use `ticket` (MT5) instead of `order_id` (Binance)
- Volume in lots (0.01, 0.02) instead of quantity
- Prices might be in points (for TP/SL) - check XAUUSD config

## Testing checklist

After implementation:
- [ ] Test dry_run mode with single position
- [ ] Test dry_run mode with 3 positions
- [ ] Verify position_group_id saved to database
- [ ] Check trailing stop updates
- [ ] Test Telegram notifications
- [ ] Verify CSV logging

## Notes

- XAUUSD uses points (30, 55, 90) not percentages
- min_order_size for MT5 is typically 0.01 lots
- total_position_size would be in lots (e.g., 0.1 = 0.1 lots)
- MT5 has different position tracking (tickets vs order IDs)

## Reference

See completed implementation in:
`trading_bots/crypto_bot/live_bot_binance_fullauto.py`
