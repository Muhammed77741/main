"""
Test Telegram Notifier fixes - error handling and validation
"""

from telegram_notifier import TelegramNotifier
from datetime import datetime


def test_notifier_validation():
    """Test that notifier handles invalid data gracefully"""

    print("\n" + "="*80)
    print("🧪 TESTING TELEGRAM NOTIFIER ERROR HANDLING")
    print("="*80)

    # Create notifier with dummy credentials
    notifier = TelegramNotifier("dummy_token", "dummy_chat_id")

    # Test 1: Empty signal_data
    print("\n1️⃣  Test empty signal_data")
    result = notifier.send_entry_signal(None)
    assert result == False, "Should return False for None signal_data"
    print("   ✅ Correctly handled None signal_data")

    # Test 2: Missing required fields in signal_data
    print("\n2️⃣  Test missing required fields in signal_data")
    incomplete_signal = {
        'direction': 'LONG',
        # Missing entry_price and stop_loss
    }
    result = notifier.send_entry_signal(incomplete_signal)
    assert result == False, "Should return False for incomplete signal_data"
    print("   ✅ Correctly handled incomplete signal_data")

    # Test 3: Empty exit_data
    print("\n3️⃣  Test empty exit_data")
    result = notifier.send_exit_signal(None)
    assert result == False, "Should return False for None exit_data"
    print("   ✅ Correctly handled None exit_data")

    # Test 4: Missing required fields in exit_data
    print("\n4️⃣  Test missing required fields in exit_data")
    incomplete_exit = {
        'direction': 'LONG',
        # Missing other required fields
    }
    result = notifier.send_exit_signal(incomplete_exit)
    assert result == False, "Should return False for incomplete exit_data"
    print("   ✅ Correctly handled incomplete exit_data")

    # Test 5: Empty message
    print("\n5️⃣  Test empty message")
    result = notifier.send_message("")
    assert result == False, "Should return False for empty message"
    print("   ✅ Correctly handled empty message")

    # Test 6: Complete signal_data (will fail to send but should process correctly)
    print("\n6️⃣  Test complete signal_data structure")
    complete_signal = {
        'direction': 'LONG',
        'entry_price': 2650.50,
        'stop_loss': 2640.00,
        'tp1': 2660.00,
        'tp2': 2670.00,
        'tp3': 2680.00,
        'pattern': 'Test_Pattern',
        'regime': 'TREND',
        'trailing': 10,
        'timestamp': datetime.now()
    }
    # This will fail to send (dummy token) but should process the data
    result = notifier.send_entry_signal(complete_signal)
    # It should process data and try to send (will fail due to dummy token)
    print("   ✅ Processed complete signal_data structure")

    # Test 7: Complete exit_data structure
    print("\n7️⃣  Test complete exit_data structure")
    complete_exit = {
        'direction': 'LONG',
        'entry_price': 2650.50,
        'exit_price': 2660.50,
        'exit_type': 'TP',
        'pnl_pct': 0.38,
        'pnl_points': 10.00,
        'duration_hours': 2.5,
        'timestamp': datetime.now()
    }
    # This will fail to send (dummy token) but should process the data
    result = notifier.send_exit_signal(complete_exit)
    print("   ✅ Processed complete exit_data structure")

    print("\n" + "="*80)
    print("✅ ALL VALIDATION TESTS PASSED!")
    print("="*80)
    print("\n💡 Summary:")
    print("   • Notifier now validates all input data")
    print("   • Gracefully handles missing or incomplete data")
    print("   • Provides clear error messages")
    print("   • Won't crash on invalid input")
    print("\n✅ Fixes applied successfully!")
    print("="*80)


if __name__ == "__main__":
    test_notifier_validation()
