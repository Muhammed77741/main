#!/usr/bin/env python3
"""Check positions in database"""
import sqlite3
from datetime import datetime

db_path = "trading_app/trading_app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check positions for BCHUSD
print("="*70)
print("BCHUSD POSITIONS IN DATABASE")
print("="*70)

# First, check table structure
cursor.execute("PRAGMA table_info(trades)")
columns = cursor.fetchall()
print("Trades table columns:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")
print()

cursor.execute("""
    SELECT *
    FROM trades
    WHERE bot_id = 'bchusd'
    ORDER BY id DESC
    LIMIT 10
""")

results = cursor.fetchall()

if results:
    print(f"Found {len(results)} recent trades:")
    print()
    for row in results:
        print(f"Row: {row}")
        print("-"*70)
else:
    print("No trades found for BCHUSD")

print()

# Check position groups
print("="*70)
print("POSITION GROUPS FOR BCHUSD")
print("="*70)

cursor.execute("""
    SELECT group_id, bot_id, tp1_hit, entry_price, max_price,
           trade_type, created_at
    FROM position_groups
    WHERE bot_id = 'bchusd'
    ORDER BY created_at DESC
    LIMIT 5
""")

groups = cursor.fetchall()

if groups:
    print(f"Found {len(groups)} position groups:")
    print()
    for row in groups:
        group_id, bot_id, tp1_hit, entry, max_price, trade_type, created = row
        print(f"Group ID: {group_id}")
        print(f"  Entry: ${entry:.2f}, Max: ${max_price:.2f}")
        print(f"  Type: {trade_type}, TP1 Hit: {tp1_hit}")
        print(f"  Created: {created}")
        print("-"*70)
else:
    print("No position groups found for BCHUSD")

# Check live positions from MT5
print()
print("="*70)
print("CHECKING MT5 POSITIONS")
print("="*70)

try:
    import MetaTrader5 as mt5

    if not mt5.initialize():
        print("ERROR: Failed to initialize MT5")
    else:
        positions = mt5.positions_get(symbol='BCHUSD')

        if positions:
            print(f"Found {len(positions)} open positions in MT5:")
            print()
            for p in positions:
                print(f"Ticket: {p.ticket}")
                print(f"  Type: {'BUY' if p.type == 0 else 'SELL'}")
                print(f"  Volume: {p.volume}")
                print(f"  Entry: ${p.price_open:.2f}")
                print(f"  Current: ${p.price_current:.2f}")
                print(f"  SL: ${p.sl:.2f}, TP: ${p.tp:.2f}")
                print(f"  Profit: ${p.profit:.2f}")
                print(f"  Comment: {p.comment}")
                print("-"*70)
        else:
            print("No open positions in MT5 for BCHUSD")

        mt5.shutdown()

except ImportError:
    print("MetaTrader5 module not available")
except Exception as e:
    print(f"Error checking MT5: {e}")

conn.close()
