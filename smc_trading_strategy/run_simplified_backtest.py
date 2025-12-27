"""
Test Simplified SMC Strategy
Pure SMC + Volume Analysis (без MA и HTF фильтров)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simplified_smc_strategy import SimplifiedSMCStrategy
from smc_strategy import SMCStrategy
from backtester import Backtester
from data_loader import generate_sample_data, validate_data


def plot_simplified_results(df: pd.DataFrame, equity_curve: list, trades: list):
    """Plot results for simplified strategy"""
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

    # Plot 1: Price with signals
    ax1 = fig.add_subplot(gs[0:2, :])
    ax1.plot(df.index, df['close'], label='Close', color='black', linewidth=1, alpha=0.8)

    # Plot Order Blocks
    bullish_ob = df[df['bullish_ob']]
    ax1.scatter(bullish_ob.index, bullish_ob['low'], color='lightgreen', marker='s',
               s=100, alpha=0.6, label='Bullish OB', edgecolors='green', linewidths=1)

    bearish_ob = df[df['bearish_ob']]
    ax1.scatter(bearish_ob.index, bearish_ob['high'], color='lightcoral', marker='s',
               s=100, alpha=0.6, label='Bearish OB', edgecolors='red', linewidths=1)

    # Plot signals
    buy_signals = df[df['signal'] == 1]
    sell_signals = df[df['signal'] == -1]

    ax1.scatter(buy_signals.index, buy_signals['entry_price'], color='green',
               marker='^', s=200, label='BUY', zorder=5, edgecolors='darkgreen', linewidths=2)
    ax1.scatter(sell_signals.index, sell_signals['entry_price'], color='red',
               marker='v', s=200, label='SELL', zorder=5, edgecolors='darkred', linewidths=2)

    # Add signal reasons as annotations
    for idx in buy_signals.index:
        reason = buy_signals.loc[idx, 'signal_reason']
        quality = buy_signals.loc[idx, 'candle_quality']
        ax1.annotate(f'{quality:.0f}', xy=(idx, buy_signals.loc[idx, 'entry_price']),
                    xytext=(0, 20), textcoords='offset points', fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7))

    for idx in sell_signals.index:
        reason = sell_signals.loc[idx, 'signal_reason']
        quality = sell_signals.loc[idx, 'candle_quality']
        ax1.annotate(f'{quality:.0f}', xy=(idx, sell_signals.loc[idx, 'entry_price']),
                    xytext=(0, -20), textcoords='offset points', fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='lightcoral', alpha=0.7))

    ax1.set_title('Simplified SMC Strategy - Pure SMC + Volume', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Volume
    ax2 = fig.add_subplot(gs[2, :])
    colors = ['green' if c > o else 'red' for c, o in zip(df['close'], df['open'])]
    ax2.bar(df.index, df['volume'], color=colors, alpha=0.5, width=0.8)
    ax2.plot(df.index, df['volume_ma'], color='blue', linewidth=2, label='Volume MA')

    # Highlight high volume candles
    high_vol = df[df['high_volume']]
    ax2.scatter(high_vol.index, high_vol['volume'], color='orange', s=50,
               marker='o', label='High Volume', zorder=5)

    ax2.set_title('Volume Analysis', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Volume')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    # Plot 3: Equity Curve
    ax3 = fig.add_subplot(gs[3, 0])
    ax3.plot(equity_curve, color='blue', linewidth=2, label='Equity')
    ax3.axhline(y=equity_curve[0], color='gray', linestyle='--', alpha=0.5, label='Initial')
    ax3.fill_between(range(len(equity_curve)), equity_curve[0], equity_curve,
                     where=[e >= equity_curve[0] for e in equity_curve],
                     alpha=0.3, color='green', label='Profit')
    ax3.fill_between(range(len(equity_curve)), equity_curve[0], equity_curve,
                     where=[e < equity_curve[0] for e in equity_curve],
                     alpha=0.3, color='red', label='Loss')
    ax3.set_title('Equity Curve', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Bar')
    ax3.set_ylabel('Equity ($)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: Trade PnL
    ax4 = fig.add_subplot(gs[3, 1])
    if trades:
        trade_pnls = [t['pnl'] for t in trades]
        colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnls]
        ax4.bar(range(len(trade_pnls)), trade_pnls, color=colors, alpha=0.6, edgecolor='black')
        ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

        # Add cumulative PnL line
        cumulative_pnl = np.cumsum(trade_pnls)
        ax4.plot(range(len(cumulative_pnl)), cumulative_pnl, color='blue',
                linewidth=2, marker='o', markersize=4, label='Cumulative PnL')

        ax4.set_title('Trade PnL Distribution', fontsize=12, fontweight='bold')
        ax4.set_xlabel('Trade Number')
        ax4.set_ylabel('PnL ($)')
        ax4.legend()
        ax4.grid(True, alpha=0.3, axis='y')

    plt.savefig('simplified_backtest_results.png', dpi=150, bbox_inches='tight')
    print("\n📊 Chart saved as 'simplified_backtest_results.png'")


def compare_all_strategies(df: pd.DataFrame):
    """Compare all strategy versions"""
    print("\n" + "="*70)
    print("COMPLETE STRATEGY COMPARISON")
    print("="*70)

    results = []

    # 1. Basic SMC
    print("\n1️⃣  Basic SMC Strategy...")
    basic = SMCStrategy(risk_reward_ratio=2.0, swing_length=10)
    df_basic = basic.run_strategy(df.copy())
    bt_basic = Backtester(initial_capital=10000)
    stats_basic = bt_basic.run(df_basic)

    results.append({
        'Strategy': 'Basic SMC',
        'Trades': stats_basic['total_trades'],
        'Win Rate %': f"{stats_basic['win_rate']:.1f}",
        'Return %': f"{stats_basic['total_return_pct']:.2f}",
        'Profit Factor': f"{stats_basic['profit_factor']:.2f}",
        'Sharpe': f"{stats_basic['sharpe_ratio']:.2f}",
        'Max DD %': f"{stats_basic['max_drawdown']:.2f}"
    })

    # 2. Simplified SMC (Pure SMC + Volume)
    print("\n2️⃣  Simplified SMC (Pure SMC + Volume)...")
    simplified = SimplifiedSMCStrategy(
        risk_reward_ratio=2.0,
        swing_length=10,
        volume_lookback=2,
        min_candle_quality=50
    )
    df_simplified = simplified.run_strategy(df.copy())
    bt_simplified = Backtester(initial_capital=10000)
    stats_simplified = bt_simplified.run(df_simplified)

    results.append({
        'Strategy': 'Simplified SMC',
        'Trades': stats_simplified['total_trades'],
        'Win Rate %': f"{stats_simplified['win_rate']:.1f}",
        'Return %': f"{stats_simplified['total_return_pct']:.2f}",
        'Profit Factor': f"{stats_simplified['profit_factor']:.2f}",
        'Sharpe': f"{stats_simplified['sharpe_ratio']:.2f}",
        'Max DD %': f"{stats_simplified['max_drawdown']:.2f}"
    })

    # 3. Simplified with lower quality threshold
    print("\n3️⃣  Simplified SMC (Lower Quality Threshold)...")
    simplified_relaxed = SimplifiedSMCStrategy(
        risk_reward_ratio=2.0,
        swing_length=10,
        volume_lookback=2,
        min_candle_quality=40  # Lower threshold
    )
    df_relaxed = simplified_relaxed.run_strategy(df.copy())
    bt_relaxed = Backtester(initial_capital=10000)
    stats_relaxed = bt_relaxed.run(df_relaxed)

    results.append({
        'Strategy': 'Simplified (Q=40)',
        'Trades': stats_relaxed['total_trades'],
        'Win Rate %': f"{stats_relaxed['win_rate']:.1f}",
        'Return %': f"{stats_relaxed['total_return_pct']:.2f}",
        'Profit Factor': f"{stats_relaxed['profit_factor']:.2f}",
        'Sharpe': f"{stats_relaxed['sharpe_ratio']:.2f}",
        'Max DD %': f"{stats_relaxed['max_drawdown']:.2f}"
    })

    # Display comparison table
    print("\n")
    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))
    print("\n" + "="*70)

    # Return best performing strategy
    best_idx = df_results['Return %'].apply(lambda x: float(x)).idxmax()
    best_strategy = df_results.iloc[best_idx]['Strategy']

    print(f"\n🏆 Best Performer: {best_strategy}")

    return stats_simplified, df_simplified


def main():
    """Main execution"""
    print("\n🎯 SIMPLIFIED SMC STRATEGY - Pure SMC + Volume Analysis")
    print("="*70)
    print("\n✨ Philosophy:")
    print("  • NO MA filters (retail indicator)")
    print("  • NO HTF multiplier (overcomplicated)")
    print("  • YES Market Structure (SMC core)")
    print("  • YES Order Blocks & FVG (institutional zones)")
    print("  • YES Volume Analysis (smart money footprint)")
    print("  • YES Candle Quality Scoring (0-100)")

    # Generate data
    print("\n📥 Loading data...")
    print("  Generating sample data (365 days)...")

    df = generate_sample_data(days=365, start_price=50000, volatility=0.025)

    if not validate_data(df):
        print("❌ Data validation failed")
        return

    print(f"  ✅ Generated {len(df)} candles")
    print(f"  Date range: {df.index[0]} to {df.index[-1]}")

    # Run comparison
    stats, df_result = compare_all_strategies(df)

    # Detailed results for simplified strategy
    print("\n" + "="*70)
    print("SIMPLIFIED SMC STRATEGY - DETAILED RESULTS")
    print("="*70)

    backtester = Backtester(initial_capital=10000)
    backtester.print_results(stats)

    # Show sample signals with reasons
    signals = df_result[df_result['signal'] != 0]
    if len(signals) > 0:
        print("\n📋 Sample Signals:")
        print("-" * 70)
        for idx in signals.index[:5]:  # First 5 signals
            sig = signals.loc[idx]
            direction = "LONG" if sig['signal'] == 1 else "SHORT"
            print(f"\n{idx}: {direction}")
            print(f"  Quality: {sig['candle_quality']:.0f}/100")
            print(f"  Reason: {sig['signal_reason']}")
            print(f"  Entry: ${sig['entry_price']:.2f}")
            print(f"  Stop: ${sig['stop_loss']:.2f}")
            print(f"  Target: ${sig['take_profit']:.2f}")
            print(f"  R:R: 1:{(sig['take_profit'] - sig['entry_price']) / abs(sig['entry_price'] - sig['stop_loss']):.1f}")

    # Save results
    if stats['total_trades'] > 0:
        df_trades = pd.DataFrame(stats['trades'])
        df_trades.to_csv('simplified_trades.csv', index=False)
        print(f"\n\n💾 Trades saved to 'simplified_trades.csv'")

        # Plot
        print("\n📈 Generating charts...")
        capital = 10000
        equity = [capital]
        for trade in stats['trades']:
            capital += trade['pnl']
            equity.append(capital)

        plot_simplified_results(df_result, equity, stats['trades'])

    print("\n✅ Simplified Backtest Complete!\n")


if __name__ == "__main__":
    main()
