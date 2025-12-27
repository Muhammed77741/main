"""
Test New Strategies on 2025 Data
1. Candlestick Patterns Strategy
2. Improved Original Strategy
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from candlestick_patterns_strategy import CandlestickPatternsStrategy
from improved_original_strategy import ImprovedOriginalStrategy
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
    """
    Backtest and collect monthly statistics
    """
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

                trades.append({'pnl_pct': pnl_pct, 'exit_reason': exit_reason})

                monthly_stats[current_month]['trades'] += 1
                monthly_stats[current_month]['pnl'] += pnl_pct

                if pnl_pct > 0:
                    monthly_stats[current_month]['wins'] += 1
                else:
                    monthly_stats[current_month]['losses'] += 1
                break

    return trades, monthly_stats


def print_results(strategy_name, trades, monthly_stats):
    """
    Print strategy results
    """
    print("\n" + "="*80)
    print(f"📊 {strategy_name.upper()} - RESULTS")
    print("="*80)

    if not trades:
        print("⚠️  No trades generated!")
        return

    total_trades = len(trades)
    wins = len([t for t in trades if t['pnl_pct'] > 0])
    losses = total_trades - wins
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0
    total_pnl = sum([t['pnl_pct'] for t in trades])

    print(f"\nOverall Performance:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Wins: {wins} | Losses: {losses}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Total PnL: {total_pnl:+.2f}%")
    print(f"  Avg PnL per Trade: {total_pnl/total_trades:+.2f}%")
    print(f"  Avg Trades per Month: {total_trades/11:.1f}")

    # Monthly breakdown
    print(f"\n📅 Monthly Breakdown:")
    profitable_months = 0
    for month in sorted(monthly_stats.keys()):
        stats = monthly_stats[month]
        if stats['pnl'] > 0:
            profitable_months += 1
        wr = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
        print(f"  {month}: {stats['trades']:3d} trades | WR: {wr:5.1f}% | PnL: {stats['pnl']:+7.2f}%")

    print(f"\n  Profitable Months: {profitable_months}/11 ({profitable_months/11*100:.0f}%)")

    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl_month': total_pnl / 11,
        'profitable_months': profitable_months
    }


def compare_all_strategies(candlestick_results, improved_results, original_results):
    """
    Compare all three strategies
    """
    print("\n" + "="*90)
    print("⚔️  STRATEGY COMPARISON - Candlestick vs Improved vs Original")
    print("="*90)

    print(f"\n{'METRIC':<30} {'Candlestick':<20} {'Improved':<20} {'Original':<20}")
    print("-"*90)

    print(f"{'Total Trades':<30} {candlestick_results['total_trades']:<20} {improved_results['total_trades']:<20} {original_results['total_trades']:<20}")
    print(f"{'Win Rate (%)':<30} {candlestick_results['win_rate']:<20.1f} {improved_results['win_rate']:<20.1f} {original_results['win_rate']:<20.1f}")
    print(f"{'Total PnL (%)':<30} {candlestick_results['total_pnl']:<+20.2f} {improved_results['total_pnl']:<+20.2f} {original_results['total_pnl']:<+20.2f}")
    print(f"{'Avg PnL/Month (%)':<30} {candlestick_results['avg_pnl_month']:<+20.2f} {improved_results['avg_pnl_month']:<+20.2f} {original_results['avg_pnl_month']:<+20.2f}")
    print(f"{'Profitable Months':<30} {candlestick_results['profitable_months']:<20} {improved_results['profitable_months']:<20} {original_results['profitable_months']:<20}")

    # Determine winner
    print("\n" + "="*90)
    print("🏆 WINNER DETERMINATION")
    print("="*90)

    scores = {
        'Candlestick': 0,
        'Improved': 0,
        'Original': 0
    }

    # Score by total PnL (most important)
    pnls = {
        'Candlestick': candlestick_results['total_pnl'],
        'Improved': improved_results['total_pnl'],
        'Original': original_results['total_pnl']
    }
    winner = max(pnls, key=pnls.get)
    scores[winner] += 3

    # Score by win rate
    wrs = {
        'Candlestick': candlestick_results['win_rate'],
        'Improved': improved_results['win_rate'],
        'Original': original_results['win_rate']
    }
    winner = max(wrs, key=wrs.get)
    scores[winner] += 2

    # Score by profitable months
    pms = {
        'Candlestick': candlestick_results['profitable_months'],
        'Improved': improved_results['profitable_months'],
        'Original': original_results['profitable_months']
    }
    winner = max(pms, key=pms.get)
    scores[winner] += 1

    print(f"\nFinal Scores:")
    for strategy, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        print(f"  {strategy:15s}: {score} points")

    winner = max(scores, key=scores.get)
    print(f"\n🥇 WINNER: {winner}")

    if winner == 'Improved':
        print(f"\n   Improvements worked! Filtered out weak signals and increased quality.")
    elif winner == 'Candlestick':
        print(f"\n   Classic patterns prove their worth!")
    else:
        print(f"\n   Original strategy still the best - simpler is better!")


def main():
    """
    Main test function
    """
    print("\n" + "="*80)
    print("🚀 TESTING NEW STRATEGIES - 2025 Analysis (Jan-Nov)")
    print("="*80)

    # Generate data
    df = generate_2025_data(months=11)

    # Test Candlestick Patterns Strategy
    print("\n" + "="*80)
    print("1️⃣  CANDLESTICK PATTERNS STRATEGY")
    print("="*80)

    candlestick_strategy = CandlestickPatternsStrategy()
    df_candlestick = candlestick_strategy.run_strategy(df.copy())
    trades_candlestick, monthly_candlestick = backtest_strategy(df_candlestick, "Candlestick")
    candlestick_results = print_results("Candlestick Patterns", trades_candlestick, monthly_candlestick)

    # Test Improved Original Strategy
    print("\n" + "="*80)
    print("2️⃣  IMPROVED ORIGINAL STRATEGY")
    print("="*80)

    improved_strategy = ImprovedOriginalStrategy()
    df_improved = improved_strategy.run_strategy(df.copy())
    trades_improved, monthly_improved = backtest_strategy(df_improved, "Improved")
    improved_results = print_results("Improved Original", trades_improved, monthly_improved)

    # Original results (from previous test)
    original_results = {
        'total_trades': 417,
        'win_rate': 66.4,
        'total_pnl': 44.20,
        'avg_pnl_month': 4.02,
        'profitable_months': 10
    }

    # Compare all
    compare_all_strategies(candlestick_results, improved_results, original_results)

    print("\n✅ Testing complete!\n")


if __name__ == '__main__':
    main()
