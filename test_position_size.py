#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test position size calculation
"""
import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Test 1: With total_position_size set (should use fixed size)
print("Test 1: With total_position_size = 0.01")
total_position_size = 0.01
entry = 110.0
sl = 105.0

if total_position_size is not None:
    lot_size = total_position_size
    print(f"[OK] Using fixed position size: {lot_size} lot")
else:
    # Risk-based calculation
    risk_percent = 2.0
    balance = 10000
    risk_amount = balance * (risk_percent / 100.0)
    risk_per_point = abs(entry - sl)
    point_value = 100.0
    lot_size = risk_amount / (risk_per_point * point_value)
    lot_size = round(lot_size, 2)
    print(f"[OK] Calculated position size (risk-based): {lot_size} lot")

print(f"Final lot size: {lot_size}")
print()

# Test 2: Without total_position_size (should calculate based on risk)
print("Test 2: Without total_position_size (None)")
total_position_size = None

if total_position_size is not None:
    lot_size = total_position_size
    print(f"[OK] Using fixed position size: {lot_size} lot")
else:
    # Risk-based calculation
    risk_percent = 2.0
    balance = 10000
    risk_amount = balance * (risk_percent / 100.0)
    risk_per_point = abs(entry - sl)
    point_value = 100.0
    lot_size = risk_amount / (risk_per_point * point_value)
    lot_size = round(lot_size, 2)
    print(f"[OK] Calculated position size (risk-based): {lot_size} lot")

print(f"Final lot size: {lot_size}")
print()

# Test 3: Split into 3 positions
print("Test 3: Split 0.01 into 3 positions")
total_lot_size = 0.01
lot1 = round(total_lot_size * 0.33, 2)
lot2 = round(total_lot_size * 0.33, 2)
lot3 = round(total_lot_size * 0.34, 2)

print(f"Position 1: {lot1} lot")
print(f"Position 2: {lot2} lot")
print(f"Position 3: {lot3} lot")

min_lot = 0.01
if lot1 < min_lot or lot2 < min_lot or lot3 < min_lot:
    print(f"[WARNING] Some positions below minimum {min_lot} lot")
    print(f"Minimum total size needed: {min_lot * 3} lot")
else:
    print(f"[OK] All positions meet minimum requirement")
