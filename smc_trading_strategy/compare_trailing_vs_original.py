"""
Compare Trailing SL vs Original Strategy
Side-by-side comparison on 2025 data
"""

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def create_comparison_table():
    """
    Create comprehensive comparison table
    """

    print("\n" + "="*90)
    print("⚔️  TRAILING SL vs ORIGINAL STRATEGY - FULL COMPARISON (Jan-Nov 2025)")
    print("="*90)

    # Results from previous tests
    trailing_sl = {
        'total_trades': 94,
        'win_rate': 60.6,
        'total_pnl': 19.24,
        'avg_pnl_month': 1.75,
        'avg_trades_month': 8.5,
        'avg_pnl_trade': 0.20,
        'tp1_hits_pct': 60.0,
        'tp2_hits_pct': 36.0,
        'tp3_hits_pct': 31.0,
        'best_month': 'Jun (+9.8%)',
        'worst_month': 'Feb (-2.1%)',
        'profitable_months': 7,
        'losing_months': 4
    }

    original = {
        'total_trades': 417,
        'win_rate': 66.4,
        'total_pnl': 44.20,
        'avg_pnl_month': 4.02,
        'avg_trades_month': 37.9,
        'avg_pnl_trade': 0.11,
        'avg_win': 0.43,
        'avg_loss': -0.53,
        'profit_factor': 0.81,
        'best_month': 'Jan (+10.6%)',
        'worst_month': 'Mar (-1.0%)',
        'profitable_months': 10,
        'losing_months': 1
    }

    # Main comparison
    print(f"\n{'METRIC':<30} {'TRAILING SL':<20} {'ORIGINAL':<20} {'WINNER':<15}")
    print("-"*90)

    # Total trades
    winner = '← ORIGINAL' if original['total_trades'] > trailing_sl['total_trades'] else 'TRAILING SL →'
    print(f"{'Total Trades':<30} {trailing_sl['total_trades']:<20} {original['total_trades']:<20} {winner:<15}")

    # Win rate
    winner = '← ORIGINAL' if original['win_rate'] > trailing_sl['win_rate'] else 'TRAILING SL →'
    print(f"{'Win Rate':<30} {trailing_sl['win_rate']:<20.1f} {original['win_rate']:<20.1f} {winner:<15}")

    # Total PnL (most important!)
    winner = '← ORIGINAL' if original['total_pnl'] > trailing_sl['total_pnl'] else 'TRAILING SL →'
    print(f"{'Total PnL (%)':<30} {trailing_sl['total_pnl']:<+20.2f} {original['total_pnl']:<+20.2f} {winner:<15}")

    # Avg PnL per month
    winner = '← ORIGINAL' if original['avg_pnl_month'] > trailing_sl['avg_pnl_month'] else 'TRAILING SL →'
    print(f"{'Avg PnL per Month (%)':<30} {trailing_sl['avg_pnl_month']:<+20.2f} {original['avg_pnl_month']:<+20.2f} {winner:<15}")

    # Avg trades per month
    winner = '← ORIGINAL' if original['avg_trades_month'] > trailing_sl['avg_trades_month'] else 'TRAILING SL →'
    print(f"{'Avg Trades per Month':<30} {trailing_sl['avg_trades_month']:<20.1f} {original['avg_trades_month']:<20.1f} {winner:<15}")

    # Avg PnL per trade
    winner = '← ORIGINAL' if original['avg_pnl_trade'] > trailing_sl['avg_pnl_trade'] else 'TRAILING SL →'
    print(f"{'Avg PnL per Trade (%)':<30} {trailing_sl['avg_pnl_trade']:<+20.2f} {original['avg_pnl_trade']:<+20.2f} {winner:<15}")

    # Best month
    print(f"{'Best Month':<30} {trailing_sl['best_month']:<20} {original['best_month']:<20}")

    # Worst month
    print(f"{'Worst Month':<30} {trailing_sl['worst_month']:<20} {original['worst_month']:<20}")

    # Profitable months
    winner = '← ORIGINAL' if original['profitable_months'] > trailing_sl['profitable_months'] else 'TRAILING SL →'
    print(f"{'Profitable Months':<30} {trailing_sl['profitable_months']:<20} {original['profitable_months']:<20} {winner:<15}")

    print("\n" + "="*90)
    print("🏆 FINAL VERDICT")
    print("="*90)

    # Calculate scores
    trailing_score = 0
    original_score = 0

    # Scoring criteria (most important first)
    if original['total_pnl'] > trailing_sl['total_pnl']:
        original_score += 3  # Most important
    else:
        trailing_score += 3

    if original['avg_pnl_month'] > trailing_sl['avg_pnl_month']:
        original_score += 2
    else:
        trailing_score += 2

    if original['win_rate'] > trailing_sl['win_rate']:
        original_score += 2
    else:
        trailing_score += 2

    if original['profitable_months'] > trailing_sl['profitable_months']:
        original_score += 1
    else:
        trailing_score += 1

    if original['total_trades'] > trailing_sl['total_trades']:
        original_score += 1  # More opportunities
    else:
        trailing_score += 1

    print(f"\nScoring (0-9 points):")
    print(f"  TRAILING SL: {trailing_score} points")
    print(f"  ORIGINAL:    {original_score} points")

    if original_score > trailing_score:
        print(f"\n🥇 WINNER: ORIGINAL STRATEGY")
        print(f"\n   Key advantages:")
        print(f"   ✅ {original['total_pnl'] - trailing_sl['total_pnl']:+.2f}% more profit (+130% relative)")
        print(f"   ✅ {original['win_rate'] - trailing_sl['win_rate']:+.1f}% higher win rate")
        print(f"   ✅ {original['total_trades'] - trailing_sl['total_trades']} more trades (+344% more opportunities)")
        print(f"   ✅ {original['profitable_months']} out of 11 months profitable (vs {trailing_sl['profitable_months']})")
    else:
        print(f"\n🥇 WINNER: TRAILING SL STRATEGY")
        print(f"\n   Key advantages:")
        print(f"   ✅ Better risk management (SL to breakeven)")
        print(f"   ✅ Partial profit taking reduces drawdown")
        print(f"   ✅ Guaranteed profit after TP1")

    print("\n" + "="*90)
    print("💡 KEY INSIGHTS")
    print("="*90)

    print("\nTrailing SL Issues:")
    print("  ❌ Too few trades (94 vs 417) - missing 77% of opportunities")
    print("  ❌ Lower win rate (60.6% vs 66.4%)")
    print("  ❌ Less profit (+19.24% vs +44.20%)")
    print("  ❌ Moving SL to breakeven cuts winning trades short")
    print("  ❌ Multi-TP structure complicates execution")

    print("\nOriginal Strategy Strengths:")
    print("  ✅ Simple: Single TP @ 1.8R, single SL")
    print("  ✅ More trades = more opportunities (37.9/month vs 8.5/month)")
    print("  ✅ Higher win rate = more consistent")
    print("  ✅ Better monthly returns (+4.02% vs +1.75%)")
    print("  ✅ Only 1 losing month out of 11!")

    print("\n" + "="*90)
    print("📋 RECOMMENDATION")
    print("="*90)
    print("\n🎯 USE ORIGINAL STRATEGY (No Trailing SL)")
    print("\nReasons:")
    print("  1. 130% more profit over 11 months")
    print("  2. 4x more trading opportunities")
    print("  3. 91% month profitability (10/11 months)")
    print("  4. Simpler to execute (no partial exits)")
    print("  5. Proven consistency across diverse market conditions")

    print("\n⚠️  Trailing SL works better in theory than practice")
    print("   Moving SL to breakeven too early cuts profits on strong moves")
    print("   The original 1.8R target already provides good risk/reward")

    print("\n" + "="*90)


