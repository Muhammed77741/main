"""
Positions Monitor - monitor open positions
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from models import BotConfig


class PositionFetcherThread(QThread):
    """Thread for fetching positions from exchange without blocking GUI"""

    positions_fetched = Signal(list)  # Signal with positions data
    error_occurred = Signal(str)  # Signal with error message

    def __init__(self, config: BotConfig, db_manager=None):
        super().__init__()
        self.config = config
        self.db_manager = db_manager

    def run(self):
        """Fetch positions in background thread"""
        try:
            positions = self._fetch_positions()
            self.positions_fetched.emit(positions)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _fetch_positions(self):
        """Get open positions from exchange or database (dry_run)"""
        positions = []

        try:
            # Check if in dry_run mode - fetch from database instead
            if self.config.dry_run and self.db_manager:
                print(f"🧪 DRY RUN: Fetching positions from database for {self.config.symbol}...")
                
                open_trades = self.db_manager.get_open_trades(self.config.bot_id)
                
                print(f"📊 Found {len(open_trades)} open trades in database")
                
                # Try to get current price for P&L calculation
                current_price = None
                try:
                    if self.config.exchange == 'Binance':
                        import ccxt
                        # Use public data (no credentials needed for ticker)
                        exchange = ccxt.binance({
                            'enableRateLimit': True,
                            'options': {'defaultType': 'future'}
                        })
                        ticker = exchange.fetch_ticker(self.config.symbol)
                        current_price = ticker.get('last')
                        if current_price:
                            print(f"💰 Current {self.config.symbol} price: ${current_price:.2f}")
                    elif self.config.exchange == 'MT5':
                        import MetaTrader5 as mt5
                        if mt5.initialize():
                            try:
                                tick = mt5.symbol_info_tick(self.config.symbol)
                                if tick:
                                    current_price = tick.last
                                    print(f"💰 Current {self.config.symbol} price: ${current_price:.2f}")
                            finally:
                                mt5.shutdown()
                except Exception as e:
                    print(f"⚠️  Could not fetch current price for P&L: {e}")
                
                for trade in open_trades:
                    # Calculate unrealized P&L if we have current price
                    mark_price = current_price if current_price else trade.entry_price
                    unrealized_pnl = 0.0
                    
                    if current_price:
                        if trade.trade_type.upper() == 'BUY':
                            unrealized_pnl = (current_price - trade.entry_price) * trade.amount
                        elif trade.trade_type.upper() == 'SELL':
                            unrealized_pnl = (trade.entry_price - current_price) * trade.amount
                    
                    # Convert database trade record to position format
                    positions.append({
                        'id': trade.order_id or f"DRY-{trade.trade_id}",
                        'side': trade.trade_type.lower(),
                        'contracts': trade.amount,
                        'entryPrice': trade.entry_price,
                        'markPrice': mark_price,
                        'stopLoss': trade.stop_loss,
                        'takeProfit': trade.take_profit,
                        'unrealizedPnl': unrealized_pnl
                    })
                    print(f"   ✅ Loaded: {trade.trade_type} {trade.amount} @ ${trade.entry_price:.2f} | P&L: ${unrealized_pnl:+.2f}")
                
                return positions
            
            # Not dry_run - fetch from exchange
            if self.config.exchange == 'MT5':
                import MetaTrader5 as mt5

                # Initialize MT5
                if not mt5.initialize():
                    print(f"⚠️  MT5 initialization failed: {mt5.last_error()}")
                    return positions

                try:
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
                finally:
                    # Always shutdown MT5 to avoid resource leaks
                    mt5.shutdown()

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

                    print(f"   Position {i+1}: side={side}, contracts={contracts}")

                    if contracts > 0:
                        positions.append(pos)
                        print(f"   ✅ Added to display")
                    else:
                        print(f"   ⚠️  Skipped (no contracts)")

        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            import traceback
            traceback.print_exc()
            raise

        return positions


class PositionsMonitor(QDialog):
    """Monitor open positions"""

    def __init__(self, config: BotConfig, db_manager=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.db_manager = db_manager
        self.fetcher_thread = None
        self.is_fetching = False
        self.is_closing = False  # Flag to prevent operations during close

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
        """Refresh positions from exchange - non-blocking"""
        # Skip if already fetching or closing
        if self.is_fetching or self.is_closing:
            return

        # Show loading state
        self.summary_label.setText("🔄 Loading positions...")

        # Start fetcher thread
        self.is_fetching = True
        self.fetcher_thread = PositionFetcherThread(self.config, self.db_manager)
        self.fetcher_thread.positions_fetched.connect(self._on_positions_fetched)
        self.fetcher_thread.error_occurred.connect(self._on_fetch_error)
        self.fetcher_thread.finished.connect(self._on_fetch_finished)
        self.fetcher_thread.start()

    def _on_positions_fetched(self, positions):
        """Handle positions data received from thread"""
        # Skip if dialog is closing
        if self.is_closing:
            return
        
        print(f"📥 Positions fetched callback: {len(positions)} positions")
            
        try:
            # Clear table
            self.table.setRowCount(0)

            if not positions:
                self.summary_label.setText("No open positions")
                print("ℹ️  No positions to display")
                return

            print(f"📋 Displaying {len(positions)} positions in GUI...")
            
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
                
                print(f"   ✅ Row {i+1}: {pos_type} {amount:.4f} @ ${entry:.2f} | P&L: ${pnl:+.2f}")

            # Update summary
            summary_color = "green" if total_pnl >= 0 else "red"
            self.summary_label.setText(
                f"<b>{len(positions)} position(s) | "
                f"<span style='color: {summary_color};'>Total P&L: ${total_pnl:+.2f}</span></b>"
            )
            
            print(f"✅ GUI updated successfully with {len(positions)} positions")

        except Exception as e:
            error_msg = f"Error displaying positions: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            if not self.is_closing:
                self.summary_label.setText(error_msg)

    def _on_fetch_error(self, error_msg):
        """Handle fetch error"""
        if not self.is_closing:
            self.summary_label.setText(f"❌ Error: {error_msg}")

    def _on_fetch_finished(self):
        """Handle thread finished"""
        self.is_fetching = False
        # Disconnect signals to avoid memory leaks
        if self.fetcher_thread:
            try:
                self.fetcher_thread.positions_fetched.disconnect()
                self.fetcher_thread.error_occurred.disconnect()
                self.fetcher_thread.finished.disconnect()
            except:
                pass  # Ignore if already disconnected

    def closeEvent(self, event):
        """Handle close event"""
        # Set closing flag to prevent new operations
        self.is_closing = True
        
        # Stop refresh timer
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()

        # Stop fetcher thread if running
        if self.fetcher_thread and self.fetcher_thread.isRunning():
            # Disconnect signals first to avoid callbacks during shutdown
            try:
                self.fetcher_thread.positions_fetched.disconnect()
                self.fetcher_thread.error_occurred.disconnect()
                self.fetcher_thread.finished.disconnect()
            except:
                pass  # Ignore if already disconnected
            
            # Request thread to quit
            self.fetcher_thread.quit()
            
            # Wait for thread to finish (with timeout)
            if not self.fetcher_thread.wait(2000):  # Wait max 2 seconds
                # Force terminate if thread doesn't quit gracefully
                self.fetcher_thread.terminate()
                self.fetcher_thread.wait(1000)  # Wait for termination

        event.accept()
