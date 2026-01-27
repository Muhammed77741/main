#!/usr/bin/env python3
"""
Test script to verify the negative SL fix
Tests that pattern signals correctly reject invalid entry prices
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add trading_bots to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_bots'))

from shared.pattern_recognition_strategy import PatternRecognitionStrategy


def test_invalid_entry_prices():
    """Test that invalid entry prices are rejected"""
    print("Testing invalid entry prices...")
    
    # Create strategy with best_hours_only=False to avoid time filtering
    strategy = PatternRecognitionStrategy(best_hours_only=False)
    
    # Create a minimal dataframe
    df = pd.DataFrame({
        'open': [100.0] * 100,
        'high': [102.0] * 100,
        'low': [98.0] * 100,
        'close': [101.0] * 100,
        'volume': [1000] * 100,
        'is_active_session': [True] * 100,
        'signal': [0] * 100,
        'entry_price': [0.0] * 100,
        'stop_loss': [0.0] * 100,
        'take_profit': [0.0] * 100,
        'signal_type': [''] * 100,
    })
    df.index = pd.date_range('2024-01-01 10:00', periods=100, freq='h')  # Use active hours
    
    # Test 1: Valid pattern with positive values
    print("\nTest 1: Valid pattern with positive entry")
    pattern_valid = {
        'type': 'bull_flag',
        'direction': 1,
        'entry': 100.0,
        'support': 95.0,
        'resistance': 105.0
    }
    df_result, success = strategy._add_pattern_signal(df.copy(), 50, pattern_valid, 'bull_flag')
    assert success == True, "Valid pattern should succeed"
    assert df_result.loc[df_result.index[50], 'stop_loss'] > 0, "SL should be positive"
    print(f"✅ Valid pattern accepted. Entry: {pattern_valid['entry']}, SL: {df_result.loc[df_result.index[50], 'stop_loss']:.2f}")
    
    # Test 2: Invalid pattern with zero entry
    print("\nTest 2: Invalid pattern with zero entry")
    pattern_zero = {
        'type': 'bull_flag',
        'direction': 1,
        'entry': 0.0,
        'support': 95.0,
        'resistance': 105.0
    }
    df_result, success = strategy._add_pattern_signal(df.copy(), 50, pattern_zero, 'bull_flag')
    assert success == False, "Zero entry should be rejected"
    print(f"✅ Zero entry correctly rejected")
    
    # Test 3: Invalid pattern with negative entry
    print("\nTest 3: Invalid pattern with negative entry")
    pattern_negative = {
        'type': 'bull_flag',
        'direction': 1,
        'entry': -100.0,
        'support': 95.0,
        'resistance': 105.0
    }
    df_result, success = strategy._add_pattern_signal(df.copy(), 50, pattern_negative, 'bull_flag')
    assert success == False, "Negative entry should be rejected"
    print(f"✅ Negative entry correctly rejected")
    
    # Test 4: Pattern with None entry
    print("\nTest 4: Invalid pattern with None entry")
    pattern_none = {
        'type': 'bull_flag',
        'direction': 1,
        'entry': None,
        'support': 95.0,
        'resistance': 105.0
    }
    df_result, success = strategy._add_pattern_signal(df.copy(), 50, pattern_none, 'bull_flag')
    assert success == False, "None entry should be rejected"
    print(f"✅ None entry correctly rejected")
    
    # Test 5: SHORT pattern with valid values
    print("\nTest 5: Valid SHORT pattern with positive entry")
    pattern_short = {
        'type': 'bear_flag',
        'direction': -1,
        'entry': 100.0,
        'support': 95.0,
        'resistance': 105.0
    }
    df_result, success = strategy._add_pattern_signal(df.copy(), 50, pattern_short, 'bear_flag')
    assert success == True, "Valid SHORT pattern should succeed"
    assert df_result.loc[df_result.index[50], 'stop_loss'] > 0, "SL should be positive for SHORT"
    print(f"✅ Valid SHORT pattern accepted. Entry: {pattern_short['entry']}, SL: {df_result.loc[df_result.index[50], 'stop_loss']:.2f}")
    
    # Test 6: SHORT pattern with negative support/resistance values
    print("\nTest 6: SHORT pattern with zero/negative support values")
    pattern_short_bad = {
        'type': 'bear_flag',
        'direction': -1,
        'entry': 100.0,
        'support': 0.0,  # Invalid
        'resistance': -10.0  # Invalid
    }
    df_result, success = strategy._add_pattern_signal(df.copy(), 50, pattern_short_bad, 'bear_flag')
    # Should still work because it falls back to entry * 1.005
    assert success == True, "Should fallback to entry-based SL"
    assert df_result.loc[df_result.index[50], 'stop_loss'] > 0, "Fallback SL should be positive"
    assert df_result.loc[df_result.index[50], 'stop_loss'] == 100.0 * 1.005, "Should use fallback SL"
    print(f"✅ Correctly used fallback SL: {df_result.loc[df_result.index[50], 'stop_loss']:.2f}")
    
    print("\n" + "="*60)
    print("✅ All tests passed! Negative SL fix is working correctly")
    print("="*60)


if __name__ == "__main__":
    try:
        test_invalid_entry_prices()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
