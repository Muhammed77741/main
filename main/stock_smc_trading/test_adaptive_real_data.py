"""
Test Adaptive Stock Strategy on REAL DATA

Uses yfinance to download real stock data (4H)
Tests with Gold-inspired improvements:
- Adaptive TREND/RANGE modes
- Partial TP (50% → 30% → 20%)
- Trailing Stop
- Max Positions = 5
"""

import pandas as pd
import numpy as np
import sys

from stock_adaptive_strategy import StockAdaptiveStrategy, get_real_stock_data
from adaptive_backtester import AdaptiveBacktester


def test_adaptive_strategy(
    ticker: str = 'AAPL',
    days: int = 365,
    max_positions: int = 5
):
    """
    Test adaptive strategy on real data
    
    Args:
        ticker: Stock ticker (AAPL, MSFT, TSLA, etc.)
        days: Number of days of history
        max_positions: Max concurrent positions
    """
    print("\n" + "="*80)
    print(f"📊 ADAPTIVE STRATEGY TEST - {ticker} (REAL DATA)")
    print("="*80)
    print(f"   Period: {days} days")
    print(f"   Timeframe: 4H")
    print(f"   Max Positions: {max_positions}")
    print(f"   Inspired by: Gold SHORT Optimized (+325.70%)")
    
    # Get real data
    df = get_real_stock_data(ticker=ticker, days=days)
    
    if len(df) < 100:
        print(f"\n⚠️  Not enough data ({len(df)} candles). Need at least 100.")
        return None, None, None
    
    # Create adaptive strategy
    strategy = StockAdaptiveStrategy(
        timeframe='4H',
        fib_mode='aggressive',  # Use 2.618 like Gold
        max_positions=max_positions,
        enable_trailing_stop=True,
        enable_adaptive_modes=True,
        pattern_tolerance=0.02,
        swing_lookback=12,
        pattern_cooldown=3,
        require_trend_confirmation=False,
        min_candle_quality=25,
        min_volume_ratio=0.8,
        min_risk_pct=0.004,
        long_only=True  # Stocks = LONG only
    )
    
    # Run strategy
    df_signals = strategy.run_strategy(df)
    
    # Backtest with adaptive backtester
    backtester = AdaptiveBacktester(
        initial_capital=10000,
        risk_per_trade=0.02,  # 2% risk per trade
        max_positions=max_positions,
        commission=0.001,
        slippage=0.0005
    )
    
    results = backtester.run(df_signals)
    backtester.print_results(results)
    
    # Additional analysis
    if results['total_trades'] > 0:
        print_detailed_analysis(results, df_signals, ticker)
    
    return df_signals, results, backtester


