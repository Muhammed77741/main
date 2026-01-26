"""
Full-Auto Live Trading Bot for MT5
Uses V3 Adaptive Strategy with TREND/RANGE detection

⚠️ DANGEROUS: Trades automatically without confirmation!
"""

import MetaTrader5 as mt5
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
import signal
import json

# Add parent directory to path to access shared modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.pattern_recognition_strategy import PatternRecognitionStrategy
from shared.telegram_helper import check_telegram_bot_import
from shared.bot_resilience import retry_with_timeout, BotWatchdog, interruptible_sleep

# Add trading_app directory to path to access MT5Manager
trading_app_path = Path(__file__).parent.parent.parent / 'trading_app'
if str(trading_app_path) not in sys.path:
    sys.path.insert(0, str(trading_app_path))

from core.mt5_manager import mt5_manager

# ============================================================================
# CRITICAL: Safety constants for multi-position SL modification protection
# ============================================================================
# These constants prevent race condition where trailing stops are applied
# immediately after position opening, causing premature SL hits on positions 2 & 3
#
# Timeline:
#   0-30s:  No SL modifications allowed (position confirmation period)
#   30-60s: TP1 can close, but NO trailing activation yet
#   60s+:   Trailing can activate (only if TP1 confirmed hit)
#
# Values chosen based on:
#   - Broker confirmation time: typically 5-10 seconds
#   - Network latency: 1-5 seconds
#   - MT5 synchronization delay: 5-10 seconds
#   - Safety margin: 2x typical delays
# ============================================================================

MIN_POSITION_AGE_FOR_TRAILING = 60  # seconds - minimum 1 minute after opening before trailing can activate
MIN_POSITION_AGE_FOR_SL_MODIFY = 30  # seconds - minimum 30 seconds before any SL modification
MIN_SL_MODIFY_INTERVAL = 10          # seconds - minimum time between consecutive SL modifications
BROKER_CONFIRMATION_TIMEOUT = 10     # seconds - wait for broker confirmation after opening

# SL Distance validation constants (percentages)
MIN_SL_DISTANCE_FROM_ENTRY_PCT = 0.003   # 0.3% - minimum distance from entry price
MIN_SL_DISTANCE_FROM_PRICE_PCT = 0.002   # 0.2% - minimum distance from current price


