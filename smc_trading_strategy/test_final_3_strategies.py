"""
Test Final 3 Strategies - The Best of the Best
1. Original Multi-Signal (baseline winner)
2. Improved Original (with filters)
3. SMC + ICT + Price Action (advanced combined)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy
from improved_original_strategy import ImprovedOriginalStrategy
from smc_ict_pa_strategy import SMC_ICT_PA_Strategy
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

        if pd.isna(entry_price) or pd.isna(stop_loss) or pd.isna(take_profit):
            continue

        # Look ahead for exit
        for j in range(i+1, min(i+49, len(df_strategy))):
            exit_price = None

            if direction == 1:
                if df_strategy['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                elif df_strategy['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
            else:
                if df_strategy['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                elif df_strategy['low'].iloc[j] <= take_profit:
                    exit_price = take_profit

            if exit_price:
                if direction == 1:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100

                trades.append({'pnl_pct': pnl_pct})
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

    print(f"\n🎯 Overall Performance:")
    print(f"  Total Trades:      {total_trades}")
    print(f"  Wins:              {wins} / {total_trades}")
    print(f"  Win Rate:          {win_rate:.1f}%")
    print(f"  Total PnL:         {total_pnl:+.2f}%")
    print(f"  Avg PnL/Trade:     {avg_pnl_trade:+.2f}%")
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

    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl_month': total_pnl / 11,
        'avg_pnl_trade': avg_pnl_trade,
        'profitable_months': profitable_months
    }


def create_comparison_chart(results):
    """Create visual comparison of all 3 strategies"""
    strategies = list(results.keys())

    total_pnl = [results[s]['total_pnl'] for s in strategies]
    win_rate = [results[s]['win_rate'] for s in strategies]
    total_trades = [results[s]['total_trades'] for s in strategies]
    avg_pnl_month = [results[s]['avg_pnl_month'] for s in strategies]
    profitable_months = [results[s]['profitable_months'] for s in strategies]

    # Color scheme
    colors = ['#3498db', '#2ecc71', '#e74c3c']  # Blue, Green, Red

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # Plot 1: Total PnL
    ax1 = fig.add_subplot(gs[0, 0])
    bars1 = ax1.bar(strategies, total_pnl, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax1.set_title('Total PnL (%) - 11 Months', fontsize=13, fontweight='bold')
    ax1.set_ylabel('PnL (%)', fontsize=11)
    ax1.grid(True, alpha=0.3, axis='y')
    for i, (bar, val) in enumerate(zip(bars1, total_pnl)):
        ax1.text(bar.get_x() + bar.get_width()/2, val, f'{val:+.1f}%',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Plot 2: Win Rate
    ax2 = fig.add_subplot(gs[0, 1])
    bars2 = ax2.bar(strategies, win_rate, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax2.axhline(y=50, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='50% threshold')
    ax2.set_title('Win Rate (%)', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Win Rate (%)', fontsize=11)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.legend()
    for i, (bar, val) in enumerate(zip(bars2, win_rate)):
        ax2.text(bar.get_x() + bar.get_width()/2, val, f'{val:.1f}%',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Plot 3: Total Trades
    ax3 = fig.add_subplot(gs[1, 0])
    bars3 = ax3.bar(strategies, total_trades, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax3.set_title('Total Trades - 11 Months', fontsize=13, fontweight='bold')
    ax3.set_ylabel('Number of Trades', fontsize=11)
    ax3.grid(True, alpha=0.3, axis='y')
    for i, (bar, val) in enumerate(zip(bars3, total_trades)):
        ax3.text(bar.get_x() + bar.get_width()/2, val, str(val),
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Plot 4: Avg Monthly PnL
    ax4 = fig.add_subplot(gs[1, 1])
    bars4 = ax4.bar(strategies, avg_pnl_month, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax4.set_title('Avg Monthly PnL (%)', fontsize=13, fontweight='bold')
    ax4.set_ylabel('PnL (%)', fontsize=11)
    ax4.grid(True, alpha=0.3, axis='y')
    for i, (bar, val) in enumerate(zip(bars4, avg_pnl_month)):
        ax4.text(bar.get_x() + bar.get_width()/2, val, f'{val:+.2f}%',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Plot 5: Profitable Months
    ax5 = fig.add_subplot(gs[2, :])
    bars5 = ax5.bar(strategies, profitable_months, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax5.axhline(y=11, color='green', linestyle='--', linewidth=1.5, alpha=0.5, label='11/11 (perfect)')
    ax5.set_title('Profitable Months (out of 11)', fontsize=13, fontweight='bold')
    ax5.set_ylabel('Number of Profitable Months', fontsize=11)
    ax5.set_ylim(0, 12)
    ax5.grid(True, alpha=0.3, axis='y')
    ax5.legend()
    for i, (bar, val) in enumerate(zip(bars5, profitable_months)):
        ax5.text(bar.get_x() + bar.get_width()/2, val, f'{val}/11\n({val/11*100:.0f}%)',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    plt.suptitle('Final 3 Strategies Comparison - 2025 Performance',
                fontsize=15, fontweight='bold', y=0.995)

    plt.savefig('final_3_strategies_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 Chart saved: final_3_strategies_comparison.png")


def determine_winner(results):
    """Determine overall winner with detailed scoring"""
    print("\n" + "="*90)
    print("🏆 FINAL RANKING & WINNER DETERMINATION")
    print("="*90)

    strategies = list(results.keys())
    scores = {s: 0 for s in strategies}

    # Scoring criteria (weighted by importance)
    print("\n📊 Scoring Breakdown:")

    # 1. Total PnL (40% weight - most important)
    print("\n1️⃣ Total PnL (4 points to winner):")
    pnl_winner = max(strategies, key=lambda s: results[s]['total_pnl'])
    scores[pnl_winner] += 4
    for s in strategies:
        marker = "🏆" if s == pnl_winner else "  "
        print(f"  {marker} {s:20s}: {results[s]['total_pnl']:+7.2f}%")

    # 2. Win Rate (25% weight)
    print("\n2️⃣ Win Rate (3 points to winner):")
    wr_winner = max(strategies, key=lambda s: results[s]['win_rate'])
    scores[wr_winner] += 3
    for s in strategies:
        marker = "🏆" if s == wr_winner else "  "
        print(f"  {marker} {s:20s}: {results[s]['win_rate']:6.1f}%")

    # 3. Profitable Months (20% weight)
    print("\n3️⃣ Profitable Months (2 points to winner):")
    pm_winner = max(strategies, key=lambda s: results[s]['profitable_months'])
    scores[pm_winner] += 2
    for s in strategies:
        marker = "🏆" if s == pm_winner else "  "
        pm = results[s]['profitable_months']
        print(f"  {marker} {s:20s}: {pm}/11 ({pm/11*100:.0f}%)")

    # 4. Avg PnL per Trade (15% weight)
    print("\n4️⃣ Avg PnL per Trade (1 point to winner):")
    apt_winner = max(strategies, key=lambda s: results[s]['avg_pnl_trade'])
    scores[apt_winner] += 1
    for s in strategies:
        marker = "🏆" if s == apt_winner else "  "
        print(f"  {marker} {s:20s}: {results[s]['avg_pnl_trade']:+.3f}%")

    # Final scores
    print("\n" + "="*90)
    print("📋 FINAL SCORES (out of 10 points):")
    print("="*90)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    for i, (strategy, score) in enumerate(ranked, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else "  "
        bar = "█" * score + "░" * (10 - score)
        print(f"\n{medal} #{i} - {strategy}")
        print(f"    Score: {score}/10  [{bar}]")
        print(f"    PnL: {results[strategy]['total_pnl']:+.2f}% | WR: {results[strategy]['win_rate']:.1f}% | Trades: {results[strategy]['total_trades']}")

    # Declare winner
    winner = ranked[0][0]
    print("\n" + "="*90)
    print(f"🎉 CHAMPION: {winner.upper()}")
    print("="*90)

    # Winner analysis
    w = results[winner]
    print(f"\n✨ Champion Statistics:")
    print(f"   Total Return:     {w['total_pnl']:+.2f}%")
    print(f"   Monthly Return:   {w['avg_pnl_month']:+.2f}%")
    print(f"   Win Rate:         {w['win_rate']:.1f}%")
    print(f"   Total Trades:     {w['total_trades']}")
    print(f"   Profitable Months: {w['profitable_months']}/11 ({w['profitable_months']/11*100:.0f}%)")
    print(f"   Avg PnL/Trade:    {w['avg_pnl_trade']:+.3f}%")


def main():
    """Main test function"""
    print("\n" + "="*80)
    print("🚀 FINAL 3 STRATEGIES COMPARISON - 2025 Analysis (Jan-Nov)")
    print("="*80)
    print("\nTesting the best strategies:")
    print("  1️⃣  Original Multi-Signal (baseline winner)")
    print("  2️⃣  Improved Original (with smart filters)")
    print("  3️⃣  SMC + ICT + Price Action (advanced combined)")

    # Generate data
    df = generate_2025_data(months=11)

    results = {}

    # Test Strategy 1: Original
    print("\n" + "="*80)
    print("1️⃣  ORIGINAL MULTI-SIGNAL STRATEGY")
    print("="*80)
    strategy1 = MultiSignalGoldStrategy()
    df1 = strategy1.run_strategy(df.copy())
    trades1, monthly1 = backtest_strategy(df1, "Original")
    results['Original'] = print_results("Original Multi-Signal", trades1, monthly1)

    # Test Strategy 2: Improved
    print("\n" + "="*80)
    print("2️⃣  IMPROVED ORIGINAL STRATEGY")
    print("="*80)
    strategy2 = ImprovedOriginalStrategy()
    df2 = strategy2.run_strategy(df.copy())
    trades2, monthly2 = backtest_strategy(df2, "Improved")
    results['Improved'] = print_results("Improved Original", trades2, monthly2)

    # Test Strategy 3: SMC+ICT+PA
    print("\n" + "="*80)
    print("3️⃣  SMC + ICT + PRICE ACTION STRATEGY")
    print("="*80)
    strategy3 = SMC_ICT_PA_Strategy()
    df3 = strategy3.run_strategy(df.copy())
    trades3, monthly3 = backtest_strategy(df3, "SMC+ICT+PA")
    results['SMC+ICT+PA'] = print_results("SMC + ICT + PA", trades3, monthly3)

    # Remove None results
    results = {k: v for k, v in results.items() if v is not None}

    # Create comparison chart
    create_comparison_chart(results)

    # Determine winner
    determine_winner(results)

    print("\n✅ Testing complete!\n")


if __name__ == '__main__':
    main()
