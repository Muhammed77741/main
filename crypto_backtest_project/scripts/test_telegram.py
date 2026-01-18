"""
Test Telegram bot connection and send test message
"""

import os
from dotenv import load_dotenv
from telegram_notifier import TelegramNotifier


def main():
    print("\n" + "="*80)
    print("🧪 TELEGRAM BOT CONNECTION TEST")
    print("="*80)

    # Load .env file
    load_dotenv()

    # Get credentials
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    print("\n📋 Configuration:")
    print(f"   Token: {'✅ Found' if telegram_token else '❌ Not found'}")
    print(f"   Chat ID: {'✅ Found' if telegram_chat_id else '❌ Not found'}")

    if not telegram_token or not telegram_chat_id:
        print("\n❌ ERROR: Missing credentials in .env file!")
        print("\n📝 Create a .env file with:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token")
        print("   TELEGRAM_CHAT_ID=your_chat_id")
        print("\n💡 See PAPER_TRADING_SETUP.md for detailed instructions")
        return

    # Initialize notifier
    print("\n🔌 Connecting to Telegram...")
    notifier = TelegramNotifier(telegram_token, telegram_chat_id)

    # Test connection
    if not notifier.test_connection():
        print("\n❌ Connection test failed!")
        print("\n🔧 Check:")
        print("   1. Bot token is correct")
        print("   2. You started the bot in Telegram (/start)")
        print("   3. Internet connection is working")
        return

    # Send test message
    print("\n📤 Sending test message...")

    test_message = """
🧪 <b>ТЕСТ ПОДКЛЮЧЕНИЯ</b>

✅ Telegram бот успешно подключен!

📊 <b>Информация:</b>
  • Бот готов к работе
  • Уведомления будут приходить в этот чат
  • Paper trading бот настроен правильно

🚀 <b>Следующий шаг:</b>
Запустите paper trading бот:
<code>python paper_trading.py</code>

⚡ Готово к торговле!
"""

    if notifier.send_message(test_message):
        print("✅ Test message sent successfully!")
        print("\n📱 Check your Telegram - you should see the test message")
        print("\n✅ Everything is working! You can now run:")
        print("   python paper_trading.py")
    else:
        print("❌ Failed to send test message")
        print("\n🔧 Possible issues:")
        print("   1. Bot is not started in Telegram (send /start to your bot)")
        print("   2. Chat ID is incorrect")
        print("   3. Bot doesn't have permission to send messages")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
