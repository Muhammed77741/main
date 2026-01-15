"""
Signal Analysis Dialog - Backtest signal generation for BTC/ETH
Shows signals that would have been generated in a date range
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QHeaderView, QDateEdit, QComboBox,
    QSpinBox, QProgressBar, QTextEdit, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QDate
from models import BotConfig

# Add trading_bots to path to access strategy
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_bots'))

try:
    import pandas as pd
    import numpy as np
    import ccxt
    from shared.pattern_recognition_strategy import PatternRecognitionStrategy
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Live Bot TP Configuration - Matches live bot settings
# For Crypto (BTC/ETH) - in percentage of price
CRYPTO_TREND_TP = {'tp1': 1.5, 'tp2': 2.75, 'tp3': 4.5}      # TREND mode
CRYPTO_RANGE_TP = {'tp1': 1.0, 'tp2': 1.75, 'tp3': 2.5}      # RANGE mode

# For XAUUSD (Gold) - in points
XAUUSD_TREND_TP = {'tp1': 30, 'tp2': 55, 'tp3': 90}          # TREND mode
XAUUSD_RANGE_TP = {'tp1': 20, 'tp2': 35, 'tp3': 50}          # RANGE mode

# Live Bot SL Configuration - Matches live bot settings
# For Crypto (BTC/ETH) - in percentage of price
CRYPTO_TREND_SL = 0.8     # TREND mode: 0.8% stop loss
CRYPTO_RANGE_SL = 0.6     # RANGE mode: 0.6% stop loss

# For XAUUSD (Gold) - in points
XAUUSD_TREND_SL = 16      # TREND mode: 16 points stop loss
XAUUSD_RANGE_SL = 12      # RANGE mode: 12 points stop loss

# Regime Detection Constants
REGIME_LOOKBACK = 100                    # Bars to analyze for regime detection
REGIME_STRUCTURAL_WINDOW = 20            # Window for structural trend analysis
REGIME_STRUCTURAL_THRESHOLD = 12         # Threshold for higher highs/lower lows
REGIME_TREND_SIGNALS_REQUIRED = 3        # Signals needed to classify as TREND


class SignalAnalysisWorker(QThread):
    """Background worker for signal analysis"""
    
    progress = Signal(str)  # Progress message
    finished = Signal(object)  # DataFrame with results
    error = Signal(str)  # Error message
    
    def __init__(self, symbol, days, start_date=None, end_date=None, 
                 tp_multiplier=162, sl_multiplier=100, use_trailing=False, trailing_pct=50, timeframe='1h', use_multi_tp=False,
                 custom_tp_levels=None, custom_sl_levels=None):
        super().__init__()
        self.symbol = symbol
        self.days = days
        self.start_date = start_date
        self.end_date = end_date
        self.tp_multiplier = tp_multiplier / 100.0  # Convert to decimal (162 -> 1.62)
        self.sl_multiplier = sl_multiplier / 100.0  # Convert to decimal (100 -> 1.0)
        self.use_trailing = use_trailing
        self.trailing_pct = trailing_pct / 100.0  # Convert to decimal (50 -> 0.5)
        self.timeframe = timeframe
        self.use_multi_tp = use_multi_tp
        self.custom_tp_levels = custom_tp_levels  # Custom TP levels override
        self.custom_sl_levels = custom_sl_levels  # Custom SL levels override
        
    def run(self):
        """Run signal analysis in background"""
        try:
            self.progress.emit(f"📊 Downloading {self.symbol} data...")
            
            # Initialize Binance
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            
            # Calculate time range
            if self.start_date and self.end_date:
                start_time = datetime.combine(self.start_date, datetime.min.time())
                end_time = datetime.combine(self.end_date, datetime.max.time())
            else:
                end_time = datetime.now()
                start_time = end_time - timedelta(days=self.days)
            
            self.progress.emit(f"   Period: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
            
            # Download data
            since = int(start_time.timestamp() * 1000)
            all_candles = []
            
            while True:
                candles = exchange.fetch_ohlcv(self.symbol, self.timeframe, since=since, limit=1000)
                if not candles:
                    break
                
                all_candles.extend(candles)
                since = candles[-1][0] + 1
                
                if candles[-1][0] >= int(end_time.timestamp() * 1000):
                    break
            
            if not all_candles:
                self.error.emit("No data downloaded")
                return
            
            self.progress.emit(f"✅ Downloaded {len(all_candles)} candles")
            
            # Convert to DataFrame
            df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Filter to exact date range
            df = df[(df.index >= start_time) & (df.index <= end_time)]
            
            self.progress.emit(f"🔍 Analyzing signals using PatternRecognitionStrategy...")
            
            # Initialize strategy (same as live bot)
            strategy = PatternRecognitionStrategy(fib_mode='standard')
            
            # Run strategy
            df_signals = strategy.run_strategy(df)
            
            # Find signals
            signals_df = df_signals[df_signals['signal'] != 0].copy()
            
            self.progress.emit(f"📊 Calculating trade outcomes for {len(signals_df)} signals...")
            
            # Calculate outcomes for each signal
            self._calculate_signal_outcomes(signals_df, df_signals)
            
            self.progress.emit(f"✅ Analysis complete! Found {len(signals_df)} signals")
            
            # Return results
            self.finished.emit(signals_df)
            
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
    
    def _detect_market_regime(self, full_df, signal_idx, lookback=REGIME_LOOKBACK):
        """
        Detect market regime at signal time: TREND or RANGE
        Uses same logic as live bot
        """
        # Get data up to and including signal candle
        signal_pos = full_df.index.get_loc(signal_idx)
        start_pos = max(0, signal_pos - lookback + 1)
        recent_data = full_df.iloc[start_pos:signal_pos + 1]
        
        if len(recent_data) < REGIME_LOOKBACK:
            return 'RANGE'
        
        # 1. EMA CROSSOVER
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()
        
        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]
        
        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
        ema_trend = ema_diff_pct > 0.5
        
        # 2. ATR (volatility)
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()
        
        high_volatility = atr > avg_atr * 1.05
        
        # 3. Directional movement
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()
        
        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35
        
        # 4. Consecutive movements
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        total_moves = up_moves + down_moves
        
        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.15
        
        # 5. Structural trend
        highs = recent_data['high'].values[-REGIME_STRUCTURAL_WINDOW:]
        lows = recent_data['low'].values[-REGIME_STRUCTURAL_WINDOW:]
        
        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
        
        structural_trend = (higher_highs > REGIME_STRUCTURAL_THRESHOLD) or (lower_lows > REGIME_STRUCTURAL_THRESHOLD)
        
        # Count trend signals
        trend_signals = sum([ema_trend, high_volatility, strong_direction, directional_bias, structural_trend])
        
        # Need 3+ signals for TREND
        return 'TREND' if trend_signals >= REGIME_TREND_SIGNALS_REQUIRED else 'RANGE'

    def _calculate_signal_outcomes(self, signals_df, full_df):
        """
        Calculate trade outcome for each signal
        Check if price hit TP or SL in the following candles
        Uses same TP/SL calculation logic as live bot (TREND/RANGE regime-based)
        Supports both single-TP and multi-TP modes
        """
        # Add outcome columns
        signals_df['outcome'] = 'Unknown'
        signals_df['profit_pct'] = 0.0
        signals_df['bars_held'] = 0
        
        # Add multi-TP column if enabled
        if self.use_multi_tp:
            signals_df['tp_levels_hit'] = 'None'
        
        # Add regime column to store market regime detection
        signals_df['regime'] = 'N/A'
        
        for idx, signal_row in signals_df.iterrows():
            signal_type = signal_row['signal']
            entry_price = signal_row['close']
            original_stop_loss = signal_row.get('stop_loss', 0)
            original_take_profit = signal_row.get('take_profit', 0)
            
            # Skip if SL or TP not set
            if pd.isna(original_stop_loss) or pd.isna(original_take_profit) or original_stop_loss == 0 or original_take_profit == 0:
                signals_df.loc[idx, 'outcome'] = 'No SL/TP'
                continue
            
            # Detect market regime at signal time (like live bot)
            regime = self._detect_market_regime(full_df, idx)
            
            # Store regime in dataframe for display
            signals_df.loc[idx, 'regime'] = regime
            
            # Calculate TP levels using live bot's logic
            if self.use_multi_tp:
                # Use live bot's regime-based TP levels (or custom overrides)
                is_xauusd = 'XAUUSD' in self.symbol.upper() or 'XAU' in self.symbol.upper()
                
                # Get TP configuration (custom or default)
                if self.custom_tp_levels:
                    # Use custom TP levels from GUI
                    if regime == 'TREND':
                        tp_config = self.custom_tp_levels['trend']
                    else:
                        tp_config = self.custom_tp_levels['range']
                else:
                    # Use default TP levels
                    if is_xauusd:
                        tp_config = XAUUSD_TREND_TP if regime == 'TREND' else XAUUSD_RANGE_TP
                    else:
                        tp_config = CRYPTO_TREND_TP if regime == 'TREND' else CRYPTO_RANGE_TP
                
                if is_xauusd:
                    # XAUUSD uses points
                    tp_config = XAUUSD_TREND_TP if regime == 'TREND' else XAUUSD_RANGE_TP
                    if signal_type == 1:  # BUY
                        tp1 = entry_price + tp_config['tp1']
                        tp2 = entry_price + tp_config['tp2']
                        tp3 = entry_price + tp_config['tp3']
                    else:  # SELL
                        tp1 = entry_price - tp_config['tp1']
                        tp2 = entry_price - tp_config['tp2']
                        tp3 = entry_price - tp_config['tp3']
                else:
                    # Crypto uses percentage
                    tp_config = CRYPTO_TREND_TP if regime == 'TREND' else CRYPTO_RANGE_TP
                    if signal_type == 1:  # BUY
                        tp1 = entry_price * (1 + tp_config['tp1'] / 100)
                        tp2 = entry_price * (1 + tp_config['tp2'] / 100)
                        tp3 = entry_price * (1 + tp_config['tp3'] / 100)
                    else:  # SELL
                        tp1 = entry_price * (1 - tp_config['tp1'] / 100)
                        tp2 = entry_price * (1 - tp_config['tp2'] / 100)
                        tp3 = entry_price * (1 - tp_config['tp3'] / 100)
                
                # Calculate SL using custom values or defaults
                if self.custom_sl_levels:
                    # Use custom SL levels from GUI
                    if regime == 'TREND':
                        sl_value = self.custom_sl_levels['trend']
                    else:
                        sl_value = self.custom_sl_levels['range']
                    
                    if is_xauusd:
                        # XAUUSD uses points
                        if signal_type == 1:  # BUY
                            stop_loss = entry_price - sl_value
                        else:  # SELL
                            stop_loss = entry_price + sl_value
                    else:
                        # Crypto uses percentage
                        if signal_type == 1:  # BUY
                            stop_loss = entry_price * (1 - sl_value / 100)
                        else:  # SELL
                            stop_loss = entry_price * (1 + sl_value / 100)
                else:
                    # Use original SL (or apply multiplier if set)
                    if signal_type == 1:  # BUY
                        risk = entry_price - original_stop_loss
                        stop_loss = entry_price - (risk * self.sl_multiplier)
                    else:  # SELL
                        risk = original_stop_loss - entry_price
                        stop_loss = entry_price + (risk * self.sl_multiplier)
            else:
                # Single TP mode: use custom multipliers
                if signal_type == 1:  # BUY
                    risk = entry_price - original_stop_loss
                    stop_loss = entry_price - (risk * self.sl_multiplier)
                    take_profit = entry_price + (risk * self.tp_multiplier)
                else:  # SELL
                    risk = original_stop_loss - entry_price
                    stop_loss = entry_price + (risk * self.sl_multiplier)
                    take_profit = entry_price - (risk * self.tp_multiplier)
            
            # Get future candles after this signal
            future_candles = full_df[full_df.index > idx]
            
            if len(future_candles) == 0:
                signals_df.loc[idx, 'outcome'] = 'No Data'
                continue
            
            # Route to appropriate calculation method
            if self.use_multi_tp:
                result = self._calculate_multi_tp_outcome_live_style(
                    signal_type, entry_price, stop_loss, tp1, tp2, tp3, future_candles
                )
                signals_df.loc[idx, 'outcome'] = result['outcome']
                signals_df.loc[idx, 'profit_pct'] = result['profit_pct']
                signals_df.loc[idx, 'bars_held'] = result['bars']
                signals_df.loc[idx, 'tp_levels_hit'] = result['tp_levels_hit']
            else:
                result = self._calculate_single_tp_outcome(
                    signal_type, entry_price, stop_loss, take_profit, future_candles
                )
                signals_df.loc[idx, 'outcome'] = result['outcome']
                signals_df.loc[idx, 'profit_pct'] = result['profit_pct']
                signals_df.loc[idx, 'bars_held'] = result['bars']
    
    def _calculate_multi_tp_outcome_live_style(self, signal_type, entry_price, stop_loss, tp1, tp2, tp3, future_candles):
        """
        Calculate outcome with multiple TP levels using live bot's specific TP prices
        TP1: close 50%, TP2: close 30%, TP3: close 20%
        SL moves to breakeven after TP1
        """
        # Track position and outcomes
        remaining_position = 1.0
        total_pnl_pct = 0.0
        tps_hit = []
        outcome = 'Timeout'
        bars = 0
        
        # Track which TPs have been hit
        tp1_hit = False
        tp2_hit = False
        tp3_hit = False
        
        # Check each candle
        for future_idx, future_candle in future_candles.iterrows():
            bars += 1
            
            if signal_type == 1:  # BUY signal
                # Check SL first
                if future_candle['low'] <= stop_loss:
                    # Hit stop loss
                    pnl = ((stop_loss - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * remaining_position
                    outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                    break
                
                # Check TP levels in order
                if not tp1_hit and future_candle['high'] >= tp1:
                    # TP1 hit - close 50%
                    pnl = ((tp1 - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.5
                    remaining_position -= 0.5
                    tps_hit.append('TP1')
                    tp1_hit = True
                    # Move SL to breakeven
                    stop_loss = entry_price
                
                if tp1_hit and not tp2_hit and future_candle['high'] >= tp2:
                    # TP2 hit - close 30%
                    pnl = ((tp2 - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.3
                    remaining_position -= 0.3
                    tps_hit.append('TP2')
                    tp2_hit = True
                
                if tp2_hit and not tp3_hit and future_candle['high'] >= tp3:
                    # TP3 hit - close 20%
                    pnl = ((tp3 - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.2
                    remaining_position -= 0.2
                    tps_hit.append('TP3')
                    tp3_hit = True
                    outcome = 'Win ✅'
                    break
            
            else:  # SELL signal
                # Check SL first
                if future_candle['high'] >= stop_loss:
                    # Hit stop loss
                    pnl = ((entry_price - stop_loss) / entry_price) * 100
                    total_pnl_pct += pnl * remaining_position
                    outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                    break
                
                # Check TP levels in order
                if not tp1_hit and future_candle['low'] <= tp1:
                    # TP1 hit - close 50%
                    pnl = ((entry_price - tp1) / entry_price) * 100
                    total_pnl_pct += pnl * 0.5
                    remaining_position -= 0.5
                    tps_hit.append('TP1')
                    tp1_hit = True
                    # Move SL to breakeven
                    stop_loss = entry_price
                
                if tp1_hit and not tp2_hit and future_candle['low'] <= tp2:
                    # TP2 hit - close 30%
                    pnl = ((entry_price - tp2) / entry_price) * 100
                    total_pnl_pct += pnl * 0.3
                    remaining_position -= 0.3
                    tps_hit.append('TP2')
                    tp2_hit = True
                
                if tp2_hit and not tp3_hit and future_candle['low'] <= tp3:
                    # TP3 hit - close 20%
                    pnl = ((entry_price - tp3) / entry_price) * 100
                    total_pnl_pct += pnl * 0.2
                    remaining_position -= 0.2
                    tps_hit.append('TP3')
                    tp3_hit = True
                    outcome = 'Win ✅'
                    break
            
            # Limit check to 100 bars
            if bars >= 100:
                outcome = 'Timeout'
                # Calculate current P&L for remaining position at timeout
                current_price = future_candle['close']
                if signal_type == 1:
                    pnl = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl = ((entry_price - current_price) / entry_price) * 100
                total_pnl_pct += pnl * remaining_position
                break
        
        return {
            'outcome': outcome,
            'profit_pct': total_pnl_pct,
            'bars': bars,
            'tp_levels_hit': '+'.join(tps_hit) if tps_hit else 'None'
        }
    

    def _calculate_multi_tp_outcome(self, signal_type, entry_price, stop_loss, risk, future_candles):
        """
        Calculate outcome with multiple TP levels and partial closes
        TP1: close 50%, TP2: close 30%, TP3: close 20%
        SL moves to breakeven after TP1
        """
        # Define TP levels using Fibonacci ratios
        if signal_type == 1:  # BUY
            tp1_price = entry_price + (risk * 1.0)   # 1R
            tp2_price = entry_price + (risk * 1.618) # 1.618R  
            tp3_price = entry_price + (risk * 2.618) # 2.618R
        else:  # SELL
            tp1_price = entry_price - (risk * 1.0)
            tp2_price = entry_price - (risk * 1.618)
            tp3_price = entry_price - (risk * 2.618)
        
        # Track position and outcomes
        remaining_position = 1.0
        total_pnl_pct = 0.0
        tps_hit = []
        outcome = 'Timeout'
        bars = 0
        
        # Track which TPs have been hit
        tp1_hit = False
        tp2_hit = False
        tp3_hit = False
        
        # Check each candle
        for future_idx, future_candle in future_candles.iterrows():
            bars += 1
            
            if signal_type == 1:  # BUY signal
                # Check SL first
                if future_candle['low'] <= stop_loss:
                    # Hit stop loss
                    pnl = ((stop_loss - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * remaining_position
                    outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                    break
                
                # Check TP levels in order
                if not tp1_hit and future_candle['high'] >= tp1_price:
                    # TP1 hit - close 50%
                    pnl = ((tp1_price - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.5
                    remaining_position -= 0.5
                    tps_hit.append('TP1')
                    tp1_hit = True
                    # Move SL to breakeven
                    stop_loss = entry_price
                
                if tp1_hit and not tp2_hit and future_candle['high'] >= tp2_price:
                    # TP2 hit - close 30%
                    pnl = ((tp2_price - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.3
                    remaining_position -= 0.3
                    tps_hit.append('TP2')
                    tp2_hit = True
                
                if tp2_hit and not tp3_hit and future_candle['high'] >= tp3_price:
                    # TP3 hit - close 20%
                    pnl = ((tp3_price - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.2
                    remaining_position -= 0.2
                    tps_hit.append('TP3')
                    tp3_hit = True
                    outcome = 'Win ✅'
                    break
            
            else:  # SELL signal
                # Check SL first
                if future_candle['high'] >= stop_loss:
                    # Hit stop loss
                    pnl = ((entry_price - stop_loss) / entry_price) * 100
                    total_pnl_pct += pnl * remaining_position
                    outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                    break
                
                # Check TP levels in order
                if not tp1_hit and future_candle['low'] <= tp1_price:
                    # TP1 hit - close 50%
                    pnl = ((entry_price - tp1_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.5
                    remaining_position -= 0.5
                    tps_hit.append('TP1')
                    tp1_hit = True
                    # Move SL to breakeven
                    stop_loss = entry_price
                
                if tp1_hit and not tp2_hit and future_candle['low'] <= tp2_price:
                    # TP2 hit - close 30%
                    pnl = ((entry_price - tp2_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.3
                    remaining_position -= 0.3
                    tps_hit.append('TP2')
                    tp2_hit = True
                
                if tp2_hit and not tp3_hit and future_candle['low'] <= tp3_price:
                    # TP3 hit - close 20%
                    pnl = ((entry_price - tp3_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.2
                    remaining_position -= 0.2
                    tps_hit.append('TP3')
                    tp3_hit = True
                    outcome = 'Win ✅'
                    break
            
            # Limit check to 100 bars
            if bars >= 100:
                outcome = 'Timeout'
                # Calculate current P&L for remaining position at timeout
                current_price = future_candle['close']
                if signal_type == 1:
                    pnl = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl = ((entry_price - current_price) / entry_price) * 100
                total_pnl_pct += pnl * remaining_position
                break
        
        return {
            'outcome': outcome,
            'profit_pct': total_pnl_pct,
            'bars': bars,
            'tp_levels_hit': '+'.join(tps_hit) if tps_hit else 'None'
        }
    
    
    def _calculate_single_tp_outcome(self, signal_type, entry_price, stop_loss, take_profit, future_candles):
        """
        Calculate outcome with single TP level (original behavior)
        """
        # Check each candle to see if TP or SL was hit
        outcome = 'Open'
        profit_pct = 0.0
        bars = 0
        trailing_active = False
        trailing_stop = stop_loss
        max_profit_price = entry_price
        
        for future_idx, future_candle in future_candles.iterrows():
            bars += 1
            
            if signal_type == 1:  # BUY signal
                # Update trailing stop if enabled and in profit
                if self.use_trailing and future_candle['high'] >= take_profit:
                    trailing_active = True
                    # Track highest price
                    if future_candle['high'] > max_profit_price:
                        max_profit_price = future_candle['high']
                        # Trail at configured % of profit
                        profit_distance = max_profit_price - entry_price
                        trailing_stop = entry_price + (profit_distance * self.trailing_pct)
                
                # Check if hit SL or trailing stop
                active_stop = trailing_stop if trailing_active else stop_loss
                if future_candle['low'] <= active_stop:
                    outcome = 'Loss ❌' if not trailing_active else 'Trailing Win ✅'
                    profit_pct = ((active_stop - entry_price) / entry_price) * 100
                    break
                # Check if hit TP (only if trailing not active)
                elif not trailing_active and future_candle['high'] >= take_profit:
                    if self.use_trailing:
                        # TP hit, activate trailing
                        trailing_active = True
                        max_profit_price = future_candle['high']
                        profit_distance = max_profit_price - entry_price
                        trailing_stop = entry_price + (profit_distance * self.trailing_pct)
                    else:
                        # No trailing, close at TP
                        outcome = 'Win ✅'
                        profit_pct = ((take_profit - entry_price) / entry_price) * 100
                        break
                    
            elif signal_type == -1:  # SELL signal
                # Update trailing stop if enabled and in profit
                if self.use_trailing and future_candle['low'] <= take_profit:
                    trailing_active = True
                    # Track lowest price
                    if future_candle['low'] < max_profit_price or max_profit_price == entry_price:
                        max_profit_price = future_candle['low']
                        # Trail at configured % of profit
                        profit_distance = entry_price - max_profit_price
                        trailing_stop = entry_price - (profit_distance * self.trailing_pct)
                
                # Check if hit SL or trailing stop
                active_stop = trailing_stop if trailing_active else stop_loss
                if future_candle['high'] >= active_stop:
                    outcome = 'Loss ❌' if not trailing_active else 'Trailing Win ✅'
                    profit_pct = ((entry_price - active_stop) / entry_price) * 100
                    break
                # Check if hit TP (only if trailing not active)
                elif not trailing_active and future_candle['low'] <= take_profit:
                    if self.use_trailing:
                        # TP hit, activate trailing
                        trailing_active = True
                        max_profit_price = future_candle['low']
                        profit_distance = entry_price - max_profit_price
                        trailing_stop = entry_price - (profit_distance * self.trailing_pct)
                    else:
                        # No trailing, close at TP
                        outcome = 'Win ✅'
                        profit_pct = ((entry_price - take_profit) / entry_price) * 100
                        break
            
            # Limit check to 100 bars
            if bars >= 100:
                outcome = 'Timeout'
                # Calculate current P&L at timeout
                current_price = future_candle['close']
                if signal_type == 1:
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                else:
                    profit_pct = ((entry_price - current_price) / entry_price) * 100
                break
        
        return {
            'outcome': outcome,
            'profit_pct': profit_pct,
            'bars': bars
        }



class SignalAnalysisWorkerMT5(QThread):
    """Background worker for signal analysis using MetaTrader5"""
    
    progress = Signal(str)  # Progress message
    finished = Signal(object)  # DataFrame with results
    error = Signal(str)  # Error message
    
    def __init__(self, symbol, days, start_date=None, end_date=None, 
                 tp_multiplier=162, sl_multiplier=100, use_trailing=False, trailing_pct=50, timeframe='1h', use_multi_tp=False,
                 custom_tp_levels=None, custom_sl_levels=None):
        super().__init__()
        self.symbol = symbol
        self.days = days
        self.start_date = start_date
        self.end_date = end_date
        self.tp_multiplier = tp_multiplier / 100.0  # Convert to decimal (162 -> 1.62)
        self.sl_multiplier = sl_multiplier / 100.0  # Convert to decimal (100 -> 1.0)
        self.use_trailing = use_trailing
        self.trailing_pct = trailing_pct / 100.0  # Convert to decimal (50 -> 0.5)
        self.timeframe = timeframe
        self.use_multi_tp = use_multi_tp
        self.custom_tp_levels = custom_tp_levels  # Custom TP levels override
        self.custom_sl_levels = custom_sl_levels  # Custom SL levels override
        
    def run(self):
        """Run signal analysis in background using MT5"""
        try:
            # Try to import MetaTrader5
            try:
                import MetaTrader5 as mt5
            except ImportError:
                self.error.emit(
                    "MetaTrader5 module not installed.\n\n"
                    "Please install it with: pip install MetaTrader5\n\n"
                    "Also ensure MetaTrader 5 terminal is installed and running."
                )
                return
            
            self.progress.emit(f"📊 Connecting to MetaTrader5 for {self.symbol}...")
            
            # Initialize MT5
            if not mt5.initialize():
                self.error.emit(
                    "Failed to initialize MetaTrader5.\n\n"
                    "Please ensure:\n"
                    "  • MT5 terminal is running\n"
                    "  • You are logged into your account\n"
                    "  • No other instances are using MT5 API"
                )
                return
            
            try:
                # Calculate time range
                if self.start_date and self.end_date:
                    start_time = datetime.combine(self.start_date, datetime.min.time())
                    end_time = datetime.combine(self.end_date, datetime.max.time())
                else:
                    end_time = datetime.now()
                    start_time = end_time - timedelta(days=self.days)
                
                self.progress.emit(f"   Period: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
                
                # Convert timeframe to MT5 format
                timeframe_map = {
                    '1m': mt5.TIMEFRAME_M1,
                    '5m': mt5.TIMEFRAME_M5,
                    '15m': mt5.TIMEFRAME_M15,
                    '30m': mt5.TIMEFRAME_M30,
                    '1h': mt5.TIMEFRAME_H1,
                    '4h': mt5.TIMEFRAME_H4,
                    '1d': mt5.TIMEFRAME_D1,
                    '1w': mt5.TIMEFRAME_W1,
                }
                mt5_timeframe = timeframe_map.get(self.timeframe, mt5.TIMEFRAME_H1)
                
                # Download data from MT5
                rates = mt5.copy_rates_range(self.symbol, mt5_timeframe, start_time, end_time)
                
                if rates is None or len(rates) == 0:
                    self.error.emit(
                        f"No data received from MT5 for {self.symbol}.\n\n"
                        f"Please ensure:\n"
                        f"  • {self.symbol} is available in Market Watch\n"
                        f"  • You have historical data for this period\n"
                        f"  • The symbol name is correct"
                    )
                    return
                
                self.progress.emit(f"✅ Downloaded {len(rates)} candles from MT5")
                
                # Convert to DataFrame
                df = pd.DataFrame(rates)
                df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('timestamp', inplace=True)
                
                # Rename columns to match expected format
                df.rename(columns={
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'tick_volume': 'volume'
                }, inplace=True)
                
                # Select only needed columns
                df = df[['open', 'high', 'low', 'close', 'volume']]
                
                self.progress.emit(f"🔍 Analyzing signals using PatternRecognitionStrategy...")
                
                # Initialize strategy (same as live bot)
                strategy = PatternRecognitionStrategy(fib_mode='standard')
                
                # Run strategy
                df_signals = strategy.run_strategy(df)
                
                # Find signals
                signals_df = df_signals[df_signals['signal'] != 0].copy()
                
                self.progress.emit(f"📊 Calculating trade outcomes for {len(signals_df)} signals...")
                
                # Calculate outcomes for each signal (reuse the same logic)
                self._calculate_signal_outcomes(signals_df, df_signals)
                
                self.progress.emit(f"✅ Analysis complete! Found {len(signals_df)} signals")
                
                # Return results
                self.finished.emit(signals_df)
                
            finally:
                # Always shutdown MT5
                mt5.shutdown()
                
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
    
    def _calculate_signal_outcomes(self, signals_df, full_df):
        """
        Calculate trade outcome for each signal
        Uses same TP/SL calculation logic as live bot (TREND/RANGE regime-based)
        Supports both single-TP and multi-TP modes
        """
        # Add outcome columns
        signals_df['outcome'] = 'Unknown'
        signals_df['profit_pct'] = 0.0
        signals_df['bars_held'] = 0
        
        # Add multi-TP column if enabled
        if self.use_multi_tp:
            signals_df['tp_levels_hit'] = 'None'
        
        # Add regime column to store market regime detection
        signals_df['regime'] = 'N/A'
        
        for idx, signal_row in signals_df.iterrows():
            signal_type = signal_row['signal']
            entry_price = signal_row['close']
            original_stop_loss = signal_row.get('stop_loss', 0)
            original_take_profit = signal_row.get('take_profit', 0)
            
            # Skip if SL or TP not set
            if pd.isna(original_stop_loss) or pd.isna(original_take_profit) or original_stop_loss == 0 or original_take_profit == 0:
                signals_df.loc[idx, 'outcome'] = 'No SL/TP'
                continue
            
            # Detect market regime at signal time (like live bot)
            regime = self._detect_market_regime(full_df, idx)
            
            # Store regime in dataframe for display
            signals_df.loc[idx, 'regime'] = regime
            
            # Calculate TP levels using live bot's logic
            if self.use_multi_tp:
                # Use live bot's regime-based TP levels (or custom overrides)
                is_xauusd = 'XAUUSD' in self.symbol.upper() or 'XAU' in self.symbol.upper()
                
                # Get TP configuration (custom or default)
                if self.custom_tp_levels:
                    # Use custom TP levels from GUI
                    if regime == 'TREND':
                        tp_config = self.custom_tp_levels['trend']
                    else:
                        tp_config = self.custom_tp_levels['range']
                else:
                    # Use default TP levels
                    if is_xauusd:
                        tp_config = XAUUSD_TREND_TP if regime == 'TREND' else XAUUSD_RANGE_TP
                    else:
                        tp_config = CRYPTO_TREND_TP if regime == 'TREND' else CRYPTO_RANGE_TP
                
                if is_xauusd:
                    # XAUUSD uses points
                    tp_config = XAUUSD_TREND_TP if regime == 'TREND' else XAUUSD_RANGE_TP
                    if signal_type == 1:  # BUY
                        tp1 = entry_price + tp_config['tp1']
                        tp2 = entry_price + tp_config['tp2']
                        tp3 = entry_price + tp_config['tp3']
                    else:  # SELL
                        tp1 = entry_price - tp_config['tp1']
                        tp2 = entry_price - tp_config['tp2']
                        tp3 = entry_price - tp_config['tp3']
                else:
                    # Crypto uses percentage
                    tp_config = CRYPTO_TREND_TP if regime == 'TREND' else CRYPTO_RANGE_TP
                    if signal_type == 1:  # BUY
                        tp1 = entry_price * (1 + tp_config['tp1'] / 100)
                        tp2 = entry_price * (1 + tp_config['tp2'] / 100)
                        tp3 = entry_price * (1 + tp_config['tp3'] / 100)
                    else:  # SELL
                        tp1 = entry_price * (1 - tp_config['tp1'] / 100)
                        tp2 = entry_price * (1 - tp_config['tp2'] / 100)
                        tp3 = entry_price * (1 - tp_config['tp3'] / 100)
                
                # Calculate SL using custom values or defaults
                if self.custom_sl_levels:
                    # Use custom SL levels from GUI
                    if regime == 'TREND':
                        sl_value = self.custom_sl_levels['trend']
                    else:
                        sl_value = self.custom_sl_levels['range']
                    
                    if is_xauusd:
                        # XAUUSD uses points
                        if signal_type == 1:  # BUY
                            stop_loss = entry_price - sl_value
                        else:  # SELL
                            stop_loss = entry_price + sl_value
                    else:
                        # Crypto uses percentage
                        if signal_type == 1:  # BUY
                            stop_loss = entry_price * (1 - sl_value / 100)
                        else:  # SELL
                            stop_loss = entry_price * (1 + sl_value / 100)
                else:
                    # Use original SL (or apply multiplier if set)
                    if signal_type == 1:  # BUY
                        risk = entry_price - original_stop_loss
                        stop_loss = entry_price - (risk * self.sl_multiplier)
                    else:  # SELL
                        risk = original_stop_loss - entry_price
                        stop_loss = entry_price + (risk * self.sl_multiplier)
            else:
                # Single TP mode: use custom multipliers
                if signal_type == 1:  # BUY
                    risk = entry_price - original_stop_loss
                    stop_loss = entry_price - (risk * self.sl_multiplier)
                    take_profit = entry_price + (risk * self.tp_multiplier)
                else:  # SELL
                    risk = original_stop_loss - entry_price
                    stop_loss = entry_price + (risk * self.sl_multiplier)
                    take_profit = entry_price - (risk * self.tp_multiplier)
            
            # Get future candles after this signal
            future_candles = full_df[full_df.index > idx]
            
            if len(future_candles) == 0:
                signals_df.loc[idx, 'outcome'] = 'No Data'
                continue
            
            # Route to appropriate calculation method
            if self.use_multi_tp:
                result = self._calculate_multi_tp_outcome_live_style(
                    signal_type, entry_price, stop_loss, tp1, tp2, tp3, future_candles
                )
                signals_df.loc[idx, 'outcome'] = result['outcome']
                signals_df.loc[idx, 'profit_pct'] = result['profit_pct']
                signals_df.loc[idx, 'bars_held'] = result['bars']
                signals_df.loc[idx, 'tp_levels_hit'] = result['tp_levels_hit']
            else:
                result = self._calculate_single_tp_outcome(
                    signal_type, entry_price, stop_loss, take_profit, future_candles
                )
                signals_df.loc[idx, 'outcome'] = result['outcome']
                signals_df.loc[idx, 'profit_pct'] = result['profit_pct']
                signals_df.loc[idx, 'bars_held'] = result['bars']
    
    def _detect_market_regime(self, full_df, signal_idx, lookback=REGIME_LOOKBACK):
        """
        Detect market regime at signal time: TREND or RANGE
        Uses same logic as live bot
        """
        # Get data up to and including signal candle
        signal_pos = full_df.index.get_loc(signal_idx)
        start_pos = max(0, signal_pos - lookback + 1)
        recent_data = full_df.iloc[start_pos:signal_pos + 1]
        
        if len(recent_data) < REGIME_LOOKBACK:
            return 'RANGE'
        
        # 1. EMA CROSSOVER
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()
        
        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]
        
        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
        ema_trend = ema_diff_pct > 0.5
        
        # 2. ATR (volatility)
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()
        
        high_volatility = atr > avg_atr * 1.05
        
        # 3. Directional movement
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()
        
        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35
        
        # 4. Consecutive movements
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        total_moves = up_moves + down_moves
        
        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.15
        
        # 5. Structural trend
        highs = recent_data['high'].values[-REGIME_STRUCTURAL_WINDOW:]
        lows = recent_data['low'].values[-REGIME_STRUCTURAL_WINDOW:]
        
        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
        
        structural_trend = (higher_highs > REGIME_STRUCTURAL_THRESHOLD) or (lower_lows > REGIME_STRUCTURAL_THRESHOLD)
        
        # Count trend signals
        trend_signals = sum([ema_trend, high_volatility, strong_direction, directional_bias, structural_trend])
        
        # Need 3+ signals for TREND
        return 'TREND' if trend_signals >= REGIME_TREND_SIGNALS_REQUIRED else 'RANGE'

    def _calculate_multi_tp_outcome_live_style(self, signal_type, entry_price, stop_loss, tp1, tp2, tp3, future_candles):
        """
        Calculate outcome with multiple TP levels using live bot's specific TP prices
        TP1: close 50%, TP2: close 30%, TP3: close 20%
        SL moves to breakeven after TP1
        """
        # Track position and outcomes
        remaining_position = 1.0
        total_pnl_pct = 0.0
        tps_hit = []
        outcome = 'Timeout'
        bars = 0
        
        # Track which TPs have been hit
        tp1_hit = False
        tp2_hit = False
        tp3_hit = False
        
        # Check each candle
        for future_idx, future_candle in future_candles.iterrows():
            bars += 1
            
            if signal_type == 1:  # BUY signal
                # Check SL first
                if future_candle['low'] <= stop_loss:
                    # Hit stop loss
                    pnl = ((stop_loss - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * remaining_position
                    outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                    break
                
                # Check TP levels in order
                if not tp1_hit and future_candle['high'] >= tp1:
                    # TP1 hit - close 50%
                    pnl = ((tp1 - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.5
                    remaining_position -= 0.5
                    tps_hit.append('TP1')
                    tp1_hit = True
                    # Move SL to breakeven
                    stop_loss = entry_price
                
                if tp1_hit and not tp2_hit and future_candle['high'] >= tp2:
                    # TP2 hit - close 30%
                    pnl = ((tp2 - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.3
                    remaining_position -= 0.3
                    tps_hit.append('TP2')
                    tp2_hit = True
                
                if tp2_hit and not tp3_hit and future_candle['high'] >= tp3:
                    # TP3 hit - close 20%
                    pnl = ((tp3 - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.2
                    remaining_position -= 0.2
                    tps_hit.append('TP3')
                    tp3_hit = True
                    outcome = 'Win ✅'
                    break
            
            else:  # SELL signal
                # Check SL first
                if future_candle['high'] >= stop_loss:
                    # Hit stop loss
                    pnl = ((entry_price - stop_loss) / entry_price) * 100
                    total_pnl_pct += pnl * remaining_position
                    outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                    break
                
                # Check TP levels in order
                if not tp1_hit and future_candle['low'] <= tp1:
                    # TP1 hit - close 50%
                    pnl = ((entry_price - tp1) / entry_price) * 100
                    total_pnl_pct += pnl * 0.5
                    remaining_position -= 0.5
                    tps_hit.append('TP1')
                    tp1_hit = True
                    # Move SL to breakeven
                    stop_loss = entry_price
                
                if tp1_hit and not tp2_hit and future_candle['low'] <= tp2:
                    # TP2 hit - close 30%
                    pnl = ((entry_price - tp2) / entry_price) * 100
                    total_pnl_pct += pnl * 0.3
                    remaining_position -= 0.3
                    tps_hit.append('TP2')
                    tp2_hit = True
                
                if tp2_hit and not tp3_hit and future_candle['low'] <= tp3:
                    # TP3 hit - close 20%
                    pnl = ((entry_price - tp3) / entry_price) * 100
                    total_pnl_pct += pnl * 0.2
                    remaining_position -= 0.2
                    tps_hit.append('TP3')
                    tp3_hit = True
                    outcome = 'Win ✅'
                    break
            
            # Limit check to 100 bars
            if bars >= 100:
                outcome = 'Timeout'
                # Calculate current P&L for remaining position at timeout
                current_price = future_candle['close']
                if signal_type == 1:
                    pnl = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl = ((entry_price - current_price) / entry_price) * 100
                total_pnl_pct += pnl * remaining_position
                break
        
        return {
            'outcome': outcome,
            'profit_pct': total_pnl_pct,
            'bars': bars,
            'tp_levels_hit': '+'.join(tps_hit) if tps_hit else 'None'
        }


    def _calculate_multi_tp_outcome(self, signal_type, entry_price, stop_loss, risk, future_candles):
        """
        Calculate outcome with multiple TP levels and partial closes
        TP1: close 50%, TP2: close 30%, TP3: close 20%
        SL moves to breakeven after TP1
        """
        # Define TP levels using Fibonacci ratios
        if signal_type == 1:  # BUY
            tp1_price = entry_price + (risk * 1.0)   # 1R
            tp2_price = entry_price + (risk * 1.618) # 1.618R  
            tp3_price = entry_price + (risk * 2.618) # 2.618R
        else:  # SELL
            tp1_price = entry_price - (risk * 1.0)
            tp2_price = entry_price - (risk * 1.618)
            tp3_price = entry_price - (risk * 2.618)
        
        # Track position and outcomes
        remaining_position = 1.0
        total_pnl_pct = 0.0
        tps_hit = []
        outcome = 'Timeout'
        bars = 0
        
        # Track which TPs have been hit
        tp1_hit = False
        tp2_hit = False
        tp3_hit = False
        
        # Check each candle
        for future_idx, future_candle in future_candles.iterrows():
            bars += 1
            
            if signal_type == 1:  # BUY signal
                # Check SL first
                if future_candle['low'] <= stop_loss:
                    # Hit stop loss
                    pnl = ((stop_loss - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * remaining_position
                    outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                    break
                
                # Check TP levels in order
                if not tp1_hit and future_candle['high'] >= tp1_price:
                    # TP1 hit - close 50%
                    pnl = ((tp1_price - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.5
                    remaining_position -= 0.5
                    tps_hit.append('TP1')
                    tp1_hit = True
                    # Move SL to breakeven
                    stop_loss = entry_price
                
                if tp1_hit and not tp2_hit and future_candle['high'] >= tp2_price:
                    # TP2 hit - close 30%
                    pnl = ((tp2_price - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.3
                    remaining_position -= 0.3
                    tps_hit.append('TP2')
                    tp2_hit = True
                
                if tp2_hit and not tp3_hit and future_candle['high'] >= tp3_price:
                    # TP3 hit - close 20%
                    pnl = ((tp3_price - entry_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.2
                    remaining_position -= 0.2
                    tps_hit.append('TP3')
                    tp3_hit = True
                    outcome = 'Win ✅'
                    break
            
            else:  # SELL signal
                # Check SL first
                if future_candle['high'] >= stop_loss:
                    # Hit stop loss
                    pnl = ((entry_price - stop_loss) / entry_price) * 100
                    total_pnl_pct += pnl * remaining_position
                    outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                    break
                
                # Check TP levels in order
                if not tp1_hit and future_candle['low'] <= tp1_price:
                    # TP1 hit - close 50%
                    pnl = ((entry_price - tp1_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.5
                    remaining_position -= 0.5
                    tps_hit.append('TP1')
                    tp1_hit = True
                    # Move SL to breakeven
                    stop_loss = entry_price
                
                if tp1_hit and not tp2_hit and future_candle['low'] <= tp2_price:
                    # TP2 hit - close 30%
                    pnl = ((entry_price - tp2_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.3
                    remaining_position -= 0.3
                    tps_hit.append('TP2')
                    tp2_hit = True
                
                if tp2_hit and not tp3_hit and future_candle['low'] <= tp3_price:
                    # TP3 hit - close 20%
                    pnl = ((entry_price - tp3_price) / entry_price) * 100
                    total_pnl_pct += pnl * 0.2
                    remaining_position -= 0.2
                    tps_hit.append('TP3')
                    tp3_hit = True
                    outcome = 'Win ✅'
                    break
            
            # Limit check to 100 bars
            if bars >= 100:
                outcome = 'Timeout'
                # Calculate current P&L for remaining position at timeout
                current_price = future_candle['close']
                if signal_type == 1:
                    pnl = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl = ((entry_price - current_price) / entry_price) * 100
                total_pnl_pct += pnl * remaining_position
                break
        
        return {
            'outcome': outcome,
            'profit_pct': total_pnl_pct,
            'bars': bars,
            'tp_levels_hit': '+'.join(tps_hit) if tps_hit else 'None'
        }
    
    def _calculate_single_tp_outcome(self, signal_type, entry_price, stop_loss, take_profit, future_candles):
        """
        Calculate outcome with single TP level (original behavior)
        """
        # Check each candle to see if TP or SL was hit
        outcome = 'Open'
        profit_pct = 0.0
        bars = 0
        trailing_active = False
        trailing_stop = stop_loss
        max_profit_price = entry_price
        
        for future_idx, future_candle in future_candles.iterrows():
            bars += 1
            
            if signal_type == 1:  # BUY signal
                # Update trailing stop if enabled and in profit
                if self.use_trailing and future_candle['high'] >= take_profit:
                    trailing_active = True
                    # Track highest price
                    if future_candle['high'] > max_profit_price:
                        max_profit_price = future_candle['high']
                        # Trail at configured % of profit
                        profit_distance = max_profit_price - entry_price
                        trailing_stop = entry_price + (profit_distance * self.trailing_pct)
                
                # Check if hit SL or trailing stop
                active_stop = trailing_stop if trailing_active else stop_loss
                if future_candle['low'] <= active_stop:
                    outcome = 'Loss ❌' if not trailing_active else 'Trailing Win ✅'
                    profit_pct = ((active_stop - entry_price) / entry_price) * 100
                    break
                # Check if hit TP (only if trailing not active)
                elif not trailing_active and future_candle['high'] >= take_profit:
                    if self.use_trailing:
                        # TP hit, activate trailing
                        trailing_active = True
                        max_profit_price = future_candle['high']
                        profit_distance = max_profit_price - entry_price
                        trailing_stop = entry_price + (profit_distance * self.trailing_pct)
                    else:
                        # No trailing, close at TP
                        outcome = 'Win ✅'
                        profit_pct = ((take_profit - entry_price) / entry_price) * 100
                        break
                    
            elif signal_type == -1:  # SELL signal
                # Update trailing stop if enabled and in profit
                if self.use_trailing and future_candle['low'] <= take_profit:
                    trailing_active = True
                    # Track lowest price
                    if future_candle['low'] < max_profit_price or max_profit_price == entry_price:
                        max_profit_price = future_candle['low']
                        # Trail at configured % of profit
                        profit_distance = entry_price - max_profit_price
                        trailing_stop = entry_price - (profit_distance * self.trailing_pct)
                
                # Check if hit SL or trailing stop
                active_stop = trailing_stop if trailing_active else stop_loss
                if future_candle['high'] >= active_stop:
                    outcome = 'Loss ❌' if not trailing_active else 'Trailing Win ✅'
                    profit_pct = ((entry_price - active_stop) / entry_price) * 100
                    break
                # Check if hit TP (only if trailing not active)
                elif not trailing_active and future_candle['low'] <= take_profit:
                    if self.use_trailing:
                        # TP hit, activate trailing
                        trailing_active = True
                        max_profit_price = future_candle['low']
                        profit_distance = entry_price - max_profit_price
                        trailing_stop = entry_price - (profit_distance * self.trailing_pct)
                    else:
                        # No trailing, close at TP
                        outcome = 'Win ✅'
                        profit_pct = ((entry_price - take_profit) / entry_price) * 100
                        break
            
            # Limit check to 100 bars
            if bars >= 100:
                outcome = 'Timeout'
                # Calculate current P&L at timeout
                current_price = future_candle['close']
                if signal_type == 1:
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                else:
                    profit_pct = ((entry_price - current_price) / entry_price) * 100
                break
        
        return {
            'outcome': outcome,
            'profit_pct': profit_pct,
            'bars': bars
        }



class SignalAnalysisDialog(QDialog):
    """Show backtest signal analysis"""
    
    def __init__(self, config: BotConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.worker = None
        
        self.setWindowTitle(f"Signal Analysis - {config.name}")
        self.setMinimumSize(1400, 900)  # Increased from 1200x800 for wider table
        
        # Check dependencies
        if not DEPENDENCIES_AVAILABLE:
            QMessageBox.critical(
                self,
                "Missing Dependencies",
                f"Required packages not installed:\n\n{IMPORT_ERROR}\n\n"
                f"Please install: pip install ccxt pandas numpy"
            )
            self.close()
            return
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Info section
        info_label = QLabel(
            "📊 <b>Signal Analysis (Backtest)</b><br>"
            "Analyze which trading signals would have been generated in a date range.<br>"
            "This uses the same strategy and TP/SL levels as the live bot.<br>"
            "<i>Multi-TP mode uses regime-based TP levels (TREND vs RANGE detection).</i>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Parameters section
        params_group = self.create_params_section()
        layout.addWidget(params_group)
        
        # Progress section
        self.progress_label = QLabel("Ready to analyze")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Summary section
        self.summary_group = self.create_summary_section()
        layout.addWidget(self.summary_group)
        
        # Results table
        results_group = self.create_results_section()
        layout.addWidget(results_group, 2)  # Increased stretch factor for more space
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("🔍 Analyze Signals")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #808080;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                min-height: 40px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #696969;
            }
        """)
        self.analyze_btn.clicked.connect(self.run_analysis)
        button_layout.addWidget(self.analyze_btn)
        
        export_btn = QPushButton("💾 Export CSV")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #808080;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                min-height: 28px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #696969;
            }
        """)
        export_btn.clicked.connect(self.export_csv)
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #808080;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                min-height: 28px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #696969;
            }
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
    def create_params_section(self):
        """Create parameters section"""
        group = QGroupBox("Analysis Parameters")
        layout = QVBoxLayout(group)
        
        # Row 1: Symbol
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Symbol:"))
        
        self.symbol_combo = QComboBox()
        # Determine symbol based on bot name and symbol
        bot_name_upper = self.config.name.upper()
        symbol_upper = self.config.symbol.upper() if self.config.symbol else ''
        
        is_btc = (
            'BTC' in bot_name_upper or 
            'BITCOIN' in bot_name_upper or
            'BTC' in symbol_upper
        )
        is_eth = (
            'ETH' in bot_name_upper or 
            'ETHEREUM' in bot_name_upper or
            'ETH' in symbol_upper
        )
        is_xauusd = (
            'XAUUSD' in bot_name_upper or
            'GOLD' in bot_name_upper or
            'XAU' in bot_name_upper or
            'XAUUSD' in symbol_upper or
            'XAU' in symbol_upper
        )
        
        if is_xauusd:
            self.symbol_combo.addItems(['XAUUSD'])
        elif is_btc and not is_eth:
            self.symbol_combo.addItems(['BTC/USDT'])
        elif is_eth and not is_btc:
            self.symbol_combo.addItems(['ETH/USDT'])
        else:
            # Default: add both
            self.symbol_combo.addItems(['BTC/USDT', 'ETH/USDT'])
        row1.addWidget(self.symbol_combo)
        
        row1.addWidget(QLabel("  Timeframe:"))
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'])
        self.timeframe_combo.setCurrentText('1h')  # Default to 1h
        row1.addWidget(self.timeframe_combo)
        
        row1.addWidget(QLabel("  Days:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 365)
        self.days_spin.setValue(7)
        self.days_spin.valueChanged.connect(self.on_days_changed)
        row1.addWidget(self.days_spin)
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # Row 2: Date range
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Or use date range:"))
        
        row2.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.start_date.dateChanged.connect(self.on_date_changed)
        row2.addWidget(self.start_date)
        
        row2.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self.on_date_changed)
        row2.addWidget(self.end_date)
        
        row2.addStretch()
        layout.addLayout(row2)
        
        # Row 3: Backtest Parameters (expandable)
        params_label = QLabel("<b>Backtest Parameters</b> (optional - override strategy defaults):")
        layout.addWidget(params_label)
        
        # TP/SL parameters
        row3 = QHBoxLayout()
        
        # TP Multiplier
        row3.addWidget(QLabel("TP Multiplier:"))
        self.tp_multiplier_spin = QSpinBox()
        self.tp_multiplier_spin.setRange(10, 500)
        self.tp_multiplier_spin.setValue(162)  # Default 1.618
        self.tp_multiplier_spin.setSuffix("% (x1.62)")
        self.tp_multiplier_spin.setToolTip("Take Profit as % of risk. 162% = 1.618 R:R, 262% = 2.618 R:R")
        row3.addWidget(self.tp_multiplier_spin)
        
        # SL Multiplier  
        row3.addWidget(QLabel("  SL Multiplier:"))
        self.sl_multiplier_spin = QSpinBox()
        self.sl_multiplier_spin.setRange(50, 200)
        self.sl_multiplier_spin.setValue(100)  # Default 100% = 1.0x
        self.sl_multiplier_spin.setSuffix("% (x1.0)")
        self.sl_multiplier_spin.setToolTip("Stop Loss multiplier. 100% = default, 150% = wider SL")
        row3.addWidget(self.sl_multiplier_spin)
        
        row3.addStretch()
        layout.addLayout(row3)
        
        # Trailing stop
        row4 = QHBoxLayout()
        
        self.use_trailing_check = QCheckBox("Use Trailing Stop")
        self.use_trailing_check.setChecked(False)
        self.use_trailing_check.stateChanged.connect(self.on_trailing_changed)
        row4.addWidget(self.use_trailing_check)
        
        row4.addWidget(QLabel("  Trailing %:"))
        self.trailing_pct_spin = QSpinBox()
        self.trailing_pct_spin.setRange(10, 100)
        self.trailing_pct_spin.setValue(50)  # Default 50% of profit
        self.trailing_pct_spin.setSuffix("% of profit")
        self.trailing_pct_spin.setEnabled(False)
        self.trailing_pct_spin.setToolTip("When profit reaches TP, trail stop at this % of profit")
        row4.addWidget(self.trailing_pct_spin)
        
        row4.addStretch()
        layout.addLayout(row4)
        
        # Multi-TP mode
        row5 = QHBoxLayout()
        
        self.use_multi_tp_check = QCheckBox("Use Multiple TP Levels (Live Bot Mode)")
        self.use_multi_tp_check.setChecked(False)
        self.use_multi_tp_check.setToolTip(
            "Enable regime-based TP levels matching live bot:\n\n"
            "Crypto (BTC/ETH):\n"
            "  TREND: TP1=1.5%, TP2=2.75%, TP3=4.5%\n"
            "  RANGE: TP1=1.0%, TP2=1.75%, TP3=2.5%\n\n"
            "XAUUSD (Gold):\n"
            "  TREND: TP1=30p, TP2=55p, TP3=90p\n"
            "  RANGE: TP1=20p, TP2=35p, TP3=50p\n\n"
            "Partial closes: TP1=50%, TP2=30%, TP3=20%\n"
            "SL moves to breakeven after TP1\n"
            "Market regime auto-detected (TREND/RANGE)"
        )
        row5.addWidget(self.use_multi_tp_check)
        
        row5.addStretch()
        layout.addLayout(row5)
        
        # Multi-TP customization section (collapsible)
        self.multi_tp_custom_group = QGroupBox("Custom TP Levels (Optional - Override Defaults)")
        self.multi_tp_custom_group.setCheckable(False)
        self.multi_tp_custom_group.setVisible(False)  # Hidden by default
        multi_tp_layout = QVBoxLayout(self.multi_tp_custom_group)
        
        # Connect checkbox to show/hide customization
        self.use_multi_tp_check.stateChanged.connect(self.on_multi_tp_changed)
        
        # TREND mode TP levels
        trend_row = QHBoxLayout()
        trend_row.addWidget(QLabel("<b>TREND Mode:</b>"))
        trend_row.addWidget(QLabel("TP1:"))
        self.trend_tp1_spin = QSpinBox()
        self.trend_tp1_spin.setRange(1, 1000)
        self.trend_tp1_spin.setValue(int(CRYPTO_TREND_TP['tp1'] * 100))  # Convert to basis points for crypto
        self.trend_tp1_spin.setSuffix(" (1.5% or 30p)")
        self.trend_tp1_spin.setToolTip("TP1 for TREND mode. For Crypto: 150 = 1.5%. For XAUUSD: 30 = 30 points")
        trend_row.addWidget(self.trend_tp1_spin)
        
        trend_row.addWidget(QLabel("  TP2:"))
        self.trend_tp2_spin = QSpinBox()
        self.trend_tp2_spin.setRange(1, 1000)
        self.trend_tp2_spin.setValue(int(CRYPTO_TREND_TP['tp2'] * 100))
        self.trend_tp2_spin.setSuffix(" (2.75% or 55p)")
        self.trend_tp2_spin.setToolTip("TP2 for TREND mode. For Crypto: 275 = 2.75%. For XAUUSD: 55 = 55 points")
        trend_row.addWidget(self.trend_tp2_spin)
        
        trend_row.addWidget(QLabel("  TP3:"))
        self.trend_tp3_spin = QSpinBox()
        self.trend_tp3_spin.setRange(1, 1000)
        self.trend_tp3_spin.setValue(int(CRYPTO_TREND_TP['tp3'] * 100))
        self.trend_tp3_spin.setSuffix(" (4.5% or 90p)")
        self.trend_tp3_spin.setToolTip("TP3 for TREND mode. For Crypto: 450 = 4.5%. For XAUUSD: 90 = 90 points")
        trend_row.addWidget(self.trend_tp3_spin)
        
        trend_row.addStretch()
        multi_tp_layout.addLayout(trend_row)
        
        # RANGE mode TP levels
        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("<b>RANGE Mode:</b>"))
        range_row.addWidget(QLabel("TP1:"))
        self.range_tp1_spin = QSpinBox()
        self.range_tp1_spin.setRange(1, 1000)
        self.range_tp1_spin.setValue(int(CRYPTO_RANGE_TP['tp1'] * 100))
        self.range_tp1_spin.setSuffix(" (1.0% or 20p)")
        self.range_tp1_spin.setToolTip("TP1 for RANGE mode. For Crypto: 100 = 1.0%. For XAUUSD: 20 = 20 points")
        range_row.addWidget(self.range_tp1_spin)
        
        range_row.addWidget(QLabel("  TP2:"))
        self.range_tp2_spin = QSpinBox()
        self.range_tp2_spin.setRange(1, 1000)
        self.range_tp2_spin.setValue(int(CRYPTO_RANGE_TP['tp2'] * 100))
        self.range_tp2_spin.setSuffix(" (1.75% or 35p)")
        self.range_tp2_spin.setToolTip("TP2 for RANGE mode. For Crypto: 175 = 1.75%. For XAUUSD: 35 = 35 points")
        range_row.addWidget(self.range_tp2_spin)
        
        range_row.addWidget(QLabel("  TP3:"))
        self.range_tp3_spin = QSpinBox()
        self.range_tp3_spin.setRange(1, 1000)
        self.range_tp3_spin.setValue(int(CRYPTO_RANGE_TP['tp3'] * 100))
        self.range_tp3_spin.setSuffix(" (2.5% or 50p)")
        self.range_tp3_spin.setToolTip("TP3 for RANGE mode. For Crypto: 250 = 2.5%. For XAUUSD: 50 = 50 points")
        range_row.addWidget(self.range_tp3_spin)
        
        range_row.addStretch()
        multi_tp_layout.addLayout(range_row)
        
        # Add spacing
        multi_tp_layout.addSpacing(10)
        
        # TREND mode SL levels
        trend_sl_row = QHBoxLayout()
        trend_sl_row.addWidget(QLabel("<b>TREND Mode SL:</b>"))
        self.trend_sl_spin = QSpinBox()
        self.trend_sl_spin.setRange(1, 500)
        self.trend_sl_spin.setValue(int(CRYPTO_TREND_SL * 100))  # Convert to basis points for crypto
        self.trend_sl_spin.setSuffix(" (0.8% or 16p)")
        self.trend_sl_spin.setToolTip("Stop Loss for TREND mode. For Crypto: 80 = 0.8%. For XAUUSD: 16 = 16 points")
        trend_sl_row.addWidget(self.trend_sl_spin)
        trend_sl_row.addStretch()
        multi_tp_layout.addLayout(trend_sl_row)
        
        # RANGE mode SL levels
        range_sl_row = QHBoxLayout()
        range_sl_row.addWidget(QLabel("<b>RANGE Mode SL:</b>"))
        self.range_sl_spin = QSpinBox()
        self.range_sl_spin.setRange(1, 500)
        self.range_sl_spin.setValue(int(CRYPTO_RANGE_SL * 100))  # Convert to basis points for crypto
        self.range_sl_spin.setSuffix(" (0.6% or 12p)")
        self.range_sl_spin.setToolTip("Stop Loss for RANGE mode. For Crypto: 60 = 0.6%. For XAUUSD: 12 = 12 points")
        range_sl_row.addWidget(self.range_sl_spin)
        range_sl_row.addStretch()
        multi_tp_layout.addLayout(range_sl_row)
        
        # Help text for TP/SL values
        help_label = QLabel(
            "<i><small>For Crypto (BTC/ETH): Values are in basis points (100 = 1.0%)<br>"
            "For XAUUSD (Gold): Values are in points directly</small></i>"
        )
        help_label.setStyleSheet("color: gray;")
        multi_tp_layout.addWidget(help_label)
        
        layout.addWidget(self.multi_tp_custom_group)
        
        # Note about default strategy
        note_label = QLabel(
            "<i>Single-TP mode: Use TP/SL multipliers above (Fibonacci-style)<br>"
            "Multi-TP mode: Uses live bot's regime-based TP levels (TREND/RANGE auto-detected)</i>"
        )
        note_label.setStyleSheet("color: gray;")
        layout.addWidget(note_label)
        
        return group
    
    def on_trailing_changed(self, state):
        """Enable/disable trailing percentage when checkbox changes"""
        self.trailing_pct_spin.setEnabled(state == 2)  # 2 = Qt.Checked
    
    def on_multi_tp_changed(self, state):
        """Show/hide custom TP levels section when Multi-TP checkbox changes"""
        self.multi_tp_custom_group.setVisible(state == 2)  # 2 = Qt.Checked
        
    def create_summary_section(self):
        """Create summary section - compact layout"""
        group = QGroupBox("Summary")
        layout = QVBoxLayout(group)
        
        # Use more compact spacing
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.summary_label = QLabel("Run analysis to see summary")
        self.summary_label.setWordWrap(True)
        # Set maximum height to prevent summary from taking too much space
        self.summary_label.setMaximumHeight(120)
        layout.addWidget(self.summary_label)
        
        return group
        
    def create_results_section(self):
        """Create results table section"""
        group = QGroupBox("Signals Found")
        layout = QVBoxLayout(group)
        
        # Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(10)
        self.results_table.setHorizontalHeaderLabels([
            'Date/Time', 'Type', 'Price', 'Stop Loss', 'Take Profit', 'Result', 'Profit %', 'Bars', 'Entry Reason', 'Regime'
        ])
        
        # Configure table
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.results_table)
        
        return group
        
    def on_days_changed(self, days):
        """When days spinbox changes, update date range"""
        # Update dates to reflect the days selection
        end = QDate.currentDate()
        start = end.addDays(-days)
        
        # Block signals to avoid recursion
        self.start_date.blockSignals(True)
        self.end_date.blockSignals(True)
        
        self.start_date.setDate(start)
        self.end_date.setDate(end)
        
        self.start_date.blockSignals(False)
        self.end_date.blockSignals(False)
        
    def on_date_changed(self):
        """When date range changes, update days spinbox"""
        start = self.start_date.date()
        end = self.end_date.date()
        days = start.daysTo(end)
        
        # Block signals to avoid recursion
        self.days_spin.blockSignals(True)
        self.days_spin.setValue(max(1, days))
        self.days_spin.blockSignals(False)
        
    def run_analysis(self):
        """Run signal analysis"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Analysis Running", "Analysis is already in progress")
            return
            
        # Get parameters
        symbol = self.symbol_combo.currentText()
        timeframe = self.timeframe_combo.currentText()
        days = self.days_spin.value()
        
        # Get date range
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        
        # Get backtest parameters
        tp_multiplier = self.tp_multiplier_spin.value()
        sl_multiplier = self.sl_multiplier_spin.value()
        use_trailing = self.use_trailing_check.isChecked()
        trailing_pct = self.trailing_pct_spin.value()
        use_multi_tp = self.use_multi_tp_check.isChecked()
        
        # Get custom TP levels if multi-TP is enabled
        custom_tp_levels = None
        if use_multi_tp:
            # Determine if crypto or XAUUSD
            is_xauusd = symbol.upper() in ['XAUUSD', 'XAU']
            
            # Get values from spin boxes
            trend_tp1 = self.trend_tp1_spin.value()
            trend_tp2 = self.trend_tp2_spin.value()
            trend_tp3 = self.trend_tp3_spin.value()
            range_tp1 = self.range_tp1_spin.value()
            range_tp2 = self.range_tp2_spin.value()
            range_tp3 = self.range_tp3_spin.value()
            
            # Convert values based on symbol type
            if is_xauusd:
                # For XAUUSD, values are already in points
                custom_tp_levels = {
                    'trend': {'tp1': trend_tp1, 'tp2': trend_tp2, 'tp3': trend_tp3},
                    'range': {'tp1': range_tp1, 'tp2': range_tp2, 'tp3': range_tp3}
                }
            else:
                # For crypto, convert from basis points to percentage
                custom_tp_levels = {
                    'trend': {'tp1': trend_tp1 / 100.0, 'tp2': trend_tp2 / 100.0, 'tp3': trend_tp3 / 100.0},
                    'range': {'tp1': range_tp1 / 100.0, 'tp2': range_tp2 / 100.0, 'tp3': range_tp3 / 100.0}
                }
        
        # Get custom SL levels if multi-TP is enabled
        custom_sl_levels = None
        if use_multi_tp:
            # Determine if crypto or XAUUSD
            is_xauusd = symbol.upper() in ['XAUUSD', 'XAU']
            
            # Get values from spin boxes
            trend_sl = self.trend_sl_spin.value()
            range_sl = self.range_sl_spin.value()
            
            # Convert values based on symbol type
            if is_xauusd:
                # For XAUUSD, values are already in points
                custom_sl_levels = {
                    'trend': trend_sl,
                    'range': range_sl
                }
            else:
                # For crypto, convert from basis points to percentage
                custom_sl_levels = {
                    'trend': trend_sl / 100.0,
                    'range': range_sl / 100.0
                }
        
        # Clear previous results
        self.results_table.setRowCount(0)
        self.summary_label.setText("Analyzing...")
        
        # Show progress
        self.progress_bar.show()
        self.progress_label.setText("Starting analysis...")
        self.analyze_btn.setEnabled(False)
        
        # Create and start worker (use MT5 worker for XAUUSD, Binance worker for others)
        is_xauusd = symbol.upper() in ['XAUUSD', 'XAU']
        
        if is_xauusd:
            # Use MT5 worker for XAUUSD
            self.worker = SignalAnalysisWorkerMT5(
                symbol, days, start, end,
                tp_multiplier, sl_multiplier, use_trailing, trailing_pct, timeframe, use_multi_tp,
                custom_tp_levels, custom_sl_levels
            )
        else:
            # Use Binance worker for BTC/ETH
            self.worker = SignalAnalysisWorker(
                symbol, days, start, end,
                tp_multiplier, sl_multiplier, use_trailing, trailing_pct, timeframe, use_multi_tp,
                custom_tp_levels, custom_sl_levels
            )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_analysis_complete)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()
        
    def on_progress(self, message):
        """Update progress"""
        self.progress_label.setText(message)
        
    def on_analysis_complete(self, signals_df):
        """Handle analysis completion"""
        self.progress_bar.hide()
        self.analyze_btn.setEnabled(True)
        
        if signals_df is None or len(signals_df) == 0:
            self.progress_label.setText("❌ No signals found in this period")
            self.summary_label.setText(
                "No trading signals were generated in the selected period.\n"
                "This could mean:\n"
                "  • Market was in consolidation (no clear patterns)\n"
                "  • Volatility was too low\n"
                "  • No breakouts or reversals detected"
            )
            return
            
        # Store results
        self.current_results = signals_df
        
        # Update summary
        total_signals = len(signals_df)
        buy_signals = len(signals_df[signals_df['signal'] == 1])
        sell_signals = len(signals_df[signals_df['signal'] == -1])
        
        # Calculate date range stats
        if total_signals > 0:
            first_signal = signals_df.index[0]
            last_signal = signals_df.index[-1]
            
            # Calculate win/loss statistics
            wins = len(signals_df[signals_df['outcome'].str.contains('Win', na=False)])
            losses = len(signals_df[signals_df['outcome'].str.contains('Loss', na=False)])
            other = total_signals - wins - losses
            win_rate = (wins / total_signals * 100) if total_signals > 0 else 0
            
            # Calculate average profit for wins and losses
            avg_win = signals_df[signals_df['outcome'].str.contains('Win', na=False)]['profit_pct'].mean()
            avg_loss = signals_df[signals_df['outcome'].str.contains('Loss', na=False)]['profit_pct'].mean()
            
            # Calculate P&L metrics
            total_profit_pct = signals_df['profit_pct'].sum()
            completed_trades = wins + losses
            avg_pnl = signals_df[signals_df['outcome'].str.contains('Win|Loss', na=False)]['profit_pct'].mean()
            
            # Calculate profit factor (gross profit / gross loss)
            gross_profit = signals_df[signals_df['profit_pct'] > 0]['profit_pct'].sum()
            gross_loss = abs(signals_df[signals_df['profit_pct'] < 0]['profit_pct'].sum())
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
            
            # Total P&L with color coding
            pnl_color = 'green' if total_profit_pct > 0 else 'red' if total_profit_pct < 0 else 'gray'
            
            # Compact summary - key metrics in horizontal layout
            summary_text = (
                f"<b>Signals:</b> {total_signals} (📈{buy_signals} / 📉{sell_signals})  |  "
                f"<b style='color: green;'>Wins:</b> {wins} ({win_rate:.1f}%)  |  "
                f"<b style='color: red;'>Losses:</b> {losses}  |  "
                f"<b>PF:</b> <span style='color: {'green' if profit_factor > 1 else 'red'};'>{profit_factor:.2f}</span>  |  "
                f"<b>Total P&L:</b> <span style='color: {pnl_color}; font-weight: bold;'>{total_profit_pct:+.2f}%</span><br>"
            )
            
            # Second line with additional metrics
            if wins > 0 or losses > 0:
                summary_text += f"<b>Avg:</b> "
                if wins > 0:
                    summary_text += f"<span style='color: green;'>Win +{avg_win:.2f}%</span>"
                if wins > 0 and losses > 0:
                    summary_text += " / "
                if losses > 0:
                    summary_text += f"<span style='color: red;'>Loss {avg_loss:.2f}%</span>"
                if completed_trades > 0:
                    summary_text += f"  |  <b>Exp:</b> {avg_pnl:+.2f}%"
                summary_text += "<br>"
            
            # Add multi-TP statistics if enabled (compact format)
            if 'tp_levels_hit' in signals_df.columns:
                # Calculate TP hit rates
                tp1_hit = len(signals_df[signals_df['tp_levels_hit'].str.contains('TP1', na=False)])
                tp2_hit = len(signals_df[signals_df['tp_levels_hit'].str.contains('TP2', na=False)])
                tp3_hit = len(signals_df[signals_df['tp_levels_hit'].str.contains('TP3', na=False)])
                
                tp1_rate = (tp1_hit / total_signals * 100) if total_signals > 0 else 0
                tp2_rate = (tp2_hit / total_signals * 100) if total_signals > 0 else 0
                tp3_rate = (tp3_hit / total_signals * 100) if total_signals > 0 else 0
                
                summary_text += (
                    f"<b>Multi-TP:</b> "
                    f"TP1 {tp1_rate:.0f}% | TP2 {tp2_rate:.0f}% | TP3 {tp3_rate:.0f}%"
                )
                
                # Calculate average TPs hit per trade (for completed trades)
                completed_signals = signals_df[signals_df['tp_levels_hit'] != 'None']
                if len(completed_signals) > 0:
                    total_tps = 0
                    for tp_str in completed_signals['tp_levels_hit']:
                        if pd.notna(tp_str):
                            total_tps += str(tp_str).count('TP')
                    avg_tps = total_tps / len(completed_signals)
                    summary_text += f" | <b>Avg:</b> {avg_tps:.2f} TPs"
                
                summary_text += "<br>"
            
            # Date range and status (compact, single line)
            summary_text += f"<small>{first_signal.strftime('%Y-%m-%d')} to {last_signal.strftime('%Y-%m-%d')}"
            
            # Check last 2 days - compact status
            two_days_ago = datetime.now() - timedelta(days=2)
            recent_signals = signals_df[signals_df.index >= two_days_ago]
            
            if len(recent_signals) > 0:
                summary_text += f" | ✅ Active ({len(recent_signals)} recent)"
            else:
                days_since = (datetime.now() - last_signal).days
                summary_text += f" | ⚠️ Last: {days_since}d ago"
            summary_text += "</small>"
        else:
            summary_text = "No signals found"
            
        self.summary_label.setText(summary_text)
        self.progress_label.setText(f"✅ Analysis complete - {total_signals} signals found")
        
        # Populate table
        self.populate_results_table(signals_df)
        
    def on_analysis_error(self, error_msg):
        """Handle analysis error"""
        self.progress_bar.hide()
        self.analyze_btn.setEnabled(True)
        self.progress_label.setText(f"❌ Error: {error_msg}")
        
        QMessageBox.critical(
            self,
            "Analysis Error",
            f"Failed to analyze signals:\n\n{error_msg}\n\n"
            f"Common issues:\n"
            f"• No internet connection\n"
            f"• Binance API rate limit\n"
            f"• Invalid date range"
        )
        
    def populate_results_table(self, signals_df):
        """Populate results table with signals"""
        # Check if multi-TP mode was used
        has_tp_levels = 'tp_levels_hit' in signals_df.columns
        
        # Update table columns dynamically
        if has_tp_levels:
            self.results_table.setColumnCount(11)
            self.results_table.setHorizontalHeaderLabels([
                'Date/Time', 'Type', 'Price', 'Stop Loss', 'Take Profit', 'Result', 'Profit %', 'TP Levels Hit', 'Bars', 'Entry Reason', 'Regime'
            ])
        else:
            self.results_table.setColumnCount(10)
            self.results_table.setHorizontalHeaderLabels([
                'Date/Time', 'Type', 'Price', 'Stop Loss', 'Take Profit', 'Result', 'Profit %', 'Bars', 'Entry Reason', 'Regime'
            ])
        
        # Configure table header
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.results_table.setRowCount(len(signals_df))
        
        for row_idx, (timestamp, row) in enumerate(signals_df.iterrows()):
            col_idx = 0
            
            # Date/Time
            date_item = QTableWidgetItem(timestamp.strftime('%Y-%m-%d %H:%M'))
            self.results_table.setItem(row_idx, col_idx, date_item)
            col_idx += 1
            
            # Type
            signal_type = "BUY 📈" if row['signal'] == 1 else "SELL 📉"
            type_item = QTableWidgetItem(signal_type)
            if row['signal'] == 1:
                type_item.setForeground(Qt.darkGreen)
            else:
                type_item.setForeground(Qt.darkRed)
            self.results_table.setItem(row_idx, col_idx, type_item)
            col_idx += 1
            
            # Price
            price_item = QTableWidgetItem(f"${row['close']:.2f}")
            self.results_table.setItem(row_idx, col_idx, price_item)
            col_idx += 1
            
            # Stop Loss
            sl_value = row.get('stop_loss', 0)
            if pd.isna(sl_value):
                sl_value = 0
            sl_item = QTableWidgetItem(f"${sl_value:.2f}" if sl_value else "N/A")
            self.results_table.setItem(row_idx, col_idx, sl_item)
            col_idx += 1
            
            # Take Profit
            tp_value = row.get('take_profit', 0)
            if pd.isna(tp_value):
                tp_value = 0
            tp_item = QTableWidgetItem(f"${tp_value:.2f}" if tp_value else "N/A")
            self.results_table.setItem(row_idx, col_idx, tp_item)
            col_idx += 1
            
            # Result (Win/Loss)
            outcome = row.get('outcome', 'Unknown')
            result_item = QTableWidgetItem(str(outcome))
            if 'Win' in str(outcome):
                result_item.setForeground(Qt.darkGreen)
            elif 'Loss' in str(outcome):
                result_item.setForeground(Qt.darkRed)
            self.results_table.setItem(row_idx, col_idx, result_item)
            col_idx += 1
            
            # Profit %
            profit_pct = row.get('profit_pct', 0)
            if pd.isna(profit_pct):
                profit_pct = 0
            profit_item = QTableWidgetItem(f"{profit_pct:+.2f}%" if profit_pct != 0 else "0.00%")
            if profit_pct > 0:
                profit_item.setForeground(Qt.darkGreen)
            elif profit_pct < 0:
                profit_item.setForeground(Qt.darkRed)
            self.results_table.setItem(row_idx, col_idx, profit_item)
            col_idx += 1
            
            # TP Levels Hit (only in multi-TP mode)
            if has_tp_levels:
                tp_levels = row.get('tp_levels_hit', 'None')
                if pd.isna(tp_levels) or not tp_levels:
                    tp_levels = 'None'
                tp_levels_item = QTableWidgetItem(str(tp_levels))
                # Color code based on TPs hit
                if tp_levels == 'TP1+TP2+TP3':
                    tp_levels_item.setForeground(Qt.darkGreen)
                elif 'TP' in str(tp_levels):
                    # Use blue for better contrast than yellow
                    tp_levels_item.setForeground(Qt.darkBlue)
                self.results_table.setItem(row_idx, col_idx, tp_levels_item)
                col_idx += 1
            
            # Bars Held
            bars = row.get('bars_held', 0)
            if pd.isna(bars):
                bars = 0
            bars_item = QTableWidgetItem(f"{int(bars)}" if bars > 0 else "-")
            self.results_table.setItem(row_idx, col_idx, bars_item)
            col_idx += 1
            
            # Entry Reason
            reason = row.get('signal_reason', 'N/A')
            if pd.isna(reason) or not reason:
                reason = 'N/A'
            reason_item = QTableWidgetItem(str(reason))
            self.results_table.setItem(row_idx, col_idx, reason_item)
            col_idx += 1
            
            # Regime
            regime = row.get('regime', 'N/A')
            if pd.isna(regime) or not regime:
                regime = 'N/A'
            regime_item = QTableWidgetItem(str(regime))
            self.results_table.setItem(row_idx, col_idx, regime_item)
            
    def export_csv(self):
        """Export results to CSV"""
        if not hasattr(self, 'current_results') or self.current_results is None:
            QMessageBox.warning(self, "No Data", "Run analysis first to generate data to export")
            return
            
        # Generate filename
        symbol = self.symbol_combo.currentText().replace('/', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"signal_analysis_{symbol}_{timestamp}.csv"
        
        try:
            # Export
            self.current_results.to_csv(filename)
            QMessageBox.information(
                self,
                "Export Successful",
                f"Results exported to:\n{filename}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export CSV:\n{str(e)}"
            )
