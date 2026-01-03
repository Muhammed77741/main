#!/bin/bash
# Скрипт для запуска live paper trading бота

echo "=================================="
echo "🤖 Starting Live Paper Trading Bot"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo ""
    echo "Creating template .env file..."
    echo ""
    cat > .env << 'ENVFILE'
# Telegram Bot Configuration (optional)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Check interval in seconds (default: 3600 = 1 hour)
CHECK_INTERVAL=3600
ENVFILE
    
    echo "✅ Created .env file"
    echo ""
    echo "Please edit .env and add your Telegram credentials"
    echo "Or press Enter to run WITHOUT Telegram notifications..."
    read
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
python3 -c "import yfinance" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  yfinance not installed!"
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "🚀 Starting bot..."
echo "Press Ctrl+C to stop"
echo ""

python3 paper_trading.py
