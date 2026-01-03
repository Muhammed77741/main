"""
Stock Long-Term SMC Strategy - Based on Fibonacci 1.618 Strategy
Адаптированная Fibonacci 1.618 стратегия для долгосрочной торговли акциями
Таймфреймы: 1D (день) и 1W (неделя)

Based on: fibonacci_1618_strategy.py
"""

import pandas as pd
import numpy as np
from typing import Dict

from smc_indicators import SMCIndicators
from volume_analysis import VolumeAnalyzer


class StockLongTermStrategy:
    """
    SMC стратегия для долгосрочной торговли акциями (день/неделя)
    
    Based on Fibonacci 1.618 Strategy with adaptations for stocks:
    1. Fibonacci extension 1.618 для динамических TP
    2. Больший swing_length для недельных/дневных таймфреймов
    3. Trend filters (SMA 50/200, Golden/Death Cross)
    4. Scoring system вместо жесткого AND logic
    5. ATR-based stops для адаптации к волатильности
    
    Key Innovation from 1.618:
    - TP = Entry + (Entry - SL) * 1.618 (Golden ratio)
    - Динамический R:R на основе структуры рынка
    """

    def __init__(
        self,
        timeframe: str = '1D',  # '4H', '1D' для дневного, '1W' для недельного
        fib_extension: float = 1.618,  # Fibonacci уровень для TP
        use_aggressive_tp: bool = False,  # Use 2.618 for aggressive TP
        risk_per_trade: float = 0.02,  # 2% риска на сделку
        swing_length: int = 15,  # Средний период для дневного графика
        volume_lookback: int = 3,  # Дней для подтверждения объема
        min_candle_quality: int = 30,  # Порог качества свечи
        min_volume_ratio: float = 1.0,  # Минимальное превышение объема
        min_risk_pct: float = 0.005,  # Минимум 0.5% риска
        max_risk_pct: float = 0.15,  # Максимум 15% риска
        long_only: bool = True,  # Только LONG для акций (нет шорта)
    ):
        """
        Initialize Stock Long-Term Strategy (Based on Fibonacci 1.618)
        
        Args:
            timeframe: '1D' или '1W'
            fib_extension: Fibonacci extension level (1.618 default, 2.618 aggressive)
            use_aggressive_tp: Use 2.618 instead of 1.618
            risk_per_trade: Risk per trade as fraction
            swing_length: Swing detection length (больше для долгосрока)
            volume_lookback: Candles to check for volume confirmation
            min_candle_quality: Minimum candle quality score
            min_volume_ratio: Minimum volume ratio vs average
            min_risk_pct: Minimum risk per trade (avoid too tight SL)
            max_risk_pct: Maximum risk per trade (avoid too wide SL)
        """
        self.timeframe = timeframe
        self.fib_extension = fib_extension
        self.use_aggressive_tp = use_aggressive_tp
        self.aggressive_fib = 2.618
        self.risk_per_trade = risk_per_trade
        self.swing_length = swing_length
        self.volume_lookback = volume_lookback
        self.min_candle_quality = min_candle_quality
        self.min_volume_ratio = min_volume_ratio
        self.min_risk_pct = min_risk_pct
        self.max_risk_pct = max_risk_pct
        self.long_only = long_only
        
        # Адаптация параметров под таймфрейм
        if timeframe == '4H':
            self.swing_length = 8  # Короче для 4H (похоже на Gold 1H)
            self.volume_lookback = 2
            self.min_candle_quality = 30
            self.cooldown_candles = 2
        elif timeframe == '1W':
            self.swing_length = 8  # Меньше свечей для недельного
            self.volume_lookback = 2
            self.min_candle_quality = 25  # Ниже для недельного
            self.cooldown_candles = 1
        else:  # 1D
            self.cooldown_candles = 3
        
        # Initialize components
        self.smc = SMCIndicators(swing_length=swing_length)
        self.volume_analyzer = VolumeAnalyzer(
            volume_ma_period=20 if timeframe == '1D' else 10
        )
        
        # Track last signal to avoid overtrading (from 1.618 strategy)
        self.last_signal_candle = -100
        self.cooldown_candles = 3 if timeframe == '1D' else 1

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run complete stock long-term strategy with Fibonacci TP
        
        Similar to Fibonacci1618Strategy.run_strategy()
        """
        print(f"\n🎯 Running Stock Long-Term Strategy ({self.timeframe})")
        print(f"   Mode: FIBONACCI {self.fib_extension} EXTENSION")
        print(f"   Swing Length: {self.swing_length}")
        print(f"   Aggressive TP (2.618): {self.use_aggressive_tp}")
        print(f"   Volume Lookback: {self.volume_lookback}")
        
        # Generate signals
        df = self.generate_signals(df)
        
        # Фильтр: только LONG если long_only=True (для акций обычно нет шорта)
        if self.long_only:
            short_signals = (df['signal'] == -1).sum()
            df.loc[df['signal'] == -1, 'signal'] = 0
            if short_signals > 0:
                print(f"   Long-only mode: Removed {short_signals} SHORT signals")
        
        # Apply Fibonacci TP (key innovation from 1.618 strategy)
        df = self._apply_fibonacci_tp(df)
        
        # Print summary
        total_signals = (df['signal'] != 0).sum()
        long_signals = (df['signal'] == 1).sum()
        short_signals = (df['signal'] == -1).sum()
        
        print(f"\n📊 Signals Generated:")
        print(f"   Total: {total_signals}")
        print(f"   Long: {long_signals}")
        print(f"   Short: {short_signals}")
        
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals for stocks based on SMC + Volume
        
        Similar structure to IntradayGoldStrategy but adapted for stocks
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
        df['signal_type'] = ''
        df['position_type'] = ''
        
        # Generate signals
        for i in range(self.swing_length + 20, len(df)):
            # Cooldown check (from 1.618 strategy)
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
                    
                    # Initial TP (will be recalculated with Fibonacci)
                    take_profit = entry_price + (entry_price - stop_loss) * 2.0
                    
                    # Risk check (from 1.618 strategy - important!)
                    risk_pct = abs(entry_price - stop_loss) / entry_price
                    if risk_pct < self.min_risk_pct or risk_pct > self.max_risk_pct:
                        continue
                    
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = entry_price
                    df.loc[df.index[i], 'stop_loss'] = stop_loss
                    df.loc[df.index[i], 'take_profit'] = take_profit
                    df.loc[df.index[i], 'candle_quality'] = long_details['candle_quality']
                    df.loc[df.index[i], 'signal_reason'] = long_details['reason']
                    df.loc[df.index[i], 'signal_type'] = long_details['signal_type']
                    df.loc[df.index[i], 'position_type'] = long_details['position_type']
                    
                    self.last_signal_candle = i
            
            # === SHORT SIGNAL ===
            elif current_trend == -1:
                short_signal, short_details = self._check_short_entry(df, i)
                
                if short_signal:
                    entry_price = df['close'].iloc[i]
                    stop_loss = self._calculate_stop_loss(df, i, direction=-1)
                    
                    # Initial TP (will be recalculated with Fibonacci)
                    take_profit = entry_price - (stop_loss - entry_price) * 2.0
                    
                    # Risk check
                    risk_pct = abs(stop_loss - entry_price) / entry_price
                    if risk_pct < self.min_risk_pct or risk_pct > self.max_risk_pct:
                        continue
                    
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = entry_price
                    df.loc[df.index[i], 'stop_loss'] = stop_loss
                    df.loc[df.index[i], 'take_profit'] = take_profit
                    df.loc[df.index[i], 'candle_quality'] = short_details['candle_quality']
                    df.loc[df.index[i], 'signal_reason'] = short_details['reason']
                    df.loc[df.index[i], 'signal_type'] = short_details['signal_type']
                    df.loc[df.index[i], 'position_type'] = short_details['position_type']
                    
                    self.last_signal_candle = i
        
        # Add BOS signals (from MultiSignalGoldStrategy)
        df = self._add_bos_signals(df)
        
        return df

    def _apply_fibonacci_tp(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply Fibonacci 1.618 extension for take profit levels
        
        KEY INNOVATION from fibonacci_1618_strategy.py:
        TP = Entry + (Entry - SL) * 1.618 (Golden ratio)
        
        This creates dynamic R:R based on market structure
        """
        df = df.copy()
        
        signals_modified = 0
        
        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue
            
            entry_price = df['entry_price'].iloc[i]
            stop_loss = df['stop_loss'].iloc[i]
            
            if pd.isna(entry_price) or pd.isna(stop_loss):
                continue
            
            # Calculate Fibonacci extension TP
            # Risk = Entry - SL
            risk = abs(entry_price - stop_loss)
            
            # Fibonacci extension: TP = Entry + Risk * Fib_Level
            if df['signal'].iloc[i] == 1:  # Long
                # Use 1.618 or 2.618 depending on settings
                fib_level = self.aggressive_fib if self.use_aggressive_tp else self.fib_extension
                new_tp = entry_price + (risk * fib_level)
            else:  # Short
                fib_level = self.aggressive_fib if self.use_aggressive_tp else self.fib_extension
                new_tp = entry_price - (risk * fib_level)
            
            # Update TP
            df.loc[df.index[i], 'take_profit'] = new_tp
            signals_modified += 1
        
        if signals_modified > 0:
            print(f"   Applied Fibonacci {self.fib_extension} TP to {signals_modified} signals")
        
        return df

    def _add_stock_specific_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add stock-specific indicators
        
        New addition for stocks (not in original 1.618 strategy)
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
        Check for long entry conditions using scoring system
        
        Adapted from simplified_smc_strategy.py but with scoring system
        """
        conditions = []
        score = 0
        details = {
            'candle_quality': 0, 
            'reason': '', 
            'signal_type': 'multi_signal',
            'position_type': 'swing'
        }
        
        # Scoring system: need at least 5 points to enter
        MIN_SCORE = 5
        
        # 1. Trend confirmation (2 points)
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
        
        # 4. Order Block or FVG (2 points each) - from 1.618 strategy
        lookback = 15 if self.timeframe == '1D' else 8
        
        if df['bullish_ob'].iloc[max(0, idx-lookback):idx+1].any():
            conditions.append('Bullish_OB')
            score += 2
        
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
                score += 1
        
        # 7. Liquidity sweep (1 point)
        if df['sell_side_liquidity'].iloc[max(0, idx-5):idx].any():
            conditions.append('Liquidity_Sweep')
            score += 1
        
        # 8. BOS confirmation (2 points)
        if df['bos'].iloc[idx]:
            conditions.append('BOS')
            score += 2
        
        # 9. Price action (1 point)
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
        Check for short entry conditions using scoring system
        """
        conditions = []
        score = 0
        details = {
            'candle_quality': 0, 
            'reason': '', 
            'signal_type': 'multi_signal',
            'position_type': 'swing'
        }
        
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
        
        if df['bearish_ob'].iloc[max(0, idx-lookback):idx+1].any():
            conditions.append('Bearish_OB')
            score += 2
        
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
            
            if df['rel_volume'].iloc[idx] >= self.min_volume_ratio * 1.5:
                score += 1
                conditions.append('Strong_Volume')
        
        # 6. Candle quality (1-2 points)
        if vol_details.get('current_quality', 0) >= self.min_candle_quality:
            quality = vol_details['current_quality']
            conditions.append(f"Quality_{quality}")
            score += 1
            if quality >= 60:
                score += 1
        
        # 7. Liquidity sweep (1 point)
        if df['buy_side_liquidity'].iloc[max(0, idx-5):idx].any():
            conditions.append('Liquidity_Sweep')
            score += 1
        
        # 8. BOS confirmation (2 points)
        if df['bos'].iloc[idx]:
            conditions.append('BOS')
            score += 2
        
        # 9. Price action (1 point)
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
        
        Combined approach from 1.618 strategy (swing-based) + ATR adaptation
        """
        atr = df['atr'].iloc[idx]
        current_price = df['close'].iloc[idx]
        
        if direction == 1:  # Long
            # Stop below recent swing low (from 1.618 strategy)
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
            
            # Ensure stop is at least min_risk_pct below entry
            min_stop = current_price * (1 - self.min_risk_pct)
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
            
            # Ensure stop is at least min_risk_pct above entry
            max_stop = current_price * (1 + self.min_risk_pct)
            stop = max(stop, max_stop)
            
            return stop

    def _add_bos_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add BOS (Break of Structure) signals
        
        From MultiSignalGoldStrategy in fibonacci_1618_strategy.py
        Adapted for stocks (no time filters, use SMA filters instead)
        """
        df = df.copy()
        
        bos_signals = 0
        
        for i in range(self.swing_length + 1, len(df)):
            # Skip if already has signal
            if df['signal'].iloc[i] != 0:
                continue
            
            # Cooldown check - not too recent from last BOS signal
            if 'signal_type' in df.columns:
                lookback_start = max(0, i - self.cooldown_candles)
                recent_signals = df['signal_type'].iloc[lookback_start:i]
                if any('bos' in str(s) for s in recent_signals if pd.notna(s)):
                    continue
            
            # Find swing high/low
            swing_window = df.iloc[i - self.swing_length:i]
            
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_close = df['close'].iloc[i]
            
            swing_high = swing_window['high'].max()
            swing_low = swing_window['low'].min()
            
            # Calculate risk for min risk check (from 1.618 strategy)
            risk_long = current_close - swing_low
            risk_short = swing_high - current_close
            
            # Bullish BOS: Break above swing high
            if current_high > swing_high and current_close > swing_high:
                # Min risk check (from 1.618: 0.3% for gold, 0.5% for stocks)
                if risk_long > current_close * self.min_risk_pct:
                    entry = current_close
                    sl = swing_low
                    risk = entry - sl
                    
                    # Fibonacci TP (key from 1.618 strategy!)
                    fib_level = self.aggressive_fib if self.use_aggressive_tp else self.fib_extension
                    tp = entry + (risk * fib_level)
                    
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = entry
                    df.loc[df.index[i], 'stop_loss'] = sl
                    df.loc[df.index[i], 'take_profit'] = tp
                    df.loc[df.index[i], 'signal_type'] = 'bos_long'
                    df.loc[df.index[i], 'position_type'] = 'swing'
                    bos_signals += 1
            
            # Bearish BOS: Break below swing low
            elif current_low < swing_low and current_close < swing_low:
                # Min risk check
                if risk_short > current_close * self.min_risk_pct:
                    entry = current_close
                    sl = swing_high
                    risk = sl - entry
                    
                    # Fibonacci TP
                    fib_level = self.aggressive_fib if self.use_aggressive_tp else self.fib_extension
                    tp = entry - (risk * fib_level)
                    
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = entry
                    df.loc[df.index[i], 'stop_loss'] = sl
                    df.loc[df.index[i], 'take_profit'] = tp
                    df.loc[df.index[i], 'signal_type'] = 'bos_short'
                    df.loc[df.index[i], 'position_type'] = 'swing'
                    bos_signals += 1
        
        if bos_signals > 0:
            print(f"   Added {bos_signals} BOS signals")
        
        return df


if __name__ == "__main__":
    print("Stock Long-Term Strategy - Based on Fibonacci 1.618")
    print("Use StockLongTermStrategy for trading")
