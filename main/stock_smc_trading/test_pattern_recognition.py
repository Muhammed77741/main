"""
Test Stock Pattern Recognition Strategy
Based on WINNING Gold Pattern Recognition (+186.91%)
"""

import pandas as pd
import numpy as np

from stock_pattern_recognition_strategy import StockPatternRecognitionStrategy
from stock_data_loader import generate_stock_data
from backtester import Backtester


def test_pattern_recognition(
    ticker: str = "AAPL",
    timeframe: str = '1D',
    periods: int = 500,
    fib_mode: str = 'standard'
):
    """
    Test Pattern Recognition Strategy for stocks
    
    Args:
        ticker: Stock ticker
        timeframe: '1D' or '1W'
        periods: Number of periods
        fib_mode: 'standard' (1.618) or 'aggressive' (2.618)
    """
    print("\n" + "="*80)
    print(f"📊 STOCK PATTERN RECOGNITION TEST - {ticker} ({timeframe})")
    print("="*80)
    print(f"   Based on WINNING Gold Strategy (+186.91%)")
    print(f"   Fibonacci Mode: {fib_mode.upper()}")
    
    # Generate data
    df = generate_stock_data(
        ticker=ticker,
        timeframe=timeframe,
        periods=periods,
        initial_price=150.0,
        volatility=0.02  # 2% volatility
    )
    
    # Create strategy
    strategy = StockPatternRecognitionStrategy(
        timeframe=timeframe,
        fib_mode=fib_mode,
        pattern_tolerance=0.025,  # 2.5% tolerance (stocks less volatile)
        swing_lookback=15 if timeframe == '1D' else 8,  # Smaller lookback for stocks
        pattern_cooldown=3 if timeframe == '1D' else 1,  # Less strict cooldown
        require_trend_confirmation=False,  # Don't require SMA (too strict)
        min_candle_quality=20,  # Lower threshold
        min_volume_ratio=0.7  # More lenient
    )
    
    # Run strategy
    df_signals = strategy.run_strategy(df)
    
    # Backtest
    backtester = Backtester(
        initial_capital=10000,
        commission=0.001,
        slippage=0.0005,
        risk_per_trade=0.02
    )
    
    results = backtester.run(df_signals)
    backtester.print_results(results)
    
    # Show pattern signals
    if len(backtester.trades) > 0:
        print("\n" + "="*80)
        print("📋 PATTERN SIGNALS")
        print("="*80)
        
        pattern_signals = df_signals[df_signals['signal_type'].str.contains('pattern', na=False)]
        
        if len(pattern_signals) > 0:
            print(f"\nFound {len(pattern_signals)} pattern signals:")
            print(pattern_signals[['signal', 'signal_type', 'entry_price', 'stop_loss', 'take_profit']].head(20))
            
            # Count by pattern type
            print("\n📊 Pattern Type Distribution:")
            pattern_types = pattern_signals['signal_type'].value_counts()
            for pattern, count in pattern_types.items():
                print(f"   {pattern}: {count}")
        
        # Analyze trades
        trades_df = pd.DataFrame([t.to_dict() for t in backtester.trades])
        
        print("\n" + "="*80)
        print("📊 TRADE ANALYSIS")
        print("="*80)
        
        print(f"\nAverage Trade Duration: {(trades_df['exit_time'] - trades_df['entry_time']).mean()}")
        print(f"Best Trade: {trades_df['pnl_pct'].max():.2f}%")
        print(f"Worst Trade: {trades_df['pnl_pct'].min():.2f}%")
        
        # Win/Loss analysis
        winners = trades_df[trades_df['pnl_pct'] > 0]
        losers = trades_df[trades_df['pnl_pct'] < 0]
        
        print(f"\nWinning Trades: {len(winners)} ({len(winners)/len(trades_df)*100:.1f}%)")
        print(f"Losing Trades: {len(losers)} ({len(losers)/len(trades_df)*100:.1f}%)")
        
        if len(winners) > 0:
            print(f"Average Win: {winners['pnl_pct'].mean():.2f}%")
        if len(losers) > 0:
            print(f"Average Loss: {losers['pnl_pct'].mean():.2f}%")
    
    return df_signals, results, backtester


def compare_fibonacci_modes(ticker: str = "AAPL", timeframe: str = '1D'):
    """
    Compare Fibonacci 1.618 vs 2.618 (like Gold strategy)
    """
    print("\n" + "="*80)
    print(f"⚖️  COMPARING FIBONACCI MODES - {ticker} ({timeframe})")
    print("="*80)
    
    results_comparison = []
    
    for fib_mode in ['standard', 'aggressive']:
        print(f"\n{'='*80}")
        print(f"Testing {fib_mode.upper()} mode...")
        print(f"{'='*80}")
        
        df_signals, results, backtester = test_pattern_recognition(
            ticker=ticker,
            timeframe=timeframe,
            periods=500,
            fib_mode=fib_mode
        )
        
        results_comparison.append({
            'Mode': f"{fib_mode.upper()} ({1.618 if fib_mode == 'standard' else 2.618})",
            'Total PnL%': results.get('total_return_pct', 0),
            'Win Rate%': results.get('win_rate', 0),
            'Trades': results.get('total_trades', 0),
            'Profit Factor': results.get('profit_factor', 0),
            'Max DD%': results.get('max_drawdown', 0)
        })
    
    # Comparison table
    print("\n" + "="*80)
    print("📊 FIBONACCI MODE COMPARISON")
    print("="*80)
    
    comparison_df = pd.DataFrame(results_comparison)
    print(comparison_df.to_string(index=False))
    
    # Find best
    best_mode = comparison_df.loc[comparison_df['Total PnL%'].idxmax(), 'Mode']
    best_pnl = comparison_df['Total PnL%'].max()
    
    print(f"\n🏆 Best Mode: {best_mode}")
    print(f"   Total PnL: {best_pnl:.2f}%")
    
    return comparison_df


if __name__ == "__main__":
    # Test 1: Pattern Recognition with standard Fibonacci
    print("\n🧪 TEST 1: Pattern Recognition (Fibonacci 1.618)")
    test_pattern_recognition(
        ticker="AAPL",
        timeframe='1D',
        periods=500,
        fib_mode='standard'
    )
    
    # Test 2: Compare Fibonacci modes
    print("\n\n🧪 TEST 2: Compare Fibonacci 1.618 vs 2.618")
    comparison = compare_fibonacci_modes(ticker="AAPL", timeframe='1D')
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)
