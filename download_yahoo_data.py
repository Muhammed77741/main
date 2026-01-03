"""
Download XAUUSD 1H data from Yahoo Finance
Alternative to MT5 if MT5 is not available
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


def download_gold_data(period_years=2, interval='1h'):
    """
    Download XAUUSD data from Yahoo Finance

    Args:
        period_years: Number of years of history (default: 2)
        interval: Data interval (1h, 1d, etc.)
    """
    print("\n" + "="*80)
    print(f"📥 DOWNLOADING GOLD DATA FROM YAHOO FINANCE")
    print("="*80)
    print(f"   Symbol: GC=F (Gold Futures)")
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
        ticker = yf.Ticker("GC=F")  # Gold Futures
        df = ticker.history(start=start_date, end=end_date, interval=interval)

        if df.empty:
            print("\n❌ No data downloaded. Trying alternative symbol...")
            # Try spot gold
            ticker = yf.Ticker("GOLD")
            df = ticker.history(start=start_date, end=end_date, interval=interval)

        if df.empty:
            print("\n❌ Failed to download data")
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
        df = df.rename(columns={'index': 'datetime', 'Datetime': 'datetime', 'Date': 'datetime'})

        # Keep only required columns
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]

        # Save to CSV
        filename = f"XAUUSD_1H_YF_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False)

        print(f"\n📊 Statistics:")
        print(f"   Total candles: {len(df)}")
        print(f"   Period: {df['datetime'].iloc[0]} - {df['datetime'].iloc[-1]}")
        print(f"   First price: {df['close'].iloc[0]:.2f}")
        print(f"   Last price: {df['close'].iloc[-1]:.2f}")
        print(f"   Min price: {df['low'].min():.2f}")
        print(f"   Max price: {df['high'].max():.2f}")

        print(f"\n✅ Data saved to: {filename}")
        print("💡 Now you can run backtest with:")
        print(f"   python smc_trading_strategy/backtest_v3_short_optimized.py --file {filename}")

        return df

    except Exception as e:
        print(f"\n❌ Error downloading data: {e}")
        print("\n💡 Alternative: You can download CSV manually from:")
        print("   1. TradingView: https://www.tradingview.com/chart/")
        print("   2. Investing.com: https://www.investing.com/commodities/gold")
        print("   3. MT5 directly")
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Download Gold data from Yahoo Finance')
    parser.add_argument('--years', type=int, default=2, help='Number of years (default: 2)')
    parser.add_argument('--interval', type=str, default='1h', help='Interval: 1h, 1d (default: 1h)')
    args = parser.parse_args()

    # Download
    df = download_gold_data(period_years=args.years, interval=args.interval)

    if df is not None:
        print("\n" + "="*80)
        print("✅ SUCCESS!")
        print("="*80)
