#!/usr/bin/env python3
"""Check MT5 positions only"""
import MetaTrader5 as mt5

if not mt5.initialize():
    print(f"ERROR: {mt5.last_error()}")
    exit(1)

positions = mt5.positions_get()

if positions:
    print(f"Found {len(positions)} open positions:")
    print()
    for p in positions:
        print(f"Ticket: {p.ticket}, Symbol: {p.symbol}")
        print(f"  Type: {'BUY' if p.type == 0 else 'SELL'}, Volume: {p.volume}")
        print(f"  Entry: ${p.price_open:.2f}, Current: ${p.price_current:.2f}")
        print(f"  SL: ${p.sl:.2f}, TP: ${p.tp:.2f}")
        print(f"  Profit: ${p.profit:.2f}")
        print(f"  Comment: '{p.comment}'")
        print(f"  Magic: {p.magic}")
        print()
else:
    print("No open positions")

mt5.shutdown()
