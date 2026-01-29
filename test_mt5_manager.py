#!/usr/bin/env python3
"""
Test MT5Manager singleton with multiple concurrent connections
"""
import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_app'))

from core.mt5_manager import mt5_manager
import MetaTrader5 as mt5
import threading
import time

def bot_simulation(bot_id, iterations=5):
    """Simulate a bot making MT5 API calls"""
    print(f"[{bot_id}] Starting...")

    for i in range(iterations):
        # Ensure connection (uses singleton)
        if mt5_manager.ensure_connection():
            # Make some MT5 API calls
            account_info = mt5.account_info()
            if account_info:
                print(f"[{bot_id}] Iteration {i+1}: Balance = ${account_info.balance:.2f}")
            else:
                print(f"[{bot_id}] Iteration {i+1}: Failed to get account info")
        else:
            print(f"[{bot_id}] Iteration {i+1}: Connection failed")

        time.sleep(1)

    print(f"[{bot_id}] Finished")

def main():
    print("="*60)
    print("MT5 Manager Singleton Test")
    print("="*60)

    # Initialize MT5 connection (singleton)
    print("\n1. Initializing MT5 connection...")
    if not mt5_manager.initialize():
        print("❌ Failed to initialize MT5")
        return

    print("✅ MT5 initialized successfully")

    # Get initial account info
    account_info = mt5.account_info()
    if account_info:
        print(f"   Account: {account_info.login}")
        print(f"   Balance: ${account_info.balance:.2f}")

    # Simulate multiple bots running concurrently
    print("\n2. Starting 6 concurrent bot simulations...")
    threads = []

    for i in range(6):
        bot_id = f"BOT_{i+1}"
        thread = threading.Thread(target=bot_simulation, args=(bot_id, 5))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    print("\n3. All bots finished")

    # Test reconnection
    print("\n4. Testing reconnection...")
    if mt5_manager.reconnect():
        print("✅ Reconnection successful")
    else:
        print("❌ Reconnection failed")

    # Final connection check
    print("\n5. Final connection check...")
    if mt5_manager.ensure_connection():
        account_info = mt5.account_info()
        if account_info:
            print(f"✅ Connected - Balance: ${account_info.balance:.2f}")

    # Shutdown
    print("\n6. Shutting down MT5 connection...")
    mt5_manager.shutdown()
    print("✅ MT5 connection closed")

    print("\n" + "="*60)
    print("Test completed successfully!")
    print("="*60)

if __name__ == '__main__':
    main()
