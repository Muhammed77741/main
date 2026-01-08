"""
Test ALL Strategies: Original, Fibonacci 1.618, Pattern Recognition (1.618 & 2.618)
Compare performance on 2025 data
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
from pattern_recognition_strategy import MultiSignalPatternStrategy
from intraday_gold_data import generate_intraday_gold_data


def generate_2025_data(months=11):
    """Generate 2025 data using realistic gold price action"""
    print(f"\n📊 Generating {months} months of 2025 XAUUSD data...")
    total_days = months * 30
    df = generate_intraday_gold_data(days=total_days, timeframe='1H')
    start_date = datetime(2025, 1, 1)
    df.index = pd.date_range(start=start_date, periods=len(df), freq='h')
    df = df[df.index.dayofweek < 5]
    df = df[(df.index >= '2025-01-01') & (df.index < '2025-12-01')]
    print(f"✅ Generated {len(df)} hourly candles")
    return df


def backtest_strategy(df_strategy, strategy_name):
    """Simple backtest"""
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

        entry_time = df_signals.index[i]
        search_end = entry_time + timedelta(hours=48)

        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]

        if len(df_future) == 0:
            continue

        exit_price = None
        exit_type = None

        for j in range(len(df_future)):
            if direction == 1:
                if df_future['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif df_future['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break
            else:
                if df_future['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif df_future['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break

        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'

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
    """Print performance analysis"""
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


def compare_all_strategies(results_dict):
    """Compare all strategies"""
    print(f"\n{'='*100}")
    print(f"⚔️  STRATEGY COMPARISON - ALL STRATEGIES")
    print(f"{'='*100}\n")

    print(f"{'STRATEGY':<30} {'Total PnL':>12} {'Win Rate':>10} {'Trades':>8} {'Avg/Trade':>12} {'Prof.Months':>12}")
    print(f"{'-'*100}")

    # Sort by Total PnL
    sorted_strategies = sorted(results_dict.items(), key=lambda x: x[1]['total_pnl'], reverse=True)

    for rank, (strategy_name, results) in enumerate(sorted_strategies, 1):
        emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "

        trades_df = pd.DataFrame(results['trades'])
        trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
        monthly = trades_df.groupby('month')['pnl_pct'].sum()
        prof_months = len(monthly[monthly > 0])

        print(f"{emoji} {strategy_name:<28} {results['total_pnl']:+11.2f}% {results['win_rate']:9.1f}% {results['total_trades']:7d} {results['avg_pnl']:+11.2f}% {prof_months:>5}/11")

    print(f"\n{'='*100}")
    print(f"🏆 WINNER: {sorted_strategies[0][0].upper()}")
    print(f"{'='*100}\n")

    winner_results = sorted_strategies[0][1]
    second_results = sorted_strategies[1][1]

    diff_pnl = winner_results['total_pnl'] - second_results['total_pnl']
    diff_trades = winner_results['total_trades'] - second_results['total_trades']

    print(f"   Победитель превосходит второе место:")
    print(f"   ✅ {diff_pnl:+.2f}% больше прибыли")
    if diff_trades != 0:
        print(f"   ✅ {abs(diff_trades)} {'больше' if diff_trades > 0 else 'меньше'} сделок")


def create_comparison_chart(results_dict):
    """Create comparison chart for all strategies"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    strategies = list(results_dict.keys())
    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']

    # 1. Total PnL
    ax1 = axes[0, 0]
    pnls = [results_dict[s]['total_pnl'] for s in strategies]
    bars = ax1.bar(range(len(strategies)), pnls, color=colors[:len(strategies)], alpha=0.7)
    ax1.set_xticks(range(len(strategies)))
    ax1.set_xticklabels(strategies, rotation=15, ha='right')
    ax1.set_ylabel('Total PnL (%)')
    ax1.set_title('Total PnL Comparison')
    ax1.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom' if height > 0 else 'top')

    # 2. Win Rate
    ax2 = axes[0, 1]
    win_rates = [results_dict[s]['win_rate'] for s in strategies]
    ax2.bar(range(len(strategies)), win_rates, color=colors[:len(strategies)], alpha=0.7)
    ax2.set_xticks(range(len(strategies)))
    ax2.set_xticklabels(strategies, rotation=15, ha='right')
    ax2.set_ylabel('Win Rate (%)')
    ax2.set_title('Win Rate Comparison')
    ax2.axhline(y=50, color='black', linestyle='--', alpha=0.3, label='50% breakeven')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    # 3. Monthly PnL (stacked)
    ax3 = axes[1, 0]
    for idx, strategy in enumerate(strategies):
        trades_df = pd.DataFrame(results_dict[strategy]['trades'])
        trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
        monthly = trades_df.groupby('month')['pnl_pct'].sum()

        months = [str(m) for m in monthly.index]
        x = np.arange(len(months))

        if idx == 0:
            ax3.plot(x, monthly.values, marker='o', label=strategy, color=colors[idx], linewidth=2)
        else:
            ax3.plot(x, monthly.values, marker='s', label=strategy, color=colors[idx], linewidth=2, alpha=0.7)

    ax3.set_xlabel('Month')
    ax3.set_ylabel('PnL (%)')
    ax3.set_title('Monthly PnL Comparison')
    ax3.set_xticks(x)
    ax3.set_xticklabels(months, rotation=45)
    ax3.legend()
    ax3.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax3.grid(alpha=0.3)

    # 4. Trade Count
    ax4 = axes[1, 1]
    trade_counts = [results_dict[s]['total_trades'] for s in strategies]
    ax4.bar(range(len(strategies)), trade_counts, color=colors[:len(strategies)], alpha=0.7)
    ax4.set_xticks(range(len(strategies)))
    ax4.set_xticklabels(strategies, rotation=15, ha='right')
    ax4.set_ylabel('Number of Trades')
    ax4.set_title('Total Trades Comparison')
    ax4.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig('all_strategies_comparison.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Chart saved: all_strategies_comparison.png")


def main():
    print("="*100)
    print("🚀 ALL STRATEGIES COMPARISON - 2025 Analysis (Jan-Nov)")
    print("="*100)

    # Generate data
    df = generate_2025_data()

    results_dict = {}

    # Test 1: Original Multi-Signal
    print("\n" + "="*100)
    print("1️⃣  ORIGINAL MULTI-SIGNAL STRATEGY")
    print("="*100)
    original_strategy = OriginalStrategy()
    df_original = original_strategy.run_strategy(df.copy())
    original_results = backtest_strategy(df_original, "Original")
    if original_results:
        analyze_performance(original_results, "Original Multi-Signal")
        results_dict['Original'] = original_results

    # Test 2: Fibonacci 1.618
    print("\n" + "="*100)
    print("2️⃣  FIBONACCI 1.618 STRATEGY")
    print("="*100)
    fib_strategy = FibonacciStrategy()
    df_fib = fib_strategy.run_strategy(df.copy())
    fib_results = backtest_strategy(df_fib, "Fibonacci 1.618")
    if fib_results:
        analyze_performance(fib_results, "Fibonacci 1.618")
        results_dict['Fibonacci 1.618'] = fib_results

    # Test 3: Pattern Recognition (Standard 1.618)
    print("\n" + "="*100)
    print("3️⃣  PATTERN RECOGNITION STRATEGY (STANDARD 1.618)")
    print("="*100)
    pattern_std_strategy = MultiSignalPatternStrategy(fib_mode='standard')
    df_pattern_std = pattern_std_strategy.run_strategy(df.copy())
    pattern_std_results = backtest_strategy(df_pattern_std, "Pattern (Std)")
    if pattern_std_results:
        analyze_performance(pattern_std_results, "Pattern Recognition (1.618)")
        results_dict['Pattern (1.618)'] = pattern_std_results

    # Test 4: Pattern Recognition (Aggressive 2.618)
    print("\n" + "="*100)
    print("4️⃣  PATTERN RECOGNITION STRATEGY (AGGRESSIVE 2.618)")
    print("="*100)
    pattern_agg_strategy = MultiSignalPatternStrategy(fib_mode='aggressive')
    df_pattern_agg = pattern_agg_strategy.run_strategy(df.copy())
    pattern_agg_results = backtest_strategy(df_pattern_agg, "Pattern (Agg)")
    if pattern_agg_results:
        analyze_performance(pattern_agg_results, "Pattern Recognition (2.618)")
        results_dict['Pattern (2.618)'] = pattern_agg_results

    # Compare all
    if len(results_dict) > 0:
        compare_all_strategies(results_dict)
        create_comparison_chart(results_dict)

    print("\n✅ Testing complete!")


if __name__ == "__main__":
    main()
