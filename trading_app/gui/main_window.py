"""
Main Window - main GUI window for the trading app
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QPlainTextEdit, QListWidget, QListWidgetItem,
    QGroupBox, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from core import BotManager
from database import DatabaseManager
from models import BotConfig, BotStatus
from gui.settings_dialog import SettingsDialog
from gui.positions_monitor import PositionsMonitor
from gui.statistics_dialog import StatisticsDialog


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

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

        # Initialize UI
        self.init_ui()

        # Timer for status updates
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_display)
        self.status_timer.start(5000)  # Update every 5 seconds

        # Select first bot
        if self.bot_manager.get_all_bot_ids():
            self.select_bot(self.bot_manager.get_all_bot_ids()[0])

    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Trading Bot Manager")
        self.setGeometry(100, 100, 1400, 900)

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
        self.bot_list.currentItemChanged.connect(self.on_bot_selection_changed)

        # Add bots
        for bot_id in self.bot_manager.get_all_bot_ids():
            config = self.bot_manager.get_config(bot_id)
            item = QListWidgetItem(f"{self.get_bot_icon(bot_id)} {config.name}")
            item.setData(Qt.UserRole, bot_id)
            self.bot_list.addItem(item)

        layout.addWidget(self.bot_list)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_bot_list)
        layout.addWidget(refresh_btn)

        return panel

    def create_main_panel(self):
        """Create main content panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Bot info section
        self.info_group = self.create_info_section()
        layout.addWidget(self.info_group)

        # Status section
        self.status_group = self.create_status_section()
        layout.addWidget(self.status_group)

        # Controls section
        controls_group = self.create_controls_section()
        layout.addWidget(controls_group)

        # Logs section
        logs_group = self.create_logs_section()
        layout.addWidget(logs_group, 1)  # Give more space to logs

        return panel

    def create_info_section(self):
        """Create bot info section"""
        group = QGroupBox("Bot Information")
        layout = QVBoxLayout(group)

        self.info_label = QLabel("Select a bot from the list")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        return group

    def create_status_section(self):
        """Create status section"""
        group = QGroupBox("Status")
        layout = QVBoxLayout(group)

        self.status_label = QLabel("Status: Stopped")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        return group

    def create_controls_section(self):
        """Create controls section"""
        group = QGroupBox("Controls")
        layout = QHBoxLayout(group)

        # Start button
        self.start_btn = QPushButton("▶ Start Bot")
        self.start_btn.clicked.connect(self.start_bot)
        self.start_btn.setMinimumHeight(40)
        layout.addWidget(self.start_btn)

        # Stop button
        self.stop_btn = QPushButton("⏹ Stop Bot")
        self.stop_btn.clicked.connect(self.stop_bot)
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        # Settings button
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setMinimumHeight(40)
        layout.addWidget(settings_btn)

        # Positions button
        positions_btn = QPushButton("📊 Positions")
        positions_btn.clicked.connect(self.show_positions)
        positions_btn.setMinimumHeight(40)
        layout.addWidget(positions_btn)

        # Statistics button
        stats_btn = QPushButton("📈 Statistics")
        stats_btn.clicked.connect(self.show_statistics)
        stats_btn.setMinimumHeight(40)
        layout.addWidget(stats_btn)

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
        if not self.current_bot_id:
            return

        # Get status from cache or database
        status = self.status_cache.get(self.current_bot_id)
        if not status:
            status = self.bot_manager.get_status(self.current_bot_id)

        if not status:
            status = BotStatus(bot_id=self.current_bot_id, status='stopped')

        # Format status
        status_html = f"""
        <p><b>Status:</b> {'🟢 RUNNING' if status.status == 'running' else '⚫ STOPPED' if status.status == 'stopped' else '🔴 ERROR'}</p>
        """

        if status.status == 'running':
            status_html += f"""
            <p><b>Balance:</b> ${status.balance:,.2f}</p>
            <p><b>Equity:</b> ${status.equity:,.2f}</p>
            <p><b>P&L Today:</b> ${status.pnl_today:+,.2f} ({status.pnl_percent:+.2f}%)</p>
            <p><b>Open Positions:</b> {status.open_positions}/{status.max_positions}</p>
            """

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

    def update_controls(self):
        """Update control buttons based on bot state"""
        is_running = self.bot_manager.is_bot_running(self.current_bot_id)

        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)

    def start_bot(self):
        """Start current bot"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)

        # Confirm if not in dry run mode
        if not config.dry_run:
            reply = QMessageBox.question(
                self,
                'Confirm Start',
                f'Start {config.name} in LIVE TRADING mode?\n\nThis will trade with real money!',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

        success = self.bot_manager.start_bot(self.current_bot_id)

        if success:
            self.log(f"Starting {config.name}...")
        else:
            QMessageBox.warning(self, 'Error', 'Failed to start bot. Check logs for details.')

    def stop_bot(self):
        """Stop current bot"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)

        reply = QMessageBox.question(
            self,
            'Confirm Stop',
            f'Stop {config.name}?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

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

        dialog = PositionsMonitor(config, self)
        dialog.exec()

    def show_statistics(self):
        """Show statistics dialog"""
        if not self.current_bot_id:
            return

        config = self.bot_manager.get_config(self.current_bot_id)

        dialog = StatisticsDialog(config, self.db, self)
        dialog.exec()

    def refresh_bot_list(self):
        """Refresh bot list"""
        self.bot_list.clear()

        for bot_id in self.bot_manager.get_all_bot_ids():
            config = self.bot_manager.get_config(bot_id)
            item = QListWidgetItem(f"{self.get_bot_icon(bot_id)} {config.name}")
            item.setData(Qt.UserRole, bot_id)
            self.bot_list.addItem(item)

        self.log("Bot list refreshed")

    def clear_logs(self):
        """Clear log text"""
        self.log_text.clear()

    def log(self, message: str):
        """Add log message"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def on_bot_started(self, bot_id: str):
        """Handle bot started signal"""
        self.update_controls()
        self.log(f"Bot {bot_id} started")

    def on_bot_stopped(self, bot_id: str):
        """Handle bot stopped signal"""
        self.update_controls()
        self.update_status_display()
        self.log(f"Bot {bot_id} stopped")

    def on_bot_log(self, bot_id: str, message: str):
        """Handle bot log signal"""
        self.log(message)

    def on_bot_error(self, bot_id: str, error: str):
        """Handle bot error signal"""
        self.log(f"ERROR: {error}")
        QMessageBox.critical(self, 'Bot Error', f"Bot {bot_id} error:\n{error}")

    def on_status_updated(self, bot_id: str, status: BotStatus):
        """Handle status update signal"""
        # Cache status
        self.status_cache[bot_id] = status

        # Update display if this is current bot
        if bot_id == self.current_bot_id:
            self.update_status_display()

    def closeEvent(self, event):
        """Handle window close event"""
        # Check if any bots are running
        running_bots = [bid for bid in self.bot_manager.get_all_bot_ids()
                        if self.bot_manager.is_bot_running(bid)]

        if running_bots:
            reply = QMessageBox.question(
                self,
                'Confirm Exit',
                f'{len(running_bots)} bot(s) are still running.\n\nStop all bots and exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                event.ignore()
                return

            # Stop all bots
            self.bot_manager.stop_all_bots()

        # Close database
        self.db.close()

        event.accept()
