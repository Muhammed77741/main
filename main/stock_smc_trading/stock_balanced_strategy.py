"""
Stock Balanced Strategy - FINAL VERSION

The GOLDILOCKS solution:
- Not too aggressive (Adaptive: -60%)
- Not too conservative (Optimized: -70%)  
- JUST RIGHT ✅

Key insights from testing:
1. Stocks need TP: 0.8%/1.5%/2.5% (between Optimized and Adaptive)
2. Selective signals: 50-100/year (not 8, not 400!)
3. Pattern OR SMC confirmation (not both required)
4. Max 3 positions
5. SL: 1.0-1.5%

Target: 55-65% WR, 20-40% annual return, <15% DD
"""

import pandas as pd
import numpy as np
from typing import Dict

from stock_pattern_recognition_strategy import StockPatternRecognitionStrategy


class StockBalancedStrategy(StockPatternRecognitionStrategy):
    """
    The Balanced Approach - Learn from both failures
    """
    
    def __init__(self, timeframe: str = '4H', **kwargs):
        """Initialize Balanced Strategy"""
        
        # Moderate settings (not too strict, not too loose)
        kwargs['fib_mode'] = 'standard'
        kwargs['long_only'] = True
        kwargs['pattern_tolerance'] = 0.020  # 2.0% - moderate
        kwargs['swing_lookback'] = 12  # Moderate lookback
        kwargs['pattern_cooldown'] = 4  # 16h cooldown
        kwargs['require_trend_confirmation'] = True  # Keep this
        kwargs['min_candle_quality'] = 30  # Moderate
        kwargs['min_volume_ratio'] = 0.9  # Moderate
        kwargs['min_risk_pct'] = 0.006  # 0.6%
        
        super().__init__(timeframe=timeframe, **kwargs)
        
        # Balanced TP/SL (goldilocks zone)
        self.balanced_params = {
            'trend': {
                'tp1_pct': 0.008,  # 0.8% TP1 (close 50%)
                'tp2_pct': 0.015,  # 1.5% TP2 (close 30%)
                'tp3_pct': 0.025,  # 2.5% TP3 (close 20%)
                'sl_pct': 0.013,   # 1.3% SL
                'trailing_pct': 0.007,  # 0.7% trailing
                'timeout_hours': 40,  # ~1.7 days
            },
            'range': {
                'tp1_pct': 0.006,  # 0.6% TP1
                'tp2_pct': 0.011,  # 1.1% TP2
                'tp3_pct': 0.018,  # 1.8% TP3
                'sl_pct': 0.011,   # 1.1% SL
                'trailing_pct': 0.006,  # 0.6% trailing
                'timeout_hours': 30,  # ~1.2 days
            }
        }
        
        # Prefer good patterns but don't require them
        self.preferred_patterns = {
            'pattern_bull_flag',
            'pattern_asc_triangle',
            'pattern_falling_wedge',
            'pattern_sym_triangle'
        }
        
        # Filter out bad patterns
        self.bad_patterns = {
            'pattern_desc_triangle',
            'pattern_rising_wedge'
        }
        
        print(f"\n⚖️  Stock Balanced Strategy Initialized")
        print(f"   Approach: Goldilocks (not too hot, not too cold)")
        print(f"   TREND TP: {self.balanced_params['trend']['tp1_pct']*100:.1f}% / {self.balanced_params['trend']['tp2_pct']*100:.1f}% / {self.balanced_params['trend']['tp3_pct']*100:.1f}%")
        print(f"   TREND SL: {self.balanced_params['trend']['sl_pct']*100:.1f}%")
        print(f"   Target signals: 50-100/year")
        print(f"   Target WR: 55-65%")
    
    def detect_regime(self, df: pd.DataFrame, idx: int) -> str:
        """Simple regime detection"""
        if idx < 50:
            return 'trend'
        
        if 'ema_50' not in df.columns:
            df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        if 'ema_200' not in df.columns:
            df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        ema_50 = df['ema_50'].iloc[idx]
        ema_200 = df['ema_200'].iloc[idx]
        close = df['close'].iloc[idx]
        
        # Score-based
        score = 0
        
        # EMA separation
        if pd.notna(ema_50) and pd.notna(ema_200) and ema_200 != 0:
            sep = abs(ema_50 - ema_200) / ema_200
            if sep > 0.015:  # 1.5%
                score += 1
        
        # Price away from EMA
        if pd.notna(ema_50) and ema_50 != 0:
            dist = abs(close - ema_50) / ema_50
            if dist > 0.008:  # 0.8%
                score += 1
        
        return 'trend' if score >= 1 else 'range'
    
    def calculate_signal_quality(self, df: pd.DataFrame, idx: int) -> float:
        """
        Calculate signal quality score 0-1
        
        Higher score = keep signal
        Lower score = filter out
        """
        score = 0.5  # Base score
        
        # Bonus for good patterns
        signal_type = df.get('signal_type', pd.Series([''] * len(df))).iloc[idx]
        if signal_type in self.preferred_patterns:
            score += 0.3
        
        # Penalty for bad patterns
        if signal_type in self.bad_patterns:
            score -= 0.4
        
        # Bonus for volume
        if 'volume' in df.columns and idx > 5:
            vol = df['volume'].iloc[idx]
            avg_vol = df['volume'].iloc[max(0, idx-20):idx].mean()
            if vol > avg_vol * 1.2:
                score += 0.1
        
        # Bonus for trend alignment
        if 'above_sma50' in df.columns:
            direction = df['signal'].iloc[idx]
            above_sma = df['above_sma50'].iloc[idx]
            if (direction == 1 and above_sma) or (direction == -1 and not above_sma):
                score += 0.2
        
        return min(1.0, max(0.0, score))
    
    def apply_balanced_tp_sl(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply balanced TP/SL with quality filtering
        """
        print(f"\n🎯 Applying Balanced TP/SL + Quality Filter")
        
        df['regime'] = 'trend'
        df['tp1'] = 0.0
        df['tp2'] = 0.0
        df['tp3'] = 0.0
        df['trailing_stop_pct'] = 0.0
        df['timeout_hours'] = 40
        df['quality_score'] = 0.0
        
        kept = 0
        filtered_quality = 0
        filtered_risk = 0
        trend_cnt = 0
        range_cnt = 0
        
        # Quality threshold
        min_quality = 0.5  # Keep signals with score >= 0.5
        
        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue
            
            # Calculate quality
            quality = self.calculate_signal_quality(df, i)
            df.loc[df.index[i], 'quality_score'] = quality
            
            # Filter by quality
            if quality < min_quality:
                df.loc[df.index[i], 'signal'] = 0
                filtered_quality += 1
                continue
            
            # Detect regime
            regime = self.detect_regime(df, i)
            df.loc[df.index[i], 'regime'] = regime
            
            params = self.balanced_params[regime]
            
            if regime == 'trend':
                trend_cnt += 1
            else:
                range_cnt += 1
            
            entry = df['entry_price'].iloc[i]
            if entry == 0:
                continue
            
            direction = df['signal'].iloc[i]
            
            # Calculate TP/SL
            if direction == 1:  # LONG
                tp1 = entry * (1 + params['tp1_pct'])
                tp2 = entry * (1 + params['tp2_pct'])
                tp3 = entry * (1 + params['tp3_pct'])
                sl = entry * (1 - params['sl_pct'])
            else:
                tp1 = entry * (1 - params['tp1_pct'])
                tp2 = entry * (1 - params['tp2_pct'])
                tp3 = entry * (1 - params['tp3_pct'])
                sl = entry * (1 + params['sl_pct'])
            
            # Risk check
            risk_pct = abs(entry - sl) / entry
            if risk_pct < 0.006 or risk_pct > 0.025:  # 0.6-2.5%
                df.loc[df.index[i], 'signal'] = 0
                filtered_risk += 1
                continue
            
            # Update
            df.loc[df.index[i], 'stop_loss'] = sl
            df.loc[df.index[i], 'take_profit'] = tp3
            df.loc[df.index[i], 'tp1'] = tp1
            df.loc[df.index[i], 'tp2'] = tp2
            df.loc[df.index[i], 'tp3'] = tp3
            df.loc[df.index[i], 'trailing_stop_pct'] = params['trailing_pct']
            df.loc[df.index[i], 'timeout_hours'] = params['timeout_hours']
            
            kept += 1
        
        print(f"   Kept: {kept}")
        print(f"   Filtered (quality): {filtered_quality}")
        print(f"   Filtered (risk): {filtered_risk}")
        print(f"   TREND: {trend_cnt}, RANGE: {range_cnt}")
        print(f"   Target: 50-100 signals")
        
        if kept < 30:
            print(f"   ⚠️  Low signal count. Consider:")
            print(f"      - Longer period (2 years)")
            print(f"      - Lower min_quality (0.4)")
        elif kept > 150:
            print(f"   ⚠️  Too many signals. Consider:")
            print(f"      - Higher min_quality (0.6)")
            print(f"      - Stricter filters")
        else:
            print(f"   ✅ Good signal count!")
        
        return df
    
    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run balanced strategy"""
        # Parent pattern recognition
        df = super().run_strategy(df)
        
        # Apply balanced TP/SL and filtering
        df = self.apply_balanced_tp_sl(df)
        
        final_signals = (df['signal'] != 0).sum()
        print(f"\n✅ Final signals: {final_signals}")
        
        return df


if __name__ == "__main__":
    from stock_adaptive_strategy import get_real_stock_data
    
    df = get_real_stock_data('NVDA', days=365)
    
    strategy = StockBalancedStrategy(timeframe='4H')
    df_signals = strategy.run_strategy(df)
    
    print(f"\nSignals: {(df_signals['signal'] != 0).sum()}")
