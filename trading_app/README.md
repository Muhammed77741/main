# 🪟 Trading Bot Manager - Windows GUI Application

Professional GUI application for managing XAUUSD, BTC, and ETH trading bots.

## 📋 Phase 1 Features (MVP)

✅ **Bot Management**
- Start/Stop bots with one click
- Configure each bot independently
- Real-time status monitoring

✅ **Multi-Bot Support**
- 🥇 XAUUSD (Gold) - MT5
- ₿ BTC - Binance
- ⟠ ETH - Binance

✅ **Real-Time Monitoring**
- Live logs display
- Position monitoring
- Account balance tracking
- P&L calculations

✅ **Configuration**
- Easy settings dialog
- API key management (encrypted in DB)
- Strategy parameters (TP levels, risk %)
- Telegram notifications

✅ **Statistics & History**
- Trade history with details
- Win rate, profit factor, etc.
- Export to CSV
- Filter by date range

---

## 🚀 Installation

### Prerequisites

1. **Python 3.10+** installed
2. **MetaTrader 5** (for XAUUSD bot)
3. **Binance API keys** (for BTC/ETH bots)

### Install Dependencies

```bash
cd trading_app
pip install -r requirements.txt
```

---

## 🎯 Quick Start

### 1. Run the application

```bash
python main.py
```

### 2. Configure a bot

1. Select a bot from the list (XAUUSD, BTC, or ETH)
2. Click "⚙ Settings"
3. Configure parameters:
   - **For Binance bots**: Enter API Key and Secret
   - Set risk percentage (default: 2%)
   - Adjust TP levels if needed
   - Enable DRY RUN mode for testing
4. Click "Save"

### 3. Start trading

1. Click "▶ Start Bot"
2. Monitor logs in real-time
3. Check positions with "📊 Positions"
4. View statistics with "📈 Statistics"

### 4. Stop the bot

1. Click "⏹ Stop Bot"
2. Bot will gracefully stop after current cycle

---

## 📊 Bot Configuration

### XAUUSD Bot (Gold)

**Requirements:**
- MetaTrader 5 installed and running
- MT5 account (demo or live)
- Symbol: XAUUSD available

**Default Settings:**
- Exchange: MT5
- Timeframe: 1H
- TREND TP: 30/55/90 points
- RANGE TP: 20/35/50 points
- Multi-TP: 3 positions per signal

### BTC/ETH Bots (Crypto)

**Requirements:**
- Binance account
- API keys with Futures trading permission
- USDT balance

**Default Settings:**
- Exchange: Binance Futures
- Timeframe: 1H
- TREND TP: 1.5/2.75/4.5%
- RANGE TP: 1.0/1.75/2.5%
- Single position per signal

---

## 🎛️ Settings Explained

### Trading Parameters

- **Risk per trade**: % of balance to risk per trade (1-10%)
- **Max positions**: Maximum simultaneous positions (1-20)
- **Timeframe**: Chart timeframe for analysis
- **DRY RUN**: Test mode - no real trades

### Strategy Parameters

**TREND Mode** (strong trend detected):
- Wider TP levels for bigger moves
- More conservative entry

**RANGE Mode** (sideways market):
- Tighter TP levels for quick profits
- More aggressive entry

### Telegram Notifications

1. Create a bot via @BotFather
2. Get your Chat ID via @userinfobot
3. Enter Token and Chat ID in settings
4. Enable notifications

---

## 📈 Monitoring

### Live Logs

- All bot activities logged in real-time
- Color-coded for easy reading
- Auto-scroll to latest

### Positions Monitor

- Shows all open positions
- Entry, current price, SL, TP
- Real-time P&L
- Auto-refresh every 5 seconds

### Statistics

- Total trades, win rate, profit factor
- Best/worst trades
- Export to CSV for analysis
- Filter by date range

---

## 🗄️ Database

The app uses SQLite to store:
- Bot configurations
- Trade history
- Bot status
- Application logs

**Location**: `trading_app.db` in the app directory

**Backup**: Copy the `.db` file to backup your data

---

## ⚠️ Safety Features

### DRY RUN Mode

- Enabled by default
- Simulates trading without real orders
- Test strategies risk-free

### Confirmation Dialogs

- Starting in LIVE mode requires confirmation
- Stopping bots requires confirmation
- Closing app with running bots requires confirmation

### Error Handling

- Connection errors are logged
- Failed trades are logged
- Bot auto-stops on critical errors

---

## 🛠️ Troubleshooting

### Bot won't start

**XAUUSD Bot:**
- ✅ Check MT5 is running
- ✅ Check MT5 is logged in
- ✅ Check XAUUSD symbol is available

**Crypto Bots:**
- ✅ Check API keys are correct
- ✅ Check internet connection
- ✅ Check Binance API permissions
- ✅ Try Testnet mode first

### No signals detected

- This is normal - bot waits for good setups
- Check that market is open
- Check that symbol has recent price data

### Positions not showing

- Refresh positions monitor
- Check exchange connection
- Verify bot is actually running

---

## 📁 Project Structure

```
trading_app/
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── trading_app.db          # Database (created on first run)
│
├── gui/                    # GUI components
│   ├── main_window.py      # Main window
│   ├── settings_dialog.py  # Settings dialog
│   ├── positions_monitor.py # Positions monitor
│   └── statistics_dialog.py # Statistics dialog
│
├── core/                   # Core logic
│   ├── bot_manager.py      # Bot management
│   └── bot_thread.py       # Bot thread
│
├── models/                 # Data models
│   ├── bot_config.py       # Config model
│   ├── bot_status.py       # Status model
│   └── trade_record.py     # Trade model
│
├── database/               # Database layer
│   └── db_manager.py       # SQLite manager
│
└── utils/                  # Utilities
    └── (future utils)
```

---

## 🚧 Phase 2 Features (Future)

These features will be added later:

- [ ] License system
- [ ] Code obfuscation
- [ ] Auto-updater
- [ ] Advanced backtesting in GUI
- [ ] Multiple bot instances
- [ ] Cloud sync
- [ ] Mobile app

---

## 💡 Tips

### For Best Results:

1. **Start with DRY RUN** - Test before going live
2. **Use Testnet** for crypto bots first
3. **Monitor regularly** - Check the app daily
4. **Keep risk low** - Start with 1-2% risk
5. **Diversify** - Run multiple bots on different assets

### Performance:

- App uses ~200-500 MB RAM
- Minimal CPU usage when idle
- Internet connection required
- Runs 24/7 in background

---

## 📞 Support

### Check Logs:
1. View logs in the Live Logs section
2. Check `trading_app.db` for stored data
3. Review CSV trade logs in bot directories

### Common Issues:
- See Troubleshooting section above
- Check bot-specific READMEs in `trading_bots/` directory

---

## ⚖️ Disclaimer

**IMPORTANT**: Trading carries risk. This software is provided as-is without any guarantees. Always test on demo/testnet accounts before live trading. The developers are not responsible for any financial losses.

---

## 📜 License

Part of the Trading Bots project.

---

**Ready to trade!** 🚀

Start the app with `python main.py` and manage all your bots from one place.
