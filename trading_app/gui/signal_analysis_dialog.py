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
    QSpinBox, QProgressBar, QTextEdit, QMessageBox
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
    
    def __init__(self, symbol, days, start_date=None, end_date=None):
        super().__init__()
        self.symbol = symbol
        self.days = days
        self.start_date = start_date
        self.end_date = end_date
        
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
                candles = exchange.fetch_ohlcv(self.symbol, '1h', since=since, limit=1000)
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
            
            self.progress.emit(f"✅ Analysis complete! Found {len(signals_df)} signals")
            
            # Return results
            self.finished.emit(signals_df)
            
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")


class SignalAnalysisDialog(QDialog):
    """Show backtest signal analysis"""
    
    def __init__(self, config: BotConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.worker = None
        
        self.setWindowTitle(f"Signal Analysis - {config.name}")
        self.setMinimumSize(1200, 800)
        
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
        layout.addWidget(results_group, 1)
        
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
        # Determine symbol based on bot name
        if 'BTC' in self.config.name.upper():
            self.symbol_combo.addItems(['BTC/USDT'])
        elif 'ETH' in self.config.name.upper():
            self.symbol_combo.addItems(['ETH/USDT'])
        else:
            self.symbol_combo.addItems(['BTC/USDT', 'ETH/USDT'])
        row1.addWidget(self.symbol_combo)
        
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
        
        return group
        
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
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            'Date/Time', 'Type', 'Price', 'Stop Loss', 'Take Profit', 'Entry Reason', 'Regime'
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
        days = self.days_spin.value()
        
        # Get date range
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        
        # Clear previous results
        self.results_table.setRowCount(0)
        self.summary_label.setText("Analyzing...")
        
        # Show progress
        self.progress_bar.show()
        self.progress_label.setText("Starting analysis...")
        self.analyze_btn.setEnabled(False)
        
        # Create and start worker
        self.worker = SignalAnalysisWorker(symbol, days, start, end)
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
            
            summary_text = (
                f"<b>Total Signals:</b> {total_signals}<br>"
                f"<b>BUY Signals:</b> {buy_signals} 📈<br>"
                f"<b>SELL Signals:</b> {sell_signals} 📉<br><br>"
                f"<b>First Signal:</b> {first_signal.strftime('%Y-%m-%d %H:%M')}<br>"
                f"<b>Last Signal:</b> {last_signal.strftime('%Y-%m-%d %H:%M')}<br><br>"
            )
            
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
            sl_value = row.get('sl', 0)
            sl_item = QTableWidgetItem(f"${sl_value:.2f}" if sl_value else "N/A")
            self.results_table.setItem(row_idx, 3, sl_item)
            
            # Take Profit
            tp_value = row.get('tp', 0)
            tp_item = QTableWidgetItem(f"${tp_value:.2f}" if tp_value else "N/A")
            self.results_table.setItem(row_idx, 4, tp_item)
            
            # Entry Reason
            reason = row.get('entry_reason', 'N/A')
            reason_item = QTableWidgetItem(str(reason) if reason else "N/A")
            self.results_table.setItem(row_idx, 5, reason_item)
            
            # Regime
            regime = row.get('regime', 'N/A')
            regime_item = QTableWidgetItem(str(regime) if regime else "N/A")
            self.results_table.setItem(row_idx, 6, regime_item)
            
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
