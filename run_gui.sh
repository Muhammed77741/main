#!/bin/bash
# Launcher script for Trading Bot Manager GUI

echo "Starting Trading Bot Manager..."
echo "================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if tkinter is available
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: tkinter is not installed"
    echo "Install with: sudo apt-get install python3-tk (Ubuntu/Debian)"
    exit 1
fi

# Run the GUI
cd "$(dirname "$0")"
python3 trading_bot_gui.py

echo "Trading Bot Manager closed"
