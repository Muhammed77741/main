"""
Download real cryptocurrency data from Binance API
Alternative to Yahoo Finance - works without SSL certificate issues
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
import sys
import os

def download_binance_data(symbol, interval='1h', days=730):
    """
    Download historical data from Binance public API
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')
        interval: Candle interval (1h, 4h, 1d, etc.)
        days: Number of days of historical data
    
    Returns:
        DataFrame with OHLCV data
    """
    print(f"\n{'='*80}")
    print(f"📥 Downloading {symbol} data from Binance...")
    print(f"{'='*80}")
    
    url = "https://api.binance.com/api/v3/klines"
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    print(f"Period: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    print(f"Interval: {interval}")
    
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': int(start_time.timestamp() * 1000),
        'endTime': int(end_time.timestamp() * 1000),
        'limit': 1000
    }
    
    all_data = []
    batch_count = 0
    
    try:
        while True:
            batch_count += 1
            print(f"\rFetching batch {batch_count}... ({len(all_data)} candles)", end='')
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or len(data) == 0:
                break
            
            all_data.extend(data)
            
            # Update start time for next batch
            params['startTime'] = data[-1][0] + 1
            
            # If we got less than requested, we've reached the end
            if len(data) < 1000:
                break
                
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error downloading data: {e}")
        return None
    
    print(f"\n✅ Downloaded {len(all_data)} candles")
    
    # Create DataFrame
    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Convert timestamp to datetime
    df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
    
    # Select and convert relevant columns
    df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
    df = df.astype({
        'open': float,
        'high': float,
        'low': float,
        'close': float,
        'volume': float
    })
    
    print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")
    print(f"First price: {df['open'].iloc[0]:.2f}")
    print(f"Last price: {df['close'].iloc[-1]:.2f}")
    print(f"Price change: {((df['close'].iloc[-1] / df['open'].iloc[0]) - 1) * 100:+.2f}%")
    
    return df

def main():
    """Download BTC and ETH data from Binance"""
    
    print("\n" + "="*80)
    print("🌐 BINANCE DATA DOWNLOADER")
    print("="*80)
    print("Downloading 2 years of hourly data for BTC and ETH...")
    
    # Download Bitcoin
    btc = download_binance_data('BTCUSDT', interval='1h', days=730)
    
    if btc is None:
        print("\n❌ Failed to download BTC data")
        sys.exit(1)
    
    # Download Ethereum
    eth = download_binance_data('ETHUSDT', interval='1h', days=730)
    
    if eth is None:
        print("\n❌ Failed to download ETH data")
        sys.exit(1)
    
    # Save to CSV
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Generate filenames with date range
    start_date = btc['datetime'].min().strftime('%Y%m%d')
    end_date = btc['datetime'].max().strftime('%Y%m%d')
    
    btc_file = os.path.join(data_dir, f'BTC_1h_{start_date}_{end_date}_real.csv')
    eth_file = os.path.join(data_dir, f'ETH_1h_{start_date}_{end_date}_real.csv')
    
    btc.to_csv(btc_file, index=False)
    eth.to_csv(eth_file, index=False)
    
    print("\n" + "="*80)
    print("✅ DATA DOWNLOAD COMPLETE")
    print("="*80)
    print(f"BTC data saved: {btc_file}")
    print(f"  - {len(btc)} candles, {btc_file.split('/')[-1]}")
    print(f"ETH data saved: {eth_file}")
    print(f"  - {len(eth)} candles, {eth_file.split('/')[-1]}")
    print("\nYou can now run backtests with real data using run_final_backtest.py")
    print("="*80)

if __name__ == "__main__":
    main()