class LiveBotMT5FullAuto:
    """
    Full-automatic trading bot for MT5
    
    Features:
    - Uses V3 Adaptive Strategy with TREND/RANGE detection
    - Automatic position opening/closing
    - Adapts TP levels based on market regime
    - Risk management
    - Optional Telegram notifications
    - DRY RUN mode for testing
    """
    
    def __init__(self, telegram_token=None, telegram_chat_id=None,
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1,
                 check_interval=3600, risk_percent=2.0, max_positions=9,
                 dry_run=False, bot_id=None, use_database=True,
                 use_3_position_mode=False, total_position_size=None, min_order_size=None,
                 use_trailing_stops=True, trailing_stop_pct=0.5,
                 use_regime_based_sl=False, trend_sl=16, range_sl=12,
                 max_hold_bars=100,
                 trend_tp1=None, trend_tp2=None, trend_tp3=None,
                 range_tp1=None, range_tp2=None, range_tp3=None):
        """
        Initialize bot

        Args:
            telegram_token: Telegram bot token (optional)
            telegram_chat_id: Telegram chat ID (optional)
            symbol: Trading symbol
            timeframe: MT5 timeframe
            check_interval: Check interval in seconds
            risk_percent: Risk per trade (%)
            max_positions: Max simultaneous positions
            dry_run: If True, no real trades
            bot_id: Unique bot identifier for database tracking
            use_database: If True, use database for position tracking
            use_regime_based_sl: Use fixed regime-based SL instead of strategy SL
            trend_sl: TREND mode SL in points (default 16 for XAUUSD)
            range_sl: RANGE mode SL in points (default 12 for XAUUSD)
            max_hold_bars: Maximum bars to hold position before timeout (default 100, like backtest)
            trend_tp1/2/3: TREND mode TP levels in points (optional, defaults: 30/55/90 for XAUUSD)
            range_tp1/2/3: RANGE mode TP levels in points (optional, defaults: 20/35/50 for XAUUSD)
        """
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.check_interval = check_interval
        self.risk_percent = risk_percent
        self.max_positions = max_positions
        self.dry_run = dry_run

        # Bot identification for database
        self.bot_id = bot_id or f"xauusd_bot_{symbol}"
        self.use_database = use_database

        # Phase 2: 3-Position Mode settings
        self.use_3_position_mode = use_3_position_mode
        self.total_position_size = total_position_size
        self.min_order_size = min_order_size
        self.use_trailing_stops = use_trailing_stops  # Enable/disable trailing stops
        self.trailing_stop_pct = trailing_stop_pct  # Trailing stop percentage for 3-position mode

        # Regime-based SL settings
        self.use_regime_based_sl = use_regime_based_sl
        self.trend_sl_points = trend_sl  # SL for TREND mode in points
        self.range_sl_points = range_sl  # SL for RANGE mode in points

        # Position timeout settings
        self.max_hold_bars = max_hold_bars  # Close position after N bars if TP/SL not hit

        # Initialize strategy
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')
        
        # TREND MODE parameters (strong trend) - use provided values or defaults for XAUUSD
        self.trend_tp1 = trend_tp1 if trend_tp1 is not None else 30
        self.trend_tp2 = trend_tp2 if trend_tp2 is not None else 55
        self.trend_tp3 = trend_tp3 if trend_tp3 is not None else 90
        
        # RANGE MODE parameters (sideways) - use provided values or defaults for XAUUSD
        self.range_tp1 = range_tp1 if range_tp1 is not None else 20
        self.range_tp2 = range_tp2 if range_tp2 is not None else 35
        self.range_tp3 = range_tp3 if range_tp3 is not None else 50
        
        # Current market regime
        self.current_regime = 'RANGE'

        # Position tracking
        # FIX: Add symbol to filename for consistency with GUI and crypto bot
        symbol_clean = self.symbol.replace("/", "_")
        self.trades_file = f'bot_trades_log_{symbol_clean}.csv'
        self.tp_hits_file = f'bot_tp_hits_log_{symbol_clean}.csv'
        self.positions_tracker = {}  # {ticket: position_data}

        # Phase 2: 3-Position Mode tracking
        self.position_groups = {}  # {group_id: {'tp1_hit': bool, 'max_price': float, 'min_price': float, 'positions': [...]}}
        self.group_counter = 0  # Counter for position groups (0-99) used in magic number generation

        # Resilience features (CRITICAL: Network stability)
        self.running = True  # Flag for graceful shutdown
        self.watchdog = None  # Will be initialized in run()
        
        # Register signal handlers for graceful shutdown (only works in main thread)
        try:
            import threading
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
                print("✅ Signal handlers registered")
            else:
                print("⚠️  Running in worker thread - signal handlers not registered")
                print("   Bot will use self.running flag for graceful shutdown")
        except ValueError as e:
            print(f"⚠️  Could not register signal handlers: {e}")
            print("   Bot will use self.running flag for graceful shutdown")

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

        self.mt5_connected = False

        # Connection monitoring
        self.connection_errors = 0
        self.max_connection_errors = 5
        self.reconnect_delays = [60, 120, 300, 600, 900]  # Exponential backoff in seconds
        self.last_successful_fetch = None
        self.heartbeat_interval = 300  # Check connection every 5 minutes
        self.last_heartbeat = None

    def _initialize_trades_log(self):
        """Initialize CSV file for trade logging"""
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Ticket', 'Open_Time', 'Close_Time', 'Type', 'Volume',
                    'Entry_Price', 'SL', 'TP', 'Close_Price', 'Profit',
                    'Pips', 'Market_Regime', 'Duration_Hours', 'Status', 'Comment',
                    'Position_Group_ID', 'Position_Num'  # Add 3-position mode fields
                ])
            print(f"📝 Created trade log file: {self.trades_file}")

    
    def _initialize_tp_hits_log(self):
        """Initialize CSV file for TP hits logging"""
        if not os.path.exists(self.tp_hits_file):
            with open(self.tp_hits_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Order_ID', 'Position_Num', 'Position_Group_ID', 
                    'TP_Level', 'Type', 'Amount',
                    'Entry_Price', 'TP_Target', 'Current_Price', 'SL', 'Trailing_Active',
                    'Profit', 'Profit_Pct'
                ])
            print(f"📝 Created TP hits log file: {self.tp_hits_file}")
    
    def _generate_magic(self, position_num: int, group_counter: int) -> int:
        """
        Generate unique magic number for position tracking
        
        Format: BBBBPPGG (8 digits)
        - BBBB: bot_id hash (4 digits)  
        - PP: position_num (01, 02, 03)
        - GG: group_counter (00-99)
        
        Args:
            position_num: Position number in group (1, 2, or 3)
            group_counter: Group counter (0-99)
            
        Returns:
            int: Unique magic number
        """
        # Hash bot_id to 4 digits
        bot_hash = abs(hash(self.bot_id)) % 10000
        
        # Combine into 8-digit number
        magic = int(f"{bot_hash:04d}{position_num:02d}{group_counter:02d}")
        
        return magic
    
    def _get_position_by_magic(self, position_num: int, group_counter: int):
        """Get specific position by magic number
        
        Args:
            position_num: Position number in group (1, 2, or 3)
            group_counter: Group counter (0-99)
            
        Returns:
            MT5 position object or None
        """
        magic = self._generate_magic(position_num, group_counter)
        positions = mt5.positions_get(magic=magic)
        
        if positions and len(positions) > 0:
            return positions[0]
        return None
    
    def _get_group_positions_by_magic(self, group_counter: int) -> dict:
        """
        Get all 3 positions of a group by magic number
        
        Args:
            group_counter: Group counter (0-99)
            
        Returns:
            dict: {position_num: mt5_position, ...}
        """
        group_positions = {}
        
        for pos_num in [1, 2, 3]:
            pos = self._get_position_by_magic(pos_num, group_counter)
            if pos:
                group_positions[pos_num] = pos
        
        return group_positions
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals for graceful exit"""
        print(f"\n⚠️  Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def _cleanup(self):
        """Cleanup resources on shutdown"""
        print("\n🧹 Cleaning up resources...")
        
        # 1. Stop watchdog
        if self.watchdog:
            try:
                self.watchdog.stop()
            except Exception as e:
                print(f"⚠️  Error stopping watchdog: {e}")
        
        # 2. MT5 connection (managed by singleton - don't shutdown here)
        # The MT5Manager singleton maintains the connection for all bots
        # Only shutdown when entire app closes (in MainWindow.closeEvent)
        if self.mt5_connected:
            print("✅ Bot disconnected from shared MT5 connection")
        
        # 3. Close database
        if self.db:
            try:
                self.db.close()
                print("✅ Database connection closed")
            except Exception as e:
                print(f"⚠️  Error closing database: {e}")
        
        # 4. Send shutdown notification
        if self.telegram_bot:
            try:
                self.send_telegram("🛑 <b>Bot Stopped</b>\n\nBot has been shut down gracefully.")
                print("✅ Shutdown notification sent")
            except Exception as e:
                print(f"⚠️  Error sending notification: {e}")
        
        print("✅ Cleanup complete")
    
    def _get_position_group_model(self):
        """Helper to get PositionGroup model class (cached import)"""
        if not hasattr(self, '_PositionGroup'):
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_app'))
                from models.position_group import PositionGroup
                self._PositionGroup = PositionGroup
            except Exception as e:
                print(f"⚠️  Could not import PositionGroup model: {e}")
                self._PositionGroup = None
        return self._PositionGroup
    
    def _log_position_opened(self, ticket, position_type, volume, entry_price,
                             sl, tp, regime, comment='', position_group_id=None, position_num=0):
        """Log when position is opened"""
        open_time = datetime.now()
        current_timestamp = time.time()
        
        self.positions_tracker[ticket] = {
            'ticket': ticket,
            'open_time': open_time,
            'close_time': None,
            'type': position_type,
            'volume': volume,
            'entry_price': entry_price,
            'sl': sl,
            'tp': tp,
            'close_price': None,
            'profit': None,
            'pips': None,
            'regime': regime,
            'duration': None,
            'status': 'OPEN',
            'comment': comment,
            'position_group_id': position_group_id,
            'position_num': position_num,
            # CRITICAL: Add timestamps for SL modification protection
            'opened_at': current_timestamp,  # Unix timestamp for precise age calculation
            'confirmed_at': None,            # Will be set after broker confirmation
            'last_sl_modify_at': None        # Track last SL modification time
        }
        
        # Also save to database if enabled
        if self.use_database and self.db:
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_app'))
                from models.trade_record import TradeRecord

                # FIX: Ensure consistent order_id format with DRY- prefix for dry-run
                order_id_str = f"DRY-{ticket}" if self.dry_run else str(ticket)

                trade = TradeRecord(
                    trade_id=0,  # Will be auto-assigned by database
                    bot_id=self.bot_id,
                    symbol=self.symbol,  # Add symbol field
                    order_id=order_id_str,
                    open_time=open_time,
                    trade_type=position_type,
                    amount=volume,
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
                print(f"📊 Position saved to database: Ticket={ticket}, OrderID={order_id_str}")
            except Exception as e:
                print(f"⚠️  Failed to save position to database: {e}")
        
        print(f"📊 Logged opened position: Ticket={ticket}, Type={position_type}, Entry={entry_price}")
    
    def _log_position_closed(self, ticket, close_price, profit, status='CLOSED'):
        """Log when position is closed"""
        if ticket not in self.positions_tracker:
            print(f"⚠️  Ticket {ticket} not found in tracker")
            return
        
        pos = self.positions_tracker[ticket]
        close_time = datetime.now()
        pos['close_time'] = close_time
        pos['close_price'] = close_price
        pos['profit'] = profit
        pos['status'] = status
        
        # Calculate duration
        if pos['open_time']:
            duration = (pos['close_time'] - pos['open_time']).total_seconds() / 3600
            pos['duration'] = round(duration, 2)
        
        # Calculate pips
        if pos['type'] == 'BUY':
            pips = (close_price - pos['entry_price']) * 10  # For XAUUSD
        else:
            pips = (pos['entry_price'] - close_price) * 10
        pos['pips'] = round(pips, 1)
        
        # Calculate profit percentage (approximate)
        profit_pct = (pips / pos['entry_price']) * 100 if pos['entry_price'] > 0 else 0
        
        # Write to CSV
        self._write_trade_to_csv(pos)
        
        # Update in database if enabled
        if self.use_database and self.db:
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_app'))
                from models.trade_record import TradeRecord

                # FIX: Use same order_id format as when position was opened
                order_id_str = f"DRY-{ticket}" if self.dry_run else str(ticket)

                trade = TradeRecord(
                    trade_id=0,  # Not used for update
                    bot_id=self.bot_id,
                    symbol=self.symbol,  # Add symbol field
                    order_id=order_id_str,
                    open_time=pos['open_time'],
                    close_time=close_time,
                    duration_hours=pos['duration'],
                    trade_type=pos['type'],
                    amount=pos['volume'],
                    entry_price=pos['entry_price'],
                    close_price=close_price,
                    stop_loss=pos['sl'],
                    take_profit=pos['tp'],
                    profit=profit,
                    profit_percent=profit_pct,
                    status=status,
                    market_regime=pos['regime'],
                    comment=pos['comment']
                )
                self.db.update_trade(trade)
                print(f"📊 Position updated in database: Ticket={ticket}, OrderID={order_id_str}, Status={status}")
            except Exception as e:
                print(f"⚠️  Failed to update position in database: {e}")
        
        # Remove from tracker
        del self.positions_tracker[ticket]
        
        print(f"📊 Logged closed position: Ticket={ticket}, Profit={profit:.2f}, Pips={pips:.1f}, Duration={pos['duration']}h")
    
    def _write_trade_to_csv(self, trade_data):
        """Write completed trade to CSV file"""
        with open(self.trades_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trade_data['ticket'],
                trade_data['open_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_data['open_time'] else '',
                trade_data['close_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_data['close_time'] else '',
                trade_data['type'],
                trade_data['volume'],
                trade_data['entry_price'],
                trade_data['sl'],
                trade_data['tp'],
                trade_data['close_price'],
                trade_data['profit'],
                trade_data['pips'],
                trade_data['regime'],
                trade_data['duration'],
                trade_data['status'],
                trade_data['comment'],
                trade_data.get('position_group_id', ''),  # Add group ID
                trade_data.get('position_num', 0)         # Add position number
            ])
    
    def _get_trade_id_by_order(self, order_id):
        """Get trade_id from database by order_id (cached for performance)"""
        if not self.use_database or not self.db:
            return None
        
        try:
            # Create cache if it doesn't exist
            if not hasattr(self, '_trade_id_cache'):
                self._trade_id_cache = {}
                self._cache_timestamp = datetime.now()
            
            # Refresh cache every 60 seconds
            if (datetime.now() - self._cache_timestamp).total_seconds() > 60:
                self._trade_id_cache = {}
                self._cache_timestamp = datetime.now()
            
            # Check cache first
            order_id_str = str(order_id)
            if order_id_str in self._trade_id_cache:
                return self._trade_id_cache[order_id_str]
            
            # Query database
            trades = self.db.get_trades(self.bot_id, limit=1000)
            for trade in trades:
                if trade.order_id == order_id_str:
                    # Cache the result
                    self._trade_id_cache[order_id_str] = (trade.trade_id, trade)
                    return (trade.trade_id, trade)
            
            return None
        except Exception as e:
            print(f"⚠️  Error looking up trade_id: {e}")
            return None
    
    def _log_tp_hit(self, ticket, tp_level, current_price):
        """Log when a TP level is hit"""
        if ticket not in self.positions_tracker:
            return
        
        pos = self.positions_tracker[ticket]
        
        # Calculate duration in minutes
        duration_minutes = 0
        if pos['open_time']:
            duration_minutes = (datetime.now() - pos['open_time']).total_seconds() / 60
        
        # Calculate pips
        if pos['type'] == 'BUY':
            pips = (current_price - pos['entry_price']) * 10  # For XAUUSD
        else:
            pips = (pos['entry_price'] - current_price) * 10
        
        # Estimate profit (approximation based on pips)
        point_value = 100.0  # For XAUUSD, 1 lot = $100 per point
        profit = pips / 10 * pos['volume'] * point_value
        
        # Write to TP hits log
        with open(self.tp_hits_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ticket,
                pos.get('position_num', ''),
                pos.get('position_group_id', ''),
                tp_level,
                pos['type'],
                pos['volume'],
                pos['entry_price'],
                pos['tp'],
                current_price,
                pos['sl'],
                'TRUE' if pos.get('trailing_stop_active', False) else 'FALSE',
                round(profit, 2),
                round((profit / (pos['entry_price'] * pos['volume']) * 100) if pos['entry_price'] > 0 else 0, 2)
            ])
        
        # Log TP hit event to database
        if self.use_database and self.db:
            try:
                result = self._get_trade_id_by_order(ticket)
                if result:
                    trade_id, _ = result
                    details = json.dumps({
                        'price': current_price,
                        'profit': round(profit, 2),
                        'pips': round(pips, 1)
                    })
                    self.db.log_trade_event(
                        trade_id=trade_id,
                        bot_id=self.bot_id,
                        event_type='TP_HIT',
                        position_num=pos.get('position_num'),
                        position_group_id=pos.get('position_group_id'),
                        details=details
                    )
            except Exception as e:
                print(f"⚠️  Failed to log TP hit to database: {e}")
        
        print(f"🎯 TP HIT LOGGED: Ticket={ticket}, Level={tp_level}, Price={current_price:.2f}, Pips={pips:.1f}")
    
    def _sync_positions_with_exchange(self):
        """Sync database positions with actual exchange positions
        
        Detects positions that were manually closed on exchange but still show as OPEN in database
        """
        if not self.use_database or not self.db or self.dry_run or not self.mt5_connected:
            return
        
        try:
            # Get all OPEN positions from database
            db_trades = self.db.get_open_trades(self.bot_id)
            if not db_trades:
                return
            
            # Get current open positions from MT5
            open_positions = mt5.positions_get(symbol=self.symbol)
            mt5_position_tickets = set(pos.ticket for pos in open_positions) if open_positions else set()
            
            # Check each database position
            for trade in db_trades:
                try:
                    ticket = int(trade.order_id)
                except (ValueError, TypeError):
                    continue
                
                # If position is in database but not on MT5, it was closed manually
                if ticket not in mt5_position_tickets:
                    print(f"📊 Position #{ticket} manually closed on MT5 - syncing database...")
                    
                    # Get current price for profit calculation
                    tick = mt5.symbol_info_tick(self.symbol)
                    if tick:
                        close_price = tick.bid if trade.trade_type == 'BUY' else tick.ask
                        
                        # Calculate profit
                        if trade.trade_type == 'BUY':
                            profit = (close_price - trade.entry_price) * trade.amount
                        else:
                            profit = (trade.entry_price - close_price) * trade.amount
                    else:
                        close_price = trade.entry_price
                        profit = 0.0
                    
                    # Log the close
                    self._log_position_closed(
                        ticket=ticket,
                        close_price=close_price,
                        profit=profit,
                        status='CLOSED'
                    )
                    
                    print(f"✅ Database synced for position #{ticket}")
        except Exception as e:
            print(f"⚠️  Error syncing positions with exchange: {e}")

    def _restore_positions_from_database(self):
        """Restore positions from database on bot startup
        
        This ensures position_group_id and position_num are preserved after bot restart
        """
        if not self.use_database or not self.db:
            print("   Database not enabled - no positions to restore")
            return
        
        try:
            # Get all OPEN positions from database
            db_trades = self.db.get_open_trades(self.bot_id)
            
            if not db_trades:
                print("   No open positions in database")
                return
            
            restored_count = 0
            
            for trade in db_trades:
                # Extract ticket
                try:
                    if isinstance(trade.order_id, str) and trade.order_id.startswith('DRY-'):
                        ticket = trade.order_id  # Keep as string for dry-run
                    else:
                        ticket = int(trade.order_id)
                except (ValueError, TypeError):
                    ticket = trade.order_id
                
                # Restore to in-memory tracker with all metadata
                self.positions_tracker[ticket] = {
                    'ticket': ticket,
                    'open_time': trade.open_time,
                    'close_time': None,
                    'type': trade.trade_type,
                    'volume': trade.amount,
                    'entry_price': trade.entry_price,
                    'sl': trade.stop_loss,
                    'tp': trade.take_profit,
                    'close_price': None,
                    'profit': None,
                    'pips': None,
                    'regime': trade.market_regime,
                    'duration': None,
                    'status': trade.status,
                    'comment': trade.comment or '',
                    'position_group_id': trade.position_group_id,  # CRITICAL: Restore group_id
                    'position_num': trade.position_num,             # CRITICAL: Restore position_num
                    'opened_at': time.time() - 3600,  # Assume opened at least 1 hour ago (safe for age checks)
                    'confirmed_at': time.time() - 3600,
                    'last_sl_modify_at': None
                }
                
                restored_count += 1
            
            print(f"   ✅ Restored {restored_count} position(s) from database")
            
            # Also restore position groups
            if self.use_3_position_mode:
                # Get all position groups for this bot
                group_ids = set(pos.get('position_group_id') for pos in self.positions_tracker.values() 
                               if pos.get('position_group_id'))
                
                for group_id in group_ids:
                    try:
                        db_group = self.db.get_position_group(group_id)
                        if db_group:
                            self.position_groups[group_id] = {
                                'tp1_hit': db_group.tp1_hit,
                                'sl_hit': False,  # If positions still open, SL wasn't hit
                                'max_price': db_group.max_price,
                                'min_price': db_group.min_price,
                                'positions': [ticket for ticket, pos in self.positions_tracker.items() 
                                            if pos.get('position_group_id') == group_id],
                                'entry_price': db_group.entry_price,
                                'trade_type': db_group.trade_type,
                                'created_at': time.time() - 3600  # Safe for age checks
                            }
                            print(f"   ✅ Restored position group {group_id[:8]}")
                    except Exception as e:
                        print(f"   ⚠️  Could not restore position group {group_id[:8]}: {e}")
                        
        except Exception as e:
            print(f"   ⚠️  Error restoring positions from database: {e}")
            import traceback
            traceback.print_exc()

    def _update_3position_trailing(self, positions_to_check, current_price):
        """
        Update trailing stops for 3-position groups (Phase 2)

        Logic:
        - Track max_price/min_price for each group
        - When any position reaches TP1, activate trailing for Pos 2 & 3
        - Trailing formula: 50% retracement from max profit
        """
        if not self.use_3_position_mode or not self.use_trailing_stops:
            return

        # Group positions by position_group_id
        groups = {}
        for ticket, pos_data in positions_to_check.items():
            group_id = pos_data.get('position_group_id')
            if not group_id:
                continue  # Not a 3-position group

            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append((ticket, pos_data))

        # Process each group
        for group_id, group_positions in groups.items():
            # CRITICAL: Skip groups where SL was hit (all positions closed)
            if group_id in self.position_groups and self.position_groups[group_id].get('sl_hit', False):
                continue  # Skip this group - SL already hit, no trailing needed
            
            # Initialize group tracking if needed (CRITICAL FIX #4: Restore from DB)
            if group_id not in self.position_groups:
                # Try to restore from database first
                restored_group = None
                if self.use_database and self.db:
                    try:
                        restored_group = self.db.get_position_group(group_id)
                        if restored_group:
                            print(f"✅ Restored position group {group_id[:8]} from database")
                            print(f"   TP1 hit: {restored_group.tp1_hit}, Max: {restored_group.max_price}, Min: {restored_group.min_price}")
                    except Exception as e:
                        print(f"⚠️  Could not restore position group from DB: {e}")
                
                if restored_group:
                    # Use restored data
                    self.position_groups[group_id] = {
                        'tp1_hit': restored_group.tp1_hit,
                        'sl_hit': False,  # Always reset on restore (if positions still open, SL wasn't hit)
                        'max_price': restored_group.max_price,
                        'min_price': restored_group.min_price,
                        'positions': [p[0] for p in group_positions],
                        'entry_price': restored_group.entry_price,
                        'trade_type': restored_group.trade_type,
                        'created_at': time.time()  # CRITICAL: Add timestamp
                    }
                else:
                    # Create new group
                    entry_price = group_positions[0][1]['entry_price']
                    trade_type = group_positions[0][1]['type']
                    current_timestamp = time.time()
                    self.position_groups[group_id] = {
                        'tp1_hit': False,
                        'sl_hit': False,  # Track if SL was hit for this group
                        'max_price': entry_price,
                        'min_price': entry_price,
                        'positions': [p[0] for p in group_positions],
                        'entry_price': entry_price,
                        'trade_type': trade_type,
                        'created_at': current_timestamp  # CRITICAL: Add timestamp for age checks
                    }
                    
                    # Save to database
                    if self.use_database and self.db:
                        try:
                            PositionGroup = self._get_position_group_model()
                            if PositionGroup:
                                new_group = PositionGroup(
                                group_id=group_id,
                                bot_id=self.bot_id,
                                tp1_hit=False,
                                entry_price=entry_price,
                                max_price=entry_price,
                                min_price=entry_price,
                                trade_type=trade_type,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            self.db.save_position_group(new_group)
                            print(f"✅ Saved new position group {group_id[:8]} to database")
                        except Exception as e:
                            print(f"⚠️  Could not save position group to DB: {e}")

            group_info = self.position_groups[group_id]
            
            # ===== CRITICAL CHECK #1: Group age protection =====
            # DO NOT modify SL for at least 60 seconds after group creation
            group_age = time.time() - group_info.get('created_at', 0)
            if group_age < MIN_POSITION_AGE_FOR_TRAILING:
                # Silently skip - do not spam logs during cooldown period
                continue
            
            # ===== CRITICAL CHECK #2: Individual position age protection =====
            # Verify each position is old enough before allowing modifications
            all_positions_ready = True
            for ticket, pos_data in group_positions:
                if ticket in self.positions_tracker:
                    pos_opened_at = self.positions_tracker[ticket].get('opened_at', 0)
                    if pos_opened_at > 0:
                        pos_age = time.time() - pos_opened_at
                        if pos_age < MIN_POSITION_AGE_FOR_SL_MODIFY:
                            all_positions_ready = False
                            break
            
            if not all_positions_ready:
                # At least one position is too young - skip this group
                continue
            
            # ===== ENHANCED LOGGING: Group state for debugging =====
            if group_age < 120:  # Log for first 2 minutes only to avoid spam
                print(f"\n🔍 Group {group_id[:8]} passed age checks (age: {group_age:.1f}s)")
                print(f"   Entry: {group_info['entry_price']:.2f}, Type: {group_info['trade_type']}")
                print(f"   TP1 hit: {group_info['tp1_hit']}")
                print(f"   Max price: {group_info['max_price']:.2f}, Min price: {group_info['min_price']:.2f}")
                print(f"   Positions in group: {len(group_positions)}")

            # Update max/min price (CRITICAL FIX #4: Save to DB)
            price_updated = False
            if group_positions[0][1]['type'] == 'BUY':
                if current_price > group_info['max_price']:
                    group_info['max_price'] = current_price
                    price_updated = True
            else:  # SELL
                if current_price < group_info['min_price']:
                    group_info['min_price'] = current_price
                    price_updated = True
            
            # Save to database if price was updated
            if price_updated and self.use_database and self.db:
                try:
                    PositionGroup = self._get_position_group_model()
                    if PositionGroup:
                        updated_group = PositionGroup(
                        group_id=group_id,
                        bot_id=self.bot_id,
                        tp1_hit=group_info['tp1_hit'],
                        entry_price=group_info['entry_price'],
                        max_price=group_info['max_price'],
                        min_price=group_info['min_price'],
                        trade_type=group_info['trade_type'],
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    self.db.update_position_group(updated_group)
                except Exception as e:
                    print(f"⚠️  Could not update position group in DB: {e}")

            # Check if Position 1 is closed (not in group anymore) OR price reached TP1
            tp1_just_hit = False
            pos1_found = False
            pos1_status = None
            for ticket, pos_data in group_positions:
                if pos_data.get('position_num') == 1:
                    pos1_found = True
                    pos1_status = pos_data.get('status', 'OPEN')
                    tp1 = pos_data['tp']

                    if not group_info['tp1_hit']:  # Only check if not already hit
                        # Activate trailing if position 1 is being closed/processed
                        if pos1_status != 'OPEN':
                            group_info['tp1_hit'] = True
                            tp1_just_hit = True
                            print(f"🎯 Group {group_id[:8]} Position 1 closing ({pos1_status})! Activating trailing for Pos 2 & 3")
                        # Or if price reached TP1 (fallback for same-cycle activation)
                        elif pos_data['type'] == 'BUY':
                            if current_price >= tp1:
                                group_info['tp1_hit'] = True
                                tp1_just_hit = True
                                print(f"🎯 Group {group_id[:8]} TP1 reached at {current_price:.2f}! Activating trailing for Pos 2 & 3")
                        else:  # SELL
                            if current_price <= tp1:
                                group_info['tp1_hit'] = True
                                tp1_just_hit = True
                                print(f"🎯 Group {group_id[:8]} TP1 reached at {current_price:.2f}! Activating trailing for Pos 2 & 3")

            # If Position 1 not found in group (already closed), check WHY it closed
            if not pos1_found and not group_info['tp1_hit']:
                # CRITICAL: Don't activate trailing if position 1 closed by SL or error!
                # Only activate if it was genuinely closed by TP1
                
                # Try to find position 1 in closed trades
                pos1_closed_by_tp1 = False
                
                # Check in-memory tracker first
                for ticket, pos_data in list(self.positions_tracker.items()):
                    if (pos_data.get('position_group_id') == group_id and 
                        pos_data.get('position_num') == 1 and
                        pos_data.get('status') in ['TP1', 'TP1_PROCESSING']):
                        pos1_closed_by_tp1 = True
                        print(f"✅ Group {group_id[:8]} Position 1 confirmed closed by TP1 (from tracker)")
                        break
                
                # If not found in tracker, check database
                if not pos1_closed_by_tp1 and self.use_database and self.db:
                    try:
                        # Get all trades for this bot (using correct method name)
                        all_trades = self.db.get_trades(self.bot_id, limit=1000)
                        for trade in all_trades:
                            if (trade.position_group_id == group_id and 
                                trade.position_num == 1 and
                                trade.status in ['TP1', 'TP1_PROCESSING', 'CLOSED']):
                                # Check if close price was near TP1
                                if trade.close_price:
                                    # For BUY: close price should be >= TP1 (or very close)
                                    # For SELL: close price should be <= TP1 (or very close)
                                    tp1_price = trade.take_profit
                                    if group_info['trade_type'] == 'BUY':
                                        if trade.close_price >= tp1_price * 0.999:  # Within 0.1% of TP1
                                            pos1_closed_by_tp1 = True
                                            print(f"✅ Group {group_id[:8]} Position 1 confirmed closed by TP1 (from DB)")
                                    else:  # SELL
                                        if trade.close_price <= tp1_price * 1.001:  # Within 0.1% of TP1
                                            pos1_closed_by_tp1 = True
                                            print(f"✅ Group {group_id[:8]} Position 1 confirmed closed by TP1 (from DB)")
                                break
                    except Exception as e:
                        print(f"⚠️  Could not check position 1 status in DB: {e}")
                
                # Only activate trailing if Position 1 was confirmed to close by TP1
                if pos1_closed_by_tp1:
                    group_info['tp1_hit'] = True
                    tp1_just_hit = True
                    print(f"🎯 Group {group_id[:8]} Position 1 closed by TP1! Activating trailing for Pos 2 & 3")
                else:
                    # Position 1 closed but NOT by TP1 - do NOT activate trailing
                    print(f"⚠️  Group {group_id[:8]} Position 1 closed but NOT by TP1 - trailing NOT activated")
                    print(f"   This usually means Position 1 was closed by SL or manually")
                    print(f"   Positions 2 & 3 will keep their original SL")

            
            # Save tp1_hit to database
            if tp1_just_hit and self.use_database and self.db:
                try:
                    PositionGroup = self._get_position_group_model()
                    if PositionGroup:
                        updated_group = PositionGroup(
                        group_id=group_id,
                        bot_id=self.bot_id,
                        tp1_hit=True,
                        entry_price=group_info['entry_price'],
                        max_price=group_info['max_price'],
                        min_price=group_info['min_price'],
                        trade_type=group_info['trade_type'],
                        tp1_close_price=current_price,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    self.db.update_position_group(updated_group)
                    print(f"✅ Saved TP1 hit to database for group {group_id[:8]}")
                except Exception as e:
                    print(f"⚠️  Could not save TP1 hit to DB: {e}")

            # Update trailing stops for Pos 2 & 3 if TP1 hit
            if group_info['tp1_hit']:
                for ticket, pos_data in group_positions:
                    pos_num = pos_data.get('position_num', 0)
                    if pos_num in [2, 3]:  # Only Pos 2 and 3 trail
                        entry_price = pos_data['entry_price']

                        # Mark trailing stop as active in database
                        if self.use_database and self.db:
                            try:
                                # Find the trade in database and update trailing_stop_active flag
                                open_trades = self.db.get_open_trades(self.bot_id)
                                for trade in open_trades:
                                    if trade.order_id == str(ticket) and not trade.trailing_stop_active:
                                        trade.trailing_stop_active = True
                                        self.db.update_trade(trade)
                                        print(f"✓ Pos {pos_num} (#{ticket}) marked as trailing stop active in database")
                                        
                                        # Log trailing activation event
                                        try:
                                            details = json.dumps({
                                                'max_price': group_info['max_price'],
                                                'entry_price': entry_price
                                            })
                                            self.db.log_trade_event(
                                                trade_id=trade.trade_id,
                                                bot_id=self.bot_id,
                                                event_type='TRAILING_ACTIVATED',
                                                position_num=pos_num,
                                                position_group_id=group_id,
                                                details=details
                                            )
                                        except Exception as e:
                                            print(f"⚠️  Failed to log trailing activation: {e}")
                                        
                                        break  # Exit loop after updating the target trade
                            except Exception as e:
                                print(f"⚠️  Error updating trailing_stop_active in DB: {e}")

                        if pos_data['type'] == 'BUY':
                            # Trailing stop: configurable % retracement from max price
                            new_sl = group_info['max_price'] - (group_info['max_price'] - entry_price) * self.trailing_stop_pct

                            # Only update if new SL is better (higher) than current
                            if new_sl > pos_data['sl']:
                                # ===== CRITICAL VALIDATION #1: Check recent modification =====
                                if ticket in self.positions_tracker:
                                    last_modify = self.positions_tracker[ticket].get('last_sl_modify_at', 0)
                                    if last_modify > 0:
                                        time_since_last = time.time() - last_modify
                                        if time_since_last < MIN_SL_MODIFY_INTERVAL:
                                            print(f"   ⏳ Pos {pos_num} SL modified too recently ({time_since_last:.1f}s ago), skipping")
                                            continue
                                
                                # ===== CRITICAL VALIDATION #2: Minimum distance from entry =====
                                distance_from_entry = abs(new_sl - entry_price)
                                min_distance_from_entry = entry_price * 0.003  # minimum 0.3% from entry
                                if distance_from_entry < min_distance_from_entry:
                                    print(f"   ⚠️  Pos {pos_num} new SL too close to entry: {distance_from_entry:.2f} < {min_distance_from_entry:.2f}, skipping")
                                    continue
                                
                                # ===== CRITICAL VALIDATION #3: Minimum distance from current price =====
                                # Check minimum distance from current price (stop level)
                                symbol_info = mt5.symbol_info(self.symbol)
                                if symbol_info:
                                    stop_level = symbol_info.trade_stops_level
                                    point = symbol_info.point
                                    min_distance_broker = stop_level * point
                                    min_distance_custom = current_price * 0.002  # minimum 0.2% from current price
                                    min_distance = max(min_distance_broker, min_distance_custom)

                                    # For BUY: SL must be at least min_distance below current price
                                    distance_from_price = current_price - new_sl
                                    if distance_from_price < min_distance:
                                        # SL too close to current price - skip this update
                                        print(f"   ⚠️  Pos {pos_num} SL too close to price: {distance_from_price:.2f} < {min_distance:.2f}, skipping")
                                        continue

                                old_sl = pos_data['sl']
                                print(f"   📊 Pos {pos_num} trailing SL: {old_sl:.2f} → {new_sl:.2f} (entry: {entry_price:.2f}, max: {group_info['max_price']:.2f})")


                                # Update SL on MT5 broker (CRITICAL FIX #3)
                                sl_updated_on_broker = False
                                if not self.dry_run:
                                    try:
                                        request = {
                                            "action": mt5.TRADE_ACTION_SLTP,
                                            "position": ticket,
                                            "sl": new_sl,
                                            "tp": pos_data['tp'],
                                            "symbol": self.symbol,
                                            "magic": 234000,
                                        }
                                        result = mt5.order_send(request)
                                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                                            sl_updated_on_broker = True
                                            print(f"   ✅ SL updated on MT5 broker: {new_sl:.2f}")
                                        else:
                                            error_msg = result.comment if result else "No result"
                                            print(f"   ❌ Failed to update SL on MT5: {error_msg}")
                                    except Exception as e:
                                        print(f"   ❌ Error updating SL on MT5: {e}")
                                else:
                                    sl_updated_on_broker = True  # Simulate success in dry-run
                                
                                # Only update in memory if broker update succeeded
                                if sl_updated_on_broker:
                                    pos_data['sl'] = new_sl
                                    # Update in tracker
                                    if ticket in self.positions_tracker:
                                        self.positions_tracker[ticket]['sl'] = new_sl
                                        self.positions_tracker[ticket]['last_sl_modify_at'] = time.time()  # CRITICAL: Record modification time (BUY)
                                    
                                    # Update in database
                                    if self.use_database and self.db:
                                        try:
                                            open_trades = self.db.get_open_trades(self.bot_id)
                                            for trade in open_trades:
                                                if trade.order_id == str(ticket):
                                                    trade.stop_loss = new_sl
                                                    self.db.update_trade(trade)
                                                    break
                                        except Exception as e:
                                            print(f"   ⚠️  Failed to update SL in database: {e}")
                                    
                                    # Send Telegram notification for trailing stop update
                                    if self.telegram_bot:
                                        message = f"📊 <b>Trailing Stop Updated</b>\n\n"
                                        message += f"Ticket: #{ticket}\n"
                                        message += f"Position: {pos_num}/3\n"
                                        message += f"Type: {pos_data['type']}\n"
                                        message += f"Entry: ${entry_price:.2f}\n"
                                        message += f"New SL: ${new_sl:.2f}\n"
                                        message += f"Max Price: ${group_info['max_price']:.2f}"
                                        try:
                                            self.send_telegram(message)
                                        except Exception as e:
                                            print(f"⚠️  Failed to send Telegram notification: {e}")
                                else:
                                    print(f"   ⚠️  SL not updated in memory - broker update failed")
                        else:  # SELL
                            # Trailing stop: configurable % retracement from min price
                            new_sl = group_info['min_price'] + (entry_price - group_info['min_price']) * self.trailing_stop_pct

                            # Only update if new SL is better (lower) than current
                            if new_sl < pos_data['sl']:
                                # ===== CRITICAL VALIDATION #1: Check recent modification =====
                                if ticket in self.positions_tracker:
                                    last_modify = self.positions_tracker[ticket].get('last_sl_modify_at', 0)
                                    if last_modify > 0:
                                        time_since_last = time.time() - last_modify
                                        if time_since_last < MIN_SL_MODIFY_INTERVAL:
                                            print(f"   ⏳ Pos {pos_num} SL modified too recently ({time_since_last:.1f}s ago), skipping")
                                            continue
                                
                                # ===== CRITICAL VALIDATION #2: Minimum distance from entry =====
                                distance_from_entry = abs(new_sl - entry_price)
                                min_distance_from_entry = entry_price * 0.003  # minimum 0.3% from entry
                                if distance_from_entry < min_distance_from_entry:
                                    print(f"   ⚠️  Pos {pos_num} new SL too close to entry: {distance_from_entry:.2f} < {min_distance_from_entry:.2f}, skipping")
                                    continue
                                
                                # ===== CRITICAL VALIDATION #3: Minimum distance from current price =====
                                # Check minimum distance from current price (stop level)
                                symbol_info = mt5.symbol_info(self.symbol)
                                if symbol_info:
                                    stop_level = symbol_info.trade_stops_level
                                    point = symbol_info.point
                                    min_distance_broker = stop_level * point
                                    min_distance_custom = current_price * 0.002  # minimum 0.2% from current price
                                    min_distance = max(min_distance_broker, min_distance_custom)

                                    # For SELL: SL must be at least min_distance above current price
                                    distance_from_price = new_sl - current_price
                                    if distance_from_price < min_distance:
                                        # SL too close to current price - skip this update
                                        print(f"   ⚠️  Pos {pos_num} SL too close to price: {distance_from_price:.2f} < {min_distance:.2f}, skipping")
                                        continue

                                old_sl = pos_data['sl']
                                print(f"   📊 Pos {pos_num} trailing SL: {old_sl:.2f} → {new_sl:.2f} (entry: {entry_price:.2f}, min: {group_info['min_price']:.2f})")


                                # Update SL on MT5 broker (CRITICAL FIX #3)
                                sl_updated_on_broker = False
                                if not self.dry_run:
                                    try:
                                        request = {
                                            "action": mt5.TRADE_ACTION_SLTP,
                                            "position": ticket,
                                            "sl": new_sl,
                                            "tp": pos_data['tp'],
                                            "symbol": self.symbol,
                                            "magic": 234000,
                                        }
                                        result = mt5.order_send(request)
                                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                                            sl_updated_on_broker = True
                                            print(f"   ✅ SL updated on MT5 broker: {new_sl:.2f}")
                                        else:
                                            error_msg = result.comment if result else "No result"
                                            print(f"   ❌ Failed to update SL on MT5: {error_msg}")
                                    except Exception as e:
                                        print(f"   ❌ Error updating SL on MT5: {e}")
                                else:
                                    sl_updated_on_broker = True  # Simulate success in dry-run
                                
                                # Only update in memory if broker update succeeded
                                if sl_updated_on_broker:
                                    pos_data['sl'] = new_sl
                                    # Update in tracker
                                    if ticket in self.positions_tracker:
                                        self.positions_tracker[ticket]['sl'] = new_sl
                                        self.positions_tracker[ticket]['last_sl_modify_at'] = time.time()  # CRITICAL: Record modification time (SELL)
                                    
                                    # Update in database
                                    if self.use_database and self.db:
                                        try:
                                            open_trades = self.db.get_open_trades(self.bot_id)
                                            for trade in open_trades:
                                                if trade.order_id == str(ticket):
                                                    trade.stop_loss = new_sl
                                                    self.db.update_trade(trade)
                                                    break
                                        except Exception as e:
                                            print(f"   ⚠️  Failed to update SL in database: {e}")
                                    
                                    # Send Telegram notification for trailing stop update
                                    if self.telegram_bot:
                                        message = f"📊 <b>Trailing Stop Updated</b>\n\n"
                                        message += f"Ticket: #{ticket}\n"
                                        message += f"Position: {pos_num}/3\n"
                                        message += f"Type: {pos_data['type']}\n"
                                        message += f"Entry: ${entry_price:.2f}\n"
                                        message += f"New SL: ${new_sl:.2f}\n"
                                        message += f"Min Price: ${group_info['min_price']:.2f}"
                                        try:
                                            self.send_telegram(message)
                                        except Exception as e:
                                            print(f"⚠️  Failed to send Telegram notification: {e}")
                                else:
                                    print(f"   ⚠️  SL not updated in memory - broker update failed")

    def _check_tp_sl_realtime(self):
        """Monitor open positions in real-time and check if TP/SL levels are hit
        
        Checks:
        1. Loads open positions from database (if enabled) or tracker
        2. Current bar's high/low to see if TP/SL was touched during the bar
        3. Current price to determine exit price
        4. Closes position if TP or SL is hit
        """
        if not self.mt5_connected:
            return
        
        # Get positions to monitor
        positions_to_check = {}
        
        # If database is enabled, load positions from database
        if self.use_database and self.db:
            try:
                db_trades = self.db.get_open_trades(self.bot_id)
                if self.dry_run:
                    # Silently monitor positions in background for dry-run mode
                    pass
                elif db_trades:
                    # Log for live mode too
                    print(f"📊 LIVE: Monitoring {len(db_trades)} open position(s) from database")
                for trade in db_trades:
                    # FIX: Handle dry-run order_ids with DRY- prefix
                    # Keep ticket as string for dry-run, int for live
                    try:
                        # Try to extract number from DRY-xxx format
                        if isinstance(trade.order_id, str) and trade.order_id.startswith('DRY-'):
                            ticket = trade.order_id  # Keep as string "DRY-12345"
                        else:
                            ticket = int(trade.order_id)  # Convert to int for live
                    except (ValueError, TypeError):
                        ticket = trade.order_id  # Fallback: keep as-is
                    
                    positions_to_check[ticket] = {
                        'tp': trade.take_profit,
                        'sl': trade.stop_loss,
                        'type': trade.trade_type,
                        'entry_price': trade.entry_price,
                        'volume': trade.amount,
                        'status': trade.status,
                        'open_time': trade.open_time,
                        'regime': trade.market_regime,
                        'comment': trade.comment or '',
                        'position_group_id': trade.position_group_id,
                        'position_num': trade.position_num
                    }
                    # Also sync to in-memory tracker if not already there
                    if ticket not in self.positions_tracker:
                        self.positions_tracker[ticket] = positions_to_check[ticket].copy()
                        self.positions_tracker[ticket]['ticket'] = ticket
                        self.positions_tracker[ticket]['close_time'] = None
                        self.positions_tracker[ticket]['close_price'] = None
                        self.positions_tracker[ticket]['profit'] = None
                        self.positions_tracker[ticket]['pips'] = None
                        self.positions_tracker[ticket]['duration'] = None
            except Exception as e:
                print(f"⚠️  Error loading positions from database: {e}")
                # Fall back to in-memory tracker
                positions_to_check = self.positions_tracker.copy()
        else:
            # Use in-memory tracker
            positions_to_check = self.positions_tracker.copy()
        
        if not positions_to_check:
            return
        
        # Get current open positions from MT5 (skip if dry_run)
        open_positions = []
        mt5_position_tickets = set()
        
        if not self.dry_run:
            open_positions = mt5.positions_get(symbol=self.symbol)
            
            # Check if positions_get failed (returns None on error)
            if open_positions is None:
                print(f"⚠️  Failed to get positions from MT5 - skipping sync check")
                print(f"   This might be a temporary connection issue")
                return  # Don't sync if we can't verify MT5 state
            
            # Build set of ticket numbers from MT5 positions
            mt5_position_tickets = set(pos.ticket for pos in open_positions)
        else:
            # In dry_run mode, all database positions are "valid" (use string tickets)
            mt5_position_tickets = set(positions_to_check.keys())
        
        # Get current bar data to check high/low
        try:
            rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 1)
            if rates is not None and len(rates) > 0:
                bar_high = rates[0]['high']
                bar_low = rates[0]['low']
            else:
                # Fallback if can't get bar data
                bar_high = None
                bar_low = None
        except Exception as e:
            print(f"⚠️  Could not fetch current bar data: {e}")
            bar_high = None
            bar_low = None
        
        # Check each tracked position
        for ticket, tracked_pos in list(positions_to_check.items()):
            # Skip if already processing or closed
            if tracked_pos.get('status') not in ['OPEN']:
                continue
            
            # Check if position is still on MT5 (skip check if dry_run)
            if not self.dry_run and ticket not in mt5_position_tickets:
                # Position closed on MT5 but still in DB as OPEN
                print(f"📊 Position #{ticket} closed on MT5 but DB shows OPEN - syncing...")
                if ticket in self.positions_tracker:
                    # Try to close it properly
                    self._log_position_closed(
                        ticket=ticket,
                        close_price=tracked_pos['entry_price'],  # Unknown close price
                        profit=0.0,  # Unknown profit
                        status='CLOSED'
                    )
                continue
            
            # Get current price
            current_price = None
            if not self.dry_run:
                # Find the position data from MT5
                position = next((p for p in open_positions if p.ticket == ticket), None)
                if not position:
                    continue
                
                # Get current price
                tick = mt5.symbol_info_tick(self.symbol)
                if not tick:
                    continue
                
                # Use appropriate price based on position type
                # For BUY: close at bid (sell price), For SELL: close at ask (buy price)
                current_price = tick.bid if tracked_pos['type'] == 'BUY' else tick.ask
            else:
                # In dry_run mode, get current price from ticker
                try:
                    tick = mt5.symbol_info_tick(self.symbol)
                    if tick:
                        current_price = tick.bid if tracked_pos['type'] == 'BUY' else tick.ask
                        if not current_price or current_price <= 0:
                            print(f"⚠️  Could not get valid current price for dry_run position {ticket}")
                            continue
                    else:
                        print(f"⚠️  Could not get tick data for dry_run position {ticket}")
                        continue
                except Exception as e:
                    print(f"⚠️  Error getting current price for dry_run: {e}")
                    continue

            # Phase 2: Update trailing stops for 3-position groups
            self._update_3position_trailing({ticket: tracked_pos}, current_price)

            # Read TP/SL from tracked position (database columns or in-memory)
            # Note: SL may have been updated by trailing logic above
            tp_target = tracked_pos['tp']
            sl_target = tracked_pos['sl']
            
            # Skip if TP or SL is None/missing
            if tp_target is None or sl_target is None:
                print(f"⚠️  Position #{ticket} has missing TP ({tp_target}) or SL ({sl_target}) - skipping check")
                continue
            
            # Convert to float to ensure proper comparison
            try:
                tp_target = float(tp_target)
                sl_target = float(sl_target)
            except (ValueError, TypeError) as e:
                print(f"⚠️  Position #{ticket} has invalid TP/SL values - skipping check: {e}")
                continue

            # Check position timeout (close after max_hold_bars if TP/SL not hit)
            if self.max_hold_bars > 0:
                try:
                    open_time = tracked_pos.get('open_time')
                    if open_time:
                        # Calculate how many bars have passed since position opened
                        from datetime import datetime
                        if isinstance(open_time, str):
                            open_time = datetime.fromisoformat(open_time)

                        # Get timeframe in seconds
                        timeframe_seconds = self.check_interval  # Assumes check_interval matches timeframe

                        # Calculate bars elapsed
                        time_diff = datetime.now() - open_time
                        bars_elapsed = int(time_diff.total_seconds() / timeframe_seconds)

                        if bars_elapsed >= self.max_hold_bars:
                            # Position timeout - close at current price
                            print(f"⏰ Position #{ticket} timeout after {bars_elapsed} bars (max: {self.max_hold_bars})")
                            print(f"   Closing at current price: ${current_price:.2f}")

                            # Close position
                            if not self.dry_run:
                                # Live: close via MT5
                                close_request = {
                                    "action": mt5.TRADE_ACTION_DEAL,
                                    "symbol": self.symbol,
                                    "volume": tracked_pos['volume'],
                                    "type": mt5.ORDER_TYPE_SELL if tracked_pos['type'] == 'BUY' else mt5.ORDER_TYPE_BUY,
                                    "position": ticket,
                                    "price": current_price,
                                    "deviation": 20,
                                    "magic": 234000,
                                    "comment": "Timeout",
                                    "type_time": mt5.ORDER_TIME_GTC,
                                    "type_filling": self._get_filling_mode(),
                                }
                                result = mt5.order_send(close_request)
                                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                                    print(f"   ✅ Position closed via MT5 on timeout")
                                else:
                                    error_msg = f"retcode={result.retcode}" if result else "result is None"
                                    print(f"   ❌ Failed to close position on timeout: {error_msg}")

                            # Calculate profit
                            if tracked_pos['type'] == 'BUY':
                                profit_pct = ((current_price - tracked_pos['entry_price']) / tracked_pos['entry_price']) * 100
                            else:
                                profit_pct = ((tracked_pos['entry_price'] - current_price) / tracked_pos['entry_price']) * 100

                            # Log position closed with timeout status
                            self._log_position_closed(
                                ticket=ticket,
                                close_price=current_price,
                                profit=profit_pct,
                                status='TIMEOUT'
                            )

                            continue  # Skip TP/SL checks for this position

                except Exception as e:
                    print(f"⚠️  Error checking timeout for position #{ticket}: {e}")

            # Determine which TP level this is from position_num or comment
            tp_level = 'TP1'  # Default for single-position mode
            position_num = tracked_pos.get('position_num', 0)
            if position_num == 1:
                tp_level = 'TP1'
            elif position_num == 2:
                tp_level = 'TP2'
            elif position_num == 3:
                tp_level = 'TP3'
            elif 'P1/3' in tracked_pos.get('comment', ''):
                tp_level = 'TP1'
            elif 'P2/3' in tracked_pos.get('comment', ''):
                tp_level = 'TP2'
            elif 'P3/3' in tracked_pos.get('comment', ''):
                tp_level = 'TP3'
            elif 'TP1' in tracked_pos.get('comment', ''):
                tp_level = 'TP1'
            elif 'TP2' in tracked_pos.get('comment', ''):
                tp_level = 'TP2'
            elif 'TP3' in tracked_pos.get('comment', ''):
                tp_level = 'TP3'
            
            # Check if TP or SL is hit based on bar high/low OR current price
            tp_hit = False
            sl_hit = False
            
            if tracked_pos['type'] == 'BUY':
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
                hit_type = tp_level if tp_hit else 'SL'
                target_price = tp_target if tp_hit else sl_target

                # FIX: Add debug logging for dry-run
                if self.dry_run:
                    print(f"🧪 DRY-RUN: Detected {hit_type} hit for position #{ticket}")
                    print(f"   Type: {tracked_pos['type']}, Entry: ${tracked_pos['entry_price']:.2f}")
                    print(f"   TP Target: ${tp_target:.2f}, SL Target: ${sl_target:.2f}")
                    print(f"   Current Price: ${current_price:.2f}")
                    print(f"   Ticket type: {type(ticket)}, Tracker has: {ticket in self.positions_tracker}")
                
                # Update status in both tracker and database immediately
                processing_status = f'{hit_type}_PROCESSING'
                tracked_pos['status'] = processing_status
                if ticket in self.positions_tracker:
                    self.positions_tracker[ticket]['status'] = processing_status
                
                # Update status in database immediately to prevent re-processing
                if self.use_database and self.db:
                    try:
                        sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_app'))
                        from models.trade_record import TradeRecord
                        temp_trade = TradeRecord(
                            trade_id=0,
                            bot_id=self.bot_id,
                            symbol=self.symbol,  # Add symbol field
                            order_id=str(ticket),
                            open_time=tracked_pos['open_time'],
                            trade_type=tracked_pos['type'],
                            amount=tracked_pos['volume'],
                            entry_price=tracked_pos['entry_price'],
                            stop_loss=tracked_pos['sl'],
                            take_profit=tracked_pos['tp'],
                            status=processing_status,
                            market_regime=tracked_pos['regime'],
                            comment=tracked_pos['comment']
                        )
                        self.db.update_trade(temp_trade)
                        print(f"📊 Updated position #{ticket} status to {processing_status} in database")
                    except Exception as e:
                        print(f"⚠️  Failed to update status in database: {e}")
                
                # Log the hit
                self._log_tp_hit(ticket, hit_type, current_price)

                # FIX: Add detailed logging for TP/SL events
                print(f"📊 EVENT LOGGED: {hit_type} hit for ticket={ticket}, price={current_price:.2f}")
                if self.use_database and self.db:
                    try:
                        # Count total TP/SL events in database for verification
                        all_events = self.db.get_trade_events(bot_id=self.bot_id)
                        tp_events = [e for e in all_events if 'TP' in e.get('event_type', '')]
                        sl_events = [e for e in all_events if 'SL' in e.get('event_type', '')]
                        print(f"   Total events in DB: {len(all_events)} (TP: {len(tp_events)}, SL: {len(sl_events)})")
                    except Exception as e:
                        print(f"⚠️  Could not query events: {e}")

                # Close the position at current price
                close_successful = False
                if not self.dry_run:
                    try:
                        # Close position using MT5
                        order_type = mt5.ORDER_TYPE_SELL if tracked_pos['type'] == 'BUY' else mt5.ORDER_TYPE_BUY
                        
                        print(f"🔄 Closing position #{ticket} at current price ${current_price:.2f} ({hit_type} hit)")
                        
                        request = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "symbol": self.symbol,
                            "volume": tracked_pos['volume'],
                            "type": order_type,
                            "position": ticket,
                            "price": current_price,
                            "deviation": 20,
                            "magic": 234000,
                            "comment": f"Close_{hit_type}",
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": self._get_filling_mode(),
                        }
                        
                        result = mt5.order_send(request)
                        
                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                            print(f"✅ Position closed: Order #{result.order}")
                            close_successful = True
                        else:
                            error_msg = result.comment if result else "No result"
                            print(f"❌ Failed to close position #{ticket}: {error_msg}")
                            # Revert status back to OPEN if close failed
                            tracked_pos['status'] = 'OPEN'
                            if ticket in self.positions_tracker:
                                self.positions_tracker[ticket]['status'] = 'OPEN'
                            # Revert in database too
                            if self.use_database and self.db:
                                try:
                                    temp_trade.status = 'OPEN'
                                    self.db.update_trade(temp_trade)
                                except:
                                    pass
                    except Exception as e:
                        print(f"❌ Failed to close position #{ticket}: {e}")
                        # Revert status back to OPEN if close failed
                        tracked_pos['status'] = 'OPEN'
                        if ticket in self.positions_tracker:
                            self.positions_tracker[ticket]['status'] = 'OPEN'
                        # Revert in database too
                        if self.use_database and self.db:
                            try:
                                temp_trade.status = 'OPEN'
                                self.db.update_trade(temp_trade)
                            except:
                                pass
                        tracked_pos['status'] = 'OPEN'
                else:
                    print(f"🧪 DRY RUN: Would close position #{ticket} at ${current_price:.2f} ({hit_type} hit)")
                    close_successful = True  # Simulate successful close in dry run
                
                # If close was successful, properly log the position as closed
                if close_successful:
                    # Calculate profit in pips
                    if tracked_pos['type'] == 'BUY':
                        pips = (current_price - tracked_pos['entry_price']) * 10
                    else:
                        pips = (tracked_pos['entry_price'] - current_price) * 10
                    
                    # Estimate profit in dollars (approximate)
                    point_value = 100.0  # For XAUUSD, 1 lot = $100 per point
                    profit = pips / 10 * tracked_pos['volume'] * point_value
                    
                    # Log position as closed with proper status
                    self._log_position_closed(
                        ticket=ticket,
                        close_price=current_price,
                        profit=profit,
                        status='CLOSED'  # Status is always CLOSED after TP/SL hit
                    )

                    # FIX: Add verification logging after position closed
                    print(f"✅ Position #{ticket} closed successfully")
                    print(f"   Profit: ${profit:.2f}, Pips: {pips:.1f}")
                    print(f"   Reason: {hit_type}, Price: ${current_price:.2f}")
                    
                    # CRITICAL: If SL is hit in a 3-position group, close ALL positions in the group
                    if sl_hit and self.use_3_position_mode and tracked_pos.get('position_group_id'):
                        group_id = tracked_pos.get('position_group_id')
                        pos_num = tracked_pos.get('position_num', 'Unknown')
                        
                        print(f"\n⚠️  SL HIT for Position {pos_num} in group {group_id[:8]}")
                        print(f"   Closing ALL remaining positions in this group...")
                        
                        # Mark group as SL_HIT to prevent further trailing
                        if group_id in self.position_groups:
                            self.position_groups[group_id]['sl_hit'] = True
                        
                        # Find and close all other positions in the same group
                        for other_ticket, other_pos in list(self.positions_tracker.items()):
                            if (other_pos.get('position_group_id') == group_id and 
                                other_ticket != ticket and
                                other_pos.get('status') == 'OPEN'):
                                
                                other_pos_num = other_pos.get('position_num', 'Unknown')
                                print(f"   🔄 Closing Position {other_pos_num} (#{other_ticket}) from same group...")
                                
                                # Get current price for this position
                                try:
                                    tick = mt5.symbol_info_tick(self.symbol)
                                    if tick:
                                        group_close_price = tick.bid if other_pos['type'] == 'BUY' else tick.ask
                                    else:
                                        group_close_price = current_price
                                except:
                                    group_close_price = current_price
                                
                                # Close on MT5
                                if not self.dry_run:
                                    try:
                                        order_type = mt5.ORDER_TYPE_SELL if other_pos['type'] == 'BUY' else mt5.ORDER_TYPE_BUY
                                        request = {
                                            "action": mt5.TRADE_ACTION_DEAL,
                                            "symbol": self.symbol,
                                            "volume": other_pos['volume'],
                                            "type": order_type,
                                            "position": other_ticket,
                                            "price": group_close_price,
                                            "deviation": 20,
                                            "magic": 234000,
                                            "comment": f"Group_SL_Close",
                                            "type_time": mt5.ORDER_TIME_GTC,
                                            "type_filling": self._get_filling_mode(),
                                        }
                                        result = mt5.order_send(request)
                                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                                            print(f"      ✅ Position {other_pos_num} closed")
                                        else:
                                            print(f"      ❌ Failed to close Position {other_pos_num}")
                                    except Exception as e:
                                        print(f"      ❌ Error closing Position {other_pos_num}: {e}")
                                else:
                                    print(f"      🧪 DRY RUN: Would close Position {other_pos_num}")
                                
                                # Calculate profit for this position
                                if other_pos['type'] == 'BUY':
                                    other_pips = (group_close_price - other_pos['entry_price']) * 10
                                else:
                                    other_pips = (other_pos['entry_price'] - group_close_price) * 10
                                point_value = 100.0
                                other_profit = other_pips / 10 * other_pos['volume'] * point_value
                                
                                # Log as closed
                                self._log_position_closed(
                                    ticket=other_ticket,
                                    close_price=group_close_price,
                                    profit=other_profit,
                                    status='CLOSED'
                                )
                        
                        print(f"   ✅ Group {group_id[:8]} fully closed due to SL hit\n")

                    # Log SL/TP event to database
                    if self.use_database and self.db and sl_hit:
                        try:
                            result = self._get_trade_id_by_order(ticket)
                            if result:
                                trade_id, trade = result
                                is_trailing = getattr(trade, 'trailing_stop_active', False)
                                
                                details = json.dumps({
                                    'price': current_price,
                                    'profit': round(profit, 2),
                                    'pips': round(pips, 1)
                                })
                                # Log as TRAILING_HIT if trailing was active, otherwise SL_HIT
                                event_type = 'TRAILING_HIT' if is_trailing else 'SL_HIT'
                                self.db.log_trade_event(
                                    trade_id=trade_id,
                                    bot_id=self.bot_id,
                                    event_type=event_type,
                                    position_num=tracked_pos.get('position_num'),
                                    position_group_id=tracked_pos.get('position_group_id'),
                                    details=details
                                )
                        except Exception as e:
                            print(f"⚠️  Failed to log SL hit to database: {e}")
                
                # Send Telegram notification
                if self.telegram_bot and close_successful:
                    emoji = "🎯" if tp_hit else "🛑"
                    message = f"{emoji} <b>{hit_type} HIT & CLOSED!</b>\n\n"
                    message += f"Ticket: #{ticket}\n"
                    message += f"Type: {tracked_pos['type']}\n"
                    message += f"Entry: ${tracked_pos['entry_price']:.2f}\n"
                    message += f"{hit_type} Target: ${target_price:.2f}\n"
                    message += f"Close Price: ${current_price:.2f}\n"
                    message += f"Volume: {tracked_pos['volume']} lot\n"
                    
                    # Calculate pips
                    if tracked_pos['type'] == 'BUY':
                        pips = (current_price - tracked_pos['entry_price']) * 10
                    else:
                        pips = (tracked_pos['entry_price'] - current_price) * 10
                    
                    sign = "+" if pips >= 0 else ""
                    message += f"Pips: {sign}{pips:.1f}\n"
                    message += f"Status: CLOSED"
                    
                    try:
                        self.send_telegram(message)
                    except Exception as e:
                        print(f"⚠️  Failed to send Telegram notification: {e}")
        
    def connect_mt5(self):
        """Connect to MT5 with retry and timeout"""
        
        def _connect():
            """Internal connection function with timeout protection"""
            start_time = time.time()

            # Use MT5Manager singleton instead of direct mt5.initialize()
            if not mt5_manager.initialize():
                error = mt5.last_error()
                raise Exception(f"Failed to initialize MT5: {error}")

            # Check timeout
            if time.time() - start_time > 25:
                raise Exception("MT5 initialization timeout")

            account_info = mt5.account_info()
            if account_info is None:
                raise Exception("Failed to get account info")

            return account_info
        
        # Retry with timeout: 3 attempts, 10 sec interval, 30 sec timeout
        account_info = retry_with_timeout(
            func=_connect,
            max_attempts=3,
            retry_interval=10,
            timeout_seconds=30,
            description="MT5 Connection"
        )
        
        if account_info is None:
            error_msg = "❌ Failed to connect to MT5 after 3 attempts"
            print(error_msg)
            
            # Send to Telegram
            if self.telegram_bot:
                try:
                    self.send_telegram(
                        f"❌ <b>MT5 Connection Error</b>\n\n"
                        f"{error_msg}\n\n"
                        f"Please ensure:\n"
                        f"1. MetaTrader 5 is installed and running\n"
                        f"2. 'Algo Trading' is enabled\n"
                        f"3. You're logged into an account"
                    )
                except Exception as e:
                    print(f"⚠️  Failed to send Telegram notification: {e}")
            
            self.mt5_connected = False
            return False
            
        self.mt5_connected = True
        success_msg = f"✅ Connected to MT5: {account_info.server} - Account {account_info.login}"
        print(success_msg)
        
        # Send success notification to Telegram
        if self.telegram_bot:
            try:
                self.send_telegram(f"✅ <b>Connected to MT5</b>\n\nServer: {account_info.server}\nAccount: {account_info.login}\nBalance: ${account_info.balance:.2f}")
            except Exception as e:
                print(f"⚠️  Failed to send Telegram notification: {e}")
        
        return True
        
    def disconnect_mt5(self):
        """Mark bot as disconnected from MT5 (connection managed by singleton)"""
        if self.mt5_connected:
            # Don't call mt5.shutdown() - the MT5Manager singleton manages the connection
            # Other bots may still be using it
            self.mt5_connected = False

    def _get_filling_mode(self):
        """Get appropriate filling mode for the symbol

        Different brokers support different filling modes:
        - FOK (Fill or Kill): Execute entire order or reject
        - IOC (Immediate or Cancel): Execute partial and cancel rest
        - RETURN: Market execution

        Returns:
            int: MT5 filling mode constant
        """
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"⚠️  Cannot get symbol info for {self.symbol}, using FOK mode")
            return mt5.ORDER_FILLING_FOK

        # Check which filling modes are supported
        filling = symbol_info.filling_mode

        # Prefer FOK > IOC > RETURN
        if filling & 1:  # FOK is supported (bit 0)
            if not hasattr(self, '_filling_mode_logged'):
                print(f"✅ Using FOK (Fill or Kill) filling mode for {self.symbol}")
                self._filling_mode_logged = True
            return mt5.ORDER_FILLING_FOK
        elif filling & 2:  # IOC is supported (bit 1)
            if not hasattr(self, '_filling_mode_logged'):
                print(f"✅ Using IOC (Immediate or Cancel) filling mode for {self.symbol}")
                self._filling_mode_logged = True
            return mt5.ORDER_FILLING_IOC
        else:  # RETURN (bit 2)
            if not hasattr(self, '_filling_mode_logged'):
                print(f"✅ Using RETURN (Market Execution) filling mode for {self.symbol}")
                self._filling_mode_logged = True
            return mt5.ORDER_FILLING_RETURN

    def _handle_connection_error(self, error, operation="operation"):
        """
        Handle connection errors with smart retry logic

        Args:
            error: Exception that occurred
            operation: Name of the operation that failed
        """
        self.connection_errors += 1

        error_msg = f"❌ Connection error during {operation}: {str(error)}"
        print(error_msg)

        # Mark as disconnected if too many errors
        if self.connection_errors >= 3:
            if self.mt5_connected:
                print(f"⚠️  {self.connection_errors} consecutive errors - marking as disconnected")
                self.mt5_connected = False

                # Send Telegram notification
                if self.telegram_bot:
                    try:
                        self.send_telegram(
                            f"🔴 <b>Connection Lost</b>\n\n"
                            f"Operation: {operation}\n"
                            f"Error: {str(error)}\n"
                            f"Consecutive errors: {self.connection_errors}\n\n"
                            f"Bot will attempt to reconnect..."
                        )
                    except Exception as e:
                        print(f"⚠️  Failed to send Telegram notification: {e}")

        return None

    def _reset_connection_errors(self):
        """Reset connection error counter after successful operation"""
        if self.connection_errors > 0:
            was_errors = self.connection_errors
            self.connection_errors = 0
            self.last_successful_fetch = datetime.now()

            # Notify if connection was restored
            if was_errors >= 3 and self.telegram_bot:
                try:
                    self.send_telegram(
                        f"✅ <b>Connection Restored</b>\n\n"
                        f"After {was_errors} failed attempts, connection is working again.\n"
                        f"Bot resumed normal operation."
                    )
                except Exception as e:
                    print(f"⚠️  Failed to send Telegram notification: {e}")

    def _check_heartbeat(self):
        """
        Periodic heartbeat check to verify connection is alive
        Returns True if check passed, False otherwise
        """
        now = datetime.now()

        # Check if heartbeat is needed
        if self.last_heartbeat:
            time_since_heartbeat = (now - self.last_heartbeat).total_seconds()
            if time_since_heartbeat < self.heartbeat_interval:
                return True  # Too soon for another check

        # Perform heartbeat check
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick and tick.ask > 0:
                self.last_heartbeat = now
                self._reset_connection_errors()
                return True
        except Exception as e:
            print(f"⚠️  Heartbeat check failed: {e}")
            self._handle_connection_error(e, "heartbeat check")
            return False

        return False

    def _attempt_reconnect(self):
        """
        Attempt to reconnect with exponential backoff
        Returns True if reconnected, False otherwise
        """
        # Calculate delay based on error count
        delay_index = min(self.connection_errors - 1, len(self.reconnect_delays) - 1)
        delay = self.reconnect_delays[delay_index]

        print(f"🔄 Attempting reconnection (attempt {self.connection_errors}/{self.max_connection_errors})...")
        print(f"   Waiting {delay}s before reconnect...")

        time.sleep(delay)

        # Attempt reconnection
        if self.connect_mt5():
            print("✅ Reconnection successful!")
            self.connection_errors = 0
            self.last_successful_fetch = datetime.now()

            # Send success notification
            if self.telegram_bot:
                try:
                    self.send_telegram(
                        f"✅ <b>Reconnected Successfully</b>\n\n"
                        f"Connection restored after {delay}s wait.\n"
                        f"Bot resumed normal operation."
                    )
                except Exception as e:
                    print(f"⚠️  Failed to send Telegram notification: {e}")

            return True
        else:
            print(f"❌ Reconnection failed (attempt {self.connection_errors})")

            # Check if max attempts reached
            if self.connection_errors >= self.max_connection_errors:
                error_msg = (
                    f"🛑 <b>Critical: Max Reconnection Attempts Reached</b>\n\n"
                    f"Failed to reconnect after {self.max_connection_errors} attempts.\n"
                    f"Bot requires manual intervention.\n\n"
                    f"Please check:\n"
                    f"- MT5 terminal is running\n"
                    f"- Internet connection\n"
                    f"- Broker connection"
                )
                print(f"\n{'='*80}")
                print(error_msg.replace('<b>', '').replace('</b>', '').replace('\n', '\n'))
                print(f"{'='*80}\n")

                if self.telegram_bot:
                    try:
                        self.send_telegram(error_msg)
                    except Exception as e:
                        print(f"⚠️  Failed to send Telegram notification: {e}")

            return False

    def _check_closed_positions(self):
        """Check for positions that have been closed and log them"""
        if not self.mt5_connected:
            return
        
        # Get currently open position tickets
        open_positions = mt5.positions_get(symbol=self.symbol)
        current_tickets = set()
        if open_positions:
            current_tickets = {pos.ticket for pos in open_positions}
        
        # Find positions that were tracked but are now closed
        tracked_tickets = set(self.positions_tracker.keys())
        closed_tickets = tracked_tickets - current_tickets
        
        # Log closed positions
        for ticket in closed_tickets:
            # Try to get deal history for this ticket
            from_date = datetime.now() - timedelta(days=7)
            deals = mt5.history_deals_get(from_date, datetime.now())
            
            if deals:
                for deal in deals:
                    if deal.order == ticket and deal.entry == mt5.DEAL_ENTRY_OUT:
                        # Found the closing deal
                        self._log_position_closed(
                            ticket=ticket,
                            close_price=deal.price,
                            profit=deal.profit,
                            status='TP' if deal.comment and 'tp' in deal.comment.lower() else 
                                   'SL' if deal.comment and 'sl' in deal.comment.lower() else 
                                   'CLOSED'
                        )
                        break
            else:
                # If we can't find deal history, mark as closed
                pos_data = self.positions_tracker.get(ticket)
                if pos_data:
                    self._log_position_closed(
                        ticket=ticket,
                        close_price=pos_data['entry_price'],
                        profit=0,
                        status='CLOSED'
                    )
            
    def send_telegram(self, message):
        """Send Telegram notification (synchronous wrapper for async bot)"""
        if self.telegram_bot and self.telegram_chat_id:
            try:
                # Use asyncio to send message, handling various event loop states
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        # Create new event loop if current one is closed
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    if loop.is_running():
                        # If loop is already running (e.g., in a thread), we can't use run_until_complete
                        # In this case, we just skip sending (trading bots run in separate thread)
                        # This is acceptable as Telegram notifications are non-critical
                        print(f"ℹ️  Telegram notification skipped (event loop already running)")
                        return
                    else:
                        # Run the coroutine in the event loop
                        loop.run_until_complete(self._send_telegram_async(message))
                except RuntimeError as e:
                    # Fallback: create a new event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self._send_telegram_async(message))
                    finally:
                        try:
                            loop.close()
                        except Exception:
                            pass  # Ignore cleanup errors
            except Exception as e:
                print(f"⚠️  Telegram send failed: {e}")

    async def _send_telegram_async(self, message):
        """Async helper for sending Telegram messages"""
        try:
            await self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"⚠️  Telegram message send error: {e}")
                
    def get_market_data(self, bars=250):
        """Get historical data from MT5

        Args:
            bars: Number of bars to fetch (default 250)
                  - Market regime detection: 100 bars
                  - Swing detection: 40 bars (±20)
                  - Pattern detection: 15 bars
                  - Buffer: 95 bars
        """
        if not self.mt5_connected:
            return None

        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, bars)

        if rates is None or len(rates) == 0:
            error = mt5.last_error()
            print(f"❌ Failed to get data for {self.symbol}")
            print(f"   Error: {error}")
            print(f"   Possible reasons:")
            print(f"   • Symbol not found in Market Watch (add it in MT5)")
            print(f"   • Incorrect symbol name (check broker's symbol list)")
            print(f"   • No historical data available for this timeframe")
            print(f"   • Symbol not supported by your broker")

            # Try to get symbol info to diagnose
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                print(f"   ⚠️  Symbol '{self.symbol}' not found - MT5 connection may be lost!")
                print(f"   → Attempting to reconnect to MT5...")

                # Try to reconnect using manager
                try:
                    if mt5_manager.reconnect():
                        print(f"   ✅ MT5 reconnected successfully!")
                        self.mt5_connected = True
                        # Retry getting data
                        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, bars)
                        if rates is not None and len(rates) > 0:
                            print(f"   ✅ Data retrieved after reconnection")
                            # Will continue to dataframe processing below
                        else:
                            print(f"   ❌ Still cannot get data after reconnection")
                            return None
                    else:
                        print(f"   ❌ Failed to reconnect to MT5")
                        self.mt5_connected = False
                        return None
                except Exception as e:
                    print(f"   ❌ Reconnection error: {e}")
                    self.mt5_connected = False
                    return None
            else:
                if not symbol_info.visible:
                    print(f"   ⚠️  Symbol exists but not visible in Market Watch")
                    print(f"   → Right-click Market Watch → Show All, or add symbol manually")
                return None

        # Check again after potential reconnection
        if rates is None or len(rates) == 0:
            return None
            
        df = pd.DataFrame(rates)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('datetime')
        df = df[['open', 'high', 'low', 'close', 'tick_volume']].copy()
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        
        # Add market hours
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_overlap'] = df.index.hour.isin(range(13, 16))
        df['is_active'] = df['is_london'] | df['is_ny']
        df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])
        
        return df
        
    def detect_market_regime(self, df, lookback=100):
        """
        Detect market regime: TREND or RANGE
        
        Uses:
        1. EMA crossover (trend determined by crossing)
        2. ATR (volatility)
        3. Directional movement
        4. Consecutive candles in one direction
        """
        if len(df) < lookback:
            return 'RANGE'  # Default to range
        
        # Get recent data
        recent_data = df.iloc[-lookback:]
        
        # 1. EMA CROSSOVER (main trend indicator)
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()
        
        # Current EMA position
        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]
        
        # Difference between EMAs in %
        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
        
        # If EMAs diverge > 0.3% = clear trend
        ema_trend = ema_diff_pct > 0.3
        
        # 2. ATR (volatility - should be above average)
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()
        
        high_volatility = atr > avg_atr * 1.05
        
        # 3. Directional movement (price moves in one direction)
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()
        
        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35
        
        # 4. Consecutive movements (candles in one direction)
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        total_moves = up_moves + down_moves
        
        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.15
        
        # 5. Consecutive higher highs / lower lows
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
        
        # TREND if 3+ signals out of 5
        is_trend = trend_signals >= 3
        
        return 'TREND' if is_trend else 'RANGE'
    
    def analyze_market(self):
        """Analyze market and get signals with adaptive TP levels"""
        try:
            # Get data (no verbose logging to improve speed)
            df = self.get_market_data()
            if df is None:
                return None

            # Detect market regime
            self.current_regime = self.detect_market_regime(df)

            # Run strategy
            result = self.strategy.run_strategy(df)

            # Get last signal (most recent)
            signals = result[result['signal'] != 0]

            if len(signals) == 0:
                return None
                
            # ONLY CHECK THE MOST RECENT CLOSED CANDLE (not historical signals)
            # This ensures we only trade on fresh signals, not old ones
            last_signal = signals.iloc[-1]
            last_signal_time = signals.index[-1]
            current_time = df.index[-1]

            # Signal must be from the LAST COMPLETED CANDLE ONLY
            # If signal is older than 1.5 hours, it's from a previous candle - ignore it
            time_diff_hours = (current_time - last_signal_time).total_seconds() / 3600

            if time_diff_hours > 1.5:  # More than 1.5 hours old = not from last closed candle
                return None

            # Adjust TP based on market regime
            if self.current_regime == 'TREND':
                tp1_distance = self.trend_tp1
                tp2_distance = self.trend_tp2
                tp3_distance = self.trend_tp3
            else:
                tp1_distance = self.range_tp1
                tp2_distance = self.range_tp2
                tp3_distance = self.range_tp3

            # Calculate all 3 TP levels
            entry = last_signal['entry_price']

            # Calculate SL based on settings
            if self.use_regime_based_sl:
                # Use regime-based fixed SL
                sl_distance = self.trend_sl_points if self.current_regime == 'TREND' else self.range_sl_points
                if last_signal['signal'] == 1:  # LONG
                    sl = entry - sl_distance
                else:  # SHORT
                    sl = entry + sl_distance
            else:
                # Use strategy-calculated SL
                sl = last_signal['stop_loss']

            if last_signal['signal'] == 1:  # LONG
                tp1 = entry + tp1_distance
                tp2 = entry + tp2_distance
                tp3 = entry + tp3_distance
            else:  # SHORT
                tp1 = entry - tp1_distance
                tp2 = entry - tp2_distance
                tp3 = entry - tp3_distance

            # Validate SL/TP values
            if sl <= 0:
                print(f"\n   ❌ Invalid SL: ${sl:.2f} (must be positive)")
                print(f"      Entry: ${entry:.2f}, Strategy SL: ${last_signal['stop_loss']:.2f}")
                print(f"      Signal: {last_signal['signal']} ({'LONG' if last_signal['signal'] == 1 else 'SHORT'})")
                print(f"      Regime: {last_signal.get('regime', 'UNKNOWN')}")
                print(f"      Use regime-based SL: {self.use_regime_based_sl}")
                print(f"      Pattern: {last_signal.get('pattern', 'UNKNOWN')}")
                print(f"      Signal type: {last_signal.get('signal_type', 'UNKNOWN')}")
                print(f"\n   ⚠️  This signal was rejected by validation")
                print(f"      The strategy may have a bug in SL calculation")
                if self.use_regime_based_sl:
                    sl_setting = self.trend_sl_points if last_signal.get('regime') == 'TREND' else self.range_sl_points
                    print(f"      Regime SL setting: {sl_setting} points")
                return None

            # For LONG: SL should be below entry, TP above
            # For SHORT: SL should be above entry, TP below
            if last_signal['signal'] == 1:  # LONG
                if sl >= entry:
                    print(f"\n   ❌ Invalid LONG setup: SL (${sl:.2f}) >= Entry (${entry:.2f})")
                    return None
                if tp1 <= entry:
                    print(f"\n   ❌ Invalid LONG setup: TP1 (${tp1:.2f}) <= Entry (${entry:.2f})")
                    return None
            else:  # SHORT
                if sl <= entry:
                    print(f"\n   ❌ Invalid SHORT setup: SL (${sl:.2f}) <= Entry (${entry:.2f})")
                    return None
                if tp1 >= entry:
                    print(f"\n   ❌ Invalid SHORT setup: TP1 (${tp1:.2f}) >= Entry (${entry:.2f})")
                    return None

            # Only print signal details when signal is found (not on every check)
            direction = "LONG" if last_signal['signal'] == 1 else "SHORT"
            print(f"\n   ✅ SIGNAL FOUND!")
            print(f"      {direction} | {self.current_regime} | Entry: ${entry:.2f}")
            print(f"      SL: ${sl:.2f} | TP1/2/3: ${tp1:.2f}/${tp2:.2f}/${tp3:.2f}")

            return {
                'direction': last_signal['signal'],
                'entry': entry,
                'sl': sl,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'tp1_distance': tp1_distance,
                'tp2_distance': tp2_distance,
                'tp3_distance': tp3_distance,
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
        if not self.mt5_connected:
            return 0.0
            
        account_info = mt5.account_info()
        if account_info is None:
            return 0.0
            
        balance = account_info.balance
        risk_amount = balance * (self.risk_percent / 100.0)
        
        # Risk per lot (in account currency)
        risk_per_point = abs(entry - sl)
        
        # For XAUUSD, 1 lot = 100 oz, point value depends on broker
        # Typical: 1 point = $100 for 1 lot
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            return 0.01  # Fallback
            
        # Calculate lot size
        point_value = 100.0  # Approx for gold
        lot_size = risk_amount / (risk_per_point * point_value)
        
        # Round to 0.01
        lot_size = round(lot_size, 2)
        
        # Min/max lot size
        lot_size = max(symbol_info.volume_min, lot_size)
        lot_size = min(symbol_info.volume_max, lot_size)
        
        return lot_size
        
    def get_open_positions(self):
        """Get open positions for symbol"""
        if not self.mt5_connected:
            return []
            
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return []
            
        return list(positions)
        
    def open_position(self, signal):
        """Open position(s) with TP/SL - supports single and 3-position modes"""
        if self.use_3_position_mode:
            return self._open_3_positions(signal)
        else:
            return self._open_single_position(signal)

    def _open_single_position(self, signal):
        """Open single position with TP2 as target (original simple logic)"""
        direction_str = "BUY" if signal['direction'] == 1 else "SELL"

        print(f"\n{'='*60}")
        print(f"📈 OPENING {direction_str} POSITION")
        print(f"{'='*60}")

        # Calculate position size
        if self.total_position_size is not None:
            # Use fixed position size from settings
            lot_size = self.total_position_size
            print(f"   Lot size (fixed): {lot_size}")
        else:
            # Calculate based on risk
            lot_size = self.calculate_position_size(signal['entry'], signal['sl'])
            print(f"   Lot size (risk-based): {lot_size}")

        if self.dry_run:
            print(f"\n🧪 DRY RUN: Opening simulated {direction_str} position:")
            print(f"   Symbol: {self.symbol}")
            print(f"   Lot: {lot_size}")
            print(f"   Entry: {signal['entry']:.2f}")
            print(f"   SL: {signal['sl']:.2f}")
            print(f"   TP2: {signal['tp2']:.2f} ({signal['tp2_distance']}p)")

            # Create simulated ticket number with timestamp
            simulated_ticket = int(time.time() * 1000)

            # Log position to tracker and database
            position_type = 'BUY' if signal['direction'] == 1 else 'SELL'
            regime = signal.get('regime', 'UNKNOWN')
            regime_code = "T" if regime == 'TREND' else "R"

            self._log_position_opened(
                ticket=simulated_ticket,
                position_type=position_type,
                volume=lot_size,
                entry_price=signal['entry'],
                sl=signal['sl'],
                tp=signal['tp2'],
                regime=regime,
                comment=f"V3_{regime_code}"
            )

            print(f"   ✅ Simulated position logged: DRY-{simulated_ticket}")
            print(f"\n🧪 DRY RUN: Simulated position created and tracked")
            return True

        # Get current price
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"❌ Failed to get current price")
            return False

        price = tick.ask if signal['direction'] == 1 else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if signal['direction'] == 1 else mt5.ORDER_TYPE_SELL
        regime = signal.get('regime', 'UNKNOWN')
        regime_code = "T" if regime == 'TREND' else "R"

        # Create request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": signal['sl'],
            "tp": signal['tp2'],  # Use TP2 as main target
            "deviation": 20,
            "magic": 234000,
            "comment": f"V3_{regime_code}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_mode(),
        }

        # Send order
        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Order failed: {result.comment if result else 'No result'}")
            return False

        print(f"   ✅ Order placed!")
        print(f"      Order: #{result.order}")
        print(f"      Lot: {lot_size}")
        print(f"      Entry: {result.price:.2f}")
        print(f"      TP: {signal['tp2']:.2f}")

        # Log position
        position_type = 'BUY' if signal['direction'] == 1 else 'SELL'
        self._log_position_opened(
            ticket=result.order,
            position_type=position_type,
            volume=lot_size,
            entry_price=result.price,
            sl=signal['sl'],
            tp=signal['tp2'],
            regime=regime,
            comment=f"V3_{regime_code}"
        )

        # Send Telegram notification
        if self.telegram_bot:
            message = f"🤖 <b>Position Opened</b>\n\n"
            message += f"Direction: {direction_str}\n"
            message += f"Market Regime: {regime}\n"
            message += f"Symbol: {self.symbol}\n"
            message += f"Lot: {lot_size}\n"
            message += f"Entry: ${result.price:.2f}\n"
            message += f"SL: ${signal['sl']:.2f}\n"
            message += f"TP: ${signal['tp2']:.2f}\n"
            message += f"Risk: {self.risk_percent}%"
            try:
                self.send_telegram(message)
            except Exception as e:
                print(f"⚠️  Failed to send Telegram notification: {e}")

        return True

    def _open_3_positions(self, signal):
        """Open 3 independent positions with different TP levels and trailing (Phase 2)"""
        direction_str = "BUY" if signal['direction'] == 1 else "SELL"
        group_id = str(uuid.uuid4())

        print(f"\n{'='*60}")
        print(f"📈 OPENING 3-POSITION {direction_str} GROUP")
        print(f"{'='*60}")
        print(f"   Group ID: {group_id}")
        
        # Check max positions (need room for 3 positions)
        open_positions = self.get_open_positions()
        if len(open_positions) + 3 > self.max_positions:
            print(f"⚠️  Not enough room for 3 positions (need {3}, have {self.max_positions - len(open_positions)} slots)")
            return False
            
        # Calculate total lot size
        if self.total_position_size is not None:
            # Use fixed position size from settings
            total_lot_size = self.total_position_size
            print(f"   Using fixed position size: {total_lot_size} lot")
        else:
            # Calculate based on risk
            total_lot_size = self.calculate_position_size(signal['entry'], signal['sl'])
            print(f"   Calculated position size (risk-based): {total_lot_size} lot")
        
        # Prepare common parameters
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Symbol info not found")
            return False
        
        # Split into 3 parts: 33%, 33%, 34%
        lot1 = round(total_lot_size * 0.33, 2)
        lot2 = round(total_lot_size * 0.33, 2)
        lot3 = round(total_lot_size * 0.34, 2)
        
        # Check if ANY lot size is below minimum - reject the trade
        min_lot = symbol_info.volume_min
        if lot1 < min_lot or lot2 < min_lot or lot3 < min_lot:
            print(f"\n{'='*60}")
            print(f"❌ INSUFFICIENT POSITION SIZE FOR 3-POSITION MODE")
            print(f"{'='*60}")
            print(f"   Total position size: {total_lot_size} lot")
            print(f"   Calculated positions:")
            print(f"      Position 1 (TP1): {lot1} lot")
            print(f"      Position 2 (TP2): {lot2} lot")
            print(f"      Position 3 (TP3): {lot3} lot")
            print(f"   Broker minimum: {min_lot} lot per position")
            print(f"\n   ⚠️  REQUIRED ACTION:")
            print(f"   • Minimum total position size needed: {min_lot * 3} lot")
            print(f"   • Current total position size: {total_lot_size} lot")
            print(f"   • Please increase position size in bot settings")
            print(f"   • Or disable 3-position mode and use single position")
            print(f"{'='*60}\n")
            return False
        
        print(f"   Total lot size: {total_lot_size}")
        print(f"   Position 1 (TP1): {lot1} lot")
        print(f"   Position 2 (TP2): {lot2} lot")
        print(f"   Position 3 (TP3): {lot3} lot")
        
        if self.dry_run:
            print(f"\n🧪 DRY RUN: Opening simulated 3 {direction_str} positions:")
            print(f"   Group ID: {group_id}")
            print(f"   Entry: {signal['entry']:.2f}")
            print(f"   SL: {signal['sl']:.2f}")
            print(f"   Position 1: {lot1} lot, TP1: {signal['tp1']:.2f} ({signal['tp1_distance']}p)")
            print(f"   Position 2: {lot2} lot, TP2: {signal['tp2']:.2f} ({signal['tp2_distance']}p)")
            print(f"   Position 3: {lot3} lot, TP3: {signal['tp3']:.2f} ({signal['tp3_distance']}p)")
            print(f"   Total risk: {self.risk_percent}%")

            # Generate simulated positions and log them
            regime = signal.get('regime', 'UNKNOWN')
            regime_code = "T" if regime == 'TREND' else "R"
            position_type = 'BUY' if signal['direction'] == 1 else 'SELL'

            tp_levels = [
                (signal['tp1'], lot1, 'TP1', signal['tp1_distance'], 1),
                (signal['tp2'], lot2, 'TP2', signal['tp2_distance'], 2),
                (signal['tp3'], lot3, 'TP3', signal['tp3_distance'], 3)
            ]

            for tp_price, lot_size, tp_name, tp_distance, pos_num in tp_levels:
                # Create simulated ticket number with timestamp
                simulated_ticket = int(time.time() * 1000) + pos_num

                # Log position to tracker and database
                self._log_position_opened(
                    ticket=simulated_ticket,
                    position_type=position_type,
                    volume=lot_size,
                    entry_price=signal['entry'],
                    sl=signal['sl'],
                    tp=tp_price,
                    regime=regime,
                    comment=f"V3_{regime_code}_P{pos_num}/3",
                    position_group_id=group_id,
                    position_num=pos_num
                )

                print(f"   ✅ Simulated {tp_name} position logged: DRY-{simulated_ticket}")
                time.sleep(0.1)  # Small delay between simulated orders

            # Save PositionGroup to database for dry-run too
            if self.use_database and self.db:
                try:
                    PositionGroup = self._get_position_group_model()
                    if PositionGroup:
                        new_group = PositionGroup(
                            group_id=group_id,
                            bot_id=self.bot_id,
                            tp1_hit=False,
                            entry_price=signal['entry'],
                            max_price=signal['entry'],
                            min_price=signal['entry'],
                            trade_type=direction_str,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        self.db.save_position_group(new_group)
                        print(f"✅ Position group saved to database (dry-run): {group_id[:8]}")
                except Exception as e:
                    print(f"⚠️  Could not save position group to DB: {e}")

            print(f"\n🧪 DRY RUN: 3 simulated positions created and tracked")
            return True

        # Get current price
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"❌ Failed to get current price")
            return False
            
        price = tick.ask if signal['direction'] == 1 else tick.bid
        regime_code = "T" if signal.get('regime') == 'TREND' else "R"
        order_type = mt5.ORDER_TYPE_BUY if signal['direction'] == 1 else mt5.ORDER_TYPE_SELL
        
        # Open 3 positions
        positions_opened = []
        tp_levels = [
            (signal['tp1'], lot1, 'TP1', signal['tp1_distance'], 1),
            (signal['tp2'], lot2, 'TP2', signal['tp2_distance'], 2),
            (signal['tp3'], lot3, 'TP3', signal['tp3_distance'], 3)
        ]

        for tp_price, lot_size, tp_name, tp_distance, pos_num in tp_levels:
            # Create request (lot sizes already validated above)
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "sl": signal['sl'],
                "tp": tp_price,
                "deviation": 20,
                "magic": 234000,
                "comment": f"V3_{regime_code}_{tp_name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self._get_filling_mode(),
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                print(f"   ❌ {tp_name} order failed: No result from broker")
                print(f"      Check: MT5 connection, symbol availability, trading permissions")
                continue

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"   ❌ {tp_name} order failed!")
                print(f"      Error code: {result.retcode}")
                print(f"      Message: {result.comment}")
                print(f"      Volume: {lot_size} lot, Price: ${price:.2f}")
                continue
                
            print(f"   ✅ {tp_name} position opened!")
            print(f"      Order: #{result.order}")
            print(f"      Lot: {lot_size}")
            print(f"      TP: {tp_price:.2f} ({tp_distance}p)")
            
            # Log position
            position_type = 'BUY' if signal['direction'] == 1 else 'SELL'
            regime = signal.get('regime', 'UNKNOWN')
            self._log_position_opened(
                ticket=result.order,
                position_type=position_type,
                volume=lot_size,
                entry_price=result.price,
                sl=signal['sl'],
                tp=tp_price,
                regime=regime,
                comment=f"V3_{regime_code}_P{pos_num}/3",
                position_group_id=group_id,
                position_num=pos_num
            )

            positions_opened.append((result.order, tp_name, tp_price))
            time.sleep(0.2)  # Small delay between orders
        
        if len(positions_opened) == 0:
            print(f"\n❌ Failed to open any positions!")
            print(f"   Possible reasons:")
            print(f"   - Incorrect filling mode (check broker requirements)")
            print(f"   - Insufficient margin")
            print(f"   - Symbol not available for trading")
            print(f"   - Market closed")
            print(f"   - MT5 connection issue")
            return False
        
        print(f"\n✅ Successfully opened {len(positions_opened)}/3 positions!")
        
        # Save PositionGroup to database (CRITICAL FIX: Create position group record)
        if self.use_database and self.db:
            try:
                PositionGroup = self._get_position_group_model()
                if PositionGroup:
                    new_group = PositionGroup(
                        group_id=group_id,
                        bot_id=self.bot_id,
                        tp1_hit=False,
                        entry_price=signal['entry'],
                        max_price=signal['entry'],
                        min_price=signal['entry'],
                        trade_type=direction_str,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    self.db.save_position_group(new_group)
                    print(f"✅ Position group saved to database: {group_id[:8]}")
            except Exception as e:
                print(f"⚠️  Failed to save position group to database: {e}")
        
        # Send Telegram notification
        if self.telegram_bot:
            import asyncio
            regime = signal.get('regime', 'UNKNOWN')
            message = f"🤖 <b>3 Positions Opened (Multi-TP)</b>\n\n"
            message += f"Direction: {direction_str}\n"
            message += f"Market Regime: {regime}\n"
            message += f"Entry: ~{price:.2f}\n"
            message += f"SL: {signal['sl']:.2f}\n\n"
            message += f"<b>Take Profits:</b>\n"
            for ticket, tp_name, tp_price in positions_opened:
                message += f"  {tp_name}: ${tp_price:.2f} (#{ticket})\n"
            message += f"\nTotal risk: {self.risk_percent}%"
            self.send_telegram(message)
            
        return True
    
    def generate_report(self):
        """Generate trading report from CSV log"""
        if not os.path.exists(self.trades_file):
            print("❌ No trade log file found")
            return
        
        df = pd.read_csv(self.trades_file)
        
        if len(df) == 0:
            print("📊 No trades recorded yet")
            return
        
        print(f"\n{'='*80}")
        print("📊 TRADING REPORT")
        print(f"{'='*80}")
        print(f"Total trades: {len(df)}")
        
        if 'Status' in df.columns and 'Profit' in df.columns:
            completed = df[df['Status'].isin(['CLOSED', 'TP', 'SL'])]
            if len(completed) > 0:
                wins = completed[completed['Profit'] > 0]
                losses = completed[completed['Profit'] < 0]
                
                print(f"\n💰 P&L Summary:")
                print(f"   Total P&L: ${completed['Profit'].sum():.2f}")
                print(f"   Wins: {len(wins)} ({len(wins)/len(completed)*100:.1f}%)")
                print(f"   Losses: {len(losses)} ({len(losses)/len(completed)*100:.1f}%)")
                
                if len(wins) > 0:
                    print(f"   Avg Win: ${wins['Profit'].mean():.2f}")
                    print(f"   Max Win: ${wins['Profit'].max():.2f}")
                
                if len(losses) > 0:
                    print(f"   Avg Loss: ${losses['Profit'].mean():.2f}")
                    print(f"   Max Loss: ${losses['Profit'].min():.2f}")
                
                if len(losses) > 0 and abs(losses['Profit'].sum()) > 0:
                    pf = abs(wins['Profit'].sum()) / abs(losses['Profit'].sum())
                    print(f"   Profit Factor: {pf:.2f}")
        
        if 'Market_Regime' in df.columns:
            print(f"\n📊 By Market Regime:")
            for regime in df['Market_Regime'].unique():
                regime_trades = df[df['Market_Regime'] == regime]
                if len(regime_trades) > 0:
                    regime_profit = regime_trades['Profit'].sum() if 'Profit' in df.columns else 0
                    print(f"   {regime}: {len(regime_trades)} trades, ${regime_profit:.2f}")
        
        if 'Duration_Hours' in df.columns:
            completed = df[df['Duration_Hours'].notna()]
            if len(completed) > 0:
                print(f"\n⏱️  Duration:")
                print(f"   Avg: {completed['Duration_Hours'].mean():.1f}h")
                print(f"   Min: {completed['Duration_Hours'].min():.1f}h")
                print(f"   Max: {completed['Duration_Hours'].max():.1f}h")
        
        print(f"\n📁 Full log: {self.trades_file}")
        print(f"{'='*80}\n")
        
    def _wait_until_next_hour(self):
        """Wait until the next full hour (01:00, 02:00, etc.)
        While waiting, monitor positions every 10 seconds for TP hits"""
        now = datetime.now()
        
        # Calculate next hour
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_hour - now).total_seconds()
        
        if wait_seconds > 0:
            print(f"\n⏰ Waiting until next hour: {next_hour.strftime('%H:%M:%S')}")
            print(f"   Time now: {now.strftime('%H:%M:%S')}")
            print(f"   Wait time: {int(wait_seconds/60)} min {int(wait_seconds%60)} sec")
            print(f"   🎯 Real-time TP/SL monitoring: Active (checking every 10s, bar high/low)")
            
            # Monitor positions while waiting
            monitoring_interval = 10  # Check every 10 seconds
            elapsed = 0
            
            while elapsed < wait_seconds:
                # Sleep for monitoring interval or remaining time
                sleep_time = min(monitoring_interval, wait_seconds - elapsed)
                time.sleep(sleep_time)
                elapsed += sleep_time
                
                # Sync positions with exchange first
                self._sync_positions_with_exchange()
                
                # Check TP/SL levels in real-time
                self._check_tp_sl_realtime()
                
                # Also check for closed positions
                self._check_closed_positions()
            
    def run(self):
        """Main bot loop with resilience features"""
        print(f"\n{'='*80}")
        print(f"🤖 BOT STARTING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # Detailed startup logging
        print("📡 Step 1/5: Connecting to MT5...")
        start_time = time.time()
        if not self.connect_mt5():
            print(f"❌ Failed after {time.time() - start_time:.1f}s")
            return
        print(f"✅ Connected in {time.time() - start_time:.1f}s\n")
        
        print("💾 Step 2/5: Verifying database connection...")
        start_time = time.time()
        if self.use_database and not self.db:
            print(f"⚠️  Database not available, continuing without it")
        print(f"✅ Database ready in {time.time() - start_time:.1f}s\n")
        
        print("📊 Step 3/5: Loading initial market data...")
        start_time = time.time()
        
        def _fetch_initial_data():
            rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 200)
            if rates is None or len(rates) == 0:
                raise Exception("No data received")
            return rates
        
        rates = retry_with_timeout(
            func=_fetch_initial_data,
            max_attempts=3,
            retry_interval=10,
            timeout_seconds=20,
            description=f"Download {self.symbol} data"
        )
        
        if rates is None:
            print(f"❌ Failed to download initial data after 3 attempts")
            return
        print(f"✅ Downloaded {len(rates)} bars in {time.time() - start_time:.1f}s\n")
        
        print("🛡️  Step 4/5: Starting watchdog...")
        self.watchdog = BotWatchdog(timeout=300, check_interval=30)
        self.watchdog.start()
        print()
        
        print("🎯 Step 5/5: Restoring positions from database...")
        self._restore_positions_from_database()
        
        # Show final configuration
        print(f"\n📋 Configuration:")
        print(f"   Symbol: {self.symbol}")
        print(f"   Timeframe: H1")
        print(f"   Strategy: V3 Adaptive (TREND/RANGE detection)")
        print(f"   Check interval: Every hour on the hour")
        print(f"   Risk per trade: {self.risk_percent}%")
        print(f"   Max positions: {self.max_positions}")
        print(f"   Mode: {'🧪 DRY RUN (TEST)' if self.dry_run else '🚀 LIVE TRADING'}")
        print()
        
        print(f"{'='*80}")
        print(f"✅ BOT FULLY STARTED - Ready to trade!")
        print(f"{'='*80}\n")
        
        if self.dry_run:
            print("🧪 DRY RUN MODE: All trades will be simulated only\n")
        else:
            print("🚀 LIVE TRADING MODE: Real trades will be executed!\n")
        
        # Send startup notification to Telegram
        if self.telegram_bot and self.telegram_chat_id:
            startup_message = f"""
