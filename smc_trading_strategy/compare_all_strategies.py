"""
Compare ALL 4 Multi-Signal Strategies

1. Original Multi-Signal (baseline)
2. Enhanced Multi-Signal (5 patterns + trendlines)
3. Ultimate Multi-Signal (11 patterns)
4. Expert Multi-Signal (11 patterns + pro improvements)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy
from enhanced_multi_signal import EnhancedMultiSignal
from ultimate_multi_signal import UltimateMultiSignal
from expert_multi_signal import ExpertMultiSignal
from intraday_gold_data import generate_intraday_gold_data
from backtester import Backtester


def compare_all_strategies(df):
    """Compare all 4 strategy versions"""

    print("="*80)
    print("ALL STRATEGIES COMPARISON")
    print("="*80)

    results = []
    all_stats = []
    days = 30

    # Test 1: Original Multi-Signal
    print("\n" + "="*80)
    print("1️⃣  ORIGINAL MULTI-SIGNAL (Baseline)")
    print("="*80)

    try:
        strategy1 = MultiSignalGoldStrategy()
        df1 = strategy1.run_strategy(df.copy())
        bt1 = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
        stats1 = bt1.run(df1)

        results.append({
            'Strategy': 'Original',
            'Patterns': 4,
            'Features': 'Base',
            'Trades': stats1['total_trades'],
            'Sig/Day': f"{stats1['total_trades']/days:.2f}",
            'WR %': f"{stats1['win_rate']:.1f}",
            'Return %': f"{stats1['total_return_pct']:.2f}",
            'Sharpe': f"{stats1['sharpe_ratio']:.2f}",
            'DD %': f"{stats1['max_drawdown']:.2f}",
            'PF': f"{stats1['profit_factor']:.2f}"
        })

        all_stats.append(stats1)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Enhanced Multi-Signal
    print("\n" + "="*80)
    print("2️⃣  ENHANCED MULTI-SIGNAL (5 patterns + trendlines)")
    print("="*80)

    try:
        strategy2 = EnhancedMultiSignal()
        df2 = strategy2.run_strategy(df.copy())
        bt2 = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
        stats2 = bt2.run(df2)

        results.append({
            'Strategy': 'Enhanced',
            'Patterns': 5,
            'Features': 'Trendlines+Confluence',
            'Trades': stats2['total_trades'],
            'Sig/Day': f"{stats2['total_trades']/days:.2f}",
            'WR %': f"{stats2['win_rate']:.1f}",
            'Return %': f"{stats2['total_return_pct']:.2f}",
            'Sharpe': f"{stats2['sharpe_ratio']:.2f}",
            'DD %': f"{stats2['max_drawdown']:.2f}",
            'PF': f"{stats2['profit_factor']:.2f}"
        })

        all_stats.append(stats2)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Ultimate Multi-Signal
    print("\n" + "="*80)
    print("3️⃣  ULTIMATE MULTI-SIGNAL (11 patterns)")
    print("="*80)

    try:
        strategy3 = UltimateMultiSignal()
        df3 = strategy3.run_strategy(df.copy())
        bt3 = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
        stats3 = bt3.run(df3)

        results.append({
            'Strategy': 'Ultimate',
            'Patterns': 11,
            'Features': 'All Candlestick',
            'Trades': stats3['total_trades'],
            'Sig/Day': f"{stats3['total_trades']/days:.2f}",
            'WR %': f"{stats3['win_rate']:.1f}",
            'Return %': f"{stats3['total_return_pct']:.2f}",
            'Sharpe': f"{stats3['sharpe_ratio']:.2f}",
            'DD %': f"{stats3['max_drawdown']:.2f}",
            'PF': f"{stats3['profit_factor']:.2f}"
        })

        all_stats.append(stats3)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 4: Expert Multi-Signal
    print("\n" + "="*80)
    print("4️⃣  EXPERT MULTI-SIGNAL (11 patterns + Pro Features)")
    print("="*80)

    try:
        strategy4 = ExpertMultiSignal()
        df4 = strategy4.run_strategy(df.copy())
        bt4 = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
        stats4 = bt4.run(df4)

        results.append({
            'Strategy': 'Expert',
            'Patterns': 11,
            'Features': 'ATR+Regime+Adaptive',
            'Trades': stats4['total_trades'],
            'Sig/Day': f"{stats4['total_trades']/days:.2f}",
            'WR %': f"{stats4['win_rate']:.1f}",
            'Return %': f"{stats4['total_return_pct']:.2f}",
            'Sharpe': f"{stats4['sharpe_ratio']:.2f}",
            'DD %': f"{stats4['max_drawdown']:.2f}",
            'PF': f"{stats4['profit_factor']:.2f}"
        })

        all_stats.append(stats4)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Display comparison
    print("\n" + "="*80)
    print("FINAL COMPARISON TABLE")
    print("="*80 + "\n")

    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))

    # Winner analysis
    print("\n" + "="*80)
    print("WINNER ANALYSIS")
    print("="*80)

    # Extract numeric values
    returns = [float(r['Return %']) for r in results]
    win_rates = [float(r['WR %']) for r in results]
    sharpes = [float(r['Sharpe']) for r in results]
    trades = [r['Trades'] for r in results]

    strategy_names = [r['Strategy'] for r in results]

    # Best metrics
    best_return_idx = np.argmax(returns)
    best_wr_idx = np.argmax(win_rates)
    best_sharpe_idx = np.argmax(sharpes)
    most_trades_idx = np.argmax(trades)

    print(f"\n🏆 BEST RETURN:      {strategy_names[best_return_idx]} ({returns[best_return_idx]:.2f}%)")
    print(f"⭐ BEST WIN RATE:    {strategy_names[best_wr_idx]} ({win_rates[best_wr_idx]:.1f}%)")
    print(f"📈 BEST SHARPE:      {strategy_names[best_sharpe_idx]} ({sharpes[best_sharpe_idx]:.2f})")
    print(f"🎯 MOST SIGNALS:     {strategy_names[most_trades_idx]} ({trades[most_trades_idx]} trades)")

    # Overall winner
    print(f"\n💡 OVERALL RECOMMENDATION:")

    # Count wins
    wins = {name: 0 for name in strategy_names}
    wins[strategy_names[best_return_idx]] += 3
    wins[strategy_names[best_wr_idx]] += 3
    wins[strategy_names[best_sharpe_idx]] += 3
    wins[strategy_names[most_trades_idx]] += 1

    winner = max(wins, key=wins.get)
    winner_score = wins[winner]

    print(f"   🌟 {winner.upper()} (Score: {winner_score}/10)")

    # Detailed recommendation
    if winner == 'Original':
        print(f"   Reason: Reliable baseline performance")
    elif winner == 'Enhanced':
        print(f"   Reason: Best risk-adjusted returns + high win rate")
        print(f"   Best for: Quality over quantity traders")
    elif winner == 'Ultimate':
        print(f"   Reason: Most trading opportunities + good returns")
        print(f"   Best for: Active traders")
    elif winner == 'Expert':
        print(f"   Reason: Professional features + adaptive management")
        print(f"   Best for: Experienced traders")

    return results, all_stats


def plot_all_comparison(all_stats):
    """Plot comprehensive comparison"""

    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    strategy_names = ['Original', 'Enhanced', 'Ultimate', 'Expert']
    colors = ['#95a5a6', '#2ecc71', '#3498db', '#e74c3c']

    # Plot 1: Returns
    ax1 = fig.add_subplot(gs[0, 0])
    returns = [s['total_return_pct'] for s in all_stats]
    bars1 = ax1.bar(range(len(returns)), returns, color=colors, alpha=0.8, edgecolor='black')
    ax1.set_xticks(range(len(strategy_names)))
    ax1.set_xticklabels(strategy_names, rotation=0)
    ax1.set_ylabel('Return %')
    ax1.set_title('Total Return', fontweight='bold')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax1.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars1):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{returns[i]:.1f}%', ha='center', va='bottom' if height > 0 else 'top',
                fontsize=9, fontweight='bold')

    # Plot 2: Win Rate
    ax2 = fig.add_subplot(gs[0, 1])
    win_rates = [s['win_rate'] for s in all_stats]
    bars2 = ax2.bar(range(len(win_rates)), win_rates, color=colors, alpha=0.8, edgecolor='black')
    ax2.set_xticks(range(len(strategy_names)))
    ax2.set_xticklabels(strategy_names, rotation=0)
    ax2.set_ylabel('Win Rate %')
    ax2.set_title('Win Rate', fontweight='bold')
    ax2.axhline(y=50, color='orange', linestyle='--', linewidth=1, label='50%')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.legend()

    for i, bar in enumerate(bars2):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{win_rates[i]:.1f}%', ha='center', va='bottom',
                fontsize=9, fontweight='bold')

    # Plot 3: Signals per Day
    ax3 = fig.add_subplot(gs[0, 2])
    signals_per_day = [s['total_trades']/30 for s in all_stats]
    bars3 = ax3.bar(range(len(signals_per_day)), signals_per_day, color=colors, alpha=0.8, edgecolor='black')
    ax3.set_xticks(range(len(strategy_names)))
    ax3.set_xticklabels(strategy_names, rotation=0)
    ax3.set_ylabel('Signals/Day')
    ax3.set_title('Signal Frequency', fontweight='bold')
    ax3.axhline(y=1.0, color='green', linestyle='--', linewidth=2, label='Goal: 1.0')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.legend()

    for i, bar in enumerate(bars3):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{signals_per_day[i]:.2f}', ha='center', va='bottom',
                fontsize=9, fontweight='bold')

    # Plot 4: Sharpe Ratio
    ax4 = fig.add_subplot(gs[1, 0])
    sharpes = [s['sharpe_ratio'] for s in all_stats]
    bars4 = ax4.bar(range(len(sharpes)), sharpes, color=colors, alpha=0.8, edgecolor='black')
    ax4.set_xticks(range(len(strategy_names)))
    ax4.set_xticklabels(strategy_names, rotation=0)
    ax4.set_ylabel('Sharpe Ratio')
    ax4.set_title('Risk-Adjusted Returns', fontweight='bold')
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax4.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars4):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{sharpes[i]:.2f}', ha='center', va='bottom' if height > 0 else 'top',
                fontsize=9, fontweight='bold')

    # Plot 5: Max Drawdown
    ax5 = fig.add_subplot(gs[1, 1])
    drawdowns = [s['max_drawdown'] for s in all_stats]
    bars5 = ax5.bar(range(len(drawdowns)), drawdowns, color=colors, alpha=0.8, edgecolor='black')
    ax5.set_xticks(range(len(strategy_names)))
    ax5.set_xticklabels(strategy_names, rotation=0)
    ax5.set_ylabel('Max DD %')
    ax5.set_title('Maximum Drawdown', fontweight='bold')
    ax5.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars5):
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height,
                f'{drawdowns[i]:.1f}%', ha='center', va='top',
                fontsize=9, fontweight='bold')

    # Plot 6: Profit Factor
    ax6 = fig.add_subplot(gs[1, 2])
    profit_factors = [s['profit_factor'] if s['profit_factor'] else 0 for s in all_stats]
    bars6 = ax6.bar(range(len(profit_factors)), profit_factors, color=colors, alpha=0.8, edgecolor='black')
    ax6.set_xticks(range(len(strategy_names)))
    ax6.set_xticklabels(strategy_names, rotation=0)
    ax6.set_ylabel('Profit Factor')
    ax6.set_title('Profit Factor', fontweight='bold')
    ax6.axhline(y=1.0, color='orange', linestyle='--', linewidth=1, label='Breakeven')
    ax6.grid(True, alpha=0.3, axis='y')
    ax6.legend()

    for i, bar in enumerate(bars6):
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height,
                f'{profit_factors[i]:.2f}', ha='center', va='bottom',
                fontsize=9, fontweight='bold')

    # Plot 7: Equity Curves
    ax7 = fig.add_subplot(gs[2, :])

    for i, stats in enumerate(all_stats):
        capital = 10000
        equity = [capital]

        for trade in stats['trades']:
            capital += trade['pnl']
            equity.append(capital)

        ax7.plot(equity, label=strategy_names[i], linewidth=2, color=colors[i], alpha=0.9)

    ax7.axhline(y=10000, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Initial')
    ax7.set_xlabel('Trade Number')
    ax7.set_ylabel('Equity ($)')
    ax7.set_title('Equity Curves Comparison', fontweight='bold', fontsize=12)
    ax7.legend(loc='best', fontsize=10)
    ax7.grid(True, alpha=0.3)

    plt.suptitle('XAUUSD Gold - ALL STRATEGIES COMPARISON', fontsize=16, fontweight='bold', y=0.995)

    filename = 'all_strategies_comparison.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n📊 Comparison chart saved as '{filename}'")
    plt.close()


def main():
    """Main execution"""

    print("\n" + "="*80)
    print("ALL 4 STRATEGIES COMPARISON")
    print("="*80)

    # Generate data
    print("\n📊 Generating 30 days of 1H gold data...")
    df = generate_intraday_gold_data(days=30, timeframe='1H')

    print(f"\n✅ Data generated:")
    print(f"   Period: {len(df)} candles (30 days)")
    print(f"   Price Range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    # Compare all strategies
    results, all_stats = compare_all_strategies(df)

    # Plot comparison
    plot_all_comparison(all_stats)

    print("\n" + "="*80)
    print("✅ FULL COMPARISON COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
