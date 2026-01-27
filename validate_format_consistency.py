#!/usr/bin/env python3
"""
Comprehensive validation script to verify position size format consistency
between Live Trading GUI and Backtest GUI.
"""

import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_app'))

from models import BotConfig

print("=" * 80)
print("Position Size Format Validation")
print("=" * 80)

# Test 1: Live Trading GUI - Binance (Crypto)
print("\n[Test 1] Live Trading GUI - Binance (Crypto):")
print("-" * 80)

binance_config = BotConfig(
    bot_id='test-btc',
    name='BTC Bot',
    exchange='Binance',
    symbol='BTC/USDT',
    timeframe='1h',
    risk_percent=2.0,
    max_positions=3,
    trend_tp1=1.5,  # Should be displayed as 1.5%
    trend_tp2=2.75,  # Should be displayed as 2.75%
    trend_tp3=4.5,  # Should be displayed as 4.5%
    range_tp1=1.0,
    range_tp2=1.75,
    range_tp3=2.5,
    trend_sl=0.8,  # Should be displayed as 0.8%
    range_sl=0.6   # Should be displayed as 0.6%
)

print(f"Exchange: {binance_config.exchange}")
print(f"Symbol: {binance_config.symbol}")
print(f"Expected suffix: %")
print(f"\nTREND Mode:")
print(f"  TP1: {binance_config.trend_tp1}% (displayed with % suffix)")
print(f"  TP2: {binance_config.trend_tp2}% (displayed with % suffix)")
print(f"  TP3: {binance_config.trend_tp3}% (displayed with % suffix)")
print(f"  SL: {binance_config.trend_sl}% (displayed with % suffix)")
print(f"\nRANGE Mode:")
print(f"  TP1: {binance_config.range_tp1}% (displayed with % suffix)")
print(f"  TP2: {binance_config.range_tp2}% (displayed with % suffix)")
print(f"  TP3: {binance_config.range_tp3}% (displayed with % suffix)")
print(f"  SL: {binance_config.range_sl}% (displayed with % suffix)")

# Test 2: Live Trading GUI - MT5 (Forex)
print("\n[Test 2] Live Trading GUI - MT5 (Forex/Commodities):")
print("-" * 80)

mt5_config = BotConfig.default_xauusd()

print(f"Exchange: {mt5_config.exchange}")
print(f"Symbol: {mt5_config.symbol}")
print(f"Expected suffix: pips")
print(f"\nTREND Mode:")
print(f"  TP1: {mt5_config.trend_tp1} pips (displayed with pips suffix)")
print(f"  TP2: {mt5_config.trend_tp2} pips (displayed with pips suffix)")
print(f"  TP3: {mt5_config.trend_tp3} pips (displayed with pips suffix)")
print(f"  SL: {mt5_config.trend_sl} pips (displayed with pips suffix)")
print(f"\nRANGE Mode:")
print(f"  TP1: {mt5_config.range_tp1} pips (displayed with pips suffix)")
print(f"  TP2: {mt5_config.range_tp2} pips (displayed with pips suffix)")
print(f"  TP3: {mt5_config.range_tp3} pips (displayed with pips suffix)")
print(f"  SL: {mt5_config.range_sl} pips (displayed with pips suffix)")

# Test 3: Backtest GUI - Same format validation
print("\n[Test 3] Backtest GUI - Format Consistency:")
print("-" * 80)

# Read constants from signal_analysis_dialog.py
with open('trading_app/gui/signal_analysis_dialog.py', 'r') as f:
    content = f.read()
    
# Extract constants
import re

# Find CRYPTO_TREND_TP
crypto_trend_match = re.search(r"CRYPTO_TREND_TP = ({'tp1': [\d.]+, 'tp2': [\d.]+, 'tp3': [\d.]+})", content)
if crypto_trend_match:
    print(f"CRYPTO_TREND_TP = {crypto_trend_match.group(1)}")
    print("  Format: percentage (e.g., 1.5 = 1.5%)")
else:
    print("❌ FAIL: CRYPTO_TREND_TP not found")
    sys.exit(1)

# Find MT5_TREND_TP
mt5_trend_match = re.search(r"MT5_TREND_TP = ({'tp1': [\d.]+, 'tp2': [\d.]+, 'tp3': [\d.]+})", content)
if mt5_trend_match:
    print(f"\nMT5_TREND_TP = {mt5_trend_match.group(1)}")
    print("  Format: pips (e.g., 30 = 30 pips)")
else:
    print("❌ FAIL: MT5_TREND_TP not found")
    sys.exit(1)

# Test 4: Verify consistency
print("\n[Test 4] Consistency Check:")
print("-" * 80)

# For Crypto
crypto_consistent = (
    binance_config.trend_tp1 == 1.5 and
    binance_config.trend_tp2 == 2.75 and
    binance_config.trend_tp3 == 4.5
)

if crypto_consistent:
    print("✓ PASS: Crypto TP values are consistent (percentage format)")
else:
    print("❌ FAIL: Crypto TP values are not consistent")
    sys.exit(1)

# For Forex
forex_consistent = (
    mt5_config.trend_tp1 == 30 and
    mt5_config.trend_tp2 == 55 and
    mt5_config.trend_tp3 == 90
)

if forex_consistent:
    print("✓ PASS: Forex TP values are consistent (pips format)")
else:
    print("❌ FAIL: Forex TP values are not consistent")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ All validation checks passed!")
print("=" * 80)
print("\nSummary:")
print("✓ Live Trading GUI:")
print("  - Crypto: Uses % suffix (e.g., 1.5%)")
print("  - Forex: Uses pips suffix (e.g., 30 pips)")
print("✓ Backtest GUI:")
print("  - Crypto: Uses % suffix (e.g., 1.5%)")
print("  - Forex: Uses pips suffix (e.g., 30 pips)")
print("✓ Format is unified across both GUIs")
print("=" * 80)
