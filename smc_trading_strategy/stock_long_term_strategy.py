"""
Stock Long-Term SMC Strategy - For daily and weekly timeframes
Адаптированная SMC стратегия для долгосрочной торговли акциями
Таймфреймы: 1D (день) и 1W (неделя)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smc_indicators import SMCIndicators
from volume_analysis import VolumeAnalyzer
from typing import Dict


class StockLongTermStrategy:
    """
    SMC стратегия для долгосрочной торговли акциями (день/неделя)
    
    Отличия от внутридневной стратегии:
    1. Больший swing_length для недельных/дневных таймфреймов
    2. Более консервативный risk/reward для долгосрочных позиций
    3. Учет фундаментальных уровней поддержки/сопротивления
    4. Адаптация под более низкую волатильность акций vs криптовалют
    5. Нет временных фильтров (торговля на дневных свечах)
    """

    def __init__(
        self,
        timeframe: str = '1D',  # '1D' для дневного, '1W' для недельного
        risk_reward_ratio: float = 2.5,  # Более консервативный R:R
        risk_per_trade: float = 0.02,  # 2% риска на сделку
        swing_length: int = 15,  # Средний период для дневного графика
        volume_lookback: int = 3,  # Меньше дней для подтверждения
        min_candle_quality: int = 30,  # Более низкий порог для акций
        use_fibonacci_tp: bool = True,  # Fibonacci для TP
        fib_extension: float = 1.618,  # Классический уровень
        min_volume_ratio: float = 1.0,  # Минимальное превышение объема
    ):
        """
        Initialize Stock Long-Term Strategy
        
        Args:
            timeframe: '1D' или '1W'
            risk_reward_ratio: Risk/Reward ratio
            risk_per_trade: Risk per trade as fraction
            swing_length: Swing detection length (больше для долгосрока)
            volume_lookback: Candles to check for volume confirmation
            min_candle_quality: Minimum candle quality score
            use_fibonacci_tp: Use Fibonacci extensions for TP
            fib_extension: Fibonacci extension level (1.618, 2.618)
            min_volume_ratio: Minimum volume ratio vs average
        """
        self.timeframe = timeframe
        self.risk_reward_ratio = risk_reward_ratio
        self.risk_per_trade = risk_per_trade
        self.swing_length = swing_length
        self.volume_lookback = volume_lookback
        self.min_candle_quality = min_candle_quality
        self.use_fibonacci_tp = use_fibonacci_tp
        self.fib_extension = fib_extension
        self.min_volume_ratio = min_volume_ratio
        
        # Адаптация параметров под таймфрейм
        if timeframe == '1W':
            self.swing_length = 8  # Меньше свечей для недельного
            self.volume_lookback = 2
            self.risk_reward_ratio = 3.0  # Больший R:R для недельного
            self.min_candle_quality = 25  # Еще ниже для недельного
        
        # Initialize components
        self.smc = SMCIndicators(swing_length=swing_length)
        self.volume_analyzer = VolumeAnalyzer(
            volume_ma_period=20 if timeframe == '1D' else 10
        )
        
        # Track last signal to avoid overtrading
        self.last_signal_candle = -100
        self.cooldown_candles = 3 if timeframe == '1D' else 1

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals for stocks based on SMC + Volume
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with signals
        """
        df = df.copy()
        
        # Apply SMC indicators
        df = self.smc.apply_all_indicators(df)
        
        # Apply volume metrics
        df = self.volume_analyzer.calculate_volume_metrics(df)
        
        # Calculate additional indicators for stocks
        df = self._add_stock_specific_indicators(df)
        
        # Initialize signal columns
        df['signal'] = 0
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['candle_quality'] = 0
        df['signal_reason'] = ''
        df['position_type'] = ''  # 'swing', 'position', 'long-term'
        
        # Generate signals
        for i in range(self.swing_length + 20, len(df)):
            # Cooldown check
            if i - self.last_signal_candle < self.cooldown_candles:
                continue
            
            # Get current trend
            current_trend = df['trend'].iloc[i]
            
            if current_trend == 0:
                continue
            
            # === LONG SIGNAL ===
            if current_trend == 1:
                long_signal, long_details = self._check_long_entry(df, i)
                
                if long_signal:
                    entry_price = df['close'].iloc[i]
                    stop_loss = self._calculate_stop_loss(df, i, direction=1)
                    
                    # Calculate take profit
                    if self.use_fibonacci_tp:
                        take_profit = self._calculate_fibonacci_tp(
                            df, i, entry_price, stop_loss, direction=1
                        )
                    else:
                        take_profit = entry_price + (entry_price - stop_loss) * self.risk_reward_ratio
                    
                    # Risk check
                    risk_pct = abs(entry_price - stop_loss) / entry_price
                    if risk_pct < 0.005 or risk_pct > 0.15:  # 0.5% - 15% риск
                        continue
                    
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = entry_price
                    df.loc[df.index[i], 'stop_loss'] = stop_loss
                    df.loc[df.index[i], 'take_profit'] = take_profit
                    df.loc[df.index[i], 'candle_quality'] = long_details['candle_quality']
                    df.loc[df.index[i], 'signal_reason'] = long_details['reason']
                    df.loc[df.index[i], 'position_type'] = long_details['position_type']
                    
                    self.last_signal_candle = i
            
            # === SHORT SIGNAL ===
            elif current_trend == -1:
                short_signal, short_details = self._check_short_entry(df, i)
                
                if short_signal:
                    entry_price = df['close'].iloc[i]
                    stop_loss = self._calculate_stop_loss(df, i, direction=-1)
                    
                    # Calculate take profit
                    if self.use_fibonacci_tp:
                        take_profit = self._calculate_fibonacci_tp(
                            df, i, entry_price, stop_loss, direction=-1
                        )
                    else:
                        take_profit = entry_price - (stop_loss - entry_price) * self.risk_reward_ratio
                    
                    # Risk check
                    risk_pct = abs(stop_loss - entry_price) / entry_price
                    if risk_pct < 0.005 or risk_pct > 0.15:
                        continue
                    
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = entry_price
                    df.loc[df.index[i], 'stop_loss'] = stop_loss
                    df.loc[df.index[i], 'take_profit'] = take_profit
                    df.loc[df.index[i], 'candle_quality'] = short_details['candle_quality']
                    df.loc[df.index[i], 'signal_reason'] = short_details['reason']
                    df.loc[df.index[i], 'position_type'] = short_details['position_type']
                    
                    self.last_signal_candle = i
        
        return df

    def _add_stock_specific_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add stock-specific indicators
        
        Args:
            df: DataFrame
            
        Returns:
            DataFrame with additional indicators
        """
        # Moving averages for trend confirmation
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Price above/below major MAs
        df['above_sma50'] = df['close'] > df['sma_50']
        df['above_sma200'] = df['close'] > df['sma_200']
        
        # Golden cross / Death cross
        df['golden_cross'] = (df['sma_50'] > df['sma_200']) & (df['sma_50'].shift(1) <= df['sma_200'].shift(1))
        df['death_cross'] = (df['sma_50'] < df['sma_200']) & (df['sma_50'].shift(1) >= df['sma_200'].shift(1))
        
        # Average True Range for volatility
        df['atr'] = self._calculate_atr(df, period=14)
        
        # Relative volume
        df['rel_volume'] = df['volume'] / df['volume'].rolling(window=20).mean()
        
        return df

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr

    def _check_long_entry(self, df: pd.DataFrame, idx: int) -> tuple:
        """
        Check for long entry conditions for stocks using scoring system
        
        Returns:
            (signal, details_dict)
        """
        conditions = []
        score = 0
        details = {'candle_quality': 0, 'reason': '', 'position_type': 'swing'}
        
        # Scoring system: need at least 5 points to enter
        MIN_SCORE = 5
        
        # 1. Trend confirmation (3 points)
        if df['above_sma50'].iloc[idx]:
            conditions.append('Above_SMA50')
            score += 2
        
        # 2. Stronger trend (2 points)
        if df['above_sma200'].iloc[idx]:
            conditions.append('Above_SMA200')
            score += 2
            details['position_type'] = 'position'
        
        # 3. Golden cross bonus (2 points)
        if df['golden_cross'].iloc[max(0, idx-5):idx+1].any():
            conditions.append('Golden_Cross')
            score += 2
            details['position_type'] = 'long-term'
        
        # 4. Order Block or FVG (2 points each)
        lookback = 15 if self.timeframe == '1D' else 8
        
        # Recent bullish OB
        if df['bullish_ob'].iloc[max(0, idx-lookback):idx+1].any():
            conditions.append('Bullish_OB')
            score += 2
        
        # Recent bullish FVG
        if df['bullish_fvg'].iloc[max(0, idx-lookback):idx+1].any():
            conditions.append('Bullish_FVG')
            score += 2
        
        # 5. Volume confirmation (2 points)
        volume_confirmed, vol_details = self.volume_analyzer.check_volume_confirmation(
            df, idx, 'long', self.volume_lookback
        )
        
        if volume_confirmed:
            conditions.append(f"Volume_{vol_details['volume_strength']}")
            details['candle_quality'] = vol_details['current_quality']
            score += 2
            
            # Extra point for strong volume
            if df['rel_volume'].iloc[idx] >= self.min_volume_ratio * 1.5:
                score += 1
                conditions.append('Strong_Volume')
        
        # 6. Candle quality (1-2 points)
        if vol_details.get('current_quality', 0) >= self.min_candle_quality:
            quality = vol_details['current_quality']
            conditions.append(f"Quality_{quality}")
            score += 1
            if quality >= 60:
                score += 1  # Bonus for high quality
        
        # 7. Liquidity sweep (1 point)
        if df['sell_side_liquidity'].iloc[max(0, idx-5):idx].any():
            conditions.append('Liquidity_Sweep')
            score += 1
        
        # 8. BOS confirmation (2 points)
        if df['bos'].iloc[idx]:
            conditions.append('BOS')
            score += 2
        
        # 9. Price action (1 point) - bullish candle
        if df['close'].iloc[idx] > df['open'].iloc[idx]:
            conditions.append('Bullish_Candle')
            score += 1
        
        # Check minimum score
        if score < MIN_SCORE:
            return False, details
        
        # Signal confirmed
        conditions.append(f"Score_{score}")
        details['reason'] = ' + '.join(conditions)
        return True, details

    def _check_short_entry(self, df: pd.DataFrame, idx: int) -> tuple:
        """
        Check for short entry conditions for stocks using scoring system
        
        Returns:
            (signal, details_dict)
        """
        conditions = []
        score = 0
        details = {'candle_quality': 0, 'reason': '', 'position_type': 'swing'}
        
        # Scoring system: need at least 5 points to enter
        MIN_SCORE = 5
        
        # 1. Trend confirmation (2 points)
        if not df['above_sma50'].iloc[idx]:
            conditions.append('Below_SMA50')
            score += 2
        
        # 2. Stronger trend (2 points)
        if not df['above_sma200'].iloc[idx]:
            conditions.append('Below_SMA200')
            score += 2
            details['position_type'] = 'position'
        
        # 3. Death cross bonus (2 points)
        if df['death_cross'].iloc[max(0, idx-5):idx+1].any():
            conditions.append('Death_Cross')
            score += 2
            details['position_type'] = 'long-term'
        
        # 4. Order Block or FVG (2 points each)
        lookback = 15 if self.timeframe == '1D' else 8
        
        # Recent bearish OB
        if df['bearish_ob'].iloc[max(0, idx-lookback):idx+1].any():
            conditions.append('Bearish_OB')
            score += 2
        
        # Recent bearish FVG
        if df['bearish_fvg'].iloc[max(0, idx-lookback):idx+1].any():
            conditions.append('Bearish_FVG')
            score += 2
        
        # 5. Volume confirmation (2 points)
        volume_confirmed, vol_details = self.volume_analyzer.check_volume_confirmation(
            df, idx, 'short', self.volume_lookback
        )
        
        if volume_confirmed:
            conditions.append(f"Volume_{vol_details['volume_strength']}")
            details['candle_quality'] = vol_details['current_quality']
            score += 2
            
            # Extra point for strong volume
            if df['rel_volume'].iloc[idx] >= self.min_volume_ratio * 1.5:
                score += 1
                conditions.append('Strong_Volume')
        
        # 6. Candle quality (1-2 points)
        if vol_details.get('current_quality', 0) >= self.min_candle_quality:
            quality = vol_details['current_quality']
            conditions.append(f"Quality_{quality}")
            score += 1
            if quality >= 60:
                score += 1  # Bonus for high quality
        
        # 7. Liquidity sweep (1 point)
        if df['buy_side_liquidity'].iloc[max(0, idx-5):idx].any():
            conditions.append('Liquidity_Sweep')
            score += 1
        
        # 8. BOS confirmation (2 points)
        if df['bos'].iloc[idx]:
            conditions.append('BOS')
            score += 2
        
        # 9. Price action (1 point) - bearish candle
        if df['close'].iloc[idx] < df['open'].iloc[idx]:
            conditions.append('Bearish_Candle')
            score += 1
        
        # Check minimum score
        if score < MIN_SCORE:
            return False, details
        
        # Signal confirmed
        conditions.append(f"Score_{score}")
        details['reason'] = ' + '.join(conditions)
        return True, details

    def _calculate_stop_loss(self, df: pd.DataFrame, idx: int, direction: int) -> float:
        """
        Calculate stop loss based on swing points and ATR
        
        Args:
            df: DataFrame
            idx: Current index
            direction: 1 for long, -1 for short
            
        Returns:
            Stop loss price
        """
        atr = df['atr'].iloc[idx]
        current_price = df['close'].iloc[idx]
        
        if direction == 1:  # Long
            # Stop below recent swing low
            lookback = 30 if self.timeframe == '1D' else 15
            recent_swings = df[df['swing_low']].iloc[max(0, idx-lookback):idx]
            
            if len(recent_swings) > 0:
                swing_stop = recent_swings['low'].min()
            else:
                # Fallback: lowest low
                swing_stop = df['low'].iloc[max(0, idx-lookback):idx].min()
            
            # ATR-based stop
            atr_stop = current_price - (atr * 2)
            
            # Use whichever is closer but not too tight
            stop = max(swing_stop * 0.998, atr_stop)
            
            # Ensure stop is at least 0.5% below entry
            min_stop = current_price * 0.995
            stop = min(stop, min_stop)
            
            return stop
        
        else:  # Short
            # Stop above recent swing high
            lookback = 30 if self.timeframe == '1D' else 15
            recent_swings = df[df['swing_high']].iloc[max(0, idx-lookback):idx]
            
            if len(recent_swings) > 0:
                swing_stop = recent_swings['high'].max()
            else:
                # Fallback: highest high
                swing_stop = df['high'].iloc[max(0, idx-lookback):idx].max()
            
            # ATR-based stop
            atr_stop = current_price + (atr * 2)
            
            # Use whichever is closer but not too tight
            stop = min(swing_stop * 1.002, atr_stop)
            
            # Ensure stop is at least 0.5% above entry
            max_stop = current_price * 1.005
            stop = max(stop, max_stop)
            
            return stop

    def _calculate_fibonacci_tp(
        self, df: pd.DataFrame, idx: int, 
        entry_price: float, stop_loss: float, direction: int
    ) -> float:
        """
        Calculate take profit using Fibonacci extension
        
        Args:
            df: DataFrame
            idx: Current index
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 1 for long, -1 for short
            
        Returns:
            Take profit price
        """
        lookback = 30 if self.timeframe == '1D' else 15
        
        if direction == 1:  # Long
            # Find recent swing high and low
            recent_highs = df[df['swing_high']].iloc[max(0, idx-lookback):idx]
            recent_lows = df[df['swing_low']].iloc[max(0, idx-lookback):idx]
            
            if len(recent_highs) > 0 and len(recent_lows) > 0:
                swing_high = recent_highs['high'].max()
                swing_low = recent_lows['low'].min()
                
                # Fibonacci extension
                swing_range = swing_high - swing_low
                fib_tp = entry_price + (swing_range * self.fib_extension)
            else:
                # Fallback to R:R ratio
                fib_tp = entry_price + (entry_price - stop_loss) * self.risk_reward_ratio
        
        else:  # Short
            recent_highs = df[df['swing_high']].iloc[max(0, idx-lookback):idx]
            recent_lows = df[df['swing_low']].iloc[max(0, idx-lookback):idx]
            
            if len(recent_highs) > 0 and len(recent_lows) > 0:
                swing_high = recent_highs['high'].max()
                swing_low = recent_lows['low'].min()
                
                # Fibonacci extension
                swing_range = swing_high - swing_low
                fib_tp = entry_price - (swing_range * self.fib_extension)
            else:
                # Fallback to R:R ratio
                fib_tp = entry_price - (stop_loss - entry_price) * self.risk_reward_ratio
        
        return fib_tp

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run complete stock long-term strategy
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with signals
        """
        print(f"\n🎯 Running Stock Long-Term Strategy ({self.timeframe})")
        print(f"   Swing Length: {self.swing_length}")
        print(f"   R:R Ratio: {self.risk_reward_ratio}")
        print(f"   Fibonacci TP: {self.use_fibonacci_tp} ({self.fib_extension})")
        print(f"   Volume Lookback: {self.volume_lookback}")
        
        result_df = self.generate_signals(df)
        
        # Print summary
        total_signals = (result_df['signal'] != 0).sum()
        long_signals = (result_df['signal'] == 1).sum()
        short_signals = (result_df['signal'] == -1).sum()
        
        print(f"\n📊 Signals Generated:")
        print(f"   Total: {total_signals}")
        print(f"   Long: {long_signals}")
        print(f"   Short: {short_signals}")
        
        return result_df
