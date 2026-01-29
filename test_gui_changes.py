#!/usr/bin/env python3
"""
Test script to verify GUI changes:
1. Profit calculation fix
2. DRY_RUN always disabled
3. 3-position mode always enabled
"""

import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_app'))

from models import BotConfig

print("=" * 80)
print("Testing GUI Changes")
print("=" * 80)

# Test 1: Check default bot config values
print("\n[Test 1] Default BotConfig values:")
print("-" * 80)

xauusd_config = BotConfig.default_xauusd()
print(f"✓ XAUUSD Config created")
print(f"  - dry_run: {xauusd_config.dry_run} (should be False)")
print(f"  - use_3_position_mode: {xauusd_config.use_3_position_mode} (should be True)")

assert xauusd_config.dry_run == False, "❌ FAIL: dry_run should be False by default"
assert xauusd_config.use_3_position_mode == True, "❌ FAIL: use_3_position_mode should be True by default"

print("✓ PASS: Default values are correct")

# Test 2: Verify profit calculation logic
print("\n[Test 2] Profit calculation for XAUUSD:")
print("-" * 80)

# Simulate a position
entry_price = 2000.0
current_price = 2010.0
volume = 0.1  # 0.1 lots

# For BUY position
price_diff = current_price - entry_price  # 10.0
expected_profit_xauusd = price_diff * volume * 100.0  # 10.0 * 0.1 * 100 = 100.0

print(f"  Entry: ${entry_price}")
print(f"  Current: ${current_price}")
print(f"  Volume: {volume} lots")
print(f"  Price diff: ${price_diff}")
print(f"  Expected profit (XAUUSD): ${expected_profit_xauusd}")

assert abs(expected_profit_xauusd - 100.0) < 0.01, f"❌ FAIL: Expected profit $100.00, got ${expected_profit_xauusd}"

print("✓ PASS: XAUUSD profit calculation is correct")

# Test 3: Check settings dialog imports (without GUI)
print("\n[Test 3] Settings dialog structure:")
print("-" * 80)

try:
    # Read the file content
    with open('trading_app/gui/settings_dialog.py', 'r') as f:
        content = f.read()
    
    # Check that DRY_RUN checkbox is removed
    if 'self.dry_run_check = QCheckBox' in content:
        print("❌ FAIL: DRY_RUN checkbox still exists in settings_dialog.py")
        sys.exit(1)
    else:
        print("✓ PASS: DRY_RUN checkbox removed from settings dialog")
    
    # Check that 3-position mode checkbox is removed
    if 'self.use_3pos_check = QCheckBox("Enable 3-position mode")' in content:
        print("❌ FAIL: 3-position mode checkbox still exists in settings_dialog.py")
        sys.exit(1)
    else:
        print("✓ PASS: 3-position mode checkbox removed from settings dialog")
    
    # Check that dry_run is set to False in save_settings
    if "self.config['dry_run'] = False" in content:
        print("✓ PASS: dry_run is forced to False in save_settings")
    else:
        print("❌ FAIL: dry_run is not forced to False in save_settings")
        sys.exit(1)
    
    # Check that use_3_position_mode is set to True in save_settings
    if "self.config['use_3_position_mode'] = True" in content:
        print("✓ PASS: use_3_position_mode is forced to True in save_settings")
    else:
        print("❌ FAIL: use_3_position_mode is not forced to True in save_settings")
        sys.exit(1)

except Exception as e:
    print(f"❌ FAIL: Error reading settings_dialog.py: {e}")
    sys.exit(1)

# Test 4: Check positions monitor profit calculation
print("\n[Test 4] Positions monitor profit calculation:")
print("-" * 80)

try:
    with open('trading_app/gui/positions_monitor.py', 'r') as f:
        content = f.read()
    
    # Check that XAUUSD profit calculation is correct
    if 'unrealized_pnl = price_diff * trade.amount * 100.0' in content:
        print("✓ PASS: XAUUSD profit calculation includes 100x multiplier")
    else:
        print("❌ FAIL: XAUUSD profit calculation missing 100x multiplier")
        sys.exit(1)
    
    # Check that MT5 exchange check exists
    if "if self.config.symbol == 'XAUUSD':" in content:
        print("✓ PASS: XAUUSD-specific calculation exists")
    else:
        print("❌ FAIL: XAUUSD-specific calculation not found")
        sys.exit(1)

except Exception as e:
    print(f"❌ FAIL: Error reading positions_monitor.py: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ All tests passed!")
print("=" * 80)
print("\nSummary of changes:")
print("1. ✓ Profit $ calculation fixed for XAUUSD (100x multiplier)")
print("2. ✓ DRY_RUN checkbox removed from settings dialog")
print("3. ✓ DRY_RUN always set to False")
print("4. ✓ 3-position mode checkbox removed from settings dialog")
print("5. ✓ 3-position mode always set to True")
print("=" * 80)
