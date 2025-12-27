"""
Compare Enhanced vs Ultimate Multi-Signal strategies
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_multi_signal import EnhancedMultiSignal
from ultimate_multi_signal import UltimateMultiSignal
from intraday_gold_data import generate_intraday_gold_data
from backtester import Backtester


def compare_strategies(df):
    """Compare Enhanced vs Ultimate"""

    print("="*80)
    print("STRATEGY COMPARISON: Enhanced vs Ultimate")
    print("="*80)

    results = []
    all_stats = []

    # Test 1: Enhanced Multi-Signal (5 patterns)
    print("\n" + "="*80)
    print("1️⃣  ENHANCED MULTI-SIGNAL (5 patterns)")
    print("="*80)

    strategy1 = EnhancedMultiSignal()
    df1 = strategy1.run_strategy(df.copy())
    bt1 = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
    stats1 = bt1.run(df1)

    results.append({
        'Strategy': 'Enhanced (5)',
        'Patterns': 5,
        'Trades': stats1['total_trades'],
        'Signals/Day': f"{stats1['total_trades']/30:.2f}",
        'Win Rate %': f"{stats1['win_rate']:.1f}",
        'Return %': f"{stats1['total_return_pct']:.2f}",
        'Sharpe': f"{stats1['sharpe_ratio']:.2f}",
        'Max DD %': f"{stats1['max_drawdown']:.2f}",
        'Profit Factor': f"{stats1['profit_factor']:.2f}"
    })

    all_stats.append(stats1)

    # Test 2: Ultimate Multi-Signal (11 patterns)
    print("\n" + "="*80)
    print("2️⃣  ULTIMATE MULTI-SIGNAL (11 patterns)")
    print("="*80)

    strategy2 = UltimateMultiSignal()
    df2 = strategy2.run_strategy(df.copy())
    bt2 = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
    stats2 = bt2.run(df2)

    results.append({
        'Strategy': 'Ultimate (11)',
        'Patterns': 11,
        'Trades': stats2['total_trades'],
        'Signals/Day': f"{stats2['total_trades']/30:.2f}",
        'Win Rate %': f"{stats2['win_rate']:.1f}",
        'Return %': f"{stats2['total_return_pct']:.2f}",
        'Sharpe': f"{stats2['sharpe_ratio']:.2f}",
        'Max DD %': f"{stats2['max_drawdown']:.2f}",
        'Profit Factor': f"{stats2['profit_factor']:.2f}"
    })

    all_stats.append(stats2)

    # Display comparison
    print("\n" + "="*80)
    print("COMPARISON RESULTS")
    print("="*80 + "\n")

    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))

    # Winner analysis
    print("\n" + "="*80)
    print("WINNER ANALYSIS")
    print("="*80)

    enhanced_return = stats1['total_return_pct']
    ultimate_return = stats2['total_return_pct']

    enhanced_wr = stats1['win_rate']
    ultimate_wr = stats2['win_rate']

    enhanced_sharpe = stats1['sharpe_ratio']
    ultimate_sharpe = stats2['sharpe_ratio']

    print(f"\n📊 Best Return:      {'Enhanced' if enhanced_return > ultimate_return else 'Ultimate'} ({max(enhanced_return, ultimate_return):.2f}%)")
    print(f"⭐ Best Win Rate:    {'Enhanced' if enhanced_wr > ultimate_wr else 'Ultimate'} ({max(enhanced_wr, ultimate_wr):.1f}%)")
    print(f"📈 Best Sharpe:      {'Enhanced' if enhanced_sharpe > ultimate_sharpe else 'Ultimate'} ({max(enhanced_sharpe, ultimate_sharpe):.2f})")
    print(f"🎯 Most Signals:     {'Ultimate' if stats2['total_trades'] > stats1['total_trades'] else 'Enhanced'} ({max(stats1['total_trades'], stats2['total_trades'])} trades)")

    print(f"\n💡 RECOMMENDATION:")
    if enhanced_sharpe > ultimate_sharpe and enhanced_wr > ultimate_wr:
        print(f"   ⭐ ENHANCED Multi-Signal")
        print(f"   Reason: Better risk-adjusted returns + higher win rate")
        print(f"   Best for: Quality over quantity traders")
    elif stats2['total_trades'] > stats1['total_trades'] * 1.2 and ultimate_return > enhanced_return:
        print(f"   🌟 ULTIMATE Multi-Signal")
        print(f"   Reason: More signals + good returns")
        print(f"   Best for: Active traders who want more opportunities")
    else:
        print(f"   Both strategies are good, choose based on preference:")
        print(f"   - Enhanced: Higher quality (WR {enhanced_wr:.1f}%), fewer signals")
        print(f"   - Ultimate: More signals ({stats2['total_trades']} vs {stats1['total_trades']}), lower WR")

    return results, all_stats


def plot_comparison(all_stats):
    """Plot strategy comparison"""

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Enhanced vs Ultimate Multi-Signal Comparison', fontsize=16, fontweight='bold')

    strategy_names = ['Enhanced (5)', 'Ultimate (11)']
    colors = ['#2ecc71', '#3498db']

    # Plot 1: Returns
    ax1 = axes[0, 0]
    returns = [s['total_return_pct'] for s in all_stats]
    bars1 = ax1.bar(strategy_names, returns, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_ylabel('Return %')
    ax1.set_title('Total Return', fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars1):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{returns[i]:.2f}%', ha='center', va='bottom',
                fontsize=10, fontweight='bold')

    # Plot 2: Win Rate
    ax2 = axes[0, 1]
    win_rates = [s['win_rate'] for s in all_stats]
    bars2 = ax2.bar(strategy_names, win_rates, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_ylabel('Win Rate %')
    ax2.set_title('Win Rate', fontweight='bold')
    ax2.axhline(y=50, color='red', linestyle='--', linewidth=1, label='50%')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.legend()

    for i, bar in enumerate(bars2):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{win_rates[i]:.1f}%', ha='center', va='bottom',
                fontsize=10, fontweight='bold')

    # Plot 3: Signals per Day
    ax3 = axes[0, 2]
    signals_per_day = [s['total_trades']/30 for s in all_stats]
    bars3 = ax3.bar(strategy_names, signals_per_day, color=colors, alpha=0.7, edgecolor='black')
    ax3.set_ylabel('Signals per Day')
    ax3.set_title('Signal Frequency', fontweight='bold')
    ax3.axhline(y=1.0, color='orange', linestyle='--', linewidth=1, label='Goal: 1.0')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.legend()

    for i, bar in enumerate(bars3):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{signals_per_day[i]:.2f}', ha='center', va='bottom',
                fontsize=10, fontweight='bold')

    # Plot 4: Sharpe Ratio
    ax4 = axes[1, 0]
    sharpes = [s['sharpe_ratio'] for s in all_stats]
    bars4 = ax4.bar(strategy_names, sharpes, color=colors, alpha=0.7, edgecolor='black')
    ax4.set_ylabel('Sharpe Ratio')
    ax4.set_title('Risk-Adjusted Returns', fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars4):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{sharpes[i]:.2f}', ha='center', va='bottom',
                fontsize=10, fontweight='bold')

    # Plot 5: Max Drawdown
    ax5 = axes[1, 1]
    drawdowns = [s['max_drawdown'] for s in all_stats]
    bars5 = ax5.bar(strategy_names, drawdowns, color=colors, alpha=0.7, edgecolor='black')
    ax5.set_ylabel('Max Drawdown %')
    ax5.set_title('Maximum Drawdown', fontweight='bold')
    ax5.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars5):
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height,
                f'{drawdowns[i]:.2f}%', ha='center', va='top',
                fontsize=10, fontweight='bold')

    # Plot 6: Equity Curves
    ax6 = axes[1, 2]

    for i, stats in enumerate(all_stats):
        capital = 10000
        equity = [capital]

        for trade in stats['trades']:
            capital += trade['pnl']
            equity.append(capital)

        ax6.plot(equity, label=strategy_names[i], linewidth=2, color=colors[i], alpha=0.8)

    ax6.axhline(y=10000, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Initial')
    ax6.set_xlabel('Trade Number')
    ax6.set_ylabel('Equity ($)')
    ax6.set_title('Equity Curves', fontweight='bold')
    ax6.legend(loc='best')
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()

    filename = 'enhanced_vs_ultimate_comparison.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n📊 Comparison chart saved as '{filename}'")
    plt.close()


def main():
    """Main comparison"""

    print("\n" + "="*80)
    print("ENHANCED vs ULTIMATE MULTI-SIGNAL COMPARISON")
    print("="*80)

    # Generate data
    print("\n📊 Generating 30 days of 1H gold data...")
    df = generate_intraday_gold_data(days=30, timeframe='1H')

    print(f"\n✅ Data generated:")
    print(f"   Period: {len(df)} candles (30 days)")
    print(f"   Price Range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    # Compare strategies
    results, all_stats = compare_strategies(df)

    # Plot comparison
    plot_comparison(all_stats)

    print("\n" + "="*80)
    print("✅ COMPARISON COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
