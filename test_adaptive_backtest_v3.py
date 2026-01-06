"""
Test Adaptive Backtest V3
Simple test to validate the adaptive backtest implementation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'smc_trading_strategy'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from smc_trading_strategy.pattern_recognition_strategy import PatternRecognitionStrategy
from smc_trading_strategy.adaptive_backtest_v3 import AdaptiveBacktestV3


def generate_test_data(num_candles=500):
    """Generate synthetic test data for backtesting"""
    print("\n" + "="*80)
    print("🔧 Generating synthetic test data...")
    print("="*80)
    
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(hours=i) for i in range(num_candles)]
    
    # Generate price data with some trend
    base_price = 2000.0
    prices = []
    current_price = base_price
    
    for i in range(num_candles):
        # Add some trend and randomness
        trend = 0.1 if i % 100 < 50 else -0.1
        noise = np.random.randn() * 2
        current_price += trend + noise
        prices.append(current_price)
    
    # Create OHLCV data
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        volatility = abs(np.random.randn() * 3)
        high = price + volatility
        low = price - volatility
        open_price = price + np.random.randn() * 1
        close_price = price + np.random.randn() * 1
        volume = np.random.randint(1000, 5000)
        
        data.append({
            'datetime': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df = df.set_index('datetime')
    
    # Add session info
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_active'] = df['is_london'] | df['is_ny']
    
    print(f"   ✅ Generated {len(df)} candles")
    print(f"   Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")
    
    return df


def test_pattern_recognition_strategy():
    """Test PatternRecognitionStrategy"""
    print("\n" + "="*80)
    print("🧪 TEST 1: PatternRecognitionStrategy")
    print("="*80)
    
    df = generate_test_data(300)
    
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    df_result = strategy.run_strategy(df)
    
    signals = df_result[df_result['signal'] != 0]
    
    print(f"\n   Strategy processed {len(df_result)} candles")
    print(f"   Generated {len(signals)} signals")
    
    if len(signals) > 0:
        long_signals = len(signals[signals['signal'] == 1])
        short_signals = len(signals[signals['signal'] == -1])
        print(f"   LONG signals: {long_signals}")
        print(f"   SHORT signals: {short_signals}")
        print(f"\n   ✅ PatternRecognitionStrategy works!")
    else:
        print(f"\n   ⚠️ No signals generated (this is OK for random data)")
    
    return df_result


def test_market_regime_detection():
    """Test market regime detection"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Market Regime Detection")
    print("="*80)
    
    df = generate_test_data(200)
    backtest = AdaptiveBacktestV3()
    
    # Test regime detection at different points
    test_points = [100, 120, 140, 160, 180]
    
    print("\n   Testing regime detection at different candles:")
    for idx in test_points:
        regime = backtest.detect_market_regime(df, idx, lookback=100)
        print(f"   Candle {idx}: {regime}")
    
    print(f"\n   ✅ Market regime detection works!")


def test_adaptive_backtest():
    """Test AdaptiveBacktestV3"""
    print("\n" + "="*80)
    print("🧪 TEST 3: AdaptiveBacktestV3 Full Run")
    print("="*80)
    
    # Generate more data for backtest
    df = generate_test_data(500)
    
    # Create strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Run adaptive backtest
    backtest = AdaptiveBacktestV3(
        spread_points=2.0,
        commission_points=0.5,
        swap_per_day=-0.3
    )
    
    try:
        trades_df = backtest.backtest(df, strategy)
        
        if trades_df is not None and len(trades_df) > 0:
            print(f"\n   ✅ Backtest completed successfully!")
            print(f"   Generated {len(trades_df)} completed trades")
            
            # Show sample trades
            print(f"\n   Sample trades:")
            for i, row in trades_df.head(3).iterrows():
                print(f"   - {row['direction']} ({row['regime']}): {row['pnl_pct']:+.2f}% - Exit: {row['exit_type']}")
            
            return True
        else:
            print(f"\n   ⚠️ No trades completed (OK for synthetic data)")
            return True
            
    except Exception as e:
        print(f"\n   ❌ Error during backtest: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 ADAPTIVE BACKTEST V3 - TEST SUITE")
    print("="*80)
    
    results = []
    
    # Test 1: PatternRecognitionStrategy
    try:
        test_pattern_recognition_strategy()
        results.append(("PatternRecognitionStrategy", True))
    except Exception as e:
        print(f"\n   ❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("PatternRecognitionStrategy", False))
    
    # Test 2: Market Regime Detection
    try:
        test_market_regime_detection()
        results.append(("Market Regime Detection", True))
    except Exception as e:
        print(f"\n   ❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Market Regime Detection", False))
    
    # Test 3: Full Backtest
    try:
        success = test_adaptive_backtest()
        results.append(("AdaptiveBacktestV3", success))
    except Exception as e:
        print(f"\n   ❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("AdaptiveBacktestV3", False))
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n   🎉 ALL TESTS PASSED!")
    else:
        print("\n   ⚠️ SOME TESTS FAILED")
    
    print("="*80 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
