# Trailing Stop Simulation

Comprehensive testing tool for the 3-position trailing stop strategy.

## Features

✅ **Historical Data Simulation**
- Simulates price movements based on predefined scenarios
- Tests different market conditions: uptrend, downtrend, reversal

✅ **3-Position Group Testing**
- Opens 3 positions with different TP levels (TP1, TP2, TP3)
- TP1: 30-40% profit target (closes first, activates trailing)
- TP2: 60-80% profit target (with trailing stop)
- TP3: 100-120% profit target (with trailing stop)

✅ **Trailing Stop Mechanism**
- Activates after TP1 is hit
- 50% retracement from max/min price
- Only moves in profitable direction
- Detailed logging of every SL update

✅ **Broker Integration Testing**
- Simulates sending SL updates to broker
- Shows when and how SL modifications are sent
- Tests atomic broker-first updates

✅ **Database Persistence Testing**
- Simulates saving position group state to database
- Tracks tp1_hit, max_price, min_price
- Shows database save operations

✅ **Restart Recovery Testing**
- Simulates bot shutdown mid-trade
- Tests state restoration from database
- Verifies trailing continues after restart

✅ **Multi-Pair Support**
- XAUUSD (Gold)
- BTCUSDT (Bitcoin)
- ETHUSDT (Ethereum)

## Usage

### Run Complete Simulation

```bash
cd /home/runner/work/main-1/main-1/trading_bots/simulation
python trailing_stop_simulator.py
```

This runs 4 pre-configured scenarios across all pairs.

### Scenarios Tested

**1. XAUUSD - Strong Uptrend with Retracement**
- Entry: 2870, SL: 2850
- Tests trailing stop activation and retracement trigger
- Expected: TP1 closes, trailing activates, SL triggered on pullback

**2. BTCUSDT - Parabolic Rise**
- Entry: 89000, SL: 87500
- Tests strong momentum with all TPs hit
- Expected: All 3 positions reach their TPs

**3. ETHUSDT - SELL Downtrend with Reversal**
- Entry: 3400, SL: 3450
- Tests SELL positions and trailing in downtrend
- Expected: TP1 closes, trailing activates, reversal triggers trailing SL

**4. XAUUSD - Immediate Reversal (Worst Case)**
- Entry: 2870, SL: 2850
- Tests quick reversal before TP1
- Expected: All positions hit initial SL

## Output Example

```
🎯 TRAILING STOP SIMULATION - XAUUSD
================================================================================
Direction: BUY
Entry Price: 2870.0
Initial SL: 2850.0
TP1 (Pos 1): 2930.0
TP2 (Pos 2): 2960.0
TP3 (Pos 3): 2990.0
Trailing Stop: 50.0% retracement
Group ID: a1b2c3d4...
================================================================================

💹 Price Update #13: 2930
   🎯 TP1 REACHED! Price: 2930, TP1: 2930.0
      ✅ Position closed: TP1 #100001
      Reason: TP1 hit
      Profit: 60.00 pips
      💾 Saved to DB: TP1 closed
   ✅ Trailing stop ACTIVATED for Pos2 & Pos3

💹 Price Update #15: 2940
   📈 New MAX price: 2935 → 2940
      💾 Saved to DB: max_price updated
   🔼 TP2 Trailing SL: 2850.0 → 2885.0
      📤 Sending SL update to broker: Ticket #100002, SL=2885.0
      💾 Saved to DB: TP2 SL updated
   🔼 TP3 Trailing SL: 2850.0 → 2885.0
      📤 Sending SL update to broker: Ticket #100003, SL=2885.0
      💾 Saved to DB: TP3 SL updated
```

## Custom Scenarios

To create custom scenarios, modify the `main()` function:

```python
custom_sequence = [100, 105, 110, 115, 120, 115, 110, 105]

run_simulation(
    symbol="CUSTOM",
    scenario_name="My Custom Test",
    entry=100.0,
    sl=95.0,
    tp1=110.0,
    tp2=120.0,
    tp3=130.0,
    direction="BUY",
    price_sequence=custom_sequence
)
```

## Validation Checklist

After running simulation, verify:

- [x] TP1 correctly triggers and closes first position
- [x] Trailing stop activates ONLY after TP1 hit
- [x] SL updates sent to broker with each trailing movement
- [x] Database saves occur on state changes
- [x] Max/min price tracks correctly
- [x] Restart recovery maintains trailing state
- [x] Trailing SL only moves in profitable direction
- [x] Retracement correctly triggers trailing SL
- [x] Works for both BUY and SELL directions

## Integration with Real Bot

The simulation demonstrates the logic that's implemented in:
- `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`
- `trading_bots/crypto_bot/live_bot_binance_fullauto.py`

Key methods tested:
- `_check_tp_sl_realtime()` - TP/SL monitoring
- `_update_trailing_stop()` - Trailing calculation
- `_send_sl_to_broker()` - Broker synchronization
- `save_position_group()` - Database persistence

## Notes

- Simulation uses mock broker/database operations
- Real implementation requires MT5/Binance API integration
- Timing delays (0.3s between updates) added for readability
- Can be adapted for live paper trading with real price feeds
