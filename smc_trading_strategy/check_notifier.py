"""
Check that TelegramNotifier class is properly structured

Usage: python check_notifier.py
"""

from telegram_notifier import TelegramNotifier


def check_telegram_notifier():
    """Check TelegramNotifier class structure"""

    print("\n" + "="*80)
    print("🔍 CHECKING TELEGRAM NOTIFIER CLASS")
    print("="*80)

    # Create test instance
    print("\n1️⃣  Creating test instance...")
    notifier = TelegramNotifier("test_token", "test_chat")
    print("   ✅ Instance created")

    # Check required methods
    print("\n2️⃣  Checking required methods...")
    required_methods = [
        'send_message',
        'send_entry_signal',
        'send_exit_signal',
        'send_partial_close',
        'send_daily_summary',
        'send_startup_message',
        'send_error',
        'test_connection'
    ]

    all_good = True
    for method in required_methods:
        if hasattr(notifier, method):
            print(f"   ✅ {method}")
        else:
            print(f"   ❌ MISSING: {method}")
            all_good = False

    # Check for incorrect 'bot' attribute
    print("\n3️⃣  Checking for incorrect 'bot' attribute...")
    if hasattr(notifier, 'bot'):
        print(f"   ❌ ERROR: TelegramNotifier should NOT have 'bot' attribute!")
        print(f"   This will cause: AttributeError: 'TelegramNotifier' object has no attribute 'bot'")
        all_good = False
    else:
        print(f"   ✅ No 'bot' attribute (correct!)")

    # Check correct attributes
    print("\n4️⃣  Checking correct attributes...")
    required_attrs = ['bot_token', 'chat_id', 'base_url', 'timezone_offset']

    for attr in required_attrs:
        if hasattr(notifier, attr):
            print(f"   ✅ {attr}")
        else:
            print(f"   ⚠️  MISSING: {attr}")

    # Summary
    print("\n" + "="*80)
    if all_good:
        print("✅ TELEGRAM NOTIFIER CLASS IS CORRECT!")
        print("="*80)
        print("\n💡 You can now use it like this:")
        print("""
from telegram_notifier import TelegramNotifier

# Create notifier
notifier = TelegramNotifier(token, chat_id)

# Use methods directly (NO .bot needed!)
notifier.test_connection()           # ✅
notifier.send_message("Hello")       # ✅
notifier.send_entry_signal(data)     # ✅

# NEVER use .bot attribute:
# notifier.bot.send_message(...)     # ❌ WRONG!
""")
    else:
        print("❌ ISSUES FOUND IN TELEGRAM NOTIFIER CLASS!")
        print("="*80)
        print("\n💡 Recommendations:")
        print("   1. Pull latest changes: git pull")
        print("   2. Check telegram_notifier.py is up to date")
        print("   3. Verify no custom modifications broke the class")

    return all_good


if __name__ == "__main__":
    try:
        check_telegram_notifier()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
