#!/usr/bin/env python3
"""
Utility script to update all UNKNOWN statuses to CLOSED in the database.
This is a one-time fix for positions that were closed with UNKNOWN status.
"""

import sqlite3
import os

# Get the database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'trading_app', 'data', 'trading.db')

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
        
        # Update all UNKNOWN_PROCESSING to corresponding TP/SL status
        cursor.execute("""
            UPDATE trades 
            SET status = 'TP1' 
            WHERE status = 'TP1_PROCESSING' OR status = 'UNKNOWN_PROCESSING'
        """)
        tp1_updated = cursor.rowcount
        
        cursor.execute("""
            UPDATE trades 
            SET status = 'TP2' 
            WHERE status = 'TP2_PROCESSING'
        """)
        tp2_updated = cursor.rowcount
        
        cursor.execute("""
            UPDATE trades 
            SET status = 'TP3' 
            WHERE status = 'TP3_PROCESSING'
        """)
        tp3_updated = cursor.rowcount
        
        cursor.execute("""
            UPDATE trades 
            SET status = 'SL' 
            WHERE status = 'SL_PROCESSING'
        """)
        sl_updated = cursor.rowcount
        
        # Update any remaining UNKNOWN to CLOSED
        cursor.execute("""
            UPDATE trades 
            SET status = 'CLOSED' 
            WHERE status = 'UNKNOWN' OR status LIKE '%UNKNOWN%'
        """)
        closed_updated = cursor.rowcount
        
        conn.commit()
        
        print(f"\n✅ Database updated successfully!")
        print(f"   TP1: {tp1_updated} records")
        print(f"   TP2: {tp2_updated} records")
        print(f"   TP3: {tp3_updated} records")
        print(f"   SL: {sl_updated} records")
        print(f"   CLOSED: {closed_updated} records")
        print(f"   Total: {tp1_updated + tp2_updated + tp3_updated + sl_updated + closed_updated} records updated")
        
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
