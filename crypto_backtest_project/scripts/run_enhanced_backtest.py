"""
Run Enhanced SMC Strategy Backtest
Multi-timeframe analysis with improved filters
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_smc_strategy import EnhancedSMCStrategy
from backtester import Backtester
from data_loader import generate_sample_data, validate_data


def plot_enhanced_results(df_ltf: pd.DataFrame, df_htf: pd.DataFrame, equity_curve: list, trades: list):
    """
    Plot enhanced backtest results

    Args:
        df_ltf: LTF DataFrame with signals
        df_htf: HTF DataFrame
        equity_curve: Equity curve values
        trades: List of trades
    """
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

    # Plot 1: LTF Price with entry/exit points
    ax1 = fig.add_subplot(gs[0:2, :])
    ax1.plot(df_ltf.index, df_ltf['close'], label='LTF Close', color='black', linewidth=0.8, alpha=0.7)

    # Plot EMAs
    ax1.plot(df_ltf.index, df_ltf['ema_50'], label='EMA 50', color='blue', linewidth=1, alpha=0.5)
    ax1.plot(df_ltf.index, df_ltf['ema_200'], label='EMA 200', color='red', linewidth=1, alpha=0.5)

    # Plot signals
    buy_signals = df_ltf[df_ltf['signal'] == 1]
    sell_signals = df_ltf[df_ltf['signal'] == -1]

    ax1.scatter(buy_signals.index, buy_signals['close'], color='green', marker='^', s=150, label='BUY Signal', zorder=5, edgecolors='black')
    ax1.scatter(sell_signals.index, sell_signals['close'], color='red', marker='v', s=150, label='SELL Signal', zorder=5, edgecolors='black')

    # Plot premium/discount zones
    if 'fib_50' in df_ltf.columns:
        ax1.plot(df_ltf.index, df_ltf['fib_50'], '--', color='purple', alpha=0.3, label='Equilibrium')
        ax1.fill_between(df_ltf.index, df_ltf['fib_0'], df_ltf['fib_50'], alpha=0.1, color='green', label='Discount Zone')
        ax1.fill_between(df_ltf.index, df_ltf['fib_50'], df_ltf['fib_100'], alpha=0.1, color='red', label='Premium Zone')

    ax1.set_title('Enhanced SMC Strategy - LTF Price Action', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price')
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Plot 2: HTF Trend
    ax2 = fig.add_subplot(gs[2, 0])
    ax2.plot(df_htf.index, df_htf['close'], label='HTF Close', color='black', linewidth=1.5)
    ax2.plot(df_htf.index, df_htf['ema_50'], label='HTF EMA 50', color='blue', linewidth=1)
    ax2.set_title('HTF Trend Context', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Price')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Plot 3: RSI
    ax3 = fig.add_subplot(gs[2, 1])
    ax3.plot(df_ltf.index, df_ltf['rsi'], label='RSI', color='purple', linewidth=1)
    ax3.axhline(y=70, color='red', linestyle='--', alpha=0.5)
    ax3.axhline(y=30, color='green', linestyle='--', alpha=0.5)
    ax3.axhline(y=50, color='gray', linestyle='--', alpha=0.3)
    ax3.fill_between(df_ltf.index, 70, 100, alpha=0.2, color='red')
    ax3.fill_between(df_ltf.index, 0, 30, alpha=0.2, color='green')
    ax3.set_title('RSI Indicator', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('RSI')
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # Plot 4: Equity Curve
    ax4 = fig.add_subplot(gs[3, 0])
    ax4.plot(equity_curve, label='Equity Curve', color='blue', linewidth=2)
    ax4.axhline(y=equity_curve[0], color='gray', linestyle='--', label='Initial Capital', alpha=0.5)
    ax4.fill_between(range(len(equity_curve)), equity_curve[0], equity_curve,
                     where=[e >= equity_curve[0] for e in equity_curve], alpha=0.3, color='green')
    ax4.fill_between(range(len(equity_curve)), equity_curve[0], equity_curve,
                     where=[e < equity_curve[0] for e in equity_curve], alpha=0.3, color='red')
    ax4.set_title('Equity Curve', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Bar')
    ax4.set_ylabel('Equity ($)')
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    # Plot 5: Trade PnL Distribution
    ax5 = fig.add_subplot(gs[3, 1])
    if trades:
        trade_pnls = [t['pnl'] for t in trades]
        colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnls]
        ax5.bar(range(len(trade_pnls)), trade_pnls, color=colors, alpha=0.6, edgecolor='black')
        ax5.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax5.set_title('Trade PnL Distribution', fontsize=12, fontweight='bold')
        ax5.set_xlabel('Trade Number')
        ax5.set_ylabel('PnL ($)')
        ax5.grid(True, alpha=0.3, axis='y')

    plt.savefig('enhanced_backtest_results.png', dpi=150, bbox_inches='tight')
    print("\n📊 Enhanced chart saved as 'enhanced_backtest_results.png'")


def compare_strategies(df: pd.DataFrame):
    """
    Compare basic vs enhanced strategy

    Args:
        df: DataFrame with OHLC data
    """
    print("\n⚖️  STRATEGY COMPARISON")
    print("="*60)

    results = []

    # Test 1: Basic SMC Strategy
    print("\n1️⃣  Testing Basic SMC Strategy...")
    from smc_strategy import SMCStrategy
    basic_strategy = SMCStrategy(risk_reward_ratio=2.0, swing_length=10)
    df_basic = basic_strategy.run_strategy(df.copy())

    backtester_basic = Backtester(initial_capital=10000)
    stats_basic = backtester_basic.run(df_basic)

    results.append({
        'Strategy': 'Basic SMC',
        'Return %': stats_basic['total_return_pct'],
        'Win Rate %': stats_basic['win_rate'],
        'Total Trades': stats_basic['total_trades'],
        'Profit Factor': stats_basic['profit_factor'],
        'Sharpe Ratio': stats_basic['sharpe_ratio'],
        'Max DD %': stats_basic['max_drawdown']
    })

    # Test 2: Enhanced SMC Strategy
    print("\n2️⃣  Testing Enhanced SMC Strategy (HTF+LTF)...")
    enhanced_strategy = EnhancedSMCStrategy(
        htf_multiplier=3,  # Reduced from 4 to 3 for more signals
        risk_reward_ratio=2.0,
        swing_length=10,
        use_ma_filter=True,
        use_premium_discount=False,  # Disabled for more signals
        use_volume_filter=False,  # Disabled for more signals
        use_atr_stops=True,
        confirmation_candles=2  # Reduced from 3 to 2
    )

    df_enhanced, df_htf = enhanced_strategy.run_strategy(df.copy())

    backtester_enhanced = Backtester(initial_capital=10000)
    stats_enhanced = backtester_enhanced.run(df_enhanced)

    results.append({
        'Strategy': 'Enhanced SMC',
        'Return %': stats_enhanced['total_return_pct'],
        'Win Rate %': stats_enhanced['win_rate'],
        'Total Trades': stats_enhanced['total_trades'],
        'Profit Factor': stats_enhanced['profit_factor'],
        'Sharpe Ratio': stats_enhanced['sharpe_ratio'],
        'Max DD %': stats_enhanced['max_drawdown']
    })

    # Test 3: Enhanced without filters (to see impact)
    print("\n3️⃣  Testing Enhanced SMC (No Filters)...")
    enhanced_no_filters = EnhancedSMCStrategy(
        htf_multiplier=4,
        risk_reward_ratio=2.0,
        swing_length=10,
        use_ma_filter=False,
        use_premium_discount=False,
        use_volume_filter=False,
        use_atr_stops=True,
        confirmation_candles=3
    )

    df_no_filters, _ = enhanced_no_filters.run_strategy(df.copy())

    backtester_no_filters = Backtester(initial_capital=10000)
    stats_no_filters = backtester_no_filters.run(df_no_filters)

    results.append({
        'Strategy': 'Enhanced (No Filters)',
        'Return %': stats_no_filters['total_return_pct'],
        'Win Rate %': stats_no_filters['win_rate'],
        'Total Trades': stats_no_filters['total_trades'],
        'Profit Factor': stats_no_filters['profit_factor'],
        'Sharpe Ratio': stats_no_filters['sharpe_ratio'],
        'Max DD %': stats_no_filters['max_drawdown']
    })

    # Display comparison
    df_results = pd.DataFrame(results)
    print("\n")
    print(df_results.to_string(index=False))
    print("\n" + "="*60)

    return stats_enhanced, df_enhanced, df_htf


def main():
    """Main execution"""
    print("\n🚀 ENHANCED SMC STRATEGY BACKTESTER")
    print("="*60)
    print("\n✨ Features:")
    print("  • Multi-Timeframe Analysis (HTF for signals, LTF for entries)")
    print("  • MA Trend Filter")
    print("  • Premium/Discount Zones")
    print("  • LTF Confirmation Candles")
    print("  • ATR-based Stop Loss")
    print("  • Dynamic Risk:Reward Ratio")
    print("  • Volume Confirmation")
    print("  • RSI & MACD Filters")

    # Generate data (simulate hourly data for better multi-timeframe)
    print("\n📥 Loading data...")
    print("  Generating sample hourly data (365 days = 8760 hours)...")

    # Generate hourly-like data
    df = generate_sample_data(days=365*4, start_price=50000, volatility=0.015)  # Lower volatility for hourly
    df = df.iloc[::4]  # Simulate hourly by taking every 4th point

    print(f"  ✅ Generated {len(df)} hourly candles")
    print(f"  Date range: {df.index[0]} to {df.index[-1]}")

    # Validate data
    if not validate_data(df):
        print("❌ Data validation failed")
        return

    # Run comparison
    stats, df_enhanced, df_htf = compare_strategies(df)

    # Print detailed results for enhanced strategy
    print("\n" + "="*60)
    print("ENHANCED STRATEGY DETAILED RESULTS")
    print("="*60)

    if stats['total_trades'] == 0:
        print("\n⚠️  No trades generated. Strategy filters may be too restrictive.")
        print("\n💡 Suggestions:")
        print("  - Try reducing htf_multiplier (use 2 or 3 instead of 4)")
        print("  - Disable some filters (ma_filter, premium_discount)")
        print("  - Increase data length or volatility")
        print("  - Reduce confirmation_candles requirement")
        return

    backtester = Backtester(initial_capital=10000)
    backtester.equity_curve = [10000]  # Reconstruct for display
    backtester.print_results(stats)

    # Save trades
    if stats['total_trades'] > 0:
        df_trades = pd.DataFrame(stats['trades'])
        df_trades.to_csv('enhanced_trades.csv', index=False)
        print(f"\n💾 Enhanced trades saved to 'enhanced_trades.csv'")

        # Plot results
        print("\n📈 Generating enhanced charts...")

        # Reconstruct equity curve
        capital = 10000
        equity = [capital]
        for trade in stats['trades']:
            capital += trade['pnl']
            equity.append(capital)

        plot_enhanced_results(df_enhanced, df_htf, equity, stats['trades'])

    print("\n✅ Enhanced Backtest Complete!\n")


if __name__ == "__main__":
    main()
