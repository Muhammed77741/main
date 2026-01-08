#!/usr/bin/env python3
"""
Startup script for Crypto Full-Auto Live Trading Bot (BTC/ETH)

⚠️ DANGEROUS: This bot trades WITHOUT your confirmation!

This script:
1. Verifies .env configuration (Binance API keys required)
2. Tests Binance connection
3. Tests Telegram connection (optional)
4. Shows WARNINGS
5. Requires confirmation
6. Starts the full-automatic trading bot

Usage:
    python run_crypto_bot.py BTC  # Trade BTC/USDT
    python run_crypto_bot.py ETH  # Trade ETH/USDT
    python run_crypto_bot.py BTC --dry-run  # Test mode (no real trades)
"""

import os
import sys
import argparse
from pathlib import Path

# Add trading_bots to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_bots'))

try:
    from dotenv import load_dotenv
    import ccxt
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("\n📝 Please install required packages:")
    print("   pip install python-dotenv ccxt python-telegram-bot")
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
    """Check if .env file exists and has Binance API keys"""
    print("\n" + "="*80)
    print("🔍 CHECKING CONFIGURATION")
    print("="*80)

    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("   Binance API keys are REQUIRED for crypto trading!")
        print("\n📝 Create .env file with:")
        print("   BINANCE_API_KEY=your_api_key")
        print("   BINANCE_API_SECRET=your_api_secret")
        print("   TELEGRAM_BOT_TOKEN=your_token (optional)")
        print("   TELEGRAM_CHAT_ID=your_chat_id (optional)")
        return False

    load_dotenv()

    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not api_key or not api_secret:
        print("❌ Binance API credentials not found in .env")
        print("   API keys are REQUIRED for crypto trading!")
        return False

    print("✅ .env file configured")
    print(f"   Binance API: ENABLED")

    if telegram_token and telegram_chat_id:
        print(f"   Telegram notifications: ENABLED")
    else:
        print(f"   Telegram notifications: DISABLED")

    return True


def test_binance_connection(symbol='BTC'):
    """Test Binance connection"""
    print("\n" + "="*80)
    print("🔗 TESTING BINANCE CONNECTION")
    print("="*80)

    load_dotenv()
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    use_testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'

    if not api_key or not api_secret:
        print("❌ Binance API credentials not found!")
        return False

    try:
        # Initialize exchange
        if use_testnet:
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'defaultType': 'future'},
                'urls': {
                    'api': {
                        'public': 'https://testnet.binancefuture.com/fapi/v1',
                        'private': 'https://testnet.binancefuture.com/fapi/v1',
                    }
                }
            })
            print("✅ Using TESTNET - Safe for testing")
        else:
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'options': {'defaultType': 'future'}
            })
            print("⚠️⚠️⚠️ USING MAINNET - REAL MONEY ⚠️⚠️⚠️")

        # Load markets
        exchange.load_markets()
        print("✅ Connected to Binance successfully!")

        # Get balance
        balance = exchange.fetch_balance()
        usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0

        print(f"\n💰 Account Information:")
        print(f"   USDT Balance: ${usdt_balance:.2f}")

        # Check symbol
        trading_symbol = f"{symbol}/USDT"
        if trading_symbol in exchange.markets:
            ticker = exchange.fetch_ticker(trading_symbol)
            print(f"\n✅ {trading_symbol} is available")
            print(f"   Last Price: ${ticker['last']:.2f}")
            print(f"   24h Change: {ticker['percentage']:.2f}%")
        else:
            print(f"\n❌ {trading_symbol} not found!")
            return False

        return True

    except Exception as e:
        print(f"❌ Failed to connect to Binance: {e}")
        print("\n📝 Please ensure:")
        print("   1. API keys are correct")
        print("   2. API has Futures trading permission")
        print("   3. Internet connection is stable")
        return False


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
        from telegram import Bot
        import asyncio

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
    print("  - Max positions: 3")
    print("  - Check interval: 1 hour")

    use_defaults = input("\nUse default settings? (y/n): ").lower()

    if use_defaults == 'y':
        return {
            'risk_percent': 2.0,
            'max_positions': 3,
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

    max_pos = input("Max simultaneous positions (1-5): ")
    try:
        max_pos = int(max_pos)
        if max_pos < 1 or max_pos > 5:
            print("⚠️  Max positions must be between 1 and 5. Using 3")
            max_pos = 3
    except:
        print("⚠️  Invalid input. Using 3")
        max_pos = 3

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


def start_bot(config, symbol='BTC'):
    """Start the full-automatic crypto trading bot"""
    print("\n" + "="*80)
    if config['dry_run']:
        print(f"🧪 STARTING {symbol} DRY RUN BOT (TEST MODE)")
    else:
        print(f"🚀 STARTING {symbol} FULL-AUTO TRADING BOT")
    print("="*80)

    load_dotenv()
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    use_testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'

    try:
        from crypto_bot.live_bot_binance_fullauto import LiveBotBinanceFullAuto
    except ImportError:
        print("❌ Failed to import LiveBotBinanceFullAuto")
        print("   Make sure live_bot_binance_fullauto.py exists in trading_bots/crypto_bot/")
        return False

    # Create bot
    bot = LiveBotBinanceFullAuto(
        api_key=api_key,
        api_secret=api_secret,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        symbol=symbol,
        timeframe='1h',
        check_interval=config['check_interval'],
        risk_percent=config['risk_percent'],
        max_positions=config['max_positions'],
        dry_run=config['dry_run'],
        testnet=use_testnet
    )

    # Connect to Binance
    if not bot.connect_exchange():
        print("❌ Failed to connect to Binance")
        return False

    print("\n✅ All systems ready!")
    print("\n📊 Bot Configuration:")
    print(f"   Symbol: {symbol}/USDT")
    print(f"   Exchange: Binance Futures {'(TESTNET)' if use_testnet else '(MAINNET)'}")
    print(f"   Timeframe: 1H")
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
    parser = argparse.ArgumentParser(description='Crypto Full-Auto Trading Bot')
    parser.add_argument('symbol', choices=['BTC', 'ETH'],
                       help='Cryptocurrency symbol to trade (BTC or ETH)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run in test mode (no real trades)')
    parser.add_argument('--no-confirm', action='store_true',
                       help='Skip confirmation prompts (DANGEROUS! Use only for automated deployment)')
    parser.add_argument('--risk', type=float, default=2.0,
                       help='Risk per trade (0.5-5.0%%, default: 2.0)')
    parser.add_argument('--max-positions', type=int, default=1,
                       help='Max simultaneous positions (1-5, default: 1 for crypto)')
    args = parser.parse_args()

    # Validate args
    if args.risk < 0.5 or args.risk > 5.0:
        print(f"❌ Error: Risk must be between 0.5%% and 5.0%%. Got: {args.risk}%%")
        sys.exit(1)

    if args.max_positions < 1 or args.max_positions > 5:
        print(f"❌ Error: Max positions must be between 1 and 5. Got: {args.max_positions}")
        sys.exit(1)

    # Show warning
    show_warning(dry_run=args.dry_run)

    # Step 1: Check .env (required for Binance)
    if not check_env_file():
        sys.exit(1)

    # Step 2: Test Binance connection
    if not test_binance_connection(symbol=args.symbol):
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
    start_bot(config, symbol=args.symbol)


if __name__ == "__main__":
    main()
