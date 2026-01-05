"""
Enhanced Backtest script for ICT Price Action Strategy
Features:
- Partial closes (TP1/TP2/TP3)
- Trailing stop after TP1
- Adaptive parameters (TREND vs RANGE mode)
- Realistic costs (spread, commission, swap)
- Detailed statistics breakdown
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ict_price_action_strategy import ICTPriceActionStrategy


def load_data(filepath: str) -> pd.DataFrame:
    """
    Load OHLCV data from CSV file
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        DataFrame with OHLCV data
    """
    # Read CSV - datetime column gets auto-parsed as index
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    
    # Rename columns if needed
    if 'volume' in df.columns:
        df = df.rename(columns={'volume': 'tick_volume'})
    
    # Add spread column if missing
    if 'spread' not in df.columns:
        df['spread'] = 0
    
    # Ensure numeric types
    for col in ['open', 'high', 'low', 'close']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Handle tick_volume and spread
    if 'tick_volume' in df.columns:
        df['tick_volume'] = pd.to_numeric(df['tick_volume'], errors='coerce')
    else:
        df['tick_volume'] = 0
    
    if 'spread' in df.columns:
        df['spread'] = pd.to_numeric(df['spread'], errors='coerce')
    else:
        df['spread'] = 0
    
    # Drop any NaN rows in OHLC
    df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
    
    print(f"Loaded {len(df)} candles from {df.index[0]} to {df.index[-1]}")
    
    return df


def detect_market_mode(df: pd.DataFrame, lookback: int = 50) -> str:
    """
    Detect if market is in TREND or RANGE mode
    
    Args:
        df: DataFrame with price data
        lookback: Number of candles to analyze
        
    Returns:
        'TREND' or 'RANGE'
    """
    if len(df) < lookback:
        return 'RANGE'
    
    window = df.iloc[-lookback:]
    
    # Calculate ADX-like metric
    high_low_range = (window['high'].max() - window['low'].min()) / window['close'].mean()
    
    # Calculate trend strength using price movement
    price_change = abs(window['close'].iloc[-1] - window['close'].iloc[0]) / window['close'].iloc[0]
    
    # TREND if strong directional movement
    if high_low_range > 0.03 and price_change > 0.02:
        return 'TREND'
    else:
        return 'RANGE'


class EnhancedICTBacktester:
    """Enhanced Backtester for ICT Price Action Strategy with partial closes and adaptive parameters"""
    
    def __init__(
        self,
        initial_capital: float = 10000,
        spread_points: float = 2.0,  # 2 points spread
        commission_points: float = 0.5,  # 0.5 points commission
        swap_per_day: float = -0.3,  # -0.3 points per day
        max_positions: int = 5,
        point_value: float = 1.0,  # 1 point = $1 for XAUUSD
    ):
        """
        Initialize enhanced backtester
        
        Args:
            initial_capital: Starting capital
            spread_points: Spread in points
            commission_points: Commission in points
            swap_per_day: Swap cost per day in points
            max_positions: Maximum concurrent positions
            point_value: Dollar value per point
        """
        self.initial_capital = initial_capital
        self.spread_points = spread_points
        self.commission_points = commission_points
        self.swap_per_day = swap_per_day
        self.max_positions = max_positions
        self.point_value = point_value
        
        self.trades = []
        self.equity_curve = []
        self.open_positions = []
        
        # Adaptive parameters
        self.params = {
            'TREND': {
                'tp_levels': [40, 70, 120],  # TP1, TP2, TP3 in points
                'tp_percentages': [0.5, 0.3, 0.2],  # 50%, 30%, 20%
                'trailing_points': 20,
                'timeout_hours': 60
            },
            'RANGE': {
                'tp_levels': [25, 45, 70],  # TP1, TP2, TP3 in points
                'tp_percentages': [0.5, 0.3, 0.2],  # 50%, 30%, 20%
                'trailing_points': 15,
                'timeout_hours': 48
            }
        }
        
    def run_backtest(self, df: pd.DataFrame, strategy: ICTPriceActionStrategy) -> dict:
        """
        Run enhanced backtest on historical data
        
        Args:
            df: DataFrame with OHLCV data
            strategy: ICT strategy instance
            
        Returns:
            Dictionary with backtest results
        """
        print("\nGenerating ICT signals...")
        df_with_signals = strategy.generate_signals(df)
        
        # Initialize tracking variables
        account_balance = self.initial_capital
        self.trades = []
        self.open_positions = []
        self.equity_curve = [self.initial_capital]
        
        print(f"\nRunning enhanced backtest with partial closes...")
        print(f"Total signals: {(df_with_signals['signal'] != 0).sum()}")
        
        for i in range(len(df_with_signals)):
            current_time = df_with_signals.index[i]
            current_bar = df_with_signals.iloc[i]
            
            # Detect market mode for adaptive parameters
            mode = detect_market_mode(df_with_signals.iloc[:i+1])
            params = self.params[mode]
            
            # Update open positions
            for position in self.open_positions[:]:
                account_balance = self._update_position(
                    position, current_bar, current_time, params, account_balance
                )
            
            # Check for new signals (only if under position limit)
            if len(self.open_positions) < self.max_positions and current_bar['signal'] != 0:
                entry_params = strategy.get_entry_parameters(df_with_signals, i, account_balance)
                
                if entry_params is not None:
                    # Open new position
                    position = self._open_position(
                        entry_params, current_bar, current_time, mode, params
                    )
                    self.open_positions.append(position)
            
            # Calculate equity
            equity = account_balance
            for position in self.open_positions:
                if position['direction'] == 1:
                    unrealized_pnl = (current_bar['close'] - position['entry_price']) * position['remaining_size']
                else:
                    unrealized_pnl = (position['entry_price'] - current_bar['close']) * position['remaining_size']
                equity += unrealized_pnl * self.point_value
            
            self.equity_curve.append(equity)
        
        # Close any remaining positions at the end
        if len(df_with_signals) > 0:
            final_bar = df_with_signals.iloc[-1]
            final_time = df_with_signals.index[-1]
            for position in self.open_positions[:]:
                self._close_position(position, final_bar['close'], final_time, 'END', account_balance)
                self.open_positions.remove(position)
        
        # Calculate statistics
        results = self._calculate_statistics(account_balance)
        
        return results
    
    def _open_position(self, entry_params, current_bar, current_time, mode, params):
        """Open a new position with partial close targets"""
        direction = entry_params['signal']
        entry_price = entry_params['entry_price']
        
        # Apply spread to entry
        if direction == 1:
            entry_price += self.spread_points
        else:
            entry_price -= self.spread_points
        
        # Calculate position size (simplified: 0.01 lot per $1000)
        position_size = max(0.01, self.initial_capital / 100000)
        
        # Calculate TP levels based on mode
        tp_levels = []
        for tp_points in params['tp_levels']:
            if direction == 1:
                tp = entry_price + tp_points
            else:
                tp = entry_price - tp_points
            tp_levels.append(tp)
        
        position = {
            'entry_time': current_time,
            'entry_price': entry_price,
            'stop_loss': entry_params['stop_loss'],
            'tp_levels': tp_levels,
            'tp_percentages': params['tp_percentages'],
            'direction': direction,
            'initial_size': position_size,
            'remaining_size': position_size,
            'tp_hit': [False, False, False],  # Track which TPs hit
            'trailing_active': False,
            'trailing_stop': None,
            'trailing_points': params['trailing_points'],
            'entry_reason': entry_params['entry_reason'],
            'mode': mode,
            'timeout_time': current_time + timedelta(hours=params['timeout_hours']),
            'closed_portions': [],
            'killzone': entry_params['entry_reason'].split('+')[-1] if '+' in entry_params['entry_reason'] else 'unknown'
        }
        
        return position
    
    def _update_position(self, position, current_bar, current_time, params, account_balance):
        """Update position and check for exits"""
        direction = position['direction']
        
        # Check timeout
        if current_time >= position['timeout_time'] and position['remaining_size'] > 0:
            self._close_position(position, current_bar['close'], current_time, 'TIMEOUT', account_balance)
            if position in self.open_positions:
                self.open_positions.remove(position)
            return account_balance
        
        # Check stop loss
        if direction == 1:
            if current_bar['low'] <= position['stop_loss']:
                self._close_position(position, position['stop_loss'], current_time, 'SL', account_balance)
                if position in self.open_positions:
                    self.open_positions.remove(position)
                return account_balance
        else:
            if current_bar['high'] >= position['stop_loss']:
                self._close_position(position, position['stop_loss'], current_time, 'SL', account_balance)
                if position in self.open_positions:
                    self.open_positions.remove(position)
                return account_balance
        
        # Check TP levels for partial closes
        for tp_idx in range(3):
            if not position['tp_hit'][tp_idx]:
                tp_price = position['tp_levels'][tp_idx]
                tp_pct = position['tp_percentages'][tp_idx]
                
                if direction == 1:
                    if current_bar['high'] >= tp_price:
                        # Hit TP level - partial close
                        close_size = position['initial_size'] * tp_pct
                        pnl = self._calculate_pnl(position, tp_price, close_size, current_time)
                        account_balance += pnl
                        
                        position['remaining_size'] -= close_size
                        position['tp_hit'][tp_idx] = True
                        position['closed_portions'].append({
                            'time': current_time,
                            'price': tp_price,
                            'size': close_size,
                            'reason': f'TP{tp_idx+1}',
                            'pnl': pnl
                        })
                        
                        # Activate trailing stop after TP1
                        if tp_idx == 0:
                            position['trailing_active'] = True
                            position['trailing_stop'] = position['entry_price']  # Break even
                else:
                    if current_bar['low'] <= tp_price:
                        # Hit TP level - partial close
                        close_size = position['initial_size'] * tp_pct
                        pnl = self._calculate_pnl(position, tp_price, close_size, current_time)
                        account_balance += pnl
                        
                        position['remaining_size'] -= close_size
                        position['tp_hit'][tp_idx] = True
                        position['closed_portions'].append({
                            'time': current_time,
                            'price': tp_price,
                            'size': close_size,
                            'reason': f'TP{tp_idx+1}',
                            'pnl': pnl
                        })
                        
                        # Activate trailing stop after TP1
                        if tp_idx == 0:
                            position['trailing_active'] = True
                            position['trailing_stop'] = position['entry_price']  # Break even
        
        # Update trailing stop
        if position['trailing_active'] and position['remaining_size'] > 0:
            if direction == 1:
                # Update trailing stop upwards
                new_trailing = current_bar['close'] - position['trailing_points']
                if new_trailing > position['trailing_stop']:
                    position['trailing_stop'] = new_trailing
                
                # Check trailing stop hit
                if current_bar['low'] <= position['trailing_stop']:
                    self._close_position(position, position['trailing_stop'], current_time, 'TRAILING', account_balance)
                    if position in self.open_positions:
                        self.open_positions.remove(position)
                    return account_balance
            else:
                # Update trailing stop downwards
                new_trailing = current_bar['close'] + position['trailing_points']
                if position['trailing_stop'] is None or new_trailing < position['trailing_stop']:
                    position['trailing_stop'] = new_trailing
                
                # Check trailing stop hit
                if current_bar['high'] >= position['trailing_stop']:
                    self._close_position(position, position['trailing_stop'], current_time, 'TRAILING', account_balance)
                    if position in self.open_positions:
                        self.open_positions.remove(position)
                    return account_balance
        
        # Apply swap cost (once per day)
        if hasattr(position, 'last_swap_time'):
            if (current_time - position['last_swap_time']).total_seconds() >= 86400:
                swap_cost = self.swap_per_day * position['remaining_size'] * self.point_value
                account_balance += swap_cost
                position['last_swap_time'] = current_time
        else:
            position['last_swap_time'] = current_time
        
        return account_balance
    
    def _calculate_pnl(self, position, exit_price, size, exit_time):
        """Calculate P&L for a position close"""
        direction = position['direction']
        entry_price = position['entry_price']
        
        # Price difference
        if direction == 1:
            price_diff = exit_price - entry_price
        else:
            price_diff = entry_price - exit_price
        
        # Calculate gross P&L
        gross_pnl = price_diff * size * self.point_value
        
        # Subtract costs
        commission = self.commission_points * size * self.point_value * 2  # Entry + exit
        
        # Swap cost (approximate based on days held)
        days_held = (exit_time - position['entry_time']).total_seconds() / 86400
        swap_cost = self.swap_per_day * size * self.point_value * days_held
        
        net_pnl = gross_pnl - commission + swap_cost  # swap is negative
        
        return net_pnl
    
    def _close_position(self, position, exit_price, exit_time, exit_reason, account_balance):
        """Close remaining position"""
        if position['remaining_size'] <= 0:
            return
        
        pnl = self._calculate_pnl(position, exit_price, position['remaining_size'], exit_time)
        
        # Record trade
        trade_record = {
            'entry_time': position['entry_time'],
            'exit_time': exit_time,
            'direction': 'LONG' if position['direction'] == 1 else 'SHORT',
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'stop_loss': position['stop_loss'],
            'initial_size': position['initial_size'],
            'remaining_size': position['remaining_size'],
            'total_pnl': pnl + sum(p['pnl'] for p in position['closed_portions']),
            'pnl': pnl,
            'exit_reason': exit_reason,
            'entry_reason': position['entry_reason'],
            'mode': position['mode'],
            'killzone': position['killzone'],
            'tp1_hit': position['tp_hit'][0],
            'tp2_hit': position['tp_hit'][1],
            'tp3_hit': position['tp_hit'][2],
            'partial_closes': position['closed_portions']
        }
        
        self.trades.append(trade_record)
        position['remaining_size'] = 0
    
    def _calculate_statistics(self, final_balance):
        """Calculate comprehensive backtest statistics"""
        if len(self.trades) == 0:
            return self._empty_results()
        
        trades_df = pd.DataFrame(self.trades)
        
        # Overall metrics
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['total_pnl'] > 0]
        losing_trades = trades_df[trades_df['total_pnl'] <= 0]
        
        num_winning = len(winning_trades)
        num_losing = len(losing_trades)
        win_rate = (num_winning / total_trades * 100) if total_trades > 0 else 0
        
        total_return = final_balance - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Calculate max drawdown
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        
        # Profit factor
        gross_profit = winning_trades['total_pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['total_pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Breakdowns
        breakdown_by_direction = self._breakdown_by_column(trades_df, 'direction')
        breakdown_by_mode = self._breakdown_by_column(trades_df, 'mode')
        breakdown_by_killzone = self._breakdown_by_column(trades_df, 'killzone')
        breakdown_by_exit = self._breakdown_by_column(trades_df, 'exit_reason')
        
        # ICT pattern breakdown
        ict_patterns = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
        for _, trade in trades_df.iterrows():
            reason = trade['entry_reason']
            for pattern in ['LiqSweep', 'OTE', 'PO3', 'EqualHighs', 'EqualLows']:
                if pattern in reason:
                    ict_patterns[pattern]['count'] += 1
                    ict_patterns[pattern]['pnl'] += trade['total_pnl']
                    if trade['total_pnl'] > 0:
                        ict_patterns[pattern]['wins'] += 1
        
        return {
            'total_trades': total_trades,
            'winning_trades': num_winning,
            'losing_trades': num_losing,
            'win_rate': win_rate,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'final_balance': final_balance,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'avg_win': winning_trades['total_pnl'].mean() if len(winning_trades) > 0 else 0,
            'avg_loss': losing_trades['total_pnl'].mean() if len(losing_trades) > 0 else 0,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'breakdown_by_direction': breakdown_by_direction,
            'breakdown_by_mode': breakdown_by_mode,
            'breakdown_by_killzone': breakdown_by_killzone,
            'breakdown_by_exit': breakdown_by_exit,
            'ict_patterns': dict(ict_patterns)
        }
    
    def _breakdown_by_column(self, trades_df, column):
        """Create breakdown statistics by a column"""
        breakdown = {}
        for value in trades_df[column].unique():
            subset = trades_df[trades_df[column] == value]
            breakdown[value] = {
                'trades': len(subset),
                'wins': len(subset[subset['total_pnl'] > 0]),
                'losses': len(subset[subset['total_pnl'] <= 0]),
                'win_rate': len(subset[subset['total_pnl'] > 0]) / len(subset) * 100 if len(subset) > 0 else 0,
                'total_pnl': subset['total_pnl'].sum(),
                'avg_pnl': subset['total_pnl'].mean()
            }
        return breakdown
    
    def _empty_results(self):
        """Return empty results structure"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_return': 0,
            'total_return_pct': 0,
            'final_balance': self.initial_capital,
            'max_drawdown': 0,
            'profit_factor': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'breakdown_by_direction': {},
            'breakdown_by_mode': {},
            'breakdown_by_killzone': {},
            'breakdown_by_exit': {},
            'ict_patterns': {}
        }
    
    def print_results(self, results: dict):
        """Print detailed backtest results"""
        print("\n" + "="*80)
        print("ICT PRICE ACTION STRATEGY - ENHANCED BACKTEST RESULTS")
        print("="*80)
        print(f"\n{'OVERALL PERFORMANCE':^80}")
        print("-"*80)
        print(f"  Total Trades:      {results['total_trades']}")
        print(f"  Winning Trades:    {results['winning_trades']}")
        print(f"  Losing Trades:     {results['losing_trades']}")
        print(f"  Win Rate:          {results['win_rate']:.2f}%")
        print(f"\n  Initial Capital:   ${self.initial_capital:,.2f}")
        print(f"  Final Balance:     ${results['final_balance']:,.2f}")
        print(f"  Total Return:      ${results['total_return']:,.2f}")
        print(f"  Return %:          {results['total_return_pct']:.2f}%")
        print(f"\n  Max Drawdown:      {results['max_drawdown']:.2f}%")
        print(f"  Profit Factor:     {results['profit_factor']:.2f}")
        print(f"\n  Gross Profit:      ${results['gross_profit']:,.2f}")
        print(f"  Gross Loss:        ${results['gross_loss']:,.2f}")
        print(f"  Average Win:       ${results['avg_win']:,.2f}")
        print(f"  Average Loss:      ${results['avg_loss']:,.2f}")
        
        # Breakdown by direction
        if results['breakdown_by_direction']:
            print(f"\n{'BREAKDOWN BY DIRECTION':^80}")
            print("-"*80)
            for direction, stats in results['breakdown_by_direction'].items():
                print(f"\n  {direction}:")
                print(f"    Trades: {stats['trades']} | Wins: {stats['wins']} | Losses: {stats['losses']}")
                print(f"    Win Rate: {stats['win_rate']:.2f}% | Total PnL: ${stats['total_pnl']:.2f}")
        
        # Breakdown by mode
        if results['breakdown_by_mode']:
            print(f"\n{'BREAKDOWN BY MODE':^80}")
            print("-"*80)
            for mode, stats in results['breakdown_by_mode'].items():
                print(f"\n  {mode}:")
                print(f"    Trades: {stats['trades']} | Wins: {stats['wins']} | Losses: {stats['losses']}")
                print(f"    Win Rate: {stats['win_rate']:.2f}% | Total PnL: ${stats['total_pnl']:.2f}")
        
        # Breakdown by killzone
        if results['breakdown_by_killzone']:
            print(f"\n{'BREAKDOWN BY KILLZONE':^80}")
            print("-"*80)
            for kz, stats in results['breakdown_by_killzone'].items():
                print(f"\n  {kz}:")
                print(f"    Trades: {stats['trades']} | Wins: {stats['wins']} | Losses: {stats['losses']}")
                print(f"    Win Rate: {stats['win_rate']:.2f}% | Total PnL: ${stats['total_pnl']:.2f}")
        
        # Breakdown by exit reason
        if results['breakdown_by_exit']:
            print(f"\n{'BREAKDOWN BY EXIT TYPE':^80}")
            print("-"*80)
            for exit_reason, stats in results['breakdown_by_exit'].items():
                print(f"\n  {exit_reason}:")
                print(f"    Trades: {stats['trades']} | Wins: {stats['wins']} | Losses: {stats['losses']}")
                print(f"    Win Rate: {stats['win_rate']:.2f}% | Total PnL: ${stats['total_pnl']:.2f}")
        
        # ICT patterns
        if results['ict_patterns']:
            print(f"\n{'ICT PATTERNS PERFORMANCE':^80}")
            print("-"*80)
            for pattern, stats in results['ict_patterns'].items():
                win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
                print(f"\n  {pattern}:")
                print(f"    Count: {stats['count']} | Wins: {stats['wins']} | Win Rate: {win_rate:.2f}%")
                print(f"    Total PnL: ${stats['pnl']:.2f}")
        
        print("\n" + "="*80)
    
    def save_trades(self, filepath: str):
        """Save trade details to CSV"""
        if len(self.trades) > 0:
            trades_df = pd.DataFrame(self.trades)
            # Expand partial closes info
            trades_df['partial_closes_count'] = trades_df['partial_closes'].apply(len)
            trades_df = trades_df.drop('partial_closes', axis=1)
            trades_df.to_csv(filepath, index=False)
            print(f"\nTrade details saved to: {filepath}")
    
    def plot_results(self, df: pd.DataFrame, results: dict, save_path: str = None):
        """Plot backtest results"""
        fig, axes = plt.subplots(2, 1, figsize=(15, 10))
        
        # Plot 1: Equity curve
        ax1 = axes[0]
        ax1.plot(self.equity_curve, label='Equity', color='blue', linewidth=2)
        ax1.axhline(y=self.initial_capital, color='gray', linestyle='--', label='Initial Capital')
        ax1.set_title('ICT Price Action Strategy - Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Account Balance ($)')
        ax1.set_xlabel('Candle Index')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Trade distribution
        ax2 = axes[1]
        if len(self.trades) > 0:
            trades_df = pd.DataFrame(self.trades)
            ax2.bar(range(len(trades_df)), trades_df['total_pnl'], 
                   color=['green' if x > 0 else 'red' for x in trades_df['total_pnl']])
            ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax2.set_title('Trade P&L Distribution', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Trade Number')
            ax2.set_ylabel('P&L ($)')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"\nPlot saved to: {save_path}")
        
        plt.close()


