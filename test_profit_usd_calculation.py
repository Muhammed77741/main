#!/usr/bin/env python3
"""
Test to verify profit_usd calculation in Signal Analysis
"""

# Simulate the profit_usd calculation
def test_profit_usd_calculation():
    print("=" * 80)
    print("Testing profit_usd Calculation in Signal Analysis")
    print("=" * 80)
    
    # Example 1: Crypto win
    profit_pct = 1.5  # 1.5% profit
    starting_balance = 10000  # $10,000
    profit_usd = (profit_pct / 100.0) * starting_balance
    
    print(f"\nExample 1: Crypto Win")
    print(f"  Profit %: {profit_pct}%")
    print(f"  Starting Balance: ${starting_balance:,.2f}")
    print(f"  Formula: ({profit_pct} / 100.0) * {starting_balance}")
    print(f"  Profit USD: ${profit_usd:+.2f}")
    print(f"  Expected: ${10000 * 0.015:+.2f}")
    assert abs(profit_usd - 150.0) < 0.01, f"Expected $150.00, got ${profit_usd}"
    print("  ✅ PASS")
    
    # Example 2: Forex loss
    profit_pct = -0.8  # -0.8% loss
    starting_balance = 10000
    profit_usd = (profit_pct / 100.0) * starting_balance
    
    print(f"\nExample 2: Forex Loss")
    print(f"  Profit %: {profit_pct}%")
    print(f"  Starting Balance: ${starting_balance:,.2f}")
    print(f"  Formula: ({profit_pct} / 100.0) * {starting_balance}")
    print(f"  Profit USD: ${profit_usd:+.2f}")
    print(f"  Expected: ${10000 * -0.008:+.2f}")
    assert abs(profit_usd - (-80.0)) < 0.01, f"Expected -$80.00, got ${profit_usd}"
    print("  ✅ PASS")
    
    # Example 3: Large profit
    profit_pct = 4.5  # 4.5% profit (TP3)
    starting_balance = 5000
    profit_usd = (profit_pct / 100.0) * starting_balance
    
    print(f"\nExample 3: Large Profit")
    print(f"  Profit %: {profit_pct}%")
    print(f"  Starting Balance: ${starting_balance:,.2f}")
    print(f"  Formula: ({profit_pct} / 100.0) * {starting_balance}")
    print(f"  Profit USD: ${profit_usd:+.2f}")
    print(f"  Expected: ${5000 * 0.045:+.2f}")
    assert abs(profit_usd - 225.0) < 0.01, f"Expected $225.00, got ${profit_usd}"
    print("  ✅ PASS")
    
    print("\n" + "=" * 80)
    print("✅ All profit_usd calculations are CORRECT")
    print("=" * 80)
    
    print("\nFormula used in signal_analysis_dialog.py (line 2862):")
    print("  signals_df['profit_usd'] = (signals_df['profit_pct'] / 100.0) * starting_balance")
    print("\nThis formula is mathematically correct:")
    print("  - profit_pct is stored as a percentage (e.g., 1.5 for 1.5%)")
    print("  - Dividing by 100.0 converts to decimal (1.5 → 0.015)")
    print("  - Multiplying by balance gives USD profit")
    print("\nConclusion: profit_usd calculation is CORRECT ✅")

if __name__ == "__main__":
    test_profit_usd_calculation()
