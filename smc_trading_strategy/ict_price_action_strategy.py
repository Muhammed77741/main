"""
ICT (Inner Circle Trader) Price Action Strategy
Based on key ICT concepts:
- Liquidity Sweeps (taking out stops)
- Order Blocks (institutional entry zones)
- Fair Value Gaps (imbalance zones)
- Market Structure Shifts (BOS/ChoCh)
- Kill Zones (London/New York sessions - UTC times)
- Power of 3 (Accumulation, Manipulation, Distribution)
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime, time


class ICTPriceActionStrategy:
    """
    ICT Price Action Strategy implementation
    
    Core concepts:
    1. Liquidity Sweeps - identify where smart money hunts retail stops
    2. Order Blocks - institutional entry zones after liquidity grab
    3. Fair Value Gaps (FVG) - price inefficiencies to be filled
    4. Market Structure - Higher Highs/Lows (bullish) or Lower Highs/Lows (bearish)
    5. Kill Zones - optimal trading times (London: 02:00-05:00 UTC, NY: 13:00-16:00 UTC)
    """
    
    def __init__(
        self,
        risk_reward_ratio: float = 2.0,
        risk_per_trade: float = 0.02,
        swing_length: int = 10,
        fvg_threshold: float = 0.001,  # 0.1% gap minimum
        liquidity_lookback: int = 20,
        use_kill_zones: bool = True
    ):
        """
        Initialize ICT Strategy
        
        Args:
            risk_reward_ratio: Risk/Reward ratio (2.0 = 1:2)
            risk_per_trade: Risk per trade as fraction (0.02 = 2%)
            swing_length: Lookback period for swing highs/lows
            fvg_threshold: Minimum gap size for FVG (as percentage)
            liquidity_lookback: Candles to look back for liquidity zones
            use_kill_zones: Whether to filter trades by kill zones
        """
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade = risk_per_trade
        self.swing_length = swing_length
        self.fvg_threshold = fvg_threshold
        self.liquidity_lookback = liquidity_lookback
        self.use_kill_zones = use_kill_zones
        
    def detect_liquidity_sweeps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect liquidity sweeps - when price takes out previous swing high/low
        then reverses (stop hunt)
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            DataFrame with liquidity sweep signals
        """
        df = df.copy()
        df['bullish_liquidity_sweep'] = False
        df['bearish_liquidity_sweep'] = False
        
        # Find swing highs and lows
        for i in range(self.liquidity_lookback, len(df)):
            window = df.iloc[i-self.liquidity_lookback:i]
            current = df.iloc[i]
            
            # Bullish sweep: low takes out previous lows, then closes higher
            recent_lows = window['low'].rolling(5).min()
            if len(recent_lows) > 0:
                lowest_low = recent_lows.min()
                if (current['low'] < lowest_low and 
                    current['close'] > current['open'] and
                    current['close'] > lowest_low):
                    df.loc[df.index[i], 'bullish_liquidity_sweep'] = True
            
            # Bearish sweep: high takes out previous highs, then closes lower
            recent_highs = window['high'].rolling(5).max()
            if len(recent_highs) > 0:
                highest_high = recent_highs.max()
                if (current['high'] > highest_high and 
                    current['close'] < current['open'] and
                    current['close'] < highest_high):
                    df.loc[df.index[i], 'bearish_liquidity_sweep'] = True
        
        return df
    
    def detect_order_blocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Order Blocks - last opposing candle before strong move
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            DataFrame with order block zones
        """
        df = df.copy()
        df['bullish_ob'] = False
        df['bearish_ob'] = False
        df['ob_top'] = np.nan
        df['ob_bottom'] = np.nan
        
        for i in range(3, len(df)):
            current = df.iloc[i]
            prev1 = df.iloc[i-1]
            prev2 = df.iloc[i-2]
            prev3 = df.iloc[i-3]
            
            # Bullish Order Block: down candle followed by strong up move
            if (prev2['close'] < prev2['open'] and  # Down candle
                prev1['close'] > prev1['open'] and  # Up candle
                current['close'] > current['open'] and  # Up candle
                current['close'] > prev2['high']):  # Break above
                
                df.loc[df.index[i], 'bullish_ob'] = True
                df.loc[df.index[i], 'ob_bottom'] = prev2['low']
                df.loc[df.index[i], 'ob_top'] = prev2['high']
            
            # Bearish Order Block: up candle followed by strong down move
            if (prev2['close'] > prev2['open'] and  # Up candle
                prev1['close'] < prev1['open'] and  # Down candle
                current['close'] < current['open'] and  # Down candle
                current['close'] < prev2['low']):  # Break below
                
                df.loc[df.index[i], 'bearish_ob'] = True
                df.loc[df.index[i], 'ob_bottom'] = prev2['low']
                df.loc[df.index[i], 'ob_top'] = prev2['high']
        
        return df
    
    def detect_fair_value_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Fair Value Gaps (FVG) - price inefficiencies/imbalances
        
        Bullish FVG: gap between candle[i-2].high and candle[i].low
        Bearish FVG: gap between candle[i-2].low and candle[i].high
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            DataFrame with FVG signals
        """
        df = df.copy()
        df['bullish_fvg'] = False
        df['bearish_fvg'] = False
        df['fvg_top'] = np.nan
        df['fvg_bottom'] = np.nan
        
        for i in range(2, len(df)):
            candle_i = df.iloc[i]
            candle_i_1 = df.iloc[i-1]
            candle_i_2 = df.iloc[i-2]
            
            # Bullish FVG: gap up (candle i-2 high < candle i low)
            if candle_i_2['high'] < candle_i['low']:
                gap_size = (candle_i['low'] - candle_i_2['high']) / candle_i_2['high']
                if gap_size >= self.fvg_threshold:
                    df.loc[df.index[i], 'bullish_fvg'] = True
                    df.loc[df.index[i], 'fvg_bottom'] = candle_i_2['high']
                    df.loc[df.index[i], 'fvg_top'] = candle_i['low']
            
            # Bearish FVG: gap down (candle i-2 low > candle i high)
            if candle_i_2['low'] > candle_i['high']:
                gap_size = (candle_i_2['low'] - candle_i['high']) / candle_i['high']
                if gap_size >= self.fvg_threshold:
                    df.loc[df.index[i], 'bearish_fvg'] = True
                    df.loc[df.index[i], 'fvg_bottom'] = candle_i['high']
                    df.loc[df.index[i], 'fvg_top'] = candle_i_2['low']
        
        return df
    
    def detect_market_structure_shift(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Market Structure Shift (MSS) - also called Change of Character (ChoCh)
        
        Bullish MSS: Break above previous swing high
        Bearish MSS: Break below previous swing low
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            DataFrame with market structure signals
        """
        df = df.copy()
        df['bullish_mss'] = False
        df['bearish_mss'] = False
        df['market_structure'] = 'neutral'  # neutral, bullish, bearish
        
        current_structure = 'neutral'
        
        for i in range(self.swing_length, len(df)):
            window = df.iloc[i-self.swing_length:i]
            current = df.iloc[i]
            
            swing_high = window['high'].max()
            swing_low = window['low'].min()
            
            # Bullish MSS: break above swing high in bearish/neutral structure
            if current['close'] > swing_high and current_structure != 'bullish':
                df.loc[df.index[i], 'bullish_mss'] = True
                current_structure = 'bullish'
            
            # Bearish MSS: break below swing low in bullish/neutral structure
            elif current['close'] < swing_low and current_structure != 'bearish':
                df.loc[df.index[i], 'bearish_mss'] = True
                current_structure = 'bearish'
            
            df.loc[df.index[i], 'market_structure'] = current_structure
        
        return df
    
    def is_kill_zone(self, timestamp: datetime) -> Tuple[bool, str]:
        """
        Check if timestamp is within ICT Kill Zones (optimal trading times)
        
        Kill Zones (UTC time):
        - London Kill Zone: 02:00 - 05:00 UTC
        - New York Kill Zone: 13:00 - 16:00 UTC (08:00 - 11:00 EST / 09:00 - 12:00 EDT)
        
        Args:
            timestamp: Datetime to check
            
        Returns:
            Tuple of (is_kill_zone, zone_name)
        """
        if not self.use_kill_zones:
            return True, "any_time"
        
        hour = timestamp.hour
        
        # London Kill Zone: 02:00 - 05:00 UTC
        if 2 <= hour < 5:
            return True, "london"
        
        # New York Kill Zone: 13:00 - 16:00 UTC
        if 13 <= hour < 16:
            return True, "new_york"
        
        return False, "none"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on ICT concepts
        
        Signal Rules:
        1. Entry after liquidity sweep + order block or FVG
        2. Confirm with market structure shift
        3. Only trade during kill zones (optional)
        
        Args:
            df: DataFrame with OHLC data and timestamp
            
        Returns:
            DataFrame with trading signals
        """
        df = df.copy()
        
        # Apply all ICT indicators
        df = self.detect_liquidity_sweeps(df)
        df = self.detect_order_blocks(df)
        df = self.detect_fair_value_gaps(df)
        df = self.detect_market_structure_shift(df)
        
        # Initialize signal columns
        df['signal'] = 0  # 1 = long, -1 = short, 0 = no signal
        df['entry_reason'] = ''
        
        for i in range(self.liquidity_lookback + 5, len(df)):
            current = df.iloc[i]
            
            # Check kill zone
            is_kz, zone = self.is_kill_zone(current.name)
            
            if not is_kz and self.use_kill_zones:
                continue
            
            # Look back a few candles for setup
            lookback_window = df.iloc[max(0, i-5):i]
            
            # BULLISH SETUP
            # Liquidity sweep + (Order Block or FVG) + Bullish MSS
            bullish_sweep = lookback_window['bullish_liquidity_sweep'].any()
            bullish_ob = lookback_window['bullish_ob'].any()
            bullish_fvg = lookback_window['bullish_fvg'].any()
            bullish_mss = lookback_window['bullish_mss'].any()
            
            if bullish_sweep and (bullish_ob or bullish_fvg) and bullish_mss:
                if df.loc[df.index[i], 'signal'] == 0:  # No conflicting signal
                    df.loc[df.index[i], 'signal'] = 1
                    reasons = []
                    if bullish_sweep:
                        reasons.append('LiqSweep')
                    if bullish_ob:
                        reasons.append('OB')
                    if bullish_fvg:
                        reasons.append('FVG')
                    if bullish_mss:
                        reasons.append('MSS')
                    df.loc[df.index[i], 'entry_reason'] = '+'.join(reasons) + f'+{zone}'
            
            # BEARISH SETUP
            # Liquidity sweep + (Order Block or FVG) + Bearish MSS
            bearish_sweep = lookback_window['bearish_liquidity_sweep'].any()
            bearish_ob = lookback_window['bearish_ob'].any()
            bearish_fvg = lookback_window['bearish_fvg'].any()
            bearish_mss = lookback_window['bearish_mss'].any()
            
            if bearish_sweep and (bearish_ob or bearish_fvg) and bearish_mss:
                if df.loc[df.index[i], 'signal'] == 0:  # No conflicting signal
                    df.loc[df.index[i], 'signal'] = -1
                    reasons = []
                    if bearish_sweep:
                        reasons.append('LiqSweep')
                    if bearish_ob:
                        reasons.append('OB')
                    if bearish_fvg:
                        reasons.append('FVG')
                    if bearish_mss:
                        reasons.append('MSS')
                    df.loc[df.index[i], 'entry_reason'] = '+'.join(reasons) + f'+{zone}'
        
        return df
    
    def calculate_position_size(
        self, 
        account_balance: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        """
        Calculate position size based on risk management
        
        Args:
            account_balance: Current account balance
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Position size
        """
        risk_amount = account_balance * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0
        
        position_size = risk_amount / risk_per_unit
        return position_size
    
    def get_entry_parameters(
        self, 
        df: pd.DataFrame, 
        signal_idx: int,
        account_balance: float
    ) -> Dict:
        """
        Calculate entry, stop loss, and take profit levels
        
        Args:
            df: DataFrame with signals
            signal_idx: Index where signal occurred
            account_balance: Current account balance
            
        Returns:
            Dictionary with entry parameters
        """
        signal_row = df.iloc[signal_idx]
        signal = signal_row['signal']
        
        if signal == 0:
            return None
        
        entry_price = signal_row['close']
        
        if signal == 1:  # Long
            # Stop loss: below recent swing low
            lookback = df.iloc[max(0, signal_idx-self.swing_length):signal_idx]
            stop_loss = lookback['low'].min() * 0.998  # 0.2% buffer
            
            # Take profit: risk/reward ratio
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.risk_reward_ratio)
            
        else:  # Short
            # Stop loss: above recent swing high
            lookback = df.iloc[max(0, signal_idx-self.swing_length):signal_idx]
            stop_loss = lookback['high'].max() * 1.002  # 0.2% buffer
            
            # Take profit: risk/reward ratio
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.risk_reward_ratio)
        
        position_size = self.calculate_position_size(account_balance, entry_price, stop_loss)
        
        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'signal': signal,
            'entry_reason': signal_row['entry_reason']
        }
