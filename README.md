# 🤖 Trading Bots Project

Unified trading bot system for XAUUSD (Gold), BTC, and ETH with automatic trading strategies.

## 📁 Project Structure

```
.
├── trading_bots/              # Core bot modules
│   ├── xauusd_bot/           # Gold trading bot (MT5)
│   ├── crypto_bot/           # Crypto trading bots (Binance)
│   └── shared/               # Shared strategy modules
│
├── trading_app/              # Windows GUI Application
│   ├── main.py              # GUI entry point
│   ├── build_exe.py         # Build Windows .exe
│   └── ...                  # GUI components
│
├── run_xauusd_bot.py        # XAUUSD bot launcher
└── run_crypto_bot.py        # BTC/ETH bot launcher
```

## 🚀 Quick Start

### 1. Prerequisites

**For XAUUSD Bot:**
- Python 3.10+
- MetaTrader 5 installed and running
- MT5 account (demo or live)

**For Crypto Bots:**
- Python 3.10+
- Binance account with Futures enabled
- Binance API keys

### 2. Install Dependencies

```bash
# For XAUUSD bot
pip install -r trading_bots/xauusd_bot/requirements.txt

# For crypto bots
pip install -r trading_bots/crypto_bot/requirements.txt

# For Windows GUI app
pip install -r trading_app/requirements.txt
```

### 3. Configure Environment

Create `.env` file in project root:

```bash
# For XAUUSD (optional - Telegram only)
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id

# For Crypto Bots (required)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BINANCE_TESTNET=true  # Use testnet (recommended for testing)

# Telegram (optional for all bots)
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 🎯 Running Bots

### Command Line (with safety checks)

**XAUUSD Bot:**
```bash
# Dry run (test mode - no real trades)
python run_xauusd_bot.py --dry-run

# Live trading
python run_xauusd_bot.py
```

**Crypto Bots:**
```bash
# BTC dry run
python run_crypto_bot.py BTC --dry-run

# ETH live trading
python run_crypto_bot.py ETH

# With custom risk settings
python run_crypto_bot.py BTC --risk 1.5 --max-positions 2
```

### Windows GUI Application

```bash
cd trading_app
python main.py
```

The GUI allows you to:
- Start/stop multiple bots
- Configure each bot independently
- Monitor positions in real-time
- View statistics and trade history
- Export trades to CSV

## ⚠️ Disclaimer

Trading involves significant risk. This software is provided as-is for educational purposes. Always test on demo/testnet accounts first. The developers are not responsible for any financial losses.

---

**Start safely:** `python run_crypto_bot.py BTC --dry-run`
