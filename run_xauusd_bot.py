#!/usr/bin/env python3
"""
Startup script for Full-Auto Live Trading Bot

⚠️ DANGEROUS: This bot trades WITHOUT your confirmation!

This script:
1. Verifies .env configuration (optional for full-auto)
2. Tests MT5 connection
3. Tests Telegram connection (optional)
4. Shows WARNINGS
5. Requires confirmation
6. Starts the full-automatic trading bot

Usage:
    python run_xauusd_bot.py
    python run_xauusd_bot.py --dry-run  # Test mode (no real trades)
"""

import os
import sys
import argparse
from pathlib import Path

# Add trading_bots to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_bots'))

try:
    from dotenv import load_dotenv
    import MetaTrader5 as mt5
    from shared.telegram_helper import check_telegram_bot_import
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("\n📝 Please install required packages:")
    print("   pip install python-dotenv MetaTrader5 python-telegram-bot")
    sys.exit(1)


def show_warning(dry_run=False):
    """Show big scary warning"""
    print("\n" + "="*80)
    if dry_run:
        print("🧪 " * 40)
        print("="*80)
        print("DRY RUN MODE - TESTING ONLY")
        print("="*80)
        print("🧪 " * 40)
    else:
        print("⚠️ " * 40)
        print("="*80)
        print("FULL AUTOMATIC MODE - EXTREME RISK WARNING")
        print("="*80)
        print("⚠️ " * 40)
    print("="*80)

    if dry_run:
        print("\n🧪 DRY RUN: Bot will:")
        print("   ✅ Analyze market every hour")
        print("   ✅ Find signals using V3 Adaptive strategy")
        print("   ✅ Calculate positions (SL/TP)")
        print("   ✅ Log everything to console")
        print("   ⚠️  NO REAL TRADES will be executed")
    else:
        print("\n🤖 This bot will:")
        print("   ✅ Analyze market every hour")
        print("   ✅ Find signals using V3 Adaptive strategy")
        print("   ⚠️  OPEN POSITIONS WITHOUT YOUR PERMISSION")
        print("   ⚠️  CLOSE POSITIONS WITHOUT YOUR PERMISSION")
        print("   ⚠️  MANAGE YOUR MONEY AUTOMATICALLY")

        print("\n⚠️  RISKS:")
        print("   - Bot can lose ALL your money")
        print("   - No human supervision on entries")
        print("   - Technical errors can cause losses")
        print("   - Market conditions can change suddenly")

        print("\n✅ REQUIREMENTS:")
        print("   - You MUST test on DEMO first (7+ days)")
        print("   - You MUST understand the V3 Adaptive strategy")
        print("   - You MUST monitor your account regularly")
        print("   - You MUST set appropriate risk (1-2% recommended)")
        print("   - You MUST have stop-loss understanding")

    print("\n" + "="*80)
    if not dry_run:
        print("⚠️ " * 40)
    else:
        print("🧪 " * 40)
    print("="*80)


def check_env_file():
    """Check if .env file exists (optional for full-auto)"""
    print("\n" + "="*80)
    print("🔍 CHECKING CONFIGURATION")
    print("="*80)

    if not os.path.exists('.env'):
        print("⚠️  .env file not found")
        print("   Telegram notifications will be DISABLED")
        print("   Bot will run without notifications")
        return False

    load_dotenv()

    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not telegram_token or not telegram_chat_id:
        print("⚠️  Telegram credentials not found in .env")
        print("   Telegram notifications will be DISABLED")
        return False

    print("✅ .env file configured")
    print(f"   Telegram notifications: ENABLED")
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
        print("   2. 'Algo Trading' is enabled in MT5")
        print("   3. You're logged into an account")
        return False

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

    # Check if it's DEMO
    if 'demo' in account_info.server.lower():
        print(f"\n✅ DEMO ACCOUNT - Safe for testing")
    else:
        print(f"\n⚠️⚠️⚠️ REAL ACCOUNT DETECTED ⚠️⚠️⚠️")
        print(f"   You are about to trade with REAL MONEY!")
        print(f"   Are you ABSOLUTELY sure?")

    # Check XAUUSD
    symbol_info = mt5.symbol_info("XAUUSD")
    if symbol_info is None:
        print("\n⚠️  Warning: XAUUSD not found!")
    else:
        print(f"\n✅ XAUUSD is available")
        tick = mt5.symbol_info_tick('XAUUSD')
        if tick:
            print(f"   Bid: {tick.bid:.2f}")
            print(f"   Ask: {tick.ask:.2f}")

    mt5.shutdown()
    return True


