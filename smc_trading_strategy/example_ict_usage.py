"""
Example: How to use the ICT Price Action Strategy
This script demonstrates basic usage of the ICT strategy
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ict_price_action_strategy import ICTPriceActionStrategy


def create_sample_data():
    """Create sample OHLC data for demonstration"""
    import numpy as np
    from datetime import datetime, timedelta
    
    # Create 1000 candles of sample data
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(hours=i) for i in range(1000)]
    
    # Simulate price movement
    price = 2000
    data = []
    
    for date in dates:
        open_price = price
        high_price = price + np.random.uniform(5, 20)
        low_price = price - np.random.uniform(5, 20)
        close_price = price + np.random.uniform(-10, 10)
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'tick_volume': volume,
            'spread': 0
        })
        
        price = close_price
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    return df


def main():
    """Demonstrate ICT strategy usage"""
    
    print("="*60)
    print("ICT PRICE ACTION STRATEGY - USAGE EXAMPLE")
    print("="*60)
    
    # 1. Create or load your OHLC data
    print("\n1. Loading sample data...")
    df = create_sample_data()
    print(f"   Loaded {len(df)} candles")
    
    # 2. Initialize the strategy
    print("\n2. Initializing ICT Strategy...")
    strategy = ICTPriceActionStrategy(
        risk_reward_ratio=2.0,      # 1:2 risk/reward
        risk_per_trade=0.02,        # 2% risk per trade
        swing_length=10,            # 10 candles for swing detection
        fvg_threshold=0.001,        # 0.1% minimum gap for FVG
        liquidity_lookback=20,      # Look back 20 candles for liquidity
        use_kill_zones=True         # Only trade in kill zones
    )
    print("   ✓ Strategy initialized")
    
    # 3. Generate signals
    print("\n3. Generating ICT signals...")
    df_with_signals = strategy.generate_signals(df)
    
    # Count signals
    long_signals = (df_with_signals['signal'] == 1).sum()
    short_signals = (df_with_signals['signal'] == -1).sum()
    total_signals = long_signals + short_signals
    
    print(f"   ✓ Generated {total_signals} signals")
    print(f"     - Long signals: {long_signals}")
    print(f"     - Short signals: {short_signals}")
    
    # 4. Show ICT indicators detected
    print("\n4. ICT Indicators Detected:")
    print(f"   - Liquidity Sweeps (Bullish): {df_with_signals['bullish_liquidity_sweep'].sum()}")
    print(f"   - Liquidity Sweeps (Bearish): {df_with_signals['bearish_liquidity_sweep'].sum()}")
    print(f"   - Order Blocks (Bullish): {df_with_signals['bullish_ob'].sum()}")
    print(f"   - Order Blocks (Bearish): {df_with_signals['bearish_ob'].sum()}")
    print(f"   - Fair Value Gaps (Bullish): {df_with_signals['bullish_fvg'].sum()}")
    print(f"   - Fair Value Gaps (Bearish): {df_with_signals['bearish_fvg'].sum()}")
    print(f"   - Market Structure Shifts (Bullish): {df_with_signals['bullish_mss'].sum()}")
    print(f"   - Market Structure Shifts (Bearish): {df_with_signals['bearish_mss'].sum()}")
    
    # 5. Example: Get entry parameters for first signal
    if total_signals > 0:
        print("\n5. Example Entry Parameters:")
        
        # Find first signal
        signal_indices = df_with_signals[df_with_signals['signal'] != 0].index
        first_signal_idx = df_with_signals.index.get_loc(signal_indices[0])
        
        # Get entry parameters
        account_balance = 10000
        entry_params = strategy.get_entry_parameters(
            df_with_signals, 
            first_signal_idx, 
            account_balance
        )
        
        if entry_params:
            direction = "LONG" if entry_params['signal'] == 1 else "SHORT"
            print(f"\n   First Signal: {direction}")
            print(f"   Entry Price:    ${entry_params['entry_price']:.2f}")
            print(f"   Stop Loss:      ${entry_params['stop_loss']:.2f}")
            print(f"   Take Profit:    ${entry_params['take_profit']:.2f}")
            print(f"   Position Size:  {entry_params['position_size']:.2f}")
            print(f"   Entry Reason:   {entry_params['entry_reason']}")
            
            # Calculate risk/reward
            if entry_params['signal'] == 1:
                risk = entry_params['entry_price'] - entry_params['stop_loss']
                reward = entry_params['take_profit'] - entry_params['entry_price']
            else:
                risk = entry_params['stop_loss'] - entry_params['entry_price']
                reward = entry_params['entry_price'] - entry_params['take_profit']
            
            rr_ratio = reward / risk if risk > 0 else 0
            print(f"   Risk:           ${risk:.2f}")
            print(f"   Reward:         ${reward:.2f}")
            print(f"   R/R Ratio:      1:{rr_ratio:.2f}")
    
    print("\n" + "="*60)
    print("✅ Example completed!")
    print("\nNext steps:")
    print("  - Use backtest_ict_strategy.py to backtest on real data")
    print("  - Adjust parameters to optimize for your market")
    print("  - Integrate with your trading platform")
    print("="*60)


if __name__ == '__main__':
    main()
