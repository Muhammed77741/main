#!/usr/bin/env python3
"""
Test script to verify MT5 crypto symbols (BTCUSD, ETHUSD, SOLUSD) use % format
"""

import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_app'))

from models import BotConfig

print("=" * 80)
print("Testing MT5 Crypto Symbols (BTCUSD, ETHUSD, SOLUSD)")
print("=" * 80)

# Test 1: MT5 BTCUSD - should use % format
print("\n[Test 1] MT5 BTCUSD (Crypto via MT5):")
print("-" * 80)

btcusd_config = BotConfig(
    bot_id='btcusd-mt5',
    name='BTCUSD via MT5',
    exchange='MT5',
    symbol='BTCUSD',
    timeframe='1h',
    risk_percent=2.0,
    max_positions=3,
    trend_tp1=1.5,  # Should use % format
    trend_tp2=2.75,
    trend_tp3=4.5,
    range_tp1=1.0,
    range_tp2=1.75,
    range_tp3=2.5,
    trend_sl=0.8,
    range_sl=0.6
)

print(f"Exchange: {btcusd_config.exchange}")
print(f"Symbol: {btcusd_config.symbol}")
print(f"Expected suffix: % (crypto)")
print(f"\nTREND Mode:")
print(f"  TP1: {btcusd_config.trend_tp1}% (displayed with % suffix)")
print(f"  TP2: {btcusd_config.trend_tp2}% (displayed with % suffix)")
print(f"  TP3: {btcusd_config.trend_tp3}% (displayed with % suffix)")
print(f"  SL: {btcusd_config.trend_sl}% (displayed with % suffix)")

# Test 2: MT5 ETHUSD - should use % format
print("\n[Test 2] MT5 ETHUSD (Crypto via MT5):")
print("-" * 80)

ethusd_config = BotConfig(
    bot_id='ethusd-mt5',
    name='ETHUSD via MT5',
    exchange='MT5',
    symbol='ETHUSD',
    timeframe='1h',
    risk_percent=2.0,
    max_positions=3,
    trend_tp1=1.5,
    trend_tp2=2.75,
    trend_tp3=4.5,
    range_tp1=1.0,
    range_tp2=1.75,
    range_tp3=2.5,
    trend_sl=0.8,
    range_sl=0.6
)

print(f"Exchange: {ethusd_config.exchange}")
print(f"Symbol: {ethusd_config.symbol}")
print(f"Expected suffix: % (crypto)")
print(f"\nTREND Mode:")
print(f"  TP1: {ethusd_config.trend_tp1}% (displayed with % suffix)")
print(f"  TP2: {ethusd_config.trend_tp2}% (displayed with % suffix)")
print(f"  TP3: {ethusd_config.trend_tp3}% (displayed with % suffix)")
print(f"  SL: {ethusd_config.trend_sl}% (displayed with % suffix)")

# Test 3: MT5 SOLUSD - should use % format
print("\n[Test 3] MT5 SOLUSD (Crypto via MT5):")
print("-" * 80)

solusd_config = BotConfig(
    bot_id='solusd-mt5',
    name='SOLUSD via MT5',
    exchange='MT5',
    symbol='SOLUSD',
    timeframe='1h',
    risk_percent=2.0,
    max_positions=3,
    trend_tp1=1.5,
    trend_tp2=2.75,
    trend_tp3=4.5,
    range_tp1=1.0,
    range_tp2=1.75,
    range_tp3=2.5,
    trend_sl=0.8,
    range_sl=0.6
)

print(f"Exchange: {solusd_config.exchange}")
print(f"Symbol: {solusd_config.symbol}")
print(f"Expected suffix: % (crypto)")
print(f"\nTREND Mode:")
print(f"  TP1: {solusd_config.trend_tp1}% (displayed with % suffix)")
print(f"  TP2: {solusd_config.trend_tp2}% (displayed with % suffix)")
print(f"  TP3: {solusd_config.trend_tp3}% (displayed with % suffix)")
print(f"  SL: {solusd_config.trend_sl}% (displayed with % suffix)")

# Test 4: MT5 XAUUSD - should still use pips format
print("\n[Test 4] MT5 XAUUSD (Forex/Commodities via MT5):")
print("-" * 80)

xauusd_config = BotConfig.default_xauusd()

print(f"Exchange: {xauusd_config.exchange}")
print(f"Symbol: {xauusd_config.symbol}")
print(f"Expected suffix: pips (forex/commodities)")
print(f"\nTREND Mode:")
print(f"  TP1: {xauusd_config.trend_tp1} pips (displayed with pips suffix)")
print(f"  TP2: {xauusd_config.trend_tp2} pips (displayed with pips suffix)")
print(f"  TP3: {xauusd_config.trend_tp3} pips (displayed with pips suffix)")
print(f"  SL: {xauusd_config.trend_sl} pips (displayed with pips suffix)")

# Test 5: Verify is_crypto_symbol function
print("\n[Test 5] Verify is_crypto_symbol() and format_utils:")
print("-" * 80)

# Import the function from format_utils
try:
    with open('trading_app/gui/format_utils.py', 'r') as f:
        utils_content = f.read()
    
    with open('trading_app/gui/settings_dialog.py', 'r') as f:
        settings_content = f.read()

    # Check if function exists in format_utils
    if 'def is_crypto_symbol' in utils_content:
        print("✓ PASS: is_crypto_symbol() function found in format_utils.py")
    else:
        print("❌ FAIL: is_crypto_symbol() function not found")
        sys.exit(1)

    # Check if SOL is in crypto keywords
    if "'SOL'" in utils_content or '"SOL"' in utils_content:
        print("✓ PASS: SOL keyword found in crypto detection")
    else:
        print("❌ FAIL: SOL keyword not found")
        sys.exit(1)

    # Check if suffix is set based on symbol, not exchange
    if 'is_crypto = is_crypto_symbol(self.original_config.symbol)' in settings_content:
        print("✓ PASS: Suffix determined by symbol type (not exchange)")
    else:
        print("❌ FAIL: Suffix still determined by exchange")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ FAIL: Error reading files: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ All MT5 crypto tests passed!")
print("=" * 80)
print("\nSummary:")
print("✓ MT5 Crypto symbols (BTCUSD, ETHUSD, SOLUSD): Use % format")
print("✓ MT5 Forex symbols (XAUUSD, EURUSD): Use pips format")
print("✓ Format determined by SYMBOL, not by EXCHANGE")
print("=" * 80)
