"""
Download Bitcoin and Ethereum data from Yahoo Finance
For backtesting crypto trading strategy based on v3 advanced backtest
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


def download_crypto_data(symbol, period_years=2, interval='1h'):
    """
    Download crypto data from Yahoo Finance

    Args:
        symbol: Crypto symbol (BTC-USD, ETH-USD)
        period_years: Number of years of history (default: 2)
        interval: Data interval (1h, 1d, etc.)
    """
    print("\n" + "="*80)
    print(f"📥 DOWNLOADING CRYPTO DATA FROM YAHOO FINANCE")
    print("="*80)
    print(f"   Symbol: {symbol}")
    print(f"   Period: {period_years} years")
    print(f"   Interval: {interval}")

    # Calculate dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_years*365)

    print(f"\n📅 Downloading data:")
    print(f"   From: {start_date.strftime('%Y-%m-%d')}")
    print(f"   To: {end_date.strftime('%Y-%m-%d')}")

    try:
        # Download data
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval=interval)

        if df.empty:
            print(f"\n❌ No data downloaded for {symbol}")
            return None

        # Rename columns to match MT5 format
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Reset index to get datetime as column
        df = df.reset_index()
        if 'index' in df.columns:
            df = df.rename(columns={'index': 'datetime'})
        elif 'Datetime' in df.columns:
            df = df.rename(columns={'Datetime': 'datetime'})
        elif 'Date' in df.columns:
            df = df.rename(columns={'Date': 'datetime'})

        # Keep only required columns
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]

        # Save to CSV
        crypto_name = symbol.split('-')[0]
        filename = f"{crypto_name}_{interval}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False)

        print(f"\n📊 Statistics:")
        print(f"   Total candles: {len(df)}")
        print(f"   Period: {df['datetime'].iloc[0]} - {df['datetime'].iloc[-1]}")
        print(f"   First price: ${df['close'].iloc[0]:.2f}")
        print(f"   Last price: ${df['close'].iloc[-1]:.2f}")
        print(f"   Min price: ${df['low'].min():.2f}")
        print(f"   Max price: ${df['high'].max():.2f}")
        print(f"   Price change: {((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100):+.2f}%")

        print(f"\n✅ Data saved to: {filename}")

        return df, filename

    except Exception as e:
        print(f"\n❌ Error downloading data: {e}")
        return None


def download_all_crypto(period_years=2, interval='1h'):
    """Download both BTC and ETH"""
    print("\n" + "="*80)
    print("📥 DOWNLOADING MULTIPLE CRYPTO ASSETS")
    print("="*80)

    results = {}
    
    # Bitcoin
    print("\n🪙 Bitcoin (BTC-USD)")
    btc_result = download_crypto_data('BTC-USD', period_years, interval)
    if btc_result:
        results['BTC'] = btc_result
    
    # Ethereum
    print("\n🪙 Ethereum (ETH-USD)")
    eth_result = download_crypto_data('ETH-USD', period_years, interval)
    if eth_result:
        results['ETH'] = eth_result

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Download Crypto data from Yahoo Finance')
    parser.add_argument('--symbol', type=str, help='Symbol: BTC-USD, ETH-USD (or leave empty for both)')
    parser.add_argument('--years', type=int, default=2, help='Number of years (default: 2)')
    parser.add_argument('--interval', type=str, default='1h', help='Interval: 1h, 1d (default: 1h)')
    args = parser.parse_args()

    if args.symbol:
        # Download single crypto
        result = download_crypto_data(args.symbol, args.years, args.interval)
        if result:
            print("\n" + "="*80)
            print("✅ SUCCESS!")
            print("="*80)
    else:
        # Download all
        results = download_all_crypto(args.years, args.interval)
        if results:
            print("\n" + "="*80)
            print(f"✅ SUCCESS! Downloaded {len(results)} crypto assets")
            print("="*80)
            print("\n💡 Now you can run backtest with:")
            for crypto, (df, filename) in results.items():
                print(f"   python crypto_backtest_v3.py --file {filename}")
