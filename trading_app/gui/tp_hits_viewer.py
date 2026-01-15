"""
TP Hits Viewer - view history of Take Profit hits
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from models import BotConfig
import csv
import os
from datetime import datetime
from pathlib import Path


class TPHitsViewer(QDialog):
    """View TP hits history"""

    def __init__(self, config: BotConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.tp_hits_file = self._get_tp_hits_file()

        self.setWindowTitle(f"TP Hits History - {config.name}")
        self.setMinimumSize(1200, 700)
        self.resize(1300, 750)

        self.init_ui()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(10000)  # Refresh every 10 seconds

        # Initial load
        self.refresh_data()

    def _get_tp_hits_file(self):
        """Get TP hits file path for this bot"""
        # File is in trading_bots directory
        symbol_clean = self.config.symbol.replace("/", "_")
        filename = f'bot_tp_hits_log_{symbol_clean}.csv'

        # Check in current directory first
        if os.path.exists(filename):
            return filename

        # Check in trading_bots directory
        trading_bots_path = Path(__file__).parent.parent.parent / 'trading_bots' / filename
        if trading_bots_path.exists():
            return str(trading_bots_path)

        return filename  # Return anyway, will create if needed

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Top section - summary
        top_layout = QHBoxLayout()

        # Info label
        self.info_label = QLabel(f"TP hits for {self.config.symbol}")
        self.info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_layout.addWidget(self.info_label)

        top_layout.addStretch()

        # Filter combo
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Show:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "TP1", "TP2", "TP3", "Today", "This Week"])
        self.filter_combo.currentTextChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.filter_combo)
        top_layout.addLayout(filter_layout)

        layout.addLayout(top_layout)

        # TP hits table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            'Timestamp', 'Order ID', 'TP Level', 'Type', 'Amount',
            'Entry', 'TP Target', 'Close Price', 'SL', 'Profit $', 'Profit %'
        ])

        # Configure column widths
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)

        self.table.setColumnWidth(0, 150)  # Timestamp
        self.table.setColumnWidth(1, 100)  # Order ID
        self.table.setColumnWidth(2, 80)   # TP Level
        self.table.setColumnWidth(3, 70)   # Type
        self.table.setColumnWidth(4, 90)   # Amount
        self.table.setColumnWidth(5, 90)   # Entry
        self.table.setColumnWidth(6, 90)   # TP Target
        self.table.setColumnWidth(7, 90)   # Close Price
        self.table.setColumnWidth(8, 90)   # SL
        self.table.setColumnWidth(9, 100)  # Profit $
        # Profit % will stretch

        header.setSectionResizeMode(QHeaderView.Interactive)

        # Enable sorting
        self.table.setSortingEnabled(True)

        layout.addWidget(self.table)

        # Summary section
        self.summary_label = QLabel("No TP hits recorded")
        self.summary_label.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px;")
        layout.addWidget(self.summary_label)

        # Buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
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
        refresh_btn.clicked.connect(self.refresh_data)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()

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
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def refresh_data(self):
        """Refresh TP hits data from CSV"""
        try:
            # Check if file exists
            if not os.path.exists(self.tp_hits_file):
                self.summary_label.setText(f"No TP hits file found: {self.tp_hits_file}")
                self.table.setRowCount(0)
                return

            # Read CSV
            tp_hits = []
            with open(self.tp_hits_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tp_hits.append(row)

            # Apply filter
            filter_text = self.filter_combo.currentText()
            filtered_hits = self._apply_filter(tp_hits, filter_text)

            # Clear table
            self.table.setRowCount(0)
            self.table.setSortingEnabled(False)  # Disable while populating

            if not filtered_hits:
                self.summary_label.setText(f"No TP hits found ({filter_text})")
                return

            # Add data to table
            total_profit = 0.0
            tp_counts = {'TP1': 0, 'TP2': 0, 'TP3': 0}

            for i, hit in enumerate(filtered_hits):
                self.table.insertRow(i)

                # Timestamp
                self.table.setItem(i, 0, QTableWidgetItem(hit.get('Timestamp', '')))

                # Order ID
                self.table.setItem(i, 1, QTableWidgetItem(str(hit.get('Order_ID', ''))))

                # TP Level
                tp_level = hit.get('TP_Level', '')
                tp_item = QTableWidgetItem(tp_level)
                if tp_level == 'TP1':
                    tp_item.setBackground(QColor(220, 255, 220))  # Light green
                    tp_counts['TP1'] += 1
                elif tp_level == 'TP2':
                    tp_item.setBackground(QColor(200, 240, 200))  # Green
                    tp_counts['TP2'] += 1
                elif tp_level == 'TP3':
                    tp_item.setBackground(QColor(180, 220, 180))  # Dark green
                    tp_counts['TP3'] += 1
                self.table.setItem(i, 2, tp_item)

                # Type
                self.table.setItem(i, 3, QTableWidgetItem(hit.get('Type', '')))

                # Amount
                self.table.setItem(i, 4, QTableWidgetItem(hit.get('Amount', '')))

                # Entry Price
                self.table.setItem(i, 5, QTableWidgetItem(f"${float(hit.get('Entry_Price', 0)):.2f}"))

                # TP Target
                self.table.setItem(i, 6, QTableWidgetItem(f"${float(hit.get('TP_Target', 0)):.2f}"))

                # Current/Close Price
                self.table.setItem(i, 7, QTableWidgetItem(f"${float(hit.get('Current_Price', 0)):.2f}"))

                # SL
                self.table.setItem(i, 8, QTableWidgetItem(f"${float(hit.get('SL', 0)):.2f}"))

                # Profit $
                profit = float(hit.get('Profit', 0))
                profit_item = QTableWidgetItem(f"${profit:+.2f}")
                if profit > 0:
                    profit_item.setForeground(Qt.darkGreen)
                elif profit < 0:
                    profit_item.setForeground(Qt.red)
                self.table.setItem(i, 9, profit_item)

                # Profit %
                profit_pct = float(hit.get('Profit_Pct', 0))
                profit_pct_item = QTableWidgetItem(f"{profit_pct:+.2f}%")
                if profit_pct > 0:
                    profit_pct_item.setForeground(Qt.darkGreen)
                elif profit_pct < 0:
                    profit_pct_item.setForeground(Qt.red)
                self.table.setItem(i, 10, profit_pct_item)

                total_profit += profit

            # Re-enable sorting
            self.table.setSortingEnabled(True)

            # Update summary
            summary_color = "green" if total_profit >= 0 else "red"
            tp_breakdown = f"TP1: {tp_counts['TP1']} | TP2: {tp_counts['TP2']} | TP3: {tp_counts['TP3']}"
            self.summary_label.setText(
                f"<b>Total TP Hits: {len(filtered_hits)} ({tp_breakdown}) | "
                f"<span style='color: {summary_color};'>Total Profit: ${total_profit:+.2f}</span></b>"
            )

        except Exception as e:
            self.summary_label.setText(f"Error loading TP hits: {str(e)}")
            print(f"Error in TPHitsViewer: {e}")

    def _apply_filter(self, tp_hits, filter_text):
        """Apply filter to TP hits data"""
        if filter_text == "All":
            return tp_hits

        if filter_text in ["TP1", "TP2", "TP3"]:
            return [hit for hit in tp_hits if hit.get('TP_Level') == filter_text]

        if filter_text == "Today":
            today = datetime.now().date()
            filtered = []
            for hit in tp_hits:
                try:
                    hit_date = datetime.strptime(hit.get('Timestamp', ''), '%Y-%m-%d %H:%M:%S').date()
                    if hit_date == today:
                        filtered.append(hit)
                except:
                    pass
            return filtered

        if filter_text == "This Week":
            from datetime import timedelta
            week_ago = datetime.now() - timedelta(days=7)
            filtered = []
            for hit in tp_hits:
                try:
                    hit_date = datetime.strptime(hit.get('Timestamp', ''), '%Y-%m-%d %H:%M:%S')
                    if hit_date >= week_ago:
                        filtered.append(hit)
                except:
                    pass
            return filtered

        return tp_hits

    def closeEvent(self, event):
        """Handle close event"""
        self.refresh_timer.stop()
        event.accept()
