"""
Full-Auto Live Trading Bot for Binance (BTC/ETH)
Uses V3 Adaptive Strategy with TREND/RANGE detection
Adapted from XAUUSD bot for cryptocurrency trading

⚠️ DANGEROUS: Trades automatically without confirmation!
"""

import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import sys
from pathlib import Path
import csv
import os
import asyncio
import uuid

# Add parent directory to path to access shared modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.pattern_recognition_strategy import PatternRecognitionStrategy
from shared.telegram_helper import check_telegram_bot_import


class LiveBotBinanceFullAuto:
    """
    Full-automatic trading bot for Binance (BTC/ETH)

    Features:
    - Uses V3 Adaptive Strategy with TREND/RANGE detection
    - Automatic position opening/closing
    - Adapts TP levels based on market regime
    - Risk management
    - Optional Telegram notifications
    - DRY RUN mode for testing
    - Multi-symbol support (BTC, ETH)
    """

    def __init__(self, telegram_token=None, telegram_chat_id=None,
                 symbol='BTC/USDT', timeframe='1h',
                 check_interval=3600, risk_percent=2.0, max_positions=3,
                 dry_run=False, testnet=True, api_key=None, api_secret=None,
                 trailing_stop_enabled=True, trailing_stop_percent=1.5,
                 bot_id=None, use_database=True, use_3_position_mode=False,
                 total_position_size=None, min_order_size=None, trailing_stop_pct=0.5):
        """
        Initialize bot

        Args:
            telegram_token: Telegram bot token (optional)
            telegram_chat_id: Telegram chat ID (optional)
            symbol: Trading symbol (BTC/USDT, ETH/USDT)
            timeframe: Binance timeframe (1h, 4h, etc.)
            check_interval: Check interval in seconds
            risk_percent: Risk per trade (%)
            max_positions: Max simultaneous positions
            dry_run: If True, no real trades
            testnet: If True, use Binance testnet
            api_key: Binance API key
            api_secret: Binance API secret
            trailing_stop_enabled: Enable trailing stop
            trailing_stop_percent: Trailing stop activation threshold (%)
            bot_id: Unique bot identifier for database tracking
            use_database: If True, use database for position tracking
        """
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.check_interval = check_interval
        self.risk_percent = risk_percent
        self.max_positions = max_positions
        self.dry_run = dry_run
        self.testnet = testnet
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Bot identification for database
        self.bot_id = bot_id or f"crypto_bot_{symbol.replace('/', '_')}"
        self.use_database = use_database

        # Phase 2: 3-Position Mode settings
        self.use_3_position_mode = use_3_position_mode
        self.total_position_size = total_position_size
        self.min_order_size = min_order_size
        self.trailing_stop_pct = trailing_stop_pct  # Trailing stop percentage for 3-position mode

        # Trailing stop settings
        self.trailing_stop_enabled = trailing_stop_enabled
        self.trailing_stop_percent = trailing_stop_percent  # Activate trailing after X% profit
        self.trailing_distance_percent = 0.5  # Trail at 0.5% below peak

        # Initialize strategy
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')

        # TREND MODE parameters (strong trend) - в процентах от цены
        self.trend_tp1_pct = 1.5   # 1.5%
        self.trend_tp2_pct = 2.75  # 2.75%
        self.trend_tp3_pct = 4.5   # 4.5%

        # RANGE MODE parameters (sideways) - в процентах от цены
        self.range_tp1_pct = 1.0   # 1.0%
        self.range_tp2_pct = 1.75  # 1.75%
        self.range_tp3_pct = 2.5   # 2.5%

        # Current market regime
        self.current_regime = 'RANGE'

        # Position tracking
        self.trades_file = f'bot_trades_log_{symbol.replace("/", "_")}.csv'
        self.tp_hits_file = f'bot_tp_hits_log_{symbol.replace("/", "_")}.csv'
        self.positions_tracker = {}  # {order_id: position_data}
        self.position_peaks = {}  # Track highest profit for trailing stop

        # Phase 2: 3-Position Mode tracking
        self.position_groups = {}  # {group_id: {'tp1_hit': bool, 'max_price': float, 'min_price': float, 'positions': [...]}}

        self._initialize_trades_log()
        self._initialize_tp_hits_log()
        
        # Database connection (optional)
        self.db = None
        if self.use_database:
            try:
                # Import database manager
                sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_app'))
                from database.db_manager import DatabaseManager
                self.db = DatabaseManager()
                print(f"✅ Database connection established for bot {self.bot_id}")
            except Exception as e:
                print(f"⚠️  Failed to initialize database: {e}")
                print("     Falling back to CSV-only mode")
                self.use_database = False
                self.db = None

        # Telegram bot (optional)
        self.telegram_bot = None
        if telegram_token and telegram_chat_id:
            try:
                success, Bot, error_msg = check_telegram_bot_import()
                if not success:
                    print(error_msg)
                else:
                    try:
                        self.telegram_bot = Bot(token=telegram_token)
                    except Exception as bot_error:
                        print(f"⚠️  Failed to initialize Telegram bot: {bot_error}")
                        print("     Check your bot token is valid.")
            except Exception as e:
                print(f"⚠️  Unexpected error during Telegram initialization: {e}")

        # Exchange connection
        self.exchange = None
        self.exchange_connected = False

    def _initialize_trades_log(self):
        """Initialize CSV file for trade logging"""
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Order_ID', 'Open_Time', 'Close_Time', 'Type', 'Amount',
                    'Entry_Price', 'SL', 'TP', 'Close_Price', 'Profit',
                    'Profit_Pct', 'Market_Regime', 'Duration_Hours', 'Status', 'Comment'
                ])
            print(f"📝 Created trade log file: {self.trades_file}")

    def _initialize_tp_hits_log(self):
        """Initialize CSV file for TP hits logging"""
        if not os.path.exists(self.tp_hits_file):
            with open(self.tp_hits_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Order_ID', 'TP_Level', 'Type', 'Amount',
                    'Entry_Price', 'TP_Target', 'Current_Price', 'SL',
                    'Profit', 'Profit_Pct', 'Market_Regime', 'Duration_Minutes', 'Comment'
                ])
            print(f"📝 Created TP hits log file: {self.tp_hits_file}")

    def _log_position_opened(self, order_id, position_type, amount, entry_price,
                             sl, tp, regime, comment='', position_group_id=None, position_num=0):
        """Log when position is opened"""
        open_time = datetime.now()
        
        self.positions_tracker[order_id] = {
            'order_id': order_id,
            'open_time': open_time,
            'close_time': None,
            'type': position_type,
            'amount': amount,
            'entry_price': entry_price,
            'sl': sl,
            'tp': tp,
            'close_price': None,
            'profit': None,
            'profit_pct': None,
            'regime': regime,
            'duration': None,
            'status': 'OPEN',
            'comment': comment
        }
        
        # Also save to database if enabled
        if self.use_database and self.db:
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_app'))
                from models.trade_record import TradeRecord
                
                trade = TradeRecord(
                    trade_id=0,  # Will be auto-assigned by database
                    bot_id=self.bot_id,
                    symbol=self.symbol,  # Add symbol field
                    order_id=str(order_id),
                    open_time=open_time,
                    trade_type=position_type,
                    amount=amount,
                    entry_price=entry_price,
                    stop_loss=sl,
                    take_profit=tp,
                    status='OPEN',
                    market_regime=regime,
                    comment=comment,
                    position_group_id=position_group_id,
                    position_num=position_num
                )
                self.db.add_trade(trade)
                print(f"📊 Position saved to database: Order={order_id}")
            except Exception as e:
                print(f"⚠️  Failed to save position to database: {e}")
        
        print(f"📊 Logged opened position: Order={order_id}, Type={position_type}, Entry={entry_price}")

    def _log_position_closed(self, order_id, close_price, profit, status='CLOSED'):
        """Log when position is closed"""
        if order_id not in self.positions_tracker:
            print(f"⚠️  Order {order_id} not found in tracker")
            return

        pos = self.positions_tracker[order_id]
        close_time = datetime.now()
        pos['close_time'] = close_time
        pos['close_price'] = close_price
        pos['profit'] = profit
        pos['status'] = status

        # Calculate duration
        if pos['open_time']:
            duration = (pos['close_time'] - pos['open_time']).total_seconds() / 3600
            pos['duration'] = round(duration, 2)

        # Calculate profit percentage
        if pos['type'] == 'BUY':
            profit_pct = ((close_price - pos['entry_price']) / pos['entry_price']) * 100
        else:
            profit_pct = ((pos['entry_price'] - close_price) / pos['entry_price']) * 100
        pos['profit_pct'] = round(profit_pct, 2)

        # Write to CSV
        self._write_trade_to_csv(pos)
        
        # Update in database if enabled
        if self.use_database and self.db:
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_app'))
                from models.trade_record import TradeRecord
                
                trade = TradeRecord(
                    trade_id=0,  # Not used for update
                    bot_id=self.bot_id,
                    symbol=self.symbol,  # Add symbol field
                    order_id=str(order_id),
                    open_time=pos['open_time'],
                    close_time=close_time,
                    duration_hours=pos['duration'],
                    trade_type=pos['type'],
                    amount=pos['amount'],
                    entry_price=pos['entry_price'],
                    close_price=close_price,
                    stop_loss=pos['sl'],
                    take_profit=pos['tp'],
                    profit=profit,
                    profit_percent=pos['profit_pct'],
                    status=status,
                    market_regime=pos['regime'],
                    comment=pos['comment']
                )
                self.db.update_trade(trade)
                print(f"📊 Position updated in database: Order={order_id}, Status={status}")
            except Exception as e:
                print(f"⚠️  Failed to update position in database: {e}")

        # Remove from tracker
        del self.positions_tracker[order_id]

        print(f"📊 Logged closed position: Order={order_id}, Profit={profit:.2f} USDT, Profit%={profit_pct:.2f}%, Duration={pos['duration']}h")

    def _write_trade_to_csv(self, trade_data):
        """Write completed trade to CSV file"""
        with open(self.trades_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trade_data['order_id'],
                trade_data['open_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_data['open_time'] else '',
                trade_data['close_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_data['close_time'] else '',
                trade_data['type'],
                trade_data['amount'],
                trade_data['entry_price'],
                trade_data['sl'],
                trade_data['tp'],
                trade_data['close_price'],
                trade_data['profit'],
                trade_data['profit_pct'],
                trade_data['regime'],
                trade_data['duration'],
                trade_data['status'],
                trade_data['comment']
            ])

    def _log_tp_hit(self, order_id, tp_level, current_price):
        """Log when a TP level is hit"""
        if order_id not in self.positions_tracker:
            return

        pos = self.positions_tracker[order_id]

        # Calculate duration in minutes
        duration_minutes = 0
        if pos['open_time']:
            duration_minutes = (datetime.now() - pos['open_time']).total_seconds() / 60

        # Calculate profit percentage
        if pos['type'] == 'BUY':
            profit_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
        else:
            profit_pct = ((pos['entry_price'] - current_price) / pos['entry_price']) * 100

        # Estimate profit in USDT
        profit = profit_pct / 100 * pos['entry_price'] * pos['amount']

        # Write to TP hits log
        with open(self.tp_hits_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                order_id,
                tp_level,
                pos['type'],
                pos['amount'],
                pos['entry_price'],
                pos['tp'],
                current_price,
                pos['sl'],
                round(profit, 2),
                round(profit_pct, 2),
                pos['regime'],
                round(duration_minutes, 1),
                pos['comment']
            ])

        print(f"🎯 TP HIT LOGGED: Order={order_id}, Level={tp_level}, Price={current_price:.2f}, Profit%={profit_pct:.2f}%")

    def connect_exchange(self):
        """Connect to Binance"""
        try:
            # Validate API credentials
            if not self.api_key or not self.api_secret:
                error_msg = "❌ Binance API key and secret are required!"
                print(error_msg)
                print("💡 Please configure them in Settings:")
                print("   1. Go to Settings for this bot")
                print("   2. Enter your Binance API Key and API Secret")
                print("   3. Enable 'Use Testnet' for testing (recommended)")
                
                # Send to Telegram
                if self.telegram_bot:
                    try:
                        asyncio.run(self.send_telegram(f"❌ <b>Connection Error</b>\n\n{error_msg}\n\nPlease configure API credentials."))
                    except Exception as e:
                        print(f"⚠️  Failed to send Telegram notification: {e}")
                
                return False

            if len(self.api_key) < 10 or len(self.api_secret) < 10:
                error_msg = f"❌ Invalid API credentials format\n   API Key length: {len(self.api_key)} (expected 64)\n   API Secret length: {len(self.api_secret)} (expected 64)"
                print(error_msg)
                
                # Send to Telegram
                if self.telegram_bot:
                    try:
                        asyncio.run(self.send_telegram(f"❌ <b>Connection Error</b>\n\n{error_msg}"))
                    except Exception as e:
                        print(f"⚠️  Failed to send Telegram notification: {e}")
                
                return False

            print(f"🔄 Connecting to Binance {'Testnet' if self.testnet else 'Mainnet'}...")
            print(f"   Symbol: {self.symbol}")
            print(f"   API Key: {self.api_key[:8]}...{self.api_key[-4:]}")

            if self.testnet:
                # Testnet configuration
                print("⚠️  Using TESTNET - no real money will be traded")
                self.exchange = ccxt.binance({
                    'apiKey': self.api_key,
                    'secret': self.api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                        'adjustForTimeDifference': True,
                    },
                    'urls': {
                        'api': {
                            'public': 'https://testnet.binancefuture.com/fapi/v1',
                            'private': 'https://testnet.binancefuture.com/fapi/v1',
                        },
                        'test': {
                            'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                            'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
                        }
                    }
                })
            else:
                # Mainnet configuration
                print("⚠️  Using MAINNET - real money trading!")
                self.exchange = ccxt.binance({
                    'apiKey': self.api_key,
                    'secret': self.api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                        'adjustForTimeDifference': True,  # Auto-adjust for time sync
                    }
                })

            # Test connection
            print("🔄 Testing connection...")
            balance = self.exchange.fetch_balance()

            # Set position mode to One-Way (not Hedge mode) for simpler position tracking
            try:
                # Check current position mode
                position_mode = self.exchange.fapiPrivateGetPositionSideDual()
                is_hedge = position_mode.get('dualSidePosition', True)

                print(f"📊 Position mode: {'Hedge Mode' if is_hedge else 'One-Way Mode'}")

                # If in hedge mode, switch to one-way mode
                if is_hedge:
                    print("🔄 Switching to One-Way position mode...")
                    self.exchange.fapiPrivatePostPositionSideDual({'dualSidePosition': 'false'})
                    print("✅ Switched to One-Way position mode")
            except Exception as e:
                print(f"⚠️  Could not check/set position mode: {e}")

            self.exchange_connected = True

            usdt_free = balance.get('USDT', {}).get('free', 0) or 0
            print(f"✅ Connected to Binance {'Testnet' if self.testnet else 'Mainnet'}")
            print(f"   Available balance: {usdt_free:.2f} USDT")
            
            # Send success notification to Telegram
            if self.telegram_bot:
                try:
                    asyncio.run(self.send_telegram(f"✅ <b>Connected to Binance</b>\n\nSymbol: {self.symbol}\nBalance: {usdt_free:.2f} USDT\nMode: {'Testnet' if self.testnet else 'Mainnet'}"))
                except Exception as e:
                    print(f"⚠️  Failed to send Telegram notification: {e}")
            
            return True

        except ccxt.AuthenticationError as e:
            error_msg = f"❌ Authentication Failed: {e}"
            print(error_msg)
            print("\n💡 Troubleshooting:")
            print("   1. Check your API Key and Secret are correct")
            print("   2. Ensure API has 'Enable Futures' permission")
            print("   3. If using Testnet, get keys from: https://testnet.binancefuture.com/")
            print("   4. If using Mainnet, get keys from: https://www.binance.com/")
            print("\n⚠️  Common issues:")
            print("   - Wrong API keys (copy-paste error)")
            print("   - Using Mainnet keys on Testnet (or vice versa)")
            print("   - API doesn't have Futures trading permission")
            
            # Send to Telegram
            if self.telegram_bot:
                try:
                    asyncio.run(self.send_telegram(f"❌ <b>Authentication Failed</b>\n\n{str(e)}\n\nPlease check your API credentials."))
                except Exception as e:
                    print(f"⚠️  Failed to send Telegram notification: {e}")
            
            return False

        except ccxt.ExchangeError as e:
            error_msg = str(e)
            print(f"❌ Binance Error: {e}")

            if '-1022' in error_msg or 'Signature' in error_msg:
                print("\n💡 Signature Error - Possible causes:")
                print("   1. API Secret is incorrect")
                print("   2. System time is not synchronized")
                print("   3. Wrong Testnet/Mainnet configuration")
                print("\n🔧 Try these fixes:")
                print("   1. Double-check your API Secret (no extra spaces)")
                print("   2. Sync your system time: Settings → Time & Language → Sync now")
                print("   3. Enable 'Use Testnet' in bot settings for testing")
            elif '-1021' in error_msg or 'Timestamp' in error_msg:
                print("\n💡 Time Synchronization Error:")
                print("   Your system time is not synchronized with Binance")
                print("\n🔧 Fix:")
                print("   Windows: Settings → Time & Language → Sync now")
                print("   Or enable automatic time synchronization")

            # Send to Telegram
            if self.telegram_bot:
                try:
                    asyncio.run(self.send_telegram(f"❌ <b>Binance Exchange Error</b>\n\n{error_msg}\n\nPlease check the logs for details."))
                except Exception as e:
                    print(f"⚠️  Failed to send Telegram notification: {e}")

            return False

        except Exception as e:
            error_msg = f"❌ Connection failed: {e}\n   Error type: {type(e).__name__}"
            print(error_msg)
            
            # Send to Telegram
            if self.telegram_bot:
                try:
                    asyncio.run(self.send_telegram(f"❌ <b>Connection Failed</b>\n\n{str(e)}\n\nType: {type(e).__name__}"))
                except Exception as e:
                    print(f"⚠️  Failed to send Telegram notification: {e}")
            
            return False

    def disconnect_exchange(self):
        """Disconnect from Binance"""
        if self.exchange_connected:
            self.exchange.close()
            self.exchange_connected = False

    def update_trailing_stops(self):
        """
        Update trailing stops for all open positions

        Logic:
        1. Check each open position's current profit
        2. If profit > threshold (e.g. 1.5%), activate trailing
        3. Track peak profit for this position
        4. Move SL up to lock in profits (peak - trailing_distance%)
        """
        if not self.trailing_stop_enabled or not self.exchange_connected:
            return

        try:
            # Get open positions
            positions = self.exchange.fetch_positions([self.symbol])

            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts <= 0:
                    continue

                # Get position details
                order_id = pos.get('id', '')
                entry_price = float(pos.get('entryPrice', 0))
                current_price = float(pos.get('markPrice', 0))
                side = pos.get('side', '').lower()  # 'long' or 'short'
                unrealized_pnl_pct = float(pos.get('percentage', 0))

                # Skip if no valid data
                if not entry_price or not current_price:
                    continue

                # Calculate profit percentage
                if side == 'long':
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                else:  # short
                    profit_pct = ((entry_price - current_price) / entry_price) * 100

                # Check if trailing should be activated
                if profit_pct < self.trailing_stop_percent:
                    # Not enough profit yet to activate trailing
                    continue

                # Track peak profit
                if order_id not in self.position_peaks:
                    self.position_peaks[order_id] = {
                        'peak_price': current_price,
                        'peak_profit_pct': profit_pct,
                        'entry_price': entry_price,
                        'side': side,
                        'trailing_active': False
                    }
                    print(f"🎯 Trailing stop ACTIVATED for {order_id}: Profit={profit_pct:.2f}%")

                peak_data = self.position_peaks[order_id]

                # Update peak if current profit is higher
                if profit_pct > peak_data['peak_profit_pct']:
                    peak_data['peak_price'] = current_price
                    peak_data['peak_profit_pct'] = profit_pct
                    peak_data['trailing_active'] = True

                    # Calculate new trailing stop level
                    if side == 'long':
                        new_sl = current_price * (1 - self.trailing_distance_percent / 100)
                    else:  # short
                        new_sl = current_price * (1 + self.trailing_distance_percent / 100)

                    # Update stop loss on exchange
                    if not self.dry_run:
                        try:
                            self.exchange.edit_order(
                                order_id,
                                self.symbol,
                                params={'stopLoss': new_sl}
                            )
                            print(f"📈 Trailing SL updated: {order_id}")
                            print(f"   Peak: ${peak_data['peak_price']:.2f} (+{peak_data['peak_profit_pct']:.2f}%)")
                            print(f"   New SL: ${new_sl:.2f} (trailing {self.trailing_distance_percent}%)")
                        except Exception as e:
                            print(f"⚠️  Failed to update SL for {order_id}: {e}")
                    else:
                        print(f"🧪 DRY RUN: Would update SL to ${new_sl:.2f} for {order_id}")

        except Exception as e:
            print(f"⚠️  Error updating trailing stops: {e}")
    
    def _sync_positions_with_exchange(self):
        """Sync database positions with actual exchange positions
        
        Detects positions that were manually closed on exchange but still show as OPEN in database
        """
        if not self.use_database or not self.db or self.dry_run or not self.exchange_connected:
            return
        
        try:
            # Get all OPEN positions from database
            db_trades = self.db.get_open_trades(self.bot_id)
            if not db_trades:
                return
            
            # Get current open positions from exchange
            positions = self.exchange.fetch_positions([self.symbol])
            exchange_order_ids = set()
            for pos in positions:
                if pos['contracts'] > 0:  # Position is open
                    # Extract order ID from position info
                    if 'info' in pos and 'positionId' in pos['info']:
                        exchange_order_ids.add(str(pos['info']['positionId']))
                    elif 'id' in pos:
                        exchange_order_ids.add(str(pos['id']))
            
            # Check each database position
            for trade in db_trades:
                order_id = trade.order_id
                
                # If position is in database but not on exchange, it was closed manually
                if order_id not in exchange_order_ids:
                    print(f"📊 Position {order_id} manually closed on exchange - syncing database...")
                    
                    # Get current price for profit calculation
                    ticker = self.exchange.fetch_ticker(self.symbol)
                    close_price = ticker['last']
                    
                    # Calculate profit
                    if trade.trade_type == 'BUY':
                        profit = (close_price - trade.entry_price) * trade.amount
                    else:
                        profit = (trade.entry_price - close_price) * trade.amount
                    
                    # Log the close
                    self._log_position_closed(
                        order_id=order_id,
                        close_price=close_price,
                        profit=profit,
                        status='CLOSED'
                    )
                    
                    print(f"✅ Database synced for position {order_id}")
        except Exception as e:
            print(f"⚠️  Error syncing positions with exchange: {e}")
    
    def _update_3position_trailing(self, positions_to_check, current_price):
        """
        Update trailing stops for 3-position groups (Phase 2)

        Logic:
        - Track max_price/min_price for each group
        - When any position reaches TP1, activate trailing for Pos 2 & 3
        - Trailing formula: 50% retracement from max profit
        """
        if not self.use_3_position_mode:
            return

        # Group positions by position_group_id
        groups = {}
        for order_id, pos_data in positions_to_check.items():
            group_id = pos_data.get('position_group_id')
            if not group_id:
                continue  # Not a 3-position group

            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append((order_id, pos_data))

        # Process each group
        for group_id, group_positions in groups.items():
            # Initialize group tracking if needed
            if group_id not in self.position_groups:
                # Find entry price from any position in group
                entry_price = group_positions[0][1]['entry_price']
                self.position_groups[group_id] = {
                    'tp1_hit': False,
                    'max_price': entry_price,
                    'min_price': entry_price,
                    'positions': [p[0] for p in group_positions]
                }

            group_info = self.position_groups[group_id]

            # Update max/min price
            if group_positions[0][1]['type'] == 'BUY':
                if current_price > group_info['max_price']:
                    group_info['max_price'] = current_price
            else:  # SELL
                if current_price < group_info['min_price']:
                    group_info['min_price'] = current_price

            # Check if any position reached TP1
            for order_id, pos_data in group_positions:
                if pos_data.get('position_num') == 1:
                    tp1 = pos_data['tp']
                    if pos_data['type'] == 'BUY':
                        if current_price >= tp1:
                            group_info['tp1_hit'] = True
                            print(f"🎯 Group {group_id[:8]} TP1 reached! Activating trailing for Pos 2 & 3")
                    else:  # SELL
                        if current_price <= tp1:
                            group_info['tp1_hit'] = True
                            print(f"🎯 Group {group_id[:8]} TP1 reached! Activating trailing for Pos 2 & 3")

            # Update trailing stops for Pos 2 & 3 if TP1 hit
            if group_info['tp1_hit']:
                for order_id, pos_data in group_positions:
                    pos_num = pos_data.get('position_num', 0)
                    if pos_num in [2, 3]:  # Only Pos 2 and 3 trail
                        entry_price = pos_data['entry_price']

                        if pos_data['type'] == 'BUY':
                            # Trailing stop: configurable % retracement from max price
                            new_sl = group_info['max_price'] - (group_info['max_price'] - entry_price) * self.trailing_stop_pct

                            # Only update if new SL is better (higher) than current
                            if new_sl > pos_data['sl']:
                                print(f"   📊 Pos {pos_num} trailing SL updated: ${pos_data['sl']:.2f} → ${new_sl:.2f}")
                                pos_data['sl'] = new_sl
                                # Update in tracker
                                if order_id in self.positions_tracker:
                                    self.positions_tracker[order_id]['sl'] = new_sl
                        else:  # SELL
                            # Trailing stop: configurable % retracement from min price
                            new_sl = group_info['min_price'] + (entry_price - group_info['min_price']) * self.trailing_stop_pct

                            # Only update if new SL is better (lower) than current
                            if new_sl < pos_data['sl']:
                                print(f"   📊 Pos {pos_num} trailing SL updated: ${pos_data['sl']:.2f} → ${new_sl:.2f}")
                                pos_data['sl'] = new_sl
                                # Update in tracker
                                if order_id in self.positions_tracker:
                                    self.positions_tracker[order_id]['sl'] = new_sl

    def _check_tp_sl_realtime(self):
        """Monitor open positions in real-time and check if TP/SL levels are hit
        
        Checks:
        1. Loads open positions from database (if enabled) or tracker
        2. Current bar's high/low to see if TP/SL was touched during the bar
        3. Current price to determine exit price
        4. Closes position if TP or SL is hit
        """
        if not self.exchange_connected:
            return
        
        try:
            # Get positions to monitor
            positions_to_check = {}
            
            # If database is enabled, load positions from database
            if self.use_database and self.db:
                try:
                    db_trades = self.db.get_open_trades(self.bot_id)
                    for trade in db_trades:
                        positions_to_check[trade.order_id] = {
                            'tp': trade.take_profit,
                            'sl': trade.stop_loss,
                            'type': trade.trade_type,
                            'entry_price': trade.entry_price,
                            'amount': trade.amount,
                            'status': trade.status,
                            'open_time': trade.open_time,
                            'regime': trade.market_regime,
                            'comment': trade.comment or '',
                            'position_group_id': trade.position_group_id,
                            'position_num': trade.position_num
                        }
                        # Also sync to in-memory tracker if not already there
                        if trade.order_id not in self.positions_tracker:
                            self.positions_tracker[trade.order_id] = positions_to_check[trade.order_id].copy()
                            self.positions_tracker[trade.order_id]['order_id'] = trade.order_id
                            self.positions_tracker[trade.order_id]['close_time'] = None
                            self.positions_tracker[trade.order_id]['close_price'] = None
                            self.positions_tracker[trade.order_id]['profit'] = None
                            self.positions_tracker[trade.order_id]['profit_pct'] = None
                            self.positions_tracker[trade.order_id]['duration'] = None
                except Exception as e:
                    print(f"⚠️  Error loading positions from database: {e}")
                    # Fall back to in-memory tracker
                    positions_to_check = self.positions_tracker.copy()
            else:
                # Use in-memory tracker
                positions_to_check = self.positions_tracker.copy()
            
            if not positions_to_check:
                return
            
            # Get current open positions from exchange (skip if dry_run)
            open_positions = []
            exchange_position_ids = set()
            
            if not self.dry_run:
                open_positions = self.get_open_positions()
                exchange_position_ids = set(str(pos.get('id', '')) for pos in open_positions) if open_positions else set()
            else:
                # In dry_run mode, all database positions are "valid"
                exchange_position_ids = set(positions_to_check.keys())
            
            # Get current bar data to check high/low
            try:
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=1)
                if ohlcv and len(ohlcv) > 0:
                    current_bar = ohlcv[0]
                    bar_high = current_bar[2]  # high price
                    bar_low = current_bar[3]   # low price
                else:
                    # Fallback if can't get bar data
                    bar_high = None
                    bar_low = None
            except Exception as e:
                print(f"⚠️  Could not fetch current bar data: {e}")
                bar_high = None
                bar_low = None
            
            # Check each tracked position
            for order_id, tracked_pos in list(positions_to_check.items()):
                # Skip if already processing or closed
                if tracked_pos.get('status') not in ['OPEN']:
                    continue
                
                # Check if position is still on exchange (skip check if dry_run)
                if not self.dry_run and order_id not in exchange_position_ids:
                    # Position closed on exchange but still in DB as OPEN
                    # This means exchange TP/SL triggered it or manual close
                    print(f"📊 Position {order_id} closed on exchange but DB shows OPEN - syncing...")
                    # We can't determine exact close price, so mark as CLOSED
                    if order_id in self.positions_tracker:
                        # Try to close it properly
                        self._log_position_closed(
                            order_id=order_id,
                            close_price=tracked_pos['entry_price'],  # Unknown close price
                            profit=0.0,  # Unknown profit
                            status='CLOSED'
                        )
                    continue
                
                # Get current price
                current_price = None
                if not self.dry_run:
                    # Find the position data from exchange
                    position = next((p for p in open_positions if str(p.get('id', '')) == order_id), None)
                    if not position:
                        continue
                    
                    current_price = float(position.get('markPrice', 0))
                    if not current_price:
                        continue
                else:
                    # In dry_run mode, get current price from ticker
                    try:
                        ticker = self.exchange.fetch_ticker(self.symbol)
                        current_price = ticker.get('last', 0)
                        if not current_price:
                            print(f"⚠️  Could not get current price for dry_run position {order_id}")
                            continue
                    except Exception as e:
                        print(f"⚠️  Error getting current price for dry_run: {e}")
                        continue
                
                # Phase 2: Update trailing stops for 3-position groups
                self._update_3position_trailing({order_id: tracked_pos}, current_price)

                # Read TP/SL from tracked position (database columns or in-memory)
                # Note: SL may have been updated by trailing logic above
                tp_target = tracked_pos['tp']
                sl_target = tracked_pos['sl']
                position_type = tracked_pos['type']

                # Check if TP or SL is hit based on bar high/low OR current price
                tp_hit = False
                sl_hit = False
                
                if position_type == 'BUY':
                    # For BUY: TP is above entry, SL is below entry
                    # Check if bar high reached TP OR current price is already at/past TP
                    if (bar_high and bar_high >= tp_target) or (current_price >= tp_target):
                        tp_hit = True
                    # Check if bar low reached SL OR current price is already at/past SL
                    if (bar_low and bar_low <= sl_target) or (current_price <= sl_target):
                        sl_hit = True
                else:  # SELL
                    # For SELL: TP is below entry, SL is above entry
                    # Check if bar low reached TP OR current price is already at/past TP
                    if (bar_low and bar_low <= tp_target) or (current_price <= tp_target):
                        tp_hit = True
                    # Check if bar high reached SL OR current price is already at/past SL
                    if (bar_high and bar_high >= sl_target) or (current_price >= sl_target):
                        sl_hit = True
                
                # If TP or SL is hit
                if tp_hit or sl_hit:
                    hit_type = 'TP' if tp_hit else 'SL'
                    target_price = tp_target if tp_hit else sl_target
                    
                    # Update status in both tracker and database immediately
                    processing_status = f'{hit_type}_PROCESSING'
                    tracked_pos['status'] = processing_status
                    if order_id in self.positions_tracker:
                        self.positions_tracker[order_id]['status'] = processing_status
                    
                    # Update status in database immediately to prevent re-processing
                    if self.use_database and self.db:
                        try:
                            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_app'))
                            from models.trade_record import TradeRecord
                            temp_trade = TradeRecord(
                                trade_id=0,
                                bot_id=self.bot_id,
                                symbol=self.symbol,  # Add symbol field
                                order_id=str(order_id),
                                open_time=tracked_pos['open_time'],
                                trade_type=tracked_pos['type'],
                                amount=tracked_pos['amount'],
                                entry_price=tracked_pos['entry_price'],
                                stop_loss=tracked_pos['sl'],
                                take_profit=tracked_pos['tp'],
                                status=processing_status,
                                market_regime=tracked_pos['regime'],
                                comment=tracked_pos['comment']
                            )
                            self.db.update_trade(temp_trade)
                            print(f"📊 Updated position {order_id} status to {processing_status} in database")
                        except Exception as e:
                            print(f"⚠️  Failed to update status in database: {e}")
                    
                    # Log the hit
                    self._log_tp_hit(order_id, hit_type, current_price)
                    
                    # Close the position at current price
                    close_successful = False
                    if not self.dry_run:
                        try:
                            # Close position by placing opposite order
                            side = 'sell' if position_type == 'BUY' else 'buy'
                            amount = tracked_pos['amount']
                            
                            print(f"🔄 Closing position {order_id} at current price ${current_price:.2f} ({hit_type} hit)")
                            close_order = self.exchange.create_order(
                                symbol=self.symbol,
                                type='market',
                                side=side,
                                amount=amount
                            )
                            print(f"✅ Position closed: Order ID {close_order['id']}")
                            close_successful = True
                        except Exception as e:
                            print(f"❌ Failed to close position {order_id}: {e}")
                            # Revert status back to OPEN if close failed
                            tracked_pos['status'] = 'OPEN'
                            if order_id in self.positions_tracker:
                                self.positions_tracker[order_id]['status'] = 'OPEN'
                            # Revert in database too
                            if self.use_database and self.db:
                                try:
                                    temp_trade.status = 'OPEN'
                                    self.db.update_trade(temp_trade)
                                except:
                                    pass
                    else:
                        print(f"🧪 DRY RUN: Would close position {order_id} at ${current_price:.2f} ({hit_type} hit)")
                        close_successful = True  # Simulate successful close in dry run
                    
                    # If close was successful, properly log the position as closed
                    if close_successful:
                        # Calculate profit
                        if tracked_pos['type'] == 'BUY':
                            profit_pct = ((current_price - tracked_pos['entry_price']) / tracked_pos['entry_price']) * 100
                        else:
                            profit_pct = ((tracked_pos['entry_price'] - current_price) / tracked_pos['entry_price']) * 100
                        
                        profit_usdt = profit_pct / 100 * tracked_pos['entry_price'] * tracked_pos['amount']
                        
                        # Log position as closed with proper status
                        self._log_position_closed(
                            order_id=order_id,
                            close_price=current_price,
                            profit=profit_usdt,
                            status=hit_type  # Status will be 'TP' or 'SL'
                        )
                    
                    # Send Telegram notification
                    if self.telegram_bot and close_successful:
                        emoji = "🎯" if tp_hit else "🛑"
                        message = f"{emoji} <b>{hit_type} HIT & CLOSED!</b>\n\n"
                        message += f"Order ID: {order_id}\n"
                        message += f"Symbol: {self.symbol}\n"
                        message += f"Type: {tracked_pos['type']}\n"
                        message += f"Entry: ${tracked_pos['entry_price']:.2f}\n"
                        message += f"{hit_type} Target: ${target_price:.2f}\n"
                        message += f"Close Price: ${current_price:.2f}\n"
                        message += f"Amount: {tracked_pos['amount']}\n"
                        
                        # Calculate profit percentage
                        if tracked_pos['type'] == 'BUY':
                            profit_pct = ((current_price - tracked_pos['entry_price']) / tracked_pos['entry_price']) * 100
                        else:
                            profit_pct = ((tracked_pos['entry_price'] - current_price) / tracked_pos['entry_price']) * 100
                        
                        sign = "+" if profit_pct >= 0 else ""
                        message += f"Profit: {sign}{profit_pct:.2f}%\n"
                        message += f"Status: CLOSED"
                        
                        try:
                            asyncio.run(self.send_telegram(message))
                        except Exception as e:
                            print(f"⚠️  Failed to send Telegram notification: {e}")
        
        except Exception as e:
            print(f"⚠️  Error checking TP/SL levels: {e}")

    def get_market_data(self, bars=500):
        """Get historical data from Binance"""
        if not self.exchange_connected:
            return None

        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=bars)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('datetime')
            df = df[['open', 'high', 'low', 'close', 'volume']].copy()

            # Add market hours (UTC based)
            df['hour'] = df.index.hour
            df['is_active'] = df['hour'].isin(range(0, 24))  # Crypto trades 24/7
            df['is_best_hours'] = df['hour'].isin([8, 9, 10, 13, 14, 15, 16, 17])  # Active trading hours

            return df
        except Exception as e:
            print(f"❌ Failed to get market data: {e}")
            return None

    def detect_market_regime(self, df, lookback=100):
        """
        Detect market regime: TREND or RANGE

        Uses same logic as XAUUSD bot
        """
        if len(df) < lookback:
            return 'RANGE'

        recent_data = df.iloc[-lookback:]

        # 1. EMA CROSSOVER
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()

        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]

        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
        ema_trend = ema_diff_pct > 0.5  # Adjusted for crypto volatility

        # 2. ATR (volatility)
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()

        high_volatility = atr > avg_atr * 1.05

        # 3. Directional movement
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()

        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35

        # 4. Consecutive movements
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        total_moves = up_moves + down_moves

        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.15

        # 5. Structural trend
        highs = recent_data['high'].values[-20:]
        lows = recent_data['low'].values[-20:]

        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])

        structural_trend = (higher_highs > 12) or (lower_lows > 12)

        # Count trend signals
        trend_signals = sum([
            ema_trend,
            high_volatility,
            strong_direction,
            directional_bias,
            structural_trend
        ])

        is_trend = trend_signals >= 3

        return 'TREND' if is_trend else 'RANGE'

    def analyze_market(self):
        """Analyze market and get signals with adaptive TP levels"""
        try:
            print(f"   📥 Fetching market data...")
            df = self.get_market_data()
            if df is None:
                print(f"   ❌ Failed to get market data")
                return None

            last_close = df['close'].iloc[-1]
            last_time = df.index[-1]
            print(f"   📊 Got {len(df)} candles, last close: ${last_close:.2f} at {last_time.strftime('%Y-%m-%d %H:%M')}")

            # Detect market regime
            print(f"   🔍 Detecting market regime...")
            self.current_regime = self.detect_market_regime(df)
            print(f"   📊 Market Regime: {self.current_regime}")

            # Run strategy
            print(f"   🧠 Running V3 Adaptive Strategy...")
            result = self.strategy.run_strategy(df)

            signals = result[result['signal'] != 0]

            if len(signals) == 0:
                print(f"   ℹ️  No signals detected")
                return None

            # Check only the most recent signal
            last_signal = signals.iloc[-1]
            last_signal_time = signals.index[-1]
            current_time = df.index[-1]

            time_diff_hours = (current_time - last_signal_time).total_seconds() / 3600

            if time_diff_hours > 1.5:
                print(f"   ⏰ Last signal is {time_diff_hours:.1f}h old (not from latest candle, skipping)")
                return None

            print(f"   ✅ Signal from latest candle (age: {time_diff_hours:.1f}h)")

            # Adjust TP based on market regime (in %)
            if self.current_regime == 'TREND':
                tp1_pct = self.trend_tp1_pct
                tp2_pct = self.trend_tp2_pct
                tp3_pct = self.trend_tp3_pct
            else:
                tp1_pct = self.range_tp1_pct
                tp2_pct = self.range_tp2_pct
                tp3_pct = self.range_tp3_pct

            # Calculate TP levels in price
            entry = last_signal['entry_price']
            sl = last_signal['stop_loss']

            if last_signal['signal'] == 1:  # LONG
                tp1 = entry * (1 + tp1_pct / 100)
                tp2 = entry * (1 + tp2_pct / 100)
                tp3 = entry * (1 + tp3_pct / 100)
            else:  # SHORT
                tp1 = entry * (1 - tp1_pct / 100)
                tp2 = entry * (1 - tp2_pct / 100)
                tp3 = entry * (1 - tp3_pct / 100)

            direction = "LONG" if last_signal['signal'] == 1 else "SHORT"
            print(f"\n   ✅ FRESH SIGNAL FROM LATEST CANDLE!")
            print(f"      Direction: {direction}")
            print(f"      Market Regime: {self.current_regime}")
            print(f"      Entry: ${entry:.2f}")
            print(f"      SL: ${sl:.2f}")
            print(f"      TP1: ${tp1:.2f} ({tp1_pct}%)")
            print(f"      TP2: ${tp2:.2f} ({tp2_pct}%)")
            print(f"      TP3: ${tp3:.2f} ({tp3_pct}%)")

            return {
                'direction': last_signal['signal'],
                'entry': entry,
                'sl': sl,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'tp1_pct': tp1_pct,
                'tp2_pct': tp2_pct,
                'tp3_pct': tp3_pct,
                'time': last_signal_time,
                'regime': self.current_regime
            }

        except Exception as e:
            print(f"   ❌ Strategy analysis error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_position_size(self, entry, sl):
        """Calculate position size based on risk"""
        if not self.exchange_connected:
            return 0.0

        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance['USDT']['free']

            risk_amount = usdt_balance * (self.risk_percent / 100.0)

            # Risk per unit
            risk_per_unit = abs(entry - sl)
            risk_pct = risk_per_unit / entry

            # Position size in base currency
            position_size = risk_amount / risk_per_unit

            # Get minimum trade size
            markets = self.exchange.load_markets()
            
            # Try to find the correct symbol format
            # Binance futures uses format like ETH/USDT:USDT
            market_symbol = self.symbol
            if self.symbol not in markets:
                # Try futures format: SYMBOL:USDT
                futures_symbol = f"{self.symbol}:USDT"
                if futures_symbol in markets:
                    market_symbol = futures_symbol
                else:
                    print(f"⚠️ Symbol {self.symbol} not found in exchange markets")
                    print(f"   Available symbols: {', '.join(list(markets.keys())[:5])}...")
                    # Use default minimum for this asset type
                    min_amount = 0.001 if 'BTC' in self.symbol else 0.01
                    market_symbol = None
            
            if market_symbol and market_symbol in markets:
                market = markets[market_symbol]
                min_amount = market['limits']['amount']['min']
            else:
                # Fallback to defaults
                min_amount = 0.001 if 'BTC' in self.symbol else 0.01

            # Round to market precision
            position_size = max(min_amount, position_size)

            # Round to appropriate decimals
            if 'BTC' in self.symbol:
                position_size = round(position_size, 3)
            else:
                position_size = round(position_size, 2)

            return position_size

        except KeyError as e:
            print(f"❌ KeyError calculating position size: {e}")
            print(f"   Symbol: {self.symbol}")
            print(f"   Returning minimum fallback position size")
            return 0.001  # Minimum fallback
        except Exception as e:
            print(f"❌ Error calculating position size: {e}")
            print(f"   Error type: {type(e).__name__}")
            return 0.001  # Minimum fallback

    def get_open_positions(self):
        """Get open positions for symbol"""
        if not self.exchange_connected:
            return []

        try:
            positions = self.exchange.fetch_positions([self.symbol])
            # Filter only positions with contracts > 0
            open_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]
            return open_positions
        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            return []

    def open_position(self, signal):
        """Open position(s) with TP/SL - supports single and 3-position modes"""
        if self.use_3_position_mode:
            return self._open_3_positions(signal)
        else:
            return self._open_single_position(signal)

    def _open_single_position(self, signal):
        """Open single position with TP/SL (original logic)"""
        direction_str = "BUY" if signal['direction'] == 1 else "SELL"

        print(f"\n{'='*60}")
        print(f"📈 OPENING {direction_str} POSITION")
        print(f"{'='*60}")

        # Calculate position size
        position_size = self.calculate_position_size(signal['entry'], signal['sl'])

        print(f"   Position size: {position_size}")

        if self.dry_run:
            print(f"\n🧪 DRY RUN: Would open {direction_str} position:")
            print(f"   Symbol: {self.symbol}")
            print(f"   Amount: {position_size}")
            print(f"   Entry: ${signal['entry']:.2f}")
            print(f"   SL: ${signal['sl']:.2f}")
            print(f"   TP1: ${signal['tp1']:.2f} ({signal['tp1_pct']}%)")
            print(f"   TP2: ${signal['tp2']:.2f} ({signal['tp2_pct']}%)")
            print(f"   TP3: ${signal['tp3']:.2f} ({signal['tp3_pct']}%)")
            return True

        try:
            # Place market order
            side = 'buy' if signal['direction'] == 1 else 'sell'

            print(f"   🔄 Placing market order...")
            order = self.exchange.create_order(
                symbol=self.symbol,
                type='market',
                side=side,
                amount=position_size,
                params={
                    'stopLoss': {'triggerPrice': signal['sl']},
                    'takeProfit': {'triggerPrice': signal['tp2']}  # Using TP2 as main target
                }
            )

            print(f"   ✅ Order placed!")
            print(f"      Order ID: {order['id']}")
            print(f"      Status: {order.get('status', 'unknown')}")
            print(f"      Side: {order.get('side', 'unknown')}")
            print(f"      Amount: {order.get('amount', position_size)}")
            print(f"      Filled: {order.get('filled', 0)}")
            print(f"      Entry: ${order.get('average', signal['entry']):.2f}")

            # Verify position was created
            print(f"\n   🔍 Verifying position...")
            import time
            time.sleep(1)  # Wait for position to register
            positions = self.get_open_positions()
            print(f"   📊 Open positions after order: {len(positions)}")
            if positions:
                for pos in positions:
                    print(f"      Position: {pos.get('side')} {pos.get('contracts')} @ ${pos.get('entryPrice', 0):.2f}")

            # Log position
            position_type = 'BUY' if signal['direction'] == 1 else 'SELL'
            regime = signal.get('regime', 'UNKNOWN')
            regime_code = "T" if regime == 'TREND' else "R"

            self._log_position_opened(
                order_id=order['id'],
                position_type=position_type,
                amount=position_size,
                entry_price=order.get('average', signal['entry']),
                sl=signal['sl'],
                tp=signal['tp2'],
                regime=regime,
                comment=f"V3_{regime_code}"
            )

            # Send Telegram notification
            if self.telegram_bot:
                message = f"🤖 <b>Position Opened</b>\n\n"
                message += f"Symbol: {self.symbol}\n"
                message += f"Direction: {direction_str}\n"
                message += f"Regime: {regime}\n"
                message += f"Amount: {position_size}\n"
                message += f"Entry: ${order.get('average', signal['entry']):.2f}\n"
                message += f"SL: ${signal['sl']:.2f}\n"
                message += f"TP: ${signal['tp2']:.2f}\n"
                message += f"Risk: {self.risk_percent}%"
                asyncio.run(self.send_telegram(message))

            return True

        except Exception as e:
            print(f"❌ Failed to open position: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _open_3_positions(self, signal):
        """
        Open 3 independent positions for same signal (Phase 2)

        Position allocation:
        - Pos 1: 33% → TP1 only, no trailing
        - Pos 2: 33% → TP2, trails after TP1
        - Pos 3: 34% → TP3, trails after TP1
        """
        direction_str = "BUY" if signal['direction'] == 1 else "SELL"
        group_id = str(uuid.uuid4())

        print(f"\n{'='*60}")
        print(f"📈 OPENING 3-POSITION {direction_str} GROUP")
        print(f"{'='*60}")
        print(f"   Group ID: {group_id}")

        # Calculate total position size
        if self.total_position_size:
            total_size = self.total_position_size
            print(f"   Using fixed position size: ${total_size}")
        else:
            # Use risk-based sizing
            total_size = self.calculate_position_size(signal['entry'], signal['sl'])
            print(f"   Using risk-based size: {total_size}")

        # Validate minimum order size and calculate split
        min_size = self.min_order_size or 0.001
        pos_sizes = [
            total_size * 0.33,  # Pos 1
            total_size * 0.33,  # Pos 2
            total_size * 0.34   # Pos 3 (slightly larger for rounding)
        ]

        # Auto-adjust if below minimum
        adjusted = False
        for i in range(len(pos_sizes)):
            if pos_sizes[i] < min_size:
                print(f"   ⚠️  Position {i+1} size {pos_sizes[i]:.6f} < minimum {min_size}, adjusting...")
                pos_sizes[i] = min_size
                adjusted = True

        if adjusted:
            total_size = sum(pos_sizes)
            print(f"   Adjusted total size: {total_size:.6f}")

        # Position configuration
        positions_data = [
            {'num': 1, 'size': pos_sizes[0], 'tp': signal['tp1'], 'tp_pct': signal['tp1_pct'], 'trailing': False},
            {'num': 2, 'size': pos_sizes[1], 'tp': signal['tp2'], 'tp_pct': signal['tp2_pct'], 'trailing': True},
            {'num': 3, 'size': pos_sizes[2], 'tp': signal['tp3'], 'tp_pct': signal['tp3_pct'], 'trailing': True}
        ]

        if self.dry_run:
            print(f"\n🧪 DRY RUN: Would open 3 {direction_str} positions:")
            print(f"   Group ID: {group_id}")
            print(f"   Entry: ${signal['entry']:.2f}")
            print(f"   SL: ${signal['sl']:.2f}")
            for pos_data in positions_data:
                print(f"\n   Position {pos_data['num']}:")
                print(f"      Size: {pos_data['size']:.6f}")
                print(f"      TP: ${pos_data['tp']:.2f} ({pos_data['tp_pct']}%)")
                print(f"      Trailing: {'YES (after TP1)' if pos_data['trailing'] else 'NO'}")
            return True

        try:
            side = 'buy' if signal['direction'] == 1 else 'sell'
            orders_placed = []

            for pos_data in positions_data:
                print(f"\n   🔄 Opening Position {pos_data['num']}/{len(positions_data)}...")

                # Place market order
                order = self.exchange.create_order(
                    symbol=self.symbol,
                    type='market',
                    side=side,
                    amount=pos_data['size'],
                    params={
                        'stopLoss': {'triggerPrice': signal['sl']},
                        'takeProfit': {'triggerPrice': pos_data['tp']}
                    }
                )

                print(f"      ✅ Position {pos_data['num']} opened!")
                print(f"         Order ID: {order['id']}")
                print(f"         Size: {pos_data['size']:.6f}")
                print(f"         Entry: ${order.get('average', signal['entry']):.2f}")
                print(f"         TP: ${pos_data['tp']:.2f}")
                print(f"         Trailing: {'YES' if pos_data['trailing'] else 'NO'}")

                # Log position
                position_type = 'BUY' if signal['direction'] == 1 else 'SELL'
                regime = signal.get('regime', 'UNKNOWN')
                regime_code = "T" if regime == 'TREND' else "R"

                self._log_position_opened(
                    order_id=order['id'],
                    position_type=position_type,
                    amount=pos_data['size'],
                    entry_price=order.get('average', signal['entry']),
                    sl=signal['sl'],
                    tp=pos_data['tp'],
                    regime=regime,
                    comment=f"V3_{regime_code}_P{pos_data['num']}/3",
                    position_group_id=group_id,
                    position_num=pos_data['num']
                )

                orders_placed.append(order)
                time.sleep(0.5)  # Small delay between orders

            # Verify positions were created
            print(f"\n   🔍 Verifying positions...")
            time.sleep(1)  # Wait for positions to register
            positions = self.get_open_positions()
            print(f"   📊 Open positions after orders: {len(positions)}")
            if positions:
                for pos in positions:
                    print(f"      Position: {pos.get('side')} {pos.get('contracts')} @ ${pos.get('entryPrice', 0):.2f}")

            # Send Telegram notification
            if self.telegram_bot:
                message = f"🤖 <b>3-Position Group Opened</b>\n\n"
                message += f"Group ID: {group_id[:8]}...\n"
                message += f"Symbol: {self.symbol}\n"
                message += f"Direction: {direction_str}\n"
                message += f"Regime: {signal.get('regime', 'UNKNOWN')}\n"
                message += f"Total Size: {total_size:.6f}\n"
                message += f"Entry: ${signal['entry']:.2f}\n"
                message += f"SL: ${signal['sl']:.2f}\n\n"
                message += f"Position 1: {pos_sizes[0]:.6f} → TP1 ${signal['tp1']:.2f}\n"
                message += f"Position 2: {pos_sizes[1]:.6f} → TP2 ${signal['tp2']:.2f} (trails)\n"
                message += f"Position 3: {pos_sizes[2]:.6f} → TP3 ${signal['tp3']:.2f} (trails)\n"
                message += f"\nRisk: {self.risk_percent}%"
                asyncio.run(self.send_telegram(message))

            return True

        except Exception as e:
            print(f"❌ Failed to open 3-position group: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def send_telegram(self, message):
        """Send Telegram notification"""
        if self.telegram_bot and self.telegram_chat_id:
            try:
                await self.telegram_bot.send_message(
                    chat_id=self.telegram_chat_id,
                    text=message,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"⚠️  Telegram send failed: {e}")

    def _check_closed_positions(self):
        """Check for positions that have been closed and log them"""
        if not self.exchange_connected:
            return

        # Get currently open position order IDs
        open_positions = self.get_open_positions()
        current_order_ids = set()
        if open_positions:
            current_order_ids = {str(pos.get('id', '')) for pos in open_positions}

        # Find positions that were tracked but are now closed
        tracked_order_ids = set(self.positions_tracker.keys())
        closed_order_ids = tracked_order_ids - current_order_ids

        # Log closed positions
        for order_id in closed_order_ids:
            try:
                # Fetch order details
                order = self.exchange.fetch_order(order_id, self.symbol)

                if order['status'] == 'closed':
                    self._log_position_closed(
                        order_id=order_id,
                        close_price=order.get('average', 0),
                        profit=order.get('info', {}).get('realizedPnl', 0),
                        status='CLOSED'
                    )
            except Exception as e:
                print(f"⚠️  Error checking closed position {order_id}: {e}")

    def _wait_until_next_hour(self):
        """Wait until the next full hour while monitoring positions"""
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_hour - now).total_seconds()

        if wait_seconds > 0:
            print(f"\n⏰ Waiting until next hour: {next_hour.strftime('%H:%M:%S')}")
            print(f"   Time now: {now.strftime('%H:%M:%S')}")
            print(f"   Wait time: {int(wait_seconds/60)} min {int(wait_seconds%60)} sec")
            print(f"   🎯 Real-time TP/SL monitoring: Active (checking every 10s)")

            monitoring_interval = 10  # Check every 10 seconds
            elapsed = 0

            while elapsed < wait_seconds:
                sleep_time = min(monitoring_interval, wait_seconds - elapsed)
                time.sleep(sleep_time)
                elapsed += sleep_time

                # Sync positions with exchange first
                self._sync_positions_with_exchange()

                # Check TP/SL levels in real-time
                self._check_tp_sl_realtime()

                # Check for closed positions
                self._check_closed_positions()

    def run(self):
        """Main bot loop"""
        print(f"\n{'='*80}")
        print(f"🤖 CRYPTO BOT STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"📊 Configuration:")
        print(f"   Symbol: {self.symbol}")
        print(f"   Timeframe: {self.timeframe}")
        print(f"   Strategy: V3 Adaptive (TREND/RANGE detection)")
        print(f"   Check interval: Every hour")
        print(f"   Risk per trade: {self.risk_percent}%")
        print(f"   Max positions: {self.max_positions}")
        print(f"   Mode: {'🧪 DRY RUN (TEST)' if self.dry_run else '🚀 LIVE TRADING'}")
        print(f"   Exchange: {'TESTNET' if self.testnet else 'PRODUCTION'}")
        print(f"   🎯 Real-time TP/SL monitoring: Every 10 seconds (checks bar high/low)")
        print(f"\n🎯 Adaptive TP Levels:")
        print(f"   TREND Mode: {self.trend_tp1_pct}% / {self.trend_tp2_pct}% / {self.trend_tp3_pct}%")
        print(f"   RANGE Mode: {self.range_tp1_pct}% / {self.range_tp2_pct}% / {self.range_tp3_pct}%")
        print(f"{'='*80}\n")

        # Send startup notification to Telegram
        if self.telegram_bot and self.telegram_chat_id:
            startup_message = f"""
🤖 <b>CRYPTO BOT STARTED</b>

📊 <b>Configuration:</b>
Symbol: {self.symbol}
Timeframe: {self.timeframe}
Strategy: V3 Adaptive (TREND/RANGE)
Risk per trade: {self.risk_percent}%
Max positions: {self.max_positions}
Mode: {'🧪 DRY RUN (TEST)' if self.dry_run else '🚀 LIVE TRADING'}
Exchange: {'TESTNET' if self.testnet else 'PRODUCTION'}

🎯 <b>TP Levels:</b>
TREND: {self.trend_tp1_pct}% / {self.trend_tp2_pct}% / {self.trend_tp3_pct}%
RANGE: {self.range_tp1_pct}% / {self.range_tp2_pct}% / {self.range_tp3_pct}%

⏰ <b>Started at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ Bot is now active and monitoring the market!
"""
            try:
                asyncio.run(self.send_telegram(startup_message))
                print("📱 Startup notification sent to Telegram")
            except Exception as e:
                print(f"⚠️  Failed to send startup notification: {e}")

        # Wait until next hour before starting
        print("⏰ Bot will start checking at the next full hour...")
        self._wait_until_next_hour()

        iteration = 0

        try:
            while True:
                iteration += 1

                print(f"\n{'='*80}")
                print(f"🔄 Iteration #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*80}")

                # Check connection
                if not self.exchange_connected:
                    print("❌ Exchange disconnected! Attempting to reconnect...")
                    if not self.connect_exchange():
                        print("❌ Reconnection failed. Waiting 60s...")
                        time.sleep(60)
                        continue

                # Check current positions
                open_positions = self.get_open_positions()
                
                # Sync positions with exchange first
                self._sync_positions_with_exchange()
                
                # Check TP/SL levels in real-time
                self._check_tp_sl_realtime()
                
                print(f"📊 Open positions: {len(open_positions)}/{self.max_positions}")

                if len(open_positions) > 0:
                    for i, pos in enumerate(open_positions, 1):
                        side = pos.get('side', 'unknown')
                        contracts = pos.get('contracts', 0)
                        entry_price = pos.get('entryPrice', 0)
                        unrealized_pnl = pos.get('unrealizedPnl') if pos.get('unrealizedPnl') is not None else 0.0
                        mark_price = pos.get('markPrice', 0)
                        order_id = str(pos.get('id', ''))
                        
                        # Get status from tracker if available
                        status = 'OPEN'
                        if order_id in self.positions_tracker:
                            status = self.positions_tracker[order_id].get('status', 'OPEN')
                        
                        # Calculate profit percentage
                        profit_pct = 0.0
                        if entry_price and entry_price > 0 and mark_price and mark_price > 0:
                            if side.lower() == 'long':
                                profit_pct = ((mark_price - entry_price) / entry_price) * 100
                            elif side.lower() == 'short':
                                profit_pct = ((entry_price - mark_price) / entry_price) * 100
                        
                        print(f"   Position #{i}: {side.upper()} {contracts}, "
                              f"Entry=${entry_price:.2f}, Mark=${mark_price:.2f}, "
                              f"P&L: ${unrealized_pnl:.2f} ({profit_pct:+.2f}%), "
                              f"Status: {status}")

                # Check for closed positions
                self._check_closed_positions()

                # Update trailing stops for open positions
                if len(open_positions) > 0:
                    self.update_trailing_stops()

                # Analyze market
                print(f"\n🔍 Analyzing market...")
                signal = self.analyze_market()

                if signal:
                    print(f"\n✅ Signal detected!")

                    # Check if already have position in same direction
                    has_same_direction = False
                    for pos in open_positions:
                        pos_side = pos.get('side', '')
                        if (pos_side == 'long' and signal['direction'] == 1) or \
                           (pos_side == 'short' and signal['direction'] == -1):
                            has_same_direction = True
                            break

                    if has_same_direction:
                        direction_str = 'LONG' if signal['direction'] == 1 else 'SHORT'
                        print(f"⚠️  Already have {direction_str} position - skipping")
                    elif len(open_positions) >= self.max_positions:
                        print(f"⚠️  Max positions reached ({self.max_positions}) - skipping")
                    else:
                        # Open position
                        print(f"📈 Attempting to open position...")
                        success = self.open_position(signal)
                        if success:
                            print(f"✅ Position opened successfully!")
                        else:
                            print(f"❌ Failed to open position")
                else:
                    print("   ℹ️  No signals at this time")

                # Account status
                try:
                    balance = self.exchange.fetch_balance()
                    print(f"\n💰 Account status:")
                    print(f"   USDT Balance: {balance['USDT']['free']:.2f}")
                    print(f"   USDT Used: {balance['USDT']['used']:.2f}")
                    print(f"   USDT Total: {balance['USDT']['total']:.2f}")
                except Exception as e:
                    print(f"⚠️  Could not fetch balance: {e}")

                # Wait until next hour
                print(f"\n{'='*80}")
                print(f"💤 Waiting until next full hour...")
                print(f"   Press Ctrl+C to stop the bot")
                print(f"{'='*80}\n")

                self._wait_until_next_hour()

        except KeyboardInterrupt:
            print(f"\n\n{'='*80}")
            print("⚠️  BOT STOPPED BY USER")
            print(f"{'='*80}")
            print(f"Total iterations: {iteration}")
            print(f"Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Show final positions
            open_positions = self.get_open_positions()
            if len(open_positions) > 0:
                print(f"\n⚠️  WARNING: {len(open_positions)} position(s) still open!")
                print("   Remember to close them manually if needed.")
            else:
                print("\n✅ No open positions")

            # Send shutdown notification to Telegram
            if self.telegram_bot and self.telegram_chat_id:
                shutdown_message = f"""
⏹️ <b>CRYPTO BOT STOPPED</b>

📊 <b>Summary:</b>
Symbol: {self.symbol}
Total iterations: {iteration}
Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{"⚠️ <b>WARNING:</b> " + str(len(open_positions)) + " position(s) still open!" if len(open_positions) > 0 else "✅ No open positions"}

🛑 Bot has been stopped by user.
"""
                try:
                    asyncio.run(self.send_telegram(shutdown_message))
                    print("📱 Shutdown notification sent to Telegram")
                except Exception as e:
                    print(f"⚠️  Failed to send shutdown notification: {e}")

            print(f"{'='*80}\n")

        except Exception as e:
            print(f"\n\n❌ BOT ERROR: {e}")
            import traceback
            traceback.print_exc()

        finally:
            print("🔌 Disconnecting from Binance...")
            self.disconnect_exchange()
            print("✅ Shutdown complete")


if __name__ == "__main__":
    # Example usage - edit .env file for your configuration
    from dotenv import load_dotenv
    load_dotenv()

    bot = LiveBotBinanceFullAuto(
        symbol=os.getenv('SYMBOL', 'BTC/USDT'),
        timeframe=os.getenv('TIMEFRAME', '1h'),
        risk_percent=float(os.getenv('RISK_PERCENT', '2.0')),
        max_positions=int(os.getenv('MAX_POSITIONS', '3')),
        dry_run=os.getenv('DRY_RUN', 'True').lower() == 'true',
        testnet=os.getenv('TESTNET', 'True').lower() == 'true',
        api_key=os.getenv('BINANCE_API_KEY'),
        api_secret=os.getenv('BINANCE_API_SECRET'),
        telegram_token=os.getenv('TELEGRAM_TOKEN'),
        telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID')
    )

    # Connect and run
    if bot.connect_exchange():
        bot.run()
    else:
        print("❌ Failed to connect to exchange. Exiting...")
