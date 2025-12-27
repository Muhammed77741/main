"""
Real Market Data Loader for XAUUSD
Downloads real historical data from Yahoo Finance using direct API
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time


def download_gold_data_yahoo_api(start_date, end_date, interval='1h'):
    """
    Download real XAUUSD data using direct Yahoo Finance API
    (without yfinance library to avoid dependency issues)

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: '1h', '1d', etc.

    Returns:
        DataFrame with OHLCV data
    """
    print(f"📥 Downloading real XAUUSD data from Yahoo Finance API...")
    print(f"   Period: {start_date} to {end_date}")
    print(f"   Interval: {interval}")

    # Convert dates to timestamps
    start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
    end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())

    # XAUUSD can be accessed via Gold Futures (GC=F) or try different tickers
    tickers_to_try = [
        'GC=F',     # Gold Futures - most reliable
        'GOLD',     # Some platforms
    ]

    df = None
    ticker_used = None

    for ticker in tickers_to_try:
        try:
            print(f"\n   Trying ticker: {ticker}...")

            # Yahoo Finance API URL
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

            params = {
                'period1': start_ts,
                'period2': end_ts,
                'interval': interval,
                'includePrePost': 'false',
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                print(f"   ❌ HTTP {response.status_code}")
                continue

            data = response.json()

            if 'chart' not in data or 'result' not in data['chart']:
                print(f"   ❌ Invalid response format")
                continue

            result = data['chart']['result']
            if not result or len(result) == 0:
                print(f"   ❌ No data in response")
                continue

            quote_data = result[0]

            # Extract timestamps and OHLCV data
            timestamps = quote_data['timestamp']
            quote = quote_data['indicators']['quote'][0]

            # Create DataFrame
            df = pd.DataFrame({
                'timestamp': [datetime.fromtimestamp(ts) for ts in timestamps],
                'open': quote['open'],
                'high': quote['high'],
                'low': quote['low'],
                'close': quote['close'],
                'volume': quote['volume'],
            })

            # Remove NaN rows
            df = df.dropna()

            if len(df) > 0:
                ticker_used = ticker
                print(f"   ✅ Success with {ticker}! Downloaded {len(df)} candles")
                break
            else:
                print(f"   ❌ No valid data for {ticker}")

        except Exception as e:
            print(f"   ❌ Error with {ticker}: {str(e)[:80]}")
            continue

        # Small delay between retries
        time.sleep(0.5)

    if df is None or len(df) == 0:
        raise ValueError("Failed to download data from all tickers")

    # Clean and format data
    df = df.copy()

    # Standardize column names
    df.columns = [col.lower() for col in df.columns]

    # Ensure required columns exist
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Reset index to have timestamp as column
    df = df.reset_index()
    if 'datetime' in df.columns:
        df.rename(columns={'datetime': 'timestamp'}, inplace=True)
    elif 'date' in df.columns:
        df.rename(columns={'date': 'timestamp'}, inplace=True)

    # Set timestamp as index
    df.set_index('timestamp', inplace=True)

    # Remove any NaN values
    df = df.dropna()

    # Validate OHLC
    invalid_count = 0
    for i in range(len(df)):
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        open_price = df['open'].iloc[i]
        close = df['close'].iloc[i]

        if high < max(open_price, close) or low > min(open_price, close):
            df.loc[df.index[i], 'high'] = max(high, open_price, close)
            df.loc[df.index[i], 'low'] = min(low, open_price, close)
            invalid_count += 1

    if invalid_count > 0:
        print(f"   ⚠️  Fixed {invalid_count} invalid OHLC rows")

    print(f"\n✅ Downloaded {len(df)} candles from {ticker_used}")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    return df


def download_gold_data_alternative(start_date, end_date, interval='1h'):
    """
    Alternative: Try downloading from other free sources
    """
    # Use Yahoo API as primary method
    return download_gold_data_yahoo_api(start_date, end_date, interval)


def load_real_gold_data(year=2025, interval='1h'):
    """
    Load real XAUUSD data for a specific year

    Args:
        year: Year to load (default 2025)
        interval: '1h' or '4h'

    Returns:
        DataFrame with OHLCV data
    """
    # For 2025, we can only get data up to current date
    start_date = f"{year}-01-01"

    # Check if year is current or future
    current_year = datetime.now().year
    if year >= current_year:
        # Use current date as end
        end_date = datetime.now().strftime('%Y-%m-%d')
    else:
        # Use end of year
        end_date = f"{year}-12-31"

    df = download_gold_data_yahoo_api(start_date, end_date, interval)

    # Add market session info
    df = add_market_hours_info(df)

    return df


def add_market_hours_info(df):
    """Add market hours and session quality info"""
    df = df.copy()

    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']

    # Best hours for gold intraday
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


if __name__ == "__main__":
    print("=" * 60)
    print("REAL GOLD DATA LOADER - XAUUSD")
    print("=" * 60)

    # Test download for 2024 (full year available)
    print("\n📊 Testing download for 2024...")
    df_2024 = load_real_gold_data(year=2024, interval='1h')

    print(f"\n📈 Data Summary:")
    print(f"   Candles: {len(df_2024)}")
    print(f"   Period: {df_2024.index[0]} to {df_2024.index[-1]}")
    print(f"   Price range: ${df_2024['close'].min():.2f} - ${df_2024['close'].max():.2f}")
    print(f"   Avg hourly range: ${(df_2024['high'] - df_2024['low']).mean():.2f}")
    print(f"   Avg hourly vol: {((df_2024['high'] - df_2024['low']) / df_2024['close'] * 100).mean():.3f}%")

    # Save sample
    df_2024.to_csv('real_gold_data_2024.csv')
    print(f"\n💾 Saved to 'real_gold_data_2024.csv'")

    # Try 2025 (partial year)
    print("\n" + "=" * 60)
    print("📊 Testing download for 2025 (YTD)...")
    df_2025 = load_real_gold_data(year=2025, interval='1h')

    print(f"\n📈 Data Summary:")
    print(f"   Candles: {len(df_2025)}")
    print(f"   Period: {df_2025.index[0]} to {df_2025.index[-1]}")
    print(f"   Price range: ${df_2025['close'].min():.2f} - ${df_2025['close'].max():.2f}")
