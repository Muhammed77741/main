#!/usr/bin/env python3
"""
Clear trade history from database

Usage:
    python clear_history.py                    # Clear all closed trades (keep open)
    python clear_history.py --all              # Clear ALL trades including open
    python clear_history.py --bot crypto_bot   # Clear only for specific bot
    python clear_history.py --events           # Clear trade events only
"""
import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_app'))

from database import DatabaseManager


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Clear trade history from database')
    parser.add_argument('--all', action='store_true', help='Delete ALL trades including OPEN positions')
    parser.add_argument('--bot', type=str, help='Only clear trades for specific bot_id')
    parser.add_argument('--events', action='store_true', help='Also clear trade events')
    parser.add_argument('--groups', action='store_true', help='Also clear position groups')
    args = parser.parse_args()

    # Connect to database
    db = DatabaseManager()

    print("\n" + "="*60)
    print("🗑️  CLEAR TRADE HISTORY")
    print("="*60)

    if args.bot:
        print(f"📌 Target: Bot '{args.bot}'")
    else:
        print(f"📌 Target: ALL bots")

    if args.all:
        print(f"⚠️  Mode: DELETE ALL (including open positions)")
    else:
        print(f"✅ Mode: Keep open positions, delete closed only")

    print("\n" + "-"*60)

    # Confirm
    if args.all:
        confirm = input("\n⚠️  WARNING: This will delete ALL trades including OPEN positions!\nAre you sure? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Cancelled")
            return
    else:
        confirm = input("\nProceed with clearing closed trades? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Cancelled")
            return

    print("\n🔄 Clearing...")

    # Clear trades
    trades_deleted = db.clear_trade_history(
        bot_id=args.bot,
        keep_open=(not args.all)
    )

    # Clear events if requested
    events_deleted = 0
    if args.events or args.all:
        events_deleted = db.clear_trade_events(bot_id=args.bot)

    # Clear groups if requested
    groups_deleted = 0
    if args.groups or args.all:
        groups_deleted = db.clear_position_groups(
            bot_id=args.bot,
            keep_active=(not args.all)
        )

    print("\n" + "="*60)
    print("✅ COMPLETED")
    print("="*60)
    print(f"Trades deleted:        {trades_deleted}")
    if args.events or args.all:
        print(f"Events deleted:        {events_deleted}")
    if args.groups or args.all:
        print(f"Position groups deleted: {groups_deleted}")
    print("="*60 + "\n")

    # Close database
    db.close()


if __name__ == '__main__':
    main()
