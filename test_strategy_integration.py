#!/usr/bin/env python3
"""
Integration test to verify pattern strategy still works after SL validation fix
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add trading_bots to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_bots'))

from shared.pattern_recognition_strategy import PatternRecognitionStrategy


def create_sample_data():
    """Create sample OHLCV data with patterns"""
    np.random.seed(42)
    n = 200
    
    # Generate realistic price action
    base_price = 2000.0
    prices = []
    current = base_price
    
    for i in range(n):
        # Random walk with trend
        change = np.random.randn() * 5 + 0.1  # Slight uptrend
        current += change
        prices.append(current)
    
    # Create OHLC from prices
    df = pd.DataFrame()
    for i in range(n):
        noise = np.random.rand() * 2
        df.loc[i, 'close'] = prices[i]
        df.loc[i, 'open'] = prices[i] - noise
        df.loc[i, 'high'] = max(prices[i], prices[i] - noise) + noise
        df.loc[i, 'low'] = min(prices[i], prices[i] - noise) - noise
        df.loc[i, 'volume'] = 1000 + np.random.randint(0, 500)
    
    # Create datetime index
    df.index = pd.date_range('2024-01-01 08:00', periods=n, freq='h')
    
    # Add session filter (all active for simplicity)
    df['is_active_session'] = True
    
    return df


def test_pattern_strategy_integration():
    """Test that pattern strategy works correctly with our fixes"""
    print("\n" + "="*80)
    print("🧪 PATTERN STRATEGY INTEGRATION TEST")
    print("="*80)
    
    # Create sample data
    print("\n1️⃣  Creating sample price data...")
    df = create_sample_data()
    print(f"   ✅ Created {len(df)} candles")
    print(f"   Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
    
    # Test 1: Standard Fibonacci mode
    print("\n2️⃣  Testing strategy with standard Fibonacci mode...")
    strategy = PatternRecognitionStrategy(
        fib_mode='standard',
        best_hours_only=False
    )
    df_result = strategy.run_strategy(df.copy())
    signals = df_result[df_result['signal'] != 0]
    
    print(f"   ✅ Strategy executed successfully")
    print(f"   Signals found: {len(signals)}")
    
    # Verify all signals have valid SL/TP
    if len(signals) > 0:
        print("\n3️⃣  Validating signal quality...")
        
        all_valid = True
        for idx, row in signals.iterrows():
            entry = row['entry_price']
            sl = row['stop_loss']
            tp = row['take_profit']
            signal_type = row['signal']
            
            # Check SL is positive
            if sl <= 0:
                print(f"   ❌ Invalid SL (negative/zero) at {idx}: ${sl:.2f}")
                all_valid = False
                continue
                
            # Check TP is positive
            if tp <= 0:
                print(f"   ❌ Invalid TP (negative/zero) at {idx}: ${tp:.2f}")
                all_valid = False
                continue
            
            # Check SL is on correct side of entry
            if signal_type == 1:  # LONG
                if sl >= entry:
                    print(f"   ❌ Invalid LONG SL at {idx}: SL ${sl:.2f} >= Entry ${entry:.2f}")
                    all_valid = False
                if tp <= entry:
                    print(f"   ❌ Invalid LONG TP at {idx}: TP ${tp:.2f} <= Entry ${entry:.2f}")
                    all_valid = False
            else:  # SHORT
                if sl <= entry:
                    print(f"   ❌ Invalid SHORT SL at {idx}: SL ${sl:.2f} <= Entry ${entry:.2f}")
                    all_valid = False
                if tp >= entry:
                    print(f"   ❌ Invalid SHORT TP at {idx}: TP ${tp:.2f} >= Entry ${entry:.2f}")
                    all_valid = False
        
        if all_valid:
            print(f"   ✅ All {len(signals)} signals have valid SL/TP values")
            print("\n   Sample signals:")
            for idx, row in signals.head(3).iterrows():
                direction = "LONG" if row['signal'] == 1 else "SHORT"
                print(f"   {idx.strftime('%Y-%m-%d %H:%M')}: {direction}")
                print(f"      Entry: ${row['entry_price']:.2f}")
                print(f"      SL: ${row['stop_loss']:.2f}")
                print(f"      TP: ${row['take_profit']:.2f}")
        else:
            print(f"   ❌ Some signals have invalid SL/TP values")
            return False
    else:
        print(f"   ⚠️  No signals generated (this is OK, depends on random data)")
    
    # Test 2: Extension mode
    print("\n4️⃣  Testing strategy with 1.618 extension mode...")
    strategy_ext = PatternRecognitionStrategy(
        fib_mode='extension_1.618',
        best_hours_only=False
    )
    df_result_ext = strategy_ext.run_strategy(df.copy())
    signals_ext = df_result_ext[df_result_ext['signal'] != 0]
    
    print(f"   ✅ Extension mode executed successfully")
    print(f"   Signals found: {len(signals_ext)}")
    
    # Test 3: Verify no negative SL in any mode
    print("\n5️⃣  Final validation: No negative SL values...")
    all_sl_values = []
    
    for test_df in [df_result, df_result_ext]:
        test_signals = test_df[test_df['signal'] != 0]
        if len(test_signals) > 0:
            all_sl_values.extend(test_signals['stop_loss'].tolist())
    
    if all_sl_values:
        min_sl = min(all_sl_values)
        max_sl = max(all_sl_values)
        
        if min_sl > 0:
            print(f"   ✅ All SL values are positive")
            print(f"   SL range: ${min_sl:.2f} - ${max_sl:.2f}")
        else:
            print(f"   ❌ Found negative SL: ${min_sl:.2f}")
            return False
    else:
        print(f"   ⚠️  No signals to validate (OK for random data)")
    
    print("\n" + "="*80)
    print("✅ INTEGRATION TEST PASSED!")
    print("="*80)
    return True


if __name__ == "__main__":
    try:
        success = test_pattern_strategy_integration()
        if not success:
            print("\n❌ Integration test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during integration test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
