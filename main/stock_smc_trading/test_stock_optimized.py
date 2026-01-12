"""
Test Stock Optimized Strategy on Real Data

Conservative approach:
- Small TP (0.5%/1.0%/1.5%)
- Tight SL (0.8-1.2%)
- Pattern confirmation required
- Max 3 positions
- Target: 60%+ win rate, steady gains
"""

import pandas as pd
import numpy as np
import sys

from stock_optimized_strategy import StockOptimizedStrategy
from stock_adaptive_strategy import get_real_stock_data
from adaptive_backtester import AdaptiveBacktester


def test_stock_optimized(
    ticker: str = 'NVDA',
    days: int = 365,
    require_pattern: bool = True
):
    """
    Test stock-optimized strategy
    
    Args:
        ticker: Stock ticker
        days: Days of history
        require_pattern: Require pattern confirmation
    """
    print("\n" + "="*80)
    print(f"💎 STOCK OPTIMIZED TEST - {ticker} (REAL DATA)")
    print("="*80)
    print(f"   Strategy: Conservative, pattern-confirmed")
    print(f"   Target: 60%+ WR, small consistent gains")
    print(f"   TP: 0.5%/1.0%/1.5% (vs Gold's 1.5%/2.8%/4.5%)")
    print(f"   SL: 0.8-1.2% (vs Gold's 2-4%)")
    
    # Get real data
    df = get_real_stock_data(ticker=ticker, days=days)
    
    if len(df) < 100:
        print(f"\n⚠️  Not enough data")
        return None, None, None
    
    # Create optimized strategy
    strategy = StockOptimizedStrategy(
        timeframe='4H',
        max_positions=3,
        require_pattern_confirmation=require_pattern
    )
    
    # Run strategy
    df_signals = strategy.run_strategy(df)
    
    # Count signals
    total_signals = (df_signals['signal'] != 0).sum()
    
    if total_signals == 0:
        print(f"\n❌ No signals generated!")
        print(f"   Try:")
        print(f"   1. Longer period (days=730)")
        print(f"   2. Disable pattern requirement (require_pattern=False)")
        print(f"   3. Different ticker")
        return df_signals, None, None
    
    # Backtest
    backtester = AdaptiveBacktester(
        initial_capital=10000,
        risk_per_trade=0.02,
        max_positions=3,
        commission=0.001,
        slippage=0.0005
    )
    
    results = backtester.run(df_signals)
    backtester.print_results(results)
    
    # Analysis
    if results['total_trades'] > 0:
        print_optimized_analysis(results, df_signals, ticker)
    
    return df_signals, results, backtester


