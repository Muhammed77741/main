"""
Test Simple Trend Strategy on Multiple Stocks
Find which stocks/parameters work best
"""

import pandas as pd
import sys

from simple_trend_strategy import SimpleTrendStrategy, SimpleTrendBacktester
from stock_adaptive_strategy import get_real_stock_data


def test_single_stock(ticker: str, days: int = 730, params: dict = None):
    """Test on single stock"""
    print(f"\n{'='*80}")
    print(f"📊 Testing {ticker}")
    print(f"{'='*80}")
    
    # Get data
    df = get_real_stock_data(ticker, days=days)
    
    if len(df) < 300:
        print(f"   ⚠️  Not enough data")
        return None
    
    # Default params
    if params is None:
        params = {
            'tp_pct': 0.025,
            'sl_pct': 0.015,
            'min_adx': 25,
            'rsi_range': (40, 60)
        }
    
    # Run strategy
    strategy = SimpleTrendStrategy(timeframe='4H', **params)
    df_signals = strategy.run_strategy(df)
    
    # Backtest
    bt = SimpleTrendBacktester(initial_capital=10000, max_positions=2)
    results = bt.run(df_signals)
    bt.print_results(results)
    
    return results


def compare_all_stocks(tickers: list, days: int = 730):
    """Compare simple trend on all stocks"""
    print("\n" + "="*80)
    print("🔬 TESTING SIMPLE TREND ON MULTIPLE STOCKS")
    print("="*80)
    
    results_comp = []
    
    for ticker in tickers:
        try:
            results = test_single_stock(ticker, days=days)
            
            if results and results['total_trades'] > 0:
                # Calculate some extra metrics
                trades_df = pd.DataFrame(results['trades'])
                
                # Exit reason distribution
                exit_reasons = trades_df['exit_reason'].value_counts()
                tp_count = exit_reasons.get('TP', 0)
                trail_count = exit_reasons.get('TRAIL', 0)
                
                results_comp.append({
                    'Ticker': ticker,
                    'Trades': results['total_trades'],
                    'Win Rate%': results['win_rate'],
                    'Total PnL%': results['total_return_pct'],
                    'Profit Factor': results['profit_factor'],
                    'Avg Win $': results['avg_win'],
                    'Avg Loss $': results['avg_loss'],
                    'TP Exits': tp_count,
                    'Trail Exits': trail_count
                })
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    if len(results_comp) > 0:
        print("\n" + "="*80)
        print("📊 COMPARISON TABLE")
        print("="*80)
        
        comp_df = pd.DataFrame(results_comp)
        print(comp_df.to_string(index=False))
        
        # Analysis
        print(f"\n📈 ANALYSIS:")
        
        # Best by PnL
        best_pnl = comp_df.loc[comp_df['Total PnL%'].idxmax()]
        print(f"   Best PnL: {best_pnl['Ticker']} ({best_pnl['Total PnL%']:+.2f}%)")
        
        # Best by WR
        best_wr = comp_df.loc[comp_df['Win Rate%'].idxmax()]
        print(f"   Best WR: {best_wr['Ticker']} ({best_wr['Win Rate%']:.1f}%)")
        
        # Best by PF
        best_pf = comp_df.loc[comp_df['Profit Factor'].idxmax()]
        print(f"   Best PF: {best_pf['Ticker']} ({best_pf['Profit Factor']:.2f})")
        
        # Overall stats
        avg_pnl = comp_df['Total PnL%'].mean()
        avg_wr = comp_df['Win Rate%'].mean()
        profitable = (comp_df['Total PnL%'] > 0).sum()
        
        print(f"\n📊 OVERALL:")
        print(f"   Avg PnL: {avg_pnl:+.2f}%")
        print(f"   Avg WR: {avg_wr:.1f}%")
        print(f"   Profitable: {profitable}/{len(comp_df)}")
        
        # Conclusion
        if profitable >= len(comp_df) * 0.6 and avg_pnl > 10:
            print(f"\n   ✅✅ GREAT! Strategy works on most stocks!")
        elif profitable >= len(comp_df) * 0.5:
            print(f"\n   ✅ OK. Works on some stocks")
        else:
            print(f"\n   ❌ Strategy doesn't work consistently")
        
        # Show which exit type works best
        total_tp = comp_df['TP Exits'].sum()
        total_trail = comp_df['Trail Exits'].sum()
        print(f"\n🚪 EXIT ANALYSIS:")
        print(f"   TP exits: {total_tp}")
        print(f"   Trailing exits: {total_trail}")
        
        if total_tp > total_trail * 2:
            print(f"   💡 Fixed TP works better than trailing")
        elif total_trail > total_tp * 2:
            print(f"   💡 Trailing stop works better than fixed TP")
        else:
            print(f"   💡 Mixed results, both important")
    
    return results_comp


