"""
Stock Data Loader - Generate realistic stock price data
Генератор реалистичных данных для акций (день/неделя)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


class StockDataLoader:
    """
    Generate realistic stock price data for backtesting
    
    Features:
    - Realistic daily/weekly price movements
    - Lower volatility compared to crypto
    - Volume patterns
    - Trend periods
    - Consolidation periods
    """
    
    def __init__(
        self,
        ticker: str = "AAPL",
        initial_price: float = 150.0,
        volatility: float = 0.02,  # 2% daily volatility
        trend_strength: float = 0.0003,  # Small upward bias
        volume_base: float = 50000000  # 50M shares
    ):
        """
        Initialize Stock Data Loader
        
        Args:
            ticker: Stock ticker symbol
            initial_price: Starting price
            volatility: Daily volatility (std dev of returns)
            trend_strength: Trend bias (-0.001 to 0.001)
            volume_base: Base volume
        """
        self.ticker = ticker
        self.initial_price = initial_price
        self.volatility = volatility
        self.trend_strength = trend_strength
        self.volume_base = volume_base
        
    def generate_daily_data(
        self,
        days: int = 500,
        start_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Generate daily stock data
        
        Args:
            days: Number of days to generate
            start_date: Start date (defaults to 500 days ago)
            
        Returns:
            DataFrame with OHLCV data
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=days)
        
        # Generate date range (only business days)
        dates = pd.bdate_range(start=start_date, periods=days)
        
        # Generate price data
        df = self._generate_ohlcv(len(dates))
        df.index = dates
        
        return df
    
    def generate_weekly_data(
        self,
        weeks: int = 104,  # 2 years
        start_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Generate weekly stock data
        
        Args:
            weeks: Number of weeks to generate
            start_date: Start date
            
        Returns:
            DataFrame with OHLCV data
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(weeks=weeks)
        
        # Generate date range (weekly)
        dates = pd.date_range(start=start_date, periods=weeks, freq='W')
        
        # Adjust volatility and trend for weekly data
        original_vol = self.volatility
        original_trend = self.trend_strength
        
        self.volatility = self.volatility * np.sqrt(5)  # Weekly = ~sqrt(5) * daily
        self.trend_strength = self.trend_strength * 5
        
        # Generate price data
        df = self._generate_ohlcv(len(dates))
        df.index = dates
        
        # Restore original parameters
        self.volatility = original_vol
        self.trend_strength = original_trend
        
        return df
    
    def _generate_ohlcv(self, n_candles: int) -> pd.DataFrame:
        """
        Generate OHLCV data
        
        Args:
            n_candles: Number of candles to generate
            
        Returns:
            DataFrame with OHLCV data
        """
        np.random.seed(42)
        
        # Generate close prices using GBM (Geometric Brownian Motion)
        closes = self._generate_price_series(n_candles)
        
        # Generate OHLC from closes
        opens = closes * (1 + np.random.normal(0, self.volatility/4, n_candles))
        
        # High and Low based on volatility
        highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, self.volatility/2, n_candles)))
        lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, self.volatility/2, n_candles)))
        
        # Volume with realistic patterns
        volumes = self._generate_volume_series(n_candles, closes)
        
        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        return df
    
    def _generate_price_series(self, n: int) -> np.ndarray:
        """
        Generate price series using Geometric Brownian Motion with trend periods
        
        Args:
            n: Number of data points
            
        Returns:
            Array of prices
        """
        prices = np.zeros(n)
        prices[0] = self.initial_price
        
        # Create trend periods
        trend_changes = np.random.randint(30, 100, n // 50)  # Change trend every 30-100 days
        trend_periods = []
        
        start = 0
        for length in trend_changes:
            end = min(start + length, n)
            # Random trend direction
            trend = np.random.choice(
                [self.trend_strength * 2, -self.trend_strength, self.trend_strength / 2],
                p=[0.4, 0.3, 0.3]  # Slight upward bias
            )
            trend_periods.extend([trend] * (end - start))
            start = end
        
        # Fill remaining
        while len(trend_periods) < n:
            trend_periods.append(self.trend_strength)
        
        trend_periods = np.array(trend_periods[:n])
        
        # Generate returns
        for i in range(1, n):
            # Random return with trend
            random_return = np.random.normal(trend_periods[i], self.volatility)
            prices[i] = prices[i-1] * (1 + random_return)
        
        return prices
    
    def _generate_volume_series(self, n: int, prices: np.ndarray) -> np.ndarray:
        """
        Generate volume series with realistic patterns
        
        Args:
            n: Number of data points
            prices: Price series
            
        Returns:
            Array of volumes
        """
        # Base volume with random variation
        volumes = self.volume_base * (1 + np.random.normal(0, 0.3, n))
        
        # Higher volume on large price moves
        price_changes = np.abs(np.diff(prices, prepend=prices[0]) / prices)
        volume_multiplier = 1 + (price_changes * 5)
        volumes = volumes * volume_multiplier
        
        # Volume spikes (earnings, news, etc.)
        n_spikes = max(1, n // 50)
        spike_indices = np.random.choice(n, n_spikes, replace=False)
        volumes[spike_indices] *= np.random.uniform(2, 5, n_spikes)
        
        # Ensure positive volumes
        volumes = np.maximum(volumes, self.volume_base * 0.3)
        
        return volumes.astype(int)


def generate_stock_data(
    ticker: str = "AAPL",
    timeframe: str = '1D',
    periods: int = 500,
    start_date: Optional[datetime] = None,
    initial_price: float = 150.0,
    volatility: float = 0.02
) -> pd.DataFrame:
    """
    Convenience function to generate stock data
    
    Args:
        ticker: Stock ticker
        timeframe: '1D' or '1W'
        periods: Number of periods
        start_date: Start date
        initial_price: Starting price
        volatility: Volatility parameter
        
    Returns:
        DataFrame with OHLCV data
    """
    loader = StockDataLoader(
        ticker=ticker,
        initial_price=initial_price,
        volatility=volatility
    )
    
    if timeframe == '1D':
        df = loader.generate_daily_data(days=periods, start_date=start_date)
    elif timeframe == '1W':
        df = loader.generate_weekly_data(weeks=periods, start_date=start_date)
    else:
        raise ValueError(f"Invalid timeframe: {timeframe}. Use '1D' or '1W'")
    
    print(f"\n📊 Generated {ticker} data:")
    print(f"   Timeframe: {timeframe}")
    print(f"   Periods: {len(df)}")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"   Avg volume: {df['volume'].mean():,.0f}")
    
    return df


# Example usage
if __name__ == "__main__":
    # Generate daily data
    df_daily = generate_stock_data(
        ticker="AAPL",
        timeframe='1D',
        periods=500,
        initial_price=150.0
    )
    
    print("\nDaily Data Sample:")
    print(df_daily.head())
    print("\n" + "="*60)
    
    # Generate weekly data
    df_weekly = generate_stock_data(
        ticker="AAPL",
        timeframe='1W',
        periods=104,  # 2 years
        initial_price=150.0
    )
    
    print("\nWeekly Data Sample:")
    print(df_weekly.head())
