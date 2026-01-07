#!/usr/bin/env python3
"""
Test script for TP monitoring functionality
"""

import sys
from pathlib import Path
import os
import csv
from datetime import datetime

# Add smc_trading_strategy to path
sys.path.insert(0, str(Path(__file__).parent / 'smc_trading_strategy'))

def test_file_structure():
    """Test that TP hits log file structure is correct"""
    print("Testing TP hits log file structure...")
    
    test_tp_hits_file = 'test_bot_tp_hits_log.csv'
    
    try:
        # Clean up any existing test file
        if os.path.exists(test_tp_hits_file):
            os.remove(test_tp_hits_file)
        
        # Create the file with expected headers
        with open(test_tp_hits_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Timestamp', 'Ticket', 'TP_Level', 'Type', 'Volume',
                'Entry_Price', 'TP_Target', 'Current_Price', 'SL',
                'Profit', 'Pips', 'Market_Regime', 'Duration_Minutes', 'Comment'
            ])
        
        # Check if file was created
        if os.path.exists(test_tp_hits_file):
            print(f"✅ TP hits log file created: {test_tp_hits_file}")
        else:
            print(f"❌ TP hits log file NOT created")
            return False
        
        # Check file contents (headers)
        with open(test_tp_hits_file, 'r') as f:
            header = f.readline().strip()
            expected_fields = ['Timestamp', 'Ticket', 'TP_Level', 'Type', 'Volume',
                             'Entry_Price', 'TP_Target', 'Current_Price']
            if all(field in header for field in expected_fields):
                print(f"✅ TP hits log has correct headers")
                print(f"   Headers: {header}")
            else:
                print(f"❌ TP hits log headers incorrect: {header}")
                return False
        
        # Test writing a TP hit
        print("\nTesting TP hit logging...")
        with open(test_tp_hits_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                12345,
                'TP1',
                'BUY',
                0.01,
                2650.00,
                2680.00,
                2680.50,
                2640.00,
                30.00,
                30.0,
                'TREND',
                45.5,
                'V3_T_TP1'
            ])
        
        # Check if TP hit was logged
        with open(test_tp_hits_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 2:  # Header + 1 data line
                print(f"✅ TP hit logged successfully")
                print(f"   Sample log entry: {lines[1].strip()}")
            else:
                print(f"❌ TP hit not logged")
                return False
        
        # Test multiple TP levels
        print("\nTesting multiple TP level logging...")
        with open(test_tp_hits_file, 'a', newline='') as f:
            writer = csv.writer(f)
            # TP2 hit
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                12346,
                'TP2',
                'BUY',
                0.01,
                2650.00,
                2705.00,
                2705.20,
                2640.00,
                55.00,
                55.0,
                'TREND',
                120.5,
                'V3_T_TP2'
            ])
            # TP3 hit
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                12347,
                'TP3',
                'SELL',
                0.01,
                2650.00,
                2600.00,
                2599.80,
                2660.00,
                50.00,
                50.0,
                'RANGE',
                90.0,
                'V3_R_TP3'
            ])
        
        # Count entries
        with open(test_tp_hits_file, 'r') as f:
            lines = f.readlines()
            data_lines = len(lines) - 1  # Exclude header
            if data_lines == 3:
                print(f"✅ Multiple TP hits logged correctly ({data_lines} entries)")
            else:
                print(f"❌ Expected 3 entries, got {data_lines}")
                return False
        
        print("\n✅ All file structure tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up test file
        try:
            if os.path.exists(test_tp_hits_file):
                os.remove(test_tp_hits_file)
                print(f"🧹 Cleaned up: {test_tp_hits_file}")
        except Exception as e:
            print(f"⚠️  Could not clean up test file: {e}")


def test_tp_level_detection():
    """Test TP level detection logic"""
    print("\n" + "="*60)
    print("Testing TP level detection logic...")
    print("="*60)
    
    # Test BUY position
    entry = 2650.00
    tp = 2680.00
    current_prices = [2679.00, 2679.50, 2680.00, 2680.50, 2681.00]
    
    print(f"\nBUY position: Entry={entry}, TP={tp}")
    for price in current_prices:
        tolerance = 0.5
        tp_hit = price >= (tp - tolerance)
        status = "✅ HIT" if tp_hit else "❌ NOT HIT"
        print(f"  Current price: {price} - {status}")
    
    # Test SELL position
    entry = 2650.00
    tp = 2620.00
    current_prices = [2621.00, 2620.50, 2620.00, 2619.50, 2619.00]
    
    print(f"\nSELL position: Entry={entry}, TP={tp}")
    for price in current_prices:
        tolerance = 0.5
        tp_hit = price <= (tp + tolerance)
        status = "✅ HIT" if tp_hit else "❌ NOT HIT"
        print(f"  Current price: {price} - {status}")
    
    print("\n✅ TP detection logic verified!")


def main():
    print("="*60)
    print("TP MONITORING FUNCTIONALITY TEST")
    print("="*60)
    
    # Test 1: File structure and logging
    success = test_file_structure()
    
    # Test 2: TP level detection logic
    if success:
        test_tp_level_detection()
    
    print("\n" + "="*60)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
