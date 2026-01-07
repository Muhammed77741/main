"""
Trade Logger - Records all live trading signals and position updates to file
Tracks entry, exits, TP hits, SL hits, and P/L
"""

import json
import csv
from datetime import datetime
from pathlib import Path
import os


class TradeLogger:
    """Logger for recording live trading activity to file"""

    def __init__(self, log_dir='trade_logs'):
        """
        Initialize trade logger

        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # File paths
        self.trades_json_file = self.log_dir / 'live_trades.json'
        self.trades_csv_file = self.log_dir / 'live_trades.csv'
        self.positions_json_file = self.log_dir / 'open_positions.json'
        
        # In-memory storage
        self.trades = self._load_trades()
        self.open_positions = self._load_open_positions()
        
        print(f"✅ Trade Logger initialized")
        print(f"   Log directory: {self.log_dir.absolute()}")
        print(f"   Loaded {len(self.trades)} historical trades")
        print(f"   Open positions: {len(self.open_positions)}")

    def _load_trades(self):
        """Load historical trades from JSON file"""
        if self.trades_json_file.exists():
            try:
                with open(self.trades_json_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading trades: {e}")
                return []
        return []

    def _load_open_positions(self):
        """Load open positions from JSON file"""
        if self.positions_json_file.exists():
            try:
                with open(self.positions_json_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading open positions: {e}")
                return []
        return []

    def _save_trades(self):
        """Save all trades to JSON and CSV files"""
        # Save to JSON
        try:
            with open(self.trades_json_file, 'w', encoding='utf-8') as f:
                json.dump(self.trades, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving trades to JSON: {e}")

        # Save to CSV
        try:
            if len(self.trades) > 0:
                with open(self.trades_csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                    writer.writeheader()
                    writer.writerows(self.trades)
        except Exception as e:
            print(f"❌ Error saving trades to CSV: {e}")

    def _save_open_positions(self):
        """Save open positions to JSON file"""
        try:
            with open(self.positions_json_file, 'w', encoding='utf-8') as f:
                json.dump(self.open_positions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving open positions: {e}")

    def log_entry(self, signal_data):
        """
        Log a new trade entry

        Args:
            signal_data: Dictionary with trade entry details
                - direction: 'LONG' or 'SHORT'
                - entry_price: Entry price
                - entry_time: Entry timestamp
                - stop_loss: Stop loss price
                - tp1_price, tp2_price, tp3_price: Take profit levels
                - pattern: Pattern name (optional)
                - ticket: MT5 ticket number (optional)

        Returns:
            str: Trade ID
        """
        trade_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        entry_time = signal_data.get('entry_time', datetime.now())
        if isinstance(entry_time, str):
            entry_time_str = entry_time
        else:
            entry_time_str = entry_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(entry_time, 'strftime') else str(entry_time)

        position = {
            'trade_id': trade_id,
            'status': 'OPEN',
            'direction': signal_data['direction'],
            'entry_price': float(signal_data['entry_price']),
            'entry_time': entry_time_str,
            'stop_loss': float(signal_data['stop_loss']),
            'tp1_price': float(signal_data['tp1_price']),
            'tp2_price': float(signal_data['tp2_price']),
            'tp3_price': float(signal_data['tp3_price']),
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'tp1_hit_time': None,
            'tp2_hit_time': None,
            'tp3_hit_time': None,
            'sl_hit': False,
            'sl_hit_time': None,
            'position_remaining': 1.0,
            'total_pnl_pct': 0.0,
            'total_pnl_points': 0.0,
            'pattern': signal_data.get('pattern', 'N/A'),
            'ticket': signal_data.get('ticket', None),
            'close_pct1': signal_data.get('close_pct1', 0.5),
            'close_pct2': signal_data.get('close_pct2', 0.3),
            'close_pct3': signal_data.get('close_pct3', 0.2),
            'exit_time': None,
            'exit_price': None,
            'exit_type': None,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        self.open_positions.append(position)
        self._save_open_positions()

        print(f"📝 Logged new entry: {trade_id}")
        print(f"   Direction: {position['direction']}")
        print(f"   Entry: {position['entry_price']:.2f}")
        print(f"   TP1/2/3: {position['tp1_price']:.2f}/{position['tp2_price']:.2f}/{position['tp3_price']:.2f}")
        print(f"   SL: {position['stop_loss']:.2f}")

        return trade_id

    def log_tp_hit(self, trade_id, tp_level, hit_price, hit_time=None):
        """
        Log a take profit hit

        Args:
            trade_id: Trade ID
            tp_level: 'TP1', 'TP2', or 'TP3'
            hit_price: Price at which TP was hit
            hit_time: Time when TP was hit (default: now)

        Returns:
            bool: True if logged successfully
        """
        if hit_time is None:
            hit_time = datetime.now()
        
        hit_time_str = hit_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(hit_time, 'strftime') else str(hit_time)

        # Find position in open positions
        for pos in self.open_positions:
            if pos['trade_id'] == trade_id:
                tp_key = f"{tp_level.lower()}_hit"
                tp_time_key = f"{tp_level.lower()}_hit_time"
                
                if not pos.get(tp_key, False):
                    pos[tp_key] = True
                    pos[tp_time_key] = hit_time_str
                    
                    # Calculate PnL for this partial close
                    close_pct_key = f"close_pct{tp_level[-1]}"  # close_pct1, close_pct2, close_pct3
                    close_pct = pos.get(close_pct_key, 0.33)
                    
                    if pos['direction'] == 'LONG':
                        pnl_points = hit_price - pos['entry_price']
                    else:
                        pnl_points = pos['entry_price'] - hit_price
                    
                    pnl_pct = (pnl_points / pos['entry_price']) * 100 * close_pct
                    pos['total_pnl_pct'] += pnl_pct
                    pos['total_pnl_points'] += pnl_points * close_pct
                    pos['position_remaining'] -= close_pct
                    pos['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    self._save_open_positions()
                    
                    print(f"🎯 {tp_level} HIT logged for {trade_id}")
                    print(f"   Price: {hit_price:.2f}")
                    print(f"   Closed: {close_pct*100:.0f}% of position")
                    print(f"   PnL: {pnl_pct:+.2f}% ({pnl_points*close_pct:+.2f} points)")
                    print(f"   Remaining: {pos['position_remaining']*100:.0f}%")
                    
                    return True
                else:
                    print(f"⚠️  {tp_level} already recorded for {trade_id}")
                    return False
        
        print(f"⚠️  Trade {trade_id} not found in open positions")
        return False

    def log_sl_hit(self, trade_id, hit_price, hit_time=None):
        """
        Log a stop loss hit

        Args:
            trade_id: Trade ID
            hit_price: Price at which SL was hit
            hit_time: Time when SL was hit (default: now)

        Returns:
            bool: True if logged successfully
        """
        if hit_time is None:
            hit_time = datetime.now()
        
        hit_time_str = hit_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(hit_time, 'strftime') else str(hit_time)

        # Find and close position
        for i, pos in enumerate(self.open_positions):
            if pos['trade_id'] == trade_id:
                pos['sl_hit'] = True
                pos['sl_hit_time'] = hit_time_str
                
                # Calculate final PnL
                if pos['direction'] == 'LONG':
                    pnl_points = (hit_price - pos['entry_price']) * pos['position_remaining']
                else:
                    pnl_points = (pos['entry_price'] - hit_price) * pos['position_remaining']
                
                pnl_pct = (pnl_points / pos['entry_price']) * 100
                pos['total_pnl_pct'] += pnl_pct
                pos['total_pnl_points'] += pnl_points
                
                pos['exit_time'] = hit_time_str
                pos['exit_price'] = hit_price
                pos['exit_type'] = 'SL'
                pos['status'] = 'CLOSED'
                pos['position_remaining'] = 0.0
                pos['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Move to closed trades
                self.trades.append(pos)
                self.open_positions.pop(i)
                
                self._save_trades()
                self._save_open_positions()
                
                print(f"🛑 STOP LOSS HIT logged for {trade_id}")
                print(f"   Price: {hit_price:.2f}")
                print(f"   Total PnL: {pos['total_pnl_pct']:+.2f}% ({pos['total_pnl_points']:+.2f} points)")
                
                return True
        
        print(f"⚠️  Trade {trade_id} not found in open positions")
        return False

    def log_exit(self, trade_id, exit_price, exit_type='MANUAL', exit_time=None):
        """
        Log trade exit (for timeout or manual close)

        Args:
            trade_id: Trade ID
            exit_price: Exit price
            exit_type: 'MANUAL', 'TIMEOUT', etc.
            exit_time: Exit time (default: now)

        Returns:
            bool: True if logged successfully
        """
        if exit_time is None:
            exit_time = datetime.now()
        
        exit_time_str = exit_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(exit_time, 'strftime') else str(exit_time)

        # Find and close position
        for i, pos in enumerate(self.open_positions):
            if pos['trade_id'] == trade_id:
                # Calculate final PnL for remaining position
                if pos['position_remaining'] > 0:
                    if pos['direction'] == 'LONG':
                        pnl_points = (exit_price - pos['entry_price']) * pos['position_remaining']
                    else:
                        pnl_points = (pos['entry_price'] - exit_price) * pos['position_remaining']
                    
                    pnl_pct = (pnl_points / pos['entry_price']) * 100
                    pos['total_pnl_pct'] += pnl_pct
                    pos['total_pnl_points'] += pnl_points
                
                pos['exit_time'] = exit_time_str
                pos['exit_price'] = exit_price
                pos['exit_type'] = exit_type
                pos['status'] = 'CLOSED'
                pos['position_remaining'] = 0.0
                pos['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Move to closed trades
                self.trades.append(pos)
                self.open_positions.pop(i)
                
                self._save_trades()
                self._save_open_positions()
                
                emoji = "✅" if pos['total_pnl_pct'] > 0 else "❌"
                print(f"{emoji} EXIT logged for {trade_id}")
                print(f"   Exit type: {exit_type}")
                print(f"   Price: {exit_price:.2f}")
                print(f"   Total PnL: {pos['total_pnl_pct']:+.2f}% ({pos['total_pnl_points']:+.2f} points)")
                
                return True
        
        print(f"⚠️  Trade {trade_id} not found in open positions")
        return False

    def get_open_positions(self):
        """Get all open positions"""
        return self.open_positions.copy()

    def get_closed_trades(self):
        """Get all closed trades"""
        return self.trades.copy()

    def get_position_by_id(self, trade_id):
        """Get specific position by trade ID"""
        for pos in self.open_positions:
            if pos['trade_id'] == trade_id:
                return pos.copy()
        return None

    def get_statistics(self):
        """Get trading statistics"""
        wins = [t for t in self.trades if t['total_pnl_pct'] > 0]
        losses = [t for t in self.trades if t['total_pnl_pct'] <= 0]
        
        total_pnl = sum(t['total_pnl_pct'] for t in self.trades) if self.trades else 0
        
        return {
            'total_trades': len(self.trades),
            'open_positions': len(self.open_positions),
            'win_rate': (len(wins) / len(self.trades)) * 100 if self.trades else 0,
            'total_pnl_pct': total_pnl,
            'avg_pnl_pct': total_pnl / len(self.trades) if self.trades else 0,
            'wins': len(wins),
            'losses': len(losses),
            'tp1_hits': sum(1 for t in self.trades if t.get('tp1_hit', False)),
            'tp2_hits': sum(1 for t in self.trades if t.get('tp2_hit', False)),
            'tp3_hits': sum(1 for t in self.trades if t.get('tp3_hit', False)),
            'sl_hits': sum(1 for t in self.trades if t.get('sl_hit', False))
        }

    def print_statistics(self):
        """Print current trading statistics"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("📊 TRADING STATISTICS")
        print("="*60)
        print(f"Total trades: {stats['total_trades']}")
        print(f"Open positions: {stats['open_positions']}")
        print(f"Wins: {stats['wins']} | Losses: {stats['losses']}")
        print(f"Win rate: {stats['win_rate']:.1f}%")
        print(f"Total PnL: {stats['total_pnl_pct']:+.2f}%")
        print(f"Average PnL: {stats['avg_pnl_pct']:+.2f}%")
        print(f"\nTP hits: TP1={stats['tp1_hits']} | TP2={stats['tp2_hits']} | TP3={stats['tp3_hits']}")
        print(f"SL hits: {stats['sl_hits']}")
        print("="*60)


if __name__ == "__main__":
    # Test the logger
    logger = TradeLogger()
    
    # Test logging an entry
    trade_id = logger.log_entry({
        'direction': 'LONG',
        'entry_price': 2650.50,
        'entry_time': datetime.now(),
        'stop_loss': 2630.00,
        'tp1_price': 2680.50,
        'tp2_price': 2700.50,
        'tp3_price': 2730.50,
        'pattern': 'Bullish Engulfing',
        'close_pct1': 0.5,
        'close_pct2': 0.3,
        'close_pct3': 0.2
    })
    
    # Test logging TP hits
    logger.log_tp_hit(trade_id, 'TP1', 2680.50)
    logger.log_tp_hit(trade_id, 'TP2', 2700.50)
    
    # Print statistics
    logger.print_statistics()
