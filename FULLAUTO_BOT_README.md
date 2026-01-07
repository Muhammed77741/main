# Full-Auto Trading Bot

⚠️ **DANGER: This bot trades automatically without your confirmation!**

## Overview

This full-auto trading bot uses the **V3 Adaptive Strategy** (Pattern Recognition + Fibonacci 1.618) to automatically trade XAUUSD on MT5.

## Features

- ✅ Automatic signal detection using V3 Adaptive Strategy
- ✅ Automatic position opening/closing
- ✅ Risk management (configurable risk per trade)
- ✅ Position limits (max simultaneous positions)
- ✅ Telegram notifications (optional)
- ✅ **DRY RUN mode** for safe testing
- ✅ **Real-time TP monitoring** (checks every 10 seconds)
- ✅ **Multi-level TP tracking** (TP1, TP2, TP3) with detailed logging

## Requirements

```bash
pip install MetaTrader5 python-dotenv python-telegram-bot pandas numpy
```

## Quick Start

### 1. Test Mode (DRY RUN - Recommended First!)

```bash
python run_fullauto_bot.py --dry-run
```

This will:
- ✅ Analyze the market
- ✅ Find signals
- ✅ Calculate positions
- ✅ Log everything
- ❌ **NOT execute real trades**

### 2. Live Trading (DANGEROUS!)

**Interactive Mode (with confirmation prompts):**
```bash
python run_fullauto_bot.py
```

**Automated Mode (NO confirmation - for scripts/cron):**
```bash
# With default settings (2% risk, 3 max positions)
python run_fullauto_bot.py --no-confirm

# With custom settings
python run_fullauto_bot.py --no-confirm --risk 1.5 --max-positions 2
```

⚠️ **Only use `--no-confirm` for:**
- Automated deployment (systemd, cron, docker)
- DEMO accounts after extensive testing
- Production ONLY after 30+ days successful DEMO testing

⚠️ **Only use live trading after:**
1. Testing in DRY RUN mode for 7+ days
2. Testing on DEMO account for 7+ days  
3. Understanding the V3 Adaptive Strategy
4. Setting appropriate risk (1-2% recommended)

## Configuration

### Command Line Arguments

```bash
python run_fullauto_bot.py [OPTIONS]

Options:
  --dry-run              Run in test mode (no real trades)
  --no-confirm           Skip confirmation prompts (DANGEROUS!)
  --risk FLOAT           Risk per trade, 0.5-5.0% (default: 2.0)
  --max-positions INT    Max positions, 1-5 (default: 3)
  -h, --help             Show help message
```

### Examples

```bash
# Test mode (safe)
python run_fullauto_bot.py --dry-run

# Live with defaults, interactive confirmation
python run_fullauto_bot.py

# Live with custom risk, interactive confirmation
python run_fullauto_bot.py --risk 1.5 --max-positions 2

# Automated mode (no prompts) - for cron/systemd
python run_fullauto_bot.py --no-confirm --risk 2.0 --max-positions 3
```

### Default Settings

- Risk per trade: 2.0%
- Max positions: 3
- Check interval: 1 hour
- Symbol: XAUUSD
- Timeframe: H1

### Interactive Configuration

If you run without `--no-confirm` and without specifying `--risk` and `--max-positions`, the bot will prompt you for:
- Risk per trade (0.5-5.0%)
- Max positions (1-5)

### Telegram Notifications (Optional)