def create_comparison_chart():
    """
    Create visual comparison chart
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    strategies = ['Trailing SL', 'Original']

    # Data
    total_pnl = [19.24, 44.20]
    win_rate = [60.6, 66.4]
    total_trades = [94, 417]
    avg_pnl_month = [1.75, 4.02]

    colors = ['#FF6B6B', '#4ECDC4']

    # Plot 1: Total PnL
    axes[0, 0].bar(strategies, total_pnl, color=colors, alpha=0.7, edgecolor='black')
    axes[0, 0].set_title('Total PnL (%) - 11 Months', fontsize=12, fontweight='bold')
    axes[0, 0].set_ylabel('PnL (%)')
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(total_pnl):
        axes[0, 0].text(i, v, f'{v:+.2f}%', ha='center', va='bottom', fontweight='bold')

    # Plot 2: Win Rate
    axes[0, 1].bar(strategies, win_rate, color=colors, alpha=0.7, edgecolor='black')
    axes[0, 1].axhline(y=50, color='red', linestyle='--', linewidth=1, alpha=0.5)
    axes[0, 1].set_title('Win Rate (%)', fontsize=12, fontweight='bold')
    axes[0, 1].set_ylabel('Win Rate (%)')
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(win_rate):
        axes[0, 1].text(i, v, f'{v:.1f}%', ha='center', va='bottom', fontweight='bold')

    # Plot 3: Total Trades
    axes[1, 0].bar(strategies, total_trades, color=colors, alpha=0.7, edgecolor='black')
    axes[1, 0].set_title('Total Trades - 11 Months', fontsize=12, fontweight='bold')
    axes[1, 0].set_ylabel('Number of Trades')
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(total_trades):
        axes[1, 0].text(i, v, str(v), ha='center', va='bottom', fontweight='bold')

    # Plot 4: Avg Monthly PnL
    axes[1, 1].bar(strategies, avg_pnl_month, color=colors, alpha=0.7, edgecolor='black')
    axes[1, 1].set_title('Avg Monthly PnL (%)', fontsize=12, fontweight='bold')
    axes[1, 1].set_ylabel('PnL (%)')
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(avg_pnl_month):
        axes[1, 1].text(i, v, f'{v:+.2f}%', ha='center', va='bottom', fontweight='bold')

    plt.suptitle('Trailing SL vs Original Strategy - Comparison', fontsize=14, fontweight='bold', y=1.00)
    plt.tight_layout()
    plt.savefig('trailing_vs_original_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 Comparison chart saved: trailing_vs_original_comparison.png")

    return fig


def main():
    """
    Main comparison function
    """
    create_comparison_table()
    create_comparison_chart()

    print("\n✅ Comparison complete!\n")


if __name__ == '__main__':
    main()
