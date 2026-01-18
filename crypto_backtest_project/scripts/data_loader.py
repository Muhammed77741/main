"""
Data loader for backtesting
Supports loading data from CSV or downloading from Yahoo Finance
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


def generate_sample_data(
    days: int = 365,
    start_price: float = 50000,
    volatility: float = 0.02
) -> pd.DataFrame:
    """
    Generate sample OHLC data for testing

    Args:
        days: Number of days to generate
        start_price: Starting price
        volatility: Daily volatility

    Returns:
        DataFrame with OHLC data
    """
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    data = []
    current_price = start_price

    for date in dates:
        # Random walk with drift
        daily_return = np.random.normal(0.0005, volatility)
        current_price *= (1 + daily_return)

        # Generate OHLC with correct relationships
        open_price = current_price * (1 + np.random.normal(0, volatility/4))
        close = current_price * (1 + np.random.normal(0, volatility/4))

        # Ensure high is max and low is min
        high_offset = abs(np.random.normal(0, volatility/2))
        low_offset = abs(np.random.normal(0, volatility/2))

        high = max(open_price, close) * (1 + high_offset)
        low = min(open_price, close) * (1 - low_offset)

        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.uniform(1000, 10000)
        })

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


def load_data_from_csv(file_path: str) -> pd.DataFrame:
    """
    Load OHLC data from CSV file

    Args:
        file_path: Path to CSV file

    Returns:
        DataFrame with OHLC data
    """
    df = pd.read_csv(file_path)

    # Try to identify timestamp column
    timestamp_cols = ['timestamp', 'date', 'time', 'datetime']
    timestamp_col = None

    for col in timestamp_cols:
        if col in df.columns:
            timestamp_col = col
            break

    if timestamp_col:
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df.set_index(timestamp_col, inplace=True)

    # Ensure required columns exist
    required_cols = ['open', 'high', 'low', 'close']
    for col in required_cols:
        if col not in df.columns and col.upper() in df.columns:
            df[col] = df[col.upper()]

    return df[required_cols]


def download_data_yfinance(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = '1y'
) -> pd.DataFrame:
    """
    Download data from Yahoo Finance

    Args:
        symbol: Ticker symbol (e.g., 'BTC-USD', 'AAPL')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        period: Period if start/end not specified (e.g., '1y', '6mo')

    Returns:
        DataFrame with OHLC data
    """
    try:
        import yfinance as yf

        if start_date and end_date:
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        else:
            data = yf.download(symbol, period=period, progress=False)

        # Rename columns to lowercase
        data.columns = [col.lower() for col in data.columns]

        return data[['open', 'high', 'low', 'close', 'volume']]

    except ImportError:
        print("yfinance not installed. Install with: pip install yfinance")
        return None
    except Exception as e:
        print(f"Error downloading data: {e}")
        return None


def validate_data(df: pd.DataFrame) -> bool:
    """
    Validate OHLC data

    Args:
        df: DataFrame to validate

    Returns:
        True if valid, False otherwise
    """
    required_cols = ['open', 'high', 'low', 'close']

    # Check required columns
    for col in required_cols:
        if col not in df.columns:
            print(f"Missing required column: {col}")
            return False

    # Check for NaN values
    if df[required_cols].isna().any().any():
        print("Data contains NaN values")
        return False

    # Check OHLC relationships
    invalid_rows = (
        (df['high'] < df['low']) |
        (df['high'] < df['open']) |
        (df['high'] < df['close']) |
        (df['low'] > df['open']) |
        (df['low'] > df['close'])
    )

    if invalid_rows.any():
        print(f"Invalid OHLC relationships in {invalid_rows.sum()} rows")
        return False

    return True