Create `.env` file:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Get your bot token from [@BotFather](https://t.me/BotFather) on Telegram.

## How It Works

1. **Every hour**, the bot:
   - Downloads latest XAUUSD H1 data from MT5
   - Runs V3 Adaptive Strategy analysis
   - Detects TREND vs RANGE market conditions
   - Looks for Pattern Recognition signals

2. **If signal found**:
   - Calculates position size based on risk %
   - Checks max position limits
   - Opens 3 positions with different TP levels (TP1, TP2, TP3)
   - TP levels adapt based on market regime (TREND: 30/55/90p, RANGE: 20/35/50p)

3. **Real-time monitoring** (every 10 seconds):
   - Checks all open positions for TP hits
   - Logs TP hits to `bot_tp_hits_log.csv`
   - Sends Telegram notifications (if configured)
   - Tracks closed positions

4. **MT5 handles**:
   - Stop loss execution
   - Take profit execution
   - Position management

## Safety Features

### Built-in Protection

- ✅ Position limits (max 3 by default)
- ✅ Risk management (% per trade)
- ✅ Duplicate position check (won't open multiple LONGs)
- ✅ Account type detection (warns if REAL account)
- ✅ Connection testing before start

### DRY RUN Mode

Test everything without risking money:
```bash
python run_fullauto_bot.py --dry-run
```

## Testing Workflow

### Phase 1: DRY RUN (1-2 days)
```bash
python run_fullauto_bot.py --dry-run
```
- Verify signals are detected
- Check position calculations
- Ensure bot runs stable

### Phase 2: DEMO Account (7+ days)
```bash
# Use MT5 DEMO account
python run_fullauto_bot.py
```
- Monitor real execution
- Track performance
- Verify SL/TP work correctly

### Phase 3: LIVE (Only after success in Phase 1 & 2)
```bash
# Use MT5 REAL account - BE CAREFUL!
python run_fullauto_bot.py
```
- Start with minimum risk (0.5-1%)
- Monitor closely for first week
- Gradually increase risk if successful

## Monitoring

### Running as a Service

For automated deployment, create a systemd service:

```ini
# /etc/systemd/system/trading-bot.service
[Unit]
Description=Full-Auto Trading Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/repo
ExecStart=/usr/bin/python3 run_fullauto_bot.py --no-confirm --risk 2.0 --max-positions 3
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo journalctl -u trading-bot -f  # View logs
```

### Cron Job

For periodic execution (not recommended for continuous trading):
```bash
# Run bot every hour
0 * * * * cd /path/to/repo && python3 run_fullauto_bot.py --no-confirm --risk 2.0
```

### Logging

The bot logs:
- Market analysis results
- Signals found
- Positions opened
- **TP hits in real-time** (NEW!)
- Errors and warnings

**Log Files:**
- `bot_trades_log.csv`: Complete trade history (when positions close)
- `bot_tp_hits_log.csv`: Real-time TP hit events with detailed metrics
  - Tracks TP1, TP2, and TP3 separately
  - Includes: timestamp, ticket, TP level, profit, pips, duration, and more
  - See [TP_MONITORING_README.md](TP_MONITORING_README.md) for details

Check console output or redirect to file:
```bash
python run_fullauto_bot.py --no-confirm > bot.log 2>&1

# View TP hits log
cat bot_tp_hits_log.csv

# Analyze TP performance
tail -n 20 bot_tp_hits_log.csv
```

## Stopping the Bot

Press `Ctrl+C` to stop the bot gracefully.

## ⚠️ WARNINGS

1. **Can lose money**: Bot can lose ALL your trading capital
2. **No guarantees**: Past performance ≠ future results
3. **Technical risks**: Software bugs, connection issues, etc.
4. **Market risks**: Unexpected events, slippage, gaps
5. **Your responsibility**: You accept all risks

## Strategy Details

The bot uses **V3 Adaptive Strategy**:
- **TREND mode**: TP at 30p/55p/90p with trailing 18p
- **RANGE mode**: TP at 20p/35p/50p with trailing 15p
- **Signal source**: Pattern Recognition (triangles, flags, H&S)
- **TP calculation**: Fibonacci 1.618 extension
- **Entry filters**: Time, volatility, market structure

See `BACKTEST_ANALYSIS_FULL.md` for detailed strategy explanation.

## Backtest Results (After Bug Fix)

| Metric | Value |
|--------|-------|
| Total PnL | +83.52% (1 year) |
| Win Rate | 70.8% |
| Profit Factor | 1.98 |
| Max DD | -7.67% |
| Trades | 373 |

⚠️ **Backtest results do not guarantee live performance!**

## Troubleshooting

### MT5 Connection Failed
1. Ensure MT5 is running
2. Enable "Algo Trading" in MT5 Tools → Options
3. Login to your account
4. Check XAUUSD is in Market Watch

### No Signals Found
- Strategy is selective (only high-quality setups)
- May wait hours/days for good signals
- Normal behavior

### Position Not Opening
- Check account balance
- Check margin requirements
- Check MT5 logs for errors
- Verify symbol is tradable

## Support

This is experimental software. Use at your own risk.

For strategy questions, see documentation:
- `BACKTEST_ANALYSIS_FULL.md`
- `BACKTEST_SUMMARY_RU.md`
- `BUG_REPORT_SL_TP_SWAP.md`

## License

Use at your own risk. No warranties.
