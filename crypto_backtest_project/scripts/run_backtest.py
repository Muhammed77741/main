"""
Main script to run SMC strategy backtests
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smc_strategy import SMCStrategy
from backtester import Backtester
from data_loader import generate_sample_data, download_data_yfinance, validate_data


def plot_results(df: pd.DataFrame, equity_curve: list, trades: list, symbol: str = "Asset"):
    """
    Plot backtest results

    Args:
        df: DataFrame with OHLC and signals
        equity_curve: List of equity values
        trades: List of trades
        symbol: Asset symbol for title
    """
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12))

    # Plot 1: Price and Entry/Exit points
    ax1.plot(df.index, df['close'], label='Close Price', color='black', linewidth=1)

    # Plot buy signals
    buy_signals = df[df['signal'] == 1]
    ax1.scatter(buy_signals.index, buy_signals['close'], color='green', marker='^', s=100, label='Buy Signal', zorder=5)

    # Plot sell signals
    sell_signals = df[df['signal'] == -1]
    ax1.scatter(sell_signals.index, sell_signals['close'], color='red', marker='v', s=100, label='Sell Signal', zorder=5)

    # Plot Order Blocks
    bullish_ob = df[df['bullish_ob']]
    ax1.scatter(bullish_ob.index, bullish_ob['close'], color='lightgreen', marker='s', s=50, alpha=0.5, label='Bullish OB')

    bearish_ob = df[df['bearish_ob']]
    ax1.scatter(bearish_ob.index, bearish_ob['close'], color='lightcoral', marker='s', s=50, alpha=0.5, label='Bearish OB')

    ax1.set_title(f'{symbol} - SMC Trading Strategy', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Equity Curve
    ax2.plot(equity_curve, label='Equity Curve', color='blue', linewidth=2)
    ax2.axhline(y=equity_curve[0], color='gray', linestyle='--', label='Initial Capital')
    ax2.set_title('Equity Curve', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Trade Number')
    ax2.set_ylabel('Equity ($)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Trade PnL
    if trades:
        trade_pnls = [t['pnl'] for t in trades]
        colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnls]
        ax3.bar(range(len(trade_pnls)), trade_pnls, color=colors, alpha=0.6)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax3.set_title('Trade PnL Distribution', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Trade Number')
        ax3.set_ylabel('PnL ($)')
        ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('smc_backtest_results.png', dpi=150, bbox_inches='tight')
    print("\n📊 Chart saved as 'smc_backtest_results.png'")
    # plt.show()


def save_trades_to_csv(trades: list, filename: str = 'smc_trades.csv'):
    """
    Save trades to CSV file

    Args:
        trades: List of trade dictionaries
        filename: Output filename
    """
    if not trades:
        print("No trades to save")
        return

    df_trades = pd.DataFrame(trades)
    df_trades.to_csv(filename, index=False)
    print(f"\n💾 Trades saved to '{filename}'")


def run_optimization(df: pd.DataFrame, param_grid: dict):
    """
    Run parameter optimization

    Args:
        df: DataFrame with OHLC data
        param_grid: Dictionary with parameter ranges
    """
    print("\n🔍 Running Parameter Optimization...")

    best_return = -np.inf
    best_params = None
    results = []

    total_combinations = len(param_grid['swing_length']) * len(param_grid['risk_reward_ratio'])
    current = 0

    for swing_length in param_grid['swing_length']:
        for rr_ratio in param_grid['risk_reward_ratio']:
            current += 1
            print(f"  Testing {current}/{total_combinations}: swing={swing_length}, rr={rr_ratio:.1f}", end='\r')

            # Create strategy
            strategy = SMCStrategy(
                risk_reward_ratio=rr_ratio,
                swing_length=swing_length
            )

            # Run strategy
            df_test = strategy.run_strategy(df.copy())

            # Run backtest
            backtester = Backtester(initial_capital=10000)
            stats = backtester.run(df_test)

            # Store results
            results.append({
                'swing_length': swing_length,
                'risk_reward_ratio': rr_ratio,
                'total_return_pct': stats['total_return_pct'],
                'win_rate': stats['win_rate'],
                'sharpe_ratio': stats['sharpe_ratio'],
                'max_drawdown': stats['max_drawdown'],
                'total_trades': stats['total_trades']
            })

            # Track best
            if stats['total_return_pct'] > best_return:
                best_return = stats['total_return_pct']
                best_params = {
                    'swing_length': swing_length,
                    'risk_reward_ratio': rr_ratio
                }

    print("\n")
    print("\n🏆 OPTIMIZATION RESULTS")
    print("="*60)
    print(f"Best Return: {best_return:.2f}%")
    print(f"Best Parameters: {best_params}")

    # Save results
    df_results = pd.DataFrame(results)
    df_results.to_csv('optimization_results.csv', index=False)
    print(f"\n💾 Optimization results saved to 'optimization_results.csv'")

    return best_params


def main():
    """Main execution function"""
    print("\n🚀 SMC TRADING STRATEGY BACKTESTER")
    print("="*60)

    # Configuration
    USE_REAL_DATA = False  # Set to True to use Yahoo Finance data
    SYMBOL = "BTC-USD"
    PERIOD = "1y"
    RUN_OPTIMIZATION = False  # Set to True to run parameter optimization

    # Load data
    print("\n📥 Loading data...")
    if USE_REAL_DATA:
        print(f"  Downloading {SYMBOL} data from Yahoo Finance...")
        df = download_data_yfinance(SYMBOL, period=PERIOD)
        if df is None:
            print("  ⚠️  Failed to download data, using sample data instead")
            df = generate_sample_data(days=365)
    else:
        print("  Generating sample BTC-like data (365 days)...")
        df = generate_sample_data(days=365, start_price=50000, volatility=0.025)

    # Validate data
    if not validate_data(df):
        print("❌ Data validation failed")
        return

    print(f"  ✅ Loaded {len(df)} candles")
    print(f"  Date range: {df.index[0]} to {df.index[-1]}")

    if RUN_OPTIMIZATION:
        # Parameter optimization
        param_grid = {
            'swing_length': [5, 10, 15, 20],
            'risk_reward_ratio': [1.5, 2.0, 2.5, 3.0]
        }
        best_params = run_optimization(df, param_grid)

        # Use best parameters for final run
        swing_length = best_params['swing_length']
        risk_reward_ratio = best_params['risk_reward_ratio']
    else:
        # Default parameters
        swing_length = 10
        risk_reward_ratio = 2.0

    # Create and run strategy
    print("\n⚙️  Running SMC Strategy...")
    print(f"  Swing Length: {swing_length}")
    print(f"  Risk/Reward Ratio: {risk_reward_ratio}")

    strategy = SMCStrategy(
        risk_reward_ratio=risk_reward_ratio,
        risk_per_trade=0.02,
        use_order_blocks=True,
        use_fvg=True,
        use_liquidity=True,
        swing_length=swing_length
    )

    df_result = strategy.run_strategy(df)

    # Count signals
    buy_signals = (df_result['signal'] == 1).sum()
    sell_signals = (df_result['signal'] == -1).sum()
    print(f"  ✅ Generated {buy_signals} BUY and {sell_signals} SELL signals")

    # Run backtest
    print("\n📊 Running Backtest...")
    backtester = Backtester(
        initial_capital=10000,
        commission=0.001,
        slippage=0.0005,
        risk_per_trade=0.02
    )

    stats = backtester.run(df_result)

    # Print results
    backtester.print_results(stats)

    # Save trades
    if stats['total_trades'] > 0:
        save_trades_to_csv(stats['trades'])

        # Plot results
        print("\n📈 Generating charts...")
        plot_results(df_result, backtester.equity_curve, stats['trades'], SYMBOL)

    print("\n✅ Backtest complete!\n")


if __name__ == "__main__":
    main()
