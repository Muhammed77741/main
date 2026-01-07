# Real-time TP Monitoring Documentation

## Overview

The Full-Auto Trading Bot now includes **real-time Take Profit (TP) monitoring** that continuously tracks open positions and logs when TP levels are hit.

## Features

### 1. Continuous Monitoring
- Checks all open positions every **10 seconds** (even between hourly signal checks)
- Monitors positions during the waiting period between signal analyses
- No TP hits are missed!

### 2. Multi-Level TP Detection
The bot tracks three different TP levels for each position:
- **TP1**: Conservative target (TREND: 30p, RANGE: 20p)
- **TP2**: Moderate target (TREND: 55p, RANGE: 35p)
- **TP3**: Aggressive target (TREND: 90p, RANGE: 50p)

### 3. Detailed Logging
When a TP level is hit, the following information is logged to `bot_tp_hits_log.csv`:

| Field | Description |
|-------|-------------|
| Timestamp | Exact date and time when TP was hit |
| Ticket | MT5 order ticket number |
| TP_Level | Which TP was hit (TP1, TP2, or TP3) |
| Type | Position type (BUY or SELL) |
| Volume | Position size in lots |
| Entry_Price | Entry price of the position |
| TP_Target | Target TP price |
| Current_Price | Actual price when TP was detected |
| SL | Stop Loss level |
| Profit | Estimated profit in account currency |
| Pips | Profit in pips |
| Market_Regime | Market regime when position was opened (TREND or RANGE) |
| Duration_Minutes | How long it took to hit TP (in minutes) |
| Comment | Position comment (e.g., V3_T_TP1) |

## Log Files

The bot creates two separate log files:

1. **`bot_trades_log.csv`**: Complete trade history (when positions are fully closed)
2. **`bot_tp_hits_log.csv`**: Real-time TP hit events (NEW!)

### Example TP Hits Log

```csv
Timestamp,Ticket,TP_Level,Type,Volume,Entry_Price,TP_Target,Current_Price,SL,Profit,Pips,Market_Regime,Duration_Minutes,Comment
2026-01-07 10:15:30,123456,TP1,BUY,0.01,2650.00,2680.00,2680.50,2640.00,30.00,30.0,TREND,45.5,V3_T_TP1
2026-01-07 11:30:15,123457,TP2,BUY,0.01,2650.00,2705.00,2705.20,2640.00,55.00,55.0,TREND,120.3,V3_T_TP2
2026-01-07 14:45:00,123458,TP3,SELL,0.01,2680.00,2630.00,2629.80,2690.00,50.00,50.0,RANGE,180.0,V3_R_TP3
```

## How It Works

### Detection Logic

The bot uses a tolerance-based detection system:

**For BUY positions:**
- TP is considered hit when: `current_price >= (tp_target - tolerance)`
- Tolerance: 0.5 points (to account for slippage)

**For SELL positions:**
- TP is considered hit when: `current_price <= (tp_target + tolerance)`
- Tolerance: 0.5 points (to account for slippage)

### Integration with Bot

The monitoring is integrated at two levels:

1. **During signal check iterations** (every hour on the hour):
   - Checks TP levels immediately after checking for new signals
   - Ensures TP hits are detected even if they occur right at the hour

2. **During waiting periods** (between hours):
   - Continuously monitors every 10 seconds
   - This is the main real-time monitoring component

### Position Tracking

Each opened position is tracked in memory with:
- Ticket number
- Position type (BUY/SELL)
- Entry price, SL, and TP
- Market regime (TREND/RANGE)
- Open time
- Comment (identifies TP level)

## Telegram Notifications

When a TP is hit, the bot sends a Telegram notification (if configured) with:
- 🎯 TP HIT alert
- Ticket number
- TP level (TP1, TP2, or TP3)
- Position type and entry price
- TP target vs. current price
- Volume and calculated pips

## Benefits

1. **Transparency**: Know exactly when each TP level is hit
2. **Performance Analysis**: Analyze which TP levels work best in different market conditions
3. **Real-time Updates**: Get immediate notifications when targets are reached
4. **Detailed History**: Keep comprehensive records for backtesting and optimization

## Configuration

No additional configuration is needed! The monitoring is automatically enabled when you run the bot.

### Monitoring Settings

```python
# Built-in settings (in live_bot_mt5_fullauto.py)
monitoring_interval = 10  # Check every 10 seconds
tolerance = 0.5  # 0.5 point tolerance for TP detection
```

## Usage Example

### Starting the Bot

```bash
# Start in live mode (real trades)
python run_fullauto_bot.py

# Start in dry-run mode (testing)
python run_fullauto_bot.py --dry-run
```

### Console Output

When a TP is hit, you'll see:
```
🎯 TP HIT LOGGED: Ticket=123456, Level=TP1, Price=2680.50, Pips=30.5
```

### Checking the Logs

```bash
# View all TP hits
cat bot_tp_hits_log.csv

# Count TP hits by level
grep "TP1" bot_tp_hits_log.csv | wc -l
grep "TP2" bot_tp_hits_log.csv | wc -l
grep "TP3" bot_tp_hits_log.csv | wc -l

# View recent TP hits
tail -n 10 bot_tp_hits_log.csv
```

## Analysis Tips

### Using the TP Hits Log

1. **Success Rate by TP Level**:
   ```python
   import pandas as pd
   
   df = pd.read_csv('bot_tp_hits_log.csv')
   print(df['TP_Level'].value_counts())
   ```

2. **Average Time to Hit TP**:
   ```python
   avg_duration = df.groupby('TP_Level')['Duration_Minutes'].mean()
   print(avg_duration)
   ```

3. **Performance by Market Regime**:
   ```python
   regime_stats = df.groupby(['Market_Regime', 'TP_Level']).size()
   print(regime_stats)
   ```

## Testing

A test script is provided to verify the monitoring functionality:

```bash
python test_tp_monitoring.py
```

This tests:
- ✅ TP hits log file creation
- ✅ Correct CSV headers
- ✅ TP hit logging functionality
- ✅ Multiple TP level tracking
- ✅ BUY/SELL detection logic

## Troubleshooting

### Issue: TP hits not being logged

**Solution**: 
- Check that positions have proper comments (V3_T_TP1, V3_T_TP2, V3_T_TP3, etc.)
- Verify MT5 connection is active
- Check console output for TP hit messages

### Issue: Too many false detections

**Solution**:
- Increase tolerance value (currently 0.5 points)
- Check for price feed quality from broker

### Issue: Missing TP hits

**Solution**:
- Decrease monitoring interval (currently 10 seconds)
- Check system performance (ensure bot isn't sleeping/frozen)

## Future Enhancements

Potential improvements:
- [ ] Configurable monitoring interval
- [ ] Adjustable tolerance per TP level
- [ ] Email notifications
- [ ] TP hit statistics dashboard
- [ ] Partial close automation based on TP hits

## See Also

- [FULLAUTO_BOT_README.md](FULLAUTO_BOT_README.md) - Main bot documentation
- [QUICK_START_RU.md](QUICK_START_RU.md) - Quick start guide (Russian)
- `bot_trades_log.csv` - Complete trade history
- `bot_tp_hits_log.csv` - TP hits log (created automatically)
