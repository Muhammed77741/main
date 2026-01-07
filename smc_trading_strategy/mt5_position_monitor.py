"""
MT5 Position Monitor - Monitors open positions in MetaTrader 5
Checks position status every N seconds and detects TP/SL hits
"""

import time
from datetime import datetime
import MetaTrader5 as mt5
from trade_logger import TradeLogger


class MT5PositionMonitor:
    """Monitor MT5 positions and track TP/SL hits"""

    def __init__(self, logger=None, check_interval=30):
        """
        Initialize MT5 position monitor

        Args:
            logger: TradeLogger instance (optional)
            check_interval: How often to check positions in seconds (default: 30)
        """
        self.logger = logger if logger else TradeLogger()
        self.check_interval = check_interval
        self.running = False
        
        # Track position tickets to detect new/closed positions
        self.tracked_tickets = set()
        
        print(f"✅ MT5 Position Monitor initialized")
        print(f"   Check interval: {check_interval} seconds")

    def connect_mt5(self, login=None, password=None, server=None):
        """
        Connect to MT5 terminal

        Args:
            login: Account number (optional)
            password: Password (optional)
            server: Broker server (optional)

        Returns:
            bool: True if connected successfully
        """
        if not mt5.initialize():
            print(f"❌ MT5 initialization failed: {mt5.last_error()}")
            return False

        if login and password and server:
            authorized = mt5.login(login, password=password, server=server)
            if not authorized:
                print(f"❌ MT5 login failed: {mt5.last_error()}")
                return False
            print(f"✅ Connected to MT5 account: {login}")
        else:
            print(f"✅ Connected to MT5 terminal")

        # Display account info
        account_info = mt5.account_info()
        if account_info:
            print(f"   Account: {account_info.login}")
            print(f"   Balance: ${account_info.balance:.2f}")
            print(f"   Equity: ${account_info.equity:.2f}")

        return True

    def disconnect_mt5(self):
        """Disconnect from MT5"""
        mt5.shutdown()
        print("✅ Disconnected from MT5")

    def get_open_positions(self):
        """
        Get all open positions from MT5

        Returns:
            list: List of position dictionaries
        """
        positions = mt5.positions_get()
        
        if positions is None:
            print(f"⚠️  No positions found or error: {mt5.last_error()}")
            return []

        position_list = []
        for pos in positions:
            position_list.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'LONG' if pos.type == mt5.ORDER_TYPE_BUY else 'SHORT',
                'volume': pos.volume,
                'open_price': pos.price_open,
                'current_price': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'open_time': datetime.fromtimestamp(pos.time),
                'comment': pos.comment
            })

        return position_list

    def get_position_by_ticket(self, ticket):
        """
        Get specific position by ticket number

        Args:
            ticket: MT5 ticket number

        Returns:
            dict: Position data or None
        """
        positions = self.get_open_positions()
        for pos in positions:
            if pos['ticket'] == ticket:
                return pos
        return None

    def check_position_status(self, logged_position, mt5_position):
        """
        Check if position hit any TP or SL levels

        Args:
            logged_position: Position data from trade logger
            mt5_position: Current position data from MT5

        Returns:
            dict: Status updates (tp_hits, sl_hit)
        """
        updates = {
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'sl_hit': False
        }

        current_price = mt5_position['current_price']
        direction = logged_position['direction']
        
        # Check TP levels
        if direction == 'LONG':
            # For LONG positions, price needs to go UP to hit TPs
            if not logged_position.get('tp1_hit', False) and current_price >= logged_position['tp1_price']:
                updates['tp1_hit'] = True
            
            if not logged_position.get('tp2_hit', False) and current_price >= logged_position['tp2_price']:
                updates['tp2_hit'] = True
            
            if not logged_position.get('tp3_hit', False) and current_price >= logged_position['tp3_price']:
                updates['tp3_hit'] = True
            
            # Check SL
            if not logged_position.get('sl_hit', False) and current_price <= logged_position['stop_loss']:
                updates['sl_hit'] = True
        
        else:  # SHORT
            # For SHORT positions, price needs to go DOWN to hit TPs
            if not logged_position.get('tp1_hit', False) and current_price <= logged_position['tp1_price']:
                updates['tp1_hit'] = True
            
            if not logged_position.get('tp2_hit', False) and current_price <= logged_position['tp2_price']:
                updates['tp2_hit'] = True
            
            if not logged_position.get('tp3_hit', False) and current_price <= logged_position['tp3_price']:
                updates['tp3_hit'] = True
            
            # Check SL
            if not logged_position.get('sl_hit', False) and current_price >= logged_position['stop_loss']:
                updates['sl_hit'] = True

        return updates

    def monitor_positions_once(self):
        """
        Check all open positions once and update logger

        Returns:
            dict: Summary of updates
        """
        # Get current MT5 positions
        mt5_positions = self.get_open_positions()
        mt5_tickets = {pos['ticket'] for pos in mt5_positions}
        
        # Get logged open positions
        logged_positions = self.logger.get_open_positions()
        
        summary = {
            'checked': 0,
            'tp1_hits': 0,
            'tp2_hits': 0,
            'tp3_hits': 0,
            'sl_hits': 0,
            'closed_positions': 0
        }

        # Check each logged position
        for logged_pos in logged_positions:
            ticket = logged_pos.get('ticket')
            
            if ticket is None:
                # Position doesn't have MT5 ticket (maybe paper trading)
                continue
            
            summary['checked'] += 1
            
            # Check if position is still open in MT5
            if ticket not in mt5_tickets:
                # Position was closed in MT5
                print(f"⚠️  Position {logged_pos['trade_id']} (ticket {ticket}) closed in MT5")
                
                # Log as manual close if not already closed
                if logged_pos['status'] == 'OPEN':
                    # Get last known price from history
                    self.logger.log_exit(
                        logged_pos['trade_id'],
                        exit_price=logged_pos['entry_price'],  # Fallback to entry
                        exit_type='MT5_CLOSED'
                    )
                    summary['closed_positions'] += 1
                continue
            
            # Get current MT5 position
            mt5_pos = next((p for p in mt5_positions if p['ticket'] == ticket), None)
            if not mt5_pos:
                continue
            
            # Check for TP/SL hits
            updates = self.check_position_status(logged_pos, mt5_pos)
            
            # Log TP hits
            if updates['tp1_hit']:
                self.logger.log_tp_hit(logged_pos['trade_id'], 'TP1', mt5_pos['current_price'])
                summary['tp1_hits'] += 1
            
            if updates['tp2_hit']:
                self.logger.log_tp_hit(logged_pos['trade_id'], 'TP2', mt5_pos['current_price'])
                summary['tp2_hits'] += 1
            
            if updates['tp3_hit']:
                self.logger.log_tp_hit(logged_pos['trade_id'], 'TP3', mt5_pos['current_price'])
                summary['tp3_hits'] += 1
            
            # Log SL hit (this closes the position)
            if updates['sl_hit']:
                self.logger.log_sl_hit(logged_pos['trade_id'], mt5_pos['current_price'])
                summary['sl_hits'] += 1

        return summary

    def start_monitoring(self):
        """
        Start continuous position monitoring loop

        This runs indefinitely until stop_monitoring() is called
        """
        self.running = True
        
        print("\n" + "="*60)
        print("🔄 Starting MT5 position monitoring")
        print(f"   Checking every {self.check_interval} seconds")
        print("   Press Ctrl+C to stop")
        print("="*60 + "\n")

        try:
            while self.running:
                try:
                    print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Checking positions...")
                    
                    summary = self.monitor_positions_once()
                    
                    print(f"   ✅ Checked {summary['checked']} positions")
                    if summary['tp1_hits'] > 0:
                        print(f"   🎯 TP1 hits: {summary['tp1_hits']}")
                    if summary['tp2_hits'] > 0:
                        print(f"   🎯 TP2 hits: {summary['tp2_hits']}")
                    if summary['tp3_hits'] > 0:
                        print(f"   🎯 TP3 hits: {summary['tp3_hits']}")
                    if summary['sl_hits'] > 0:
                        print(f"   🛑 SL hits: {summary['sl_hits']}")
                    if summary['closed_positions'] > 0:
                        print(f"   ❌ Closed: {summary['closed_positions']}")
                    
                    # Wait for next check
                    time.sleep(self.check_interval)
                
                except KeyboardInterrupt:
                    print("\n⚠️  Keyboard interrupt detected")
                    break
                
                except Exception as e:
                    print(f"❌ Error during monitoring: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(self.check_interval)
        
        finally:
            self.running = False
            print("\n✅ Position monitoring stopped")

    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False


def main():
    """Test the position monitor"""
    print("🔍 MT5 Position Monitor - Test Mode\n")
    
    # Create monitor
    monitor = MT5PositionMonitor(check_interval=10)
    
    # Connect to MT5
    if not monitor.connect_mt5():
        print("❌ Failed to connect to MT5")
        return
    
    try:
        # Show current positions
        positions = monitor.get_open_positions()
        print(f"\n📊 Current open positions: {len(positions)}")
        for pos in positions:
            print(f"   Ticket: {pos['ticket']} | {pos['symbol']} | {pos['type']}")
            print(f"   Entry: {pos['open_price']:.2f} | Current: {pos['current_price']:.2f}")
            print(f"   SL: {pos['sl']:.2f} | TP: {pos['tp']:.2f}")
            print(f"   Profit: ${pos['profit']:.2f}\n")
        
        # Start monitoring
        if len(positions) > 0:
            print("Starting monitoring...")
            monitor.start_monitoring()
        else:
            print("No positions to monitor")
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    
    finally:
        monitor.disconnect_mt5()


if __name__ == "__main__":
    main()
