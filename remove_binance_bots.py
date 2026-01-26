#!/usr/bin/env python3
"""
Remove Binance bots from database
"""
import sys
import os
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_app'))

from database import DatabaseManager


def main():
    # Connect to database
    db = DatabaseManager()

    print("\n" + "="*60)
    print("🗑️  REMOVE BINANCE BOTS")
    print("="*60)

    # Remove BTC and ETH bots
    binance_bots = ['btc', 'eth']

    for bot_id in binance_bots:
        try:
            cursor = db.conn.cursor()
            cursor.execute("DELETE FROM bot_configs WHERE bot_id = ?", (bot_id,))
            db.conn.commit()

            if cursor.rowcount > 0:
                print(f"✅ Removed {bot_id.upper()} bot")
            else:
                print(f"⚠️  {bot_id.upper()} bot not found")
        except Exception as e:
            print(f"❌ Error removing {bot_id}: {e}")

    print("="*60)
    print("✅ Done! Binance bots removed.")
    print("="*60 + "\n")

    # Close database
    db.close()


if __name__ == '__main__':
    main()
