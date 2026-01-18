"""
Intraday Gold Data Generator
Generates realistic 1H XAUUSD data for intraday trading
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_intraday_gold_data(days=30, timeframe='1H'):
    """
    Generate realistic intraday XAUUSD data

    Args:
        days: Number of days to generate
        timeframe: '1H' or '4H'

    Returns:
        DataFrame with OHLCV data
    """
    # Hours per day based on timeframe
    if timeframe == '1H':
        candles_per_day = 24
    elif timeframe == '4H':
        candles_per_day = 6
    else:
        raise ValueError("Timeframe must be '1H' or '4H'")

    total_candles = days * candles_per_day

    # Gold intraday characteristics
    start_price = 1950.0

    # Session-based volatility (London/NY more volatile)
    session_volatility = {
        'asian': 0.0003,      # 0.03% per hour (quiet)
        'london': 0.0008,     # 0.08% per hour (active)
        'overlap': 0.0012,    # 0.12% per hour (most active)
        'ny': 0.0006,         # 0.06% per hour (moderate)
        'off': 0.0002         # 0.02% per hour (very quiet)
    }

    # Market regimes (change every 2-7 days)
    regimes = ['trend_up', 'trend_down', 'range', 'breakout']
    regime_durations = []
    current_regime_idx = 0

    # Initialize regime changes
    regime_change_days = [0]
    while regime_change_days[-1] < days:
        regime_change_days.append(
            regime_change_days[-1] + np.random.randint(2, 8)
        )

    data = []
    current_price = start_price

    start_datetime = datetime.now() - timedelta(days=days)

    for i in range(total_candles):
        # Calculate datetime
        if timeframe == '1H':
            current_time = start_datetime + timedelta(hours=i)
        else:
            current_time = start_datetime + timedelta(hours=i*4)

        # Determine session
        hour = current_time.hour
        if 0 <= hour < 7:
            session = 'asian'
        elif 7 <= hour < 12:
            session = 'london'
        elif 12 <= hour < 16:
            session = 'overlap'
        elif 16 <= hour < 20:
            session = 'ny'
        else:
            session = 'off'

        # Weekend (lower activity)
        if current_time.weekday() >= 5:
            session = 'off'

        # Determine current regime
        current_day = i // candles_per_day
        current_regime = 'range'
        for j, change_day in enumerate(regime_change_days[:-1]):
            if change_day <= current_day < regime_change_days[j+1]:
                current_regime = regimes[j % len(regimes)]
                break

        # Regime-based parameters
        if current_regime == 'trend_up':
            drift = 0.0003
            base_vol = 0.0006
        elif current_regime == 'trend_down':
            drift = -0.0003
            base_vol = 0.0006
        elif current_regime == 'range':
            drift = 0.0
            base_vol = 0.0004
        else:  # breakout
            drift = np.random.choice([0.0006, -0.0006])
            base_vol = 0.0010

        # Session volatility modifier
        volatility = base_vol + session_volatility[session]

        # Generate candle
        price_change = drift + np.random.normal(0, volatility)

        # Open
        open_price = current_price

        # Close
        close = open_price * (1 + price_change)

        # High/Low with intraday range
        intraday_range = abs(np.random.normal(0, volatility * 1.5))

        if close > open_price:  # Bullish candle
            high_offset = abs(np.random.normal(0, volatility * 0.5))
            low_offset = abs(np.random.normal(0, volatility * 0.3))

            high = close * (1 + high_offset)
            low = open_price * (1 - low_offset)
        else:  # Bearish candle
            high_offset = abs(np.random.normal(0, volatility * 0.3))
            low_offset = abs(np.random.normal(0, volatility * 0.5))

            high = open_price * (1 + high_offset)
            low = close * (1 - low_offset)

        # Ensure OHLC validity
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # Volume (higher in active sessions)
        base_volume = 10000
        if session == 'overlap':
            volume = base_volume * np.random.uniform(2.0, 4.0)
        elif session in ['london', 'ny']:
            volume = base_volume * np.random.uniform(1.2, 2.5)
        elif session == 'asian':
            volume = base_volume * np.random.uniform(0.7, 1.3)
        else:
            volume = base_volume * np.random.uniform(0.3, 0.8)

        # Add noise events (news spikes, etc) - 5% chance
        if np.random.random() < 0.05:
            spike_direction = np.random.choice([1, -1])
            spike_magnitude = abs(np.random.normal(0, volatility * 3))

            if spike_direction > 0:
                high = high * (1 + spike_magnitude)
                close = close * (1 + spike_magnitude * 0.6)
            else:
                low = low * (1 - spike_magnitude)
                close = close * (1 - spike_magnitude * 0.6)

            volume *= np.random.uniform(2.0, 5.0)

        data.append({
            'timestamp': current_time,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': int(volume),
            'session': session,
            'regime': current_regime
        })

        current_price = close

        # Mean reversion (keep price in realistic range)
        if current_price > 2200:
            current_price = 2200 - abs(np.random.normal(0, 10))
        elif current_price < 1700:
            current_price = 1700 + abs(np.random.normal(0, 10))

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)

    # Validate OHLC
    invalid_rows = []
    for i in range(len(df)):
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        open_price = df['open'].iloc[i]
        close = df['close'].iloc[i]

        if high < max(open_price, close) or low > min(open_price, close):
            invalid_rows.append(i)

    if invalid_rows:
        print(f"⚠️  Warning: {len(invalid_rows)} invalid OHLC rows detected and fixed")
        for i in invalid_rows:
            df.loc[df.index[i], 'high'] = max(
                df['high'].iloc[i],
                df['open'].iloc[i],
                df['close'].iloc[i]
            )
            df.loc[df.index[i], 'low'] = min(
                df['low'].iloc[i],
                df['open'].iloc[i],
                df['close'].iloc[i]
            )

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
    print("Generating intraday gold data (1H)...")

    # Generate 30 days of 1H data
    df = generate_intraday_gold_data(days=30, timeframe='1H')
    df = add_market_hours_info(df)

    print(f"\n✅ Generated {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"   Avg hourly range: ${(df['high'] - df['low']).mean():.2f}")
    print(f"   Avg hourly volatility: {((df['high'] - df['low']) / df['close'] * 100).mean():.3f}%")

    print("\nSession distribution:")
    print(df['session'].value_counts())

    print("\nRegime distribution:")
    print(df['regime'].value_counts())

    # Save sample
    df.to_csv('intraday_gold_sample.csv')
    print("\n💾 Saved to 'intraday_gold_sample.csv'")