🤖 <b>BOT STARTED</b>

📊 <b>Configuration:</b>
Symbol: {self.symbol}
Timeframe: H1
Strategy: V3 Adaptive (TREND/RANGE)
Risk per trade: {self.risk_percent}%
Max positions: {self.max_positions}
Mode: {'🧪 DRY RUN (TEST)' if self.dry_run else '🚀 LIVE TRADING'}

🎯 <b>TP Levels:</b>
TREND: {self.trend_tp1}p / {self.trend_tp2}p / {self.trend_tp3}p
RANGE: {self.range_tp1}p / {self.range_tp2}p / {self.range_tp3}p

⏰ <b>Started at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ Bot is now active and monitoring the market!
"""
            try:
                self.send_telegram(startup_message)
                print("📱 Startup notification sent to Telegram")
            except Exception as e:
                print(f"⚠️  Failed to send startup notification: {e}")
        
        # Wait until the next hour before starting
        print("⏰ Bot will start checking at the next full hour...")
        self._wait_until_next_hour()
        
        iteration = 0
        
        try:
            while self.running:  # ✅ Check running flag instead of while True
                self.watchdog.heartbeat()  # Send heartbeat at start of iteration
                iteration += 1
                
                print(f"\n{'='*80}")
                print(f"🔄 Iteration #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*80}")
                
                # Check connection
                if not self.mt5_connected:
                    self.watchdog.heartbeat()
                    print("❌ MT5 disconnected! Attempting to reconnect...")
                    if not self._attempt_reconnect():
                        print("❌ Reconnection failed. Will retry next iteration...")
                        continue

                self.watchdog.heartbeat()

                # Periodic heartbeat check
                self._check_heartbeat()
                
                # Check current positions
                open_positions = self.get_open_positions()
                
                # Sync positions with exchange first
                self._sync_positions_with_exchange()
                
                # Check TP/SL levels in real-time
                self._check_tp_sl_realtime()
                
                # Check for closed positions and log them
                self._check_closed_positions()
                
                print(f"📊 Open positions: {len(open_positions)}/{self.max_positions}")
                
                if len(open_positions) > 0:
                    for i, pos in enumerate(open_positions, 1):
                        direction = "LONG" if pos.type == mt5.ORDER_TYPE_BUY else "SHORT"
                        profit = pos.profit if pos.profit is not None else 0.0
                        ticket = pos.ticket
                        
                        # Get status from tracker if available
                        status = 'OPEN'
                        if ticket in self.positions_tracker:
                            status = self.positions_tracker[ticket].get('status', 'OPEN')
                        
                        # Calculate profit percentage
                        profit_pct = 0.0
                        if pos.price_open and pos.price_open > 0:
                            current_tick = mt5.symbol_info_tick(self.symbol)
                            if current_tick:
                                current_price = current_tick.bid if pos.type == mt5.ORDER_TYPE_BUY else current_tick.ask
                                if pos.type == mt5.ORDER_TYPE_BUY:
                                    profit_pct = ((current_price - pos.price_open) / pos.price_open) * 100
                                else:
                                    profit_pct = ((pos.price_open - current_price) / pos.price_open) * 100
                        
                        print(f"   Position #{i}: {direction} @ {pos.price_open:.2f}, "
                              f"SL={pos.sl:.2f}, TP={pos.tp:.2f}, "
                              f"P&L: ${profit:.2f} ({profit_pct:+.2f}%), "
                              f"Status: {status}")
                
                # Analyze market
                print(f"\n🔍 Analyzing market...")
                signal = self.analyze_market()
                
                if signal:
                    print(f"\n✅ Signal detected!")
                    
                    # Check if already have position in same direction
                    has_same_direction = False
                    for pos in open_positions:
                        pos_direction = 1 if pos.type == mt5.ORDER_TYPE_BUY else -1
                        if pos_direction == signal['direction']:
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
                account_info = mt5.account_info()
                if account_info:
                    print(f"\n💰 Account status:")
                    print(f"   Balance: ${account_info.balance:.2f}")
                    print(f"   Equity: ${account_info.equity:.2f}")
                    print(f"   Margin: ${account_info.margin:.2f}")
                    profit_pct = ((account_info.equity - account_info.balance) / account_info.balance * 100) if account_info.balance > 0 else 0
                    print(f"   Floating P&L: ${account_info.equity - account_info.balance:.2f} ({profit_pct:+.2f}%)")
                    
                # Wait until next full hour
                print(f"\n{'='*80}")
                print(f"💤 Waiting until next full hour...")
                print(f"   Press Ctrl+C to stop the bot")
                print(f"{'='*80}\n")
                
                # Wait until next hour (01:00, 02:00, 03:00, etc.)
                self._wait_until_next_hour()
                
        except KeyboardInterrupt:
            print("\n\n{'='*80}")
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
⏹️ <b>BOT STOPPED</b>

📊 <b>Summary:</b>
Total iterations: {iteration}
Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{"⚠️ <b>WARNING:</b> " + str(len(open_positions)) + " position(s) still open!" if len(open_positions) > 0 else "✅ No open positions"}

🛑 Bot has been stopped by user.
"""
                try:
                    self.send_telegram(shutdown_message)
                    print("📱 Shutdown notification sent to Telegram")
                except Exception as e:
                    print(f"⚠️  Failed to send shutdown notification: {e}")
            
            # Generate trading report
            self.generate_report()
                
            print(f"{'='*80}\n")
        except Exception as e:
            print(f"\n\n❌ BOT ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Always cleanup resources
            self._cleanup()