def test_telegram_connection():
    """Test Telegram connection (optional)"""
    print("\n" + "="*80)
    print("📱 TESTING TELEGRAM CONNECTION")
    print("="*80)

    if not os.path.exists('.env'):
        print("⚠️  .env not found - Telegram DISABLED")
        return False

    load_dotenv()
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not telegram_token or not telegram_chat_id:
        print("⚠️  Telegram credentials not found - DISABLED")
        return False

    try:
        import asyncio
        
        success, Bot, error_msg = check_telegram_bot_import()
        if not success:
            print(error_msg)
            return False

        async def test_bot():
            bot = Bot(token=telegram_token)
            me = await bot.get_me()
            print(f"✅ Telegram bot connected: @{me.username}")
            
            message = "⚠️ <b>FULL-AUTO BOT TEST</b>\n\n"
            message += "Testing Telegram notifications...\n"
            message += "Bot is ready to start!"
            
            await bot.send_message(chat_id=telegram_chat_id, text=message, parse_mode='HTML')
            print("✅ Test message sent! Check your Telegram.")
            return True

        return asyncio.run(test_bot())

    except Exception as e:
        print(f"❌ Error testing Telegram: {e}")
        return False


def get_configuration(dry_run=False, risk=None, max_positions=None, no_confirm=False):
    """Get configuration from user or command line args"""
    print("\n" + "="*80)
    print("⚙️  CONFIGURATION")
    print("="*80)

    if dry_run:
        print("\n🧪 DRY RUN MODE: Using safe defaults")
        return {
            'risk_percent': 2.0,
            'max_positions': 1,
            'check_interval': 3600,
            'dry_run': True
        }

    # If command line args provided, use them
    if no_confirm and risk is not None and max_positions is not None:
        print(f"\n⚙️  Using command line configuration:")
        print(f"   Risk: {risk}%")
        print(f"   Max positions: {max_positions}")
        print(f"   Check interval: 1 hour")
        return {
            'risk_percent': risk,
            'max_positions': max_positions,
            'check_interval': 3600,
            'dry_run': False
        }

    print("\nDefault settings:")
    print("  - Risk per trade: 2.0%")
    print("  - Max positions: 9")
    print("  - Check interval: 1 hour")

    use_defaults = input("\nUse default settings? (y/n): ").lower()

    if use_defaults == 'y':
        return {
            'risk_percent': 2.0,
            'max_positions': 9,
            'check_interval': 3600,
            'dry_run': False
        }

    print("\n📝 Custom configuration:")

    risk_input = input("Risk per trade (0.5-5.0%): ")
    try:
        risk = float(risk_input)
        if risk < 0.5 or risk > 5.0:
            print("⚠️  Risk must be between 0.5% and 5.0%. Using 2.0%")
            risk = 2.0
    except:
        print("⚠️  Invalid input. Using 2.0%")
        risk = 2.0

    max_pos = input("Max simultaneous positions (1-9): ")
    try:
        max_pos = int(max_pos)
        if max_pos < 1 or max_pos > 9:
            print("⚠️  Max positions must be between 1 and 9. Using 9")
            max_pos = 9
    except:
        print("⚠️  Invalid input. Using 9")
        max_pos = 9

    return {
        'risk_percent': risk,
        'max_positions': max_pos,
        'check_interval': 3600,
        'dry_run': False
    }


def final_confirmation(dry_run=False, no_confirm=False):
    """Get final confirmation from user"""
    if dry_run:
        print("\n" + "="*80)
        print("🧪 DRY RUN - NO CONFIRMATION NEEDED")
        print("="*80)
        print("\nDry run will simulate trading without real orders.")
        return True

    if no_confirm:
        print("\n" + "="*80)
        print("⚠️  NO-CONFIRM MODE - SKIPPING CONFIRMATION")
        print("="*80)
        print("\n🚨 Bot will start IMMEDIATELY without confirmation!")
        print("   Using this mode means you accept ALL risks.")
        print("   Recommended ONLY for automated deployment on DEMO accounts.")
        print("\n⏳ Starting in 3 seconds...")
        import time
        time.sleep(3)
        return True

    print("\n" + "="*80)
    print("⚠️  FINAL CONFIRMATION")
    print("="*80)

    print("\n✅ I understand that:")
    print("   1. Bot will trade WITHOUT my confirmation")
    print("   2. Bot can lose money")
    print("   3. I tested on DEMO account for 7+ days")
    print("   4. I will monitor my account regularly")
    print("   5. I use appropriate risk management")
    print("   6. I accept all responsibility")

    print("\n" + "="*80)
    confirm1 = input("Type 'I UNDERSTAND THE RISKS' to continue: ")

    if confirm1 != "I UNDERSTAND THE RISKS":
        print("\n❌ Confirmation failed. Exiting.")
        return False

    confirm2 = input("\nType 'START BOT' to begin trading: ")

    if confirm2 != "START BOT":
        print("\n❌ Confirmation failed. Exiting.")
        return False

    return True


