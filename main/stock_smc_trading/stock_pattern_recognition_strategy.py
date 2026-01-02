"""
Stock Pattern Recognition Strategy with Fibonacci Extensions
Based on WINNING Gold Pattern Recognition Strategy (+186.91%)

Recognizes CONTINUATION patterns only:
- Flags (Bullish/Bearish)
- Pennants (Bullish/Bearish)  
- Wedges (Rising/Falling)
- Triangles (Ascending/Descending/Symmetrical)

Uses Fibonacci 1.618 or 2.618 for dynamic TP
Adapted for daily/weekly stock trading
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

from stock_long_term_strategy import StockLongTermStrategy


class StockPatternRecognitionStrategy(StockLongTermStrategy):
    """
    Pattern Recognition Strategy for Stocks
    
    Based on WINNING Gold Pattern Recognition Strategy
    Adapted for daily/weekly timeframes with stock-specific filters
    """
    
    def __init__(
        self,
        timeframe: str = '1D',
        fib_mode: str = 'standard',  # 'standard' (1.618) or 'aggressive' (2.618)
        pattern_tolerance: float = 0.02,  # 2% tolerance for pattern matching
        swing_lookback: int = 30,  # Lookback for swing detection (bigger for daily)
        min_pattern_swings: int = 3,  # Minimum swings for pattern
        pattern_cooldown: int = 5,  # Days between pattern signals
        require_trend_confirmation: bool = True,  # Require SMA trend for patterns
        **kwargs
    ):
        """
        Initialize Stock Pattern Recognition Strategy
        
        Args:
            timeframe: '1D' or '1W'
            fib_mode: 'standard' (1.618) or 'aggressive' (2.618)
            pattern_tolerance: Tolerance for pattern matching (учет теней)
            swing_lookback: Lookback period for swing detection
            min_pattern_swings: Minimum swings required
            pattern_cooldown: Days between pattern signals (avoid overtrading)
            require_trend_confirmation: Require SMA 50/200 trend confirmation
            **kwargs: Additional parameters for parent class
        """
        # Set Fibonacci based on mode
        if fib_mode == 'aggressive':
            fib_extension = 2.618
            use_aggressive_tp = True
        else:
            fib_extension = 1.618
            use_aggressive_tp = False
        
        # Initialize parent with Fibonacci settings
        super().__init__(
            timeframe=timeframe,
            fib_extension=fib_extension,
            use_aggressive_tp=use_aggressive_tp,
            swing_length=15 if timeframe == '1D' else 8,
            **kwargs
        )
        
        self.fib_mode = fib_mode
        self.pattern_tolerance = pattern_tolerance
        # Adjust swing lookback per timeframe
        if timeframe == '4H':
            self.swing_lookback = int(swing_lookback * 0.5)  # Shorter for 4H
        elif timeframe == '1W':
            self.swing_lookback = int(swing_lookback * 0.6)  # Shorter for weekly
        else:
            self.swing_lookback = swing_lookback
        self.min_pattern_swings = min_pattern_swings
        # Adjust cooldown per timeframe
        if timeframe == '4H':
            self.pattern_cooldown = 2  # Shorter cooldown for 4H
        elif timeframe == '1W':
            self.pattern_cooldown = max(1, pattern_cooldown // 3)
        else:
            self.pattern_cooldown = pattern_cooldown
        self.require_trend_confirmation = require_trend_confirmation
        
        self.last_pattern_signal = -1000
        
        print(f"   Mode: PATTERN RECOGNITION (Stock)")
        print(f"   Fibonacci Mode: {fib_mode.upper()} ({fib_extension})")
        print(f"   Pattern Tolerance: {pattern_tolerance*100}% (включая тени)")
        print(f"   Swing Lookback: {self.swing_lookback}")
        print(f"   Pattern Cooldown: {self.pattern_cooldown} {timeframe}")
        print(f"   Trend Confirmation: {require_trend_confirmation}")
    
    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run pattern recognition strategy for stocks
        """
        print(f"\n🎯 Running Stock Pattern Recognition Strategy ({self.timeframe})")
        
        # Find swing points FIRST (before parent strategy)
        df = self._find_pattern_swing_points(df)
        
        # Run parent strategy (base signals + Fibonacci TP)
        df = super().run_strategy(df)
        
        # Detect continuation patterns (AFTER parent, so we have indicators)
        df = self._detect_patterns(df)
        
        # Print summary
        total_signals = (df['signal'] != 0).sum()
        pattern_signals = (df['signal_type'].str.contains('pattern', na=False)).sum()
        
        print(f"\n📊 Total Signals: {total_signals}")
        print(f"   Pattern Signals: {pattern_signals}")
        print(f"   Other Signals: {total_signals - pattern_signals}")
        
        return df
    
    def _find_pattern_swing_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Find swing highs and lows for pattern recognition
        
        Uses longer lookback than parent class for more significant swings
        """
        df = df.copy()
        
        # Initialize columns
        df['pattern_swing_high'] = False
        df['pattern_swing_low'] = False
        
        # Need enough data
        if len(df) < self.swing_lookback * 2:
            print(f"   ⚠️  Not enough data for pattern detection (need {self.swing_lookback*2}, have {len(df)})")
            return df
        
        swings_found = 0
        
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            # Swing high - учитываем тени (high)
            window_highs = df['high'].iloc[i-self.swing_lookback:i+self.swing_lookback+1]
            if df['high'].iloc[i] == window_highs.max():
                df.loc[df.index[i], 'pattern_swing_high'] = True
                swings_found += 1
            
            # Swing low - учитываем тени (low)
            window_lows = df['low'].iloc[i-self.swing_lookback:i+self.swing_lookback+1]
            if df['low'].iloc[i] == window_lows.min():
                df.loc[df.index[i], 'pattern_swing_low'] = True
                swings_found += 1
        
        print(f"   Found {swings_found} swing points for pattern detection")
        
        return df
    
    def _detect_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect CONTINUATION chart patterns only
        (Flags, Pennants, Wedges, Triangles)
        
        Based on WINNING Gold strategy but adapted for stocks
        """
        df = df.copy()
        
        # Get swing points
        swing_highs = df[df['pattern_swing_high'] == True].copy()
        swing_lows = df[df['pattern_swing_low'] == True].copy()
        
        patterns_found = 0
        
        # Detect patterns (sliding window approach)
        for i in range(self.swing_lookback + 20, len(df)):
            # Skip if already has signal
            if df['signal'].iloc[i] != 0:
                continue
            
            # Cooldown check - avoid overtrading patterns
            if i - self.last_pattern_signal < self.pattern_cooldown:
                continue
            
            # Get recent swings
            recent_highs = swing_highs[swing_highs.index < df.index[i]].tail(5)
            recent_lows = swing_lows[swing_lows.index < df.index[i]].tail(5)
            
            if len(recent_highs) < 2 or len(recent_lows) < 2:
                continue
            
            # Try to detect each pattern type
            # 1. BULLISH FLAG
            pattern = self._detect_bull_flag(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'bull_flag')
                if added:
                    patterns_found += 1
                    self.last_pattern_signal = i
                    continue
            
            # 2. BEARISH FLAG
            pattern = self._detect_bear_flag(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'bear_flag')
                if added:
                    patterns_found += 1
                    self.last_pattern_signal = i
                    continue
            
            # 3. BULLISH PENNANT
            pattern = self._detect_bull_pennant(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'bull_pennant')
                if added:
                    patterns_found += 1
                    self.last_pattern_signal = i
                    continue
            
            # 4. BEARISH PENNANT
            pattern = self._detect_bear_pennant(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'bear_pennant')
                if added:
                    patterns_found += 1
                    self.last_pattern_signal = i
                    continue
            
            # 5. ASCENDING TRIANGLE (Bullish Continuation)
            pattern = self._detect_ascending_triangle(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'asc_triangle')
                if added:
                    patterns_found += 1
                    self.last_pattern_signal = i
                    continue
            
            # 6. DESCENDING TRIANGLE (Bearish Continuation)
            pattern = self._detect_descending_triangle(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'desc_triangle')
                if added:
                    patterns_found += 1
                    self.last_pattern_signal = i
                    continue
            
            # 7. SYMMETRICAL TRIANGLE
            pattern = self._detect_symmetrical_triangle(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'sym_triangle')
                if added:
                    patterns_found += 1
                    self.last_pattern_signal = i
                    continue
            
            # 8. FALLING WEDGE (Bullish)
            pattern = self._detect_falling_wedge(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'falling_wedge')
                if added:
                    patterns_found += 1
                    self.last_pattern_signal = i
                    continue
            
            # 9. RISING WEDGE (Bearish)
            pattern = self._detect_rising_wedge(df, i, recent_highs, recent_lows)
            if pattern:
                df, added = self._add_pattern_signal(df, i, pattern, 'rising_wedge')
                if added:
                    patterns_found += 1
                    self.last_pattern_signal = i
                    continue
        
        print(f"   Detected {patterns_found} continuation patterns")
        
        return df
    
    # ============ PATTERN DETECTION METHODS (from Gold strategy) ============
    
    def _detect_bull_flag(self, df, idx, recent_highs, recent_lows):
        """
        Detect Bullish Flag (Continuation)
        Strong uptrend + consolidation channel (slight down) + breakout up
        """
        if len(recent_highs) < 3 or len(recent_lows) < 3:
            return None
        
        # Check for uptrend before flag (flagpole)
        lookback = min(idx, 15 if self.timeframe == '1D' else 8)
        flagpole_data = df.iloc[max(0, idx-lookback):idx]
        if len(flagpole_data) < 5:
            return None
        
        # Uptrend check (at least 1% move)
        if flagpole_data['close'].iloc[-1] <= flagpole_data['close'].iloc[0] * 1.01:
            return None
        
        # Flag: parallel channel
        flag_highs = recent_highs.tail(2)
        flag_lows = recent_lows.tail(2)
        
        if len(flag_highs) == 2 and len(flag_lows) == 2:
            resistance = flag_highs['high'].max()
            
            # Breakout above
            if df['close'].iloc[idx] > resistance:
                return {
                    'type': 'bull_flag',
                    'direction': 1,
                    'entry': df['close'].iloc[idx],
                    'resistance': resistance,
                    'support': flag_lows['low'].min()
                }
        
        return None
    
    def _detect_bear_flag(self, df, idx, recent_highs, recent_lows):
        """
        Detect Bearish Flag (Continuation)
        """
        if len(recent_highs) < 3 or len(recent_lows) < 3:
            return None
        
        lookback = min(idx, 15 if self.timeframe == '1D' else 8)
        flagpole_data = df.iloc[max(0, idx-lookback):idx]
        if len(flagpole_data) < 5:
            return None
        
        # Downtrend check
        if flagpole_data['close'].iloc[-1] >= flagpole_data['close'].iloc[0] * 0.99:
            return None
        
        flag_highs = recent_highs.tail(2)
        flag_lows = recent_lows.tail(2)
        
        if len(flag_highs) == 2 and len(flag_lows) == 2:
            support = flag_lows['low'].min()
            
            if df['close'].iloc[idx] < support:
                return {
                    'type': 'bear_flag',
                    'direction': -1,
                    'entry': df['close'].iloc[idx],
                    'resistance': flag_highs['high'].max(),
                    'support': support
                }
        
        return None
    
    def _detect_bull_pennant(self, df, idx, recent_highs, recent_lows):
        """
        Detect Bullish Pennant (Continuation)
        Like flag but converging
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        lookback = min(idx, 15 if self.timeframe == '1D' else 8)
        pole_data = df.iloc[max(0, idx-lookback):idx]
        if len(pole_data) < 5:
            return None
        
        if pole_data['close'].iloc[-1] <= pole_data['close'].iloc[0] * 1.01:
            return None
        
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']
        
        if high2 < high1 and low2 > low1:  # Converging
            resistance = high2
            
            if df['close'].iloc[idx] > resistance:
                return {
                    'type': 'bull_pennant',
                    'direction': 1,
                    'entry': df['close'].iloc[idx],
                    'resistance': resistance,
                    'support': low2
                }
        
        return None
    
    def _detect_bear_pennant(self, df, idx, recent_highs, recent_lows):
        """Detect Bearish Pennant"""
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        lookback = min(idx, 15 if self.timeframe == '1D' else 8)
        pole_data = df.iloc[max(0, idx-lookback):idx]
        if len(pole_data) < 5:
            return None
        
        if pole_data['close'].iloc[-1] >= pole_data['close'].iloc[0] * 0.99:
            return None
        
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']
        
        if high2 < high1 and low2 > low1:  # Converging
            support = low2
            
            if df['close'].iloc[idx] < support:
                return {
                    'type': 'bear_pennant',
                    'direction': -1,
                    'entry': df['close'].iloc[idx],
                    'resistance': high2,
                    'support': support
                }
        
        return None
    
    def _detect_ascending_triangle(self, df, idx, recent_highs, recent_lows):
        """
        Detect Ascending Triangle (Bullish Continuation)
        Flat resistance + rising support
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        
        tolerance = high1 * self.pattern_tolerance
        if abs(high1 - high2) <= tolerance:  # Flat resistance
            low1 = recent_lows.iloc[-2]['low']
            low2 = recent_lows.iloc[-1]['low']
            
            if low2 > low1:  # Rising lows
                resistance = max(high1, high2)
                
                if df['close'].iloc[idx] > resistance:
                    return {
                        'type': 'asc_triangle',
                        'direction': 1,
                        'entry': df['close'].iloc[idx],
                        'resistance': resistance,
                        'support': low2
                    }
        
        return None
    
    def _detect_descending_triangle(self, df, idx, recent_highs, recent_lows):
        """
        Detect Descending Triangle (Bearish Continuation)
        Flat support + falling resistance
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']
        
        tolerance = low1 * self.pattern_tolerance
        if abs(low1 - low2) <= tolerance:  # Flat support
            high1 = recent_highs.iloc[-2]['high']
            high2 = recent_highs.iloc[-1]['high']
            
            if high2 < high1:  # Falling highs
                support = min(low1, low2)
                
                if df['close'].iloc[idx] < support:
                    return {
                        'type': 'desc_triangle',
                        'direction': -1,
                        'entry': df['close'].iloc[idx],
                        'resistance': high2,
                        'support': support
                    }
        
        return None
    
    def _detect_symmetrical_triangle(self, df, idx, recent_highs, recent_lows):
        """
        Detect Symmetrical Triangle (Continuation - direction depends on breakout)
        Rising lows + Falling highs converging
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']
        
        if high2 < high1 and low2 > low1:  # Converging
            resistance = high2
            support = low2
            
            # Breakout above (bullish)
            if df['close'].iloc[idx] > resistance:
                return {
                    'type': 'sym_triangle',
                    'direction': 1,
                    'entry': df['close'].iloc[idx],
                    'resistance': resistance,
                    'support': support
                }
            # Breakout below (bearish)
            elif df['close'].iloc[idx] < support:
                return {
                    'type': 'sym_triangle',
                    'direction': -1,
                    'entry': df['close'].iloc[idx],
                    'resistance': resistance,
                    'support': support
                }
        
        return None
    
    def _detect_falling_wedge(self, df, idx, recent_highs, recent_lows):
        """
        Detect Falling Wedge (Bullish Continuation)
        Both highs and lows falling but converging
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']
        
        # Both falling
        if high2 < high1 and low2 < low1:
            # Converging (lows fall slower than highs)
            high_slope = (high1 - high2) / high1
            low_slope = (low1 - low2) / low1
            
            if high_slope > low_slope:  # Converging
                resistance = high2
                
                if df['close'].iloc[idx] > resistance:
                    return {
                        'type': 'falling_wedge',
                        'direction': 1,
                        'entry': df['close'].iloc[idx],
                        'resistance': resistance,
                        'support': low2
                    }
        
        return None
    
    def _detect_rising_wedge(self, df, idx, recent_highs, recent_lows):
        """
        Detect Rising Wedge (Bearish Continuation)
        Both highs and lows rising but converging
        """
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        high1 = recent_highs.iloc[-2]['high']
        high2 = recent_highs.iloc[-1]['high']
        low1 = recent_lows.iloc[-2]['low']
        low2 = recent_lows.iloc[-1]['low']
        
        # Both rising
        if high2 > high1 and low2 > low1:
            # Converging (highs rise slower than lows)
            high_slope = (high2 - high1) / high1
            low_slope = (low2 - low1) / low1
            
            if low_slope > high_slope:  # Converging
                support = low2
                
                if df['close'].iloc[idx] < support:
                    return {
                        'type': 'rising_wedge',
                        'direction': -1,
                        'entry': df['close'].iloc[idx],
                        'resistance': high2,
                        'support': support
                    }
        
        return None
    
    def _add_pattern_signal(self, df, idx, pattern, pattern_name):
        """
        Add trading signal based on detected pattern
        
        With stock-specific filters (NO time filters, use SMA instead)
        """
        if pattern is None:
            return df, False
        
        # Stock-specific: Trend confirmation filter (instead of time filter)
        if self.require_trend_confirmation:
            direction = pattern['direction']
            
            # Bullish patterns: prefer above SMA 50
            if direction == 1 and not df['above_sma50'].iloc[idx]:
                return df, False
            
            # Bearish patterns: prefer below SMA 50
            if direction == -1 and df['above_sma50'].iloc[idx]:
                return df, False
        
        direction = pattern['direction']
        entry = pattern['entry']
        
        # Calculate SL and TP based on pattern
        if direction == 1:  # Long
            # SL below support
            if 'support' in pattern:
                sl = pattern['support'] * 0.999
            else:
                sl = pattern.get('neckline', pattern.get('head', entry * 0.98)) * 0.999
            
            # Fibonacci TP (KEY from winning strategy!)
            risk = entry - sl
            tp = entry + (risk * self.fib_extension)
        
        else:  # Short
            # SL above resistance
            if 'resistance' in pattern:
                sl = pattern['resistance'] * 1.001
            else:
                sl = pattern.get('neckline', pattern.get('head', entry * 1.02)) * 1.001
            
            # Fibonacci TP
            risk = sl - entry
            tp = entry - (risk * self.fib_extension)
        
        # Min risk check (0.5% for stocks, not 0.3% like gold)
        risk_pct = abs(entry - sl) / entry
        if risk_pct < self.min_risk_pct or risk_pct > self.max_risk_pct:
            return df, False
        
        # Add signal
        df.loc[df.index[idx], 'signal'] = direction
        df.loc[df.index[idx], 'entry_price'] = entry
        df.loc[df.index[idx], 'stop_loss'] = sl
        df.loc[df.index[idx], 'take_profit'] = tp
        df.loc[df.index[idx], 'signal_type'] = f"pattern_{pattern_name}"
        df.loc[df.index[idx], 'position_type'] = 'pattern'
        
        return df, True


if __name__ == "__main__":
    print("Stock Pattern Recognition Strategy - Based on Gold Winner (+186.91%)")
    print("Continuation Patterns: Flags, Pennants, Wedges, Triangles")
    print("Fibonacci Modes: 'standard' (1.618) or 'aggressive' (2.618)")
