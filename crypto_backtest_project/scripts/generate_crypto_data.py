"""
Generate sample crypto data for backtesting
This creates realistic-looking crypto price data based on random walk with volatility
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_crypto_data(symbol, start_date, end_date, initial_price, volatility=0.03):
    """
    Generate realistic crypto price data
    
    Args:
        symbol: Crypto symbol (BTC, ETH)
        start_date: Start datetime
        end_date: End datetime
        initial_price: Starting price
        volatility: Daily volatility (default 3%)
    """
    print(f"\n📊 Generating {symbol} data...")
    print(f"   Period: {start_date} to {end_date}")
    print(f"   Initial price: ${initial_price:,.2f}")
    
    # Generate hourly timestamps
    timestamps = []
    current = start_date
    while current <= end_date:
        timestamps.append(current)
        current += timedelta(hours=1)
    
    num_candles = len(timestamps)
    print(f"   Candles: {num_candles}")
    
    # Generate price data using geometric brownian motion
    np.random.seed(42 if symbol == 'BTC' else 43)
    
    # Generate returns
    returns = np.random.normal(0, volatility/np.sqrt(24), num_candles)  # Hourly volatility
    
    # Add trend component
    trend = np.linspace(0, 0.5, num_candles)  # Upward trend over period
    returns += trend / num_candles
    
    # Calculate prices
    prices = initial_price * np.exp(np.cumsum(returns))
    
    # Generate OHLC data
    data = []
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        # Generate realistic OHLC
        volatility_factor = np.random.uniform(0.003, 0.01)  # 0.3-1% intra-candle movement
        
        high = close * (1 + volatility_factor * np.random.uniform(0.5, 1.0))
        low = close * (1 - volatility_factor * np.random.uniform(0.5, 1.0))
        
        if i == 0:
            open_price = initial_price
        else:
            open_price = data[-1]['close']
        
        # Ensure high is highest and low is lowest
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Generate volume (crypto has varying volume)
        base_volume = 1000000 if symbol == 'BTC' else 500000
        volume = base_volume * np.random.uniform(0.5, 2.0)
        
        data.append({
            'datetime': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    
    print(f"   Price range: ${df['low'].min():,.2f} - ${df['high'].max():,.2f}")
    print(f"   Final price: ${df['close'].iloc[-1]:,.2f}")
    print(f"   Total return: {((df['close'].iloc[-1] - initial_price) / initial_price * 100):+.2f}%")
    
    return df


def generate_btc_eth_data(years=2):
    """Generate both BTC and ETH data"""
    print("\n" + "="*80)
    print("📊 GENERATING CRYPTO DATA FOR BACKTESTING")
    print("="*80)
    
    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years*365)
    
    # Bitcoin - starting around $40,000
    btc_df = generate_crypto_data('BTC', start_date, end_date, 40000, volatility=0.04)
    btc_filename = f"BTC_1h_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    btc_df.to_csv(btc_filename, index=False)
    print(f"\n✅ BTC data saved to: {btc_filename}")
    
    # Ethereum - starting around $2,200
    eth_df = generate_crypto_data('ETH', start_date, end_date, 2200, volatility=0.05)
    eth_filename = f"ETH_1h_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    eth_df.to_csv(eth_filename, index=False)
    print(f"✅ ETH data saved to: {eth_filename}")
    
    return {
        'BTC': (btc_df, btc_filename),
        'ETH': (eth_df, eth_filename)
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate sample crypto data')
    parser.add_argument('--years', type=int, default=2, help='Number of years (default: 2)')
    args = parser.parse_args()
    
    results = generate_btc_eth_data(args.years)
    
    print("\n" + "="*80)
    print("✅ SUCCESS!")
    print("="*80)
    print("\n💡 Now you can run backtest with:")
    for crypto, (df, filename) in results.items():
        print(f"   python crypto_backtest_v3.py --file {filename}")
