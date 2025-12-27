"""
Test Intraday Gold Strategies
Target: 1+ signals per day
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import (
    IntradayGoldStrategy,
    IntradayGoldScalper,
    IntradayGoldConservative,
    MultiSignalGoldStrategy
)
from ultra_aggressive_gold import UltraAggressiveGoldStrategy
from optimized_intraday_gold import OptimizedIntradayGold
from gold_optimized_smc_strategy import GoldOptimizedSMCStrategy
from backtester import Backtester
from intraday_gold_data import generate_intraday_gold_data


def test_intraday_strategies(df):
    """
    Test all intraday strategies

    Strategies:
    1. Daily Gold-Optimized (baseline - should have few signals)
    2. Intraday Gold (balanced - target 1-2/day)
    3. Intraday Scalper (aggressive - target 2-5/day)
    4. Intraday Conservative (selective - target 0.5-1/day)
    5. Multi-Signal Gold (all patterns - target 2-3/day)
    """
    print(f"\n{'='*80}")
    print(f"INTRADAY GOLD STRATEGY TESTING (1H Timeframe)")
    print(f"{'='*80}")
    print(f"Data: {len(df)} hourly candles ({len(df)//24} days)")
    print(f"Price Range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"Avg Hourly Vol: {((df['high'] - df['low']) / df['close'] * 100).mean():.3f}%")

    results = []
    all_stats = []
    days = len(df) // 24

    # Backtester settings
    initial_capital = 10000
    commission = 0.001
    slippage = 0.0005

    # Test 1: Daily strategy as baseline (should have very few signals)
    print(f"\n{'='*80}")
    print("1️⃣  DAILY GOLD-OPTIMIZED (Baseline - for comparison)")
    print(f"{'='*80}")

    try:
        strategy1 = GoldOptimizedSMCStrategy(
            swing_length=12,
            min_candle_quality=40
        )
        df1 = strategy1.run_strategy(df.copy())
        bt1 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats1 = bt1.run(df1)

        signals_per_day = stats1['total_trades'] / days if days > 0 else 0

        results.append({
            'Strategy': 'Daily (Baseline)',
            'Total Trades': stats1['total_trades'],
            'Trades/Day': f"{signals_per_day:.2f}",
            'Win Rate %': f"{stats1['win_rate']:.1f}",
            'Return %': f"{stats1['total_return_pct']:.2f}",
            'Sharpe': f"{stats1['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats1['max_drawdown']:.2f}"
        })

        all_stats.append(stats1)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Intraday Gold (Balanced)
    print(f"\n{'='*80}")
    print("2️⃣  INTRADAY GOLD (Balanced - Target 1-2/day)")
    print(f"{'='*80}")

    try:
        strategy2 = IntradayGoldStrategy()
        df2 = strategy2.run_strategy(df.copy())
        bt2 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats2 = bt2.run(df2)

        signals_per_day = stats2['total_trades'] / days if days > 0 else 0

        results.append({
            'Strategy': 'Intraday Balanced',
            'Total Trades': stats2['total_trades'],
            'Trades/Day': f"{signals_per_day:.2f}",
            'Win Rate %': f"{stats2['win_rate']:.1f}",
            'Return %': f"{stats2['total_return_pct']:.2f}",
            'Sharpe': f"{stats2['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats2['max_drawdown']:.2f}"
        })

        all_stats.append(stats2)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Intraday Scalper
    print(f"\n{'='*80}")
    print("3️⃣  INTRADAY SCALPER (Aggressive - Target 2-5/day)")
    print(f"{'='*80}")

    try:
        strategy3 = IntradayGoldScalper()
        df3 = strategy3.run_strategy(df.copy())
        bt3 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats3 = bt3.run(df3)

        signals_per_day = stats3['total_trades'] / days if days > 0 else 0

        results.append({
            'Strategy': 'Intraday Scalper',
            'Total Trades': stats3['total_trades'],
            'Trades/Day': f"{signals_per_day:.2f}",
            'Win Rate %': f"{stats3['win_rate']:.1f}",
            'Return %': f"{stats3['total_return_pct']:.2f}",
            'Sharpe': f"{stats3['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats3['max_drawdown']:.2f}"
        })

        all_stats.append(stats3)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 4: Intraday Conservative
    print(f"\n{'='*80}")
    print("4️⃣  INTRADAY CONSERVATIVE (Selective - Target 0.5-1/day)")
    print(f"{'='*80}")

    try:
        strategy4 = IntradayGoldConservative()
        df4 = strategy4.run_strategy(df.copy())
        bt4 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats4 = bt4.run(df4)

        signals_per_day = stats4['total_trades'] / days if days > 0 else 0

        results.append({
            'Strategy': 'Intraday Conservative',
            'Total Trades': stats4['total_trades'],
            'Trades/Day': f"{signals_per_day:.2f}",
            'Win Rate %': f"{stats4['win_rate']:.1f}",
            'Return %': f"{stats4['total_return_pct']:.2f}",
            'Sharpe': f"{stats4['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats4['max_drawdown']:.2f}"
        })

        all_stats.append(stats4)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 5: Multi-Signal Strategy
    print(f"\n{'='*80}")
    print("5️⃣  MULTI-SIGNAL GOLD (All Patterns - Target 2-3/day)")
    print(f"{'='*80}")

    try:
        strategy5 = MultiSignalGoldStrategy()
        df5 = strategy5.run_strategy(df.copy())
        bt5 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats5 = bt5.run(df5)

        signals_per_day = stats5['total_trades'] / days if days > 0 else 0

        results.append({
            'Strategy': 'Multi-Signal',
            'Total Trades': stats5['total_trades'],
            'Trades/Day': f"{signals_per_day:.2f}",
            'Win Rate %': f"{stats5['win_rate']:.1f}",
            'Return %': f"{stats5['total_return_pct']:.2f}",
            'Sharpe': f"{stats5['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats5['max_drawdown']:.2f}"
        })

        all_stats.append(stats5)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 6: Ultra-Aggressive Strategy
    print(f"\n{'='*80}")
    print("6️⃣  ULTRA-AGGRESSIVE GOLD (Maximum Signals - Target 1-3+/day)")
    print(f"{'='*80}")

    try:
        strategy6 = UltraAggressiveGoldStrategy()
        df6 = strategy6.run_strategy(df.copy())
        bt6 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats6 = bt6.run(df6)

        signals_per_day = stats6['total_trades'] / days if days > 0 else 0

        results.append({
            'Strategy': 'Ultra-Aggressive',
            'Total Trades': stats6['total_trades'],
            'Trades/Day': f"{signals_per_day:.2f}",
            'Win Rate %': f"{stats6['win_rate']:.1f}",
            'Return %': f"{stats6['total_return_pct']:.2f}",
            'Sharpe': f"{stats6['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats6['max_drawdown']:.2f}"
        })

        all_stats.append(stats6)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test 7: Optimized Intraday (Best Balance)
    print(f"\n{'='*80}")
    print("7️⃣  OPTIMIZED INTRADAY (Best Balance - Target 1-2/day, 40-50% WR)")
    print(f"{'='*80}")

    try:
        strategy7 = OptimizedIntradayGold()
        df7 = strategy7.run_strategy(df.copy())
        bt7 = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
        stats7 = bt7.run(df7)

        signals_per_day = stats7['total_trades'] / days if days > 0 else 0

        results.append({
            'Strategy': 'Optimized Intraday',
            'Total Trades': stats7['total_trades'],
            'Trades/Day': f"{signals_per_day:.2f}",
            'Win Rate %': f"{stats7['win_rate']:.1f}",
            'Return %': f"{stats7['total_return_pct']:.2f}",
            'Sharpe': f"{stats7['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats7['max_drawdown']:.2f}"
        })

        all_stats.append(stats7)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Display results
    print(f"\n{'='*80}")
    print("INTRADAY COMPARISON RESULTS")
    print(f"{'='*80}\n")

    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))

    # Find best by trades/day
    df_results['Trades_Per_Day_Num'] = df_results['Trades/Day'].astype(float)

    best_frequency = df_results.loc[df_results['Trades_Per_Day_Num'].idxmax()]
    best_return = df_results.loc[df_results['Return %'].astype(float).idxmax()]

    print(f"\n{'='*80}")
    print(f"📊 ANALYSIS")
    print(f"{'='*80}")
    print(f"Most Signals: {best_frequency['Strategy']} ({best_frequency['Trades/Day']} trades/day)")
    print(f"Best Returns: {best_return['Strategy']} ({best_return['Return %']}%)")

    # Check if we met goal (1+ trades/day)
    strategies_meeting_goal = df_results[df_results['Trades_Per_Day_Num'] >= 1.0]

    if len(strategies_meeting_goal) > 0:
        print(f"\n✅ {len(strategies_meeting_goal)} strategies met goal of 1+ trades/day:")
        for idx, row in strategies_meeting_goal.iterrows():
            print(f"   - {row['Strategy']}: {row['Trades/Day']} trades/day")
    else:
        print(f"\n⚠️  No strategies met goal of 1+ trades/day")
        print(f"   Highest: {best_frequency['Strategy']} with {best_frequency['Trades/Day']} trades/day")

    return results, all_stats


def plot_intraday_results(df, all_stats, strategy_names, days):
    """Plot intraday comparison"""

    valid_stats = [s for s in all_stats if s['total_trades'] > 0]
    valid_names = [strategy_names[i] for i, s in enumerate(all_stats) if s['total_trades'] > 0]

    if len(valid_stats) == 0:
        print("\n⚠️  No valid strategies to plot")
        return

    fig = plt.figure(figsize=(18, 10))
    gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

    # Plot 1: Trades per Day
    ax1 = fig.add_subplot(gs[0, 0])
    trades_per_day = [s['total_trades'] / days for s in valid_stats]
    colors = ['green' if tpd >= 1.0 else 'orange' for tpd in trades_per_day]
    bars = ax1.bar(range(len(trades_per_day)), trades_per_day, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xticks(range(len(valid_names)))
    ax1.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax1.set_ylabel('Trades per Day')
    ax1.set_title('Signal Frequency (Target: 1+ per day)', fontweight='bold')
    ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Goal: 1/day')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.legend()

    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{trades_per_day[i]:.2f}', ha='center', va='bottom',
                fontsize=9, fontweight='bold')

    # Plot 2: Returns
    ax2 = fig.add_subplot(gs[0, 1])
    returns = [s['total_return_pct'] for s in valid_stats]
    colors2 = ['green' if r > 0 else 'red' for r in returns]
    bars2 = ax2.bar(range(len(returns)), returns, color=colors2, alpha=0.7, edgecolor='black')
    ax2.set_xticks(range(len(valid_names)))
    ax2.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax2.set_ylabel('Return %')
    ax2.set_title('Total Return', fontweight='bold')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax2.grid(True, alpha=0.3, axis='y')

    # Plot 3: Win Rate
    ax3 = fig.add_subplot(gs[0, 2])
    win_rates = [s['win_rate'] for s in valid_stats]
    bars3 = ax3.bar(range(len(win_rates)), win_rates, color='steelblue', alpha=0.7, edgecolor='black')
    ax3.set_xticks(range(len(valid_names)))
    ax3.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax3.set_ylabel('Win Rate %')
    ax3.set_title('Win Rate', fontweight='bold')
    ax3.axhline(y=50, color='orange', linestyle='--', linewidth=1, label='50%')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.legend()

    # Plot 4: Sharpe Ratio
    ax4 = fig.add_subplot(gs[1, 0])
    sharpes = [s['sharpe_ratio'] for s in valid_stats]
    colors4 = ['green' if sh > 0 else 'red' for sh in sharpes]
    bars4 = ax4.bar(range(len(sharpes)), sharpes, color=colors4, alpha=0.7, edgecolor='black')
    ax4.set_xticks(range(len(valid_names)))
    ax4.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax4.set_ylabel('Sharpe Ratio')
    ax4.set_title('Risk-Adjusted Returns', fontweight='bold')
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax4.grid(True, alpha=0.3, axis='y')

    # Plot 5: Max Drawdown
    ax5 = fig.add_subplot(gs[1, 1])
    drawdowns = [s['max_drawdown'] for s in valid_stats]
    bars5 = ax5.bar(range(len(drawdowns)), drawdowns, color='crimson', alpha=0.7, edgecolor='black')
    ax5.set_xticks(range(len(valid_names)))
    ax5.set_xticklabels(valid_names, rotation=45, ha='right', fontsize=9)
    ax5.set_ylabel('Max Drawdown %')
    ax5.set_title('Maximum Drawdown', fontweight='bold')
    ax5.grid(True, alpha=0.3, axis='y')

    # Plot 6: Equity Curves
    ax6 = fig.add_subplot(gs[1, 2])

    for i, stats in enumerate(valid_stats):
        if stats['total_trades'] > 0:
            capital = 10000
            equity = [capital]

            for trade in stats['trades']:
                capital += trade['pnl']
                equity.append(capital)

            ax6.plot(equity, label=valid_names[i], linewidth=2, alpha=0.8)

    ax6.axhline(y=10000, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Initial')
    ax6.set_xlabel('Trade Number')
    ax6.set_ylabel('Equity ($)')
    ax6.set_title('Equity Curves', fontweight='bold')
    ax6.legend(loc='best', fontsize=8)
    ax6.grid(True, alpha=0.3)

    plt.suptitle(f'XAUUSD Intraday (1H) - Strategy Comparison ({days} days)',
                 fontsize=14, fontweight='bold', y=0.995)

    filename = 'intraday_gold_comparison.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n📊 Chart saved as '{filename}'")
    plt.close()


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("INTRADAY GOLD STRATEGY TESTING")
    print("Target: 1+ signals per day")
    print("="*80)

    # Generate 30 days of 1H data
    days = 30
    print(f"\n📊 Generating {days} days of 1H XAUUSD data...")
    df = generate_intraday_gold_data(days=days, timeframe='1H')

    print(f"\n✅ Data generated:")
    print(f"   Period: {len(df)} hourly candles ({days} days)")
    print(f"   Date Range: {df.index[0]} to {df.index[-1]}")
    print(f"   Price Range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"   Avg Hourly Range: ${(df['high'] - df['low']).mean():.2f}")

    # Test all strategies
    results, all_stats = test_intraday_strategies(df)

    # Plot results
    strategy_names = ['Daily (Baseline)', 'Intraday Balanced', 'Intraday Scalper',
                     'Intraday Conservative', 'Multi-Signal', 'Ultra-Aggressive', 'Optimized Intraday']

    if len(all_stats) > 0:
        plot_intraday_results(df, all_stats, strategy_names, days)

        # Save best strategy trades
        valid_stats = [s for s in all_stats if s['total_trades'] > 0]

        if len(valid_stats) > 0:
            # Find strategy with most trades/day
            trades_per_day = [s['total_trades'] / days for s in valid_stats]
            best_idx = np.argmax(trades_per_day)
            best_stats = valid_stats[best_idx]
            best_name = strategy_names[best_idx]

            print(f"\n{'='*80}")
            print(f"DETAILED RESULTS - {best_name}")
            print(f"{'='*80}")

            bt = Backtester(initial_capital=10000)
            bt.print_results(best_stats)

            if best_stats['total_trades'] > 0:
                df_trades = pd.DataFrame(best_stats['trades'])
                df_trades.to_csv('intraday_gold_best_trades.csv', index=False)
                print(f"\n💾 Best strategy trades saved to 'intraday_gold_best_trades.csv'")

    print(f"\n{'='*80}")
    print("✅ INTRADAY TESTING COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
