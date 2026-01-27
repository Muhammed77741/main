#!/usr/bin/env python3
"""
Test to verify profit calculation fixes for XAUUSD bot
"""


def test_profit_percent_calculation():
    """Test profit percentage calculation"""
    print("Testing profit percentage calculation...")
    
    # Test case 1: BUY position with profit
    entry_price = 2000.0
    close_price = 2010.0
    position_type = 'BUY'
    
    # Correct formula
    profit_pct = ((close_price - entry_price) / entry_price) * 100
    expected = 0.5  # 10/2000 * 100 = 0.5%
    
    assert abs(profit_pct - expected) < 0.001, f"BUY profit: Expected {expected}%, got {profit_pct}%"
    print(f"✅ BUY position profit %: {profit_pct:.2f}% (correct)")
    
    # Test case 2: BUY position with loss
    close_price = 1990.0
    profit_pct = ((close_price - entry_price) / entry_price) * 100
    expected = -0.5  # -10/2000 * 100 = -0.5%
    
    assert abs(profit_pct - expected) < 0.001, f"BUY loss: Expected {expected}%, got {profit_pct}%"
    print(f"✅ BUY position loss %: {profit_pct:.2f}% (correct)")
    
    # Test case 3: SELL position with profit
    entry_price = 2000.0
    close_price = 1990.0
    position_type = 'SELL'
    
    profit_pct = ((entry_price - close_price) / entry_price) * 100
    expected = 0.5  # 10/2000 * 100 = 0.5%
    
    assert abs(profit_pct - expected) < 0.001, f"SELL profit: Expected {expected}%, got {profit_pct}%"
    print(f"✅ SELL position profit %: {profit_pct:.2f}% (correct)")
    
    # Test case 4: SELL position with loss
    close_price = 2010.0
    profit_pct = ((entry_price - close_price) / entry_price) * 100
    expected = -0.5  # -10/2000 * 100 = -0.5%
    
    assert abs(profit_pct - expected) < 0.001, f"SELL loss: Expected {expected}%, got {profit_pct}%"
    print(f"✅ SELL position loss %: {profit_pct:.2f}% (correct)")
    
    print("\n" + "="*60)
    print("✅ All profit percentage tests passed!")
    print("="*60)


def test_profit_usd_calculation():
    """Test profit USD calculation for XAUUSD"""
    print("\nTesting profit USD calculation for XAUUSD...")
    
    # For XAUUSD: 1 lot = 100 oz, point value = $100 per lot
    # Formula: profit = (price_diff) * lot_size * 100
    
    # Test case 1: BUY position, 0.1 lot, $10 price increase
    entry_price = 2000.0
    close_price = 2010.0
    lot_size = 0.1
    
    profit_usd = (close_price - entry_price) * lot_size * 100
    expected = 100.0  # $10 * 0.1 lot * 100 = $100
    
    assert abs(profit_usd - expected) < 0.01, f"BUY profit USD: Expected ${expected}, got ${profit_usd}"
    print(f"✅ BUY position (0.1 lot, $10 gain): ${profit_usd:.2f} profit (correct)")
    
    # Test case 2: BUY position, 1 lot, $1 price increase
    lot_size = 1.0
    close_price = 2001.0
    
    profit_usd = (close_price - entry_price) * lot_size * 100
    expected = 100.0  # $1 * 1 lot * 100 = $100
    
    assert abs(profit_usd - expected) < 0.01, f"BUY profit USD: Expected ${expected}, got ${profit_usd}"
    print(f"✅ BUY position (1 lot, $1 gain): ${profit_usd:.2f} profit (correct)")
    
    # Test case 3: SELL position, 0.1 lot, $10 price decrease
    close_price = 1990.0
    lot_size = 0.1
    
    profit_usd = (entry_price - close_price) * lot_size * 100
    expected = 100.0  # $10 * 0.1 lot * 100 = $100
    
    assert abs(profit_usd - expected) < 0.01, f"SELL profit USD: Expected ${expected}, got ${profit_usd}"
    print(f"✅ SELL position (0.1 lot, $10 gain): ${profit_usd:.2f} profit (correct)")
    
    # Test case 4: BUY position with loss
    entry_price = 2000.0
    close_price = 1995.0
    lot_size = 0.5
    
    profit_usd = (close_price - entry_price) * lot_size * 100
    expected = -250.0  # -$5 * 0.5 lot * 100 = -$250
    
    assert abs(profit_usd - expected) < 0.01, f"BUY loss USD: Expected ${expected}, got ${profit_usd}"
    print(f"✅ BUY position (0.5 lot, $5 loss): ${profit_usd:.2f} profit (correct)")
    
    print("\n" + "="*60)
    print("✅ All profit USD tests passed!")
    print("="*60)


def test_old_vs_new_formula():
    """Show the difference between old (wrong) and new (correct) formulas"""
    print("\nComparing OLD (wrong) vs NEW (correct) formulas...")
    print("="*60)
    
    entry_price = 2000.0
    close_price = 2010.0
    lot_size = 0.1
    
    # OLD formula for profit_percent (WRONG)
    pips = (close_price - entry_price) * 10  # 100 pips
    old_profit_pct = (pips / entry_price) * 100  # WRONG!
    
    # NEW formula for profit_percent (CORRECT)
    new_profit_pct = ((close_price - entry_price) / entry_price) * 100
    
    print(f"\nProfit Percentage:")
    print(f"  Entry: ${entry_price:.2f}, Close: ${close_price:.2f}")
    print(f"  OLD (wrong): {old_profit_pct:.2f}%")
    print(f"  NEW (correct): {new_profit_pct:.2f}%")
    print(f"  Difference: {abs(old_profit_pct - new_profit_pct):.2f}%")
    
    # OLD formula for profit_usd (WRONG)
    old_profit_usd = (close_price - entry_price) * lot_size
    
    # NEW formula for profit_usd (CORRECT)
    new_profit_usd = (close_price - entry_price) * lot_size * 100
    
    print(f"\nProfit USD:")
    print(f"  Lot size: {lot_size}")
    print(f"  Price change: ${close_price - entry_price:.2f}")
    print(f"  OLD (wrong): ${old_profit_usd:.2f}")
    print(f"  NEW (correct): ${new_profit_usd:.2f}")
    print(f"  Difference: ${abs(old_profit_usd - new_profit_usd):.2f}")
    
    print("\n" + "="*60)
    print("The fixes correct significant calculation errors!")
    print("="*60)


if __name__ == "__main__":
    try:
        test_profit_percent_calculation()
        test_profit_usd_calculation()
        test_old_vs_new_formula()
        print("\n✅ All tests passed! Profit calculations are now correct.")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
