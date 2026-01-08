"""
Generate realistic XAUUSD (Gold) data based on actual market characteristics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_realistic_gold_data(days=365):
    """
    Generate realistic XAUUSD data with proper market characteristics

    Gold characteristics:
    - Price range: ~1800-2100 USD/oz typically
    - Daily volatility: ~0.5-1.5%
    - Trending behavior with ranges
    - Higher volume on breakouts
    """

    # Starting values (typical gold prices)
    start_price = 1950.0  # USD per oz
    current_price = start_price

    # Generate timestamps (daily)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')

    data = []

    # Market regime (trending vs ranging)
    regime_length = 30  # days
    current_regime = np.random.choice(['trend_up', 'trend_down', 'range'])
    regime_counter = 0

    for i, date in enumerate(dates):
        # Change regime periodically
        regime_counter += 1
        if regime_counter >= regime_length:
            current_regime = np.random.choice(['trend_up', 'trend_down', 'range'],
                                             p=[0.3, 0.3, 0.4])
            regime_counter = 0
            regime_length = np.random.randint(20, 50)

        # Set drift based on regime
        if current_regime == 'trend_up':
            drift = 0.002  # 0.2% daily upward drift
            volatility = 0.012  # 1.2% daily volatility
        elif current_regime == 'trend_down':
            drift = -0.002  # 0.2% daily downward drift
            volatility = 0.012
        else:  # ranging
            drift = 0.0
            volatility = 0.008  # 0.8% volatility in range

        # Add some noise to make it realistic
        actual_drift = drift + np.random.normal(0, 0.001)
        actual_volatility = volatility * np.random.uniform(0.8, 1.2)

        # Calculate daily move
        daily_return = np.random.normal(actual_drift, actual_volatility)
        current_price *= (1 + daily_return)

        # Keep price in realistic range (1700-2200)
        current_price = max(1700, min(2200, current_price))

        # Generate OHLC
        # Intraday volatility ~0.3-0.8%
        intraday_range_pct = np.random.uniform(0.003, 0.008)

        # Open price (with small gap)
        gap = np.random.normal(0, 0.002)
        open_price = current_price * (1 + gap)

        # Close price
        close = current_price * (1 + np.random.normal(0, 0.001))

        # High and low based on direction
        if close > open_price:  # Bullish day
            high = max(open_price, close) * (1 + abs(np.random.normal(0, intraday_range_pct/2)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, intraday_range_pct/2)))
        else:  # Bearish day
            high = max(open_price, close) * (1 + abs(np.random.normal(0, intraday_range_pct/2)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, intraday_range_pct/2)))

        # Ensure OHLC relationships
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # Volume (higher on breakouts and trend days)
        base_volume = 100000
        volume_multiplier = 1.0

        # Higher volume on big moves
        if abs(daily_return) > 0.015:  # 1.5% move
            volume_multiplier = 2.0
        elif abs(daily_return) > 0.010:  # 1% move
            volume_multiplier = 1.5

        # Higher volume in trends
        if current_regime in ['trend_up', 'trend_down']:
            volume_multiplier *= 1.3

        volume = base_volume * volume_multiplier * np.random.uniform(0.7, 1.3)

        data.append({
            'timestamp': date,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': int(volume)
        })

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)

    return df


def generate_realistic_bitcoin_data(days=365):
    """Generate realistic Bitcoin data"""
    start_price = 45000.0
    current_price = start_price

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')

    data = []

    # BTC is more volatile than gold
    regime_length = 20
    current_regime = np.random.choice(['bull', 'bear', 'range'])
    regime_counter = 0

    for i, date in enumerate(dates):
        regime_counter += 1
        if regime_counter >= regime_length:
            current_regime = np.random.choice(['bull', 'bear', 'range'],
                                             p=[0.35, 0.25, 0.4])
            regime_counter = 0
            regime_length = np.random.randint(15, 40)

        if current_regime == 'bull':
            drift = 0.005  # 0.5% daily
            volatility = 0.03  # 3% volatility
        elif current_regime == 'bear':
            drift = -0.003
            volatility = 0.035
        else:
            drift = 0.0
            volatility = 0.02

        daily_return = np.random.normal(drift, volatility)
        current_price *= (1 + daily_return)
        current_price = max(20000, min(70000, current_price))

        # Generate OHLC
        intraday_range_pct = np.random.uniform(0.01, 0.03)
        open_price = current_price * (1 + np.random.normal(0, 0.005))
        close = current_price * (1 + np.random.normal(0, 0.003))

        if close > open_price:
            high = max(open_price, close) * (1 + abs(np.random.normal(0, intraday_range_pct/2)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, intraday_range_pct/2)))
        else:
            high = max(open_price, close) * (1 + abs(np.random.normal(0, intraday_range_pct/2)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, intraday_range_pct/2)))

        high = max(high, open_price, close)
        low = min(low, open_price, close)

        base_volume = 5000000
        volume_multiplier = 1.0
        if abs(daily_return) > 0.03:
            volume_multiplier = 2.5
        elif abs(daily_return) > 0.02:
            volume_multiplier = 1.8

        volume = base_volume * volume_multiplier * np.random.uniform(0.5, 1.5)

        data.append({
            'timestamp': date,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': int(volume)
        })

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df
