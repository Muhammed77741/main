"""
Run Stock Long-Term Strategy Backtest
Запуск бэктеста стратегии для акций (день/неделя)
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_long_term_strategy import StockLongTermStrategy
from stock_data_loader import generate_stock_data
from backtester import Backtester


def run_single_stock_backtest(
    ticker: str = "AAPL",
    timeframe: str = '1D',
    periods: int = 500,
    initial_capital: float = 10000,
    use_fibonacci: bool = True,
    fib_extension: float = 1.618
):
    """
    Run backtest for a single stock
    
    Args:
        ticker: Stock ticker
        timeframe: '1D' or '1W'
        periods: Number of periods to backtest
        initial_capital: Starting capital
        use_fibonacci: Use Fibonacci TP
        fib_extension: Fibonacci extension level
        
    Returns:
        Dictionary with results
    """
    print("\n" + "="*80)
    print(f"🎯 STOCK LONG-TERM STRATEGY BACKTEST - {ticker} ({timeframe})")
    print("="*80)
    
    # Generate data
    df = generate_stock_data(
        ticker=ticker,
        timeframe=timeframe,
        periods=periods,
        initial_price=150.0 if ticker == "AAPL" else 100.0,
        volatility=0.02  # 2% daily volatility for stocks
    )
    
    # Run strategy
    strategy = StockLongTermStrategy(
        timeframe=timeframe,
        risk_reward_ratio=2.5 if timeframe == '1D' else 3.0,
        risk_per_trade=0.02,
        swing_length=20 if timeframe == '1D' else 10,
        volume_lookback=5 if timeframe == '1D' else 3,
        min_candle_quality=40,
        use_fibonacci_tp=use_fibonacci,
        fib_extension=fib_extension,
        min_volume_ratio=1.2
    )
    
    df_signals = strategy.run_strategy(df)
    
    # Run backtest
    backtester = Backtester(
        initial_capital=initial_capital,
        commission=0.001,  # 0.1% commission
        slippage=0.0005,  # 0.05% slippage
        risk_per_trade=0.02
    )
    
    results = backtester.run(df_signals)
    backtester.print_results(results)
    
    # Monthly breakdown
    if len(backtester.trades) > 0:
        print("\n" + "="*80)
        print("📅 MONTHLY BREAKDOWN")
        print("="*80)
        
        trades_df = pd.DataFrame([t.to_dict() for t in backtester.trades])
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
        trades_df['month'] = trades_df['entry_time'].dt.to_period('M')
        
        monthly = trades_df.groupby('month').agg({
            'pnl_pct': ['count', 'sum', 'mean'],
            'direction': lambda x: (x == 'LONG').sum() / len(x) * 100
        }).round(2)
        
        monthly.columns = ['Trades', 'Total_PnL%', 'Avg_PnL%', 'Long_Ratio%']
        
        print(monthly)
        
        # Win rate by month
        monthly_wr = trades_df.groupby('month').apply(
            lambda x: (x['pnl_pct'] > 0).sum() / len(x) * 100
        ).round(1)
        
        print("\n📊 Monthly Win Rate:")
        for month, wr in monthly_wr.items():
            print(f"   {month}: {wr:.1f}%")
    
    return {
        'ticker': ticker,
        'timeframe': timeframe,
        'results': results,
        'df': df_signals,
        'backtester': backtester
    }


def compare_timeframes(ticker: str = "AAPL"):
    """
    Compare daily vs weekly timeframes
    
    Args:
        ticker: Stock ticker
    """
    print("\n" + "="*80)
    print(f"⚖️  COMPARING TIMEFRAMES: {ticker}")
    print("="*80)
    
    # Run daily backtest
    print("\n1️⃣  DAILY TIMEFRAME (1D)")
    print("-"*80)
    daily_results = run_single_stock_backtest(
        ticker=ticker,
        timeframe='1D',
        periods=500
    )
    
    # Run weekly backtest
    print("\n2️⃣  WEEKLY TIMEFRAME (1W)")
    print("-"*80)
    weekly_results = run_single_stock_backtest(
        ticker=ticker,
        timeframe='1W',
        periods=104  # 2 years
    )
    
    # Comparison
    print("\n" + "="*80)
    print("📊 TIMEFRAME COMPARISON")
    print("="*80)
    
    comparison_df = pd.DataFrame({
        'Daily (1D)': {
            'Total PnL%': daily_results['results'].get('total_return_pct', 0),
            'Win Rate%': daily_results['results'].get('win_rate', 0),
            'Total Trades': daily_results['results'].get('total_trades', 0),
            'Max DD%': daily_results['results'].get('max_drawdown', 0),
            'Sharpe': daily_results['results'].get('sharpe_ratio', 0),
            'Profit Factor': daily_results['results'].get('profit_factor', 0)
        },
        'Weekly (1W)': {
            'Total PnL%': weekly_results['results'].get('total_return_pct', 0),
            'Win Rate%': weekly_results['results'].get('win_rate', 0),
            'Total Trades': weekly_results['results'].get('total_trades', 0),
            'Max DD%': weekly_results['results'].get('max_drawdown', 0),
            'Sharpe': weekly_results['results'].get('sharpe_ratio', 0),
            'Profit Factor': weekly_results['results'].get('profit_factor', 0)
        }
    })
    
    print(comparison_df.round(2))
    
    # Plot comparison
    plot_timeframe_comparison(daily_results, weekly_results, ticker)
    
    return daily_results, weekly_results


def plot_timeframe_comparison(daily_results, weekly_results, ticker):
    """
    Plot comparison between daily and weekly strategies
    
    Args:
        daily_results: Daily backtest results
        weekly_results: Weekly backtest results
        ticker: Stock ticker
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f'{ticker} Stock Long-Term Strategy - Daily vs Weekly', fontsize=16, fontweight='bold')
    
    # 1. Equity curves
    ax1 = axes[0, 0]
    daily_equity = daily_results['backtester'].equity_curve
    weekly_equity = weekly_results['backtester'].equity_curve
    
    ax1.plot(daily_equity, label='Daily (1D)', linewidth=2, color='blue')
    ax1.plot(weekly_equity, label='Weekly (1W)', linewidth=2, color='green')
    ax1.axhline(y=10000, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.set_title('Equity Curves', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Trade Number')
    ax1.set_ylabel('Equity ($)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Metrics comparison
    ax2 = axes[0, 1]
    metrics = ['Total PnL%', 'Win Rate%', 'Profit Factor']
    daily_vals = [
        daily_results['results']['total_return_pct'],
        daily_results['results']['win_rate'],
        daily_results['results']['profit_factor']
    ]
    weekly_vals = [
        weekly_results['results']['total_return_pct'],
        weekly_results['results']['win_rate'],
        weekly_results['results']['profit_factor']
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax2.bar(x - width/2, daily_vals, width, label='Daily', color='blue', alpha=0.7)
    bars2 = ax2.bar(x + width/2, weekly_vals, width, label='Weekly', color='green', alpha=0.7)
    
    ax2.set_title('Metrics Comparison', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=9)
    
    # 3. Trade count by direction
    ax3 = axes[1, 0]
    daily_long = daily_results['results']['long_trades']
    daily_short = daily_results['results']['short_trades']
    weekly_long = weekly_results['results']['long_trades']
    weekly_short = weekly_results['results']['short_trades']
    
    categories = ['Daily Long', 'Daily Short', 'Weekly Long', 'Weekly Short']
    values = [daily_long, daily_short, weekly_long, weekly_short]
    colors = ['lightblue', 'lightcoral', 'lightgreen', 'salmon']
    
    bars = ax3.bar(categories, values, color=colors, alpha=0.7)
    ax3.set_title('Trade Distribution', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Number of Trades')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=10)
    
    # 4. Win rate by direction
    ax4 = axes[1, 1]
    daily_long_wr = daily_results['results']['long_win_rate']
    daily_short_wr = daily_results['results']['short_win_rate']
    weekly_long_wr = weekly_results['results']['long_win_rate']
    weekly_short_wr = weekly_results['results']['short_win_rate']
    
    categories = ['Long', 'Short']
    daily_wrs = [daily_long_wr, daily_short_wr]
    weekly_wrs = [weekly_long_wr, weekly_short_wr]
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax4.bar(x - width/2, daily_wrs, width, label='Daily', color='blue', alpha=0.7)
    bars2 = ax4.bar(x + width/2, weekly_wrs, width, label='Weekly', color='green', alpha=0.7)
    
    ax4.set_title('Win Rate by Direction', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Win Rate (%)')
    ax4.set_xticks(x)
    ax4.set_xticklabels(categories)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_ylim(0, 100)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # Save plot
    filename = f'stock_longterm_{ticker.lower()}_comparison.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\n📈 Chart saved: {filename}")
    
    plt.close()


def test_fibonacci_levels(ticker: str = "AAPL", timeframe: str = '1D'):
    """
    Test different Fibonacci extension levels
    
    Args:
        ticker: Stock ticker
        timeframe: '1D' or '1W'
    """
    print("\n" + "="*80)
    print(f"🔬 TESTING FIBONACCI LEVELS - {ticker} ({timeframe})")
    print("="*80)
    
    fib_levels = [1.618, 2.0, 2.618]
    results_list = []
    
    for fib in fib_levels:
        print(f"\n📊 Testing Fibonacci {fib}")
        print("-"*80)
        
        # Generate data
        df = generate_stock_data(
            ticker=ticker,
            timeframe=timeframe,
            periods=500 if timeframe == '1D' else 104
        )
        
        # Run strategy
        strategy = StockLongTermStrategy(
            timeframe=timeframe,
            use_fibonacci_tp=True,
            fib_extension=fib
        )
        
        df_signals = strategy.run_strategy(df)
        
        # Backtest
        backtester = Backtester(initial_capital=10000)
        results = backtester.run(df_signals)
        
        results_list.append({
            'Fib Level': fib,
            'Total PnL%': results['total_return_pct'],
            'Win Rate%': results['win_rate'],
            'Trades': results['total_trades'],
            'Profit Factor': results['profit_factor'],
            'Max DD%': results['max_drawdown']
        })
        
        print(f"   Total PnL: {results['total_return_pct']:.2f}%")
        print(f"   Win Rate: {results['win_rate']:.2f}%")
    
    # Comparison table
    print("\n" + "="*80)
    print("📊 FIBONACCI LEVELS COMPARISON")
    print("="*80)
    
    comparison_df = pd.DataFrame(results_list).set_index('Fib Level')
    print(comparison_df.round(2))
    
    # Find best
    best_fib = comparison_df['Total PnL%'].idxmax()
    print(f"\n🏆 Best Fibonacci Level: {best_fib}")
    print(f"   Total PnL: {comparison_df.loc[best_fib, 'Total PnL%']:.2f}%")
    
    return comparison_df


if __name__ == "__main__":
    # Test 1: Single stock backtest (Daily)
    print("\n🧪 TEST 1: Single Stock Backtest (Daily)")
    daily_result = run_single_stock_backtest(
        ticker="AAPL",
        timeframe='1D',
        periods=500
    )
    
    # Test 2: Single stock backtest (Weekly)
    print("\n🧪 TEST 2: Single Stock Backtest (Weekly)")
    weekly_result = run_single_stock_backtest(
        ticker="AAPL",
        timeframe='1W',
        periods=104
    )
    
    # Test 3: Compare timeframes
    print("\n🧪 TEST 3: Compare Timeframes")
    daily_vs_weekly = compare_timeframes(ticker="AAPL")
    
    # Test 4: Test Fibonacci levels
    print("\n🧪 TEST 4: Test Fibonacci Levels")
    fib_comparison = test_fibonacci_levels(ticker="AAPL", timeframe='1D')
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)
