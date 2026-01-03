"""
Stock Adaptive Strategy - Inspired by Gold SHORT Optimized (+325.70%)

Key Features:
- Adaptive TREND/RANGE modes
- Trailing Stop after TP1
- Partial TP (50% → 30% → 20%)
- Max Positions = 5
- Market regime detection
- Asymmetric parameters for better risk management
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple

from stock_pattern_recognition_strategy import StockPatternRecognitionStrategy


class StockAdaptiveStrategy(StockPatternRecognitionStrategy):
    """
    Adaptive Stock Strategy with TREND/RANGE modes
    Based on winning Gold SHORT Optimized strategy
    """
    
    def __init__(
        self,
        timeframe: str = '4H',
        fib_mode: str = 'aggressive',
        max_positions: int = 5,
        enable_trailing_stop: bool = True,
        enable_adaptive_modes: bool = True,
        **kwargs
    ):
        """
        Initialize Adaptive Stock Strategy
        
        Args:
            timeframe: '4H', '1D', '1W'
            fib_mode: 'standard' or 'aggressive'
            max_positions: Maximum concurrent positions (5 recommended)
            enable_trailing_stop: Use trailing stop after TP1
            enable_adaptive_modes: Use TREND/RANGE adaptive parameters
        """
        super().__init__(timeframe=timeframe, fib_mode=fib_mode, **kwargs)
        
        self.max_positions = max_positions
        self.enable_trailing_stop = enable_trailing_stop
        self.enable_adaptive_modes = enable_adaptive_modes
        
        # Market regime
        self.current_regime = 'TREND'  # 'TREND' or 'RANGE'
        
        # Adaptive parameters (similar to Gold strategy)
        self.trend_params = {
            'tp1_pct': 0.015,  # 1.5% for TP1 (close 50%)
            'tp2_pct': 0.028,  # 2.8% for TP2 (close 30%)
            'tp3_pct': 0.045,  # 4.5% for TP3 (close 20%)
            'trailing_stop_pct': 0.009,  # 0.9% trailing (activates after TP1)
            'timeout_hours': 60,  # 60 hours = 2.5 days
        }
        
        self.range_params = {
            'tp1_pct': 0.010,  # 1.0% for TP1 (close 50%)
            'tp2_pct': 0.018,  # 1.8% for TP2 (close 30%)
            'tp3_pct': 0.025,  # 2.5% for TP3 (close 20%)
            'trailing_stop_pct': 0.008,  # 0.8% trailing
            'timeout_hours': 48,  # 48 hours = 2 days
        }
        
        print(f"\n💡 Adaptive Stock Strategy Initialized")
        print(f"   Max Positions: {max_positions}")
        print(f"   Trailing Stop: {enable_trailing_stop}")
        print(f"   Adaptive Modes: {enable_adaptive_modes}")
        print(f"   TREND TP: {self.trend_params['tp1_pct']*100:.1f}% / {self.trend_params['tp2_pct']*100:.1f}% / {self.trend_params['tp3_pct']*100:.1f}%")
        print(f"   RANGE TP: {self.range_params['tp1_pct']*100:.1f}% / {self.range_params['tp2_pct']*100:.1f}% / {self.range_params['tp3_pct']*100:.1f}%")
    
    def detect_market_regime(self, df: pd.DataFrame, idx: int) -> str:
        """
        Detect market regime: TREND or RANGE
        
        Based on 5 indicators (like Gold strategy):
        1. EMA trend strength
        2. ATR volatility
        3. Price direction
        4. Market bias
        5. Market structure
        
        Args:
            df: DataFrame with price data
            idx: Current index
            
        Returns:
            'TREND' or 'RANGE'
        """
        if not self.enable_adaptive_modes:
            return 'TREND'  # Default
        
        if idx < 50:
            return 'TREND'
        
        # Need EMA and ATR
        if 'ema_50' not in df.columns:
            df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        if 'ema_200' not in df.columns:
            df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        if 'atr' not in df.columns:
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['atr'] = tr.rolling(window=14).mean()
        
        score = 0
        
        # 1. EMA Trend Strength
        ema_50 = df['ema_50'].iloc[idx]
        ema_200 = df['ema_200'].iloc[idx]
        ema_diff = abs(ema_50 - ema_200) / ema_200
        
        if ema_diff > 0.02:  # 2% separation = strong trend
            score += 1
        
        # 2. ATR Volatility (high ATR = trending)
        current_atr = df['atr'].iloc[idx]
        avg_atr = df['atr'].iloc[max(0, idx-50):idx].mean()
        
        if current_atr > avg_atr * 1.1:
            score += 1
        
        # 3. Price Direction (consistent movement)
        close_now = df['close'].iloc[idx]
        close_20_ago = df['close'].iloc[max(0, idx-20)]
        price_change = abs(close_now - close_20_ago) / close_20_ago
        
        if price_change > 0.03:  # 3% move in 20 candles
            score += 1
        
        # 4. Market Bias (above/below EMA 50)
        if ema_50 != 0:
            distance_from_ema = abs(close_now - ema_50) / ema_50
            if distance_from_ema > 0.01:  # 1% away from EMA
                score += 1
        
        # 5. Market Structure (higher highs/lower lows)
        recent_highs = df['high'].iloc[max(0, idx-10):idx]
        recent_lows = df['low'].iloc[max(0, idx-10):idx]
        
        if len(recent_highs) > 5 and len(recent_lows) > 5:
            if recent_highs.iloc[-1] > recent_highs.iloc[0] or recent_lows.iloc[-1] < recent_lows.iloc[0]:
                score += 1
        
        # Decision: 3+ signals = TREND, otherwise RANGE
        regime = 'TREND' if score >= 3 else 'RANGE'
        
        return regime
    
    def apply_adaptive_tp_sl(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply adaptive TP/SL based on market regime
        
        Overwrites Fibonacci TP with adaptive levels:
        - TREND: larger TP (1.5% / 2.8% / 4.5%)
        - RANGE: smaller TP (1.0% / 1.8% / 2.5%)
        
        Args:
            df: DataFrame with signals
            
        Returns:
            DataFrame with adaptive TP/SL
        """
        print(f"\n🎯 Applying Adaptive TP/SL (TREND/RANGE)")
        
        df['regime'] = 'TREND'
        df['tp1'] = 0.0
        df['tp2'] = 0.0
        df['tp3'] = 0.0
        df['trailing_stop_pct'] = 0.0
        
        trend_count = 0
        range_count = 0
        
        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue
            
            # Detect regime
            regime = self.detect_market_regime(df, i)
            df.loc[df.index[i], 'regime'] = regime
            
            if regime == 'TREND':
                trend_count += 1
                params = self.trend_params
            else:
                range_count += 1
                params = self.range_params
            
            # Get entry and SL
            entry = df['entry_price'].iloc[i]
            sl = df['stop_loss'].iloc[i]
            
            if entry == 0 or sl == 0:
                continue
            
            direction = df['signal'].iloc[i]
            
            # Calculate adaptive TP levels
            if direction == 1:  # LONG
                tp1 = entry * (1 + params['tp1_pct'])
                tp2 = entry * (1 + params['tp2_pct'])
                tp3 = entry * (1 + params['tp3_pct'])
            else:  # SHORT (but we use long_only, so shouldn't happen)
                tp1 = entry * (1 - params['tp1_pct'])
                tp2 = entry * (1 - params['tp2_pct'])
                tp3 = entry * (1 - params['tp3_pct'])
            
            # Update TP
            df.loc[df.index[i], 'take_profit'] = tp3  # Final TP for backtester
            df.loc[df.index[i], 'tp1'] = tp1
            df.loc[df.index[i], 'tp2'] = tp2
            df.loc[df.index[i], 'tp3'] = tp3
            df.loc[df.index[i], 'trailing_stop_pct'] = params['trailing_stop_pct']
        
        print(f"   TREND signals: {trend_count}")
        print(f"   RANGE signals: {range_count}")
        
        return df
    
    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run adaptive strategy with TREND/RANGE modes
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with signals and adaptive TP/SL
        """
        # First run parent strategy (Pattern Recognition)
        df = super().run_strategy(df)
        
        # Apply adaptive TP/SL
        if self.enable_adaptive_modes:
            df = self.apply_adaptive_tp_sl(df)
        
        return df


def get_real_stock_data(ticker: str = 'AAPL', days: int = 365) -> pd.DataFrame:
    """
    Get real stock data (or generate realistic synthetic data)
    
    In production, replace with:
    - yfinance
    - Alpha Vantage
    - Interactive Brokers API
    
    Args:
        ticker: Stock ticker
        days: Number of days
        
    Returns:
        DataFrame with OHLCV data
    """
    try:
        import yfinance as yf
        
        print(f"\n📥 Downloading real data for {ticker}...")
        
        # Download 4H data (1 year)
        stock = yf.Ticker(ticker)
        df = stock.history(period=f"{days}d", interval='1h')  # Get hourly first
        
        if df.empty:
            raise Exception("No data from yfinance")
        
        # Resample to 4H
        df_4h = df.resample('4H').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        # Rename columns
        df_4h.columns = ['open', 'high', 'low', 'close', 'volume']
        
        print(f"   ✅ Downloaded {len(df_4h)} 4H candles")
        print(f"   Date range: {df_4h.index[0]} to {df_4h.index[-1]}")
        print(f"   Price range: ${df_4h['close'].min():.2f} - ${df_4h['close'].max():.2f}")
        
        return df_4h
        
    except Exception as e:
        print(f"   ⚠️  Could not download real data: {e}")
        print(f"   Using synthetic data instead...")
        
        from stock_data_loader import generate_stock_data
        return generate_stock_data(
            ticker=ticker,
            timeframe='4H',
            periods=days,
            initial_price=150.0,
            volatility=0.015
        )


if __name__ == "__main__":
    print("\n🧪 Testing Adaptive Stock Strategy")
    
    # Get real data
    df = get_real_stock_data(ticker='AAPL', days=365)
    
    # Create adaptive strategy
    strategy = StockAdaptiveStrategy(
        timeframe='4H',
        fib_mode='aggressive',
        max_positions=5,
        enable_trailing_stop=True,
        enable_adaptive_modes=True,
        pattern_tolerance=0.02,
        swing_lookback=12,
        pattern_cooldown=3,
        long_only=True
    )
    
    # Run strategy
    df_signals = strategy.run_strategy(df)
    
    print(f"\n✅ Strategy completed")
    print(f"   Total signals: {(df_signals['signal'] != 0).sum()}")
    print(f"   TREND signals: {(df_signals['regime'] == 'TREND').sum()}")
    print(f"   RANGE signals: {(df_signals['regime'] == 'RANGE').sum()}")
