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


class SignalAnalysisWorker(QThread):
    """Background worker for signal analysis"""
    
    progress = Signal(str)  # Progress message
    finished = Signal(object)  # DataFrame with results
    error = Signal(str)  # Error message
    
    def __init__(self, symbol, days, start_date=None, end_date=None, 
                 tp_multiplier=162, sl_multiplier=100, use_trailing=False, trailing_pct=50, timeframe='1h'):
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
    
    def _calculate_signal_outcomes(self, signals_df, full_df):
        """
        Calculate trade outcome for each signal
        Check if price hit TP or SL in the following candles
        Applies custom TP/SL multipliers and trailing stop if configured
        """
        # Add outcome columns
        signals_df['outcome'] = 'Unknown'
        signals_df['profit_pct'] = 0.0
        signals_df['bars_held'] = 0
        
        for idx, signal_row in signals_df.iterrows():
            signal_type = signal_row['signal']
            entry_price = signal_row['close']
            original_stop_loss = signal_row.get('stop_loss', 0)
            original_take_profit = signal_row.get('take_profit', 0)
            
            # Skip if SL or TP not set
            if pd.isna(original_stop_loss) or pd.isna(original_take_profit) or original_stop_loss == 0 or original_take_profit == 0:
                signals_df.loc[idx, 'outcome'] = 'No SL/TP'
                continue
            
            # Apply custom multipliers
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
            
            signals_df.loc[idx, 'outcome'] = outcome
            signals_df.loc[idx, 'profit_pct'] = profit_pct
            signals_df.loc[idx, 'bars_held'] = bars



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
            "This uses the same strategy as the live bot."
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
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.analyze_btn.setMinimumHeight(40)
        button_layout.addWidget(self.analyze_btn)
        
        export_btn = QPushButton("💾 Export CSV")
        export_btn.clicked.connect(self.export_csv)
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
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
        
        # Note about default strategy
        note_label = QLabel("<i>Leave at defaults to use bot's configured strategy settings</i>")
        note_label.setStyleSheet("color: gray;")
        layout.addWidget(note_label)
        
        return group
    
    def on_trailing_changed(self, state):
        """Enable/disable trailing percentage when checkbox changes"""
        self.trailing_pct_spin.setEnabled(state == 2)  # 2 = Qt.Checked
        
    def create_summary_section(self):
        """Create summary section"""
        group = QGroupBox("Summary")
        layout = QVBoxLayout(group)
        
        self.summary_label = QLabel("Run analysis to see summary")
        self.summary_label.setWordWrap(True)
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
        
        # Clear previous results
        self.results_table.setRowCount(0)
        self.summary_label.setText("Analyzing...")
        
        # Show progress
        self.progress_bar.show()
        self.progress_label.setText("Starting analysis...")
        self.analyze_btn.setEnabled(False)
        
        # Create and start worker
        self.worker = SignalAnalysisWorker(
            symbol, days, start, end,
            tp_multiplier, sl_multiplier, use_trailing, trailing_pct, timeframe
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
            
            summary_text = (
                f"<b>Total Signals:</b> {total_signals}<br>"
                f"<b>BUY Signals:</b> {buy_signals} 📈<br>"
                f"<b>SELL Signals:</b> {sell_signals} 📉<br><br>"
                f"<b>═══ P&L SUMMARY ═══</b><br>"
                f"<b style='color: green;'>Wins:</b> {wins} ({win_rate:.1f}%)<br>"
                f"<b style='color: red;'>Losses:</b> {losses}<br>"
                f"<b>Other (Open/Timeout):</b> {other}<br><br>"
            )
            
            if wins > 0:
                summary_text += f"<b>Avg Win:</b> <span style='color: green;'>+{avg_win:.2f}%</span><br>"
            if losses > 0:
                summary_text += f"<b>Avg Loss:</b> <span style='color: red;'>{avg_loss:.2f}%</span><br>"
            
            if completed_trades > 0:
                summary_text += f"<b>Expectancy:</b> {avg_pnl:+.2f}% per trade<br>"
                
            if profit_factor > 0:
                pf_color = 'green' if profit_factor > 1 else 'red'
                summary_text += f"<b>Profit Factor:</b> <span style='color: {pf_color};'>{profit_factor:.2f}</span><br>"
            
            # Total P&L with color coding
            pnl_color = 'green' if total_profit_pct > 0 else 'red' if total_profit_pct < 0 else 'gray'
            summary_text += f"<b>Total P&L:</b> <span style='color: {pnl_color}; font-size: 14pt;'>{total_profit_pct:+.2f}%</span><br><br>"
            
            summary_text += f"<b>First Signal:</b> {first_signal.strftime('%Y-%m-%d %H:%M')}<br>"
            summary_text += f"<b>Last Signal:</b> {last_signal.strftime('%Y-%m-%d %H:%M')}<br><br>"
            
            # Check last 2 days
            two_days_ago = datetime.now() - timedelta(days=2)
            recent_signals = signals_df[signals_df.index >= two_days_ago]
            
            if len(recent_signals) > 0:
                summary_text += f"<b>✅ Signals in last 2 days:</b> {len(recent_signals)}<br>"
                summary_text += "<span style='color: green;'>Bot is generating signals normally!</span>"
            else:
                days_since = (datetime.now() - last_signal).days
                summary_text += f"<b>⚠️ No signals in last 2 days</b><br>"
                summary_text += f"Last signal was {days_since} days ago<br>"
                summary_text += "<span style='color: orange;'>Market may be in consolidation</span>"
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
        self.results_table.setRowCount(len(signals_df))
        
        for row_idx, (timestamp, row) in enumerate(signals_df.iterrows()):
            # Date/Time
            date_item = QTableWidgetItem(timestamp.strftime('%Y-%m-%d %H:%M'))
            self.results_table.setItem(row_idx, 0, date_item)
            
            # Type
            signal_type = "BUY 📈" if row['signal'] == 1 else "SELL 📉"
            type_item = QTableWidgetItem(signal_type)
            if row['signal'] == 1:
                type_item.setForeground(Qt.darkGreen)
            else:
                type_item.setForeground(Qt.darkRed)
            self.results_table.setItem(row_idx, 1, type_item)
            
            # Price
            price_item = QTableWidgetItem(f"${row['close']:.2f}")
            self.results_table.setItem(row_idx, 2, price_item)
            
            # Stop Loss
            sl_value = row.get('stop_loss', 0)
            if pd.isna(sl_value):
                sl_value = 0
            sl_item = QTableWidgetItem(f"${sl_value:.2f}" if sl_value else "N/A")
            self.results_table.setItem(row_idx, 3, sl_item)
            
            # Take Profit
            tp_value = row.get('take_profit', 0)
            if pd.isna(tp_value):
                tp_value = 0
            tp_item = QTableWidgetItem(f"${tp_value:.2f}" if tp_value else "N/A")
            self.results_table.setItem(row_idx, 4, tp_item)
            
            # Result (Win/Loss)
            outcome = row.get('outcome', 'Unknown')
            result_item = QTableWidgetItem(str(outcome))
            if 'Win' in str(outcome):
                result_item.setForeground(Qt.darkGreen)
            elif 'Loss' in str(outcome):
                result_item.setForeground(Qt.darkRed)
            self.results_table.setItem(row_idx, 5, result_item)
            
            # Profit %
            profit_pct = row.get('profit_pct', 0)
            if pd.isna(profit_pct):
                profit_pct = 0
            profit_item = QTableWidgetItem(f"{profit_pct:+.2f}%" if profit_pct != 0 else "0.00%")
            if profit_pct > 0:
                profit_item.setForeground(Qt.darkGreen)
            elif profit_pct < 0:
                profit_item.setForeground(Qt.darkRed)
            self.results_table.setItem(row_idx, 6, profit_item)
            
            # Bars Held
            bars = row.get('bars_held', 0)
            if pd.isna(bars):
                bars = 0
            bars_item = QTableWidgetItem(f"{int(bars)}" if bars > 0 else "-")
            self.results_table.setItem(row_idx, 7, bars_item)
            
            # Entry Reason
            reason = row.get('signal_reason', 'N/A')
            if pd.isna(reason) or not reason:
                reason = 'N/A'
            reason_item = QTableWidgetItem(str(reason))
            self.results_table.setItem(row_idx, 8, reason_item)
            
            # Regime
            regime = row.get('regime', 'N/A')
            if pd.isna(regime) or not regime:
                regime = 'N/A'
            regime_item = QTableWidgetItem(str(regime))
            self.results_table.setItem(row_idx, 9, regime_item)
            
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
