"""
Positions Monitor - monitor open positions
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from models import BotConfig


class PositionFetcherThread(QThread):
    """Thread for fetching positions from exchange without blocking GUI"""

    positions_fetched = Signal(list)  # Signal with positions data
    error_occurred = Signal(str)  # Signal with error message
    current_price_fetched = Signal(float)  # Signal with current price

    def __init__(self, config: BotConfig, db_manager=None):
        super().__init__()
        self.config = config
        self.db_manager = db_manager
        self.current_price = None

    def run(self):
        """Fetch positions in background thread"""
        try:
            positions = self._fetch_positions()
            self.positions_fetched.emit(positions)
            # Emit current price if available
            if self.current_price and self.current_price > 0:
                self.current_price_fetched.emit(self.current_price)
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
                        if current_price and current_price > 0:
                            print(f"💰 Current {self.config.symbol} price: ${current_price:.2f}")
                        else:
                            print(f"⚠️  Invalid price received: {current_price}")
                    elif self.config.exchange == 'MT5':
                        import MetaTrader5 as mt5
                        if mt5.initialize():
                            try:
                                tick = mt5.symbol_info_tick(self.config.symbol)
                                if tick and tick.last > 0:
                                    current_price = tick.last
                                    print(f"💰 Current {self.config.symbol} price: ${current_price:.2f}")
                                elif tick:
                                    # Try bid/ask if last is not available
                                    current_price = (tick.bid + tick.ask) / 2 if tick.bid > 0 and tick.ask > 0 else None
                                    if current_price:
                                        print(f"💰 Current {self.config.symbol} price: ${current_price:.2f} (from bid/ask)")
                                    else:
                                        print(f"⚠️  MT5 tick data invalid: last={tick.last}, bid={tick.bid}, ask={tick.ask}")
                                else:
                                    print(f"⚠️  MT5 symbol_info_tick returned None for {self.config.symbol}")
                            finally:
                                mt5.shutdown()
                        else:
                            print(f"⚠️  MT5 initialization failed: {mt5.last_error()}")
                except Exception as e:
                    print(f"⚠️  Could not fetch current price for P&L: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Store current price for signal emission
                self.current_price = current_price
                
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
        self.current_price = None  # Store current price

        self.setWindowTitle(f"Open Positions - {config.name}")
        self.setMinimumSize(1000, 600)  # Increased width for better column visibility
        self.resize(1100, 650)  # Default size

        self.init_ui()

        # Auto-refresh timer (10 seconds as requested)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_positions)
        # Don't start automatically - user can enable via checkbox

        # Initial load
        self.refresh_positions()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Info label with symbol and current price
        self.info_label = QLabel(f"Monitoring positions for {self.config.symbol}")
        layout.addWidget(self.info_label)
        
        # Current price label (prominently displayed)
        self.price_label = QLabel("💰 Current Price: Loading...")
        self.price_label.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 5px;")
        layout.addWidget(self.price_label)

        # Positions table
        self.table = QTableWidget()
        self.table.setColumnCount(9)  # Added checkbox column
        self.table.setHorizontalHeaderLabels([
            'Select', 'Order ID', 'Type', 'Amount', 'Entry', 'Current', 'SL', 'TP', 'P&L'
        ])
        
        # Enable selection
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.MultiSelection)

        # Configure column widths for better readability
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)  # Stretch P&L column

        # Set specific column widths
        self.table.setColumnWidth(0, 60)   # Select checkbox
        self.table.setColumnWidth(1, 100)  # Order ID
        self.table.setColumnWidth(2, 70)   # Type
        self.table.setColumnWidth(3, 100)  # Amount
        self.table.setColumnWidth(4, 100)  # Entry
        self.table.setColumnWidth(5, 100)  # Current
        self.table.setColumnWidth(6, 100)  # SL
        self.table.setColumnWidth(7, 100)  # TP
        # P&L (column 8) will stretch automatically

        # Allow user to resize columns
        header.setSectionResizeMode(QHeaderView.Interactive)

        layout.addWidget(self.table)

        # Summary label
        self.summary_label = QLabel("No positions")
        layout.addWidget(self.summary_label)

        # Control buttons layout
        controls_layout = QHBoxLayout()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.clicked.connect(self.refresh_positions)
        controls_layout.addWidget(refresh_btn)
        
        # Close Selected button
        self.close_selected_btn = QPushButton("❌ Close Selected Positions")
        self.close_selected_btn.clicked.connect(self.close_selected_positions)
        self.close_selected_btn.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold;")
        self.close_selected_btn.setEnabled(False)  # Disabled until positions are loaded
        controls_layout.addWidget(self.close_selected_btn)
        
        # Auto-refresh checkbox
        self.auto_refresh_checkbox = QCheckBox("Auto-refresh every 10s")
        self.auto_refresh_checkbox.setChecked(False)
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        controls_layout.addWidget(self.auto_refresh_checkbox)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def toggle_auto_refresh(self, state):
        """Toggle auto-refresh timer"""
        if state == Qt.Checked:
            # Enable auto-refresh every 10 seconds
            self.refresh_timer.start(10000)  # 10 seconds
            print("✅ Auto-refresh enabled (every 10 seconds)")
        else:
            # Disable auto-refresh
            self.refresh_timer.stop()
            print("⏸️  Auto-refresh disabled")
    
    def close_selected_positions(self):
        """Close selected positions"""
        from PySide6.QtWidgets import QMessageBox
        
        # Get selected positions
        selected_positions = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                order_id = self.table.item(row, 1).text()
                pos_type = self.table.item(row, 2).text()
                amount = self.table.item(row, 3).text()
                selected_positions.append({
                    'row': row,
                    'order_id': order_id,
                    'type': pos_type,
                    'amount': amount
                })
        
        if not selected_positions:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("No Selection")
            msg.setText("Please select at least one position to close.")
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #333;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            msg.exec()
            return
        
        # Confirm closure
        position_list = "\n".join([
            f"- {pos['type']} {pos['amount']} (ID: {pos['order_id']})"
            for pos in selected_positions
        ])
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Confirm Close Positions")
        msg.setText(f"Are you sure you want to close {len(selected_positions)} position(s)?\n\n{position_list}")
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
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        reply = msg.exec()
        
        if reply != msg.button(QMessageBox.Yes):
            return
        
        # Close positions
        self.summary_label.setText(f"🔄 Closing {len(selected_positions)} position(s)...")
        success_count = 0
        error_count = 0
        errors = []
        
        try:
            # Check if positions are dry_run positions (start with "DRY-")
            dry_run_positions = [p for p in selected_positions if p['order_id'].startswith('DRY-')]
            exchange_positions = [p for p in selected_positions if not p['order_id'].startswith('DRY-')]
            
            # Close dry_run positions in database only
            if dry_run_positions and self.config.dry_run and self.db_manager:
                print(f"🧪 DRY RUN: Closing {len(dry_run_positions)} positions in database...")
                for pos in dry_run_positions:
                    try:
                        # Find position in database by order_id
                        open_trades = self.db_manager.get_open_trades(self.config.bot_id)
                        matching_trade = None
                        for trade in open_trades:
                            if trade.order_id == pos['order_id']:
                                matching_trade = trade
                                break
                        
                        if not matching_trade:
                            errors.append(f"DRY position {pos['order_id']} not found in database")
                            error_count += 1
                            continue
                        
                        # Get current price for P&L calculation
                        current_price = None
                        try:
                            if self.config.exchange == 'Binance':
                                import ccxt
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
                                        if tick:
                                            current_price = tick.last if tick.last > 0 else (tick.bid + tick.ask) / 2
                                    finally:
                                        mt5.shutdown()
                        except:
                            current_price = matching_trade.entry_price  # Fallback to entry price
                        
                        if not current_price or current_price <= 0:
                            current_price = matching_trade.entry_price
                        
                        # Calculate profit
                        if matching_trade.trade_type.upper() == 'BUY':
                            profit = (current_price - matching_trade.entry_price) * matching_trade.amount
                        else:
                            profit = (matching_trade.entry_price - current_price) * matching_trade.amount
                        
                        profit_percent = (profit / (matching_trade.entry_price * matching_trade.amount)) * 100 if matching_trade.entry_price > 0 else 0
                        
                        # Update trade in database
                        from datetime import datetime
                        matching_trade.close_time = datetime.now()
                        matching_trade.close_price = current_price
                        matching_trade.profit = profit
                        matching_trade.profit_percent = profit_percent
                        matching_trade.status = 'CLOSED'
                        matching_trade.comment = (matching_trade.comment or '') + ' | Manual close from GUI'
                        
                        self.db_manager.update_trade(matching_trade)
                        
                        print(f"✅ DRY RUN: Closed position {pos['order_id']} in database (P&L: ${profit:+.2f})")
                        success_count += 1
                    
                    except Exception as e:
                        errors.append(f"DRY position {pos['order_id']}: {str(e)}")
                        error_count += 1
                        import traceback
                        traceback.print_exc()
            
            # If no database manager but there are dry_run positions, show error
            elif dry_run_positions and not self.db_manager:
                for pos in dry_run_positions:
                    errors.append(f"DRY position {pos['order_id']}: No database manager available")
                    error_count += len(dry_run_positions)
            
            # Close exchange positions normally
            if not exchange_positions:
                # No exchange positions to close
                pass
            elif self.config.exchange == 'MT5':
                import MetaTrader5 as mt5
                
                if not mt5.initialize():
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Critical)
                    msg.setWindowTitle("Error")
                    msg.setText(f"MT5 initialization failed: {mt5.last_error()}")
                    msg.setStyleSheet("""
                        QMessageBox {
                            background-color: white;
                        }
                        QMessageBox QLabel {
                            color: #333;
                            font-size: 13px;
                        }
                        QPushButton {
                            background-color: #F44336;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            padding: 8px 16px;
                            min-width: 80px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #D32F2F;
                        }
                    """)
                    msg.exec()
                    return
                
                try:
                    for pos in exchange_positions:
                        try:
                            ticket = int(pos['order_id'])
                            
                            # Get position details from MT5
                            mt5_pos = mt5.positions_get(ticket=ticket)
                            if not mt5_pos or len(mt5_pos) == 0:
                                errors.append(f"Position {ticket} not found")
                                error_count += 1
                                continue
                            
                            mt5_pos = mt5_pos[0]
                            
                            # Determine close order type
                            order_type = mt5.ORDER_TYPE_SELL if mt5_pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                            
                            # Get current price
                            tick = mt5.symbol_info_tick(self.config.symbol)
                            if not tick:
                                errors.append(f"Could not get price for {ticket}")
                                error_count += 1
                                continue
                            
                            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
                            
                            # Close request
                            request = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "symbol": self.config.symbol,
                                "volume": mt5_pos.volume,
                                "type": order_type,
                                "position": ticket,
                                "price": price,
                                "deviation": 20,
                                "magic": 234000,
                                "comment": "Manual close from GUI",
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC,
                            }
                            
                            result = mt5.order_send(request)
                            
                            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"✅ Closed position {ticket}")
                                success_count += 1
                            else:
                                error_msg = result.comment if result else "No result"
                                errors.append(f"Position {ticket}: {error_msg}")
                                error_count += 1
                        
                        except Exception as e:
                            errors.append(f"Position {pos['order_id']}: {str(e)}")
                            error_count += 1
                
                finally:
                    mt5.shutdown()
            
            elif self.config.exchange == 'Binance' and exchange_positions:
                import ccxt
                
                # Create exchange instance
                if self.config.testnet:
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
                    exchange = ccxt.binance({
                        'apiKey': self.config.api_key,
                        'secret': self.config.api_secret,
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'future',
                            'adjustForTimeDifference': True,
                        }
                    })
                
                for pos in exchange_positions:
                    try:
                        # Close position by placing opposite order
                        # Binance requires us to fetch current position and close with market order
                        positions = exchange.fetch_positions([self.config.symbol])
                        
                        # Find matching position
                        matching_pos = None
                        for p in positions:
                            if str(p.get('id')) == pos['order_id']:
                                matching_pos = p
                                break
                        
                        if not matching_pos:
                            errors.append(f"Position {pos['order_id']} not found")
                            error_count += 1
                            continue
                        
                        contracts = float(matching_pos.get('contracts', 0))
                        if contracts <= 0:
                            errors.append(f"Position {pos['order_id']} has no contracts")
                            error_count += 1
                            continue
                        
                        # Determine side for closing
                        pos_side = matching_pos.get('side', '').lower()
                        close_side = 'sell' if pos_side == 'long' else 'buy'
                        
                        # Place market order to close
                        order = exchange.create_order(
                            symbol=self.config.symbol,
                            type='market',
                            side=close_side,
                            amount=contracts,
                            params={'reduceOnly': True}
                        )
                        
                        print(f"✅ Closed Binance position {pos['order_id']}")
                        success_count += 1
                    
                    except Exception as e:
                        errors.append(f"Position {pos['order_id']}: {str(e)}")
                        error_count += 1
            
            elif exchange_positions:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("Error")
                msg.setText(f"Unsupported exchange: {self.config.exchange}")
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: white;
                    }
                    QMessageBox QLabel {
                        color: #333;
                        font-size: 13px;
                    }
                    QPushButton {
                        background-color: #F44336;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 8px 16px;
                        min-width: 80px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #D32F2F;
                    }
                """)
                msg.exec()
                return
        
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Error")
            msg.setText(f"Error closing positions: {str(e)}")
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #333;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                }
            """)
            msg.exec()
            import traceback
            traceback.print_exc()
            return
        
        # Show result
        result_msg = f"✅ Successfully closed {success_count} position(s)"
        if error_count > 0:
            result_msg += f"\n❌ Failed to close {error_count} position(s)"
            if errors:
                result_msg += "\n\nErrors:\n" + "\n".join(errors[:5])  # Show first 5 errors
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Close Positions Result")
        msg.setText(result_msg)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #333;
                font-size: 13px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        msg.exec()
        
        # Refresh positions after closing
        self.refresh_positions()

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
        self.fetcher_thread.current_price_fetched.connect(self._on_current_price_fetched)
        self.fetcher_thread.error_occurred.connect(self._on_fetch_error)
        self.fetcher_thread.finished.connect(self._on_fetch_finished)
        self.fetcher_thread.start()

    def _on_current_price_fetched(self, price):
        """Handle current price received from thread"""
        if self.is_closing:
            return
        
        self.current_price = price
        # Update price label
        self.price_label.setText(f"💰 Current {self.config.symbol} Price: ${price:.2f}")
        self.price_label.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 5px; color: blue;")
    
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
                self.close_selected_btn.setEnabled(False)
                print("ℹ️  No positions to display")
                return

            print(f"📋 Displaying {len(positions)} positions in GUI...")
            
            # Enable close button since we have positions
            self.close_selected_btn.setEnabled(True)
            
            # Add positions to table
            total_pnl = 0.0

            for i, pos in enumerate(positions):
                self.table.insertRow(i)

                # Checkbox for selection
                checkbox = QCheckBox()
                checkbox.setStyleSheet("margin-left: 15px;")
                self.table.setCellWidget(i, 0, checkbox)

                # Order ID
                self.table.setItem(i, 1, QTableWidgetItem(str(pos.get('id', 'N/A'))))

                # Type
                pos_type = pos.get('side', 'N/A').upper()
                self.table.setItem(i, 2, QTableWidgetItem(pos_type))

                # Amount
                amount = pos.get('contracts', pos.get('amount', 0))
                self.table.setItem(i, 3, QTableWidgetItem(f"{amount:.4f}"))

                # Entry price
                entry = pos.get('entryPrice', pos.get('price_open', 0))
                self.table.setItem(i, 4, QTableWidgetItem(f"${entry:.2f}"))

                # Current price
                current = pos.get('markPrice', pos.get('price_current', entry))
                self.table.setItem(i, 5, QTableWidgetItem(f"${current:.2f}"))

                # SL
                sl = pos.get('stopLoss', pos.get('sl', 0))
                self.table.setItem(i, 6, QTableWidgetItem(f"${sl:.2f}" if sl else 'N/A'))

                # TP
                tp = pos.get('takeProfit', pos.get('tp', 0))
                self.table.setItem(i, 7, QTableWidgetItem(f"${tp:.2f}" if tp else 'N/A'))

                # P&L
                pnl = pos.get('unrealizedPnl', pos.get('profit', 0))
                pnl_item = QTableWidgetItem(f"${pnl:+.2f}")

                # Color code P&L
                if pnl > 0:
                    pnl_item.setForeground(Qt.green)
                elif pnl < 0:
                    pnl_item.setForeground(Qt.red)

                self.table.setItem(i, 8, pnl_item)

                total_pnl += pnl
                
                print(f"   ✅ Row {i+1}: {pos_type} {amount:.4f} @ ${entry:.2f} | P&L: ${pnl:+.2f}")

            # Update summary
            summary_color = "green" if total_pnl >= 0 else "red"
            price_display = f" | Price: ${self.current_price:.2f}" if self.current_price and self.current_price > 0 else ""
            self.summary_label.setText(
                f"<b>{len(positions)} position(s){price_display} | "
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
                self.fetcher_thread.current_price_fetched.disconnect()
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
                self.fetcher_thread.current_price_fetched.disconnect()
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