def main():
    """Main function to run backtest"""
    
    # Configuration
    CSV_FILE = '../XAUUSD_1H_MT5_20241227_20251227.csv'
    INITIAL_CAPITAL = 10000
    
    print("="*80)
    print("ICT PRICE ACTION STRATEGY - ENHANCED BACKTEST")
    print("="*80)
    
    # Load data
    print(f"\nLoading data from: {CSV_FILE}")
    df = load_data(CSV_FILE)
    
    # Initialize strategy
    print("\nInitializing Enhanced ICT Price Action Strategy...")
    strategy = ICTPriceActionStrategy(
        risk_reward_ratio=2.0,
        risk_per_trade=0.02,
        swing_length=10,
        fvg_threshold=0.001,
        liquidity_lookback=20,
        use_kill_zones=True,
        fib_levels=[0.618, 0.786],
        killzone_only=False,  # Don't filter by killzone to get more signals
        premium_discount_filter=False,  # Don't filter by premium/discount initially
        min_liquidity_sweep=2
    )
    
    # Initialize backtester
    backtester = EnhancedICTBacktester(
        initial_capital=INITIAL_CAPITAL,
        spread_points=2.0,
        commission_points=0.5,
        swap_per_day=-0.3,
        max_positions=5
    )
    
    # Run backtest
    results = backtester.run_backtest(df, strategy)
    
    # Print results
    backtester.print_results(results)
    
    # Save results
    backtester.save_trades('ict_strategy_trades.csv')
    backtester.plot_results(df, results, 'ict_strategy_backtest_results.png')
    
    print("\n✅ Enhanced backtest completed successfully!")
    print("\nFiles generated:")
    print("  - ict_strategy_trades.csv")
    print("  - ict_strategy_backtest_results.png")


if __name__ == '__main__':
    main()
