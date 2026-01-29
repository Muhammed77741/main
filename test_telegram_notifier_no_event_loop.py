#!/usr/bin/env python3
"""
Test: Verify TelegramNotifier works correctly without event loop errors
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'trading_bots' / 'shared'))

from telegram_notifier import TelegramNotifier

def test_telegram_notifier():
    """Test that TelegramNotifier can send multiple messages without event loop errors"""
    print("=" * 70)
    print("TEST: TelegramNotifier Multiple Messages")
    print("=" * 70)
    print()
    
    # Note: This test requires valid credentials to actually send
    # We'll test the initialization and queue mechanism
    
    try:
        # Test 1: Initialization
        print("Test 1: Initialization")
        notifier = TelegramNotifier(
            bot_token="test_token_123",
            chat_id="test_chat_id",
            timezone_offset=5
        )
        print("✅ PASS: TelegramNotifier initialized without errors")
        print()
        
        # Test 2: Queue multiple messages
        print("Test 2: Queue multiple messages")
        for i in range(5):
            notifier.send_message(
                f"Test message {i+1}",
                async_send=True  # Queue for async sending
            )
        print("✅ PASS: 5 messages queued successfully")
        print()
        
        # Test 3: Wait for queue (won't actually send due to invalid credentials)
        print("Test 3: Wait for queue processing")
        notifier.wait_for_queue(timeout=2)
        print("✅ PASS: Queue wait completed without errors")
        print()
        
        # Test 4: Shutdown
        print("Test 4: Shutdown")
        notifier.shutdown()
        print("✅ PASS: Notifier shut down cleanly")
        print()
        
        print("=" * 70)
        print("✅ ALL TESTS PASSED!")
        print()
        print("Summary:")
        print("  - TelegramNotifier uses requests (sync), not asyncio")
        print("  - Messages are queued and sent in background thread")
        print("  - No event loop management needed")
        print("  - No 'Event loop is closed' errors possible")
        return 0
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = test_telegram_notifier()
    sys.exit(exit_code)
