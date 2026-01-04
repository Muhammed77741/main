#!/usr/bin/env python3
"""
Startup script for Semi-Auto Live Trading Bot

This script:
1. Verifies .env configuration
2. Tests MT5 connection
3. Tests Telegram connection
4. Starts the semi-automatic trading bot

Usage:
    python run_semiauto_bot.py
"""

import os
import sys
from dotenv import load_dotenv
import MetaTrader5 as mt5

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("\n" + "="*80)
    print("🔍 CHECKING CONFIGURATION")
    print("="*80)

    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("\n📝 Please create a .env file with:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token")
        print("   TELEGRAM_CHAT_ID=your_chat_id")
        print("\nHow to get Telegram credentials:")
        print("   1. Create bot: Talk to @BotFather on Telegram")
        print("   2. Get chat ID: Talk to @userinfobot")
        return False

    load_dotenv()

    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not telegram_token or not telegram_chat_id:
        print("❌ Missing Telegram credentials in .env file!")
        print("\n📝 Required variables:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token")
        print("   TELEGRAM_CHAT_ID=your_chat_id")
        return False

    print("✅ .env file configured correctly")
    print(f"   Bot Token: {telegram_token[:10]}...{telegram_token[-5:]}")
    print(f"   Chat ID: {telegram_chat_id}")

    return True

def test_mt5_connection():
    """Test MT5 connection"""
    print("\n" + "="*80)
    print("🔗 TESTING MT5 CONNECTION")
    print("="*80)

    if not mt5.initialize():
        print("❌ Failed to connect to MT5!")
        print("\n📝 Please ensure:")
        print("   1. MetaTrader 5 is installed and running")
        print("   2. 'Algo Trading' is enabled in MT5 (Tools → Options → Expert Advisors)")
        print("   3. You're logged into a demo or live account")
        return False

    # Get account info
    account_info = mt5.account_info()

    if account_info is None:
        print("❌ Failed to get account info!")
        mt5.shutdown()
        return False

    print("✅ Connected to MT5 successfully!")
    print(f"\n💰 Account Information:")
    print(f"   Server: {account_info.server}")
    print(f"   Login: {account_info.login}")
    print(f"   Balance: ${account_info.balance:.2f}")
    print(f"   Equity: ${account_info.equity:.2f}")
    print(f"   Leverage: {account_info.leverage}x")
    print(f"   Currency: {account_info.currency}")

    # Check if XAUUSD is available
    symbol_info = mt5.symbol_info("XAUUSD")
    if symbol_info is None:
        print("\n⚠️  Warning: XAUUSD not found!")
        print("   Bot will try to enable it automatically")
    else:
        print(f"\n✅ XAUUSD is available")
        print(f"   Bid: {mt5.symbol_info_tick('XAUUSD').bid:.2f}")
        print(f"   Ask: {mt5.symbol_info_tick('XAUUSD').ask:.2f}")

    mt5.shutdown()
    return True

def test_telegram_connection():
    """Test Telegram connection"""
    print("\n" + "="*80)
    print("📱 TESTING TELEGRAM CONNECTION")
    print("="*80)

    load_dotenv()
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    try:
        from telegram_notifier import TelegramNotifier

        notifier = TelegramNotifier(telegram_token, telegram_chat_id)

        if notifier.test_connection():
            print("✅ Telegram connection successful!")
            print(f"   Sending test message...")

            message = "✅ **Test Message**\n\nSemi-Auto Bot configuration test successful!"
            notifier.bot.send_message(
                chat_id=telegram_chat_id,
                text=message,
                parse_mode='Markdown'
            )

            print("✅ Test message sent! Check your Telegram.")
            return True
        else:
            print("❌ Telegram connection failed!")
            return False

    except Exception as e:
        print(f"❌ Error testing Telegram: {e}")
        return False

def start_bot():
    """Start the semi-automatic trading bot"""
    print("\n" + "="*80)
    print("🚀 STARTING SEMI-AUTO TRADING BOT")
    print("="*80)

    load_dotenv()
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    from live_bot_mt5_semiauto import LiveBotMT5SemiAuto

    # Create bot
    bot = LiveBotMT5SemiAuto(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        symbol='XAUUSD',
        timeframe=mt5.TIMEFRAME_H1,
        check_interval=3600  # 1 hour
    )

    # Connect to MT5
    if not bot.connect_mt5():
        print("❌ Failed to connect to MT5")
        return False

    print("\n✅ All systems ready!")
    print("\n📊 Bot Configuration:")
    print("   Symbol: XAUUSD")
    print("   Timeframe: H1")
    print("   Check interval: 1 hour")
    print("   Mode: SEMI-AUTOMATIC (requires your confirmation)")
    print("\n⚠️  IMPORTANT:")
    print("   - Bot will send signals to your Telegram")
    print("   - Use /confirm <signal_id> to execute trades")
    print("   - Use /cancel <signal_id> to reject signals")
    print("   - Position management is automatic after confirmation")
    print("\n🎯 Commands available in Telegram:")
    print("   /status - Bot and account status")
    print("   /positions - Show open positions")
    print("   /confirm <id> [lot] - Confirm signal")
    print("   /cancel <id> - Cancel signal")
    print("   /help - Show help")

    input("\n⏸  Press ENTER to start the bot (Ctrl+C to stop)...")

    # Run bot
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Bot stopped by user")
        print("✅ Shutdown complete")

    return True

def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("🤖 SEMI-AUTOMATIC LIVE TRADING BOT - V9 STRATEGY")
    print("="*80)
    print("\nThis bot will:")
    print("  1. Analyze XAUUSD market every hour")
    print("  2. Detect signals using V9 strategy (champion +49.33%)")
    print("  3. Send signals to your Telegram for confirmation")
    print("  4. Execute trades ONLY after your approval")
    print("  5. Manage positions automatically (TP/SL/Trailing)")

    # Step 1: Check .env
    if not check_env_file():
        sys.exit(1)

    # Step 2: Test MT5
    if not test_mt5_connection():
        sys.exit(1)

    # Step 3: Test Telegram
    if not test_telegram_connection():
        sys.exit(1)

    # Step 4: Start bot
    start_bot()

if __name__ == "__main__":
    main()
