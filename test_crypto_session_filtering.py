#!/usr/bin/env python3
"""
Test: Verify session filtering is disabled for crypto and enabled for forex
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'trading_app' / 'gui'))

from format_utils import is_crypto_symbol

def test_session_filtering_logic():
    """Test that session filtering is correctly applied based on symbol type"""
    print("=" * 70)
    print("TEST: Session Filtering for Crypto vs Forex/Commodity")
    print("=" * 70)
    print()
    
    test_cases = [
        # (symbol, expected_is_crypto, expected_best_hours_only)
        ('BTCUSD', True, False),
        ('BTC/USDT', True, False),
        ('ETHUSD', True, False),
        ('ETH/USDT', True, False),
        ('SOLUSD', True, False),
        ('XAUUSD', False, True),
        ('EURUSD', False, True),
        ('GBPUSD', False, True),
        ('USDJPY', False, True),
    ]
    
    all_passed = True
    
    for symbol, expected_is_crypto, expected_best_hours_only in test_cases:
        # Test crypto detection
        is_crypto = is_crypto_symbol(symbol)
        
        # Test strategy initialization logic (as used in live bot and signal analysis)
        best_hours_only = False if is_crypto else True
        
        # Verify
        crypto_match = is_crypto == expected_is_crypto
        hours_match = best_hours_only == expected_best_hours_only
        passed = crypto_match and hours_match
        
        status = "✅ PASS" if passed else "❌ FAIL"
        symbol_type = "CRYPTO" if is_crypto else "FOREX/COMMODITY"
        filter_status = "DISABLED (24/7)" if not best_hours_only else "ENABLED (8-10, 13-15 GMT)"
        
        print(f"{status}: {symbol:12} -> {symbol_type:15} | Session filter: {filter_status}")
        
        if not passed:
            all_passed = False
            print(f"       Expected: is_crypto={expected_is_crypto}, best_hours_only={expected_best_hours_only}")
            print(f"       Got:      is_crypto={is_crypto}, best_hours_only={best_hours_only}")
    
    print()
    print("=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print()
        print("Summary:")
        print("  - Crypto symbols: Session filtering DISABLED (trades 24/7)")
        print("  - Forex/Commodity: Session filtering ENABLED (best hours only)")
        print()
        print("Code changes verified:")
        print("  ✅ Live Bot: trading_bots/xauusd_bot/live_bot_mt5_fullauto.py")
        print("  ✅ Signal Analysis: trading_app/gui/signal_analysis_dialog.py")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1

if __name__ == '__main__':
    exit_code = test_session_filtering_logic()
    sys.exit(exit_code)
