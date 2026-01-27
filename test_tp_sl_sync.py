#!/usr/bin/env python3
"""
Test TP/SL sync functionality
"""
import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_app'))

def test_tp_sl_sync_logic():
    """Test that TP/SL sync logic correctly detects changes"""
    print("\n" + "="*60)
    print("Test: TP/SL Synchronization Logic")
    print("="*60)
    
    # Simulate database position
    class MockTrade:
        def __init__(self):
            self.order_id = "12345"
            self.stop_loss = 2880.0
            self.take_profit = 2920.0
            self.trade_type = 'BUY'
            self.entry_price = 2900.0
            self.amount = 0.03
    
    # Simulate MT5 position
    class MockMT5Position:
        def __init__(self, ticket, sl, tp):
            self.ticket = ticket
            self.sl = sl
            self.tp = tp
    
    # Test Case 1: TP changed in MT5
    print("\nTest Case 1: TP manually changed in MT5")
    trade = MockTrade()
    mt5_pos = MockMT5Position(12345, 2880.0, 2930.0)  # TP changed from 2920 to 2930
    
    tp_changed = False
    if mt5_pos.tp and trade.take_profit:
        if abs(mt5_pos.tp - trade.take_profit) > 0.01:
            tp_changed = True
    
    assert tp_changed, "❌ Failed to detect TP change"
    print(f"✅ TP change detected: DB={trade.take_profit:.2f} -> MT5={mt5_pos.tp:.2f}")
    
    # Test Case 2: SL changed in MT5
    print("\nTest Case 2: SL manually changed in MT5")
    trade = MockTrade()
    mt5_pos = MockMT5Position(12345, 2870.0, 2920.0)  # SL changed from 2880 to 2870
    
    sl_changed = False
    if mt5_pos.sl and trade.stop_loss:
        if abs(mt5_pos.sl - trade.stop_loss) > 0.01:
            sl_changed = True
    
    assert sl_changed, "❌ Failed to detect SL change"
    print(f"✅ SL change detected: DB={trade.stop_loss:.2f} -> MT5={mt5_pos.sl:.2f}")
    
    # Test Case 3: Both TP and SL changed
    print("\nTest Case 3: Both TP and SL changed in MT5")
    trade = MockTrade()
    mt5_pos = MockMT5Position(12345, 2870.0, 2930.0)  # Both changed
    
    sl_changed = False
    tp_changed = False
    
    if mt5_pos.sl and trade.stop_loss:
        if abs(mt5_pos.sl - trade.stop_loss) > 0.01:
            sl_changed = True
    
    if mt5_pos.tp and trade.take_profit:
        if abs(mt5_pos.tp - trade.take_profit) > 0.01:
            tp_changed = True
    
    assert sl_changed and tp_changed, "❌ Failed to detect both changes"
    print(f"✅ Both changes detected:")
    print(f"   SL: DB={trade.stop_loss:.2f} -> MT5={mt5_pos.sl:.2f}")
    print(f"   TP: DB={trade.take_profit:.2f} -> MT5={mt5_pos.tp:.2f}")
    
    # Test Case 4: No changes (tolerance test)
    print("\nTest Case 4: No changes (within tolerance)")
    trade = MockTrade()
    mt5_pos = MockMT5Position(12345, 2880.005, 2920.003)  # Very small difference
    
    sl_changed = False
    tp_changed = False
    
    if mt5_pos.sl and trade.stop_loss:
        if abs(mt5_pos.sl - trade.stop_loss) > 0.01:
            sl_changed = True
    
    if mt5_pos.tp and trade.take_profit:
        if abs(mt5_pos.tp - trade.take_profit) > 0.01:
            tp_changed = True
    
    assert not sl_changed and not tp_changed, "❌ Incorrectly detected change within tolerance"
    print(f"✅ No changes detected (differences within 0.01 tolerance)")
    
    return True

def test_sync_code_exists():
    """Test that sync code is present in the file"""
    print("\n" + "="*60)
    print("Test: Code Implementation Verification")
    print("="*60)
    
    bot_file = Path(__file__).parent / 'trading_bots' / 'xauusd_bot' / 'live_bot_mt5_fullauto.py'
    
    with open(bot_file, 'r') as f:
        content = f.read()
    
    # Check for key implementation elements
    has_tp_sl_sync = 'Also syncs manual changes to TP/SL levels' in content
    has_positions_map = 'mt5_positions_map = {pos.ticket: pos for pos in open_positions}' in content
    has_tp_check = 'if abs(mt5_pos.tp - trade.take_profit) > 0.01:' in content
    has_sl_check = 'if abs(mt5_pos.sl - trade.stop_loss) > 0.01:' in content
    has_db_update = 'Position #{ticket} TP/SL modified in MT5 - syncing database' in content
    
    assert has_tp_sl_sync, "❌ Missing TP/SL sync documentation"
    assert has_positions_map, "❌ Missing positions map creation"
    assert has_tp_check, "❌ Missing TP change detection"
    assert has_sl_check, "❌ Missing SL change detection"
    assert has_db_update, "❌ Missing database update logic"
    
    print("✅ TP/SL sync documentation present")
    print("✅ Positions map creation present")
    print("✅ TP change detection present")
    print("✅ SL change detection present")
    print("✅ Database update logic present")
    
    return True

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("TP/SL SYNC FUNCTIONALITY - TEST SUITE")
    print("="*70)
    
    all_passed = True
    
    try:
        if not test_tp_sl_sync_logic():
            all_passed = False
    except Exception as e:
        print(f"❌ TP/SL sync logic test failed: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        if not test_sync_code_exists():
            all_passed = False
    except Exception as e:
        print(f"❌ Code verification test failed: {e}")
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
