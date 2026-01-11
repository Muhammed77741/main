#!/usr/bin/env python3
"""
Simple test script to verify Telegram bot setup.

Usage:
    python test_telegram_setup.py
    
This script will:
1. Check if python-telegram-bot is correctly installed
2. Test connection to Telegram
3. Send a test message

You can also provide token and chat_id as command-line arguments:
    python test_telegram_setup.py YOUR_BOT_TOKEN YOUR_CHAT_ID
"""

import sys
import os
import asyncio

# Add trading_bots to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trading_bots'))

from shared.telegram_helper import check_telegram_bot_import


def get_credentials():
    """Get Telegram credentials from args or .env file"""
    if len(sys.argv) >= 3:
        # From command line arguments
        return sys.argv[1], sys.argv[2]
    
    # Try to load from .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        return token, chat_id
    except ImportError:
        return None, None


async def test_telegram(bot_token, chat_id):
    """Test Telegram bot connection and send message"""
    print("📱 Testing Telegram Bot Setup\n")
    print("=" * 50)
    
    # Step 1: Check if package is installed correctly
    print("\n1️⃣ Checking python-telegram-bot installation...")
    success, Bot, error_msg = check_telegram_bot_import()
    
    if not success:
        print("❌ FAILED\n")
        print(error_msg)
        return False
    
    print("✅ PASSED - python-telegram-bot is installed correctly")
    
    # Step 2: Test bot credentials
    print("\n2️⃣ Testing bot credentials...")
    if not bot_token or not chat_id:
        print("❌ FAILED\n")
        print("Bot token or chat ID not provided.\n")
        print("Usage:")
        print("  python test_telegram_setup.py YOUR_BOT_TOKEN YOUR_CHAT_ID")
        print("\nOr create a .env file with:")
        print("  TELEGRAM_BOT_TOKEN=your_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        return False
    
    print(f"✅ Token: {bot_token[:10]}...{bot_token[-5:]}")
    print(f"✅ Chat ID: {chat_id}")
    
    # Step 3: Test connection
    print("\n3️⃣ Testing connection to Telegram...")
    try:
        bot = Bot(token=bot_token)
        me = await bot.get_me()
        print(f"✅ PASSED - Connected as @{me.username}")
        print(f"   Bot name: {me.first_name}")
        print(f"   Bot ID: {me.id}")
    except Exception as e:
        print(f"❌ FAILED\n")
        print(f"Error: {e}\n")
        print("Common issues:")
        print("  - Invalid bot token")
        print("  - No internet connection")
        print("  - Firewall blocking connection")
        return False
    
    # Step 4: Send test message
    print("\n4️⃣ Sending test message...")
    try:
        message = """
🎉 <b>Telegram Setup Test</b>

✅ Your Telegram bot is configured correctly!

<b>What's working:</b>
• python-telegram-bot is installed
• Bot token is valid
• Connection to Telegram API is working
• Messages can be sent to your chat

<b>You're all set!</b> 🚀

Your trading bots can now send notifications to this chat.
"""
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        print("✅ PASSED - Test message sent successfully!")
        print("\n📱 Check your Telegram - you should see the test message!")
    except Exception as e:
        print(f"❌ FAILED\n")
        print(f"Error: {e}\n")
        print("Common issues:")
        print("  - Invalid chat ID")
        print("  - Bot not started (send /start to your bot first)")
        print("  - Bot blocked by user")
        print("  - Bot not added as admin (for channels)")
        return False
    
    # All tests passed!
    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED!")
    print("\nYour Telegram setup is working correctly.")
    print("You can now use Telegram notifications in your bots.")
    print("=" * 50)
    return True


def main():
    """Main function"""
    print("🤖 Telegram Bot Setup Verification Tool")
    print("Version 1.0\n")
    
    # Get credentials
    bot_token, chat_id = get_credentials()
    
    # Run async test
    try:
        result = asyncio.run(test_telegram(bot_token, chat_id))
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
