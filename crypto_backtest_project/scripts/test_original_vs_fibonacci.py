"""
Test Original Multi-Signal vs Fibonacci 1.618 Strategy
Compare performance on 2025 XAUUSD data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy as OriginalStrategy
from fibonacci_1618_strategy import MultiSignalGoldStrategy as FibonacciStrategy
from intraday_gold_data import generate_intraday_gold_data


def generate_2025_data(months=11):
    """Generate 2025 data using realistic gold price action"""
    print(f"\n📊 Generating {months} months of 2025 XAUUSD data...")
    total_days = months * 30
    df = generate_intraday_gold_data(days=total_days, timeframe='1H')
    start_date = datetime(2025, 1, 1)
    df.index = pd.date_range(start=start_date, periods=len(df), freq='h')
    # Filter to weekdays only
    df = df[df.index.dayofweek < 5]
    # Keep only Jan-Nov 2025
    df = df[(df.index >= '2025-01-01') & (df.index < '2025-12-01')]
    print(f"✅ Generated {len(df)} hourly candles")
    return df


def backtest_strategy(df_strategy, strategy_name):
    """
    Simple backtest: Execute all signals and track wins/losses
    """
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    if len(df_signals) == 0:
        print(f"⚠️  No signals generated!")
        return None

    trades = []
    wins = 0
    losses = 0
    total_pnl = 0

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']

        # Find exit in next 48 hours (2 days)
        entry_time = df_signals.index[i]
        search_end = entry_time + timedelta(hours=48)

        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]

        if len(df_future) == 0:
            continue

        # Check for SL or TP hit
        exit_price = None
        exit_type = None

        for j in range(len(df_future)):
            if direction == 1:  # Long
                if df_future['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif df_future['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break
            else:  # Short
                if df_future['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif df_future['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break

        if exit_price is None:
            # No exit found, close at last candle
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'

        # Calculate PnL
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        total_pnl += pnl_pct

        if pnl_pct > 0:
            wins += 1
        else:
            losses += 1

        trades.append({
            'entry_time': entry_time,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'signal_type': signal.get('signal_type', 'unknown')
        })

    return {
        'total_trades': len(trades),
        'wins': wins,
        'losses': losses,
        'win_rate': (wins / len(trades) * 100) if len(trades) > 0 else 0,
        'total_pnl': total_pnl,
        'avg_pnl': total_pnl / len(trades) if len(trades) > 0 else 0,
        'trades': trades,
        'df_signals': df_signals
    }


def analyze_performance(results, strategy_name):
    """Print detailed performance analysis"""
    if results is None:
        print(f"⚠️  Cannot analyze - no trades generated\n")
        return

    print(f"\n{'='*80}")
    print(f"📊 {strategy_name.upper()} - RESULTS")
    print(f"{'='*80}\n")

    print(f"🎯 Overall Performance:")
    print(f"  Total Trades:      {results['total_trades']}")
    print(f"  Wins:              {results['wins']} / {results['total_trades']}")
    print(f"  Win Rate:          {results['win_rate']:.1f}%")
    print(f"  Total PnL:         {results['total_pnl']:+.2f}%")
    print(f"  Avg PnL/Trade:     {results['avg_pnl']:+.2f}%")

    # Monthly breakdown
    trades_df = pd.DataFrame(results['trades'])
    trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')

    print(f"\n📅 Monthly Performance:")
    monthly = trades_df.groupby('month').agg({
        'pnl_pct': ['count', lambda x: (x > 0).sum() / len(x) * 100, 'sum']
    }).round(2)
    monthly.columns = ['Trades', 'WR%', 'PnL%']

    for month, row in monthly.iterrows():
        profitable = "💰" if row['PnL%'] > 0 else "📉"
        print(f"  {month}:  {int(row['Trades']):3d} trades | {row['WR%']:5.1f}% WR | {row['PnL%']:+7.2f}% {profitable}")

    profitable_months = len(monthly[monthly['PnL%'] > 0])
    print(f"\n  💰 Profitable Months: {profitable_months}/11 ({profitable_months/11*100:.0f}%)")

    # Performance by signal type
    print(f"\n📊 Performance by Signal Type:")
    by_type = trades_df.groupby('signal_type').agg({
        'pnl_pct': ['count', lambda x: (x > 0).sum() / len(x) * 100, 'sum']
    }).round(2)
    by_type.columns = ['Trades', 'WR%', 'PnL%']
    by_type = by_type.sort_values('PnL%', ascending=False)

    for signal_type, row in by_type.iterrows():
        print(f"  {signal_type:25s}: {int(row['Trades']):3d} trades | {row['WR%']:5.1f}% WR | {row['PnL%']:+7.2f}%")


def compare_strategies(original_results, fib_results):
    """Compare two strategies head-to-head"""
    print(f"\n{'='*90}")
    print(f"⚔️  ORIGINAL vs FIBONACCI 1.618 - DETAILED COMPARISON")
    print(f"{'='*90}\n")

    metrics = {
        'Total PnL (%)': ('total_pnl', True),
        'Win Rate (%)': ('win_rate', True),
        'Total Trades': ('total_trades', True),
        'Avg PnL/Trade (%)': ('avg_pnl', True),
    }

    print(f"{'METRIC':<25} {'Original':<20} {'Fibonacci':<20} {'Winner':<20}")
    print(f"{'-'*90}")

    score_original = 0
    score_fib = 0

    for metric_name, (metric_key, higher_better) in metrics.items():
        orig_val = original_results[metric_key]
        fib_val = fib_results[metric_key]

        if higher_better:
            winner = "Original" if orig_val > fib_val else "Fibonacci"
            if orig_val > fib_val:
                score_original += 1
            else:
                score_fib += 1
        else:
            winner = "Original" if orig_val < fib_val else "Fibonacci"
            if orig_val < fib_val:
                score_original += 1
            else:
                score_fib += 1

        print(f"{metric_name:<25} {orig_val:<20.2f} {fib_val:<20.2f} {winner:<20}")

    print(f"\n{'='*90}")
    print(f"🏆 OVERALL WINNER")
    print(f"{'='*90}\n")

    print(f"Scoring (0-{len(metrics)} points):")
    print(f"  Original:  {score_original} points")
    print(f"  Fibonacci: {score_fib} points\n")

    if score_original > score_fib:
        print(f"🥇 WINNER: ORIGINAL MULTI-SIGNAL\n")
        diff_pnl = original_results['total_pnl'] - fib_results['total_pnl']
        diff_trades = original_results['total_trades'] - fib_results['total_trades']
        print(f"   Original outperforms Fibonacci!")
        print(f"   Advantages:")
        print(f"   ✅ {diff_pnl:+.2f}% more profit")
        if diff_trades != 0:
            print(f"   ✅ {abs(diff_trades)} {'more' if diff_trades > 0 else 'fewer'} trades")
    else:
        print(f"🥇 WINNER: FIBONACCI 1.618\n")
        diff_pnl = fib_results['total_pnl'] - original_results['total_pnl']
        diff_trades = fib_results['total_trades'] - original_results['total_trades']
        print(f"   Fibonacci 1.618 extension creates better risk/reward!")
        print(f"   Advantages:")
        print(f"   ✅ {diff_pnl:+.2f}% more profit")
        if diff_trades != 0:
            print(f"   ✅ {abs(diff_trades)} {'more' if diff_trades > 0 else 'fewer'} trades")


def main():
    print("="*80)
    print("🚀 ORIGINAL vs FIBONACCI 1.618 - 2025 Analysis (Jan-Nov)")
    print("="*80)
    print()

    # Generate data
    df = generate_2025_data()

    # Test 1: Original Multi-Signal Strategy
    print("="*80)
    print("1️⃣  ORIGINAL MULTI-SIGNAL STRATEGY")
    print("="*80)
    print()

    original_strategy = OriginalStrategy()
    df_original = original_strategy.run_strategy(df.copy())
    original_results = backtest_strategy(df_original, "Original Multi-Signal")
    analyze_performance(original_results, "Original Multi-Signal")

    # Test 2: Fibonacci 1.618 Strategy
    print("\n" + "="*80)
    print("2️⃣  FIBONACCI 1.618 STRATEGY")
    print("="*80)
    print()

    fib_strategy = FibonacciStrategy()
    df_fib = fib_strategy.run_strategy(df.copy())
    fib_results = backtest_strategy(df_fib, "Fibonacci 1.618")
    analyze_performance(fib_results, "Fibonacci 1.618")

    # Compare
    if original_results and fib_results:
        compare_strategies(original_results, fib_results)

        # Create comparison chart
        create_comparison_chart(original_results, fib_results)

    print("\n✅ Testing complete!")


def create_comparison_chart(original_results, fib_results):
    """Create visual comparison chart"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # 1. Total PnL comparison
    ax1 = axes[0, 0]
    strategies = ['Original', 'Fibonacci 1.618']
    pnls = [original_results['total_pnl'], fib_results['total_pnl']]
    colors = ['#2ecc71' if p > 0 else '#e74c3c' for p in pnls]
    ax1.bar(strategies, pnls, color=colors, alpha=0.7)
    ax1.set_ylabel('Total PnL (%)')
    ax1.set_title('Total PnL Comparison')
    ax1.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax1.grid(axis='y', alpha=0.3)

    # 2. Win Rate comparison
    ax2 = axes[0, 1]
    win_rates = [original_results['win_rate'], fib_results['win_rate']]
    ax2.bar(strategies, win_rates, color=['#3498db', '#9b59b6'], alpha=0.7)
    ax2.set_ylabel('Win Rate (%)')
    ax2.set_title('Win Rate Comparison')
    ax2.axhline(y=50, color='black', linestyle='--', alpha=0.3, label='50% breakeven')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    # 3. Monthly PnL comparison
    ax3 = axes[1, 0]
    orig_trades = pd.DataFrame(original_results['trades'])
    fib_trades = pd.DataFrame(fib_results['trades'])

    orig_trades['month'] = pd.to_datetime(orig_trades['entry_time']).dt.to_period('M')
    fib_trades['month'] = pd.to_datetime(fib_trades['entry_time']).dt.to_period('M')

    orig_monthly = orig_trades.groupby('month')['pnl_pct'].sum()
    fib_monthly = fib_trades.groupby('month')['pnl_pct'].sum()

    x = np.arange(len(orig_monthly))
    width = 0.35

    ax3.bar(x - width/2, orig_monthly.values, width, label='Original', alpha=0.7, color='#2ecc71')
    ax3.bar(x + width/2, fib_monthly.values, width, label='Fibonacci', alpha=0.7, color='#9b59b6')
    ax3.set_xlabel('Month')
    ax3.set_ylabel('PnL (%)')
    ax3.set_title('Monthly PnL Comparison')
    ax3.set_xticks(x)
    ax3.set_xticklabels([str(m) for m in orig_monthly.index], rotation=45)
    ax3.legend()
    ax3.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax3.grid(axis='y', alpha=0.3)

    # 4. Trade count comparison
    ax4 = axes[1, 1]
    trade_counts = [original_results['total_trades'], fib_results['total_trades']]
    ax4.bar(strategies, trade_counts, color=['#e67e22', '#1abc9c'], alpha=0.7)
    ax4.set_ylabel('Number of Trades')
    ax4.set_title('Total Trades Comparison')
    ax4.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig('original_vs_fibonacci_comparison.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Chart saved: original_vs_fibonacci_comparison.png")


if __name__ == "__main__":
    main()