def start_bot(config):
    """Start the full-automatic trading bot"""
    print("\n" + "="*80)
    if config['dry_run']:
        print("🧪 STARTING DRY RUN BOT (TEST MODE)")
    else:
        print("🚀 STARTING FULL-AUTO TRADING BOT")
    print("="*80)

    load_dotenv()
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    try:
        from xauusd_bot.live_bot_mt5_fullauto import LiveBotMT5FullAuto
    except ImportError:
        print("❌ Failed to import LiveBotMT5FullAuto")
        print("   Make sure live_bot_mt5_fullauto.py exists in trading_bots/xauusd_bot/")
        return False

    # Create bot
    bot = LiveBotMT5FullAuto(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        symbol='XAUUSD',
        timeframe=mt5.TIMEFRAME_H1,
        check_interval=config['check_interval'],
        risk_percent=config['risk_percent'],
        max_positions=config['max_positions'],
        dry_run=config['dry_run']
    )

    # Connect to MT5
    if not bot.connect_mt5():
        print("❌ Failed to connect to MT5")
        return False

    print("\n✅ All systems ready!")
    print("\n📊 Bot Configuration:")
    print(f"   Symbol: XAUUSD")
    print(f"   Timeframe: H1")
    print(f"   Risk per trade: {config['risk_percent']}%")
    print(f"   Max positions: {config['max_positions']}")
    print(f"   Check interval: {config['check_interval']/3600:.1f}h")
    print(f"   Mode: {'DRY RUN (TEST)' if config['dry_run'] else 'LIVE TRADING'}")
    
    if config['dry_run']:
        print("\n🧪 DRY RUN: No real trades will be executed")
    else:
        print("\n⚠️  Bot will now trade AUTOMATICALLY")
    print("⚠️  Press Ctrl+C to stop")

    input("\n⏸  Press ENTER to start the bot...")

    # Run bot
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Bot stopped by user")
        print("✅ Shutdown complete")
    except Exception as e:
        print(f"\n\n❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Full-Auto Trading Bot')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run in test mode (no real trades)')
    parser.add_argument('--no-confirm', action='store_true',
                       help='Skip confirmation prompts (DANGEROUS! Use only for automated deployment)')
    parser.add_argument('--risk', type=float, default=2.0,
                       help='Risk per trade (0.5-5.0%%, default: 2.0)')
    parser.add_argument('--max-positions', type=int, default=9,
                       help='Max simultaneous positions (1-9, default: 9)')
    args = parser.parse_args()

    # Validate args
    if args.risk < 0.5 or args.risk > 5.0:
        print(f"❌ Error: Risk must be between 0.5%% and 5.0%%. Got: {args.risk}%%")
        sys.exit(1)
    
    if args.max_positions < 1 or args.max_positions > 9:
        print(f"❌ Error: Max positions must be between 1 and 9. Got: {args.max_positions}")
        sys.exit(1)

    # Show warning
    show_warning(dry_run=args.dry_run)

    # Step 1: Check .env (optional)
    check_env_file()

    # Step 2: Test MT5
    if not test_mt5_connection():
        sys.exit(1)

    # Step 3: Test Telegram (optional)
    test_telegram_connection()

    # Step 4: Get configuration
    config = get_configuration(
        dry_run=args.dry_run,
        risk=args.risk,
        max_positions=args.max_positions,
        no_confirm=args.no_confirm
    )

    # Step 5: Final confirmation
    if not final_confirmation(dry_run=args.dry_run, no_confirm=args.no_confirm):
        sys.exit(0)

    # Step 6: Start bot
    start_bot(config)


if __name__ == "__main__":
    main()
