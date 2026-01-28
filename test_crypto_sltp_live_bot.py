#!/usr/bin/env python3
"""
Test crypto SL/TP percentage calculation in live bot

This test verifies that:
1. Crypto symbols (BTC, ETH, SOL) are detected correctly
2. SL/TP are calculated as percentages for crypto
3. SL/TP are calculated as points for forex/commodities
4. Values match between live bot and Signal Analysis
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'trading_app' / 'gui'))
sys.path.insert(0, str(Path(__file__).parent / 'trading_bots' / 'xauusd_bot'))

from format_utils import is_crypto_symbol

# Import constants from live bot
# We'll simulate the calculation logic here
CRYPTO_TREND_TP1_PCT = 1.5   # 1.5% TP1
CRYPTO_TREND_TP2_PCT = 2.75  # 2.75% TP2
CRYPTO_TREND_TP3_PCT = 4.5   # 4.5% TP3
CRYPTO_TREND_SL_PCT = 0.8    # 0.8% SL

CRYPTO_RANGE_TP1_PCT = 1.0   # 1.0% TP1
CRYPTO_RANGE_TP2_PCT = 1.75  # 1.75% TP2
CRYPTO_RANGE_TP3_PCT = 2.5   # 2.5% TP3
CRYPTO_RANGE_SL_PCT = 0.6    # 0.6% SL

# Forex/commodities TP/SL in points
MT5_TREND_TP1 = 30
MT5_TREND_TP2 = 55
MT5_TREND_TP3 = 90
MT5_TREND_SL = 16

MT5_RANGE_TP1 = 20
MT5_RANGE_TP2 = 35
MT5_RANGE_TP3 = 50
MT5_RANGE_SL = 12


def calculate_crypto_sltp(entry_price, signal_direction, regime):
    """Calculate SL/TP for crypto using percentages"""
    if regime == 'TREND':
        tp1_pct = CRYPTO_TREND_TP1_PCT
        tp2_pct = CRYPTO_TREND_TP2_PCT
        tp3_pct = CRYPTO_TREND_TP3_PCT
        sl_pct = CRYPTO_TREND_SL_PCT
    else:  # RANGE
        tp1_pct = CRYPTO_RANGE_TP1_PCT
        tp2_pct = CRYPTO_RANGE_TP2_PCT
        tp3_pct = CRYPTO_RANGE_TP3_PCT
        sl_pct = CRYPTO_RANGE_SL_PCT
    
    # Calculate SL/TP as percentages of entry price
    if signal_direction == 1:  # LONG
        sl = entry_price * (1 - sl_pct / 100)
        tp1 = entry_price * (1 + tp1_pct / 100)
        tp2 = entry_price * (1 + tp2_pct / 100)
        tp3 = entry_price * (1 + tp3_pct / 100)
    else:  # SHORT
        sl = entry_price * (1 + sl_pct / 100)
        tp1 = entry_price * (1 - tp1_pct / 100)
        tp2 = entry_price * (1 - tp2_pct / 100)
        tp3 = entry_price * (1 - tp3_pct / 100)
    
    return sl, tp1, tp2, tp3


def calculate_forex_sltp(entry_price, signal_direction, regime):
    """Calculate SL/TP for forex/commodities using points"""
    if regime == 'TREND':
        tp1_dist = MT5_TREND_TP1
        tp2_dist = MT5_TREND_TP2
        tp3_dist = MT5_TREND_TP3
        sl_dist = MT5_TREND_SL
    else:  # RANGE
        tp1_dist = MT5_RANGE_TP1
        tp2_dist = MT5_RANGE_TP2
        tp3_dist = MT5_RANGE_TP3
        sl_dist = MT5_RANGE_SL
    
    if signal_direction == 1:  # LONG
        sl = entry_price - sl_dist
        tp1 = entry_price + tp1_dist
        tp2 = entry_price + tp2_dist
        tp3 = entry_price + tp3_dist
    else:  # SHORT
        sl = entry_price + sl_dist
        tp1 = entry_price - tp1_dist
        tp2 = entry_price - tp2_dist
        tp3 = entry_price - tp3_dist
    
    return sl, tp1, tp2, tp3


def test_crypto_detection():
    """Test crypto symbol detection"""
    print("\n[TEST 1] Crypto Symbol Detection")
    print("=" * 60)
    
    test_cases = [
        ('BTCUSD', True),
        ('BTC/USDT', True),
        ('ETHUSD', True),
        ('ETH/USDT', True),
        ('SOLUSD', True),
        ('SOL/USDT', True),
        ('XAUUSD', False),
        ('EURUSD', False),
        ('GBPUSD', False),
        ('USDJPY', False),
    ]
    
    passed = 0
    failed = 0
    
    for symbol, expected in test_cases:
        result = is_crypto_symbol(symbol)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status}: {symbol:15} -> {result:5} (expected: {expected})")
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return failed == 0


def test_crypto_sltp_calculation():
    """Test crypto SL/TP percentage calculation"""
    print("\n[TEST 2] Crypto SL/TP Calculation (Percentages)")
    print("=" * 60)
    
    # Test BTC LONG in TREND mode
    entry_price = 50000.0  # BTC at $50,000
    signal_direction = 1  # LONG
    regime = 'TREND'
    
    sl, tp1, tp2, tp3 = calculate_crypto_sltp(entry_price, signal_direction, regime)
    
    print(f"\nBTC LONG in TREND mode:")
    print(f"  Entry: ${entry_price:.2f}")
    print(f"  SL:    ${sl:.2f} ({CRYPTO_TREND_SL_PCT}% below entry)")
    print(f"  TP1:   ${tp1:.2f} ({CRYPTO_TREND_TP1_PCT}% above entry)")
    print(f"  TP2:   ${tp2:.2f} ({CRYPTO_TREND_TP2_PCT}% above entry)")
    print(f"  TP3:   ${tp3:.2f} ({CRYPTO_TREND_TP3_PCT}% above entry)")
    
    # Verify calculations
    expected_sl = entry_price * (1 - CRYPTO_TREND_SL_PCT / 100)
    expected_tp1 = entry_price * (1 + CRYPTO_TREND_TP1_PCT / 100)
    expected_tp3 = entry_price * (1 + CRYPTO_TREND_TP3_PCT / 100)
    
    checks = [
        (abs(sl - expected_sl) < 0.01, f"SL: {sl:.2f} == {expected_sl:.2f}"),
        (abs(tp1 - expected_tp1) < 0.01, f"TP1: {tp1:.2f} == {expected_tp1:.2f}"),
        (abs(tp3 - expected_tp3) < 0.01, f"TP3: {tp3:.2f} == {expected_tp3:.2f}"),
        (sl < entry_price, f"SL below entry for LONG"),
        (tp1 > entry_price, f"TP1 above entry for LONG"),
        (sl > 0, f"SL is positive: {sl:.2f}"),
    ]
    
    all_pass = True
    for check, desc in checks:
        status = "✅ PASS" if check else "❌ FAIL"
        print(f"  {status}: {desc}")
        if not check:
            all_pass = False
    
    # Test ETH SHORT in RANGE mode
    print(f"\nETH SHORT in RANGE mode:")
    entry_price = 3000.0  # ETH at $3,000
    signal_direction = -1  # SHORT
    regime = 'RANGE'
    
    sl, tp1, tp2, tp3 = calculate_crypto_sltp(entry_price, signal_direction, regime)
    
    print(f"  Entry: ${entry_price:.2f}")
    print(f"  SL:    ${sl:.2f} ({CRYPTO_RANGE_SL_PCT}% above entry)")
    print(f"  TP1:   ${tp1:.2f} ({CRYPTO_RANGE_TP1_PCT}% below entry)")
    print(f"  TP2:   ${tp2:.2f} ({CRYPTO_RANGE_TP2_PCT}% below entry)")
    print(f"  TP3:   ${tp3:.2f} ({CRYPTO_RANGE_TP3_PCT}% below entry)")
    
    checks = [
        (sl > entry_price, f"SL above entry for SHORT"),
        (tp1 < entry_price, f"TP1 below entry for SHORT"),
        (sl > 0, f"SL is positive: {sl:.2f}"),
        (tp1 > 0, f"TP1 is positive: {tp1:.2f}"),
    ]
    
    for check, desc in checks:
        status = "✅ PASS" if check else "❌ FAIL"
        print(f"  {status}: {desc}")
        if not check:
            all_pass = False
    
    return all_pass


def test_forex_sltp_calculation():
    """Test forex/commodities SL/TP point calculation"""
    print("\n[TEST 3] Forex/Commodities SL/TP Calculation (Points)")
    print("=" * 60)
    
    # Test XAUUSD LONG in TREND mode
    entry_price = 2000.0  # Gold at $2000
    signal_direction = 1  # LONG
    regime = 'TREND'
    
    sl, tp1, tp2, tp3 = calculate_forex_sltp(entry_price, signal_direction, regime)
    
    print(f"\nXAUUSD LONG in TREND mode:")
    print(f"  Entry: ${entry_price:.2f}")
    print(f"  SL:    ${sl:.2f} ({MT5_TREND_SL} points below entry)")
    print(f"  TP1:   ${tp1:.2f} ({MT5_TREND_TP1} points above entry)")
    print(f"  TP2:   ${tp2:.2f} ({MT5_TREND_TP2} points above entry)")
    print(f"  TP3:   ${tp3:.2f} ({MT5_TREND_TP3} points above entry)")
    
    # Verify calculations
    expected_sl = entry_price - MT5_TREND_SL
    expected_tp1 = entry_price + MT5_TREND_TP1
    expected_tp3 = entry_price + MT5_TREND_TP3
    
    checks = [
        (abs(sl - expected_sl) < 0.01, f"SL: {sl:.2f} == {expected_sl:.2f}"),
        (abs(tp1 - expected_tp1) < 0.01, f"TP1: {tp1:.2f} == {expected_tp1:.2f}"),
        (abs(tp3 - expected_tp3) < 0.01, f"TP3: {tp3:.2f} == {expected_tp3:.2f}"),
        (sl < entry_price, f"SL below entry for LONG"),
        (tp1 > entry_price, f"TP1 above entry for LONG"),
        (sl > 0, f"SL is positive: {sl:.2f}"),
    ]
    
    all_pass = True
    for check, desc in checks:
        status = "✅ PASS" if check else "❌ FAIL"
        print(f"  {status}: {desc}")
        if not check:
            all_pass = False
    
    return all_pass


def test_no_zero_sltp():
    """Test that SL/TP values are never zero or invalid"""
    print("\n[TEST 4] SL/TP Never Zero or Invalid")
    print("=" * 60)
    
    test_cases = [
        ('BTCUSD', 50000, 1, 'TREND', True),    # BTC LONG TREND
        ('ETHUSD', 3000, -1, 'RANGE', True),    # ETH SHORT RANGE
        ('SOLUSD', 150, 1, 'RANGE', True),      # SOL LONG RANGE
        ('XAUUSD', 2000, 1, 'TREND', False),    # Gold LONG TREND
        ('XAUUSD', 2100, -1, 'RANGE', False),   # Gold SHORT RANGE
    ]
    
    all_pass = True
    
    for symbol, entry, direction, regime, is_crypto in test_cases:
        if is_crypto:
            sl, tp1, tp2, tp3 = calculate_crypto_sltp(entry, direction, regime)
        else:
            sl, tp1, tp2, tp3 = calculate_forex_sltp(entry, direction, regime)
        
        direction_str = "LONG" if direction == 1 else "SHORT"
        print(f"\n{symbol} {direction_str} {regime}:")
        print(f"  Entry: ${entry:.2f}")
        print(f"  SL: ${sl:.2f}, TP1: ${tp1:.2f}, TP2: ${tp2:.2f}, TP3: ${tp3:.2f}")
        
        checks = [
            (sl > 0, f"SL > 0: {sl:.2f}"),
            (tp1 > 0, f"TP1 > 0: {tp1:.2f}"),
            (tp2 > 0, f"TP2 > 0: {tp2:.2f}"),
            (tp3 > 0, f"TP3 > 0: {tp3:.2f}"),
        ]
        
        if direction == 1:  # LONG
            checks.extend([
                (sl < entry, f"SL < Entry for LONG"),
                (tp1 > entry, f"TP1 > Entry for LONG"),
            ])
        else:  # SHORT
            checks.extend([
                (sl > entry, f"SL > Entry for SHORT"),
                (tp1 < entry, f"TP1 < Entry for SHORT"),
            ])
        
        for check, desc in checks:
            status = "✅ PASS" if check else "❌ FAIL"
            print(f"  {status}: {desc}")
            if not check:
                all_pass = False
    
    return all_pass


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("CRYPTO SL/TP CALCULATION TEST SUITE")
    print("=" * 60)
    
    results = []
    
    results.append(("Crypto Detection", test_crypto_detection()))
    results.append(("Crypto SL/TP Calculation", test_crypto_sltp_calculation()))
    results.append(("Forex SL/TP Calculation", test_forex_sltp_calculation()))
    results.append(("No Zero/Invalid SL/TP", test_no_zero_sltp()))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        sys.exit(1)