def print_optimized_analysis(results: dict, df: pd.DataFrame, ticker: str):
    """Print optimized strategy analysis"""
    print("\n" + "="*80)
    print("📊 STOCK OPTIMIZED ANALYSIS")
    print("="*80)
    
    trades_df = pd.DataFrame(results['trades'])
    
    # Trade frequency
    if len(df) > 0:
        days_tested = (df.index[-1] - df.index[0]).days
        trades_per_day = results['total_trades'] / days_tested
        print(f"\n📅 TRADE FREQUENCY:")
        print(f"   Days tested: {days_tested}")
        print(f"   Total trades: {results['total_trades']}")
        print(f"   Trades/day: {trades_per_day:.2f}")
        print(f"   Trades/week: {trades_per_day*7:.1f}")
        print(f"   Trades/month: {trades_per_day*30:.1f}")
    
    # Pattern distribution
    if 'signal_type' in df.columns:
        pattern_signals = df[df['signal'] != 0]
        if len(pattern_signals) > 0 and 'signal_type' in pattern_signals.columns:
            print(f"\n🎯 PATTERN DISTRIBUTION:")
            patterns = pattern_signals['signal_type'].value_counts().head(5)
            for pattern, count in patterns.items():
                print(f"   {pattern}: {count}")
    
    # Exit analysis
    print(f"\n🚪 EXIT ANALYSIS:")
    exit_counts = trades_df['exit_reason'].value_counts()
    for reason, count in exit_counts.items():
        pct = count / len(trades_df) * 100
        avg_pnl = trades_df[trades_df['exit_reason'] == reason]['pnl_pct'].mean()
        print(f"   {reason}: {count} ({pct:.1f}%), avg: {avg_pnl:+.2f}%")
    
    # TP hit rates
    print(f"\n🎯 TP HIT RATES:")
    print(f"   TP1: {results['tp1_hit_rate']:.1f}% (target: 60%+)")
    print(f"   TP2: {results['tp2_hit_rate']:.1f}% (target: 30%+)")
    print(f"   TP3: {results['tp3_hit_rate']:.1f}% (target: 10%+)")
    
    tp1_ok = results['tp1_hit_rate'] >= 60
    tp2_ok = results['tp2_hit_rate'] >= 30
    tp3_ok = results['tp3_hit_rate'] >= 10
    
    if tp1_ok and tp2_ok and tp3_ok:
        print(f"   ✅ All TP levels good!")
    elif tp1_ok:
        print(f"   ⚠️  TP1 good, but TP2/TP3 need improvement")
    else:
        print(f"   ❌ TP levels too aggressive, consider smaller targets")
    
    # Win rate check
    print(f"\n📊 QUALITY METRICS:")
    wr = results['win_rate']
    pf = results['profit_factor']
    
    print(f"   Win Rate: {wr:.1f}% (target: 60%+)")
    print(f"   Profit Factor: {pf:.2f} (target: 1.5+)")
    
    if wr >= 60 and pf >= 1.5:
        print(f"   ✅ Excellent quality!")
    elif wr >= 55 and pf >= 1.3:
        print(f"   ✅ Good quality")
    elif wr >= 50 and pf >= 1.1:
        print(f"   ⚠️  Acceptable, can be improved")
    else:
        print(f"   ❌ Needs optimization")
    
    # Best/worst
    print(f"\n🏆 TOP 5 TRADES:")
    best = trades_df.nlargest(5, 'pnl_pct')[['entry_time', 'exit_reason', 'pnl_pct', 'tp1_hit', 'tp2_hit', 'tp3_hit']]
    best['entry_time'] = pd.to_datetime(best['entry_time']).dt.strftime('%Y-%m-%d')
    print(best.to_string(index=False))
    
    print(f"\n📉 WORST 5 TRADES:")
    worst = trades_df.nsmallest(5, 'pnl_pct')[['entry_time', 'exit_reason', 'pnl_pct']]
    worst['entry_time'] = pd.to_datetime(worst['entry_time']).dt.strftime('%Y-%m-%d')
    print(worst.to_string(index=False))
    
    # Monthly performance
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    trades_df['month'] = trades_df['entry_time'].dt.to_period('M')
    
    monthly = trades_df.groupby('month')['pnl_pct'].agg(['count', 'sum', 'mean'])
    profitable_months = (monthly['sum'] > 0).sum()
    total_months = len(monthly)
    
    print(f"\n📅 MONTHLY PERFORMANCE:")
    print(f"   Profitable: {profitable_months}/{total_months} ({profitable_months/total_months*100:.1f}%)")
    print(f"   Best month: +{monthly['sum'].max():.2f}%")
    print(f"   Worst month: {monthly['sum'].min():.2f}%")
    
    # Annualized
    if len(df) > 0:
        days = (df.index[-1] - df.index[0]).days
        if days > 0:
            annual = results['total_return_pct'] * (365 / days)
            print(f"\n📈 ANNUALIZED:")
            print(f"   Return: {annual:+.2f}%/year")
            
            if annual > 30:
                print(f"   ✅ Excellent!")
            elif annual > 15:
                print(f"   ✅ Good")
            elif annual > 0:
                print(f"   ⚠️  Positive but low")
            else:
                print(f"   ❌ Negative")


