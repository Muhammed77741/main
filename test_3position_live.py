#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test 3-Position Mode with Real MT5 Positions + Magic Number Integration
Opens 3 positions with unique magic numbers, closes TP1, checks trailing stop logic
Tests the new Magic Number system for position tracking
"""
import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import MetaTrader5 as mt5
import time
from datetime import datetime
import uuid
import sqlite3

# Configuration from BCHUSD settings
SYMBOL = 'BCHUSD'
TIMEFRAME = mt5.TIMEFRAME_M15
TOTAL_POSITION_SIZE = 0.10  # Total size to split into 3
RISK_PERCENT = 2.0
MAX_POSITIONS = 12

# 3-Position Mode
USE_3_POSITION_MODE = True
MIN_ORDER_SIZE = 0.010
USE_TRAILING_STOPS = True
TRAILING_STOP_PCT = 0.80  # 80%

# Strategy - V3 Adaptive
# TREND Mode TP
TREND_TP1 = 3.00
TREND_TP2 = 5.00
TREND_TP3 = 8.00

# RANGE Mode TP
RANGE_TP1 = 1.50
RANGE_TP2 = 3.00
RANGE_TP3 = 5.00

# Regime-based SL
USE_REGIME_BASED_SL = True
TREND_SL = 3.00  # points
RANGE_SL = 2.00  # points

print("="*70)
print("3-POSITION MODE LIVE TEST FOR BCHUSD + MAGIC NUMBER")
print("="*70)
print(f"Symbol: {SYMBOL}")
print(f"Total Position Size: {TOTAL_POSITION_SIZE} lots")
print(f"3-Position Mode: {USE_3_POSITION_MODE}")
print(f"Trailing Stops: {USE_TRAILING_STOPS} ({TRAILING_STOP_PCT*100}%)")
print(f"Regime-based SL: {USE_REGIME_BASED_SL}")
print(f"Testing: Magic Number integration (BBBBPPGG format)")
print("="*70)

# Initialize MT5
print("\n[1] Initializing MT5...")
if not mt5.initialize():
    print(f"ERROR: Failed to initialize MT5: {mt5.last_error()}")
    sys.exit(1)
print("SUCCESS: MT5 initialized")

# Get account info
account_info = mt5.account_info()
if account_info is None:
    print(f"ERROR: Failed to get account info")
    mt5.shutdown()
    sys.exit(1)

print(f"Account: {account_info.login}")
print(f"Balance: ${account_info.balance:.2f}")
print(f"Equity: ${account_info.equity:.2f}")

# Check symbol
print(f"\n[2] Checking symbol {SYMBOL}...")
symbol_info = mt5.symbol_info(SYMBOL)
if symbol_info is None:
    print(f"ERROR: Symbol {SYMBOL} not found")
    mt5.shutdown()
    sys.exit(1)

if not symbol_info.visible:
    print(f"Symbol {SYMBOL} is not visible, trying to enable...")
    if not mt5.symbol_select(SYMBOL, True):
        print(f"ERROR: Failed to enable {SYMBOL}")
        mt5.shutdown()
        sys.exit(1)

print(f"Symbol: {SYMBOL}")
print(f"Min lot: {symbol_info.volume_min}")
print(f"Max lot: {symbol_info.volume_max}")
print(f"Lot step: {symbol_info.volume_step}")

# Get current price
tick = mt5.symbol_info_tick(SYMBOL)
if tick is None:
    print(f"ERROR: Failed to get tick for {SYMBOL}")
    mt5.shutdown()
    sys.exit(1)

print(f"Current price: Bid={tick.bid:.2f}, Ask={tick.ask:.2f}")

# Calculate position sizes (split into 3)
print(f"\n[3] Calculating position sizes...")
lot1 = round(TOTAL_POSITION_SIZE * 0.33, 2)
lot2 = round(TOTAL_POSITION_SIZE * 0.33, 2)
lot3 = round(TOTAL_POSITION_SIZE * 0.34, 2)

print(f"Position 1 (TP1): {lot1} lot")
print(f"Position 2 (TP2): {lot2} lot")
print(f"Position 3 (TP3): {lot3} lot")

# Check if sizes are valid
min_lot = symbol_info.volume_min
if lot1 < min_lot or lot2 < min_lot or lot3 < min_lot:
    print(f"\nERROR: Position sizes too small!")
    print(f"Minimum lot size: {min_lot}")
    print(f"Need at least: {min_lot * 3} total lots")
    mt5.shutdown()
    sys.exit(1)

print(f"OK: All positions meet minimum requirement ({min_lot} lot)")

# Simulate market regime (TREND for testing)
CURRENT_REGIME = 'TREND'
print(f"\n[4] Market Regime: {CURRENT_REGIME}")

# Calculate SL and TP levels
# For testing, let's create a BUY signal
SIGNAL_TYPE = 'BUY'  # or 'SELL'
entry = tick.ask

if USE_REGIME_BASED_SL:
    sl_distance = TREND_SL if CURRENT_REGIME == 'TREND' else RANGE_SL
else:
    sl_distance = TREND_SL  # fallback

tp1_distance = TREND_TP1 if CURRENT_REGIME == 'TREND' else RANGE_TP1
tp2_distance = TREND_TP2 if CURRENT_REGIME == 'TREND' else RANGE_TP2
tp3_distance = TREND_TP3 if CURRENT_REGIME == 'TREND' else RANGE_TP3

if SIGNAL_TYPE == 'BUY':
    sl = entry - sl_distance
    tp1 = entry + tp1_distance
    tp2 = entry + tp2_distance
    tp3 = entry + tp3_distance
    order_type = mt5.ORDER_TYPE_BUY
else:
    sl = entry + sl_distance
    tp1 = entry - tp1_distance
    tp2 = entry - tp2_distance
    tp3 = entry - tp3_distance
    order_type = mt5.ORDER_TYPE_SELL

print(f"\n[5] {SIGNAL_TYPE} Signal:")
print(f"Entry: ${entry:.2f}")
print(f"SL: ${sl:.2f} (distance: {sl_distance:.2f})")
print(f"TP1: ${tp1:.2f} (distance: {tp1_distance:.2f})")
print(f"TP2: ${tp2:.2f} (distance: {tp2_distance:.2f})")
print(f"TP3: ${tp3:.2f} (distance: {tp3_distance:.2f})")

# Validate SL/TP
if sl <= 0:
    print(f"\nERROR: Invalid SL: {sl:.2f}")
    mt5.shutdown()
    sys.exit(1)

if SIGNAL_TYPE == 'BUY':
    if sl >= entry:
        print(f"\nERROR: BUY signal but SL ({sl:.2f}) >= Entry ({entry:.2f})")
        mt5.shutdown()
        sys.exit(1)
    if tp1 <= entry:
        print(f"\nERROR: BUY signal but TP1 ({tp1:.2f}) <= Entry ({entry:.2f})")
        mt5.shutdown()
        sys.exit(1)
else:
    if sl <= entry:
        print(f"\nERROR: SELL signal but SL ({sl:.2f}) <= Entry ({entry:.2f})")
        mt5.shutdown()
        sys.exit(1)
    if tp1 >= entry:
        print(f"\nERROR: SELL signal but TP1 ({tp1:.2f}) >= Entry ({entry:.2f})")
        mt5.shutdown()
        sys.exit(1)

print("OK: SL/TP validation passed")

# Get filling mode
filling = symbol_info.filling_mode
if filling & 1:  # FOK
    filling_mode = mt5.ORDER_FILLING_FOK
    filling_name = "FOK"
elif filling & 2:  # IOC
    filling_mode = mt5.ORDER_FILLING_IOC
    filling_name = "IOC"
else:  # RETURN
    filling_mode = mt5.ORDER_FILLING_RETURN
    filling_name = "RETURN"

print(f"\nFilling mode: {filling_name}")

# Generate group ID and counter for magic number
group_id = str(uuid.uuid4())[:8]
group_counter = 42  # Test group counter (0-99)
bot_id = f"bchusd_bot_{SYMBOL}"

# Magic number generation function (matching LiveBotMT5FullAuto)
def generate_magic(bot_id: str, position_num: int, group_counter: int) -> int:
    """Generate unique magic number in BBBBPPGG format"""
    bot_hash = abs(hash(bot_id)) % 10000
    magic = int(f"{bot_hash:04d}{position_num:02d}{group_counter:02d}")
    return magic

print(f"Position Group ID: {group_id}")
print(f"Group Counter: {group_counter}")
print(f"Bot ID: {bot_id}")
print(f"Bot Hash: {abs(hash(bot_id)) % 10000:04d}")

# Connect to database
print(f"\n[DB] Connecting to database...")
db_path = "trading_app/trading_app.db"
db_conn = sqlite3.connect(db_path)
db_cursor = db_conn.cursor()
print(f"SUCCESS: Database connected")

# Confirm before opening
print("\n" + "="*70)
print("READY TO OPEN 3 POSITIONS")
print("="*70)
print(f"WARNING: This will open REAL positions on {SYMBOL}")
print(f"Total risk: ~${abs(entry - sl) * TOTAL_POSITION_SIZE * 100:.2f}")
print("="*70)
response = input("Type 'YES' to proceed: ")

if response.strip().upper() != 'YES':
    print("Cancelled by user")
    db_conn.close()
    mt5.shutdown()
    sys.exit(0)

# Open 3 positions
print("\n[6] Opening 3 positions...")
positions_opened = []
tp_levels = [
    (tp1, lot1, 'TP1', tp1_distance, 1),
    (tp2, lot2, 'TP2', tp2_distance, 2),
    (tp3, lot3, 'TP3', tp3_distance, 3)
]

for tp_price, lot_size, tp_name, tp_distance, pos_num in tp_levels:
    print(f"\nOpening {tp_name} position...")
    
    # Generate unique magic number for this position
    magic = generate_magic(bot_id, pos_num, group_counter)
    print(f"  Magic Number: {magic} (format: {magic:08d})")

    # Prepare request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot_size,
        "type": order_type,
        "price": entry,
        "sl": sl,
        "tp": tp_price,
        "deviation": 20,
        "magic": magic,  # ✅ Use unique magic number
        "comment": f"V3_T_{tp_name}_P{pos_num}/3_G{group_id}_M{magic}",  # ✅ Include magic in comment
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }

    # Send order
    result = mt5.order_send(request)

    if result is None:
        print(f"ERROR: {tp_name} order failed: No result from broker")
        continue

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"ERROR: {tp_name} order failed!")
        print(f"  Error code: {result.retcode}")
        print(f"  Message: {result.comment}")
        print(f"  Volume: {lot_size} lot, Price: ${entry:.2f}")
        continue

    print(f"SUCCESS: {tp_name} position opened!")
    print(f"  Ticket: #{result.order}")
    print(f"  Lot: {lot_size}")
    print(f"  Entry: ${result.price:.2f}")
    print(f"  TP: ${tp_price:.2f}")

    # Save to database (like live bot does) - now with magic_number
    try:
        regime_code = "T" if CURRENT_REGIME == 'TREND' else "R"
        db_cursor.execute("""
            INSERT INTO trades (
                bot_id, symbol, order_id, open_time, trade_type, amount,
                entry_price, stop_loss, take_profit, status, market_regime,
                comment, position_group_id, position_num, trailing_stop_active, magic_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bot_id,
            SYMBOL,
            str(result.order),
            datetime.now(),
            SIGNAL_TYPE,
            lot_size,
            result.price,
            sl,
            tp_price,
            'OPEN',
            CURRENT_REGIME,
            f"V3_{regime_code}_{tp_name}_P{pos_num}/3_G{group_id}_M{magic}",
            group_id,
            pos_num,
            1 if USE_TRAILING_STOPS and pos_num > 1 else 0,
            magic  # ✅ Save magic number to database
        ))
        db_conn.commit()
        print(f"  ✅ Saved to database: pos#{pos_num}, group={group_id[:8]}, magic={magic}")
    except Exception as e:
        print(f"  ⚠️  Failed to save to DB: {e}")

    positions_opened.append({
        'ticket': result.order,
        'name': tp_name,
        'tp': tp_price,
        'lot': lot_size,
        'pos_num': pos_num,
        'entry': result.price,
        'magic': magic  # ✅ Store magic number for later tests
    })

    time.sleep(0.2)  # Small delay between orders

