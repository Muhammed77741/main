"""
Backtest script for ICT Price Action Strategy
Tests the strategy on historical XAUUSD data from CSV
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

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
    # Read CSV with proper encoding (MT5 uses UTF-16-LE)
    df = pd.read_csv(filepath, encoding='utf-16-le', header=None)
    
    # Set column names based on MT5 format
    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'tick_volume', 'spread']
    
    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y.%m.%d %H:%M')
    df.set_index('timestamp', inplace=True)
    
    # Ensure numeric types
    for col in ['open', 'high', 'low', 'close', 'tick_volume', 'spread']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop any NaN rows
    df.dropna(inplace=True)
    
    print(f"Loaded {len(df)} candles from {df.index[0]} to {df.index[-1]}")
    
    return df


class ICTBacktester:
    """Backtester for ICT Price Action Strategy"""
    
    def __init__(
        self,
        initial_capital: float = 10000,
        commission: float = 0.001,  # 0.1% per trade
        slippage: float = 0.0005,  # 0.05% slippage
        use_partial_close: bool = True,  # NEW: Use 3 TP levels
        use_trailing_stop: bool = True  # NEW: Trailing stop after TP1
    ):
        """
        Initialize backtester
        
        Args:
            initial_capital: Starting capital
            commission: Commission per trade (as decimal)
            slippage: Slippage per trade (as decimal)
            use_partial_close: Use 3 TP levels with partial closes
            use_trailing_stop: Enable trailing stop after TP1
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.trades = []
        self.equity_curve = []
        self.use_partial_close = use_partial_close
        self.use_trailing_stop = use_trailing_stop
        
        # Partial close percentages
        self.tp1_pct = 0.4  # Close 40% at TP1
        self.tp2_pct = 0.3  # Close 30% at TP2
        self.tp3_pct = 0.3  # Close 30% at TP3
        
    def run_backtest(self, df: pd.DataFrame, strategy: ICTPriceActionStrategy) -> dict:
        """
        Run backtest on historical data
        
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
        position = None
        
        self.trades = []
        self.equity_curve = [self.initial_capital]
        
        print(f"\nRunning backtest...")
        print(f"Total signals: {(df_with_signals['signal'] != 0).sum()}")
        
        for i in range(len(df_with_signals)):
            current_time = df_with_signals.index[i]
            current_bar = df_with_signals.iloc[i]
            
            # Check if we have an open position
            if position is not None:
                direction = position['direction']
                
                # Check for partial TP levels
                if self.use_partial_close:
                    # TP1 check
                    if not position['tp1_hit']:
                        if (direction == 1 and current_bar['high'] >= position['tp1']) or \
                           (direction == -1 and current_bar['low'] <= position['tp1']):
                            # Close 40% at TP1
                            close_size = position['position_size'] * self.tp1_pct
                            pnl = self._calculate_partial_pnl(position, position['tp1'], close_size)
                            account_balance += pnl
                            
                            position['remaining_size'] -= close_size
                            position['tp1_hit'] = True
                            position['partial_closes'].append({
                                'time': current_time,
                                'level': 'TP1',
                                'price': position['tp1'],
                                'size': close_size,
                                'pnl': pnl
                            })
                            
                            # Activate trailing stop after TP1
                            if self.use_trailing_stop:
                                position['trailing_active'] = True
                    
                    # TP2 check
                    if position['tp1_hit'] and not position['tp2_hit']:
                        if (direction == 1 and current_bar['high'] >= position['tp2']) or \
                           (direction == -1 and current_bar['low'] <= position['tp2']):
                            # Close 30% at TP2
                            close_size = position['position_size'] * self.tp2_pct
                            pnl = self._calculate_partial_pnl(position, position['tp2'], close_size)
                            account_balance += pnl
                            
                            position['remaining_size'] -= close_size
                            position['tp2_hit'] = True
                            position['partial_closes'].append({
                                'time': current_time,
                                'level': 'TP2',
                                'price': position['tp2'],
                                'size': close_size,
                                'pnl': pnl
                            })
                    
                    # TP3 check - close remaining position
                    if position['tp2_hit'] and not position['tp3_hit']:
                        if (direction == 1 and current_bar['high'] >= position['tp3']) or \
                           (direction == -1 and current_bar['low'] <= position['tp3']):
                            # Close remaining 30% at TP3
                            exit_price = position['tp3']
                            exit_reason = 'TP3'
                            self._close_position(position, exit_price, current_time, exit_reason, account_balance)
                            account_balance = self._update_balance(position, exit_price, account_balance)
                            position = None
                            continue
                    
                    # Update trailing stop if active
                    if position['trailing_active'] and position is not None:
                        if direction == 1:
                            new_trailing = current_bar['high'] - position['trailing_distance']
                            position['stop_loss'] = max(position['stop_loss'], new_trailing)
                        else:
                            new_trailing = current_bar['low'] + position['trailing_distance']
                            position['stop_loss'] = min(position['stop_loss'], new_trailing)
                
                # Check stop loss (on remaining position)
                if position is not None:
                    if direction == 1:  # Long position
                        if current_bar['low'] <= position['stop_loss']:
                            exit_price = position['stop_loss']
                            exit_reason = 'SL'
                            self._close_position(position, exit_price, current_time, exit_reason, account_balance)
                            account_balance = self._update_balance(position, exit_price, account_balance)
                            position = None
                    elif direction == -1:  # Short position
                        if current_bar['high'] >= position['stop_loss']:
                            exit_price = position['stop_loss']
                            exit_reason = 'SL'
                            self._close_position(position, exit_price, current_time, exit_reason, account_balance)
                            account_balance = self._update_balance(position, exit_price, account_balance)
                            position = None
                
                # If not using partial close, check regular TP
                if not self.use_partial_close and position is not None:
                    if direction == 1:
                        if current_bar['high'] >= position['take_profit']:
                            exit_price = position['take_profit']
                            exit_reason = 'TP'
                            self._close_position(position, exit_price, current_time, exit_reason, account_balance)
                            account_balance = self._update_balance(position, exit_price, account_balance)
                            position = None
                    elif direction == -1:
                        if current_bar['low'] <= position['take_profit']:
                            exit_price = position['take_profit']
                            exit_reason = 'TP'
                            self._close_position(position, exit_price, current_time, exit_reason, account_balance)
                            account_balance = self._update_balance(position, exit_price, account_balance)
                            position = None
            
            # Check for new signals (only if no position)
            if position is None and current_bar['signal'] != 0:
                # Get entry parameters
                entry_params = strategy.get_entry_parameters(df_with_signals, i, account_balance)
                
                if entry_params is not None:
                    # Apply slippage to entry
                    entry_price = entry_params['entry_price']
                    if entry_params['signal'] == 1:
                        entry_price *= (1 + self.slippage)
                    else:
                        entry_price *= (1 - self.slippage)
                    
                    # Calculate TP levels for partial close
                    risk = abs(entry_price - entry_params['stop_loss'])
                    
                    position = {
                        'entry_time': current_time,
                        'entry_price': entry_price,
                        'stop_loss': entry_params['stop_loss'],
                        'take_profit': entry_params['take_profit'],
                        'position_size': entry_params['position_size'],
                        'remaining_size': entry_params['position_size'],
                        'direction': entry_params['signal'],
                        'entry_reason': entry_params['entry_reason'],
                        'signal_confidence': entry_params.get('signal_confidence', 'high'),
                        'risk_reward_ratio': entry_params.get('risk_reward_ratio', 2.5),
                        'tp1_hit': False,
                        'tp2_hit': False,
                        'tp3_hit': False,
                        'trailing_active': False,
                        'trailing_distance': 20,  # 20 points trailing distance
                        'partial_closes': []
                    }
                    
                    # Calculate TP levels
                    if self.use_partial_close:
                        if position['direction'] == 1:  # LONG
                            position['tp1'] = entry_price + (risk * 1.0)  # 1:1
                            position['tp2'] = entry_price + (risk * 2.0)  # 1:2
                            position['tp3'] = entry_price + (risk * 3.0)  # 1:3
                        else:  # SHORT
                            position['tp1'] = entry_price - (risk * 1.0)
                            position['tp2'] = entry_price - (risk * 2.0)
                            position['tp3'] = entry_price - (risk * 3.0)
                    else:
                        position['tp1'] = entry_params['take_profit']
                        position['tp2'] = entry_params['take_profit']
                        position['tp3'] = entry_params['take_profit']
            
            # Update equity curve
            if position is not None:
                # Calculate unrealized P&L
                if position['direction'] == 1:
                    unrealized_pnl = (current_bar['close'] - position['entry_price']) * position['position_size']
                else:
                    unrealized_pnl = (position['entry_price'] - current_bar['close']) * position['position_size']
                self.equity_curve.append(account_balance + unrealized_pnl)
            else:
                self.equity_curve.append(account_balance)
        
        # Close any remaining position at the end
        if position is not None:
            exit_price = df_with_signals.iloc[-1]['close']
            exit_time = df_with_signals.index[-1]
            self._close_position(position, exit_price, exit_time, 'END', account_balance)
            account_balance = self._update_balance(position, exit_price, account_balance)
        
        # Calculate statistics
        results = self._calculate_statistics(account_balance)
        
        return results
    
    def _calculate_partial_pnl(self, position, exit_price, close_size):
        """Calculate P&L for a partial close"""
        if position['direction'] == 1:
            pnl = (exit_price - position['entry_price']) * close_size
        else:
            pnl = (position['entry_price'] - exit_price) * close_size
        
        # Apply commission
        commission_cost = exit_price * close_size * self.commission
        pnl -= commission_cost
        
        return pnl
    
    def _close_position(self, position, exit_price, exit_time, exit_reason, account_balance):
        """Close a position and record the trade"""
        # Use remaining size for final close (if partial closes happened)
        close_size = position.get('remaining_size', position['position_size'])
        
        if position['direction'] == 1:
            pnl = (exit_price - position['entry_price']) * close_size
        else:
            pnl = (position['entry_price'] - exit_price) * close_size
        
        # Apply commission
        commission_cost = (position['entry_price'] * position['position_size'] * self.commission +
                          exit_price * close_size * self.commission)
        pnl -= commission_cost
        
        # Add partial close PnLs
        total_partial_pnl = sum([pc['pnl'] for pc in position.get('partial_closes', [])])
        total_pnl = pnl + total_partial_pnl
        
        trade_record = {
            'entry_time': position['entry_time'],
            'exit_time': exit_time,
            'direction': 'LONG' if position['direction'] == 1 else 'SHORT',
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'stop_loss': position['stop_loss'],
            'take_profit': position['take_profit'],
            'position_size': position['position_size'],
            'pnl': total_pnl,
            'pnl_pct': (total_pnl / (position['entry_price'] * position['position_size'])) * 100,
            'exit_reason': exit_reason,
            'entry_reason': position['entry_reason'],
            'signal_confidence': position.get('signal_confidence', 'high'),
            'risk_reward_ratio': position.get('risk_reward_ratio', 2.5),
            'partial_closes': len(position.get('partial_closes', []))
        }
        
        self.trades.append(trade_record)
    
    def _update_balance(self, position, exit_price, account_balance):
        """Update account balance after closing position"""
        # Use remaining size for final close
        close_size = position.get('remaining_size', position['position_size'])
        
        if position['direction'] == 1:
            pnl = (exit_price - position['entry_price']) * close_size
        else:
            pnl = (position['entry_price'] - exit_price) * close_size
        
        # Apply commission
        commission_cost = (position['entry_price'] * position['position_size'] * self.commission +
                          exit_price * close_size * self.commission)
        pnl -= commission_cost
        
        # Note: partial close PnLs already added to account_balance during execution
        return account_balance + pnl
    
    def _calculate_statistics(self, final_balance):
        """Calculate backtest statistics"""
        if len(self.trades) == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'total_return_pct': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0
            }
        
        trades_df = pd.DataFrame(self.trades)
        
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] <= 0]
        
        total_trades = len(trades_df)
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
        
        # Calculate Sharpe ratio (assuming daily returns)
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 0 and returns.std() != 0 else 0
        
        # Profit factor
        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Average trade metrics
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        
        # Confidence level statistics (if available)
        confidence_stats = {}
        if 'signal_confidence' in trades_df.columns:
            for conf_level in ['high', 'medium', 'low']:
                conf_trades = trades_df[trades_df['signal_confidence'] == conf_level]
                if len(conf_trades) > 0:
                    conf_wins = (conf_trades['pnl'] > 0).sum()
                    confidence_stats[f'{conf_level}_conf_trades'] = len(conf_trades)
                    confidence_stats[f'{conf_level}_conf_wr'] = (conf_wins / len(conf_trades) * 100)
                    confidence_stats[f'{conf_level}_conf_avg_pnl'] = conf_trades['pnl'].mean()
                else:
                    confidence_stats[f'{conf_level}_conf_trades'] = 0
                    confidence_stats[f'{conf_level}_conf_wr'] = 0
                    confidence_stats[f'{conf_level}_conf_avg_pnl'] = 0
        
        results = {
            'total_trades': total_trades,
            'winning_trades': num_winning,
            'losing_trades': num_losing,
            'win_rate': win_rate,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'final_balance': final_balance,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss
        }
        
        # Add confidence stats
        results.update(confidence_stats)
        
        return results
    
    def plot_results(self, df: pd.DataFrame, results: dict, save_path: str = None):
        """
        Plot backtest results
        
        Args:
            df: Original DataFrame
            results: Backtest results
            save_path: Path to save the plot
        """
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        
        # Plot 1: Price and trades
        ax1 = axes[0]
        ax1.plot(df.index, df['close'], label='Price', alpha=0.7, linewidth=1)
        
        # Plot trades
        trades_df = pd.DataFrame(self.trades)
        if len(trades_df) > 0:
            long_entries = trades_df[trades_df['direction'] == 'LONG']
            short_entries = trades_df[trades_df['direction'] == 'SHORT']
            
            for _, trade in long_entries.iterrows():
                ax1.scatter(trade['entry_time'], trade['entry_price'], color='green', marker='^', s=100, alpha=0.7)
                ax1.scatter(trade['exit_time'], trade['exit_price'], color='red', marker='v', s=100, alpha=0.7)
            
            for _, trade in short_entries.iterrows():
                ax1.scatter(trade['entry_time'], trade['entry_price'], color='red', marker='v', s=100, alpha=0.7)
                ax1.scatter(trade['exit_time'], trade['exit_price'], color='green', marker='^', s=100, alpha=0.7)
        
        ax1.set_title('ICT Price Action Strategy - Price & Trades', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Equity curve
        ax2 = axes[1]
        ax2.plot(self.equity_curve, label='Equity', color='blue', linewidth=2)
        ax2.axhline(y=self.initial_capital, color='gray', linestyle='--', label='Initial Capital')
        ax2.set_title('Equity Curve', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Account Balance ($)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Trade distribution
        ax3 = axes[2]
        if len(trades_df) > 0:
            ax3.bar(range(len(trades_df)), trades_df['pnl'], 
                   color=['green' if x > 0 else 'red' for x in trades_df['pnl']])
            ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax3.set_title('Trade P&L Distribution', fontsize=14, fontweight='bold')
            ax3.set_xlabel('Trade Number')
            ax3.set_ylabel('P&L ($)')
            ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"\nPlot saved to: {save_path}")
        
        plt.close()
    
    def print_results(self, results: dict):
        """Print backtest results"""
        print("\n" + "="*60)
        print("ICT PRICE ACTION STRATEGY - BACKTEST RESULTS")
        print("="*60)
        print(f"\nPerformance Metrics:")
        print(f"  Total Trades:      {results['total_trades']}")
        print(f"  Winning Trades:    {results['winning_trades']}")
        print(f"  Losing Trades:     {results['losing_trades']}")
        print(f"  Win Rate:          {results['win_rate']:.2f}%")
        print(f"\nReturns:")
        print(f"  Initial Capital:   ${self.initial_capital:,.2f}")
        print(f"  Final Balance:     ${results['final_balance']:,.2f}")
        print(f"  Total Return:      ${results['total_return']:,.2f}")
        print(f"  Return %:          {results['total_return_pct']:.2f}%")
        print(f"\nRisk Metrics:")
        print(f"  Max Drawdown:      {results['max_drawdown']:.2f}%")
        print(f"  Sharpe Ratio:      {results['sharpe_ratio']:.2f}")
        print(f"  Profit Factor:     {results['profit_factor']:.2f}")
        print(f"\nTrade Analytics:")
        print(f"  Gross Profit:      ${results['gross_profit']:,.2f}")
        print(f"  Gross Loss:        ${results['gross_loss']:,.2f}")
        print(f"  Average Win:       ${results['avg_win']:,.2f}")
        print(f"  Average Loss:      ${results['avg_loss']:,.2f}")
        
        # Print confidence level statistics if available
        if 'high_conf_trades' in results:
            print(f"\nSignal Confidence Breakdown:")
            print(f"  High Confidence:   {results['high_conf_trades']} trades, "
                  f"{results['high_conf_wr']:.1f}% WR, "
                  f"${results['high_conf_avg_pnl']:.2f} avg")
            print(f"  Medium Confidence: {results['medium_conf_trades']} trades, "
                  f"{results['medium_conf_wr']:.1f}% WR, "
                  f"${results['medium_conf_avg_pnl']:.2f} avg")
            print(f"  Low Confidence:    {results['low_conf_trades']} trades, "
                  f"{results['low_conf_wr']:.1f}% WR, "
                  f"${results['low_conf_avg_pnl']:.2f} avg")
        
        print("="*60)
    
    def save_trades(self, filepath: str):
        """Save trade details to CSV"""
        if len(self.trades) > 0:
            trades_df = pd.DataFrame(self.trades)
            trades_df.to_csv(filepath, index=False)
            print(f"\nTrade details saved to: {filepath}")


def main():
    """Main function to run backtest"""
    
    # Configuration
    CSV_FILE = '../XAUUSD_1H_MT5.csv'
    INITIAL_CAPITAL = 10000
    RISK_PER_TRADE = 0.02  # 2%
    RISK_REWARD_RATIO = 2.5  # Baseline for adaptive (will adjust 2.0-3.0)
    
    print("="*60)
    print("ICT PRICE ACTION STRATEGY BACKTEST (IMPROVED)")
    print("="*60)
    
    # Load data
    print(f"\nLoading data from: {CSV_FILE}")
    df = load_data(CSV_FILE)
    
    # Initialize strategy with NEW improvements
    print("\nInitializing IMPROVED ICT Price Action Strategy...")
    print("  ✓ Flexible entry conditions (Tier 1/2/3)")
    print("  ✓ Expanded kill zones (15h/day)")
    print("  ✓ ATR-based adaptive R:R (2.0-3.0)")
    print("  ✓ Premium/Discount zone filter")
    print("  ✓ Volume confirmation")
    
    strategy = ICTPriceActionStrategy(
        risk_reward_ratio=RISK_REWARD_RATIO,
        risk_per_trade=RISK_PER_TRADE,
        swing_length=10,
        fvg_threshold=0.001,  # 0.1% minimum gap
        liquidity_lookback=20,
        use_kill_zones=True,  # Expanded kill zones
        use_adaptive_rr=True,  # NEW: ATR-based R:R
        use_premium_discount=True,  # NEW: Premium/discount filter
        use_volume_confirmation=True,  # NEW: Volume filter
        use_flexible_entry=True  # NEW: Tier-based entries
    )
    
    # Initialize backtester with NEW features
    print("\nInitializing backtester with:")
    print("  ✓ 3 TP levels (40%/30%/30% partial close)")
    print("  ✓ Trailing stop after TP1")
    
    backtester = ICTBacktester(
        initial_capital=INITIAL_CAPITAL,
        commission=0.001,  # 0.1%
        slippage=0.0005,  # 0.05%
        use_partial_close=True,  # NEW: 3 TP levels
        use_trailing_stop=True  # NEW: Trailing stop
    )
    
    # Run backtest
    results = backtester.run_backtest(df, strategy)
    
    # Print results
    backtester.print_results(results)
    
    # Save results with new filename
    backtester.save_trades('ict_strategy_improved_trades.csv')
    backtester.plot_results(df, results, 'ict_strategy_improved_backtest_results.png')
    
    print("\n✅ IMPROVED Backtest completed successfully!")
    print("\nFiles generated:")
    print("  - ict_strategy_improved_trades.csv")
    print("  - ict_strategy_improved_backtest_results.png")


if __name__ == '__main__':
    main()
