"""
Statistics Dialog - show trading statistics
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt
from models import BotConfig
from database import DatabaseManager


class StatisticsDialog(QDialog):
    """Show trading statistics"""

    def __init__(self, config: BotConfig, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = db

        self.setWindowTitle(f"Statistics - {config.name}")
        self.setMinimumSize(1000, 700)

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
        """Create summary section"""
        group = QGroupBox("Summary")
        layout = QVBoxLayout(group)

        self.summary_label = QLabel("Loading...")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        return group

    def create_history_section(self):
        """Create history section"""
        group = QGroupBox("Trade History")
        layout = QVBoxLayout(group)

        # Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            'Date', 'Type', 'Entry', 'Exit', 'Profit', 'Profit %', 'Pips', 'Duration', 'Regime'
        ])

        # Resize columns
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        layout.addWidget(self.history_table)

        return group

    def load_statistics(self):
        """Load statistics from database"""
        # Get trades
        trades = self.db.get_trades(self.config.bot_id, limit=1000)

        # Filter by period (TODO: implement date filtering)
        # For now, just use all trades

        if not trades:
            self.summary_label.setText("No trades yet")
            self.history_table.setRowCount(0)
            return

        # Calculate statistics
        total_trades = len(trades)
        closed_trades = [t for t in trades if t.status in ['TP', 'SL', 'CLOSED'] and t.profit is not None]

        if not closed_trades:
            self.summary_label.setText(f"Total trades: {total_trades} (none closed yet)")
            self.populate_history_table(trades)
            return

        wins = [t for t in closed_trades if t.profit > 0]
        losses = [t for t in closed_trades if t.profit < 0]

        total_profit = sum(t.profit for t in closed_trades)
        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0

        avg_win = sum(t.profit for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.profit for t in losses) / len(losses) if losses else 0
        max_win = max((t.profit for t in wins), default=0)
        max_loss = min((t.profit for t in losses), default=0)

        # Profit factor
        total_wins = sum(t.profit for t in wins)
        total_losses = abs(sum(t.profit for t in losses))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

        # Format summary
        summary_html = f"""
        <p><b>Total Trades:</b> {total_trades} ({len(closed_trades)} closed)</p>
        <p><b>Win Rate:</b> {win_rate:.1f}% ({len(wins)}W / {len(losses)}L)</p>
        <p><b>Total P&L:</b> <span style='color: {"green" if total_profit >= 0 else "red"};'>${total_profit:+,.2f}</span></p>
        <p><b>Avg Win:</b> ${avg_win:,.2f} | <b>Avg Loss:</b> ${avg_loss:,.2f}</p>
        <p><b>Best Trade:</b> <span style='color: green;'>${max_win:+,.2f}</span> |
           <b>Worst Trade:</b> <span style='color: red;'>${max_loss:+,.2f}</span></p>
        <p><b>Profit Factor:</b> {profit_factor:.2f}</p>
        """

        # By regime
        trend_trades = [t for t in closed_trades if t.market_regime == 'TREND']
        range_trades = [t for t in closed_trades if t.market_regime == 'RANGE']

        if trend_trades or range_trades:
            summary_html += "<p><b>By Market Regime:</b></p>"
            if trend_trades:
                trend_pnl = sum(t.profit for t in trend_trades)
                summary_html += f"<p>• TREND: {len(trend_trades)} trades, ${trend_pnl:+,.2f}</p>"
            if range_trades:
                range_pnl = sum(t.profit for t in range_trades)
                summary_html += f"<p>• RANGE: {len(range_trades)} trades, ${range_pnl:+,.2f}</p>"

        self.summary_label.setText(summary_html)

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

            # Entry
            self.history_table.setItem(i, 2, QTableWidgetItem(f"${trade.entry_price:.2f}"))

            # Exit
            exit_str = f"${trade.close_price:.2f}" if trade.close_price else 'OPEN'
            self.history_table.setItem(i, 3, QTableWidgetItem(exit_str))

            # Profit
            if trade.profit is not None:
                profit_item = QTableWidgetItem(f"${trade.profit:+.2f}")
                if trade.profit > 0:
                    profit_item.setForeground(Qt.green)
                elif trade.profit < 0:
                    profit_item.setForeground(Qt.red)
                self.history_table.setItem(i, 4, profit_item)
            else:
                self.history_table.setItem(i, 4, QTableWidgetItem('OPEN'))

            # Profit %
            if trade.profit_percent is not None:
                pct_item = QTableWidgetItem(f"{trade.profit_percent:+.2f}%")
                if trade.profit_percent > 0:
                    pct_item.setForeground(Qt.green)
                elif trade.profit_percent < 0:
                    pct_item.setForeground(Qt.red)
                self.history_table.setItem(i, 5, pct_item)
            else:
                self.history_table.setItem(i, 5, QTableWidgetItem('-'))

            # Pips (calculate from entry/exit)
            pips = '-'
            if trade.close_price and trade.entry_price:
                if self.config.exchange == 'MT5':
                    # For XAUUSD
                    pips_val = (trade.close_price - trade.entry_price) * 10 if trade.trade_type == 'BUY' else (trade.entry_price - trade.close_price) * 10
                    pips = f"{pips_val:.1f}p"
                else:
                    # For crypto, show %
                    pips_val = ((trade.close_price - trade.entry_price) / trade.entry_price * 100) if trade.trade_type == 'BUY' else ((trade.entry_price - trade.close_price) / trade.entry_price * 100)
                    pips = f"{pips_val:.2f}%"

            self.history_table.setItem(i, 6, QTableWidgetItem(pips))

            # Duration
            duration_str = f"{trade.duration_hours:.1f}h" if trade.duration_hours else 'OPEN'
            self.history_table.setItem(i, 7, QTableWidgetItem(duration_str))

            # Regime
            regime = trade.market_regime or '-'
            self.history_table.setItem(i, 8, QTableWidgetItem(regime))

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
