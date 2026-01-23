"""
Adaptive Backtester with Partial TP and Trailing Stop

Features:
- Partial TP: 50% at TP1, 30% at TP2, 20% at TP3
- Trailing Stop after TP1 hit
- Max concurrent positions
- Position timeout
- Full trade logging
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class Position:
    """Represents an open position with partial TP"""
    
    def __init__(
        self,
        entry_idx: int,
        entry_time: datetime,
        entry_price: float,
        direction: int,
        stop_loss: float,
        tp1: float,
        tp2: float,
        tp3: float,
        position_size: float,
        trailing_stop_pct: float = 0.0,
        timeout_hours: int = 48
    ):
        self.entry_idx = entry_idx
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.direction = direction  # 1 = LONG, -1 = SHORT
        self.stop_loss = stop_loss
        self.tp1 = tp1
        self.tp2 = tp2
        self.tp3 = tp3
        self.position_size = position_size
        self.trailing_stop_pct = trailing_stop_pct
        self.timeout_hours = timeout_hours
        
        # Partial close tracking
        self.remaining_size = 1.0  # 100%
        self.tp1_hit = False
        self.tp2_hit = False
        self.tp3_hit = False
        
        # Trailing stop
        self.trailing_active = False
        self.trailing_stop_price = stop_loss
        self.highest_price = entry_price  # For LONG
        self.lowest_price = entry_price   # For SHORT
        
        # PnL tracking
        self.realized_pnl = 0.0
        self.closed_portions = []
    
    def update_trailing_stop(self, current_price: float):
        """Update trailing stop if active"""
        if not self.trailing_active:
            return
        
        if self.direction == 1:  # LONG
            if current_price > self.highest_price:
                self.highest_price = current_price
                # Trail from highest
                self.trailing_stop_price = self.highest_price * (1 - self.trailing_stop_pct)
        else:  # SHORT
            if current_price < self.lowest_price:
                self.lowest_price = current_price
                # Trail from lowest
                self.trailing_stop_price = self.lowest_price * (1 + self.trailing_stop_pct)
    
    def check_tp_levels(self, high: float, low: float, current_time: datetime) -> List[Dict]:
        """
        Check if any TP levels were hit
        
        Returns list of partial closes
        """
        closes = []
        
        if self.direction == 1:  # LONG
            # Check TP1 (50%)
            if not self.tp1_hit and high >= self.tp1:
                self.tp1_hit = True
                portion = 0.5
                pnl_pct = (self.tp1 - self.entry_price) / self.entry_price * 100
                pnl = self.position_size * portion * pnl_pct / 100
                self.realized_pnl += pnl
                self.remaining_size -= portion
                
                # Activate trailing stop
                self.trailing_active = True
                self.highest_price = self.tp1
                self.trailing_stop_price = self.tp1 * (1 - self.trailing_stop_pct)
                
                closes.append({
                    'time': current_time,
                    'level': 'TP1',
                    'price': self.tp1,
                    'portion': portion,
                    'pnl_pct': pnl_pct,
                    'pnl': pnl
                })
            
            # Check TP2 (30%)
            if self.tp1_hit and not self.tp2_hit and high >= self.tp2:
                self.tp2_hit = True
                portion = 0.3
                pnl_pct = (self.tp2 - self.entry_price) / self.entry_price * 100
                pnl = self.position_size * portion * pnl_pct / 100
                self.realized_pnl += pnl
                self.remaining_size -= portion
                
                closes.append({
                    'time': current_time,
                    'level': 'TP2',
                    'price': self.tp2,
                    'portion': portion,
                    'pnl_pct': pnl_pct,
                    'pnl': pnl
                })
            
            # Check TP3 (20%)
            if self.tp2_hit and not self.tp3_hit and high >= self.tp3:
                self.tp3_hit = True
                portion = 0.2
                pnl_pct = (self.tp3 - self.entry_price) / self.entry_price * 100
                pnl = self.position_size * portion * pnl_pct / 100
                self.realized_pnl += pnl
                self.remaining_size -= portion
                
                closes.append({
                    'time': current_time,
                    'level': 'TP3',
                    'price': self.tp3,
                    'portion': portion,
                    'pnl_pct': pnl_pct,
                    'pnl': pnl
                })
        
        # Store closes
        self.closed_portions.extend(closes)
        
        return closes
    
    def is_fully_closed(self) -> bool:
        """Check if position is fully closed"""
        return self.remaining_size <= 0.01  # Allow small floating point errors
    
    def check_stop_loss(self, low: float, high: float) -> bool:
        """Check if stop loss or trailing stop was hit"""
        if self.direction == 1:  # LONG
            # Check regular SL or trailing SL
            if self.trailing_active:
                return low <= self.trailing_stop_price
            else:
                return low <= self.stop_loss
        else:  # SHORT
            if self.trailing_active:
                return high >= self.trailing_stop_price
            else:
                return high >= self.stop_loss
    
    def check_timeout(self, current_time: datetime) -> bool:
        """Check if position has timed out"""
        time_diff = current_time - self.entry_time
        hours_open = time_diff.total_seconds() / 3600
        return hours_open >= self.timeout_hours


class AdaptiveBacktester:
    """Backtester with partial TP and trailing stop"""
    
    def __init__(
        self,
        initial_capital: float = 10000,
        risk_per_trade: float = 0.02,
        max_positions: int = 5,
        commission: float = 0.001,
        slippage: float = 0.0005
    ):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_positions = max_positions
        self.commission = commission
        self.slippage = slippage
        
        self.capital = initial_capital
        self.peak_capital = initial_capital
        self.positions: List[Position] = []
        self.closed_trades = []
        self.equity_curve = [initial_capital]
    
    def can_open_position(self) -> bool:
        """Check if we can open a new position"""
        return len(self.positions) < self.max_positions
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk"""
        risk_amount = self.capital * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0
        
        position_size = risk_amount / risk_per_unit
        return position_size * entry_price  # Dollar amount
    
    def open_position(
        self,
        idx: int,
        time: datetime,
        entry_price: float,
        direction: int,
        stop_loss: float,
        tp1: float,
        tp2: float,
        tp3: float,
        trailing_stop_pct: float,
        timeout_hours: int
    ):
        """Open a new position"""
        position_size = self.calculate_position_size(entry_price, stop_loss)
        
        if position_size == 0:
            return
        
        # Apply commission and slippage
        entry_price_adj = entry_price * (1 + self.commission + self.slippage * direction)
        
        position = Position(
            entry_idx=idx,
            entry_time=time,
            entry_price=entry_price_adj,
            direction=direction,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            position_size=position_size,
            trailing_stop_pct=trailing_stop_pct,
            timeout_hours=timeout_hours
        )
        
        self.positions.append(position)
    
    def update_positions(self, idx: int, time: datetime, high: float, low: float, close: float):
        """Update all open positions"""
        positions_to_close = []
        
        for pos in self.positions:
            # Check TP levels
            partial_closes = pos.check_tp_levels(high, low, time)
            
            # Update trailing stop
            pos.update_trailing_stop(close)
            
            # Check stop loss
            if pos.check_stop_loss(low, high):
                exit_price = pos.trailing_stop_price if pos.trailing_active else pos.stop_loss
                exit_reason = 'TRAILING_SL' if pos.trailing_active else 'SL'
                positions_to_close.append((pos, exit_price, exit_reason, time))
                continue
            
            # Check timeout
            if pos.check_timeout(time):
                positions_to_close.append((pos, close, 'TIMEOUT', time))
                continue
            
            # Check if fully closed
            if pos.is_fully_closed():
                positions_to_close.append((pos, None, 'FULL_TP', time))
        
        # Close positions
        for pos, exit_price, reason, exit_time in positions_to_close:
            self.close_position(pos, exit_price, reason, exit_time)
    
    def close_position(self, pos: Position, exit_price: Optional[float], reason: str, exit_time: datetime):
        """Close a position"""
        # If not fully closed via TP, close remaining
        if not pos.is_fully_closed() and exit_price is not None:
            remaining_pct = (exit_price - pos.entry_price) / pos.entry_price * 100
            if pos.direction == -1:
                remaining_pct = -remaining_pct
            
            remaining_pnl = pos.position_size * pos.remaining_size * remaining_pct / 100
            pos.realized_pnl += remaining_pnl
        
        # Apply commission on exit
        commission_cost = pos.position_size * self.commission
        pos.realized_pnl -= commission_cost
        
        # Update capital
        self.capital += pos.realized_pnl
        
        # Track peak
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital
        
        # Log trade
        total_pnl_pct = pos.realized_pnl / pos.position_size * 100 if pos.position_size > 0 else 0
        
        self.closed_trades.append({
            'entry_time': pos.entry_time,
            'exit_time': exit_time,
            'direction': 'LONG' if pos.direction == 1 else 'SHORT',
            'entry_price': pos.entry_price,
            'exit_price': exit_price if exit_price else pos.tp3,
            'stop_loss': pos.stop_loss,
            'tp1': pos.tp1,
            'tp2': pos.tp2,
            'tp3': pos.tp3,
            'tp1_hit': pos.tp1_hit,
            'tp2_hit': pos.tp2_hit,
            'tp3_hit': pos.tp3_hit,
            'trailing_hit': (reason == 'TRAILING_SL'),
            'pnl': pos.realized_pnl,
            'pnl_pct': total_pnl_pct,
            'exit_reason': reason,
            'partial_closes': len(pos.closed_portions)
        })
        
        # Remove from open positions
        self.positions.remove(pos)
    
    def run(self, df: pd.DataFrame) -> Dict:
        """Run backtest"""
        print(f"\n🔄 Running Adaptive Backtest...")
        print(f"   Max Positions: {self.max_positions}")
        print(f"   Risk per Trade: {self.risk_per_trade*100}%")
        
        for i in range(len(df)):
            time = df.index[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            close = df['close'].iloc[i]
            
            # Update existing positions first
            self.update_positions(i, time, high, low, close)
            
            # Check for new signal
            signal = df['signal'].iloc[i]
            if signal != 0 and self.can_open_position():
                entry = df['entry_price'].iloc[i]
                sl = df['stop_loss'].iloc[i]
                tp1 = df.get('tp1', df['take_profit']).iloc[i]
                tp2 = df.get('tp2', df['take_profit']).iloc[i]
                tp3 = df.get('tp3', df['take_profit']).iloc[i]
                trailing_pct = df.get('trailing_stop_pct', pd.Series([0.009]*len(df))).iloc[i]
                
                # Get regime params
                regime = df.get('regime', pd.Series(['TREND']*len(df))).iloc[i]
                timeout_hours = 60 if regime == 'TREND' else 48
                
                if entry > 0 and sl > 0:
                    self.open_position(
                        i, time, entry, int(signal), sl,
                        tp1, tp2, tp3,
                        trailing_pct, timeout_hours
                    )
            
            # Track equity
            total_equity = self.capital
            for pos in self.positions:
                unrealized = pos.position_size * (close - pos.entry_price) / pos.entry_price * pos.direction * pos.remaining_size
                total_equity += unrealized
            
            self.equity_curve.append(total_equity)
        
        # Close remaining positions at end
        if len(df) > 0:
            last_time = df.index[-1]
            last_close = df['close'].iloc[-1]
            for pos in self.positions[:]:
                self.close_position(pos, last_close, 'END', last_time)
        
        # Calculate statistics
        return self.calculate_stats()
    
    def calculate_stats(self) -> Dict:
        """Calculate backtest statistics"""
        if len(self.closed_trades) == 0:
            return {
                'total_trades': 0,
                'total_return_pct': 0,
                'win_rate': 0
            }
        
        df_trades = pd.DataFrame(self.closed_trades)
        
        wins = df_trades[df_trades['pnl'] > 0]
        losses = df_trades[df_trades['pnl'] <= 0]
        
        total_return = self.capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        max_dd = ((self.peak_capital - min(self.equity_curve)) / self.peak_capital) * 100 if self.peak_capital > 0 else 0
        
        # Sharpe ratio (simplified)
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        stats = {
            'total_trades': len(self.closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(self.closed_trades) * 100,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'final_capital': self.capital,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0,
            'tp1_hit_rate': (df_trades['tp1_hit'].sum() / len(df_trades)) * 100,
            'tp2_hit_rate': (df_trades['tp2_hit'].sum() / len(df_trades)) * 100,
            'tp3_hit_rate': (df_trades['tp3_hit'].sum() / len(df_trades)) * 100,
            'trailing_exits': (df_trades['exit_reason'] == 'TRAILING_SL').sum(),
            'trades': self.closed_trades
        }
        
        return stats
    
    def print_results(self, stats: Dict):
        """Print backtest results"""
        print("\n" + "="*70)
        print("ADAPTIVE BACKTEST RESULTS (with Partial TP & Trailing Stop)")
        print("="*70)
        
        print(f"\n💰 CAPITAL")
        print(f"  Initial Capital:     ${self.initial_capital:,.2f}")
        print(f"  Final Capital:       ${stats['final_capital']:,.2f}")
        print(f"  Total Return:        ${stats['total_return']:,.2f}")
        print(f"  Total Return %:      {stats['total_return_pct']:.2f}%")
        
        print(f"\n📊 TRADE STATISTICS")
        print(f"  Total Trades:        {stats['total_trades']}")
        print(f"  Winning Trades:      {stats['winning_trades']}")
        print(f"  Losing Trades:       {stats['losing_trades']}")
        print(f"  Win Rate:            {stats['win_rate']:.2f}%")
        print(f"  Average Win:         ${stats['avg_win']:.2f}")
        print(f"  Average Loss:        ${stats['avg_loss']:.2f}")
        print(f"  Profit Factor:       {stats['profit_factor']:.2f}")
        
        print(f"\n🎯 PARTIAL TP STATISTICS")
        print(f"  TP1 Hit Rate:        {stats['tp1_hit_rate']:.1f}%")
        print(f"  TP2 Hit Rate:        {stats['tp2_hit_rate']:.1f}%")
        print(f"  TP3 Hit Rate:        {stats['tp3_hit_rate']:.1f}%")
        print(f"  Trailing SL Exits:   {stats['trailing_exits']}")
        
        print(f"\n📉 RISK METRICS")
        print(f"  Max Drawdown:        {stats['max_drawdown']:.2f}%")
        print(f"  Sharpe Ratio:        {stats['sharpe_ratio']:.2f}")
        
        print("\n" + "="*70)
