"""
Test SMC Strategies on Realistic XAUUSD (Gold) Data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simplified_smc_strategy import SimplifiedSMCStrategy
from smc_strategy import SMCStrategy
from backtester import Backtester
from realistic_gold_data import generate_realistic_gold_data, generate_realistic_bitcoin_data
from data_loader import validate_data


def plot_gold_results(asset_name, df, equity_curves, all_trades, all_stats):
    """Plot comprehensive results for all strategies"""

    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(5, 2, hspace=0.4, wspace=0.3)

    # Plot 1: Price Chart with all signals
    ax1 = fig.add_subplot(gs[0:2, :])
    ax1.plot(df.index, df['close'], label='Gold Price', color='gold', linewidth=1.5, alpha=0.8)

    # Plot signals for each strategy with different colors
    colors = {'Basic SMC': 'blue', 'Simplified SMC': 'green'}
    markers_long = {'^': 'Basic SMC', '^': 'Simplified SMC'}

    for strategy_name, trades in all_trades.items():
        if len(trades) == 0:
            continue

        df_trades = pd.DataFrame(trades)

        # Long trades
        long_trades = df_trades[df_trades['direction'] == 'LONG']
        if len(long_trades) > 0:
            ax1.scatter(long_trades['entry_time'], long_trades['entry_price'],
                       color=colors.get(strategy_name, 'gray'), marker='^',
                       s=120, label=f'{strategy_name} LONG', alpha=0.7,
                       edgecolors='black', linewidths=1)

        # Short trades
        short_trades = df_trades[df_trades['direction'] == 'SHORT']
        if len(short_trades) > 0:
            ax1.scatter(short_trades['entry_time'], short_trades['entry_price'],
                       color=colors.get(strategy_name, 'gray'), marker='v',
                       s=120, label=f'{strategy_name} SHORT', alpha=0.7,
                       edgecolors='black', linewidths=1)

    ax1.set_title(f'{asset_name} - SMC Strategies Comparison', fontsize=16, fontweight='bold')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Price (USD)', fontsize=12)
    ax1.legend(loc='best', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Equity Curves Comparison
    ax2 = fig.add_subplot(gs[2, :])
    for strategy_name, equity in equity_curves.items():
        if len(equity) > 0:
            ax2.plot(equity, label=strategy_name, linewidth=2, alpha=0.8)

    ax2.axhline(y=10000, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    ax2.set_title('Equity Curves Comparison', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Bar', fontsize=12)
    ax2.set_ylabel('Equity ($)', fontsize=12)
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    # Plot 3: Win Rate Comparison
    ax3 = fig.add_subplot(gs[3, 0])
    strategies = list(all_stats.keys())
    win_rates = [all_stats[s]['win_rate'] for s in strategies]
    colors_bar = ['green' if wr >= 50 else 'red' for wr in win_rates]

    ax3.bar(strategies, win_rates, color=colors_bar, alpha=0.7, edgecolor='black')
    ax3.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% Threshold')
    ax3.set_title('Win Rate Comparison', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Win Rate (%)', fontsize=11)
    ax3.set_ylim(0, 100)
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=15, ha='right')

    # Plot 4: Return Comparison
    ax4 = fig.add_subplot(gs[3, 1])
    returns = [all_stats[s]['total_return_pct'] for s in strategies]
    colors_bar = ['green' if r > 0 else 'red' for r in returns]

    ax4.bar(strategies, returns, color=colors_bar, alpha=0.7, edgecolor='black')
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax4.set_title('Total Return Comparison', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Return (%)', fontsize=11)
    ax4.grid(True, alpha=0.3, axis='y')
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=15, ha='right')

    # Plot 5: Trade Count and Profit Factor
    ax5 = fig.add_subplot(gs[4, 0])
    trade_counts = [all_stats[s]['total_trades'] for s in strategies]
    ax5.bar(strategies, trade_counts, color='skyblue', alpha=0.7, edgecolor='black')
    ax5.set_title('Total Trades', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Number of Trades', fontsize=11)
    ax5.grid(True, alpha=0.3, axis='y')
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=15, ha='right')

    # Plot 6: Sharpe Ratio
    ax6 = fig.add_subplot(gs[4, 1])
    sharpe_ratios = [all_stats[s]['sharpe_ratio'] for s in strategies]
    colors_bar = ['green' if sr > 1 else 'orange' if sr > 0 else 'red' for sr in sharpe_ratios]

    ax6.bar(strategies, sharpe_ratios, color=colors_bar, alpha=0.7, edgecolor='black')
    ax6.axhline(y=1, color='gray', linestyle='--', alpha=0.5, label='Good Threshold (1.0)')
    ax6.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax6.set_title('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax6.set_ylabel('Sharpe Ratio', fontsize=11)
    ax6.legend(fontsize=9)
    ax6.grid(True, alpha=0.3, axis='y')
    plt.setp(ax6.xaxis.get_majorticklabels(), rotation=15, ha='right')

    filename = f'{asset_name.lower().replace("/", "_")}_complete_analysis.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n📊 Complete analysis chart saved as '{filename}'")
    plt.close()


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("SMC STRATEGY - XAUUSD (GOLD) REALISTIC DATA TESTING")
    print("="*80)

    # Generate realistic gold data
    print("\n📥 Generating realistic XAUUSD data (1 year)...")
    df_gold = generate_realistic_gold_data(days=365)

    if not validate_data(df_gold):
        print("❌ Data validation failed")
        return

    print(f"  ✅ Generated {len(df_gold)} daily candles")
    print(f"  📅 Date range: {df_gold.index[0].date()} to {df_gold.index[-1].date()}")
    print(f"  💰 Price range: ${df_gold['close'].min():.2f} - ${df_gold['close'].max():.2f}")
    print(f"  📊 Avg daily volatility: {(df_gold['close'].pct_change().std() * 100):.2f}%")

    # Test all strategies
    print("\n" + "="*80)
    print("TESTING ALL STRATEGIES ON XAUUSD")
    print("="*80)

    all_results = {}
    all_stats = {}
    all_trades = {}
    equity_curves = {}

    # 1. Basic SMC
    print("\n1️⃣  Basic SMC Strategy...")
    try:
        basic = SMCStrategy(risk_reward_ratio=2.0, swing_length=10)
        df_basic = basic.run_strategy(df_gold.copy())
        bt_basic = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
        stats_basic = bt_basic.run(df_basic)

        all_stats['Basic SMC'] = stats_basic
        all_trades['Basic SMC'] = stats_basic['trades']
        equity_curves['Basic SMC'] = bt_basic.equity_curve

        print(f"  Trades: {stats_basic['total_trades']}")
        print(f"  Win Rate: {stats_basic['win_rate']:.1f}%")
        print(f"  Return: {stats_basic['total_return_pct']:.2f}%")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 2. Simplified SMC
    print("\n2️⃣  Simplified SMC Strategy (Pure SMC + Volume)...")
    try:
        simplified = SimplifiedSMCStrategy(
            risk_reward_ratio=2.0,
            swing_length=10,
            volume_lookback=2,
            min_candle_quality=50
        )
        df_simplified = simplified.run_strategy(df_gold.copy())
        bt_simplified = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
        stats_simplified = bt_simplified.run(df_simplified)

        all_stats['Simplified SMC'] = stats_simplified
        all_trades['Simplified SMC'] = stats_simplified['trades']
        equity_curves['Simplified SMC'] = bt_simplified.equity_curve

        print(f"  Trades: {stats_simplified['total_trades']}")
        print(f"  Win Rate: {stats_simplified['win_rate']:.1f}%")
        print(f"  Return: {stats_simplified['total_return_pct']:.2f}%")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Results table
    print("\n" + "="*80)
    print("COMPREHENSIVE RESULTS - XAUUSD")
    print("="*80)

    results_data = []
    for strategy_name, stats in all_stats.items():
        results_data.append({
            'Strategy': strategy_name,
            'Trades': stats['total_trades'],
            'Win Rate %': f"{stats['win_rate']:.1f}",
            'Return %': f"{stats['total_return_pct']:.2f}",
            'Final Capital': f"${stats['final_capital']:.2f}",
            'Profit Factor': f"{stats['profit_factor']:.2f}",
            'Sharpe Ratio': f"{stats['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats['max_drawdown']:.2f}",
            'Avg Win': f"${stats['avg_win']:.2f}" if stats['avg_win'] else '$0.00',
            'Avg Loss': f"${stats['avg_loss']:.2f}" if stats['avg_loss'] else '$0.00'
        })

    df_results = pd.DataFrame(results_data)
    print("\n" + df_results.to_string(index=False))

    # Find best strategy
    valid_returns = [(name, stats['total_return_pct']) for name, stats in all_stats.items()]
    valid_returns.sort(key=lambda x: x[1], reverse=True)

    if len(valid_returns) > 0:
        best_name, best_return = valid_returns[0]
        print(f"\n🏆 BEST STRATEGY: {best_name} ({best_return:.2f}%)")

        # Detailed results for best strategy
        print("\n" + "="*80)
        print(f"DETAILED RESULTS - {best_name}")
        print("="*80)

        best_stats = all_stats[best_name]
        bt = Backtester(initial_capital=10000)
        bt.print_results(best_stats)

        # Save trades
        if best_stats['total_trades'] > 0:
            df_trades = pd.DataFrame(best_stats['trades'])
            df_trades.to_csv('xauusd_best_trades.csv', index=False)
            print(f"\n💾 Best strategy trades saved to 'xauusd_best_trades.csv'")

            # Show sample trades
            print("\n📋 Sample Trades (First 5):")
            print("-" * 80)
            for i, trade in enumerate(best_stats['trades'][:5]):
                print(f"\nTrade {i+1}:")
                print(f"  Direction: {trade['direction']}")
                print(f"  Entry: {trade['entry_time']} @ ${trade['entry_price']:.2f}")
                print(f"  Exit: {trade['exit_time']} @ ${trade['exit_price']:.2f}")
                print(f"  PnL: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
                print(f"  Reason: {trade['exit_reason']}")

    # Plot comprehensive analysis
    print("\n📈 Generating comprehensive analysis charts...")
    plot_gold_results('XAUUSD', df_gold, equity_curves, all_trades, all_stats)

    print("\n✅ XAUUSD Analysis Complete!\n")


if __name__ == "__main__":
    main()
