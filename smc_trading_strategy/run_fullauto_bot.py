"""
Full Auto Trading Bot - Live trading with MT5
Automatically detects signals, logs trades, monitors positions, and sends notifications
"""

import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import MetaTrader5 as mt5
import threading

from pattern_recognition_strategy import PatternRecognitionStrategy
from trade_logger import TradeLogger
from mt5_position_monitor import MT5PositionMonitor
from telegram_notifier import TelegramNotifier
from mt5_data_downloader import MT5DataDownloader

# Constants
SIGNAL_FRESHNESS_BUFFER_SECONDS = 3600  # Allow 1 hour buffer for signal freshness check
NOTIFICATION_BUFFER_SECONDS = 5  # Buffer for detecting recent TP hits


class FullAutoTradingBot:
    """Full auto trading bot with live MT5 integration"""

    def __init__(self, 
                 symbol='XAUUSD',
                 timeframe=mt5.TIMEFRAME_H1,
                 check_interval=3600,
                 monitor_interval=30,
                 tp1=30, tp2=50, tp3=80,
                 close_pct1=0.5, close_pct2=0.3, close_pct3=0.2,
                 telegram_token=None,
                 telegram_chat_id=None,
                 auto_trade=False,
                 risk_percent=1.0,
                 enable_trailing_stop=True,
                 trailing_stop_distance=20):
        """
        Initialize full auto trading bot

        Args:
            symbol: Trading symbol (default: XAUUSD)
            timeframe: MT5 timeframe (default: H1)
            check_interval: Signal check interval in seconds (default: 3600 = 1 hour)
            monitor_interval: Position monitoring interval in seconds (default: 30)
            tp1, tp2, tp3: Take profit levels in points
            close_pct1, close_pct2, close_pct3: Close percentages for each TP
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            auto_trade: If True, automatically opens trades (default: False)
            risk_percent: Risk per trade as % of account balance (default: 1.0%)
            enable_trailing_stop: Enable trailing stop after TP1 (default: True)
            trailing_stop_distance: Trailing stop distance in points (default: 20)
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.check_interval = check_interval
        self.monitor_interval = monitor_interval
        
        # TP configuration
        self.tp1 = tp1
        self.tp2 = tp2
        self.tp3 = tp3
        self.close_pct1 = close_pct1
        self.close_pct2 = close_pct2
        self.close_pct3 = close_pct3
        
        # Auto-trading configuration
        self.auto_trade = auto_trade
        self.risk_percent = risk_percent
        self.enable_trailing_stop = enable_trailing_stop
        self.trailing_stop_distance = trailing_stop_distance
        
        # Initialize components
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')
        self.logger = TradeLogger()
        self.monitor = MT5PositionMonitor(logger=self.logger, check_interval=monitor_interval)
        self.mt5_downloader = MT5DataDownloader(symbol=symbol, timeframe=timeframe)
        
        # Telegram notifications
        if telegram_token and telegram_chat_id:
            self.notifier = TelegramNotifier(telegram_token, telegram_chat_id)
            self.notifier.test_connection()
        else:
            self.notifier = None
            print("⚠️  Telegram notifications disabled")
        
        # State
        self.running = False
        self.last_signal_check = None
        self.monitor_thread = None
        self.trailing_stop_thread = None
        
        print("\n" + "="*70)
        print("🤖 FULL AUTO TRADING BOT INITIALIZED")
        print("="*70)
        print(f"Symbol: {symbol}")
        print(f"Timeframe: {self._timeframe_to_string(timeframe)}")
        print(f"Signal check: Every {check_interval}s ({check_interval/60:.0f} min)")
        print(f"Position monitoring: Every {monitor_interval}s")
        print(f"TP levels: {tp1}п/{tp2}п/{tp3}п")
        print(f"Close %: {close_pct1*100:.0f}%/{close_pct2*100:.0f}%/{close_pct3*100:.0f}%")
        if auto_trade:
            print(f"⚠️  AUTO-TRADE: ENABLED (Risk: {risk_percent}% per trade)")
            print(f"   Trailing Stop: {'ENABLED' if enable_trailing_stop else 'DISABLED'} ({trailing_stop_distance}п)")
        else:
            print(f"📊 Mode: MONITORING ONLY (no auto-trading)")
        print("="*70 + "\n")

    def _timeframe_to_string(self, timeframe):
        """Convert MT5 timeframe to string"""
        timeframes = {
            mt5.TIMEFRAME_M1: '1M',
            mt5.TIMEFRAME_M5: '5M',
            mt5.TIMEFRAME_M15: '15M',
            mt5.TIMEFRAME_M30: '30M',
            mt5.TIMEFRAME_H1: '1H',
            mt5.TIMEFRAME_H4: '4H',
            mt5.TIMEFRAME_D1: '1D'
        }
        return timeframes.get(timeframe, f'TF{timeframe}')

    def connect_mt5(self, login=None, password=None, server=None):
        """
        Connect to MT5 terminal

        Args:
            login: Account number (optional, from .env)
            password: Password (optional, from .env)
            server: Broker server (optional, from .env)

        Returns:
            bool: True if connected
        """
        print("🔌 Connecting to MT5...")
        
        if not self.mt5_downloader.connect(login=login, password=password, server=server):
            print("❌ Failed to connect MT5 downloader")
            return False
        
        if not self.monitor.connect_mt5(login=login, password=password, server=server):
            print("❌ Failed to connect MT5 monitor")
            return False
        
        print("✅ MT5 connected successfully\n")
        return True

    def disconnect_mt5(self):
        """Disconnect from MT5"""
        self.monitor.disconnect_mt5()
        mt5.shutdown()
        print("✅ Disconnected from MT5")

    def calculate_position_size(self, entry_price, sl_price):
        """
        Calculate position size based on risk percentage
        
        Args:
            entry_price: Entry price
            sl_price: Stop loss price
            
        Returns:
            float: Lot size
        """
        # Get account balance
        account_info = mt5.account_info()
        if account_info is None:
            print("❌ Failed to get account info")
            return 0.01  # Return minimum lot
        
        balance = account_info.balance
        risk_amount = balance * (self.risk_percent / 100)
        
        # Calculate risk in points
        risk_points = abs(entry_price - sl_price)
        
        # For XAUUSD, 1 lot = $100 per point typically
        # But let's get the actual contract size
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print("❌ Failed to get symbol info")
            return 0.01
        
        # Calculate lot size
        # risk_amount = lot_size * risk_points * contract_size
        lot_size = risk_amount / (risk_points * symbol_info.trade_contract_size / 100)
        
        # Round to symbol's volume step
        lot_step = symbol_info.volume_step
        lot_size = round(lot_size / lot_step) * lot_step
        
        # Ensure within min/max limits
        lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
        
        return lot_size

    def open_mt5_positions(self, signal_data, trade_id):
        """
        Open 3 positions in MT5 with different TP levels
        
        Args:
            signal_data: Signal information dict
            trade_id: Trade ID from logger
            
        Returns:
            list: List of tickets for opened positions
        """
        if not self.auto_trade:
            print("⚠️  Auto-trade disabled, skipping position opening")
            return []
        
        direction = signal_data['direction']
        entry_price = signal_data['entry_price']
        stop_loss = signal_data['stop_loss']
        tp1_price = signal_data['tp1_price']
        tp2_price = signal_data['tp2_price']
        tp3_price = signal_data['tp3_price']
        
        print(f"\n{'='*60}")
        print(f"💰 OPENING 3 MT5 POSITIONS")
        print(f"{'='*60}")
        
        # Calculate total lot size
        total_lot_size = self.calculate_position_size(entry_price, stop_loss)
        
        # Split into 3 parts based on close percentages
        lot1 = round(total_lot_size * self.close_pct1, 2)
        lot2 = round(total_lot_size * self.close_pct2, 2)
        lot3 = round(total_lot_size * self.close_pct3, 2)
        
        print(f"   Total lot size: {total_lot_size:.2f}")
        print(f"   Position 1 (TP1): {lot1:.2f} lot")
        print(f"   Position 2 (TP2): {lot2:.2f} lot")
        print(f"   Position 3 (TP3): {lot3:.2f} lot")
        
        # Get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Symbol info not found")
            return []
        
        # Get current price
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"❌ Failed to get current price")
            return []
        
        price = tick.ask if direction == 'LONG' else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if direction == 'LONG' else mt5.ORDER_TYPE_SELL
        
        # Open 3 positions
        opened_tickets = []
        tp_levels = [
            (tp1_price, lot1, 'TP1'),
            (tp2_price, lot2, 'TP2'),
            (tp3_price, lot3, 'TP3')
        ]
        
        for tp_price, lot_size, tp_name in tp_levels:
            # Ensure minimum lot size
            if lot_size < symbol_info.volume_min:
                print(f"   ⚠️  {tp_name}: lot size {lot_size} < minimum {symbol_info.volume_min}, adjusting")
                lot_size = symbol_info.volume_min
            
            # Create request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "sl": stop_loss,
                "tp": tp_price,
                "deviation": 20,
                "magic": 234000,
                "comment": f"AUTO_{tp_name}_{trade_id[:8]}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                print(f"   ❌ {tp_name} order failed: No result")
                continue
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"   ❌ {tp_name} order failed: {result.retcode} - {result.comment}")
                continue
            
            print(f"   ✅ {tp_name} position opened!")
            print(f"      Ticket: #{result.order}")
            print(f"      Lot: {lot_size:.2f}")
            print(f"      Entry: {result.price:.2f}")
            print(f"      TP: {tp_price:.2f}")
            
            opened_tickets.append(result.order)
        
        if len(opened_tickets) == 0:
            print(f"\n❌ Failed to open any positions!")
        else:
            print(f"\n✅ Successfully opened {len(opened_tickets)}/3 positions!")
        
        return opened_tickets

    def manage_trailing_stops(self):
        """
        Background thread to manage trailing stops for open positions
        Activates trailing stop after TP1 is hit
        """
        print(f"🔄 Trailing stop manager started")
        
        while self.running:
            try:
                time.sleep(self.monitor_interval)
                
                if not self.running or not self.enable_trailing_stop:
                    break
                
                # Get open positions from logger
                open_positions = self.logger.get_open_positions()
                
                for pos in open_positions:
                    # Only apply trailing stop if TP1 is hit
                    if not pos.get('tp1_hit', False):
                        continue
                    
                    ticket = pos.get('ticket')
                    if not ticket:
                        continue
                    
                    # Get current MT5 position
                    mt5_positions = mt5.positions_get(ticket=ticket)
                    if not mt5_positions or len(mt5_positions) == 0:
                        continue
                    
                    mt5_pos = mt5_positions[0]
                    current_price = mt5_pos.price_current
                    current_sl = mt5_pos.sl
                    entry_price = pos['entry_price']
                    direction = pos['direction']
                    
                    # Calculate new trailing stop
                    if direction == 'LONG':
                        # For LONG: SL should trail below current price
                        new_sl = current_price - self.trailing_stop_distance
                        # Only move SL up, never down
                        if new_sl > current_sl and new_sl > entry_price:
                            self._modify_position_sl(ticket, new_sl)
                    else:  # SHORT
                        # For SHORT: SL should trail above current price
                        new_sl = current_price + self.trailing_stop_distance
                        # Only move SL down, never up
                        if new_sl < current_sl and new_sl < entry_price:
                            self._modify_position_sl(ticket, new_sl)
                
            except Exception as e:
                print(f"❌ Error in trailing stop manager: {e}")
                import traceback
                traceback.print_exc()
        
        print("✅ Trailing stop manager stopped")

    def _modify_position_sl(self, ticket, new_sl):
        """
        Modify stop loss for a position
        
        Args:
            ticket: Position ticket
            new_sl: New stop loss price
        """
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   🔄 Trailing SL updated for #{ticket}: {new_sl:.2f}")
            return True
        else:
            if result:
                print(f"   ⚠️  Failed to update SL for #{ticket}: {result.comment}")
            return False

    def check_for_signals(self):
        """Check for new trading signals"""
        print(f"\n{'='*70}")
        print(f"🔍 CHECKING FOR SIGNALS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        try:
            # Download latest data
            df = self.mt5_downloader.get_realtime_data(period_hours=120)
            
            if df is None or len(df) == 0:
                print("❌ Failed to download data")
                return
            
            print(f"✅ Downloaded {len(df)} candles")
            print(f"   Latest: {df.index[-1]} | Price: {df['close'].iloc[-1]:.2f}")
            
            # Run strategy
            df_strategy = self.strategy.run_strategy(df.copy())
            
            # Get signals
            df_signals = df_strategy[df_strategy['signal'] != 0]
            
            if len(df_signals) == 0:
                print("📊 No signals found")
                return
            
            # Check last signal
            last_signal = df_signals.iloc[-1]
            last_signal_time = df_signals.index[-1]
            
            # Check if signal is new (within our check interval)
            if self.last_signal_check is not None:
                time_since_check = (datetime.now() - self.last_signal_check).total_seconds()
                signal_age = (df.index[-1] - last_signal_time).total_seconds()
                
                # Allow buffer for signal freshness check
                if signal_age > time_since_check + SIGNAL_FRESHNESS_BUFFER_SECONDS:
                    print(f"📊 Last signal is old ({signal_age/3600:.1f}h ago), ignoring")
                    return
            
            # New signal detected!
            print(f"\n🎯 NEW SIGNAL DETECTED!")
            print(f"   Time: {last_signal_time}")
            
            direction = 'LONG' if last_signal['signal'] == 1 else 'SHORT'
            entry_price = last_signal['entry_price']
            stop_loss = last_signal['stop_loss']
            
            print(f"   Direction: {direction}")
            print(f"   Entry: {entry_price:.2f}")
            print(f"   SL: {stop_loss:.2f}")
            
            # Calculate TP levels
            if direction == 'LONG':
                tp1_price = entry_price + self.tp1
                tp2_price = entry_price + self.tp2
                tp3_price = entry_price + self.tp3
            else:
                tp1_price = entry_price - self.tp1
                tp2_price = entry_price - self.tp2
                tp3_price = entry_price - self.tp3
            
            print(f"   TP1: {tp1_price:.2f} ({self.close_pct1*100:.0f}%)")
            print(f"   TP2: {tp2_price:.2f} ({self.close_pct2*100:.0f}%)")
            print(f"   TP3: {tp3_price:.2f} ({self.close_pct3*100:.0f}%)")
            
            # Log the trade entry
            trade_id = self.logger.log_entry({
                'direction': direction,
                'entry_price': entry_price,
                'entry_time': last_signal_time,
                'stop_loss': stop_loss,
                'tp1_price': tp1_price,
                'tp2_price': tp2_price,
                'tp3_price': tp3_price,
                'pattern': last_signal.get('pattern', 'N/A'),
                'close_pct1': self.close_pct1,
                'close_pct2': self.close_pct2,
                'close_pct3': self.close_pct3,
                'ticket': None  # Will be updated if MT5 positions are opened
            })
            
            print(f"\n✅ Signal logged with ID: {trade_id}")
            
            # Open MT5 positions if auto-trade is enabled
            if self.auto_trade:
                signal_for_trading = {
                    'direction': direction,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'tp1_price': tp1_price,
                    'tp2_price': tp2_price,
                    'tp3_price': tp3_price
                }
                
                tickets = self.open_mt5_positions(signal_for_trading, trade_id)
                
                if tickets:
                    # Update logged position with ticket numbers
                    # Note: We opened 3 positions, but logger tracks them as one "virtual" position
                    # The MT5 monitor will track individual MT5 positions
                    print(f"   📝 Opened MT5 tickets: {tickets}")
            
            # Send Telegram notification
            if self.notifier:
                self.notifier.send_entry_signal({
                    'direction': direction,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'tp1': tp1_price,
                    'tp2': tp2_price,
                    'tp3': tp3_price,
                    'pattern': last_signal.get('pattern', 'N/A'),
                    'timestamp': last_signal_time
                })
            
        except Exception as e:
            print(f"❌ Error checking signals: {e}")
            import traceback
            traceback.print_exc()
            
            if self.notifier:
                self.notifier.send_error(f"Error checking signals: {str(e)}")

    def monitor_positions_loop(self):
        """Background thread for monitoring positions"""
        print(f"🔄 Position monitoring thread started")
        
        while self.running:
            try:
                time.sleep(self.monitor_interval)
                
                if not self.running:
                    break
                
                # Get current open positions before checking
                positions_before = {pos['trade_id']: pos for pos in self.logger.get_open_positions()}
                
                # Check positions
                summary = self.monitor.monitor_positions_once()
                
                # Get positions after checking
                positions_after = {pos['trade_id']: pos for pos in self.logger.get_open_positions()}
                
                # Find positions that were closed (in before but not in after)
                closed_trade_ids = set(positions_before.keys()) - set(positions_after.keys())
                
                # Send notifications for closed positions
                if self.notifier and closed_trade_ids:
                    # Get closed trades from logger
                    closed_trades = self.logger.get_closed_trades()
                    
                    for trade_id in closed_trade_ids:
                        # Find the closed trade
                        closed_trade = next((t for t in closed_trades if t['trade_id'] == trade_id), None)
                        
                        if closed_trade:
                            # Calculate duration
                            try:
                                entry_time = datetime.strptime(closed_trade['entry_time'], '%Y-%m-%d %H:%M:%S')
                                exit_time = datetime.strptime(closed_trade['exit_time'], '%Y-%m-%d %H:%M:%S')
                                duration_hours = (exit_time - entry_time).total_seconds() / 3600
                            except:
                                duration_hours = 0
                            
                            # Send exit notification
                            self.notifier.send_exit_signal({
                                'direction': closed_trade['direction'],
                                'entry_price': closed_trade['entry_price'],
                                'exit_price': closed_trade['exit_price'],
                                'exit_type': closed_trade['exit_type'],
                                'pnl_pct': closed_trade['total_pnl_pct'],
                                'pnl_points': closed_trade['total_pnl_points'],
                                'duration_hours': duration_hours,
                                'timestamp': exit_time if 'exit_time' in locals() else datetime.now()
                            })
                
                # Send notifications for TP/SL hits
                if self.notifier and (summary['tp1_hits'] > 0 or summary['tp2_hits'] > 0 or 
                                     summary['tp3_hits'] > 0):
                    
                    # Get recent updates from logger
                    open_positions = self.logger.get_open_positions()
                    
                    # Send notifications for each TP hit
                    for pos in open_positions:
                        # Check if TP was just hit (in last monitor interval)
                        for tp_level in ['tp1', 'tp2', 'tp3']:
                            if pos.get(f'{tp_level}_hit', False):
                                hit_time_str = pos.get(f'{tp_level}_hit_time')
                                if hit_time_str:
                                    try:
                                        hit_time = datetime.strptime(hit_time_str, '%Y-%m-%d %H:%M:%S')
                                        time_since_hit = (datetime.now() - hit_time).total_seconds()
                                        
                                        # If hit in last monitoring interval, send notification
                                        if time_since_hit <= self.monitor_interval + NOTIFICATION_BUFFER_SECONDS:
                                            tp_num = tp_level[-1]  # '1', '2', or '3'
                                            tp_price = pos[f'{tp_level}_price']
                                            
                                            # Calculate partial profit
                                            close_pct = pos.get(f'close_pct{tp_num}', 0.33)
                                            if pos['direction'] == 'LONG':
                                                pnl_points = tp_price - pos['entry_price']
                                            else:
                                                pnl_points = pos['entry_price'] - tp_price
                                            
                                            pnl_pct = (pnl_points / pos['entry_price']) * 100 * close_pct
                                            
                                            self.notifier.send_partial_close({
                                                'direction': pos['direction'],
                                                'tp_level': f'TP{tp_num}',
                                                'tp_price': tp_price,
                                                'entry_price': pos['entry_price'],
                                                'close_pct': close_pct,
                                                'pnl_pct': pnl_pct,
                                                'pnl_points': pnl_points * close_pct,
                                                'position_remaining': pos['position_remaining'],
                                                'timestamp': hit_time
                                            })
                                    except:
                                        pass
                
            except Exception as e:
                print(f"❌ Error in monitoring thread: {e}")
                import traceback
                traceback.print_exc()
        
        print("✅ Position monitoring thread stopped")

    def run(self):
        """
        Main bot loop
        Checks for signals and monitors positions
        """
        self.running = True
        
        # Send startup notification
        if self.notifier:
            self.notifier.send_startup_message()
        
        # Start position monitoring in background thread
        self.monitor_thread = threading.Thread(target=self.monitor_positions_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start trailing stop manager if enabled
        if self.enable_trailing_stop and self.auto_trade:
            self.trailing_stop_thread = threading.Thread(target=self.manage_trailing_stops, daemon=True)
            self.trailing_stop_thread.start()
        
        print("\n" + "="*70)
        print("🚀 BOT STARTED - LIVE TRADING MODE")
        print("="*70)
        print("   Signal checking: Active")
        print("   Position monitoring: Active")
        if self.enable_trailing_stop and self.auto_trade:
            print("   Trailing stop: Active")
        print("   Press Ctrl+C to stop")
        print("="*70 + "\n")
        
        try:
            # Initial signal check
            self.check_for_signals()
            self.last_signal_check = datetime.now()
            
            # Main loop
            while self.running:
                # Sleep until next signal check
                time.sleep(self.check_interval)
                
                if not self.running:
                    break
                
                # Check for signals
                self.check_for_signals()
                self.last_signal_check = datetime.now()
                
                # Print statistics
                print("\n" + "-"*70)
                self.logger.print_statistics()
                print("-"*70)
        
        except KeyboardInterrupt:
            print("\n⚠️  Keyboard interrupt received")
        
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            
            if self.notifier:
                self.notifier.send_error(f"Fatal error: {str(e)}")
        
        finally:
            self.stop()

    def stop(self):
        """Stop the bot"""
        print("\n🛑 Stopping bot...")
        self.running = False
        
        # Wait for monitoring thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            print("   Waiting for monitoring thread...")
            self.monitor_thread.join(timeout=5)
        
        # Final statistics
        self.logger.print_statistics()
        
        print("✅ Bot stopped successfully")


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("🤖 FULL AUTO TRADING BOT")
    print("="*70 + "\n")
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration from .env
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    check_interval = int(os.getenv('CHECK_INTERVAL', 3600))
    monitor_interval = int(os.getenv('MONITOR_INTERVAL', 30))
    
    # MT5 credentials (optional)
    mt5_login = os.getenv('MT5_LOGIN')
    mt5_password = os.getenv('MT5_PASSWORD')
    mt5_server = os.getenv('MT5_SERVER')
    
    # TP configuration
    tp1 = int(os.getenv('TP1', 30))
    tp2 = int(os.getenv('TP2', 50))
    tp3 = int(os.getenv('TP3', 80))
    close_pct1 = float(os.getenv('CLOSE_PCT1', 0.5))
    close_pct2 = float(os.getenv('CLOSE_PCT2', 0.3))
    close_pct3 = float(os.getenv('CLOSE_PCT3', 0.2))
    
    # Auto-trading configuration
    auto_trade = os.getenv('AUTO_TRADE', 'false').lower() == 'true'
    risk_percent = float(os.getenv('RISK_PERCENT', 1.0))
    enable_trailing_stop = os.getenv('ENABLE_TRAILING_STOP', 'true').lower() == 'true'
    trailing_stop_distance = int(os.getenv('TRAILING_STOP_DISTANCE', 20))
    
    # Symbol and timeframe
    symbol = os.getenv('SYMBOL', 'XAUUSD')
    timeframe_str = os.getenv('TIMEFRAME', 'H1')
    
    # Convert timeframe string to MT5 constant
    timeframe_map = {
        'M1': mt5.TIMEFRAME_M1,
        'M5': mt5.TIMEFRAME_M5,
        'M15': mt5.TIMEFRAME_M15,
        'M30': mt5.TIMEFRAME_M30,
        'H1': mt5.TIMEFRAME_H1,
        'H4': mt5.TIMEFRAME_H4,
        'D1': mt5.TIMEFRAME_D1
    }
    timeframe = timeframe_map.get(timeframe_str, mt5.TIMEFRAME_H1)
    
    # Create bot
    bot = FullAutoTradingBot(
        symbol=symbol,
        timeframe=timeframe,
        check_interval=check_interval,
        monitor_interval=monitor_interval,
        tp1=tp1, tp2=tp2, tp3=tp3,
        close_pct1=close_pct1, close_pct2=close_pct2, close_pct3=close_pct3,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        auto_trade=auto_trade,
        risk_percent=risk_percent,
        enable_trailing_stop=enable_trailing_stop,
        trailing_stop_distance=trailing_stop_distance
    )
    
    # Connect to MT5
    if not bot.connect_mt5(login=mt5_login, password=mt5_password, server=mt5_server):
        print("❌ Failed to connect to MT5. Make sure MT5 is running.")
        return
    
    try:
        # Run bot
        bot.run()
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    
    finally:
        bot.disconnect_mt5()
        print("\n✅ Bot shutdown complete")


if __name__ == "__main__":
    # Check if running on Windows (MT5 only works on Windows)
    if sys.platform != 'win32':
        print("⚠️  WARNING: MT5 only works on Windows!")
        print("   This bot requires MetaTrader 5 to be installed.")
        print("   If you want to use paper trading instead, use paper_trading_mt5.py")
        sys.exit(1)
    
    main()
