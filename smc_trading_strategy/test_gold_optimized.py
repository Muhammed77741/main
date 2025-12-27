"""
Test Gold-Optimized SMC Strategy
Compare all strategy versions on XAUUSD data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smc_strategy import SMCStrategy
from simplified_smc_strategy import SimplifiedSMCStrategy
from gold_optimized_smc_strategy import (
    GoldOptimizedSMCStrategy,
    GoldOptimizedAggressiveStrategy,
    GoldOptimizedConservativeStrategy
)
from backtester import Backtester
from realistic_gold_data import generate_realistic_gold_data


def test_all_gold_strategies(df):
    """
    Test all strategy versions on gold data

    Strategies:
    1. Basic SMC (baseline)
    2. Simplified SMC (volume-focused)
    3. Gold-Optimized SMC (default)
    4. Gold-Optimized Aggressive (more signals)
    5. Gold-Optimized Conservative (fewer, high-quality signals)
    """
    print(f"\n{'='*80}")
    print(f"GOLD STRATEGY COMPARISON")
    print(f"{'='*80}")
    print(f"Data: {len(df)} candles")
    print(f"Price Range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"Avg Daily Vol: {(df['high'] - df['low']).mean() / df['close'].mean() * 100:.2f}%")

    results = []
    all_stats = []
    all_dfs = []

    # Backtester settings
    initial_capital = 10000
    commission = 0.001  # 0.1%
    slippage = 0.0005   # 0.05%

    # Test 1: Basic SMC (baseline)
    print(f"\n{'='*80}")
    print("1️⃣  BASIC SMC STRATEGY (Baseline)")
    print(f"{'='*80}")

    try:
        strategy1 = SMCStrategy(risk_reward_ratio=2.0, swing_length=10)
        df1 = strategy1.run_strategy(df.copy())
        bt1 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats1 = bt1.run(df1)

        results.append({
            'Strategy': 'Basic SMC',
            'Trades': stats1['total_trades'],
            'Win Rate %': f"{stats1['win_rate']:.1f}",
            'Return %': f"{stats1['total_return_pct']:.2f}",
            'Profit Factor': f"{stats1['profit_factor']:.2f}",
            'Sharpe': f"{stats1['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats1['max_drawdown']:.2f}",
            'Final Capital': f"${stats1['final_capital']:.2f}"
        })

        all_stats.append(stats1)
        all_dfs.append(df1)

    except Exception as e:
        print(f"❌ Error in Basic SMC: {e}")
        results.append({
            'Strategy': 'Basic SMC',
            'Trades': 'ERROR',
            'Win Rate %': '-',
            'Return %': '-',
            'Profit Factor': '-',
            'Sharpe': '-',
            'Max DD %': '-',
            'Final Capital': '-'
        })

    # Test 2: Simplified SMC
    print(f"\n{'='*80}")
    print("2️⃣  SIMPLIFIED SMC STRATEGY (Volume-Focused)")
    print(f"{'='*80}")

    try:
        strategy2 = SimplifiedSMCStrategy(
            risk_reward_ratio=2.0,
            swing_length=10,
            volume_lookback=2,
            min_candle_quality=50
        )
        df2 = strategy2.run_strategy(df.copy())
        bt2 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats2 = bt2.run(df2)

        results.append({
            'Strategy': 'Simplified SMC',
            'Trades': stats2['total_trades'],
            'Win Rate %': f"{stats2['win_rate']:.1f}",
            'Return %': f"{stats2['total_return_pct']:.2f}",
            'Profit Factor': f"{stats2['profit_factor']:.2f}",
            'Sharpe': f"{stats2['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats2['max_drawdown']:.2f}",
            'Final Capital': f"${stats2['final_capital']:.2f}"
        })

        all_stats.append(stats2)
        all_dfs.append(df2)

    except Exception as e:
        print(f"❌ Error in Simplified SMC: {e}")
        results.append({
            'Strategy': 'Simplified SMC',
            'Trades': 'ERROR',
            'Win Rate %': '-',
            'Return %': '-',
            'Profit Factor': '-',
            'Sharpe': '-',
            'Max DD %': '-',
            'Final Capital': '-'
        })

    # Test 3: Gold-Optimized SMC (Default)
    print(f"\n{'='*80}")
    print("3️⃣  GOLD-OPTIMIZED SMC STRATEGY (Default)")
    print(f"{'='*80}")

    try:
        strategy3 = GoldOptimizedSMCStrategy(
            risk_reward_ratio=2.5,
            swing_length=12,
            volume_lookback=1,
            min_candle_quality=40,
            trade_active_sessions_only=True,
            avoid_round_numbers=True,
            use_adaptive_rr=True
        )
        df3 = strategy3.run_strategy(df.copy())
        bt3 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats3 = bt3.run(df3)

        results.append({
            'Strategy': 'Gold-Optimized',
            'Trades': stats3['total_trades'],
            'Win Rate %': f"{stats3['win_rate']:.1f}",
            'Return %': f"{stats3['total_return_pct']:.2f}",
            'Profit Factor': f"{stats3['profit_factor']:.2f}",
            'Sharpe': f"{stats3['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats3['max_drawdown']:.2f}",
            'Final Capital': f"${stats3['final_capital']:.2f}"
        })

        all_stats.append(stats3)
        all_dfs.append(df3)

    except Exception as e:
        print(f"❌ Error in Gold-Optimized: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            'Strategy': 'Gold-Optimized',
            'Trades': 'ERROR',
            'Win Rate %': '-',
            'Return %': '-',
            'Profit Factor': '-',
            'Sharpe': '-',
            'Max DD %': '-',
            'Final Capital': '-'
        })

    # Test 4: Gold-Optimized Aggressive
    print(f"\n{'='*80}")
    print("4️⃣  GOLD-OPTIMIZED AGGRESSIVE (More Signals)")
    print(f"{'='*80}")

    try:
        strategy4 = GoldOptimizedAggressiveStrategy()
        df4 = strategy4.run_strategy(df.copy())
        bt4 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats4 = bt4.run(df4)

        results.append({
            'Strategy': 'Gold-Aggressive',
            'Trades': stats4['total_trades'],
            'Win Rate %': f"{stats4['win_rate']:.1f}",
            'Return %': f"{stats4['total_return_pct']:.2f}",
            'Profit Factor': f"{stats4['profit_factor']:.2f}",
            'Sharpe': f"{stats4['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats4['max_drawdown']:.2f}",
            'Final Capital': f"${stats4['final_capital']:.2f}"
        })

        all_stats.append(stats4)
        all_dfs.append(df4)

    except Exception as e:
        print(f"❌ Error in Gold-Aggressive: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            'Strategy': 'Gold-Aggressive',
            'Trades': 'ERROR',
            'Win Rate %': '-',
            'Return %': '-',
            'Profit Factor': '-',
            'Sharpe': '-',
            'Max DD %': '-',
            'Final Capital': '-'
        })

    # Test 5: Gold-Optimized Conservative
    print(f"\n{'='*80}")
    print("5️⃣  GOLD-OPTIMIZED CONSERVATIVE (High Quality)")
    print(f"{'='*80}")

    try:
        strategy5 = GoldOptimizedConservativeStrategy()
        df5 = strategy5.run_strategy(df.copy())
        bt5 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats5 = bt5.run(df5)

        results.append({
            'Strategy': 'Gold-Conservative',
            'Trades': stats5['total_trades'],
            'Win Rate %': f"{stats5['win_rate']:.1f}",
            'Return %': f"{stats5['total_return_pct']:.2f}",
            'Profit Factor': f"{stats5['profit_factor']:.2f}",
            'Sharpe': f"{stats5['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats5['max_drawdown']:.2f}",
            'Final Capital': f"${stats5['final_capital']:.2f}"
        })

        all_stats.append(stats5)
        all_dfs.append(df5)

    except Exception as e:
        print(f"❌ Error in Gold-Conservative: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            'Strategy': 'Gold-Conservative',
            'Trades': 'ERROR',
            'Win Rate %': '-',
            'Return %': '-',
            'Profit Factor': '-',
            'Sharpe': '-',
            'Max DD %': '-',
            'Final Capital': '-'
        })

    # Display results
    print(f"\n{'='*80}")
    print("COMPARISON RESULTS")
    print(f"{'='*80}\n")

    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))

    # Find best strategy
    valid_results = df_results[df_results['Return %'] != '-'].copy()
    if len(valid_results) > 0:
        valid_results['Return_Num'] = valid_results['Return %'].astype(float)
        best_idx = valid_results['Return_Num'].idxmax()
        best_name = valid_results.iloc[best_idx]['Strategy']
        best_return = valid_results.iloc[best_idx]['Return %']

        print(f"\n{'='*80}")
        print(f"🏆 BEST STRATEGY: {best_name} ({best_return}%)")
        print(f"{'='*80}")

    return results, all_stats, all_dfs


def plot_gold_comparison(df, all_stats, strategy_names, initial_capital=10000):
    """Plot comparison of all strategies"""

    valid_stats = [s for s in all_stats if s['total_trades'] > 0]
    valid_names = [strategy_names[i] for i, s in enumerate(all_stats) if s['total_trades'] > 0]

    if len(valid_stats) == 0:
        print("\n⚠️  No valid strategies to plot")
        return

    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Plot 1: Returns Comparison
    ax1 = fig.add_subplot(gs[0, 0])
    returns = [s['total_return_pct'] for s in valid_stats]
    colors = ['green' if r > 0 else 'red' for r in returns]
    bars = ax1.bar(range(len(returns)), returns, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xticks(range(len(valid_names)))
    ax1.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax1.set_ylabel('Return %')
    ax1.set_title('Total Return Comparison', fontweight='bold')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax1.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{returns[i]:.2f}%', ha='center', va='bottom' if height > 0 else 'top',
                fontsize=9, fontweight='bold')

    # Plot 2: Win Rate Comparison
    ax2 = fig.add_subplot(gs[0, 1])
    win_rates = [s['win_rate'] for s in valid_stats]
    bars2 = ax2.bar(range(len(win_rates)), win_rates, color='steelblue', alpha=0.7, edgecolor='black')
    ax2.set_xticks(range(len(valid_names)))
    ax2.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax2.set_ylabel('Win Rate %')
    ax2.set_title('Win Rate Comparison', fontweight='bold')
    ax2.axhline(y=50, color='orange', linestyle='--', linewidth=1, label='50% Baseline')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.legend()

    for i, bar in enumerate(bars2):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{win_rates[i]:.1f}%', ha='center', va='bottom',
                fontsize=9, fontweight='bold')

    # Plot 3: Number of Trades
    ax3 = fig.add_subplot(gs[0, 2])
    trade_counts = [s['total_trades'] for s in valid_stats]
    bars3 = ax3.bar(range(len(trade_counts)), trade_counts, color='purple', alpha=0.7, edgecolor='black')
    ax3.set_xticks(range(len(valid_names)))
    ax3.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax3.set_ylabel('Number of Trades')
    ax3.set_title('Trade Count Comparison', fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars3):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{trade_counts[i]}', ha='center', va='bottom',
                fontsize=9, fontweight='bold')

    # Plot 4: Profit Factor
    ax4 = fig.add_subplot(gs[1, 0])
    profit_factors = [s['profit_factor'] if s['profit_factor'] else 0 for s in valid_stats]
    colors4 = ['green' if pf > 1.0 else 'red' for pf in profit_factors]
    bars4 = ax4.bar(range(len(profit_factors)), profit_factors, color=colors4, alpha=0.7, edgecolor='black')
    ax4.set_xticks(range(len(valid_names)))
    ax4.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax4.set_ylabel('Profit Factor')
    ax4.set_title('Profit Factor Comparison', fontweight='bold')
    ax4.axhline(y=1.0, color='orange', linestyle='--', linewidth=1, label='Breakeven')
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.legend()

    # Plot 5: Max Drawdown
    ax5 = fig.add_subplot(gs[1, 1])
    drawdowns = [s['max_drawdown'] for s in valid_stats]
    bars5 = ax5.bar(range(len(drawdowns)), drawdowns, color='crimson', alpha=0.7, edgecolor='black')
    ax5.set_xticks(range(len(valid_names)))
    ax5.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax5.set_ylabel('Max Drawdown %')
    ax5.set_title('Maximum Drawdown Comparison', fontweight='bold')
    ax5.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars5):
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height,
                f'{drawdowns[i]:.1f}%', ha='center', va='top',
                fontsize=9, fontweight='bold')

    # Plot 6: Sharpe Ratio
    ax6 = fig.add_subplot(gs[1, 2])
    sharpes = [s['sharpe_ratio'] for s in valid_stats]
    colors6 = ['green' if sh > 0 else 'red' for sh in sharpes]
    bars6 = ax6.bar(range(len(sharpes)), sharpes, color=colors6, alpha=0.7, edgecolor='black')
    ax6.set_xticks(range(len(valid_names)))
    ax6.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax6.set_ylabel('Sharpe Ratio')
    ax6.set_title('Sharpe Ratio Comparison', fontweight='bold')
    ax6.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax6.grid(True, alpha=0.3, axis='y')

    # Plot 7: Equity Curves
    ax7 = fig.add_subplot(gs[2, :])

    for i, stats in enumerate(valid_stats):
        if stats['total_trades'] > 0:
            capital = initial_capital
            equity = [capital]

            for trade in stats['trades']:
                capital += trade['pnl']
                equity.append(capital)

            ax7.plot(equity, label=valid_names[i], linewidth=2, alpha=0.8)

    ax7.axhline(y=initial_capital, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Initial Capital')
    ax7.set_xlabel('Trade Number')
    ax7.set_ylabel('Equity ($)')
    ax7.set_title('Equity Curves Comparison', fontweight='bold', fontsize=12)
    ax7.legend(loc='best')
    ax7.grid(True, alpha=0.3)

    plt.suptitle('XAUUSD Gold - Strategy Comparison', fontsize=16, fontweight='bold', y=0.995)

    filename = 'gold_strategies_comparison.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n📊 Comparison chart saved as '{filename}'")
    plt.close()


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("GOLD-OPTIMIZED SMC STRATEGY TESTING")
    print("="*80)

    # Generate realistic gold data
    print("\n📊 Generating realistic XAUUSD data...")
    df = generate_realistic_gold_data(days=365)

    print(f"\n✅ Data generated:")
    print(f"   Period: {len(df)} days")
    print(f"   Date Range: {df.index[0]} to {df.index[-1]}")
    print(f"   Price Range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"   Avg Daily Range: ${(df['high'] - df['low']).mean():.2f}")

    # Test all strategies
    results, all_stats, all_dfs = test_all_gold_strategies(df)

    # Plot comparison
    strategy_names = ['Basic SMC', 'Simplified SMC', 'Gold-Optimized',
                     'Gold-Aggressive', 'Gold-Conservative']

    if len(all_stats) > 0:
        initial_capital = 10000
        plot_gold_comparison(df, all_stats, strategy_names)

        # Save detailed results for best strategy
        valid_stats = [(i, s) for i, s in enumerate(all_stats) if s['total_trades'] > 0]

        if len(valid_stats) > 0:
            # Find best by return
            best_idx, best_stats = max(valid_stats, key=lambda x: x[1]['total_return_pct'])
            best_name = strategy_names[best_idx]

            print(f"\n{'='*80}")
            print(f"DETAILED RESULTS - {best_name}")
            print(f"{'='*80}")

            bt = Backtester(initial_capital=10000)
            bt.print_results(best_stats)

            # Save trades
            if best_stats['total_trades'] > 0:
                df_trades = pd.DataFrame(best_stats['trades'])
                df_trades.to_csv('gold_optimized_best_trades.csv', index=False)
                print(f"\n💾 Best strategy trades saved to 'gold_optimized_best_trades.csv'")

    print(f"\n{'='*80}")
    print("✅ GOLD-OPTIMIZED TESTING COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
