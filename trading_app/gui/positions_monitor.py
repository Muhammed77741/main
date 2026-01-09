"""
Positions Monitor - monitor open positions
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView
)
from PySide6.QtCore import Qt, QTimer
from models import BotConfig


class PositionsMonitor(QDialog):
    """Monitor open positions"""

    def __init__(self, config: BotConfig, parent=None):
        super().__init__(parent)
        self.config = config

        self.setWindowTitle(f"Open Positions - {config.name}")
        self.setMinimumSize(1000, 600)  # Increased width for better column visibility
        self.resize(1100, 650)  # Default size

        self.init_ui()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_positions)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

        # Initial load
        self.refresh_positions()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Info label
        self.info_label = QLabel(f"Monitoring positions for {self.config.symbol}")
        layout.addWidget(self.info_label)

        # Positions table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            'Order ID', 'Type', 'Amount', 'Entry', 'Current', 'SL', 'TP', 'P&L'
        ])

        # Configure column widths for better readability
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)  # Stretch P&L column

        # Set specific column widths
        self.table.setColumnWidth(0, 100)  # Order ID
        self.table.setColumnWidth(1, 70)   # Type
        self.table.setColumnWidth(2, 100)  # Amount
        self.table.setColumnWidth(3, 100)  # Entry
        self.table.setColumnWidth(4, 100)  # Current
        self.table.setColumnWidth(5, 100)  # SL
        self.table.setColumnWidth(6, 100)  # TP
        # P&L (column 7) will stretch automatically

        # Allow user to resize columns
        header.setSectionResizeMode(QHeaderView.Interactive)

        layout.addWidget(self.table)

        # Summary label
        self.summary_label = QLabel("No positions")
        layout.addWidget(self.summary_label)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_positions)
        layout.addWidget(refresh_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def refresh_positions(self):
        """Refresh positions from exchange"""
        try:
            positions = self.get_positions()

            # Clear table
            self.table.setRowCount(0)

            if not positions:
                self.summary_label.setText("No open positions")
                return

            # Add positions to table
            total_pnl = 0.0

            for i, pos in enumerate(positions):
                self.table.insertRow(i)

                # Order ID
                self.table.setItem(i, 0, QTableWidgetItem(str(pos.get('id', 'N/A'))))

                # Type
                pos_type = pos.get('side', 'N/A').upper()
                self.table.setItem(i, 1, QTableWidgetItem(pos_type))

                # Amount
                amount = pos.get('contracts', pos.get('amount', 0))
                self.table.setItem(i, 2, QTableWidgetItem(f"{amount:.4f}"))

                # Entry price
                entry = pos.get('entryPrice', pos.get('price_open', 0))
                self.table.setItem(i, 3, QTableWidgetItem(f"${entry:.2f}"))

                # Current price
                current = pos.get('markPrice', pos.get('price_current', entry))
                self.table.setItem(i, 4, QTableWidgetItem(f"${current:.2f}"))

                # SL
                sl = pos.get('stopLoss', pos.get('sl', 0))
                self.table.setItem(i, 5, QTableWidgetItem(f"${sl:.2f}" if sl else 'N/A'))

                # TP
                tp = pos.get('takeProfit', pos.get('tp', 0))
                self.table.setItem(i, 6, QTableWidgetItem(f"${tp:.2f}" if tp else 'N/A'))

                # P&L
                pnl = pos.get('unrealizedPnl', pos.get('profit', 0))
                pnl_item = QTableWidgetItem(f"${pnl:+.2f}")

                # Color code P&L
                if pnl > 0:
                    pnl_item.setForeground(Qt.green)
                elif pnl < 0:
                    pnl_item.setForeground(Qt.red)

                self.table.setItem(i, 7, pnl_item)

                total_pnl += pnl

            # Update summary
            summary_color = "green" if total_pnl >= 0 else "red"
            self.summary_label.setText(
                f"<b>{len(positions)} position(s) | "
                f"<span style='color: {summary_color};'>Total P&L: ${total_pnl:+.2f}</span></b>"
            )

        except Exception as e:
            self.summary_label.setText(f"Error loading positions: {str(e)}")

    def get_positions(self):
        """Get open positions from exchange"""
        positions = []

        try:
            if self.config.exchange == 'MT5':
                import MetaTrader5 as mt5

                if not mt5.initialize():
                    return positions

                mt5_positions = mt5.positions_get(symbol=self.config.symbol)

                if mt5_positions:
                    for pos in mt5_positions:
                        positions.append({
                            'id': pos.ticket,
                            'side': 'buy' if pos.type == 0 else 'sell',
                            'contracts': pos.volume,
                            'entryPrice': pos.price_open,
                            'markPrice': pos.price_current,
                            'stopLoss': pos.sl,
                            'takeProfit': pos.tp,
                            'unrealizedPnl': pos.profit
                        })

            elif self.config.exchange == 'Binance':
                import ccxt

                # Create exchange instance with proper testnet/mainnet configuration
                if self.config.testnet:
                    # Testnet configuration
                    exchange = ccxt.binance({
                        'apiKey': self.config.api_key,
                        'secret': self.config.api_secret,
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'future',
                            'adjustForTimeDifference': True,
                        },
                        'urls': {
                            'api': {
                                'public': 'https://testnet.binancefuture.com/fapi/v1',
                                'private': 'https://testnet.binancefuture.com/fapi/v1',
                            }
                        }
                    })
                else:
                    # Mainnet configuration
                    exchange = ccxt.binance({
                        'apiKey': self.config.api_key,
                        'secret': self.config.api_secret,
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'future',
                            'adjustForTimeDifference': True,
                        }
                    })

                # Fetch positions
                print(f"🔍 Fetching positions for {self.config.symbol}...")
                binance_positions = exchange.fetch_positions([self.config.symbol])

                print(f"📊 Raw positions data: {len(binance_positions)} positions returned")

                for i, pos in enumerate(binance_positions):
                    contracts = float(pos.get('contracts', 0))
                    side = pos.get('side', 'unknown')
                    info = pos.get('info', {})

                    print(f"   Position {i+1}: side={side}, contracts={contracts}")
                    print(f"   Full data: {pos}")

                    if contracts > 0:
                        positions.append(pos)
                        print(f"   ✅ Added to display")
                    else:
                        print(f"   ⚠️  Skipped (no contracts)")

        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            import traceback
            traceback.print_exc()

        return positions

    def closeEvent(self, event):
        """Handle close event"""
        self.refresh_timer.stop()
        event.accept()
