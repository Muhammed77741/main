"""
Compare Multi-Timeframe S/R Retest Strategy vs Original
Test on 2025 data (Jan-Nov)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy
from mtf_sr_retest_strategy import MTF_SR_Retest_Strategy
from intraday_gold_data import generate_intraday_gold_data


def generate_2025_data(months=11):
    """Generate 2025 data"""
    print(f"\n📊 Generating {months} months of 2025 XAUUSD data...")
    total_days = months * 30
    df = generate_intraday_gold_data(days=total_days, timeframe='1H')
    start_date = datetime(2025, 1, 1)
    df.index = pd.date_range(start=start_date, periods=len(df), freq='1h')
    df = df[df.index.dayofweek < 5]
    df = df[(df.index >= '2025-01-01') & (df.index < '2025-12-01')]
    print(f"✅ Generated {len(df)} hourly candles")
    return df


def backtest_strategy(df_strategy, strategy_name):
    """Backtest and collect monthly statistics"""
    trades = []
    monthly_stats = {}

    for i in range(len(df_strategy)):
        if df_strategy['signal'].iloc[i] == 0:
            continue

        current_time = df_strategy.index[i]
        current_month = current_time.strftime('%Y-%m')

        if current_month not in monthly_stats:
            monthly_stats[current_month] = {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0}

        entry_price = df_strategy['entry_price'].iloc[i]
        stop_loss = df_strategy['stop_loss'].iloc[i]
        take_profit = df_strategy['take_profit'].iloc[i]
        direction = df_strategy['signal'].iloc[i]
        signal_type = df_strategy['signal_type'].iloc[i] if 'signal_type' in df_strategy.columns else 'unknown'

        if pd.isna(entry_price) or pd.isna(stop_loss) or pd.isna(take_profit):
            continue

        # Look ahead for exit
        for j in range(i+1, min(i+49, len(df_strategy))):
            exit_price = None
            exit_reason = None

            if direction == 1:
                if df_strategy['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                elif df_strategy['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
            else:
                if df_strategy['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                elif df_strategy['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'

            if exit_price:
                if direction == 1:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100

                trades.append({
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'signal_type': signal_type
                })

                monthly_stats[current_month]['trades'] += 1
                monthly_stats[current_month]['pnl'] += pnl_pct

                if pnl_pct > 0:
                    monthly_stats[current_month]['wins'] += 1
                else:
                    monthly_stats[current_month]['losses'] += 1
                break

    return trades, monthly_stats


def print_results(strategy_name, trades, monthly_stats):
    """Print strategy results"""
    print("\n" + "="*80)
    print(f"📊 {strategy_name.upper()} - RESULTS")
    print("="*80)

    if not trades:
        print("⚠️  No trades generated!")
        return None

    total_trades = len(trades)
    wins = len([t for t in trades if t['pnl_pct'] > 0])
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0
    total_pnl = sum([t['pnl_pct'] for t in trades])
    avg_pnl_trade = total_pnl / total_trades if total_trades > 0 else 0

    avg_win = np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] > 0]) if wins > 0 else 0
    avg_loss = np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] <= 0]) if (total_trades - wins) > 0 else 0

    print(f"\n🎯 Overall Performance:")
    print(f"  Total Trades:      {total_trades}")
    print(f"  Wins:              {wins} / {total_trades}")
    print(f"  Win Rate:          {win_rate:.1f}%")
    print(f"  Total PnL:         {total_pnl:+.2f}%")
    print(f"  Avg PnL/Trade:     {avg_pnl_trade:+.2f}%")
    print(f"  Avg Win:           {avg_win:+.2f}%")
    print(f"  Avg Loss:          {avg_loss:+.2f}%")
    print(f"  Avg Trades/Month:  {total_trades/11:.1f}")

    # Monthly breakdown
    print(f"\n📅 Monthly Performance:")
    profitable_months = 0
    for month in sorted(monthly_stats.keys()):
        stats = monthly_stats[month]
        if stats['pnl'] > 0:
            profitable_months += 1
        wr = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
        print(f"  {month}: {stats['trades']:3d} trades | {wr:5.1f}% WR | {stats['pnl']:+7.2f}%")

    print(f"\n  💰 Profitable Months: {profitable_months}/11 ({profitable_months/11*100:.0f}%)")

    # Signal type breakdown
    signal_types = {}
    for trade in trades:
        st = str(trade['signal_type'])
        if st not in signal_types:
            signal_types[st] = {'count': 0, 'wins': 0, 'pnl': 0}
        signal_types[st]['count'] += 1
        if trade['pnl_pct'] > 0:
            signal_types[st]['wins'] += 1
        signal_types[st]['pnl'] += trade['pnl_pct']

    if signal_types:
        print(f"\n📊 Performance by Signal Type:")
        for st in sorted(signal_types.keys(), key=lambda x: signal_types[x]['pnl'], reverse=True):
            stats = signal_types[st]
            wr = stats['wins'] / stats['count'] * 100 if stats['count'] > 0 else 0
            print(f"  {st:25s}: {stats['count']:3d} trades | {wr:5.1f}% WR | {stats['pnl']:+7.2f}%")

    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl_month': total_pnl / 11,
        'avg_pnl_trade': avg_pnl_trade,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profitable_months': profitable_months
    }


def create_comparison_chart(original_results, mtf_results):
    """Create comparison chart"""
    strategies = ['Original', 'MTF S/R Retest']

    total_pnl = [original_results['total_pnl'], mtf_results['total_pnl']]
    win_rate = [original_results['win_rate'], mtf_results['win_rate']]
    total_trades = [original_results['total_trades'], mtf_results['total_trades']]
    profitable_months = [original_results['profitable_months'], mtf_results['profitable_months']]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    colors = ['#3498db', '#e74c3c']  # Blue, Red

    # Plot 1: Total PnL
    ax1 = axes[0, 0]
    bars = ax1.bar(strategies, total_pnl, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax1.set_title('Total PnL (%) - 11 Months', fontsize=13, fontweight='bold')
    ax1.set_ylabel('PnL (%)', fontsize=11)
    ax1.grid(True, alpha=0.3, axis='y')
    for i, (bar, val) in enumerate(zip(bars, total_pnl)):
        ax1.text(bar.get_x() + bar.get_width()/2, val, f'{val:+.1f}%',
                ha='center', va='bottom' if val > 0 else 'top', fontweight='bold', fontsize=11)

    # Plot 2: Win Rate
    ax2 = axes[0, 1]
    bars = ax2.bar(strategies, win_rate, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax2.axhline(y=50, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='50%')
    ax2.set_title('Win Rate (%)', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Win Rate (%)', fontsize=11)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.legend()
    for i, (bar, val) in enumerate(zip(bars, win_rate)):
        ax2.text(bar.get_x() + bar.get_width()/2, val, f'{val:.1f}%',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Plot 3: Total Trades
    ax3 = axes[1, 0]
    bars = ax3.bar(strategies, total_trades, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax3.set_title('Total Trades - 11 Months', fontsize=13, fontweight='bold')
    ax3.set_ylabel('Number of Trades', fontsize=11)
    ax3.grid(True, alpha=0.3, axis='y')
    for i, (bar, val) in enumerate(zip(bars, total_trades)):
        ax3.text(bar.get_x() + bar.get_width()/2, val, str(val),
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Plot 4: Profitable Months
    ax4 = axes[1, 1]
    bars = ax4.bar(strategies, profitable_months, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax4.axhline(y=11, color='green', linestyle='--', linewidth=1.5, alpha=0.5, label='11/11')
    ax4.set_title('Profitable Months (out of 11)', fontsize=13, fontweight='bold')
    ax4.set_ylabel('Profitable Months', fontsize=11)
    ax4.set_ylim(0, 12)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.legend()
    for i, (bar, val) in enumerate(zip(bars, profitable_months)):
        ax4.text(bar.get_x() + bar.get_width()/2, val, f'{val}/11\n({val/11*100:.0f}%)',
                ha='center', va='bottom', fontweight='bold', fontsize=10)

    plt.suptitle('MTF S/R Retest vs Original - Comparison', fontsize=15, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig('mtf_vs_original_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 Chart saved: mtf_vs_original_comparison.png")


def compare_strategies(original_results, mtf_results):
    """Compare and determine winner"""
    print("\n" + "="*90)
    print("⚔️  MTF S/R RETEST vs ORIGINAL - DETAILED COMPARISON")
    print("="*90)

    print(f"\n{'METRIC':<25} {'Original':<20} {'MTF S/R Retest':<20} {'Winner':<20}")
    print("-"*90)

    # Total PnL
    winner = 'Original' if original_results['total_pnl'] > mtf_results['total_pnl'] else 'MTF S/R'
    print(f"{'Total PnL (%)':<25} {original_results['total_pnl']:<+20.2f} {mtf_results['total_pnl']:<+20.2f} {winner:<20}")

    # Win Rate
    winner = 'Original' if original_results['win_rate'] > mtf_results['win_rate'] else 'MTF S/R'
    print(f"{'Win Rate (%)':<25} {original_results['win_rate']:<20.1f} {mtf_results['win_rate']:<20.1f} {winner:<20}")

    # Total Trades
    winner = 'Original' if original_results['total_trades'] > mtf_results['total_trades'] else 'MTF S/R'
    print(f"{'Total Trades':<25} {original_results['total_trades']:<20} {mtf_results['total_trades']:<20} {winner:<20}")

    # Avg PnL/Trade
    winner = 'Original' if original_results['avg_pnl_trade'] > mtf_results['avg_pnl_trade'] else 'MTF S/R'
    print(f"{'Avg PnL/Trade (%)':<25} {original_results['avg_pnl_trade']:<+20.2f} {mtf_results['avg_pnl_trade']:<+20.2f} {winner:<20}")

    # Avg Win
    winner = 'Original' if original_results['avg_win'] > mtf_results['avg_win'] else 'MTF S/R'
    print(f"{'Avg Win (%)':<25} {original_results['avg_win']:<+20.2f} {mtf_results['avg_win']:<+20.2f} {winner:<20}")

    # Avg Loss
    winner = 'Original' if original_results['avg_loss'] > mtf_results['avg_loss'] else 'MTF S/R'  # Less negative is better
    print(f"{'Avg Loss (%)':<25} {original_results['avg_loss']:<+20.2f} {mtf_results['avg_loss']:<+20.2f} {winner:<20}")

    # Profitable Months
    winner = 'Original' if original_results['profitable_months'] > mtf_results['profitable_months'] else 'MTF S/R'
    print(f"{'Profitable Months':<25} {original_results['profitable_months']:<20} {mtf_results['profitable_months']:<20} {winner:<20}")

    # Overall winner
    print("\n" + "="*90)
    print("🏆 OVERALL WINNER")
    print("="*90)

    orig_score = 0
    mtf_score = 0

    if original_results['total_pnl'] > mtf_results['total_pnl']:
        orig_score += 3
    else:
        mtf_score += 3

    if original_results['win_rate'] > mtf_results['win_rate']:
        orig_score += 2
    else:
        mtf_score += 2

    if original_results['profitable_months'] > mtf_results['profitable_months']:
        orig_score += 1
    else:
        mtf_score += 1

    if original_results['avg_pnl_trade'] > mtf_results['avg_pnl_trade']:
        orig_score += 1
    else:
        mtf_score += 1

    print(f"\nScoring (0-7 points):")
    print(f"  Original:      {orig_score} points")
    print(f"  MTF S/R Retest: {mtf_score} points")

    if orig_score > mtf_score:
        print(f"\n🥇 WINNER: ORIGINAL MULTI-SIGNAL")
        print(f"\n   Original maintains its dominance!")
        print(f"   Advantages:")
        print(f"   ✅ {abs(original_results['total_pnl'] - mtf_results['total_pnl']):.2f}% more profit")
        print(f"   ✅ {abs(original_results['total_trades'] - mtf_results['total_trades'])} more trades")
    else:
        print(f"\n🥇 WINNER: MTF S/R RETEST")
        print(f"\n   New strategy proves superior!")
        print(f"   Advantages:")
        print(f"   ✅ Multi-timeframe confirmation")
        print(f"   ✅ Professional S/R zone approach")


def main():
    """Main test function"""
    print("\n" + "="*80)
    print("🚀 MTF S/R RETEST vs ORIGINAL - 2025 Analysis (Jan-Nov)")
    print("="*80)

    # Generate data
    df = generate_2025_data(months=11)

    # Test Original
    print("\n" + "="*80)
    print("1️⃣  ORIGINAL MULTI-SIGNAL STRATEGY")
    print("="*80)
    strategy_original = MultiSignalGoldStrategy()
    df_original = strategy_original.run_strategy(df.copy())
    trades_original, monthly_original = backtest_strategy(df_original, "Original")
    original_results = print_results("Original Multi-Signal", trades_original, monthly_original)

    # Test MTF S/R Retest
    print("\n" + "="*80)
    print("2️⃣  MULTI-TIMEFRAME S/R RETEST STRATEGY")
    print("="*80)
    strategy_mtf = MTF_SR_Retest_Strategy()
    df_mtf = strategy_mtf.run_strategy(df.copy())
    trades_mtf, monthly_mtf = backtest_strategy(df_mtf, "MTF S/R")
    mtf_results = print_results("MTF S/R Retest", trades_mtf, monthly_mtf)

    # Compare
    if original_results and mtf_results:
        create_comparison_chart(original_results, mtf_results)
        compare_strategies(original_results, mtf_results)
    else:
        print("\n⚠️  Cannot compare - one or both strategies generated no trades")

    print("\n✅ Testing complete!\n")


if __name__ == '__main__':
    main()
