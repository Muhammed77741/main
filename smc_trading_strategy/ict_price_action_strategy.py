"""
ICT (Inner Circle Trader) Price Action Strategy
Based on key ICT concepts:
- Liquidity Sweeps (taking out stops)
- Order Blocks (institutional entry zones)
- Fair Value Gaps (imbalance zones)
- Market Structure Shifts (BOS/ChoCh)
- Kill Zones (London/New York sessions)
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
    5. Kill Zones - optimal trading times (London: 02:00-05:00, NY: 07:00-10:00 ET)
    """
    
    def __init__(
        self,
        risk_reward_ratio: float = 2.0,
        risk_per_trade: float = 0.02,
        swing_length: int = 10,
        fvg_threshold: float = 0.001,  # 0.1% gap minimum
        liquidity_lookback: int = 20,
        use_kill_zones: bool = True,
        fib_levels: list = None,
        killzone_only: bool = True,
        premium_discount_filter: bool = True,
        min_liquidity_sweep: int = 2
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
            fib_levels: Fibonacci levels for OTE (default [0.618, 0.786])
            killzone_only: Trade only in killzones
            premium_discount_filter: Filter by premium/discount zones
            min_liquidity_sweep: Minimum equal highs/lows for liquidity pool
        """
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade = risk_per_trade
        self.swing_length = swing_length
        self.fvg_threshold = fvg_threshold
        self.liquidity_lookback = liquidity_lookback
        self.use_kill_zones = use_kill_zones
        self.fib_levels = fib_levels if fib_levels is not None else [0.618, 0.786]
        self.killzone_only = killzone_only
        self.premium_discount_filter = premium_discount_filter
        self.min_liquidity_sweep = min_liquidity_sweep
        
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
    
    def detect_equal_highs_lows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Equal Highs/Lows - Liquidity Pools where stops accumulate
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            DataFrame with equal highs/lows signals
        """
        df = df.copy()
        df['equal_highs'] = False
        df['equal_lows'] = False
        
        tolerance = 0.002  # 0.2% tolerance for "equal" levels
        
        for i in range(self.swing_length * 2, len(df)):
            window = df.iloc[i-self.swing_length*2:i]
            current = df.iloc[i]
            
            # Find swing highs in window
            swing_highs = []
            for j in range(self.swing_length, len(window) - self.swing_length):
                if window['high'].iloc[j] == window['high'].iloc[j-self.swing_length:j+self.swing_length+1].max():
                    swing_highs.append(window['high'].iloc[j])
            
            # Check for equal highs
            if len(swing_highs) >= self.min_liquidity_sweep:
                for h1 in swing_highs:
                    equal_count = sum(1 for h2 in swing_highs if abs(h1 - h2) / h1 < tolerance)
                    if equal_count >= self.min_liquidity_sweep:
                        df.loc[df.index[i], 'equal_highs'] = True
                        break
            
            # Find swing lows in window
            swing_lows = []
            for j in range(self.swing_length, len(window) - self.swing_length):
                if window['low'].iloc[j] == window['low'].iloc[j-self.swing_length:j+self.swing_length+1].min():
                    swing_lows.append(window['low'].iloc[j])
            
            # Check for equal lows
            if len(swing_lows) >= self.min_liquidity_sweep:
                for l1 in swing_lows:
                    equal_count = sum(1 for l2 in swing_lows if abs(l1 - l2) / l1 < tolerance)
                    if equal_count >= self.min_liquidity_sweep:
                        df.loc[df.index[i], 'equal_lows'] = True
                        break
        
        return df
    
    def detect_premium_discount(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Premium vs Discount Zones based on candle equilibrium
        
        Premium zone (50-100%): Optimal for shorts
        Discount zone (0-50%): Optimal for longs
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            DataFrame with premium/discount zones
        """
        df = df.copy()
        df['premium_zone'] = False
        df['discount_zone'] = False
        df['equilibrium'] = np.nan
        
        for i in range(len(df)):
            candle_high = df['high'].iloc[i]
            candle_low = df['low'].iloc[i]
            candle_close = df['close'].iloc[i]
            
            # Calculate equilibrium (50% of candle)
            equilibrium = (candle_high + candle_low) / 2
            df.loc[df.index[i], 'equilibrium'] = equilibrium
            
            # Determine if price is in premium or discount
            candle_range = candle_high - candle_low
            if candle_range > 0:
                price_position = (candle_close - candle_low) / candle_range
                
                # Premium zone: 50-100% (upper half)
                if price_position >= 0.5:
                    df.loc[df.index[i], 'premium_zone'] = True
                # Discount zone: 0-50% (lower half)
                else:
                    df.loc[df.index[i], 'discount_zone'] = True
        
        return df
    
    def detect_ote_zone(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Optimal Trade Entry (OTE) zones using Fibonacci retracement
        
        OTE zones are 0.618-0.786 Fibonacci retracements - best entry points
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            DataFrame with OTE zone signals
        """
        df = df.copy()
        df['bullish_ote'] = False
        df['bearish_ote'] = False
        df['ote_level'] = np.nan
        
        for i in range(self.swing_length * 2, len(df)):
            window = df.iloc[i-self.swing_length*2:i]
            current = df.iloc[i]
            
            # Find recent swing high and low
            swing_high = window['high'].max()
            swing_low = window['low'].min()
            move_range = swing_high - swing_low
            
            if move_range == 0:
                continue
            
            # Bullish OTE: Price retraces to 0.618-0.786 of upward move
            if current['close'] > swing_low:
                retracement = (swing_high - current['close']) / move_range
                if 0.618 <= retracement <= 0.786:
                    df.loc[df.index[i], 'bullish_ote'] = True
                    df.loc[df.index[i], 'ote_level'] = retracement
            
            # Bearish OTE: Price retraces to 0.618-0.786 of downward move
            if current['close'] < swing_high:
                retracement = (current['close'] - swing_low) / move_range
                if 0.618 <= retracement <= 0.786:
                    df.loc[df.index[i], 'bearish_ote'] = True
                    df.loc[df.index[i], 'ote_level'] = retracement
        
        return df
    
    def detect_power_of_3(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Power of 3 (PO3) pattern:
        Phase 1: Accumulation (consolidation)
        Phase 2: Manipulation (Judas Swing - false breakout)
        Phase 3: Distribution (real move in opposite direction)
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            DataFrame with PO3 pattern signals
        """
        df = df.copy()
        df['po3_bullish'] = False
        df['po3_bearish'] = False
        df['po3_phase'] = ''
        
        lookback = 20  # Window for PO3 pattern
        
        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback:i]
            current = df.iloc[i]
            
            # Calculate price range and volatility
            window_high = window['high'].max()
            window_low = window['low'].min()
            window_range = window_high - window_low
            window_std = window['close'].std()
            
            if window_range == 0 or window_std == 0:
                continue
            
            # Phase 1: Consolidation (low volatility in first half)
            first_half = window.iloc[:lookback//2]
            first_half_range = first_half['high'].max() - first_half['low'].min()
            
            # Phase 2: Manipulation (spike in second half)
            second_half = window.iloc[lookback//2:]
            judas_swing_up = second_half['high'].max() > window_high * 0.995
            judas_swing_down = second_half['low'].min() < window_low * 1.005
            
            # Phase 3: Distribution (current reversal)
            # Bullish PO3: False breakdown (manipulation down) then strong move up
            if judas_swing_down and current['close'] > window_high * 0.99:
                df.loc[df.index[i], 'po3_bullish'] = True
                df.loc[df.index[i], 'po3_phase'] = 'distribution_bullish'
            
            # Bearish PO3: False breakout (manipulation up) then strong move down
            if judas_swing_up and current['close'] < window_low * 1.01:
                df.loc[df.index[i], 'po3_bearish'] = True
                df.loc[df.index[i], 'po3_phase'] = 'distribution_bearish'
        
        return df
    
    def is_kill_zone(self, timestamp: datetime) -> Tuple[bool, str]:
        """
        Check if timestamp is within ICT Kill Zones (optimal trading times)
        
        Kill Zones (GMT/UTC time):
        - London Kill Zone: 07:00 - 10:00 GMT (high priority)
        - New York Kill Zone: 12:00 - 15:00 GMT (high priority)
        - Asian Kill Zone: 01:00 - 05:00 GMT (low priority)
        
        Args:
            timestamp: Datetime to check
            
        Returns:
            Tuple of (is_kill_zone, zone_name)
        """
        if not self.use_kill_zones:
            return True, "any_time"
        
        hour = timestamp.hour
        
        # London Kill Zone: 07:00 - 10:00 GMT (high priority)
        if 7 <= hour < 10:
            return True, "london"
        
        # New York Kill Zone: 12:00 - 15:00 GMT (high priority)
        if 12 <= hour < 15:
            return True, "new_york"
        
        # Asian Kill Zone: 01:00 - 05:00 GMT (low priority)
        if 1 <= hour < 5:
            return True, "asian"
        
        return False, "none"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on ICT concepts
        
        Signal Rules (More practical approach):
        1. Primary: Liquidity sweep OR Order Block OR FVG
        2. Confirmation: Market Structure Shift (MSS)
        3. Optional filters: Premium/Discount zones, OTE, PO3 (add confluence)
        4. Killzone filter (if enabled)
        
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
        df = self.detect_equal_highs_lows(df)
        df = self.detect_premium_discount(df)
        df = self.detect_ote_zone(df)
        df = self.detect_power_of_3(df)
        
        # Initialize signal columns
        df['signal'] = 0  # 1 = long, -1 = short, 0 = no signal
        df['entry_reason'] = ''
        
        for i in range(self.liquidity_lookback + 5, len(df)):
            current = df.iloc[i]
            
            # Check kill zone
            is_kz, zone = self.is_kill_zone(current.name)
            
            if not is_kz and self.killzone_only:
                continue
            
            # Look back a few candles for setup
            lookback_window = df.iloc[max(0, i-5):i]
            
            # BULLISH SETUP
            # Core: (Liquidity sweep OR Order Block OR FVG) + MSS
            bullish_sweep = lookback_window['bullish_liquidity_sweep'].any()
            bullish_ob = lookback_window['bullish_ob'].any()
            bullish_fvg = lookback_window['bullish_fvg'].any()
            bullish_mss = lookback_window['bullish_mss'].any()
            
            # At least one ICT pattern + MSS confirmation
            has_bullish_pattern = bullish_sweep or bullish_ob or bullish_fvg
            
            # Additional confluence (adds to score but not required)
            equal_lows = lookback_window['equal_lows'].any()  # Liquidity pool
            bullish_ote = lookback_window['bullish_ote'].any()  # OTE zone
            po3_bullish = lookback_window['po3_bullish'].any()  # Power of 3
            
            # Premium/Discount filter (if enabled)
            in_discount = True
            if self.premium_discount_filter:
                in_discount = current['discount_zone']
            
            # Generate signal if conditions met
            if has_bullish_pattern and bullish_mss and in_discount:
                if df.loc[df.index[i], 'signal'] == 0:  # No conflicting signal
                    df.loc[df.index[i], 'signal'] = 1
                    reasons = []
                    if bullish_sweep:
                        reasons.append('LiqSweep')
                    if equal_lows:
                        reasons.append('EqualLows')
                    if bullish_ob:
                        reasons.append('OB')
                    if bullish_fvg:
                        reasons.append('FVG')
                    if bullish_mss:
                        reasons.append('MSS')
                    if bullish_ote:
                        reasons.append('OTE')
                    if po3_bullish:
                        reasons.append('PO3')
                    if self.premium_discount_filter:
                        reasons.append('Discount')
                    df.loc[df.index[i], 'entry_reason'] = '+'.join(reasons) + f'+{zone}'
            
            # BEARISH SETUP
            # Core: (Liquidity sweep OR Order Block OR FVG) + MSS
            bearish_sweep = lookback_window['bearish_liquidity_sweep'].any()
            bearish_ob = lookback_window['bearish_ob'].any()
            bearish_fvg = lookback_window['bearish_fvg'].any()
            bearish_mss = lookback_window['bearish_mss'].any()
            
            # At least one ICT pattern + MSS confirmation
            has_bearish_pattern = bearish_sweep or bearish_ob or bearish_fvg
            
            # Additional confluence
            equal_highs = lookback_window['equal_highs'].any()  # Liquidity pool
            bearish_ote = lookback_window['bearish_ote'].any()  # OTE zone
            po3_bearish = lookback_window['po3_bearish'].any()  # Power of 3
            
            # Premium/Discount filter (if enabled)
            in_premium = True
            if self.premium_discount_filter:
                in_premium = current['premium_zone']
            
            # Generate signal if conditions met
            if has_bearish_pattern and bearish_mss and in_premium:
                if df.loc[df.index[i], 'signal'] == 0:  # No conflicting signal
                    df.loc[df.index[i], 'signal'] = -1
                    reasons = []
                    if bearish_sweep:
                        reasons.append('LiqSweep')
                    if equal_highs:
                        reasons.append('EqualHighs')
                    if bearish_ob:
                        reasons.append('OB')
                    if bearish_fvg:
                        reasons.append('FVG')
                    if bearish_mss:
                        reasons.append('MSS')
                    if bearish_ote:
                        reasons.append('OTE')
                    if po3_bearish:
                        reasons.append('PO3')
                    if self.premium_discount_filter:
                        reasons.append('Premium')
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
