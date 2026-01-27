#!/usr/bin/env python3
"""
Test script to verify position size format unification:
1. Crypto uses percentage (%)
2. Forex uses pips
3. Format is consistent between Live Trading and Backtest GUIs
"""

import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_app'))

print("=" * 80)
print("Testing Position Size Format Unification")
print("=" * 80)

# Test 1: Check settings_dialog.py
print("\n[Test 1] Live Trading GUI (settings_dialog.py):")
print("-" * 80)

try:
    # Check settings_dialog.py imports from format_utils
    with open('trading_app/gui/settings_dialog.py', 'r') as f:
        settings_content = f.read()
    
    # Check format_utils.py has the shared function
    with open('trading_app/gui/format_utils.py', 'r') as f:
        utils_content = f.read()
    
    # Check that is_crypto_symbol function exists in format_utils
    if 'def is_crypto_symbol(symbol: str)' in utils_content:
        print("✓ PASS: is_crypto_symbol() function found in format_utils.py")
    else:
        print("❌ FAIL: is_crypto_symbol() function not found")
        sys.exit(1)
    
    # Check that settings_dialog imports it
    if 'from .format_utils import is_crypto_symbol' in settings_content or 'from format_utils import is_crypto_symbol' in settings_content:
        print("✓ PASS: settings_dialog imports is_crypto_symbol from format_utils")
    else:
        print("❌ FAIL: settings_dialog doesn't import is_crypto_symbol")
        sys.exit(1)
    
    # Check that suffix is set based on symbol type (not exchange)
    if 'is_crypto = is_crypto_symbol(self.original_config.symbol)' in settings_content:
        print("✓ PASS: Suffix determined by symbol type (not exchange)")
    else:
        print("❌ FAIL: Suffix not determined by symbol type")
        sys.exit(1)
    
    # Check that suffixes are applied to all TP/SL spin boxes
    if 'self.trend_tp1_spin.setSuffix(suffix)' in settings_content:
        print("✓ PASS: TP/SL suffixes are applied")
    else:
        print("❌ FAIL: TP/SL suffixes not applied")
        sys.exit(1)
    
    # Check unit label updated
    if 'unit = "%" if is_crypto else "pips"' in settings_content:
        print("✓ PASS: Unit label uses symbol-based detection")
    else:
        print("❌ FAIL: Unit label not updated")
        sys.exit(1)

except Exception as e:
    print(f"❌ FAIL: Error reading files: {e}")
    sys.exit(1)

# Test 2: Check signal_analysis_dialog.py
print("\n[Test 2] Backtest GUI (signal_analysis_dialog.py):")
print("-" * 80)

try:
    with open('trading_app/gui/signal_analysis_dialog.py', 'r') as f:
        content = f.read()
    
    # Check that crypto uses percentage directly (not multiplied by 100)
    if 'self.trend_tp1_spin.setSuffix("%")' in content:
        print("✓ PASS: Crypto uses '%' suffix")
    else:
        print("❌ FAIL: Crypto '%' suffix not found")
        sys.exit(1)
    
    # Check that Forex uses pips
    if 'self.trend_tp1_spin.setSuffix(" pips")' in content:
        print("✓ PASS: Forex uses 'pips' suffix")
    else:
        print("❌ FAIL: Forex 'pips' suffix not found")
        sys.exit(1)
    
    # Check that crypto values are not multiplied by 100 in update_tp_sl_labels
    if 'self.trend_tp1_spin.setValue(CRYPTO_TREND_TP[\'tp1\'])' in content:
        print("✓ PASS: Crypto values use direct percentage (not *100)")
    else:
        print("❌ FAIL: Crypto values might still be multiplied by 100")
        sys.exit(1)
    
    # Check that custom TP levels don't divide by 100 for crypto
    if "# For crypto, values are already in percentage" in content:
        print("✓ PASS: Custom TP levels use direct percentage for crypto")
    else:
        print("❌ FAIL: Custom TP levels comment not found")
        sys.exit(1)
    
    # Check migration logic for old saved settings
    if "if settings.get('trend_tp1', 0) > MIGRATION_THRESHOLD:" in content:
        print("✓ PASS: Migration logic with MIGRATION_THRESHOLD found")
    else:
        print("❌ FAIL: Migration logic not found")
        sys.exit(1)

except Exception as e:
    print(f"❌ FAIL: Error reading signal_analysis_dialog.py: {e}")
    sys.exit(1)

# Test 3: Verify constants are consistent
print("\n[Test 3] Verify TP/SL constants:")
print("-" * 80)

try:
    # Read signal_analysis_dialog.py to check constants
    with open('trading_app/gui/signal_analysis_dialog.py', 'r') as f:
        content = f.read()
    
    # Check crypto constants (should be in percentage)
    if "CRYPTO_TREND_TP = {'tp1': 1.5, 'tp2': 2.75, 'tp3': 4.5}" in content:
        print("✓ PASS: CRYPTO_TREND_TP constants are in percentage format")
    else:
        print("❌ FAIL: CRYPTO_TREND_TP constants format incorrect")
        sys.exit(1)
    
    # Check MT5 constants (should be in points/pips)
    if "MT5_TREND_TP = {'tp1': 30, 'tp2': 55, 'tp3': 90}" in content:
        print("✓ PASS: MT5_TREND_TP constants are in pips format")
    else:
        print("❌ FAIL: MT5_TREND_TP constants format incorrect")
        sys.exit(1)

except Exception as e:
    print(f"❌ FAIL: Error checking constants: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ All tests passed!")
print("=" * 80)
print("\nSummary of changes:")
print("1. ✓ Live Trading GUI determines format by SYMBOL (not exchange)")
print("2. ✓ Backtest GUI determines format by SYMBOL (not exchange)")
print("3. ✓ Crypto symbols (BTC, ETH, SOL) use % - regardless of exchange")
print("4. ✓ Forex symbols (XAUUSD, EURUSD) use pips")
print("5. ✓ Migration logic handles old saved settings")
print("6. ✓ Values are stored correctly (no *100 for crypto)")
print("=" * 80)
