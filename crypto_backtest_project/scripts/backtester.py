"""
Advanced Backtesting Engine for SMC Strategy
Includes realistic trading simulation with commissions, slippage, and detailed analytics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
import json


class Trade:
    """Trade class to track individual trades"""

    def __init__(
        self,
        entry_time: datetime,
        entry_price: float,
        direction: int,  # 1 for long, -1 for short
        stop_loss: float,
        take_profit: float,
        size: float
    ):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.direction = direction
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.size = size
        self.exit_time = None
        self.exit_price = None
        self.pnl = 0
        self.pnl_pct = 0
        self.exit_reason = None  # 'tp', 'sl', 'signal'

    def close(self, exit_time: datetime, exit_price: float, reason: str):
        """Close the trade"""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason

        if self.direction == 1:  # Long
            self.pnl = (exit_price - self.entry_price) * self.size
            self.pnl_pct = (exit_price - self.entry_price) / self.entry_price
        else:  # Short
            self.pnl = (self.entry_price - exit_price) * self.size
            self.pnl_pct = (self.entry_price - exit_price) / self.entry_price

    def to_dict(self) -> Dict:
        """Convert trade to dictionary"""
        return {
            'entry_time': self.entry_time,
            'entry_price': self.entry_price,
            'direction': 'LONG' if self.direction == 1 else 'SHORT',
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'size': self.size,
            'exit_time': self.exit_time,
            'exit_price': self.exit_price,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct * 100,
            'exit_reason': self.exit_reason
        }


class Backtester:
    """Advanced backtesting engine"""

    def __init__(
        self,
        initial_capital: float = 10000,
        commission: float = 0.001,  # 0.1% per trade
        slippage: float = 0.0005,  # 0.05% slippage
        risk_per_trade: float = 0.02  # 2% risk per trade
    ):
        """
        Initialize Backtester

        Args:
            initial_capital: Starting capital
            commission: Commission per trade (as fraction)
            slippage: Slippage per trade (as fraction)
            risk_per_trade: Risk per trade (as fraction of capital)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.risk_per_trade = risk_per_trade

        self.capital = initial_capital
        self.equity_curve = []
        self.trades: List[Trade] = []
        self.current_trade: Trade = None

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """
        Calculate position size based on risk management

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price

        Returns:
            Position size
        """
        risk_amount = self.capital * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 0

        position_size = risk_amount / risk_per_unit
        return position_size

    def apply_costs(self, price: float, direction: int) -> float:
        """
        Apply commission and slippage to price

        Args:
            price: Original price
            direction: 1 for buy, -1 for sell

        Returns:
            Adjusted price
        """
        # Apply slippage
        if direction == 1:  # Buy
            price *= (1 + self.slippage)
        else:  # Sell
            price *= (1 - self.slippage)

        return price

    def check_exit_conditions(self, row: pd.Series) -> Tuple[bool, str, float]:
        """
        Check if current trade should be exited

        Args:
            row: Current candle data

        Returns:
            (should_exit, reason, exit_price)
        """
        if self.current_trade is None:
            return False, None, None

        # Check stop loss
        if self.current_trade.direction == 1:  # Long
            if row['low'] <= self.current_trade.stop_loss:
                return True, 'sl', self.current_trade.stop_loss
            if row['high'] >= self.current_trade.take_profit:
                return True, 'tp', self.current_trade.take_profit
        else:  # Short
            if row['high'] >= self.current_trade.stop_loss:
                return True, 'sl', self.current_trade.stop_loss
            if row['low'] <= self.current_trade.take_profit:
                return True, 'tp', self.current_trade.take_profit

        # Check for opposite signal
        if row['signal'] != 0 and row['signal'] != self.current_trade.direction:
            return True, 'signal', row['close']

        return False, None, None

    def run(self, df: pd.DataFrame) -> Dict:
        """
        Run backtest on data with signals

        Args:
            df: DataFrame with OHLC data and signals

        Returns:
            Dictionary with backtest results
        """
        self.capital = self.initial_capital
        self.equity_curve = [self.initial_capital]
        self.trades = []
        self.current_trade = None

        for i in range(len(df)):
            row = df.iloc[i]

            # Check exit conditions for current trade
            if self.current_trade is not None:
                should_exit, reason, exit_price = self.check_exit_conditions(row)

                if should_exit:
                    # Apply costs
                    exit_price = self.apply_costs(exit_price, -self.current_trade.direction)

                    # Close trade
                    self.current_trade.close(row.name, exit_price, reason)

                    # Update capital
                    self.capital += self.current_trade.pnl
                    # Deduct commission
                    commission_cost = abs(self.current_trade.pnl) * self.commission
                    self.capital -= commission_cost

                    # Store trade
                    self.trades.append(self.current_trade)
                    self.current_trade = None

            # Check for new entry signal
            if row['signal'] != 0 and self.current_trade is None:
                entry_price = row['entry_price']
                stop_loss = row['stop_loss']
                take_profit = row['take_profit']

                # Calculate position size
                position_size = self.calculate_position_size(entry_price, stop_loss)

                if position_size > 0:
                    # Apply costs
                    entry_price = self.apply_costs(entry_price, row['signal'])

                    # Open new trade
                    self.current_trade = Trade(
                        entry_time=row.name,
                        entry_price=entry_price,
                        direction=int(row['signal']),
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        size=position_size
                    )

            # Update equity curve
            current_equity = self.capital
            if self.current_trade is not None:
                # Calculate unrealized PnL
                if self.current_trade.direction == 1:
                    unrealized_pnl = (row['close'] - self.current_trade.entry_price) * self.current_trade.size
                else:
                    unrealized_pnl = (self.current_trade.entry_price - row['close']) * self.current_trade.size
                current_equity += unrealized_pnl

            self.equity_curve.append(current_equity)

        # Close any remaining open trade at last price
        if self.current_trade is not None:
            last_row = df.iloc[-1]
            exit_price = self.apply_costs(last_row['close'], -self.current_trade.direction)
            self.current_trade.close(last_row.name, exit_price, 'end')
            self.capital += self.current_trade.pnl
            self.trades.append(self.current_trade)
            self.current_trade = None

        # Calculate statistics
        stats = self.calculate_statistics(df)

        return stats

    def calculate_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate comprehensive backtest statistics

        Args:
            df: Original dataframe with dates

        Returns:
            Dictionary with statistics
        """
        if len(self.trades) == 0:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'total_return_pct': 0,
                'message': 'No trades executed'
            }

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        total_pnl = sum(t.pnl for t in self.trades)
        total_return_pct = (self.capital - self.initial_capital) / self.initial_capital * 100

        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0

        profit_factor = abs(sum(t.pnl for t in winning_trades) / sum(t.pnl for t in losing_trades)) if losing_trades and sum(t.pnl for t in losing_trades) != 0 else 0

        # Calculate max drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max * 100
        max_drawdown = np.min(drawdown)

        # Sharpe ratio (simplified, assuming daily data)
        returns = np.diff(equity_array) / equity_array[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

        # Exit reason breakdown
        exit_reasons = {}
        for trade in self.trades:
            reason = trade.exit_reason
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        # Long vs Short performance
        long_trades = [t for t in self.trades if t.direction == 1]
        short_trades = [t for t in self.trades if t.direction == -1]

        long_win_rate = len([t for t in long_trades if t.pnl > 0]) / len(long_trades) if long_trades else 0
        short_win_rate = len([t for t in short_trades if t.pnl > 0]) / len(short_trades) if short_trades else 0

        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return': total_pnl,
            'total_return_pct': total_return_pct,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'exit_reasons': exit_reasons,
            'long_trades': len(long_trades),
            'short_trades': len(short_trades),
            'long_win_rate': long_win_rate * 100,
            'short_win_rate': short_win_rate * 100,
            'trades': [t.to_dict() for t in self.trades]
        }

    def print_results(self, stats: Dict):
        """
        Print backtest results in a formatted way

        Args:
            stats: Statistics dictionary
        """
        print("\n" + "="*60)
        print("SMC STRATEGY BACKTEST RESULTS")
        print("="*60)

        if stats['total_trades'] == 0:
            print("\n⚠️  No trades executed")
            return

        print(f"\n📊 CAPITAL")
        print(f"  Initial Capital:     ${stats['initial_capital']:,.2f}")
        print(f"  Final Capital:       ${stats['final_capital']:,.2f}")
        print(f"  Total Return:        ${stats['total_return']:,.2f}")
        print(f"  Total Return %:      {stats['total_return_pct']:.2f}%")

        print(f"\n📈 TRADE STATISTICS")
        print(f"  Total Trades:        {stats['total_trades']}")
        print(f"  Winning Trades:      {stats['winning_trades']}")
        print(f"  Losing Trades:       {stats['losing_trades']}")
        print(f"  Win Rate:            {stats['win_rate']:.2f}%")
        print(f"  Average Win:         ${stats['avg_win']:.2f}")
        print(f"  Average Loss:        ${stats['avg_loss']:.2f}")
        print(f"  Profit Factor:       {stats['profit_factor']:.2f}")

        print(f"\n📉 RISK METRICS")
        print(f"  Max Drawdown:        {stats['max_drawdown']:.2f}%")
        print(f"  Sharpe Ratio:        {stats['sharpe_ratio']:.2f}")

        print(f"\n🎯 TRADE BREAKDOWN")
        print(f"  Long Trades:         {stats['long_trades']} (Win Rate: {stats['long_win_rate']:.2f}%)")
        print(f"  Short Trades:        {stats['short_trades']} (Win Rate: {stats['short_win_rate']:.2f}%)")

        print(f"\n🚪 EXIT REASONS")
        for reason, count in stats['exit_reasons'].items():
            print(f"  {reason.upper():20s} {count}")

        print("\n" + "="*60)
