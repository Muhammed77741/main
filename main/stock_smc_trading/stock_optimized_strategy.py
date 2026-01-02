"""
Stock Optimized Strategy - Adapted for Real Stock Market Behavior

Key differences from Gold:
- Stocks move SLOWER → smaller TP (0.5%/1.0%/1.5% vs 1.5%/2.8%/4.5%)
- Stocks less volatile → tighter SL (0.8-1.2% vs 2-4%)
- Need MORE filters → Pattern + SMC confirmation required
- Shorter holding time → 24-36h timeout vs 48-60h
- Max 1-2 trades per day (not 5-10!)

Target: Conservative, high win rate, small consistent gains
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

from stock_pattern_recognition_strategy import StockPatternRecognitionStrategy


class StockOptimizedStrategy(StockPatternRecognitionStrategy):
    """
    Optimized for REAL stock market behavior
    Based on analysis: stocks move 3-5x slower than Gold
    """
    
    def __init__(
        self,
        timeframe: str = '4H',
        max_positions: int = 3,  # More conservative than Gold's 5
        require_pattern_confirmation: bool = True,  # MUST have pattern
        **kwargs
    ):
        """
        Initialize Stock Optimized Strategy
        
        Args:
            timeframe: '4H' recommended
            max_positions: Max 3 (more conservative)
            require_pattern_confirmation: Require pattern + SMC confirmation
        """
        # Force conservative settings
        kwargs['fib_mode'] = 'standard'  # Use 1.618, not 2.618
        kwargs['long_only'] = True
        kwargs['pattern_tolerance'] = 0.015  # Tighter: 1.5%
        kwargs['swing_lookback'] = 15  # More lookback for better patterns
        kwargs['pattern_cooldown'] = 6  # 1 day cooldown (6 candles * 4H)
        kwargs['require_trend_confirmation'] = True  # MUST be in trend
        kwargs['min_candle_quality'] = 35  # Higher quality
        kwargs['min_volume_ratio'] = 1.0  # At least average volume
        kwargs['min_risk_pct'] = 0.005  # 0.5% min risk
        
        super().__init__(timeframe=timeframe, **kwargs)
        
        self.max_positions = max_positions
        self.require_pattern_confirmation = require_pattern_confirmation
        
        # Stock-specific TP/SL (3-5x smaller than Gold)
        self.stock_params = {
            'trend': {
                'tp1_pct': 0.005,   # 0.5% for TP1 (close 50%)
                'tp2_pct': 0.010,   # 1.0% for TP2 (close 30%)
                'tp3_pct': 0.015,   # 1.5% for TP3 (close 20%)
                'sl_pct': 0.012,    # 1.2% stop loss
                'trailing_stop_pct': 0.006,  # 0.6% trailing
                'timeout_hours': 36,  # 1.5 days
            },
            'range': {
                'tp1_pct': 0.004,   # 0.4% for TP1
                'tp2_pct': 0.007,   # 0.7% for TP2
                'tp3_pct': 0.010,   # 1.0% for TP3
                'sl_pct': 0.010,    # 1.0% stop loss
                'trailing_stop_pct': 0.005,  # 0.5% trailing
                'timeout_hours': 24,  # 1 day
            }
        }
        
        # Good patterns for stocks (from analysis)
        self.good_patterns = [
            'pattern_bull_flag',
            'pattern_asc_triangle',
            'pattern_falling_wedge',
            'pattern_sym_triangle',
            'pattern_bull_pennant'
        ]
        
        # Bad patterns to filter out
        self.bad_patterns = [
            'pattern_desc_triangle',
            'pattern_rising_wedge',
            'pattern_bear_flag',
            'pattern_bear_pennant'
        ]
        
        print(f"\n💎 Stock Optimized Strategy Initialized")
        print(f"   Max Positions: {max_positions}")
        print(f"   Pattern Required: {require_pattern_confirmation}")
        print(f"   TREND TP: {self.stock_params['trend']['tp1_pct']*100:.1f}% / {self.stock_params['trend']['tp2_pct']*100:.1f}% / {self.stock_params['trend']['tp3_pct']*100:.1f}%")
        print(f"   TREND SL: {self.stock_params['trend']['sl_pct']*100:.1f}%")
        print(f"   RANGE TP: {self.stock_params['range']['tp1_pct']*100:.1f}% / {self.stock_params['range']['tp2_pct']*100:.1f}% / {self.stock_params['range']['tp3_pct']*100:.1f}%")
        print(f"   RANGE SL: {self.stock_params['range']['sl_pct']*100:.1f}%")
    
    def detect_market_regime(self, df: pd.DataFrame, idx: int) -> str:
        """
        Simplified regime detection for stocks
        
        Stocks are more often in TREND than Gold (less choppy)
        
        Args:
            df: DataFrame
            idx: Current index
            
        Returns:
            'trend' or 'range'
        """
        if idx < 50:
            return 'trend'
        
        # Ensure we have EMAs
        if 'ema_50' not in df.columns:
            df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        if 'ema_200' not in df.columns:
            df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        score = 0
        
        # 1. EMA separation
        ema_50 = df['ema_50'].iloc[idx]
        ema_200 = df['ema_200'].iloc[idx]
        
        if pd.notna(ema_50) and pd.notna(ema_200) and ema_200 != 0:
            ema_diff = abs(ema_50 - ema_200) / ema_200
            if ema_diff > 0.02:  # 2% separation
                score += 1
        
        # 2. Price trend (20 candles)
        if idx >= 20:
            close_now = df['close'].iloc[idx]
            close_20 = df['close'].iloc[idx-20]
            price_change = abs(close_now - close_20) / close_20
            
            if price_change > 0.03:  # 3% move
                score += 1
        
        # 3. Above/below EMA 50
        close = df['close'].iloc[idx]
        if pd.notna(ema_50) and ema_50 != 0:
            distance = abs(close - ema_50) / ema_50
            if distance > 0.01:  # 1% away
                score += 1
        
        return 'trend' if score >= 2 else 'range'
    
    def apply_stock_optimized_tp_sl(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply stock-optimized TP/SL
        
        Much smaller than Gold because stocks move slower
        
        Args:
            df: DataFrame with signals
            
        Returns:
            DataFrame with optimized TP/SL
        """
        print(f"\n🎯 Applying Stock-Optimized TP/SL")
        
        # Initialize columns
        df['regime'] = 'trend'
        df['tp1'] = 0.0
        df['tp2'] = 0.0
        df['tp3'] = 0.0
        df['trailing_stop_pct'] = 0.0
        df['timeout_hours'] = 36
        
        signals_kept = 0
        signals_filtered = 0
        pattern_filtered = 0
        trend_count = 0
        range_count = 0
        
        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue
            
            # FILTER 1: Pattern confirmation required
            if self.require_pattern_confirmation:
                signal_type = df.get('signal_type', pd.Series([''] * len(df))).iloc[i]
                
                # Must have a good pattern
                if not signal_type or signal_type not in self.good_patterns:
                    df.loc[df.index[i], 'signal'] = 0  # Remove signal
                    pattern_filtered += 1
                    continue
                
                # Filter bad patterns
                if signal_type in self.bad_patterns:
                    df.loc[df.index[i], 'signal'] = 0
                    pattern_filtered += 1
                    continue
            
            # Detect regime
            regime = self.detect_market_regime(df, i)
            df.loc[df.index[i], 'regime'] = regime
            
            params = self.stock_params[regime]
            
            if regime == 'trend':
                trend_count += 1
            else:
                range_count += 1
            
            entry = df['entry_price'].iloc[i]
            
            if entry == 0:
                continue
            
            # Calculate stock-optimized TP/SL
            direction = df['signal'].iloc[i]
            
            if direction == 1:  # LONG
                tp1 = entry * (1 + params['tp1_pct'])
                tp2 = entry * (1 + params['tp2_pct'])
                tp3 = entry * (1 + params['tp3_pct'])
                sl = entry * (1 - params['sl_pct'])
            else:  # SHORT (shouldn't happen with long_only)
                tp1 = entry * (1 - params['tp1_pct'])
                tp2 = entry * (1 - params['tp2_pct'])
                tp3 = entry * (1 - params['tp3_pct'])
                sl = entry * (1 + params['sl_pct'])
            
            # FILTER 2: Risk check (must be reasonable)
            risk_pct = abs(entry - sl) / entry
            if risk_pct < 0.005 or risk_pct > 0.02:  # Between 0.5% and 2%
                df.loc[df.index[i], 'signal'] = 0
                signals_filtered += 1
                continue
            
            # Update TP/SL
            df.loc[df.index[i], 'stop_loss'] = sl
            df.loc[df.index[i], 'take_profit'] = tp3
            df.loc[df.index[i], 'tp1'] = tp1
            df.loc[df.index[i], 'tp2'] = tp2
            df.loc[df.index[i], 'tp3'] = tp3
            df.loc[df.index[i], 'trailing_stop_pct'] = params['trailing_stop_pct']
            df.loc[df.index[i], 'timeout_hours'] = params['timeout_hours']
            
            signals_kept += 1
        
        print(f"   Signals kept: {signals_kept}")
        print(f"   Pattern filtered: {pattern_filtered}")
        print(f"   Risk filtered: {signals_filtered}")
        print(f"   TREND: {trend_count}")
        print(f"   RANGE: {range_count}")
        
        return df
    
    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run stock-optimized strategy
        
        Args:
            df: OHLCV data
            
        Returns:
            DataFrame with optimized signals
        """
        # Run parent pattern recognition
        df = super().run_strategy(df)
        
        # Apply stock-optimized TP/SL and filters
        df = self.apply_stock_optimized_tp_sl(df)
        
        # Count final signals
        final_signals = (df['signal'] != 0).sum()
        print(f"\n✅ Final signals: {final_signals}")
        
        if final_signals < 10:
            print(f"   ⚠️  Warning: Only {final_signals} signals. Consider:")
            print(f"      - Increasing data period")
            print(f"      - Relaxing pattern_tolerance")
            print(f"      - Disabling require_pattern_confirmation")
        
        return df


if __name__ == "__main__":
    print("\n🧪 Testing Stock Optimized Strategy")
    
    # Test with real data
    from stock_adaptive_strategy import get_real_stock_data
    
    df = get_real_stock_data(ticker='NVDA', days=365)
    
    strategy = StockOptimizedStrategy(
        timeframe='4H',
        max_positions=3,
        require_pattern_confirmation=True
    )
    
    df_signals = strategy.run_strategy(df)
    
    print(f"\n✅ Strategy completed")
    print(f"   Total signals: {(df_signals['signal'] != 0).sum()}")