def compare_optimized_vs_adaptive(ticker: str = 'NVDA', days: int = 365):
    """
    Compare optimized vs adaptive strategy
    
    Args:
        ticker: Stock ticker
        days: Days to test
    """
    print("\n" + "="*80)
    print(f"⚖️  OPTIMIZED vs ADAPTIVE COMPARISON - {ticker}")
    print("="*80)
    
    results_comp = []
    
    # Test 1: Stock Optimized
    print(f"\n1️⃣  STOCK OPTIMIZED (Conservative)")
    df1, res1, bt1 = test_stock_optimized(ticker=ticker, days=days, require_pattern=True)
    
    if res1 and res1['total_trades'] > 0:
        results_comp.append({
            'Strategy': 'Stock Optimized',
            'Trades': res1['total_trades'],
            'Win Rate%': res1['win_rate'],
            'Total PnL%': res1['total_return_pct'],
            'Profit Factor': res1['profit_factor'],
            'Max DD%': res1['max_drawdown'],
            'TP1 Hit%': res1['tp1_hit_rate'],
            'TP3 Hit%': res1['tp3_hit_rate']
        })
    
    # Test 2: Adaptive (aggressive)
    print(f"\n\n2️⃣  ADAPTIVE (Aggressive, Gold-style)")
    
    from test_adaptive_real_data import test_adaptive_strategy
    df2, res2, bt2 = test_adaptive_strategy(ticker=ticker, days=days, max_positions=5)
    
    if res2 and res2['total_trades'] > 0:
        results_comp.append({
            'Strategy': 'Adaptive (Gold)',
            'Trades': res2['total_trades'],
            'Win Rate%': res2['win_rate'],
            'Total PnL%': res2['total_return_pct'],
            'Profit Factor': res2['profit_factor'],
            'Max DD%': res2['max_drawdown'],
            'TP1 Hit%': res2['tp1_hit_rate'],
            'TP3 Hit%': res2['tp3_hit_rate']
        })
    
    # Compare
    if len(results_comp) > 0:
        print("\n" + "="*80)
        print("📊 STRATEGY COMPARISON")
        print("="*80)
        
        comp_df = pd.DataFrame(results_comp)
        print(comp_df.to_string(index=False))
        
        if len(comp_df) == 2:
            print(f"\n💡 INSIGHTS:")
            
            opt_pnl = comp_df.iloc[0]['Total PnL%']
            ada_pnl = comp_df.iloc[1]['Total PnL%']
            
            opt_wr = comp_df.iloc[0]['Win Rate%']
            ada_wr = comp_df.iloc[1]['Win Rate%']
            
            opt_trades = comp_df.iloc[0]['Trades']
            ada_trades = comp_df.iloc[1]['Trades']
            
            print(f"   Optimized: {opt_trades} trades, {opt_wr:.1f}% WR, {opt_pnl:+.2f}% PnL")
            print(f"   Adaptive:  {ada_trades} trades, {ada_wr:.1f}% WR, {ada_pnl:+.2f}% PnL")
            
            if opt_pnl > ada_pnl and opt_wr > ada_wr:
                print(f"\n   ✅ OPTIMIZED WINS! Better PnL AND WR")
            elif opt_pnl > ada_pnl:
                print(f"\n   ✅ OPTIMIZED better PnL ({opt_pnl-ada_pnl:+.2f}%)")
            elif opt_wr > ada_wr:
                print(f"\n   ✅ OPTIMIZED better WR (+{opt_wr-ada_wr:.1f}%)")
            else:
                print(f"\n   ⚠️  Adaptive has advantages")
    
    return results_comp


def test_multiple_stocks_optimized(
    tickers: list = ['NVDA', 'AAPL', 'MSFT', 'TSLA', 'GOOGL'],
    days: int = 365
):
    """Test optimized strategy on multiple stocks"""
    print("\n" + "="*80)
    print(f"🔬 TESTING STOCK OPTIMIZED ON MULTIPLE TICKERS")
    print("="*80)
    
    results = []
    
    for ticker in tickers:
        print(f"\n{'='*80}")
        print(f"Testing {ticker}...")
        print(f"{'='*80}")
        
        try:
            df, res, bt = test_stock_optimized(ticker=ticker, days=days, require_pattern=True)
            
            if res and res['total_trades'] > 0:
                results.append({
                    'Ticker': ticker,
                    'Trades': res['total_trades'],
                    'Win Rate%': res['win_rate'],
                    'Total PnL%': res['total_return_pct'],
                    'Profit Factor': res['profit_factor'],
                    'Max DD%': res['max_drawdown'],
                    'Sharpe': res['sharpe_ratio']
                })
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    if len(results) > 0:
        print("\n" + "="*80)
        print("📊 MULTI-TICKER RESULTS")
        print("="*80)
        
        results_df = pd.DataFrame(results)
        print(results_df.to_string(index=False))
        
        # Best ticker
        best = results_df.loc[results_df['Total PnL%'].idxmax()]
        print(f"\n🏆 BEST: {best['Ticker']} ({best['Total PnL%']:+.2f}%)")
        
        # Overall stats
        avg_wr = results_df['Win Rate%'].mean()
        avg_pnl = results_df['Total PnL%'].mean()
        positive_tickers = (results_df['Total PnL%'] > 0).sum()
        
        print(f"\n📊 OVERALL:")
        print(f"   Avg Win Rate: {avg_wr:.1f}%")
        print(f"   Avg PnL: {avg_pnl:+.2f}%")
        print(f"   Positive tickers: {positive_tickers}/{len(results_df)}")
    
    return results


if __name__ == "__main__":
    # Test 1: Single stock (NVDA - best from previous test)
    print("\n🧪 TEST 1: NVDA with Stock Optimized")
    test_stock_optimized(ticker='NVDA', days=365, require_pattern=True)
    
    # Test 2: Compare with Adaptive
    print("\n\n🧪 TEST 2: Optimized vs Adaptive")
    compare_optimized_vs_adaptive(ticker='NVDA', days=365)
    
    # Test 3: Multiple stocks
    print("\n\n🧪 TEST 3: Multiple Stocks")
    test_multiple_stocks_optimized(
        tickers=['NVDA', 'AAPL', 'MSFT', 'TSLA', 'GOOGL'],
        days=365
    )
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)
