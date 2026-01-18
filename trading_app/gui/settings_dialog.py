"""
Settings Dialog - configure bot settings
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLineEdit, QDoubleSpinBox, QSpinBox,
    QCheckBox, QComboBox, QGroupBox, QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from models import BotConfig


class SettingsDialog(QDialog):
    """Bot settings dialog"""

    def __init__(self, config: BotConfig, parent=None):
        super().__init__(parent)
        self.config = config.to_dict()  # Work with copy
        self.original_config = config

        self.setWindowTitle(f"Settings - {config.name}")
        self.setModal(True)
        self.setMinimumWidth(600)

        self.init_ui()
        self.load_config()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Exchange settings
        if self.original_config.exchange == 'Binance':
            exchange_group = self.create_binance_group()
            layout.addWidget(exchange_group)

        # Trading parameters
        trading_group = self.create_trading_group()
        layout.addWidget(trading_group)

        # Strategy settings
        strategy_group = self.create_strategy_group()
        layout.addWidget(strategy_group)

        # Telegram settings
        telegram_group = self.create_telegram_group()
        layout.addWidget(telegram_group)

        # Buttons
        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
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
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
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
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        test_btn = QPushButton("Test Connection")
        test_btn.setStyleSheet("""
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
        test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(test_btn)

        layout.addLayout(button_layout)

    def create_binance_group(self):
        """Create Binance settings group"""
        group = QGroupBox("Binance API")
        layout = QFormLayout(group)

        # API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        layout.addRow("API Key:", self.api_key_input)

        # API Secret
        self.api_secret_input = QLineEdit()
        self.api_secret_input.setEchoMode(QLineEdit.Password)
        layout.addRow("API Secret:", self.api_secret_input)

        # Testnet
        self.testnet_check = QCheckBox("Use Testnet")
        layout.addRow("", self.testnet_check)

        return group

    def create_trading_group(self):
        """Create trading parameters group"""
        group = QGroupBox("Trading Parameters")
        layout = QFormLayout(group)

        # Symbol (read-only for now)
        self.symbol_label = QLabel()
        layout.addRow("Symbol:", self.symbol_label)

        # Timeframe
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(['1m', '5m', '15m', '30m', '1h', '4h', '1d'])
        layout.addRow("Timeframe:", self.timeframe_combo)

        # Risk percent
        self.risk_spin = QDoubleSpinBox()
        self.risk_spin.setRange(0.1, 10.0)
        self.risk_spin.setSingleStep(0.1)
        self.risk_spin.setDecimals(1)
        self.risk_spin.setSuffix("%")
        layout.addRow("Risk per trade:", self.risk_spin)

        # Max positions
        self.max_pos_spin = QSpinBox()
        self.max_pos_spin.setRange(1, 20)
        layout.addRow("Max positions:", self.max_pos_spin)

        # DRY RUN mode
        self.dry_run_check = QCheckBox("DRY RUN mode (no real trades)")
        layout.addRow("", self.dry_run_check)

        # Phase 2: 3-Position Mode
        layout.addRow(QLabel("<b>3-Position Mode:</b>"))

        self.use_3pos_check = QCheckBox("Enable 3-position mode")
        layout.addRow("", self.use_3pos_check)

        self.total_pos_size_spin = QDoubleSpinBox()
        self.total_pos_size_spin.setRange(0.01, 100000.0)
        self.total_pos_size_spin.setSingleStep(10.0)
        self.total_pos_size_spin.setDecimals(2)
        unit = "USD" if self.original_config.exchange == 'Binance' else "lots"
        self.total_pos_size_spin.setSuffix(f" {unit}")
        layout.addRow("Total position size:", self.total_pos_size_spin)

        self.min_order_size_spin = QDoubleSpinBox()
        self.min_order_size_spin.setRange(0.001, 1000.0)
        self.min_order_size_spin.setSingleStep(0.01)
        self.min_order_size_spin.setDecimals(3)
        self.min_order_size_spin.setSuffix(f" {unit}")
        layout.addRow("Min order size:", self.min_order_size_spin)

        self.use_trailing_check = QCheckBox("Enable trailing stops (Pos 2 & 3)")
        self.use_trailing_check.setToolTip("Enable trailing stops for positions 2 and 3 after TP1 is hit")
        layout.addRow("", self.use_trailing_check)

        self.trailing_stop_pct_spin = QSpinBox()
        self.trailing_stop_pct_spin.setRange(10, 90)
        self.trailing_stop_pct_spin.setValue(50)
        self.trailing_stop_pct_spin.setSuffix("%")
        self.trailing_stop_pct_spin.setToolTip("Trailing stop percentage (50% = price can retrace 50% from max profit)")
        layout.addRow("Trailing stop %:", self.trailing_stop_pct_spin)

        return group

    def create_strategy_group(self):
        """Create strategy settings group"""
        group = QGroupBox("Strategy - V3 Adaptive")
        layout = QVBoxLayout(group)

        # TREND mode TP
        trend_layout = QFormLayout()
        trend_label = QLabel("<b>TREND Mode TP Levels:</b>")
        trend_layout.addRow(trend_label)

        self.trend_tp1_spin = QDoubleSpinBox()
        self.trend_tp1_spin.setRange(0.1, 1000.0)
        self.trend_tp1_spin.setSingleStep(0.5)
        self.trend_tp1_spin.setDecimals(2)
        trend_layout.addRow("TP1:", self.trend_tp1_spin)

        self.trend_tp2_spin = QDoubleSpinBox()
        self.trend_tp2_spin.setRange(0.1, 1000.0)
        self.trend_tp2_spin.setSingleStep(0.5)
        self.trend_tp2_spin.setDecimals(2)
        trend_layout.addRow("TP2:", self.trend_tp2_spin)

        self.trend_tp3_spin = QDoubleSpinBox()
        self.trend_tp3_spin.setRange(0.1, 1000.0)
        self.trend_tp3_spin.setSingleStep(0.5)
        self.trend_tp3_spin.setDecimals(2)
        trend_layout.addRow("TP3:", self.trend_tp3_spin)

        layout.addLayout(trend_layout)

        # RANGE mode TP
        range_layout = QFormLayout()
        range_label = QLabel("<b>RANGE Mode TP Levels:</b>")
        range_layout.addRow(range_label)

        self.range_tp1_spin = QDoubleSpinBox()
        self.range_tp1_spin.setRange(0.1, 1000.0)
        self.range_tp1_spin.setSingleStep(0.5)
        self.range_tp1_spin.setDecimals(2)
        range_layout.addRow("TP1:", self.range_tp1_spin)

        self.range_tp2_spin = QDoubleSpinBox()
        self.range_tp2_spin.setRange(0.1, 1000.0)
        self.range_tp2_spin.setSingleStep(0.5)
        self.range_tp2_spin.setDecimals(2)
        range_layout.addRow("TP2:", self.range_tp2_spin)

        self.range_tp3_spin = QDoubleSpinBox()
        self.range_tp3_spin.setRange(0.1, 1000.0)
        self.range_tp3_spin.setSingleStep(0.5)
        self.range_tp3_spin.setDecimals(2)
        range_layout.addRow("TP3:", self.range_tp3_spin)

        layout.addLayout(range_layout)

        # Unit label
        unit = "%" if self.original_config.exchange == 'Binance' else "points"
        unit_label = QLabel(f"<i>Unit: {unit}</i>")
        layout.addWidget(unit_label)

        return group

    def create_telegram_group(self):
        """Create Telegram settings group"""
        group = QGroupBox("Telegram Notifications")
        layout = QFormLayout(group)

        # Enable checkbox
        self.telegram_enable_check = QCheckBox("Enable Telegram notifications")
        layout.addRow("", self.telegram_enable_check)

        # Token
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setEchoMode(QLineEdit.Password)
        layout.addRow("Bot Token:", self.telegram_token_input)

        # Chat ID
        self.telegram_chat_input = QLineEdit()
        layout.addRow("Chat ID:", self.telegram_chat_input)

        return group

    def load_config(self):
        """Load configuration into form"""
        # Binance API
        if self.original_config.exchange == 'Binance':
            if self.config.get('api_key'):
                self.api_key_input.setText(self.config['api_key'])
            if self.config.get('api_secret'):
                self.api_secret_input.setText(self.config['api_secret'])
            self.testnet_check.setChecked(self.config.get('testnet', True))

        # Trading parameters
        self.symbol_label.setText(self.config['symbol'])
        self.timeframe_combo.setCurrentText(self.config.get('timeframe', '1h'))
        self.risk_spin.setValue(self.config.get('risk_percent', 2.0))
        self.max_pos_spin.setValue(self.config.get('max_positions', 3))
        self.dry_run_check.setChecked(self.config.get('dry_run', True))

        # Strategy
        self.trend_tp1_spin.setValue(self.config.get('trend_tp1', 1.5))
        self.trend_tp2_spin.setValue(self.config.get('trend_tp2', 2.75))
        self.trend_tp3_spin.setValue(self.config.get('trend_tp3', 4.5))
        self.range_tp1_spin.setValue(self.config.get('range_tp1', 1.0))
        self.range_tp2_spin.setValue(self.config.get('range_tp2', 1.75))
        self.range_tp3_spin.setValue(self.config.get('range_tp3', 2.5))

        # Phase 2: 3-Position Mode
        self.use_3pos_check.setChecked(self.config.get('use_3_position_mode', False))

        # Handle None values by using 'or' fallback
        total_pos_default = 100.0 if self.original_config.exchange == 'Binance' else 0.1
        min_order_default = 10.0 if self.original_config.exchange == 'Binance' else 0.01

        self.total_pos_size_spin.setValue(self.config.get('total_position_size') or total_pos_default)
        self.min_order_size_spin.setValue(self.config.get('min_order_size') or min_order_default)
        self.use_trailing_check.setChecked(self.config.get('use_trailing_stops', True))
        self.trailing_stop_pct_spin.setValue(int((self.config.get('trailing_stop_pct') or 0.5) * 100))  # Convert 0.5 to 50

        # Telegram
        self.telegram_enable_check.setChecked(self.config.get('telegram_enabled', False))
        if self.config.get('telegram_token'):
            self.telegram_token_input.setText(self.config['telegram_token'])
        if self.config.get('telegram_chat_id'):
            self.telegram_chat_input.setText(self.config['telegram_chat_id'])

    def save_settings(self):
        """Save settings"""
        # Update config dict
        if self.original_config.exchange == 'Binance':
            self.config['api_key'] = self.api_key_input.text()
            self.config['api_secret'] = self.api_secret_input.text()
            self.config['testnet'] = self.testnet_check.isChecked()

        self.config['timeframe'] = self.timeframe_combo.currentText()
        self.config['risk_percent'] = self.risk_spin.value()
        self.config['max_positions'] = self.max_pos_spin.value()
        self.config['dry_run'] = self.dry_run_check.isChecked()

        self.config['trend_tp1'] = self.trend_tp1_spin.value()
        self.config['trend_tp2'] = self.trend_tp2_spin.value()
        self.config['trend_tp3'] = self.trend_tp3_spin.value()
        self.config['range_tp1'] = self.range_tp1_spin.value()
        self.config['range_tp2'] = self.range_tp2_spin.value()
        self.config['range_tp3'] = self.range_tp3_spin.value()

        # Phase 2: 3-Position Mode
        self.config['use_3_position_mode'] = self.use_3pos_check.isChecked()
        self.config['total_position_size'] = self.total_pos_size_spin.value()
        self.config['min_order_size'] = self.min_order_size_spin.value()
        self.config['use_trailing_stops'] = self.use_trailing_check.isChecked()
        self.config['trailing_stop_pct'] = self.trailing_stop_pct_spin.value() / 100.0  # Convert 50 to 0.5

        self.config['telegram_enabled'] = self.telegram_enable_check.isChecked()
        self.config['telegram_token'] = self.telegram_token_input.text()
        self.config['telegram_chat_id'] = self.telegram_chat_input.text()

        self.accept()

    def get_config(self) -> BotConfig:
        """Get updated configuration"""
        return BotConfig.from_dict(self.config)

    def test_connection(self):
        """Test exchange connection"""
        QMessageBox.information(
            self,
            'Test Connection',
            'Connection test will be implemented in the bot itself.\n\n'
            'Start the bot to test connection.'
        )