def test_parameter_variations(ticker: str = 'AAPL', days: int = 730):
    """Test different parameter sets to find best"""
    print("\n" + "="*80)
    print(f"🔬 PARAMETER OPTIMIZATION - {ticker}")
    print("="*80)
    
    param_sets = [
        {'name': 'Conservative', 'tp_pct': 0.020, 'sl_pct': 0.012, 'min_adx': 30, 'rsi_range': (45, 55)},
        {'name': 'Balanced', 'tp_pct': 0.025, 'sl_pct': 0.015, 'min_adx': 25, 'rsi_range': (40, 60)},
        {'name': 'Aggressive', 'tp_pct': 0.035, 'sl_pct': 0.020, 'min_adx': 20, 'rsi_range': (35, 65)},
        {'name': 'Tight SL', 'tp_pct': 0.025, 'sl_pct': 0.010, 'min_adx': 25, 'rsi_range': (40, 60)},
        {'name': 'Wide TP', 'tp_pct': 0.040, 'sl_pct': 0.015, 'min_adx': 25, 'rsi_range': (40, 60)},
    ]
    
    results_list = []
    
    for param_set in param_sets:
        name = param_set.pop('name')
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
        
        df = get_real_stock_data(ticker, days=days)
        strategy = SimpleTrendStrategy(timeframe='4H', **param_set)
        df_signals = strategy.run_strategy(df)
        
        bt = SimpleTrendBacktester(initial_capital=10000, max_positions=2)
        results = bt.run(df_signals)
        
        if results['total_trades'] > 0:
            results_list.append({
                'Params': name,
                'Trades': results['total_trades'],
                'WR%': results['win_rate'],
                'PnL%': results['total_return_pct'],
                'PF': results['profit_factor']
            })
    
    if len(results_list) > 0:
        print("\n" + "="*80)
        print("📊 PARAMETER COMPARISON")
        print("="*80)
        
        results_df = pd.DataFrame(results_list)
        print(results_df.to_string(index=False))
        
        best = results_df.loc[results_df['PnL%'].idxmax()]
        print(f"\n🏆 BEST: {best['Params']} ({best['PnL%']:+.2f}%)")
    
    return results_list


if __name__ == "__main__":
    # Test 1: All stocks with default params
    print("\n🧪 TEST 1: Simple Trend on Multiple Stocks")
    comparison = compare_all_stocks(
        tickers=['NVDA', 'AAPL', 'MSFT', 'TSLA', 'GOOGL'],
        days=730
    )
    
    # Test 2: Parameter optimization (if time)
    print("\n\n🧪 TEST 2: Parameter Optimization (AAPL)")
    param_results = test_parameter_variations(ticker='AAPL', days=730)
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)
    
    # Final recommendation
    if comparison:
        comp_df = pd.DataFrame(comparison)
        best_stock = comp_df.loc[comp_df['Total PnL%'].idxmax(), 'Ticker']
        best_pnl = comp_df['Total PnL%'].max()
        
        print(f"\n💡 FINAL RECOMMENDATION:")
        if best_pnl > 15:
            print(f"   ✅ Use Simple Trend on {best_stock} ({best_pnl:+.2f}%)")
            print(f"   ✅ Strategy works!")
        elif best_pnl > 0:
            print(f"   ⚠️  Marginal profit ({best_pnl:+.2f}%)")
            print(f"   Consider longer timeframe or different approach")
        else:
            print(f"   ❌ Simple trend doesn't work on these stocks")
            print(f"   Recommendation: Try buy & hold or fundamental-based")
