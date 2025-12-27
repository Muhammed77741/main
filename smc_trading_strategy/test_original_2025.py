"""
Test Original Multi-Signal Strategy (WITHOUT Trailing SL) on 2025 Data
Monthly breakdown analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy
from intraday_gold_data import generate_intraday_gold_data


def generate_2025_data(months=11):
    """
    Generate 2025 data from January to November
    """
    print(f"\n📊 Generating {months} months of 2025 XAUUSD data...")

    total_days = months * 30
    df = generate_intraday_gold_data(days=total_days, timeframe='1H')

    start_date = datetime(2025, 1, 1)
    df.index = pd.date_range(
        start=start_date,
        periods=len(df),
        freq='1h'
    )

    df = df[df.index.dayofweek < 5]
    df = df[(df.index >= '2025-01-01') & (df.index < '2025-12-01')]

    print(f"✅ Generated {len(df)} hourly candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    print(f"   Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")

    return df


def backtest_with_monthly_stats(df_strategy):
    """
    Backtest the strategy and collect monthly statistics
    """
    trades = []
    monthly_stats = {}

    # Track all open positions
    for i in range(len(df_strategy)):
        if df_strategy['signal'].iloc[i] == 0:
            continue

        current_time = df_strategy.index[i]
        current_month = current_time.strftime('%Y-%m')

        # Initialize monthly stats
        if current_month not in monthly_stats:
            monthly_stats[current_month] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'pnl': 0.0,
                'total_r': 0.0,
                'tp_hits': 0,
                'sl_hits': 0
            }

        entry_price = df_strategy['entry_price'].iloc[i]
        stop_loss = df_strategy['stop_loss'].iloc[i]
        take_profit = df_strategy['take_profit'].iloc[i]
        direction = df_strategy['signal'].iloc[i]
        signal_type = df_strategy['signal_type'].iloc[i] if 'signal_type' in df_strategy.columns else 'unknown'

        if pd.isna(entry_price) or pd.isna(stop_loss) or pd.isna(take_profit):
            continue

        # Look ahead to find exit (max 48 hours = 2 days)
        exit_price = None
        exit_reason = None
        exit_time = None

        for j in range(i+1, min(i+49, len(df_strategy))):
            if direction == 1:  # Long
                # Check SL first
                if df_strategy['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    exit_time = df_strategy.index[j]
                    break
                # Check TP
                elif df_strategy['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    exit_time = df_strategy.index[j]
                    break
            else:  # Short
                # Check SL first
                if df_strategy['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    exit_time = df_strategy.index[j]
                    break
                # Check TP
                elif df_strategy['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    exit_time = df_strategy.index[j]
                    break

        # If no exit found, skip this trade
        if exit_price is None:
            continue

        # Calculate PnL
        if direction == 1:
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            risk = abs(entry_price - stop_loss)
            r_multiple = (exit_price - entry_price) / risk if risk > 0 else 0
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100
            risk = abs(stop_loss - entry_price)
            r_multiple = (entry_price - exit_price) / risk if risk > 0 else 0

        # Record trade
        trades.append({
            'entry_time': current_time,
            'exit_time': exit_time,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'pnl_pct': pnl_pct,
            'r_multiple': r_multiple,
            'exit_reason': exit_reason,
            'signal_type': signal_type
        })

        # Update monthly stats
        monthly_stats[current_month]['trades'] += 1
        monthly_stats[current_month]['pnl'] += pnl_pct
        monthly_stats[current_month]['total_r'] += r_multiple

        if pnl_pct > 0:
            monthly_stats[current_month]['wins'] += 1
            if exit_reason == 'TP':
                monthly_stats[current_month]['tp_hits'] += 1
        else:
            monthly_stats[current_month]['losses'] += 1
            if exit_reason == 'SL':
                monthly_stats[current_month]['sl_hits'] += 1

    return trades, monthly_stats


def print_monthly_breakdown(monthly_stats):
    """
    Print detailed monthly breakdown
    """
    print("\n" + "="*80)
    print("📅 MONTHLY BREAKDOWN (Jan-Nov 2025) - ORIGINAL STRATEGY")
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
        avg_r = stats['total_r'] / trades if trades > 0 else 0

        total_trades += trades
        total_wins += wins
        total_losses += losses
        total_pnl += pnl

        print(f"\n{month}:")
        print(f"  Trades: {trades:3d} | Wins: {wins:3d} | Losses: {losses:3d} | WR: {win_rate:5.1f}%")
        print(f"  PnL: {pnl:+7.2f}% | Avg R: {avg_r:+5.2f}R")
        print(f"  TP hits: {stats['tp_hits']:3d} | SL hits: {stats['sl_hits']:3d}")

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
    print(f"Avg PnL per trade: {total_pnl/total_trades:+.2f}%")

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
    avg_r_per_month = [
        monthly_stats[m]['total_r'] / monthly_stats[m]['trades']
        if monthly_stats[m]['trades'] > 0 else 0
        for m in months_order
    ]

    month_labels = [datetime.strptime(m, '%Y-%m').strftime('%b') for m in months_order]

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Plot 1: Monthly PnL
    colors = ['green' if pnl > 0 else 'red' for pnl in pnl_per_month]
    axes[0, 0].bar(month_labels, pnl_per_month, color=colors, alpha=0.7, edgecolor='black')
    axes[0, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[0, 0].set_title('Monthly PnL (%) - Original Strategy (No Trailing SL)', fontsize=12, fontweight='bold')
    axes[0, 0].set_ylabel('PnL (%)')
    axes[0, 0].grid(True, alpha=0.3)

    for i, pnl in enumerate(pnl_per_month):
        axes[0, 0].text(i, pnl, f'{pnl:+.1f}%', ha='center', va='bottom' if pnl > 0 else 'top', fontsize=9)

    # Plot 2: Trades per Month
    axes[0, 1].bar(month_labels, trades_per_month, color='steelblue', alpha=0.7, edgecolor='black')
    axes[0, 1].set_title('Trades per Month - Original Strategy', fontsize=12, fontweight='bold')
    axes[0, 1].set_ylabel('Number of Trades')
    axes[0, 1].grid(True, alpha=0.3)

    for i, trades in enumerate(trades_per_month):
        axes[0, 1].text(i, trades, str(trades), ha='center', va='bottom', fontsize=9)

    # Plot 3: Win Rate per Month
    axes[1, 0].plot(month_labels, win_rates, marker='o', linewidth=2, markersize=8, color='purple')
    axes[1, 0].axhline(y=50, color='red', linestyle='--', linewidth=1, label='50% WR')
    axes[1, 0].set_title('Win Rate per Month - Original Strategy', fontsize=12, fontweight='bold')
    axes[1, 0].set_ylabel('Win Rate (%)')
    axes[1, 0].set_xlabel('Month')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend()

    for i, wr in enumerate(win_rates):
        axes[1, 0].text(i, wr, f'{wr:.0f}%', ha='center', va='bottom', fontsize=9)

    # Plot 4: Avg R-Multiple per Month
    colors_r = ['green' if r > 0 else 'red' for r in avg_r_per_month]
    axes[1, 1].bar(month_labels, avg_r_per_month, color=colors_r, alpha=0.7, edgecolor='black')
    axes[1, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[1, 1].set_title('Avg R-Multiple per Month - Original Strategy', fontsize=12, fontweight='bold')
    axes[1, 1].set_ylabel('Avg R-Multiple')
    axes[1, 1].set_xlabel('Month')
    axes[1, 1].grid(True, alpha=0.3)

    for i, r in enumerate(avg_r_per_month):
        axes[1, 1].text(i, r, f'{r:+.2f}R', ha='center', va='bottom' if r > 0 else 'top', fontsize=9)

    plt.tight_layout()
    plt.savefig('original_monthly_results_2025.png', dpi=150, bbox_inches='tight')
    print(f"\n📈 Chart saved: original_monthly_results_2025.png")

    return fig


def main():
    """
    Main test function
    """
    print("\n" + "="*80)
    print("🚀 ORIGINAL MULTI-SIGNAL STRATEGY - 2025 ANALYSIS (Jan-Nov)")
    print("   WITHOUT Trailing Stop Loss")
    print("="*80)

    # Generate 11 months of data
    df = generate_2025_data(months=11)

    # Run original strategy
    print("\n📊 Running Original Multi-Signal Strategy...")
    strategy = MultiSignalGoldStrategy()
    df_result = strategy.run_strategy(df)

    # Backtest with monthly breakdown
    print("\n🔍 Backtesting with monthly analysis...")
    trades, monthly_stats = backtest_with_monthly_stats(df_result)

    # Print results
    summary = print_monthly_breakdown(monthly_stats)

    # Detailed trade analysis
    print("\n" + "="*80)
    print("📈 TRADE ANALYSIS")
    print("="*80)

    avg_win = np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] > 0]) if any(t['pnl_pct'] > 0 for t in trades) else 0
    avg_loss = np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] < 0]) if any(t['pnl_pct'] < 0 for t in trades) else 0

    print(f"Average Win: {avg_win:+.2f}%")
    print(f"Average Loss: {avg_loss:+.2f}%")
    print(f"Profit Factor: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "N/A")

    # Signal type breakdown
    signal_types = {}
    for trade in trades:
        st = trade['signal_type']
        if st not in signal_types:
            signal_types[st] = {'count': 0, 'wins': 0, 'pnl': 0}
        signal_types[st]['count'] += 1
        if trade['pnl_pct'] > 0:
            signal_types[st]['wins'] += 1
        signal_types[st]['pnl'] += trade['pnl_pct']

    print(f"\n📊 Performance by Signal Type:")
    for st, stats in sorted(signal_types.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr = stats['wins'] / stats['count'] * 100 if stats['count'] > 0 else 0
        st_str = str(st) if not isinstance(st, str) else st
        print(f"  {st_str:20s}: {stats['count']:3d} trades | WR: {wr:5.1f}% | PnL: {stats['pnl']:+7.2f}%")

    # Create visualizations
    plot_monthly_results(monthly_stats)

    print("\n✅ Analysis complete!")
    print("\nFiles created:")
    print("   📊 original_monthly_results_2025.png - Monthly performance charts")


if __name__ == '__main__':
    main()
