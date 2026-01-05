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
        risk_reward_ratio: float = 2.5,  # Changed default to adaptive baseline
        risk_per_trade: float = 0.02,
        swing_length: int = 10,
        fvg_threshold: float = 0.001,  # 0.1% gap minimum
        liquidity_lookback: int = 20,
        use_kill_zones: bool = True,
        use_adaptive_rr: bool = True,  # NEW: Use ATR-based R:R
        use_premium_discount: bool = True,  # NEW: Filter by price zones
        use_volume_confirmation: bool = True,  # NEW: Volume filter
        use_flexible_entry: bool = True  # NEW: Tier-based entry system
    ):
        """
        Initialize ICT Strategy
        
        Args:
            risk_reward_ratio: Risk/Reward ratio (2.5 = 1:2.5 default for adaptive)
            risk_per_trade: Risk per trade as fraction (0.02 = 2%)
            swing_length: Lookback period for swing highs/lows
            fvg_threshold: Minimum gap size for FVG (as percentage)
            liquidity_lookback: Candles to look back for liquidity zones
            use_kill_zones: Whether to filter trades by kill zones
            use_adaptive_rr: Use ATR-based adaptive risk/reward
            use_premium_discount: Filter entries by premium/discount zones
            use_volume_confirmation: Require volume confirmation
            use_flexible_entry: Use tiered entry system (more signals)
        """
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade = risk_per_trade
        self.swing_length = swing_length
        self.fvg_threshold = fvg_threshold
        self.liquidity_lookback = liquidity_lookback
        self.use_kill_zones = use_kill_zones
        self.use_adaptive_rr = use_adaptive_rr
        self.use_premium_discount = use_premium_discount
        self.use_volume_confirmation = use_volume_confirmation
        self.use_flexible_entry = use_flexible_entry
        
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
        
        IMPROVED Kill Zones (GMT time):
        - London Kill Zone: 07:00 - 12:00 GMT (5 hours - real European session)
        - New York Kill Zone: 13:00 - 20:00 GMT (7 hours - US session + overlap)
        - Asian Kill Zone: 00:00 - 03:00 GMT (3 hours - Asian session, lower priority)
        
        Total coverage: 15 hours/day (vs previous 6 hours)
        
        Args:
            timestamp: Datetime to check
            
        Returns:
            Tuple of (is_kill_zone, zone_name)
        """
        if not self.use_kill_zones:
            return True, "any_time"
        
        hour = timestamp.hour
        
        # Asian Kill Zone: 00:00 - 03:00 GMT
        if 0 <= hour < 3:
            return True, "asian"
        
        # London Kill Zone: 07:00 - 12:00 GMT (expanded from 02:00-05:00)
        if 7 <= hour < 12:
            return True, "london"
        
        # New York Kill Zone: 13:00 - 20:00 GMT (expanded from 13:00-16:00)
        if 13 <= hour < 20:
            return True, "new_york"
        
        return False, "none"
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range for volatility measurement
        
        Args:
            df: DataFrame with OHLC data
            period: ATR period (default 14)
            
        Returns:
            Series with ATR values
        """
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr
    
    def get_adaptive_risk_reward(self, df: pd.DataFrame, signal_idx: int) -> float:
        """
        Adaptive R:R based on ATR volatility
        
        High volatility (ATR > 1.5x avg): R:R 1:3 (ride the trend)
        Medium volatility (ATR 0.8-1.5x avg): R:R 1:2.5
        Low volatility (ATR < 0.8x avg): R:R 1:2 (quick scalp)
        
        Args:
            df: DataFrame with OHLC data
            signal_idx: Index of signal
            
        Returns:
            Risk/reward ratio
        """
        if not self.use_adaptive_rr:
            return self.risk_reward_ratio
        
        atr = self.calculate_atr(df)
        
        if signal_idx < 50:
            return self.risk_reward_ratio  # Not enough history
        
        current_atr = atr.iloc[signal_idx]
        avg_atr = atr.iloc[max(0, signal_idx-50):signal_idx].mean()
        
        if pd.isna(current_atr) or pd.isna(avg_atr) or avg_atr == 0:
            return self.risk_reward_ratio  # default
        
        atr_ratio = current_atr / avg_atr
        
        if atr_ratio > 1.5:
            return 3.0  # high volatility - bigger targets
        elif atr_ratio > 0.8:
            return 2.5  # medium
        else:
            return 2.0  # low volatility - quick exits
    
    def detect_premium_discount(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        """
        Determine if current price is in premium or discount zone
        
        Premium (upper 50%): Sell zone - SHORT only
        Discount (lower 50%): Buy zone - LONG only
        
        Args:
            df: DataFrame with OHLC data
            lookback: Period for high/low range
            
        Returns:
            DataFrame with zone column
        """
        df = df.copy()
        df['zone'] = 'neutral'
        
        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback:i+1]
            high_20 = window['high'].max()
            low_20 = window['low'].min()
            equilibrium = (high_20 + low_20) / 2
            
            current_price = df.iloc[i]['close']
            
            if current_price > equilibrium:
                df.loc[df.index[i], 'zone'] = 'premium'  # SHORT zone
            else:
                df.loc[df.index[i], 'zone'] = 'discount'  # LONG zone
        
        return df
    
    def has_volume_confirmation(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check if entry has volume confirmation
        Current volume should be > 1.2x average volume
        
        Args:
            df: DataFrame with volume data
            idx: Index to check
            
        Returns:
            True if volume confirmed
        """
        if not self.use_volume_confirmation:
            return True
        
        if 'tick_volume' not in df.columns and 'volume' not in df.columns:
            return True  # Skip if no volume data
        
        vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
        
        if idx < 20:
            return True  # Not enough history
        
        current_vol = df.iloc[idx][vol_col]
        avg_vol = df.iloc[max(0, idx-20):idx][vol_col].mean()
        
        if pd.isna(current_vol) or pd.isna(avg_vol) or avg_vol == 0:
            return True
        
        return current_vol > avg_vol * 1.2
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on ICT concepts
        
        IMPROVED Signal Rules:
        Tier 1 (high confidence): Liquidity Sweep + OB + MSS
        Tier 2 (medium confidence): MSS + (OB OR FVG)
        Tier 3 (low confidence): Liquidity Sweep + (OB OR FVG)
        
        Additional filters:
        - Kill zones (expanded to 15h/day)
        - Premium/Discount zones (optional)
        - Volume confirmation (optional)
        
        Args:
            df: DataFrame with OHLC data and timestamp
            
        Returns:
            DataFrame with trading signals and confidence levels
        """
        df = df.copy()
        
        # Apply all ICT indicators
        df = self.detect_liquidity_sweeps(df)
        df = self.detect_order_blocks(df)
        df = self.detect_fair_value_gaps(df)
        df = self.detect_market_structure_shift(df)
        
        # Apply premium/discount zones if enabled
        if self.use_premium_discount:
            df = self.detect_premium_discount(df)
        else:
            df['zone'] = 'neutral'
        
        # Initialize signal columns
        df['signal'] = 0  # 1 = long, -1 = short, 0 = no signal
        df['signal_confidence'] = ''  # high, medium, low
        df['entry_reason'] = ''
        
        for i in range(self.liquidity_lookback + 5, len(df)):
            current = df.iloc[i]
            
            # Check kill zone
            is_kz, zone = self.is_kill_zone(current.name)
            
            if not is_kz and self.use_kill_zones:
                continue
            
            # Check volume confirmation
            if not self.has_volume_confirmation(df, i):
                continue
            
            # Look back a few candles for setup
            lookback_window = df.iloc[max(0, i-5):i]
            
            # Get current zone
            current_zone = current['zone']
            
            # BULLISH SETUP
            bullish_sweep = lookback_window['bullish_liquidity_sweep'].any()
            bullish_ob = lookback_window['bullish_ob'].any()
            bullish_fvg = lookback_window['bullish_fvg'].any()
            bullish_mss = lookback_window['bullish_mss'].any()
            
            # Filter by premium/discount: LONG only in discount
            if self.use_premium_discount and current_zone == 'premium':
                pass  # Skip LONG in premium
            else:
                if self.use_flexible_entry:
                    # Tier 1 (strongest): Liquidity Sweep + OB + MSS
                    tier1 = bullish_sweep and bullish_ob and bullish_mss
                    # Tier 2 (strong): MSS + (OB OR FVG)
                    tier2 = bullish_mss and (bullish_ob or bullish_fvg)
                    # Tier 3 (medium): Liquidity Sweep + (OB OR FVG)
                    tier3 = bullish_sweep and (bullish_ob or bullish_fvg)
                    
                    confidence = ''
                    if tier1:
                        confidence = 'high'
                    elif tier2:
                        confidence = 'medium'
                    elif tier3:
                        confidence = 'low'
                    
                    if tier1 or tier2 or tier3:
                        if df.loc[df.index[i], 'signal'] == 0:  # No conflicting signal
                            df.loc[df.index[i], 'signal'] = 1
                            df.loc[df.index[i], 'signal_confidence'] = confidence
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
                else:
                    # Original strict conditions
                    if bullish_sweep and (bullish_ob or bullish_fvg) and bullish_mss:
                        if df.loc[df.index[i], 'signal'] == 0:
                            df.loc[df.index[i], 'signal'] = 1
                            df.loc[df.index[i], 'signal_confidence'] = 'high'
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
            bearish_sweep = lookback_window['bearish_liquidity_sweep'].any()
            bearish_ob = lookback_window['bearish_ob'].any()
            bearish_fvg = lookback_window['bearish_fvg'].any()
            bearish_mss = lookback_window['bearish_mss'].any()
            
            # Filter by premium/discount: SHORT only in premium
            if self.use_premium_discount and current_zone == 'discount':
                pass  # Skip SHORT in discount
            else:
                if self.use_flexible_entry:
                    # Tier 1 (strongest): Liquidity Sweep + OB + MSS
                    tier1 = bearish_sweep and bearish_ob and bearish_mss
                    # Tier 2 (strong): MSS + (OB OR FVG)
                    tier2 = bearish_mss and (bearish_ob or bearish_fvg)
                    # Tier 3 (medium): Liquidity Sweep + (OB OR FVG)
                    tier3 = bearish_sweep and (bearish_ob or bearish_fvg)
                    
                    confidence = ''
                    if tier1:
                        confidence = 'high'
                    elif tier2:
                        confidence = 'medium'
                    elif tier3:
                        confidence = 'low'
                    
                    if tier1 or tier2 or tier3:
                        if df.loc[df.index[i], 'signal'] == 0:  # No conflicting signal
                            df.loc[df.index[i], 'signal'] = -1
                            df.loc[df.index[i], 'signal_confidence'] = confidence
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
                else:
                    # Original strict conditions
                    if bearish_sweep and (bearish_ob or bearish_fvg) and bearish_mss:
                        if df.loc[df.index[i], 'signal'] == 0:
                            df.loc[df.index[i], 'signal'] = -1
                            df.loc[df.index[i], 'signal_confidence'] = 'high'
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
        
        IMPROVED: Now uses adaptive R:R based on ATR volatility
        
        Args:
            df: DataFrame with signals
            signal_idx: Index where signal occurred
            account_balance: Current account balance
            
        Returns:
            Dictionary with entry parameters including signal_confidence
        """
        signal_row = df.iloc[signal_idx]
        signal = signal_row['signal']
        
        if signal == 0:
            return None
        
        entry_price = signal_row['close']
        
        # Get adaptive risk/reward ratio
        risk_reward_ratio = self.get_adaptive_risk_reward(df, signal_idx)
        
        if signal == 1:  # Long
            # Stop loss: below recent swing low
            lookback = df.iloc[max(0, signal_idx-self.swing_length):signal_idx]
            stop_loss = lookback['low'].min() * 0.998  # 0.2% buffer
            
            # Take profit: risk/reward ratio
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * risk_reward_ratio)
            
        else:  # Short
            # Stop loss: above recent swing high
            lookback = df.iloc[max(0, signal_idx-self.swing_length):signal_idx]
            stop_loss = lookback['high'].max() * 1.002  # 0.2% buffer
            
            # Take profit: risk/reward ratio
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * risk_reward_ratio)
        
        position_size = self.calculate_position_size(account_balance, entry_price, stop_loss)
        
        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'signal': signal,
            'entry_reason': signal_row['entry_reason'],
            'signal_confidence': signal_row.get('signal_confidence', 'high'),
            'risk_reward_ratio': risk_reward_ratio
        }