def print_detailed_analysis(results: dict, df: pd.DataFrame, ticker: str):
    """Print detailed trade analysis"""
    print("\n" + "="*80)
    print("📊 DETAILED ANALYSIS")
    print("="*80)
    
    trades_df = pd.DataFrame(results['trades'])
    
    # Regime performance
    print("\n🎯 REGIME PERFORMANCE:")
    
    df_with_regime = df[df['signal'] != 0].copy()
    if 'regime' in df_with_regime.columns:
        trend_signals = (df_with_regime['regime'] == 'TREND').sum()
        range_signals = (df_with_regime['regime'] == 'RANGE').sum()
        total_signals = len(df_with_regime)
        
        print(f"   TREND: {trend_signals} signals ({trend_signals/total_signals*100:.1f}%)")
        print(f"   RANGE: {range_signals} signals ({range_signals/total_signals*100:.1f}%)")
    
    # Exit reason breakdown
    print("\n🚪 EXIT REASONS:")
    exit_counts = trades_df['exit_reason'].value_counts()
    for reason, count in exit_counts.items():
        pct = count / len(trades_df) * 100
        reason_trades = trades_df[trades_df['exit_reason'] == reason]
        avg_pnl = reason_trades['pnl_pct'].mean()
        print(f"   {reason}: {count} ({pct:.1f}%), avg PnL: {avg_pnl:.2f}%")
    
    # Partial TP analysis
    print("\n🎯 PARTIAL TP BREAKDOWN:")
    print(f"   TP1 only: {((trades_df['tp1_hit']) & (~trades_df['tp2_hit'])).sum()} trades")
    print(f"   TP1+TP2: {((trades_df['tp2_hit']) & (~trades_df['tp3_hit'])).sum()} trades")
    print(f"   Full TP (TP1+TP2+TP3): {trades_df['tp3_hit'].sum()} trades")
    print(f"   No TP hit: {(~trades_df['tp1_hit']).sum()} trades")
    
    # Trailing stop impact
    trailing_trades = trades_df[trades_df['trailing_hit'] == True]
    if len(trailing_trades) > 0:
        print(f"\n📈 TRAILING STOP IMPACT:")
        print(f"   Trailing exits: {len(trailing_trades)}")
        print(f"   Avg PnL from trailing: {trailing_trades['pnl_pct'].mean():.2f}%")
        print(f"   Total from trailing: {trailing_trades['pnl_pct'].sum():.2f}%")
    
    # Best/worst trades
    print(f"\n🏆 BEST TRADES:")
    best_trades = trades_df.nlargest(5, 'pnl_pct')[['entry_time', 'exit_reason', 'pnl_pct', 'tp1_hit', 'tp2_hit', 'tp3_hit']]
    best_trades['entry_time'] = pd.to_datetime(best_trades['entry_time']).dt.strftime('%Y-%m-%d')
    print(best_trades.to_string(index=False))
    
    print(f"\n📉 WORST TRADES:")
    worst_trades = trades_df.nsmallest(5, 'pnl_pct')[['entry_time', 'exit_reason', 'pnl_pct']]
    worst_trades['entry_time'] = pd.to_datetime(worst_trades['entry_time']).dt.strftime('%Y-%m-%d')
    print(worst_trades.to_string(index=False))
    
    # Time analysis
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    trades_df['hold_time'] = (pd.to_datetime(trades_df['exit_time']) - trades_df['entry_time']).dt.total_seconds() / 3600
    
    print(f"\n⏱️  HOLD TIME STATS:")
    print(f"   Average: {trades_df['hold_time'].mean():.1f} hours ({trades_df['hold_time'].mean()/24:.1f} days)")
    print(f"   Median: {trades_df['hold_time'].median():.1f} hours ({trades_df['hold_time'].median()/24:.1f} days)")
    print(f"   Min: {trades_df['hold_time'].min():.1f} hours")
    print(f"   Max: {trades_df['hold_time'].max():.1f} hours ({trades_df['hold_time'].max()/24:.1f} days)")
    
    # Monthly/Weekly breakdown
    trades_df['entry_month'] = trades_df['entry_time'].dt.to_period('M')
    monthly_pnl = trades_df.groupby('entry_month')['pnl_pct'].agg(['count', 'sum', 'mean'])
    
    if len(monthly_pnl) > 0:
        print(f"\n📅 MONTHLY BREAKDOWN:")
        print(monthly_pnl.to_string())
        
        profitable_months = (monthly_pnl['sum'] > 0).sum()
        total_months = len(monthly_pnl)
        print(f"\n   Profitable months: {profitable_months}/{total_months} ({profitable_months/total_months*100:.1f}%)")
    
    # Annualized return
    if len(df) > 0:
        days_tested = (df.index[-1] - df.index[0]).days
        if days_tested > 0:
            annualized_return = results['total_return_pct'] * (365 / days_tested)
            print(f"\n📈 ANNUALIZED RETURN: {annualized_return:.2f}%")


def compare_stocks(tickers: list = ['AAPL', 'MSFT', 'GOOGL'], days: int = 365):
    """
    Compare adaptive strategy across multiple stocks
    
    Args:
        tickers: List of stock tickers
        days: Number of days to test
    """
    print("\n" + "="*80)
    print(f"⚖️  COMPARING ADAPTIVE STRATEGY ACROSS STOCKS")
    print("="*80)
    
    results_comparison = []
    
    for ticker in tickers:
        print(f"\n{'='*80}")
        print(f"Testing {ticker}...")
        print(f"{'='*80}")
        
        try:
            df, results, bt = test_adaptive_strategy(
                ticker=ticker,
                days=days,
                max_positions=5
            )
            
            if results and results['total_trades'] > 0:
                results_comparison.append({
                    'Ticker': ticker,
                    'Trades': results['total_trades'],
                    'Win Rate%': results['win_rate'],
                    'Total PnL%': results['total_return_pct'],
                    'Profit Factor': results['profit_factor'],
                    'Max DD%': results['max_drawdown'],
                    'Sharpe': results['sharpe_ratio'],
                    'TP1 Hit%': results['tp1_hit_rate'],
                    'TP3 Hit%': results['tp3_hit_rate'],
                    'Trailing Exits': results['trailing_exits']
                })
        except Exception as e:
            print(f"   ❌ Error testing {ticker}: {e}")
            continue
    
    if len(results_comparison) > 0:
        print("\n" + "="*80)
        print("📊 COMPARISON TABLE")
        print("="*80)
        
        comparison_df = pd.DataFrame(results_comparison)
        print(comparison_df.to_string(index=False))
        
        # Find best
        best_ticker = comparison_df.loc[comparison_df['Total PnL%'].idxmax(), 'Ticker']
        best_pnl = comparison_df['Total PnL%'].max()
        
        print(f"\n🏆 BEST PERFORMER: {best_ticker} ({best_pnl:.2f}%)")
    
    return results_comparison


if __name__ == "__main__":
    # Check if yfinance is installed
    try:
        import yfinance as yf
        print("✅ yfinance installed")
    except ImportError:
        print("⚠️  yfinance not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
        print("✅ yfinance installed")
    
    # Test 1: Single stock (AAPL)
    print("\n🧪 TEST 1: AAPL with Adaptive Strategy")
    test_adaptive_strategy(ticker='AAPL', days=365, max_positions=5)
    
    # Test 2: Compare multiple stocks
    print("\n\n🧪 TEST 2: Compare Multiple Stocks")
    comparison = compare_stocks(
        tickers=['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'],
        days=365
    )
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)
