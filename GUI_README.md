# Trading Bot Manager GUI

An attractive and informative graphical user interface for managing cryptocurrency and forex trading bots.

## Features

### Visual Design
- **Large, Prominent Title**: "🤖 TRADING BOT MANAGER" displayed in 32pt bold font
- **Modern Dark Theme**: Professional color scheme with dark background (#1e1e2e)
- **Informative Layout**: Three-panel design (bot list, details, activity log)
- **Color-Coded Status**: 
  - Green for running bots and profits
  - Red for stopped bots and losses
  - Blue accents for highlights

### Bot Management
- **Multiple Bot Support**: Manage BTC/USDT, ETH/USDT, and XAUUSD trading bots
- **Individual Bot Cards**: Each bot displays:
  - Current status (Running/Stopped)
  - Profit & Loss (P&L)
  - Number of open positions
- **Easy Selection**: Click "Select" to view detailed information

### Monitoring & Controls
- **Real-Time Statistics**:
  - Account Balance
  - Total P&L with percentage
  - Open Positions (current/maximum)
  - Win Rate
  - Total Trades
  - Active Strategy
- **Bot Controls**:
  - ▶ START BOT - Launch trading bot
  - ⏹ STOP BOT - Stop active trading
  - ⚙️ SETTINGS - Configure bot parameters
- **Live Activity Log**: Real-time log messages with timestamps
- **Auto-Updating Footer**: Connection status and current time

## Running the Application

### Requirements
- Python 3.8+
- tkinter (usually included with Python)

### Installation
```bash
# Install tkinter if not present (Ubuntu/Debian)
sudo apt-get install python3-tk

# No additional packages required
```

### Usage
```bash
# Run the GUI
python3 trading_bot_gui.py
```

## Usage Instructions

1. **Select a Bot**: Click the "Select" button on any bot card in the left panel
2. **View Details**: The center panel will show detailed statistics for the selected bot
3. **Start Trading**: Click "▶ START BOT" to begin trading
4. **Monitor Activity**: Watch the live activity log for real-time updates
5. **Stop Trading**: Click "⏹ STOP BOT" to stop the bot safely
6. **Configure**: Click "⚙️ SETTINGS" to adjust bot parameters (coming soon)

## Interface Overview

```
┌─────────────────────────────────────────────────────────┐
│  🤖 TRADING BOT MANAGER                                 │
│  Advanced Cryptocurrency & Forex Trading System         │
├──────────┬──────────────────────────────────────────────┤
│          │                                               │
│  Bot     │         Bot Details & Controls                │
│  List    │                                               │
│          │                                               │
├──────────┴──────────────────────────────────────────────┤
│                Live Activity Log                         │
└─────────────────────────────────────────────────────────┘
```

## Color Scheme

- **Background**: Dark blue-gray (#1e1e2e)
- **Text**: Light purple-gray (#cdd6f4)
- **Accents**: Sky blue (#89b4fa)
- **Success**: Green (#a6e3a1)
- **Danger**: Pink (#f38ba8)
- **Warning**: Yellow (#f9e2af)
- **Cards**: Darker blue-gray (#313244)
- **Title**: Light purple (#cba6f7)

## Future Enhancements

- Integration with actual trading bot backends
- Real-time chart visualization
- Settings dialog for bot configuration
- Position management interface
- Trade history viewer
- Performance analytics
- Export functionality
- Multi-language support

## License

Part of the Trading Bot System project.
