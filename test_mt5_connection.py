#!/usr/bin/env python3
"""
Test MT5 Connection
Diagnostic script to check MT5 connection and display account info
"""
import sys
import os
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    import MetaTrader5 as mt5

    print("=" * 60)
    print("🔌 MT5 CONNECTION TEST")
    print("=" * 60)

    # Try to shutdown first
    print("\n1️⃣ Shutting down any existing connection...")
    try:
        mt5.shutdown()
        print("   ✅ Shutdown complete")
    except Exception as e:
        print(f"   ⚠️  Shutdown warning: {e}")

    # Try to initialize
    print("\n2️⃣ Initializing MT5...")
    if not mt5.initialize():
        error = mt5.last_error()
        print(f"   ❌ Failed to initialize MT5")
        print(f"   Error code: {error[0] if error else 'Unknown'}")
        print(f"   Error message: {error[1] if error and len(error) > 1 else 'Unknown'}")
        print("\n💡 Troubleshooting:")
        print("   • Check that MT5 terminal is running")
        print("   • Make sure you are logged in to your trading account")
        print("   • Try closing and reopening MT5")
        print("   • Make sure no other Python scripts are using MT5")
        sys.exit(1)

    print("   ✅ MT5 initialized successfully")

    # Get account info
    print("\n3️⃣ Getting account information...")
    account_info = mt5.account_info()

    if account_info is None:
        error = mt5.last_error()
        print(f"   ❌ Failed to get account info")
        print(f"   Error: {error}")
        mt5.shutdown()
        sys.exit(1)

    print("   ✅ Account info retrieved")

    # Display account details
    print("\n" + "=" * 60)
    print("📊 ACCOUNT INFORMATION")
    print("=" * 60)
    print(f"Login:           {account_info.login}")
    print(f"Server:          {account_info.server}")
    print(f"Name:            {account_info.name}")
    print(f"Company:         {account_info.company}")
    print(f"Currency:        {account_info.currency}")
    print(f"Balance:         {account_info.balance}")
    print(f"Equity:          {account_info.equity}")
    print(f"Margin:          {account_info.margin}")
    print(f"Free Margin:     {account_info.margin_free}")
    print(f"Leverage:        1:{account_info.leverage}")

    # Get symbols
    print("\n4️⃣ Getting available symbols...")
    symbols = mt5.symbols_get()

    if symbols:
        visible_symbols = [s.name for s in symbols if s.visible]
        print(f"   ✅ Found {len(symbols)} total symbols")
        print(f"   ✅ {len(visible_symbols)} visible symbols")

        # Show first 20 visible symbols
        print("\n📋 First 20 visible symbols:")
        for i, symbol in enumerate(visible_symbols[:20], 1):
            print(f"   {i:2d}. {symbol}")

        if len(visible_symbols) > 20:
            print(f"   ... and {len(visible_symbols) - 20} more")
    else:
        print("   ⚠️  No symbols found")

    # Test getting tick data
    print("\n5️⃣ Testing tick data (EURUSD)...")
    tick = mt5.symbol_info_tick("EURUSD")

    if tick:
        print(f"   ✅ EURUSD tick data:")
        print(f"      Bid:  {tick.bid}")
        print(f"      Ask:  {tick.ask}")
        print(f"      Last: {tick.last}")
    else:
        print("   ⚠️  Could not get EURUSD tick data")

    # Shutdown
    print("\n6️⃣ Shutting down MT5...")
    mt5.shutdown()
    print("   ✅ Shutdown complete")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - MT5 CONNECTION WORKING")
    print("=" * 60)

except ImportError:
    print("❌ MetaTrader5 library not installed")
    print("\nInstall it with:")
    print("   pip install MetaTrader5")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
