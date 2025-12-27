"""
Test SMC Strategies on Real Market Data (XAUUSD, BTC, EUR/USD)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simplified_smc_strategy import SimplifiedSMCStrategy
from smc_strategy import SMCStrategy
from enhanced_smc_strategy import EnhancedSMCStrategy
from backtester import Backtester
from data_loader import download_data_yfinance


def download_gold_data(period='1y'):
    """Download XAUUSD (Gold) data from Yahoo Finance"""
    print(f"\n📥 Downloading XAUUSD (Gold) data ({period})...")

    # Gold ticker on Yahoo Finance
    ticker = 'GC=F'  # Gold Futures

    df = download_data_yfinance(ticker, period=period)

    if df is None or len(df) == 0:
        print("  ❌ Failed to download gold data")
        return None

    print(f"  ✅ Downloaded {len(df)} candles")
    print(f"  📅 Date range: {df.index[0]} to {df.index[-1]}")
    print(f"  💰 Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    return df


def download_bitcoin_data(period='1y'):
    """Download BTC-USD data"""
    print(f"\n📥 Downloading BTC-USD data ({period})...")

    ticker = 'BTC-USD'

    df = download_data_yfinance(ticker, period=period)

    if df is None or len(df) == 0:
        print("  ❌ Failed to download BTC data")
        return None

    print(f"  ✅ Downloaded {len(df)} candles")
    print(f"  📅 Date range: {df.index[0]} to {df.index[-1]}")
    print(f"  💰 Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    return df


def download_eurusd_data(period='1y'):
    """Download EUR/USD data"""
    print(f"\n📥 Downloading EUR/USD data ({period})...")

    ticker = 'EURUSD=X'

    df = download_data_yfinance(ticker, period=period)

    if df is None or len(df) == 0:
        print("  ❌ Failed to download EUR/USD data")
        return None

    print(f"  ✅ Downloaded {len(df)} candles")
    print(f"  📅 Date range: {df.index[0]} to {df.index[-1]}")
    print(f"  💰 Price range: ${df['close'].min():.4f} - ${df['close'].max():.4f}")

    return df


def test_all_strategies(df, asset_name):
    """Test all 3 strategy versions"""
    print(f"\n{'='*80}")
    print(f"TESTING ON {asset_name}")
    print(f"{'='*80}")

    results = []

    # 1. Basic SMC
    print("\n1️⃣  Basic SMC Strategy...")
    try:
        basic = SMCStrategy(risk_reward_ratio=2.0, swing_length=10)
        df_basic = basic.run_strategy(df.copy())
        bt_basic = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
        stats_basic = bt_basic.run(df_basic)

        results.append({
            'Strategy': 'Basic SMC',
            'Trades': stats_basic['total_trades'],
            'Win Rate %': f"{stats_basic['win_rate']:.1f}",
            'Return %': f"{stats_basic['total_return_pct']:.2f}",
            'Profit Factor': f"{stats_basic['profit_factor']:.2f}",
            'Sharpe': f"{stats_basic['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats_basic['max_drawdown']:.2f}",
            'Avg Win $': f"{stats_basic['avg_win']:.2f}" if stats_basic['avg_win'] else '0.00',
            'Avg Loss $': f"{stats_basic['avg_loss']:.2f}" if stats_basic['avg_loss'] else '0.00'
        })
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results.append({
            'Strategy': 'Basic SMC',
            'Trades': 0,
            'Win Rate %': 'ERROR',
            'Return %': 'ERROR',
            'Profit Factor': '-',
            'Sharpe': '-',
            'Max DD %': '-',
            'Avg Win $': '-',
            'Avg Loss $': '-'
        })

    # 2. Enhanced SMC
    print("\n2️⃣  Enhanced SMC Strategy...")
    try:
        enhanced = EnhancedSMCStrategy(
            htf_multiplier=3,
            risk_reward_ratio=2.0,
            swing_length=10,
            use_ma_filter=False,  # Disabled based on error analysis
            use_premium_discount=False,
            use_volume_filter=True,
            use_atr_stops=True,
            confirmation_candles=2
        )
        df_enhanced, df_htf = enhanced.run_strategy(df.copy())
        bt_enhanced = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
        stats_enhanced = bt_enhanced.run(df_enhanced)

        results.append({
            'Strategy': 'Enhanced SMC',
            'Trades': stats_enhanced['total_trades'],
            'Win Rate %': f"{stats_enhanced['win_rate']:.1f}",
            'Return %': f"{stats_enhanced['total_return_pct']:.2f}",
            'Profit Factor': f"{stats_enhanced['profit_factor']:.2f}",
            'Sharpe': f"{stats_enhanced['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats_enhanced['max_drawdown']:.2f}",
            'Avg Win $': f"{stats_enhanced['avg_win']:.2f}" if stats_enhanced['avg_win'] else '0.00',
            'Avg Loss $': f"{stats_enhanced['avg_loss']:.2f}" if stats_enhanced['avg_loss'] else '0.00'
        })
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results.append({
            'Strategy': 'Enhanced SMC',
            'Trades': 0,
            'Win Rate %': 'ERROR',
            'Return %': 'ERROR',
            'Profit Factor': '-',
            'Sharpe': '-',
            'Max DD %': '-',
            'Avg Win $': '-',
            'Avg Loss $': '-'
        })

    # 3. Simplified SMC
    print("\n3️⃣  Simplified SMC Strategy...")
    try:
        simplified = SimplifiedSMCStrategy(
            risk_reward_ratio=2.0,
            swing_length=10,
            volume_lookback=2,
            min_candle_quality=50
        )
        df_simplified = simplified.run_strategy(df.copy())
        bt_simplified = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
        stats_simplified = bt_simplified.run(df_simplified)

        results.append({
            'Strategy': 'Simplified SMC',
            'Trades': stats_simplified['total_trades'],
            'Win Rate %': f"{stats_simplified['win_rate']:.1f}",
            'Return %': f"{stats_simplified['total_return_pct']:.2f}",
            'Profit Factor': f"{stats_simplified['profit_factor']:.2f}",
            'Sharpe': f"{stats_simplified['sharpe_ratio']:.2f}",
            'Max DD %': f"{stats_simplified['max_drawdown']:.2f}",
            'Avg Win $': f"{stats_simplified['avg_win']:.2f}" if stats_simplified['avg_win'] else '0.00',
            'Avg Loss $': f"{stats_simplified['avg_loss']:.2f}" if stats_simplified['avg_loss'] else '0.00'
        })

        best_strategy_data = (stats_simplified, df_simplified, 'Simplified')
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results.append({
            'Strategy': 'Simplified SMC',
            'Trades': 0,
            'Win Rate %': 'ERROR',
            'Return %': 'ERROR',
            'Profit Factor': '-',
            'Sharpe': '-',
            'Max DD %': '-',
            'Avg Win $': '-',
            'Avg Loss $': '-'
        })
        best_strategy_data = None

    # Display results
    print("\n")
    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))
    print(f"\n{'='*80}")

    # Find best strategy
    valid_results = df_results[df_results['Return %'] != 'ERROR'].copy()
    if len(valid_results) > 0:
        valid_results['Return_Num'] = valid_results['Return %'].astype(float)
        best_idx = valid_results['Return_Num'].idxmax()
        best_name = valid_results.iloc[best_idx]['Strategy']
        best_return = valid_results.iloc[best_idx]['Return %']
        print(f"\n🏆 Best Strategy for {asset_name}: {best_name} ({best_return}%)")

    return results, best_strategy_data


def plot_real_data_results(df, asset_name, equity_curve, trades):
    """Plot results for real data"""
    if len(trades) == 0:
        print(f"\n⚠️  No trades to plot for {asset_name}")
        return

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # Plot 1: Price with signals
    ax1 = fig.add_subplot(gs[0:2, :])
    ax1.plot(df.index, df['close'], label='Close Price', color='black', linewidth=1)

    # Plot signals
    buy_signals = df[df['signal'] == 1]
    sell_signals = df[df['signal'] == -1]

    if len(buy_signals) > 0:
        ax1.scatter(buy_signals.index, buy_signals['entry_price'],
                   color='green', marker='^', s=150, label='BUY',
                   zorder=5, edgecolors='darkgreen', linewidths=2)

    if len(sell_signals) > 0:
        ax1.scatter(sell_signals.index, sell_signals['entry_price'],
                   color='red', marker='v', s=150, label='SELL',
                   zorder=5, edgecolors='darkred', linewidths=2)

    ax1.set_title(f'{asset_name} - SMC Strategy Results', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Equity Curve
    ax2 = fig.add_subplot(gs[2, 0])
    ax2.plot(equity_curve, color='blue', linewidth=2, label='Equity')
    ax2.axhline(y=equity_curve[0], color='gray', linestyle='--', alpha=0.5)
    ax2.fill_between(range(len(equity_curve)), equity_curve[0], equity_curve,
                     where=[e >= equity_curve[0] for e in equity_curve],
                     alpha=0.3, color='green')
    ax2.fill_between(range(len(equity_curve)), equity_curve[0], equity_curve,
                     where=[e < equity_curve[0] for e in equity_curve],
                     alpha=0.3, color='red')
    ax2.set_title('Equity Curve', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Bar')
    ax2.set_ylabel('Equity ($)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: PnL Distribution
    ax3 = fig.add_subplot(gs[2, 1])
    trade_pnls = [t['pnl'] for t in trades]
    colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnls]
    ax3.bar(range(len(trade_pnls)), trade_pnls, color=colors, alpha=0.6, edgecolor='black')
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

    cumulative = np.cumsum(trade_pnls)
    ax3.plot(range(len(cumulative)), cumulative, color='blue',
            linewidth=2, marker='o', markersize=4, label='Cumulative')

    ax3.set_title('Trade PnL', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Trade #')
    ax3.set_ylabel('PnL ($)')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')

    filename = f'{asset_name.lower().replace("/", "_")}_results.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n📊 Chart saved as '{filename}'")
    plt.close()


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("SMC STRATEGY - REAL MARKET DATA TESTING")
    print("="*80)
    print("\n🎯 Testing on:")
    print("  • XAUUSD (Gold)")
    print("  • BTC-USD (Bitcoin)")
    print("  • EUR/USD (Euro)")

    all_results = {}

    # Test 1: XAUUSD (Gold)
    print("\n" + "="*80)
    print("TEST 1: XAUUSD (GOLD)")
    print("="*80)

    df_gold = download_gold_data(period='1y')

    if df_gold is not None and len(df_gold) > 100:
        results_gold, best_gold = test_all_strategies(df_gold, 'XAUUSD')
        all_results['XAUUSD'] = results_gold

        # Plot best strategy results for gold
        if best_gold is not None:
            stats, df_result, strategy_name = best_gold
            if stats['total_trades'] > 0:
                capital = 10000
                equity = [capital]
                for trade in stats['trades']:
                    capital += trade['pnl']
                    equity.append(capital)

                plot_real_data_results(df_result, 'XAUUSD', equity, stats['trades'])

                # Save detailed results
                print(f"\n📋 Detailed Results for XAUUSD ({strategy_name}):")
                print("-" * 80)
                backtester = Backtester(initial_capital=10000)
                backtester.print_results(stats)

                # Save trades
                df_trades = pd.DataFrame(stats['trades'])
                df_trades.to_csv('xauusd_trades.csv', index=False)
                print(f"\n💾 XAUUSD trades saved to 'xauusd_trades.csv'")
    else:
        print("\n⚠️  Insufficient XAUUSD data")

    # Test 2: BTC-USD
    print("\n" + "="*80)
    print("TEST 2: BTC-USD (BITCOIN)")
    print("="*80)

    df_btc = download_bitcoin_data(period='1y')

    if df_btc is not None and len(df_btc) > 100:
        results_btc, best_btc = test_all_strategies(df_btc, 'BTC-USD')
        all_results['BTC-USD'] = results_btc

        if best_btc is not None:
            stats, df_result, strategy_name = best_btc
            if stats['total_trades'] > 0:
                capital = 10000
                equity = [capital]
                for trade in stats['trades']:
                    capital += trade['pnl']
                    equity.append(capital)

                plot_real_data_results(df_result, 'BTC-USD', equity, stats['trades'])
    else:
        print("\n⚠️  Insufficient BTC data")

    # Test 3: EUR/USD
    print("\n" + "="*80)
    print("TEST 3: EUR/USD (FOREX)")
    print("="*80)

    df_eur = download_eurusd_data(period='1y')

    if df_eur is not None and len(df_eur) > 100:
        results_eur, best_eur = test_all_strategies(df_eur, 'EUR/USD')
        all_results['EUR/USD'] = results_eur

        if best_eur is not None:
            stats, df_result, strategy_name = best_eur
            if stats['total_trades'] > 0:
                capital = 10000
                equity = [capital]
                for trade in stats['trades']:
                    capital += trade['pnl']
                    equity.append(capital)

                plot_real_data_results(df_result, 'EUR/USD', equity, stats['trades'])
    else:
        print("\n⚠️  Insufficient EUR/USD data")

    # Final Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - ALL ASSETS")
    print("="*80)

    for asset, results in all_results.items():
        print(f"\n{asset}:")
        df_res = pd.DataFrame(results)
        print(df_res.to_string(index=False))

    print("\n✅ Real Data Testing Complete!\n")


if __name__ == "__main__":
    main()
