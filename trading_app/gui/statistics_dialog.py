"""
Statistics Dialog - show trading statistics
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QHeaderView, QComboBox, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from models import BotConfig
from database import DatabaseManager


class StatisticsDialog(QDialog):
    """Show trading statistics"""

    def __init__(self, config: BotConfig, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = db

        self.setWindowTitle(f"📊 Statistics - {config.name}")
        self.setMinimumSize(1200, 800)
        
        # Apply modern styling
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
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
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 600;
                min-height: 28px;
                font-size: 12px;
                background-color: #2196F3;
                color: white;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QTableWidget {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background-color: white;
                gridline-color: #F0F0F0;
                alternate-background-color: #FAFAFA;
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
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                min-height: 26px;
            }
        """)

        self.init_ui()
        self.load_statistics()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Period selector
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Period:"))

        self.period_combo = QComboBox()
        self.period_combo.addItems([
            'Last 7 days',
            'Last 30 days',
            'Last 90 days',
            'All time'
        ])
        self.period_combo.currentIndexChanged.connect(self.load_statistics)
        period_layout.addWidget(self.period_combo)
        period_layout.addStretch()

        layout.addLayout(period_layout)

        # Summary section
        summary_group = self.create_summary_section()
        layout.addWidget(summary_group)

        # Trade history table
        history_group = self.create_history_section()
        layout.addWidget(history_group, 1)

        # Buttons
        button_layout = QHBoxLayout()

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_csv)
        button_layout.addWidget(export_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_statistics)
        button_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def create_summary_section(self):
        """Create summary section with modern card-based layout"""
        group = QGroupBox("Summary")
        
        # Use grid layout for cards
        layout = QGridLayout(group)
        layout.setSpacing(10)
        
        # Create placeholders for metric cards
        self.total_trades_card = self.create_metric_card("🎯 Total Trades", "0", "#2196F3")
        self.total_profit_card = self.create_metric_card("💰 Total Profit", "$0.00", "#4CAF50")
        self.win_rate_card = self.create_metric_card("📊 Win Rate", "0%", "#FF9800")
        self.avg_trade_card = self.create_metric_card("📈 Avg Trade", "$0.00", "#9C27B0")
        self.avg_duration_card = self.create_metric_card("⏱️ Avg Duration", "0h", "#00BCD4")
        self.max_drawdown_card = self.create_metric_card("📉 Max Drawdown", "$0.00", "#F44336")
        
        # Arrange cards in 3x2 grid
        layout.addWidget(self.total_trades_card, 0, 0)
        layout.addWidget(self.total_profit_card, 0, 1)
        layout.addWidget(self.win_rate_card, 0, 2)
        layout.addWidget(self.avg_trade_card, 1, 0)
        layout.addWidget(self.avg_duration_card, 1, 1)
        layout.addWidget(self.max_drawdown_card, 1, 2)

        return group
    
    def create_metric_card(self, title, value, color):
        """Create a metric display card"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                padding: 12px;
                min-height: 70px;
            }}
            QLabel {{
                color: white;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        
        # Title label
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Value label  
        value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(18)
        value_font.setBold(True)
        value_label.setFont(value_font)
        layout.addWidget(value_label)
        
        # Store value label for updates
        card.value_label = value_label
        
        layout.addStretch()
        
        return card
    
    def update_metric_card(self, card, value, color=None):
        """Update a metric card with new value and optionally new color"""
        card.value_label.setText(value)
        if color:
            current_style = card.styleSheet()
            # Update color in stylesheet
            new_style = current_style.replace(
                current_style.split('background-color:')[1].split(';')[0],
                f' {color}'
            )
            card.setStyleSheet(new_style)

    def create_history_section(self):
        """Create history section"""
        group = QGroupBox("Trade History")
        layout = QVBoxLayout(group)

        # Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(12)
        self.history_table.setHorizontalHeaderLabels([
            'Date', 'Type', 'Amount', 'Entry', 'Exit', 'SL', 'TP', 
            'Profit', 'Profit %', 'Duration', 'Regime', 'Status'
        ])
        
        # Enable alternating row colors
        self.history_table.setAlternatingRowColors(True)

        # Configure column widths for better readability
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(True)  # Stretch Status column

        # Set specific column widths
        self.history_table.setColumnWidth(0, 130)  # Date
        self.history_table.setColumnWidth(1, 60)   # Type
        self.history_table.setColumnWidth(2, 80)   # Amount
        self.history_table.setColumnWidth(3, 100)  # Entry
        self.history_table.setColumnWidth(4, 100)  # Exit
        self.history_table.setColumnWidth(5, 100)  # SL
        self.history_table.setColumnWidth(6, 100)  # TP
        self.history_table.setColumnWidth(7, 100)  # Profit
        self.history_table.setColumnWidth(8, 80)   # Profit %
        self.history_table.setColumnWidth(9, 90)   # Duration
        self.history_table.setColumnWidth(10, 80)  # Regime
        # Status (column 11) will stretch automatically

        # Allow user to resize columns
        header.setSectionResizeMode(QHeaderView.Interactive)

        layout.addWidget(self.history_table)

        return group

    def load_statistics(self):
        """Load statistics from database"""
        # Get trades
        trades = self.db.get_trades(self.config.bot_id, limit=1000)

        # Filter by period (TODO: implement date filtering)
        # For now, just use all trades

        if not trades:
            # Update cards with zero values
            self.update_metric_card(self.total_trades_card, "0")
            self.update_metric_card(self.total_profit_card, "$0.00")
            self.update_metric_card(self.win_rate_card, "0%")
            self.update_metric_card(self.avg_trade_card, "$0.00")
            self.update_metric_card(self.avg_duration_card, "0h")
            self.update_metric_card(self.max_drawdown_card, "$0.00")
            self.history_table.setRowCount(0)
            return

        # Calculate statistics
        total_trades = len(trades)
        closed_trades = [t for t in trades if t.status in ['TP', 'SL', 'CLOSED'] and t.profit is not None]

        if not closed_trades:
            # Update with partial data
            self.update_metric_card(self.total_trades_card, str(total_trades))
            self.update_metric_card(self.total_profit_card, "$0.00")
            self.update_metric_card(self.win_rate_card, "0%")
            self.update_metric_card(self.avg_trade_card, "$0.00")
            self.update_metric_card(self.avg_duration_card, "0h")
            self.update_metric_card(self.max_drawdown_card, "$0.00")
            self.populate_history_table(trades)
            return

        wins = [t for t in closed_trades if t.profit > 0]
        losses = [t for t in closed_trades if t.profit < 0]

        total_profit = sum(t.profit for t in closed_trades)
        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0

        avg_win = sum(t.profit for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.profit for t in losses) / len(losses) if losses else 0
        avg_trade = total_profit / len(closed_trades) if closed_trades else 0
        
        # Calculate average duration
        durations = []
        for t in closed_trades:
            if t.open_time and t.close_time:
                duration = (t.close_time - t.open_time).total_seconds() / 3600  # hours
                durations.append(duration)
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Calculate max drawdown
        max_loss = min((t.profit for t in losses), default=0)

        # Update metric cards
        self.update_metric_card(self.total_trades_card, str(total_trades))
        
        # Update profit card with color
        profit_color = "#4CAF50" if total_profit >= 0 else "#F44336"
        self.update_metric_card(self.total_profit_card, f"${total_profit:+,.2f}", profit_color)
        
        self.update_metric_card(self.win_rate_card, f"{win_rate:.1f}%")
        
        # Update average trade card with color
        avg_color = "#4CAF50" if avg_trade >= 0 else "#F44336"
        self.update_metric_card(self.avg_trade_card, f"${avg_trade:+,.2f}", avg_color)
        
        self.update_metric_card(self.avg_duration_card, f"{avg_duration:.1f}h")
        self.update_metric_card(self.max_drawdown_card, f"${max_loss:+,.2f}")

        # Populate history table
        self.populate_history_table(trades[:100])  # Show last 100 trades

    def populate_history_table(self, trades):
        """Populate history table"""
        self.history_table.setRowCount(0)

        for i, trade in enumerate(trades):
            self.history_table.insertRow(i)

            # Date
            date_str = trade.open_time.strftime('%Y-%m-%d %H:%M') if trade.open_time else 'N/A'
            self.history_table.setItem(i, 0, QTableWidgetItem(date_str))

            # Type
            self.history_table.setItem(i, 1, QTableWidgetItem(trade.trade_type))

            # Amount
            amount_str = f"{trade.amount:.4f}" if trade.amount else '-'
            self.history_table.setItem(i, 2, QTableWidgetItem(amount_str))

            # Entry
            self.history_table.setItem(i, 3, QTableWidgetItem(f"${trade.entry_price:.2f}"))

            # Exit
            exit_str = f"${trade.close_price:.2f}" if trade.close_price else '-'
            self.history_table.setItem(i, 4, QTableWidgetItem(exit_str))

            # SL
            sl_str = f"${trade.stop_loss:.2f}" if trade.stop_loss else '-'
            self.history_table.setItem(i, 5, QTableWidgetItem(sl_str))

            # TP
            tp_str = f"${trade.take_profit:.2f}" if trade.take_profit else '-'
            self.history_table.setItem(i, 6, QTableWidgetItem(tp_str))

            # Profit
            if trade.profit is not None:
                profit_item = QTableWidgetItem(f"${trade.profit:+.2f}")
                # Bold and color code profits
                font = QFont()
                font.setBold(True)
                profit_item.setFont(font)
                if trade.profit > 0:
                    profit_item.setForeground(QColor("#4CAF50"))  # Green
                elif trade.profit < 0:
                    profit_item.setForeground(QColor("#F44336"))  # Red
                self.history_table.setItem(i, 7, profit_item)
            else:
                self.history_table.setItem(i, 7, QTableWidgetItem('-'))

            # Profit %
            if trade.profit_percent is not None:
                pct_item = QTableWidgetItem(f"{trade.profit_percent:+.2f}%")
                # Bold and color code percentage
                font = QFont()
                font.setBold(True)
                pct_item.setFont(font)
                if trade.profit_percent > 0:
                    pct_item.setForeground(QColor("#4CAF50"))  # Green
                elif trade.profit_percent < 0:
                    pct_item.setForeground(QColor("#F44336"))  # Red
                self.history_table.setItem(i, 8, pct_item)
            else:
                self.history_table.setItem(i, 8, QTableWidgetItem('-'))

            # Duration
            duration_str = f"{trade.duration_hours:.1f}h" if trade.duration_hours else '-'
            self.history_table.setItem(i, 9, QTableWidgetItem(duration_str))

            # Regime
            regime = trade.market_regime or '-'
            self.history_table.setItem(i, 10, QTableWidgetItem(regime))

            # Status with badge styling
            status = trade.status or 'OPEN'
            status_item = QTableWidgetItem(f"{self.get_status_emoji(status)} {status}")
            status_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.history_table.setItem(i, 11, status_item)
    
    def get_status_emoji(self, status):
        """Get emoji for status"""
        status_map = {
            'OPEN': '🟢',
            'TP': '🎯',
            'TP1': '🎯',
            'TP2': '🎯',
            'TP3': '🎯',
            'SL': '🛑',
            'CLOSED': '⚪'
        }
        return status_map.get(status, '⚫')

    def export_csv(self):
        """Export trades to CSV"""
        from PySide6.QtWidgets import QFileDialog
        import csv

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Trades",
            f"{self.config.bot_id}_trades.csv",
            "CSV Files (*.csv)"
        )

        if not filename:
            return

        trades = self.db.get_trades(self.config.bot_id, limit=10000)

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    'Date', 'Type', 'Amount', 'Entry', 'Exit', 'SL', 'TP',
                    'Profit', 'Profit %', 'Duration (h)', 'Regime', 'Status'
                ])

                # Data
                for trade in trades:
                    writer.writerow([
                        trade.open_time.strftime('%Y-%m-%d %H:%M:%S') if trade.open_time else '',
                        trade.trade_type,
                        trade.amount,
                        trade.entry_price,
                        trade.close_price or '',
                        trade.stop_loss,
                        trade.take_profit,
                        trade.profit or '',
                        trade.profit_percent or '',
                        trade.duration_hours or '',
                        trade.market_regime or '',
                        trade.status
                    ])

            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, 'Export Complete', f'Trades exported to:\n{filename}')

        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, 'Export Error', f'Failed to export:\n{str(e)}')