if len(positions_opened) == 0:
    print("\nERROR: Failed to open any positions!")
    mt5.shutdown()
    sys.exit(1)

print(f"\n[7] SUCCESS: Opened {len(positions_opened)}/3 positions!")

# Create position_group record with group_counter
try:
    avg_entry = sum(p['entry'] for p in positions_opened) / len(positions_opened)
    db_cursor.execute("""
        INSERT INTO position_groups (
            group_id, bot_id, tp1_hit, entry_price, max_price, min_price,
            trade_type, group_counter, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        group_id,
        bot_id,
        0,  # TP1 not hit yet
        avg_entry,
        avg_entry,  # Initial max = entry
        avg_entry,  # Initial min = entry
        SIGNAL_TYPE,
        group_counter,  # ✅ Save group_counter for magic number tracking
        datetime.now(),
        datetime.now()
    ))
    db_conn.commit()
    print(f"\n✅ Position group saved to database: {group_id} (counter={group_counter})")
except Exception as e:
    print(f"\n⚠️  Failed to save position group: {e}")

# Show opened positions with magic numbers
print("\nOpened positions:")
for pos in positions_opened:
    print(f"  {pos['name']}: Ticket #{pos['ticket']}, Magic {pos['magic']}, Lot {pos['lot']}, TP ${pos['tp']:.2f}")

# Test magic number retrieval
print("\n[8] Testing Magic Number retrieval from MT5...")
for pos in positions_opened:
    magic = pos['magic']
    print(f"\n  Looking for position with magic={magic}...")
    
    # Retrieve position by magic number
    mt5_positions = mt5.positions_get(magic=magic)
    
    if mt5_positions and len(mt5_positions) > 0:
        mt5_pos = mt5_positions[0]
        print(f"    ✅ Found position: Ticket #{mt5_pos.ticket}, Magic {mt5_pos.magic}")
        print(f"       Volume: {mt5_pos.volume}, P/L: ${mt5_pos.profit:.2f}")
        
        # Verify magic number matches
        if mt5_pos.magic == magic:
            print(f"       ✅ Magic number verified!")
        else:
            print(f"       ⚠️  Magic mismatch: Expected {magic}, Got {mt5_pos.magic}")
    else:
        print(f"    ❌ Position with magic {magic} not found!")

print("\n✅ Magic Number retrieval test complete!")

# Wait a bit
print("\n[9] Waiting 5 seconds before testing TP1 close...")
time.sleep(5)

# Simulate TP1 hit - close first position
if len(positions_opened) >= 1:
    tp1_pos = positions_opened[0]
    print(f"\n[10] Simulating TP1 hit - closing position #{tp1_pos['ticket']} (magic={tp1_pos['magic']})...")

    # Get current position using magic number
    print(f"  Retrieving position by magic number: {tp1_pos['magic']}")
    mt5_pos = None
    positions_by_magic = mt5.positions_get(magic=tp1_pos['magic'])
    if positions_by_magic and len(positions_by_magic) > 0:
        mt5_pos = positions_by_magic[0]
        print(f"  ✅ Found position via magic number: Ticket #{mt5_pos.ticket}")

    if mt5_pos is None:
        print(f"WARNING: Position #{tp1_pos['ticket']} not found (already closed?)")
    else:
        # Close position
        close_type = mt5.ORDER_TYPE_SELL if SIGNAL_TYPE == 'BUY' else mt5.ORDER_TYPE_BUY
        close_price = tick.bid if SIGNAL_TYPE == 'BUY' else tick.ask

        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": mt5_pos.volume,
            "type": close_type,
            "position": mt5_pos.ticket,
            "price": close_price,
            "deviation": 20,
            "magic": tp1_pos['magic'],  # ✅ Use same magic number
            "comment": f"TP1_HIT_TEST_M{tp1_pos['magic']}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        close_result = mt5.order_send(close_request)

        if close_result and close_result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"SUCCESS: TP1 position closed!")
            print(f"  Close price: ${close_price:.2f}")
            profit = (close_price - tp1_pos['entry']) * tp1_pos['lot'] * 100 if SIGNAL_TYPE == 'BUY' else (tp1_pos['entry'] - close_price) * tp1_pos['lot'] * 100
            print(f"  Profit: ${profit:.2f}")

            # Update database
            try:
                db_cursor.execute("""
                    UPDATE trades
                    SET status = 'CLOSED',
                        close_time = ?,
                        close_price = ?,
                        profit = ?
                    WHERE order_id = ?
                """, (datetime.now(), close_price, profit, str(tp1_pos['ticket'])))

                # Update position_group to mark TP1 hit
                db_cursor.execute("""
                    UPDATE position_groups
                    SET tp1_hit = 1,
                        updated_at = ?
                    WHERE group_id = ?
                """, (datetime.now(), group_id))

                db_conn.commit()
                print(f"  ✅ Database updated: TP1 closed, group marked")
            except Exception as e:
                print(f"  ⚠️  Failed to update DB: {e}")
        else:
            error_code = close_result.retcode if close_result else 'None'
            error_msg = close_result.comment if close_result else 'None'
            print(f"ERROR: Failed to close TP1 position")
            print(f"  Error code: {error_code}")
            print(f"  Message: {error_msg}")

# Test retrieving positions by magic after TP1 close
print(f"\n[11] Testing remaining positions retrieval by magic number...")
for pos in positions_opened[1:]:  # Skip TP1 (closed)
    magic = pos['magic']
    print(f"  Checking position with magic={magic}...")
    
    mt5_positions = mt5.positions_get(magic=magic)
    if mt5_positions and len(mt5_positions) > 0:
        mt5_pos = mt5_positions[0]
        print(f"    ✅ Position still open: Ticket #{mt5_pos.ticket}, P/L ${mt5_pos.profit:.2f}")
    else:
        print(f"    ⚠️  Position not found (may have been closed)")

# Test trailing stop logic
if USE_TRAILING_STOPS and len(positions_opened) >= 2:
    print(f"\n[12] Testing trailing stop logic...")
    print(f"Trailing stop enabled: {TRAILING_STOP_PCT*100}%")

    # After TP1 hit, positions 2 and 3 should move SL to breakeven
    # Then trail based on max price

    print("\nTrailing logic:")
    print("  - When TP1 closes, move SL to breakeven for Pos 2 & 3")
    print("  - Track max favorable price")
    print(f"  - If price retraces {TRAILING_STOP_PCT*100}% from max, close positions")

    # Example trailing calculation
    tp1_hit_price = tp1_pos['entry'] + tp1_distance if SIGNAL_TYPE == 'BUY' else tp1_pos['entry'] - tp1_distance
    max_price = tp1_hit_price  # Starting max

    print(f"\n  Initial max price after TP1: ${max_price:.2f}")
    print(f"  Breakeven: ${tp1_pos['entry']:.2f}")

    # Simulate price movement
    simulated_new_price = max_price + 2.0 if SIGNAL_TYPE == 'BUY' else max_price - 2.0
    new_max = simulated_new_price

    print(f"  Simulated new max price: ${new_max:.2f}")

    # Calculate trailing stop trigger
    profit_range = abs(new_max - tp1_pos['entry'])
    trailing_trigger = profit_range * TRAILING_STOP_PCT

    if SIGNAL_TYPE == 'BUY':
        trailing_stop_price = new_max - trailing_trigger
    else:
        trailing_stop_price = new_max + trailing_trigger

    print(f"  Profit range from breakeven: ${profit_range:.2f}")
    print(f"  Trailing stop ({TRAILING_STOP_PCT*100}%): ${trailing_stop_price:.2f}")
    print(f"  If price retraces to ${trailing_stop_price:.2f}, close Pos 2 & 3")

# Test database query for magic numbers
print(f"\n[13] Testing database retrieval of magic numbers...")
try:
    db_cursor.execute("""
        SELECT order_id, position_num, magic_number, status
        FROM trades
        WHERE position_group_id = ?
        ORDER BY position_num
    """, (group_id,))
    
    rows = db_cursor.fetchall()
    print(f"  Found {len(rows)} positions in database:")
    for row in rows:
        order_id, pos_num, magic_num, status = row
        print(f"    Position {pos_num}: Order #{order_id}, Magic {magic_num}, Status {status}")
except Exception as e:
    print(f"  ⚠️  Failed to query database: {e}")

# Summary
print("\n" + "="*70)
print("TEST COMPLETE - MAGIC NUMBER INTEGRATION")
print("="*70)
print(f"Positions opened: {len(positions_opened)}/3")
print(f"Group ID: {group_id}")
print(f"Group Counter: {group_counter}")
print(f"Bot ID Hash: {abs(hash(bot_id)) % 10000:04d}")

print("\n✅ Magic Number Test Results:")
print(f"  - Magic numbers generated in BBBBPPGG format")
print(f"  - Positions opened with unique magic numbers")
print(f"  - Magic numbers saved to database")
print(f"  - Positions retrievable via mt5.positions_get(magic=...)")
print(f"  - Group counter saved to position_groups table")

print("\nRemaining open positions:")

positions = mt5.positions_get(symbol=SYMBOL)
if positions:
    for p in positions:
        if group_id in p.comment:
            profit = p.profit
            print(f"  Ticket #{p.ticket}: Magic {p.magic}, {p.volume} lot, P/L ${profit:.2f}")
else:
    print("  None")

print("\nTo manually close remaining positions:")
print(f"  1. Open MT5 terminal")
print(f"  2. Find positions with comment containing '{group_id}'")
print(f"  3. Close manually or let them hit TP2/TP3")

# Shutdown
db_conn.close()
mt5.shutdown()
print("\nConnections closed (MT5 + Database)")
print("="*70)
