"""
Main Window - main GUI window for the trading app
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QPlainTextEdit, QListWidget, QListWidgetItem,
    QGroupBox, QMessageBox, QSplitter, QApplication, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QColor
from core import BotManager
from database import DatabaseManager
from models import BotConfig, BotStatus
from gui.settings_dialog import SettingsDialog
from gui.positions_monitor import PositionsMonitor
from gui.statistics_dialog import StatisticsDialog
from gui.signal_analysis_dialog import SignalAnalysisDialog


class PriceFetcherWorker(QThread):
    """Background worker for fetching current prices from exchange"""

    price_updated = Signal(str, float)  # Signal(bot_id, price)
    error = Signal(str)  # Error message

    def __init__(self, bot_id, config):
        super().__init__()
        self.bot_id = bot_id
        self.config = config
        self._is_running = True

    def run(self):
        """Fetch price in background"""
        if not self._is_running:
            return

        try:
            current_price = None

            if self.config.exchange == 'Binance':
                import ccxt
                # Use public data (no credentials needed for ticker)
                exchange = ccxt.binance({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'future'}
                })
                ticker = exchange.fetch_ticker(self.config.symbol)
                current_price = ticker.get('last')

            elif self.config.exchange == 'MT5':
                import MetaTrader5 as mt5
                if mt5.initialize():
                    try:
                        tick = mt5.symbol_info_tick(self.config.symbol)
                        if tick and tick.last > 0:
                            current_price = tick.last
                        elif tick:
                            # Try bid/ask if last is not available
                            current_price = (tick.bid + tick.ask) / 2 if tick.bid > 0 and tick.ask > 0 else None
                    finally:
                        mt5.shutdown()

            if current_price and self._is_running:
                self.price_updated.emit(self.bot_id, current_price)

        except Exception as e:
            if self._is_running:
                self.error.emit(f"Error fetching price: {e}")

    def stop(self):
        """Stop the worker"""
        self._is_running = False


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Closing flag to prevent operations during shutdown
        self.is_closing = False

        # Initialize database and bot manager
        self.db = DatabaseManager()
        self.bot_manager = BotManager(self.db)

        # Connect bot manager signals
        self.bot_manager.bot_started.connect(self.on_bot_started)
        self.bot_manager.bot_stopped.connect(self.on_bot_stopped)
        self.bot_manager.bot_log.connect(self.on_bot_log)
        self.bot_manager.bot_error.connect(self.on_bot_error)
        self.bot_manager.bot_status_updated.connect(self.on_status_updated)

        # Current bot
        self.current_bot_id = None

        # Status cache
        self.status_cache = {}

        # Price cache for live positions - prevents UI freezing
        self.current_prices = {}  # {bot_id: price}
        self.price_fetcher = None

        # Initialize UI
        self.init_ui()

        # Timer for status updates
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_display)
        self.status_timer.start(5000)  # Update every 5 seconds

        # Timer for background price fetching (less frequent to avoid API rate limits)
        self.price_timer = QTimer()
        self.price_timer.timeout.connect(self.start_price_fetching)
        self.price_timer.start(10000)  # Fetch price every 10 seconds

        # Select first bot
        if self.bot_manager.get_all_bot_ids():
            self.select_bot(self.bot_manager.get_all_bot_ids()[0])
    
    def get_modern_stylesheet(self):
        """Return modern stylesheet for the application"""
        return """
            QMainWindow {
                background-color: #F5F5F5;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 20px;
                padding-left: 10px;
                padding-right: 10px;
                padding-bottom: 15px;
                font-weight: bold;
                font-size: 13px;
                background-color: white;
                color: #333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: #2196F3;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                min-height: 45px;
                font-size: 13px;
                color: white;
            }
            QPushButton:hover {
                opacity: 0.9;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            }
            QPushButton:pressed {
                transform: translateY(1px);
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #999999;
            }
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background-color: white;
                padding: 5px;
            }
            QListWidget::item {
                border-radius: 4px;
                padding: 8px;
                margin: 2px;
            }
            QListWidget::item:hover {
                background-color: #E3F2FD;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QPlainTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background-color: #FAFAFA;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
            QLabel {
                color: #555;
            }
            QTableWidget {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background-color: white;
                gridline-color: #F0F0F0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #333;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 6px;
                background-color: white;
                min-height: 30px;
            }
            QComboBox:hover {
                border-color: #2196F3;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
        """

    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Trading Bot Manager")
        self.setGeometry(100, 100, 1400, 900)
        
        # Apply modern styling
        self.setStyleSheet(self.get_modern_stylesheet())

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - bot list
        left_panel = self.create_bot_list_panel()
        splitter.addWidget(left_panel)

        # Right panel - main content
        right_panel = self.create_main_panel()
        splitter.addWidget(right_panel)

        # Set splitter sizes (20% left, 80% right)
        splitter.setSizes([280, 1120])

        main_layout.addWidget(splitter)

    def create_bot_list_panel(self):
        """Create bot list panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Title
        title = QLabel("Trading Bots")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Bot list
        self.bot_list = QListWidget()
        self.bot_list.setStyleSheet("""
            QListWidget::item {
                font-size: 14px;
                font-weight: 600;
            }
        """)
        self.bot_list.currentItemChanged.connect(self.on_bot_selection_changed)

        # Add bots
        for bot_id in self.bot_manager.get_all_bot_ids():
            config = self.bot_manager.get_config(bot_id)

            # Check if bot is running
            is_running = self.bot_manager.is_bot_running(bot_id)
            status_indicator = "🟢" if is_running else "⚫"

            item = QListWidgetItem(f"{status_indicator} {self.get_bot_icon(bot_id)} {config.name}")
            item.setData(Qt.UserRole, bot_id)

            # Set background color based on status
            if is_running:
                from PySide6.QtGui import QColor
                item.setBackground(QColor(220, 255, 220))  # Light green

            self.bot_list.addItem(item)

        layout.addWidget(self.bot_list)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_bot_list)
        layout.addWidget(refresh_btn)

        return panel

    def create_main_panel(self):
        """Create main content panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Combined info and status section (horizontal)
        self.combined_info_status_group = self.create_combined_info_status_section()
        layout.addWidget(self.combined_info_status_group)

        # Live open positions section
        self.live_positions_group = self.create_live_positions_section()
        layout.addWidget(self.live_positions_group)

        # Controls section
        controls_group = self.create_controls_section()
        layout.addWidget(controls_group)

        # Active bots section
        self.active_bots_group = self.create_active_bots_section()
        layout.addWidget(self.active_bots_group)

        # Logs section
        logs_group = self.create_logs_section()
        layout.addWidget(logs_group, 1)  # Give more space to logs

        return panel

    def create_combined_info_status_section(self):
        """Create combined bot info and status section (horizontal layout)"""
        group = QGroupBox("Bot Information & Status")
        main_layout = QHBoxLayout(group)
        
        # Left side: Bot Information
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(5, 5, 5, 5)
        
        info_title = QLabel("📋 Bot Configuration")
        info_title_font = QFont()
        info_title_font.setPointSize(11)
        info_title_font.setBold(True)
        info_title.setFont(info_title_font)
        info_layout.addWidget(info_title)
        
        self.info_label = QLabel("Select a bot from the list")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label, 1)
        
        main_layout.addWidget(info_widget, 1)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #E0E0E0;")
        main_layout.addWidget(separator)
        
        # Right side: Status
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(5, 5, 5, 5)
        
        status_title = QLabel("📊 Live Status")
        status_title_font = QFont()
        status_title_font.setPointSize(11)
        status_title_font.setBold(True)
        status_title.setFont(status_title_font)
        status_layout.addWidget(status_title)
        
        self.status_label = QLabel("Status: Stopped")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label, 1)
        
        main_layout.addWidget(status_widget, 1)
        
        return group
    
    def create_live_positions_section(self):
        """Create live open positions section"""
        group = QGroupBox("📊 Live Open Positions")
        layout = QVBoxLayout(group)
        
        self.live_positions_label = QLabel("No open positions")
        self.live_positions_label.setWordWrap(True)
        self.live_positions_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #F9F9F9;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.live_positions_label)
        
        return group

    def create_controls_section(self):
        """Create controls section"""
        group = QGroupBox("Controls")
        layout = QHBoxLayout(group)

        # Start button
        self.start_btn = QPushButton("▶ Start Bot")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.start_btn.clicked.connect(self.start_bot)
        self.start_btn.setMinimumHeight(50)
        layout.addWidget(self.start_btn)

        # Stop button
        self.stop_btn = QPushButton("⏹ Stop Bot")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_bot)
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        # Settings button
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setMinimumHeight(50)
        layout.addWidget(settings_btn)

        # Positions button
        positions_btn = QPushButton("📊 Positions")
        positions_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        positions_btn.clicked.connect(self.show_positions)
        positions_btn.setMinimumHeight(50)
        layout.addWidget(positions_btn)

        # Statistics button
        stats_btn = QPushButton("📈 Statistics")
        stats_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        stats_btn.clicked.connect(self.show_statistics)
        stats_btn.setMinimumHeight(50)
        layout.addWidget(stats_btn)

        # TP Hits button
        tp_hits_btn = QPushButton("🎯 TP Hits")
        tp_hits_btn.setStyleSheet("""
            QPushButton {
                background-color: #00BCD4;
                color: white;
            }
            QPushButton:hover {
                background-color: #0097A7;
            }
        """)
        tp_hits_btn.clicked.connect(self.show_tp_hits)
        tp_hits_btn.setMinimumHeight(50)
        layout.addWidget(tp_hits_btn)

        # Signal Analysis button (Backtest)
        signal_analysis_btn = QPushButton("🔍 Signal Analysis")
        signal_analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        signal_analysis_btn.clicked.connect(self.show_signal_analysis)
        signal_analysis_btn.setMinimumHeight(50)
        layout.addWidget(signal_analysis_btn)

        return group

    def create_active_bots_section(self):
        """Create active bots section"""
        group = QGroupBox("Active Bots")
        layout = QHBoxLayout(group)

        # Active bots label
        self.active_bots_label = QLabel("No bots running")
        self.active_bots_label.setStyleSheet("font-weight: bold; color: #555;")
        layout.addWidget(self.active_bots_label)

        layout.addStretch()

        return group

    def create_logs_section(self):
        """Create logs section"""
        group = QGroupBox("Live Logs")
        layout = QVBoxLayout(group)

        # Log text area
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)  # Limit to 1000 lines
        layout.addWidget(self.log_text)

        # Clear button
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.clear_logs)
        layout.addWidget(clear_btn)

        return group

    def get_bot_icon(self, bot_id: str) -> str:
        """Get icon for bot"""
        icons = {
            'xauusd': '🥇',
            'btc': '₿',
            'eth': '⟠'
        }
        return icons.get(bot_id, '🤖')

    def select_bot(self, bot_id: str):
        """Select a bot"""
        self.current_bot_id = bot_id
        self.update_info_display()
        self.update_status_display()
        self.update_controls()
        # Trigger immediate price fetch for the newly selected bot if it has positions
        self.start_price_fetching()

    def on_bot_selection_changed(self, current, previous):
        """Handle bot selection change"""
        if current:
            bot_id = current.data(Qt.UserRole)
            self.select_bot(bot_id)

    def update_info_display(self):
        """Update bot info display"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)
        if not config:
            return

        info_html = f"""
        <h3>{self.get_bot_icon(self.current_bot_id)} {config.name}</h3>
        <p><b>Symbol:</b> {config.symbol}</p>
        <p><b>Exchange:</b> {config.exchange}</p>
        <p><b>Strategy:</b> {config.strategy.upper()}</p>
        <p><b>Risk per trade:</b> {config.risk_percent}%</p>
        <p><b>Max positions:</b> {config.max_positions}</p>
        <p><b>Timeframe:</b> {config.timeframe}</p>
        <p><b>Mode:</b> {'🧪 DRY RUN' if config.dry_run else '🚀 LIVE TRADING'}</p>
        """

        self.info_label.setText(info_html)

    def update_status_display(self):
        """Update status display"""
        # Skip if closing or no current bot
        if self.is_closing or not self.current_bot_id:
            return

        # Check if widgets still exist
        if not hasattr(self, 'status_label') or self.status_label is None:
            return

        try:
            # Get status from cache or database
            status = self.status_cache.get(self.current_bot_id)
            if not status:
                status = self.bot_manager.get_status(self.current_bot_id)
        except Exception as e:
            print(f"⚠️  Error getting status: {e}")
            return

        if not status:
            status = BotStatus(bot_id=self.current_bot_id, status='stopped')

        # Format status
        status_html = f"""
        <p><b>Status:</b> {'🟢 RUNNING' if status.status == 'running' else '⚫ STOPPED' if status.status == 'stopped' else '🔴 ERROR'}</p>
        """

        # Get actual open positions count from database (more reliable than status object)
        try:
            open_trades = self.db.get_open_trades(self.current_bot_id)
            actual_open_positions = len(open_trades) if open_trades else 0
        except Exception as e:
            # Fallback to status if DB read fails, log the error for debugging
            print(f"⚠️  Failed to get open positions from DB: {e}")
            actual_open_positions = status.open_positions
        
        # Always show balance/equity info (not dependent on running status)
        # This ensures balance is visible even when bot status temporarily changes
        status_html += f"""
        <p><b>Balance:</b> ${status.balance:,.2f}</p>
        <p><b>Equity:</b> ${status.equity:,.2f}</p>
        <p><b>P&L Today:</b> ${status.pnl_today:+,.2f} ({status.pnl_percent:+.2f}%)</p>
        <p><b>Open Positions:</b> {actual_open_positions}/{status.max_positions}</p>
        """

        if status.status == 'running':
            if status.current_regime:
                status_html += f"<p><b>Market Regime:</b> {status.current_regime}</p>"

            if status.total_trades > 0:
                status_html += f"""
                <p><b>Total Trades:</b> {status.total_trades}</p>
                <p><b>Win Rate:</b> {status.win_rate:.1f}%</p>
                """

        if status.error_message:
            status_html += f"<p style='color: red;'><b>Error:</b> {status.error_message}</p>"

        self.status_label.setText(status_html)
        
        # Update live positions
        self.update_live_positions_display()

    def start_price_fetching(self):
        """Start background price fetching for current bot"""
        if self.is_closing or not self.current_bot_id:
            return

        # Don't start new fetcher if one is already running
        if self.price_fetcher and self.price_fetcher.isRunning():
            return

        # Get open trades to see if we need to fetch price
        try:
            open_trades = self.db.get_open_trades(self.current_bot_id)
            if not open_trades or len(open_trades) == 0:
                return  # No positions, no need to fetch price
        except:
            return

        # Get bot config
        config = self.db.load_config(self.current_bot_id)
        if not config:
            return

        # Start background fetcher
        self.price_fetcher = PriceFetcherWorker(self.current_bot_id, config)
        self.price_fetcher.price_updated.connect(self.on_price_updated)
        self.price_fetcher.error.connect(self.on_price_error)
        self.price_fetcher.finished.connect(self.on_price_fetch_finished)
        self.price_fetcher.start()

    def on_price_updated(self, bot_id, price):
        """Handle price update from background fetcher"""
        if not self.is_closing:
            self.current_prices[bot_id] = price
            # Update display if this is the current bot
            if bot_id == self.current_bot_id:
                self.update_live_positions_display()

    def on_price_error(self, error):
        """Handle price fetch error"""
        # Silently fail - price will be fetched next time
        pass

    def on_price_fetch_finished(self):
        """Clean up when fetcher finishes"""
        if self.price_fetcher:
            self.price_fetcher.deleteLater()
            self.price_fetcher = None

    def update_live_positions_display(self):
        """Update live open positions display - simplified to show only count and P&L%"""
        if not hasattr(self, 'live_positions_label') or self.live_positions_label is None:
            return

        if not self.current_bot_id:
            self.live_positions_label.setText("No bot selected")
            return

        try:
            # Get open positions from database
            open_trades = self.db.get_open_trades(self.current_bot_id)

            if not open_trades or len(open_trades) == 0:
                self.live_positions_label.setText("<p style='color: #666; font-size: 13px;'>No open positions</p>")
                return

            # Get bot config
            config = self.db.load_config(self.current_bot_id)
            if not config:
                self.live_positions_label.setText("<p style='color: #F44336;'>Bot config not found</p>")
                return

            # Use cached price from background fetcher (non-blocking)
            current_price = self.current_prices.get(self.current_bot_id)

            # Build display with position count (always show this)
            positions_html = f"""
            <div style='font-size: 14px; padding: 8px;'>
                <p style='margin: 4px 0;'>
                    <b>Open Positions:</b> <span style='font-size: 16px; color: #2196F3; font-weight: bold;'>{len(open_trades)}</span>
                </p>
            """

            # Calculate and show P&L only if price is available
            if current_price and current_price > 0:
                # Calculate total P&L and total entry value for percentage
                total_pnl = 0.0
                total_entry_value = 0.0
                
                for trade in open_trades:
                    if trade.entry_price and trade.entry_price > 0 and trade.amount:
                        if trade.trade_type.upper() == 'BUY':
                            trade.profit = (current_price - trade.entry_price) * trade.amount
                        elif trade.trade_type.upper() == 'SELL':
                            trade.profit = (trade.entry_price - current_price) * trade.amount
                    total_pnl += (trade.profit or 0.0)
                    # Add to entry value only if both values are valid
                    if trade.entry_price and trade.amount:
                        total_entry_value += trade.entry_price * trade.amount

                # Calculate total P&L percentage with proper validation
                if total_entry_value > 0:
                    total_pnl_pct = (total_pnl / total_entry_value * 100)
                    pnl_color = '#4CAF50' if total_pnl >= 0 else '#F44336'
                    positions_html += f"""
                <p style='margin: 4px 0;'>
                    <b>Total P&L:</b> <span style='color: {pnl_color}; font-weight: bold; font-size: 16px;'>
                    {total_pnl_pct:+.2f}%</span>
                </p>
                """
                else:
                    # Show calculating if we have price but can't calculate
                    positions_html += "<p style='margin: 4px 0; color: #FF9800;'><b>Total P&L:</b> Calculating...</p>"
            else:
                # Price not available yet - trigger immediate fetch
                if not self.price_fetcher or not self.price_fetcher.isRunning():
                    self.start_price_fetching()
                positions_html += "<p style='margin: 4px 0; color: #FF9800;'><b>Total P&L:</b> Fetching price...</p>"

            positions_html += "</div>"
            
            self.live_positions_label.setText(positions_html)
            
        except Exception as e:
            print(f"Error updating live positions: {e}")
            self.live_positions_label.setText(f"<p style='color: #F44336;'>Error loading positions</p>")

    def update_controls(self):
        """Update control buttons based on bot state"""
        is_running = self.bot_manager.is_bot_running(self.current_bot_id)

        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)

    def update_active_bots_display(self):
        """Update active bots display"""
        running_bots = []

        for bot_id in self.bot_manager.get_all_bot_ids():
            if self.bot_manager.is_bot_running(bot_id):
                config = self.bot_manager.get_config(bot_id)
                icon = self.get_bot_icon(bot_id)
                running_bots.append(f"{icon} {config.name}")

        if running_bots:
            bots_text = ", ".join(running_bots)
            self.active_bots_label.setText(f"🟢 Running: {bots_text}")
            self.active_bots_label.setStyleSheet("font-weight: bold; color: green;")
        else:
            self.active_bots_label.setText("⚫ No bots running")
            self.active_bots_label.setStyleSheet("font-weight: bold; color: #555;")

    def start_bot(self):
        """Start current bot"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)

        # Confirm if not in dry run mode
        if not config.dry_run:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle('Confirm Start')
            msg.setText(f'⚠️  Start {config.name} in LIVE TRADING mode?\n\nThis will trade with real money!')
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #333;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #696969;
                }
            """)
            reply = msg.exec()

            if reply != QMessageBox.Yes:
                return

        success = self.bot_manager.start_bot(self.current_bot_id)

        if success:
            self.log(f"Starting {config.name}...")
        else:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Error')
            msg.setText('❌ Failed to start bot. Check logs for details.')
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #333;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #696969;
                }
            """)
            msg.exec()

    def stop_bot(self):
        """Stop current bot"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle('Confirm Stop')
        msg.setText(f'⏹️  Stop {config.name}?')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #333;
                font-size: 13px;
            }
            QPushButton {
                background-color: #808080;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #696969;
            }
        """)
        reply = msg.exec()

        if reply != QMessageBox.Yes:
            return

        success = self.bot_manager.stop_bot(self.current_bot_id)

        if success:
            self.log(f"Stopping {config.name}...")

    def show_settings(self):
        """Show settings dialog"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)

        dialog = SettingsDialog(config, self)
        if dialog.exec():
            # Save updated config
            updated_config = dialog.get_config()
            self.bot_manager.update_config(updated_config)
            self.update_info_display()
            self.log(f"Settings updated for {config.name}")

    def show_positions(self):
        """Show positions monitor"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)
        
        if not config:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Error')
            msg.setText('❌ Bot configuration not found.')
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #333;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #696969;
                }
            """)
            msg.exec()
            return

        try:
            dialog = PositionsMonitor(config, self.db, self)
            dialog.exec()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle('Error')
            msg.setText(f'❌ Failed to open positions monitor:\n{str(e)}')
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #333;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #696969;
                }
            """)
            msg.exec()

    def show_statistics(self):
        """Show statistics dialog"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)

        dialog = StatisticsDialog(config, self.db, self)
        dialog.exec()

    def show_tp_hits(self):
        """Show TP hits history"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)

        from gui.tp_hits_viewer import TPHitsViewer
        dialog = TPHitsViewer(config, self)
        dialog.exec()

    def show_signal_analysis(self):
        """Show signal analysis dialog"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)
        
        # Check for supported bots: BTC/ETH (Binance) and XAUUSD/Gold (MT5)
        bot_name_upper = config.name.upper()
        symbol_upper = config.symbol.upper() if config.symbol else ''
        
        is_supported = (
            'BTC' in bot_name_upper or 
            'ETH' in bot_name_upper or
            'BITCOIN' in bot_name_upper or 
            'ETHEREUM' in bot_name_upper or
            'XAUUSD' in bot_name_upper or
            'GOLD' in bot_name_upper or
            'XAU' in bot_name_upper or
            'BTC' in symbol_upper or 
            'ETH' in symbol_upper or
            'XAUUSD' in symbol_upper or
            'XAU' in symbol_upper
        )
        
        if not is_supported:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Not Available")
            msg.setText("ℹ️  Signal Analysis is currently available for BTC, ETH, and XAUUSD bots only.")
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #333;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #696969;
                }
            """)
            msg.exec()
            return

        dialog = SignalAnalysisDialog(config, self)
        dialog.exec()

    def refresh_bot_list(self):
        """Refresh bot list"""
        self.bot_list.clear()

        for bot_id in self.bot_manager.get_all_bot_ids():
            config = self.bot_manager.get_config(bot_id)

            # Check if bot is running
            is_running = self.bot_manager.is_bot_running(bot_id)
            status_indicator = "🟢" if is_running else "⚫"

            item = QListWidgetItem(f"{status_indicator} {self.get_bot_icon(bot_id)} {config.name}")
            item.setData(Qt.UserRole, bot_id)

            # Set background color based on status
            if is_running:
                from PySide6.QtGui import QColor
                item.setBackground(QColor(220, 255, 220))  # Light green

            self.bot_list.addItem(item)

        self.log("Bot list refreshed")

    def clear_logs(self):
        """Clear log text"""
        self.log_text.clear()

    def log(self, message: str):
        """Add log message"""
        if self.is_closing:
            return
        try:
            if hasattr(self, 'log_text') and self.log_text is not None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_text.appendPlainText(f"[{timestamp}] {message}")
        except:
            pass  # Ignore errors during logging

    def on_bot_started(self, bot_id: str):
        """Handle bot started signal"""
        self.update_controls()
        self.update_active_bots_display()
        self.refresh_bot_list()  # Refresh to show green indicator
        self.log(f"Bot {bot_id} started")

    def on_bot_stopped(self, bot_id: str):
        """Handle bot stopped signal"""
        self.update_controls()
        self.update_status_display()
        self.update_active_bots_display()
        self.refresh_bot_list()  # Refresh to remove green indicator
        self.log(f"Bot {bot_id} stopped")

    def on_bot_log(self, bot_id: str, message: str):
        """Handle bot log signal"""
        if self.is_closing:
            return
        try:
            self.log(message)
        except:
            pass

    def on_bot_error(self, bot_id: str, error: str):
        """Handle bot error signal"""
        if self.is_closing:
            return
        try:
            self.log(f"ERROR: {error}")
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle('Bot Error')
            msg.setText(f'❌ Bot {bot_id} error:\n{error}')
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #333;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #696969;
                }
            """)
            msg.exec()
        except:
            pass

    def on_status_updated(self, bot_id: str, status: BotStatus):
        """Handle status update signal"""
        if self.is_closing:
            return
        try:
            # Cache status
            self.status_cache[bot_id] = status

            # Update display if this is current bot
            if bot_id == self.current_bot_id:
                self.update_status_display()
        except:
            pass

    def closeEvent(self, event):
        """Handle window close event"""
        # Set closing flag to prevent further operations
        self.is_closing = True

        # Stop all timers
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        if hasattr(self, 'price_timer'):
            self.price_timer.stop()

        # Stop price fetcher thread if running
        if hasattr(self, 'price_fetcher') and self.price_fetcher:
            if self.price_fetcher.isRunning():
                self.price_fetcher.stop()
                self.price_fetcher.wait(2000)  # Wait max 2 seconds

        # Check if any bots are running
        running_bots = [bid for bid in self.bot_manager.get_all_bot_ids()
                        if self.bot_manager.is_bot_running(bid)]

        if running_bots:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle('Confirm Exit')
            msg.setText(f'⚠️  {len(running_bots)} bot(s) are still running.\n\nStop all bots and exit?')
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #333;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #696969;
                }
            """)
            reply = msg.exec()

            if reply != QMessageBox.Yes:
                event.ignore()
                # Reset closing flag and restart timers if user cancels
                self.is_closing = False
                if hasattr(self, 'status_timer'):
                    self.status_timer.start(5000)
                if hasattr(self, 'price_timer'):
                    self.price_timer.start(10000)
                return

            # Stop all bots
            print("🛑 Stopping all bots...")
            self.bot_manager.stop_all_bots()

            # Process any pending events from stopped threads
            print("⏳ Waiting for threads to finish...")
            QApplication.processEvents()

            # Give threads time to finish cleanup
            import time
            time.sleep(0.5)

            # Process remaining signals
            QApplication.processEvents()

        # Disconnect all signals to prevent callbacks after close
        try:
            self.bot_manager.bot_started.disconnect()
            self.bot_manager.bot_stopped.disconnect()
            self.bot_manager.bot_log.disconnect()
            self.bot_manager.bot_error.disconnect()
            self.bot_manager.bot_status_updated.disconnect()
        except:
            pass  # Ignore if already disconnected

        # Close database
        print("🗄️  Closing database...")
        self.db.close()

        print("✅ Application closed cleanly")
        event.accept()
