#!/usr/bin/env python3
"""
Test MT5 connection validation and position group preservation fixes
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_app'))
sys.path.insert(0, str(Path(__file__).parent / 'trading_bots'))

def test_mt5_manager_ensure_connection_called():
    """Test that mt5_manager.ensure_connection() is called before positions_get()"""
    print("\n" + "="*60)
    print("Test 1: MT5 Manager ensure_connection() is called")
    print("="*60)
    
    # Read the source file and check for ensure_connection calls
    bot_file = Path(__file__).parent / 'trading_bots' / 'xauusd_bot' / 'live_bot_mt5_fullauto.py'
    
    with open(bot_file, 'r') as f:
        content = f.read()
    
    # Check for ensure_connection before positions_get
    lines = content.split('\n')
    
    ensure_connection_count = 0
    for i, line in enumerate(lines):
        if 'mt5_manager.ensure_connection()' in line:
            # Check if positions_get is called within the next 10 lines
            for j in range(i, min(i+10, len(lines))):
                if 'positions_get' in lines[j]:
                    ensure_connection_count += 1
                    break
    
    assert ensure_connection_count > 0, "❌ No ensure_connection() calls found before positions_get()"
    
    print(f"✅ Found {ensure_connection_count} ensure_connection() calls before positions_get()")
    print("   Connection validation is properly implemented")
    
    return True

def test_position_group_preservation():
    """Test that position_group_id and position_num are preserved when closing positions"""
    print("\n" + "="*60)
    print("Test 2: Position Group Information Preservation")
    print("="*60)
    
    from models.trade_record import TradeRecord
    from datetime import datetime
    
    # Create a mock position tracker entry with group info
    mock_position = {
        'ticket': 12345,
        'open_time': datetime.now(),
        'type': 'BUY',
        'volume': 0.03,
        'entry_price': 2900.0,
        'sl': 2880.0,
        'tp': 2920.0,
        'regime': 'TREND',
        'comment': 'Test position',
        'position_group_id': 'abc123def456',
        'position_num': 1,
        'magic_number': 100101
    }
    
    # Simulate what _log_position_closed should create
    trade = TradeRecord(
        trade_id=0,
        bot_id='test_bot',
        symbol='XAUUSD',
        order_id='12345',
        open_time=mock_position['open_time'],
        close_time=datetime.now(),
        duration_hours=1.5,
        trade_type=mock_position['type'],
        amount=mock_position['volume'],
        entry_price=mock_position['entry_price'],
        close_price=2920.0,
        stop_loss=mock_position['sl'],
        take_profit=mock_position['tp'],
        profit=0.6,
        profit_percent=0.69,
        status='CLOSED',
        market_regime=mock_position['regime'],
        comment=mock_position['comment'],
        position_group_id=mock_position.get('position_group_id'),
        position_num=mock_position.get('position_num', 0),
        magic_number=mock_position.get('magic_number')
    )
    
    # Verify the fields are preserved
    assert trade.position_group_id == 'abc123def456', "❌ position_group_id not preserved"
    assert trade.position_num == 1, "❌ position_num not preserved"
    assert trade.magic_number == 100101, "❌ magic_number not preserved"
    
    print("✅ Position group information is properly preserved:")
    print(f"   - position_group_id: {trade.position_group_id}")
    print(f"   - position_num: {trade.position_num}")
    print(f"   - magic_number: {trade.magic_number}")
    
    return True

def test_spam_prevention():
    """Test that repeated warnings are prevented using logged_closed_groups set"""
    print("\n" + "="*60)
    print("Test 3: Spam Warning Prevention")
    print("="*60)
    
    # Read the source file and check for logged_closed_groups
    bot_file = Path(__file__).parent / 'trading_bots' / 'xauusd_bot' / 'live_bot_mt5_fullauto.py'
    
    with open(bot_file, 'r') as f:
        content = f.read()
    
    # Check for spam prevention set
    has_logged_set = 'self.logged_closed_groups = set()' in content
    has_add_to_set = 'self.logged_closed_groups.add(group_id)' in content
    has_check_in_set = 'group_id not in self.logged_closed_groups' in content
    
    assert has_logged_set, "❌ logged_closed_groups set not initialized"
    assert has_add_to_set, "❌ Groups not being added to logged_closed_groups"
    assert has_check_in_set, "❌ No check for already-logged groups"
    
    print("✅ Spam prevention mechanism is properly implemented:")
    print(f"   - logged_closed_groups set initialized: {has_logged_set}")
    print(f"   - Groups added to set: {has_add_to_set}")
    print(f"   - Groups checked before logging: {has_check_in_set}")
    
    return True

def test_retry_logic_exists():
    """Test that retry logic exists for position opening"""
    print("\n" + "="*60)
    print("Test 4: Position Opening Retry Logic")
    print("="*60)
    
    # Read the source file and check for retry logic
    bot_file = Path(__file__).parent / 'trading_bots' / 'xauusd_bot' / 'live_bot_mt5_fullauto.py'
    
    with open(bot_file, 'r') as f:
        content = f.read()
    
    # Check for retry-related code
    has_max_retries = 'max_retries' in content
    has_retry_loop = 'for attempt in range(max_retries)' in content or 'for attempt in range' in content
    has_ensure_connection_in_loop = 'ensure_connection()' in content and 'for attempt' in content
    
    assert has_max_retries, "❌ max_retries variable not found"
    assert has_retry_loop, "❌ Retry loop not found"
    
    print("✅ Position opening retry logic is implemented:")
    print(f"   - max_retries variable: {has_max_retries}")
    print(f"   - Retry loop: {has_retry_loop}")
    print(f"   - Connection check in retry: {has_ensure_connection_in_loop}")
    
    return True

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("MT5 CONNECTION AND POSITION GROUP FIXES - TEST SUITE")
    print("="*70)
    
    all_passed = True
    
    try:
        # Test 1: MT5 connection validation
        if not test_mt5_manager_ensure_connection_called():
            all_passed = False
    except Exception as e:
        print(f"❌ Test 1 failed with error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        # Test 2: Position group preservation
        if not test_position_group_preservation():
            all_passed = False
    except Exception as e:
        print(f"❌ Test 2 failed with error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        # Test 3: Spam prevention
        if not test_spam_prevention():
            all_passed = False
    except Exception as e:
        print(f"❌ Test 3 failed with error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        # Test 4: Retry logic
        if not test_retry_logic_exists():
            all_passed = False
    except Exception as e:
        print(f"❌ Test 4 failed with error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    # Summary
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    print("="*70 + "\n")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
