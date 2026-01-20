#!/usr/bin/env python3
"""
Utility script to update all UNKNOWN statuses to CLOSED in the database.
This fixes positions that were closed with UNKNOWN status.
"""

import sqlite3
import os

# Get the database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'trading_app.db')

def fix_unknown_status():
    """Update all UNKNOWN statuses to CLOSED in the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # First, let's see how many UNKNOWN records we have
        cursor.execute("SELECT COUNT(*) FROM trades WHERE status LIKE '%UNKNOWN%'")
        count = cursor.fetchone()[0]
        print(f"📊 Found {count} trades with UNKNOWN status")
        
        if count == 0:
            print("✅ No UNKNOWN statuses to fix!")
            return
        
        # Show some examples
        cursor.execute("SELECT order_id, status, entry_price, close_price FROM trades WHERE status LIKE '%UNKNOWN%' LIMIT 5")
        print("\n📋 Sample records:")
        for row in cursor.fetchall():
            print(f"  Order: {row[0]}, Status: {row[1]}, Entry: {row[2]}, Close: {row[3]}")
        
        # Update all UNKNOWN statuses to CLOSED
        cursor.execute("""
            UPDATE trades 
            SET status = 'CLOSED' 
            WHERE status LIKE '%UNKNOWN%'
        """)
        updated = cursor.rowcount
        
        conn.commit()
        
        print(f"\n✅ Database updated successfully!")
        print(f"   CLOSED: {updated} records updated")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔧 Starting database status fix...")
    print(f"📂 Database: {DB_PATH}\n")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        print("   Please ensure the trading_app database exists.")
        exit(1)
    
    fix_unknown_status()
    print("\n✨ Done!")
