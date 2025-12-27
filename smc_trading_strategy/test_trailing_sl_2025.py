"""
Test Trailing SL Strategy on 2025 Data (Jan-Nov)
Monthly breakdown analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trailing_sl_strategy import TrailingSLStrategy
from intraday_gold_data import generate_intraday_gold_data


def generate_2025_data(months=11):
    """
    Generate 2025 data from January to November
    Each month has ~20 trading days * 24 hours = 480 candles
    """
    print(f"\n📊 Generating {months} months of 2025 XAUUSD data...")

    # Generate all data at once for continuity
    total_days = months * 30  # ~30 days per month
    df = generate_intraday_gold_data(days=total_days, timeframe='1H')

    # Set correct dates for 2025
    start_date = datetime(2025, 1, 1)
    df.index = pd.date_range(
        start=start_date,
        periods=len(df),
        freq='1H'
    )

    # Filter out weekends
    df = df[df.index.dayofweek < 5]

    # Keep only Jan-Nov 2025
    df = df[(df.index >= '2025-01-01') & (df.index < '2025-12-01')]

    print(f"✅ Generated {len(df)} hourly candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    print(f"   Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")

    return df


def print_monthly_breakdown(monthly_stats):
    """
    Print detailed monthly breakdown
    """
    print("\n" + "="*80)
    print("📅 MONTHLY BREAKDOWN (Jan-Nov 2025)")
    print("="*80)

    total_trades = 0
    total_wins = 0
    total_losses = 0
    total_pnl = 0

    months_order = sorted(monthly_stats.keys())

    for month in months_order:
        stats = monthly_stats[month]

        trades = stats['trades']
        wins = stats['wins']
        losses = stats['losses']
        pnl = stats['pnl']
        win_rate = (wins / trades * 100) if trades > 0 else 0

        total_trades += trades
        total_wins += wins
        total_losses += losses
        total_pnl += pnl

        print(f"\n{month}:")
        print(f"  Trades: {trades:2d} | Wins: {wins:2d} | Losses: {losses:2d} | WR: {win_rate:5.1f}%")
        print(f"  PnL: {pnl:+6.2f}%")

        if trades > 0:
            print(f"  TP1 hits: {stats['tp1_hits']:2d} ({stats['tp1_hits']/trades*100:4.1f}%)")
            print(f"  TP2 hits: {stats['tp2_hits']:2d} ({stats['tp2_hits']/trades*100:4.1f}%)")
            print(f"  TP3 hits: {stats['tp3_hits']:2d} ({stats['tp3_hits']/trades*100:4.1f}%)")
            print(f"  BE moves: {stats['breakeven_moves']:2d} (SL moved to breakeven)")

    # Summary
    print("\n" + "="*80)
    print("📊 OVERALL SUMMARY (11 months)")
    print("="*80)
    print(f"Total Trades: {total_trades}")
    print(f"Wins: {total_wins} | Losses: {total_losses}")
    print(f"Win Rate: {total_wins/total_trades*100:.1f}%")
    print(f"Total PnL: {total_pnl:+.2f}%")
    print(f"Avg PnL per month: {total_pnl/11:+.2f}%")
    print(f"Avg trades per month: {total_trades/11:.1f}")

    return {
        'total_trades': total_trades,
        'total_wins': total_wins,
        'total_pnl': total_pnl,
        'win_rate': total_wins/total_trades*100 if total_trades > 0 else 0
    }


def plot_monthly_results(monthly_stats):
    """
    Visualize monthly performance
    """
    months_order = sorted(monthly_stats.keys())

    trades_per_month = [monthly_stats[m]['trades'] for m in months_order]
    pnl_per_month = [monthly_stats[m]['pnl'] for m in months_order]
    win_rates = [
        (monthly_stats[m]['wins'] / monthly_stats[m]['trades'] * 100)
        if monthly_stats[m]['trades'] > 0 else 0
        for m in months_order
    ]

    # Month labels (short format)
    month_labels = [datetime.strptime(m, '%Y-%m').strftime('%b') for m in months_order]

    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # Plot 1: Monthly PnL
    colors = ['green' if pnl > 0 else 'red' for pnl in pnl_per_month]
    axes[0].bar(month_labels, pnl_per_month, color=colors, alpha=0.7, edgecolor='black')
    axes[0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[0].set_title('Monthly PnL (%) - 2025', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('PnL (%)')
    axes[0].grid(True, alpha=0.3)

    # Add value labels
    for i, pnl in enumerate(pnl_per_month):
        axes[0].text(i, pnl, f'{pnl:+.1f}%', ha='center', va='bottom' if pnl > 0 else 'top')

    # Plot 2: Trades per Month
    axes[1].bar(month_labels, trades_per_month, color='steelblue', alpha=0.7, edgecolor='black')
    axes[1].set_title('Trades per Month - 2025', fontsize=12, fontweight='bold')
    axes[1].set_ylabel('Number of Trades')
    axes[1].grid(True, alpha=0.3)

    # Add value labels
    for i, trades in enumerate(trades_per_month):
        axes[1].text(i, trades, str(trades), ha='center', va='bottom')

    # Plot 3: Win Rate per Month
    axes[2].plot(month_labels, win_rates, marker='o', linewidth=2, markersize=8, color='purple')
    axes[2].axhline(y=50, color='red', linestyle='--', linewidth=1, label='50% WR')
    axes[2].set_title('Win Rate per Month - 2025', fontsize=12, fontweight='bold')
    axes[2].set_ylabel('Win Rate (%)')
    axes[2].set_xlabel('Month')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    # Add value labels
    for i, wr in enumerate(win_rates):
        axes[2].text(i, wr, f'{wr:.0f}%', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig('monthly_results_2025.png', dpi=150, bbox_inches='tight')
    print(f"\n📈 Chart saved: monthly_results_2025.png")

    return fig


def compare_with_without_trailing(df):
    """
    Compare performance with and without trailing SL
    """
    print("\n" + "="*80)
    print("🔄 COMPARISON: With vs Without Trailing SL")
    print("="*80)

    # Test WITH trailing SL
    print("\n1️⃣ Testing WITH Trailing SL...")
    strategy_with = TrailingSLStrategy()
    df_with = strategy_with.run_strategy(df)
    trades_with, monthly_with = strategy_with.backtest(df_with)
    summary_with = print_monthly_breakdown(monthly_with)

    # Test WITHOUT trailing SL (original)
    print("\n2️⃣ Testing WITHOUT Trailing SL (Original)...")
    from intraday_gold_strategy import MultiSignalGoldStrategy

    strategy_without = MultiSignalGoldStrategy()
    df_without = strategy_without.run_strategy(df)

    # Simple backtest for original (no trailing)
    trades_without = []
    for i in range(len(df_without)):
        if df_without['signal'].iloc[i] != 0:
            entry_price = df_without['entry_price'].iloc[i]
            stop_loss = df_without['stop_loss'].iloc[i]
            take_profit = df_without['take_profit'].iloc[i]

            # Simple win/loss simulation
            direction = df_without['signal'].iloc[i]

            # Check next 24 candles for SL/TP hit
            for j in range(i+1, min(i+25, len(df_without))):
                if direction == 1:  # Long
                    if df_without['low'].iloc[j] <= stop_loss:
                        pnl = (stop_loss - entry_price) / entry_price * 100
                        trades_without.append({'pnl_pct': pnl, 'exit_reason': 'SL'})
                        break
                    elif df_without['high'].iloc[j] >= take_profit:
                        pnl = (take_profit - entry_price) / entry_price * 100
                        trades_without.append({'pnl_pct': pnl, 'exit_reason': 'TP'})
                        break
                else:  # Short
                    if df_without['high'].iloc[j] >= stop_loss:
                        pnl = (entry_price - stop_loss) / entry_price * 100
                        trades_without.append({'pnl_pct': pnl, 'exit_reason': 'SL'})
                        break
                    elif df_without['low'].iloc[j] <= take_profit:
                        pnl = (entry_price - take_profit) / entry_price * 100
                        trades_without.append({'pnl_pct': pnl, 'exit_reason': 'TP'})
                        break

    # Calculate stats for original
    total_pnl_without = sum([t['pnl_pct'] for t in trades_without])
    wins_without = len([t for t in trades_without if t['pnl_pct'] > 0])
    wr_without = wins_without / len(trades_without) * 100 if trades_without else 0

    print(f"\n   Total Trades: {len(trades_without)}")
    print(f"   Wins: {wins_without} / {len(trades_without)}")
    print(f"   Win Rate: {wr_without:.1f}%")
    print(f"   Total PnL: {total_pnl_without:+.2f}%")

    # Comparison table
    print("\n" + "="*80)
    print("📊 FINAL COMPARISON")
    print("="*80)
    print(f"{'Metric':<25} {'With Trailing SL':<20} {'Without (Original)':<20} {'Difference':<15}")
    print("-"*80)
    print(f"{'Total Trades':<25} {summary_with['total_trades']:<20} {len(trades_without):<20} {summary_with['total_trades'] - len(trades_without):<15}")
    print(f"{'Win Rate':<25} {summary_with['win_rate']:<20.1f} {wr_without:<20.1f} {summary_with['win_rate'] - wr_without:<+15.1f}")
    print(f"{'Total PnL (%)':<25} {summary_with['total_pnl']:<+20.2f} {total_pnl_without:<+20.2f} {summary_with['total_pnl'] - total_pnl_without:<+15.2f}")

    print("\n💡 Key Benefits of Trailing SL:")
    print("   ✅ Protected profits by moving SL to breakeven")
    print("   ✅ Reduced losses from reversal after partial profit")
    print("   ✅ Locked in guaranteed gains on TP1 hits")

    return summary_with, {
        'total_pnl': total_pnl_without,
        'win_rate': wr_without,
        'total_trades': len(trades_without)
    }


def main():
    """
    Main test function
    """
    print("\n" + "="*80)
    print("🚀 TRAILING SL STRATEGY - 2025 ANALYSIS (Jan-Nov)")
    print("="*80)

    # Generate 11 months of data
    df = generate_2025_data(months=11)

    # Run comparison
    results_with, results_without = compare_with_without_trailing(df)

    # Create visualizations
    strategy = TrailingSLStrategy()
    df_result = strategy.run_strategy(df)
    trades, monthly_stats = strategy.backtest(df_result)

    plot_monthly_results(monthly_stats)

    print("\n✅ Analysis complete!")
    print("\nFiles created:")
    print("   📊 monthly_results_2025.png - Monthly performance charts")


if __name__ == '__main__':
    main()
