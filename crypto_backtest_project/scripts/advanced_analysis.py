"""
Advanced Analysis and Optimization for SMC Strategy
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smc_strategy import SMCStrategy
from backtester import Backtester
from data_loader import generate_sample_data


def run_monte_carlo_simulation(df: pd.DataFrame, n_simulations: int = 100):
    """
    Run Monte Carlo simulation to test strategy robustness

    Args:
        df: DataFrame with OHLC data
        n_simulations: Number of simulations
    """
    print("\n🎲 Running Monte Carlo Simulation...")
    print(f"  Simulations: {n_simulations}")

    results = []

    for i in range(n_simulations):
        print(f"  Simulation {i+1}/{n_simulations}", end='\r')

        # Shuffle the data (bootstrap)
        df_sample = df.sample(frac=1.0, replace=True).sort_index()

        # Run strategy
        strategy = SMCStrategy(risk_reward_ratio=2.0, swing_length=10)
        df_result = strategy.run_strategy(df_sample)

        # Run backtest
        backtester = Backtester(initial_capital=10000)
        stats = backtester.run(df_result)

        results.append({
            'total_return_pct': stats['total_return_pct'],
            'win_rate': stats['win_rate'],
            'sharpe_ratio': stats['sharpe_ratio'],
            'max_drawdown': stats['max_drawdown'],
            'total_trades': stats['total_trades']
        })

    df_results = pd.DataFrame(results)

    print("\n")
    print("\n📊 MONTE CARLO RESULTS")
    print("="*60)
    print(f"\nTotal Return %:")
    print(f"  Mean:        {df_results['total_return_pct'].mean():.2f}%")
    print(f"  Median:      {df_results['total_return_pct'].median():.2f}%")
    print(f"  Std Dev:     {df_results['total_return_pct'].std():.2f}%")
    print(f"  Min:         {df_results['total_return_pct'].min():.2f}%")
    print(f"  Max:         {df_results['total_return_pct'].max():.2f}%")

    print(f"\nWin Rate:")
    print(f"  Mean:        {df_results['win_rate'].mean():.2f}%")
    print(f"  Median:      {df_results['win_rate'].median():.2f}%")

    print(f"\nSharpe Ratio:")
    print(f"  Mean:        {df_results['sharpe_ratio'].mean():.2f}")
    print(f"  Median:      {df_results['sharpe_ratio'].median():.2f}")

    # Plot distribution
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    axes[0, 0].hist(df_results['total_return_pct'], bins=30, edgecolor='black', alpha=0.7)
    axes[0, 0].axvline(df_results['total_return_pct'].mean(), color='red', linestyle='--', label='Mean')
    axes[0, 0].set_title('Total Return Distribution')
    axes[0, 0].set_xlabel('Return %')
    axes[0, 0].legend()

    axes[0, 1].hist(df_results['win_rate'], bins=30, edgecolor='black', alpha=0.7, color='green')
    axes[0, 1].axvline(df_results['win_rate'].mean(), color='red', linestyle='--', label='Mean')
    axes[0, 1].set_title('Win Rate Distribution')
    axes[0, 1].set_xlabel('Win Rate %')
    axes[0, 1].legend()

    axes[1, 0].hist(df_results['sharpe_ratio'], bins=30, edgecolor='black', alpha=0.7, color='orange')
    axes[1, 0].axvline(df_results['sharpe_ratio'].mean(), color='red', linestyle='--', label='Mean')
    axes[1, 0].set_title('Sharpe Ratio Distribution')
    axes[1, 0].set_xlabel('Sharpe Ratio')
    axes[1, 0].legend()

    axes[1, 1].hist(df_results['max_drawdown'], bins=30, edgecolor='black', alpha=0.7, color='purple')
    axes[1, 1].axvline(df_results['max_drawdown'].mean(), color='red', linestyle='--', label='Mean')
    axes[1, 1].set_title('Max Drawdown Distribution')
    axes[1, 1].set_xlabel('Max Drawdown %')
    axes[1, 1].legend()

    plt.tight_layout()
    plt.savefig('monte_carlo_results.png', dpi=150)
    print(f"\n📊 Monte Carlo chart saved as 'monte_carlo_results.png'")

    return df_results


def walk_forward_analysis(df: pd.DataFrame, train_size: int = 200, test_size: int = 50):
    """
    Walk-forward analysis to test strategy on unseen data

    Args:
        df: DataFrame with OHLC data
        train_size: Size of training window
        test_size: Size of testing window
    """
    print("\n🚶 Running Walk-Forward Analysis...")
    print(f"  Train Size: {train_size} days")
    print(f"  Test Size:  {test_size} days")

    results = []
    n_windows = (len(df) - train_size) // test_size

    for i in range(n_windows):
        train_start = i * test_size
        train_end = train_start + train_size
        test_start = train_end
        test_end = test_start + test_size

        if test_end > len(df):
            break

        print(f"  Window {i+1}/{n_windows}", end='\r')

        # Train on training data (in this case, we just use same params)
        df_train = df.iloc[train_start:train_end]

        # Test on test data
        df_test = df.iloc[test_start:test_end]

        # Run strategy on test data
        strategy = SMCStrategy(risk_reward_ratio=2.0, swing_length=10)
        df_result = strategy.run_strategy(df_test)

        # Run backtest
        backtester = Backtester(initial_capital=10000)
        stats = backtester.run(df_result)

        results.append({
            'window': i+1,
            'test_start': df_test.index[0],
            'test_end': df_test.index[-1],
            'total_return_pct': stats['total_return_pct'],
            'win_rate': stats['win_rate'],
            'total_trades': stats['total_trades']
        })

    df_results = pd.DataFrame(results)

    print("\n")
    print("\n📊 WALK-FORWARD ANALYSIS RESULTS")
    print("="*60)
    print(f"\nAverage Return per Window: {df_results['total_return_pct'].mean():.2f}%")
    print(f"Win Rate Consistency:      {df_results['win_rate'].mean():.2f}%")
    print(f"Positive Windows:          {(df_results['total_return_pct'] > 0).sum()}/{len(df_results)}")

    # Plot results
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    ax1.plot(df_results['window'], df_results['total_return_pct'], marker='o', linewidth=2)
    ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax1.set_title('Walk-Forward Returns by Window')
    ax1.set_xlabel('Window')
    ax1.set_ylabel('Return %')
    ax1.grid(True, alpha=0.3)

    ax2.plot(df_results['window'], df_results['win_rate'], marker='s', color='green', linewidth=2)
    ax2.set_title('Walk-Forward Win Rate by Window')
    ax2.set_xlabel('Window')
    ax2.set_ylabel('Win Rate %')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('walk_forward_results.png', dpi=150)
    print(f"\n📊 Walk-forward chart saved as 'walk_forward_results.png'")

    return df_results


def compare_parameters(df: pd.DataFrame):
    """
    Compare different parameter combinations

    Args:
        df: DataFrame with OHLC data
    """
    print("\n⚙️  Comparing Different Parameters...")

    param_combinations = [
        {'swing_length': 5, 'risk_reward': 1.5},
        {'swing_length': 10, 'risk_reward': 2.0},
        {'swing_length': 15, 'risk_reward': 2.5},
        {'swing_length': 20, 'risk_reward': 3.0},
    ]

    results = []

    for i, params in enumerate(param_combinations):
        print(f"  Testing params {i+1}/{len(param_combinations)}: swing={params['swing_length']}, rr={params['risk_reward']}", end='\r')

        strategy = SMCStrategy(
            risk_reward_ratio=params['risk_reward'],
            swing_length=params['swing_length']
        )

        df_result = strategy.run_strategy(df.copy())
        backtester = Backtester(initial_capital=10000)
        stats = backtester.run(df_result)

        results.append({
            'swing_length': params['swing_length'],
            'risk_reward': params['risk_reward'],
            'total_return_pct': stats['total_return_pct'],
            'win_rate': stats['win_rate'],
            'sharpe_ratio': stats['sharpe_ratio'],
            'max_drawdown': stats['max_drawdown'],
            'total_trades': stats['total_trades'],
            'profit_factor': stats['profit_factor']
        })

    df_results = pd.DataFrame(results)

    print("\n")
    print("\n📊 PARAMETER COMPARISON")
    print("="*60)
    print(df_results.to_string(index=False))

    return df_results


def main():
    """Main execution"""
    print("\n🔬 SMC STRATEGY - ADVANCED ANALYSIS")
    print("="*60)

    # Generate data
    print("\n📥 Generating data...")
    df = generate_sample_data(days=365, start_price=50000, volatility=0.025)
    print(f"  ✅ Generated {len(df)} candles")

    # Run different analyses
    print("\n" + "="*60)

    # 1. Parameter comparison
    param_results = compare_parameters(df)

    # 2. Monte Carlo simulation
    monte_carlo_results = run_monte_carlo_simulation(df, n_simulations=20)

    # 3. Walk-forward analysis
    walk_forward_results = walk_forward_analysis(df, train_size=200, test_size=50)

    print("\n✅ Advanced Analysis Complete!")
    print("\nGenerated files:")
    print("  - monte_carlo_results.png")
    print("  - walk_forward_results.png")
    print("\n")


if __name__ == "__main__":
    main()
