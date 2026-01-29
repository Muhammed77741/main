#!/usr/bin/env python3
"""Check bot configuration in database"""
import sqlite3

db_path = "trading_app/trading_app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all bot configs
cursor.execute("""
    SELECT bot_id, symbol, total_position_size, use_3_position_mode, risk_percent
    FROM bot_configs
""")

results = cursor.fetchall()

if results:
    print("All Bot Configurations:")
    print("="*70)
    for row in results:
        bot_id, symbol, total_pos, use_3pos, risk_pct = row
        print(f"Bot ID: {bot_id}")
        print(f"Symbol: {symbol}")
        print(f"Total Position Size: {total_pos}")
        print(f"Use 3-Position Mode: {use_3pos}")
        print(f"Risk Percent: {risk_pct}%")
        print("-"*70)
else:
    print("No bots found in database")

conn.close()
