"""
Test Stock Pattern Recognition Strategy on 4H timeframe
Similar to Gold 1H but for stocks
"""

import pandas as pd
import numpy as np

from stock_pattern_recognition_strategy import StockPatternRecognitionStrategy
from stock_data_loader import generate_stock_data
from backtester import Backtester


def test_4h_pattern_recognition(
    ticker: str = "AAPL",
    days: int = 180,  # 6 months of 4H data
    fib_mode: str = 'standard'
):
    """
    Test Pattern Recognition on 4H timeframe
    
    Args:
        ticker: Stock ticker
        days: Number of days (will generate 6x candles per day)
        fib_mode: 'standard' (1.618) or 'aggressive' (2.618)
    """
    print("\n" + "="*80)
    print(f"📊 4H PATTERN RECOGNITION TEST - {ticker}")
    print("="*80)
    print(f"   Similar to Gold 1H Strategy (+186.91%)")
    print(f"   Fibonacci Mode: {fib_mode.upper()}")
    print(f"   Total Candles: {days * 6} (6 per day)")
    
    # Generate 4H data
    df = generate_stock_data(
        ticker=ticker,
        timeframe='4H',
        periods=days,
        initial_price=150.0,
        volatility=0.015  # Slightly lower than daily
    )
    
    # Create strategy with 4H-optimized parameters
    strategy = StockPatternRecognitionStrategy(
        timeframe='4H',
        fib_mode=fib_mode,
        pattern_tolerance=0.02,  # 2% tolerance
        swing_lookback=12,  # Smaller for 4H (like Gold 1H uses 20)
        pattern_cooldown=2,  # 2 candles (8 hours)
        require_trend_confirmation=False,  # More lenient like Gold
        min_candle_quality=20,
        min_volume_ratio=0.7,
        min_risk_pct=0.003  # 0.3% min risk (like Gold)
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
    
    # Detailed analysis
    if len(backtester.trades) > 0:
        print("\n" + "="*80)
        print("📋 PATTERN ANALYSIS")
        print("="*80)
        
        pattern_signals = df_signals[df_signals['signal_type'].str.contains('pattern', na=False)]
        
        if len(pattern_signals) > 0:
            print(f"\n✅ Found {len(pattern_signals)} pattern signals")
            
            # Pattern types
            print("\n📊 Pattern Distribution:")
            pattern_types = pattern_signals['signal_type'].value_counts()
            for pattern, count in pattern_types.items():
                pattern_name = pattern.replace('pattern_', '').replace('_', ' ').title()
                print(f"   {pattern_name}: {count}")
            
            # Show top patterns
            print("\n🎯 Top Pattern Signals:")
            print(pattern_signals[['signal', 'signal_type', 'entry_price', 'take_profit']].head(10).to_string())
        else:
            print("\n⚠️  No pattern signals found")
        
        # Trade analysis
        trades_df = pd.DataFrame([t.to_dict() for t in backtester.trades])
        
        print("\n" + "="*80)
        print("📊 TRADE METRICS")
        print("="*80)
        
        # Time-based analysis
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
        trades_df['hour'] = trades_df['entry_time'].dt.hour
        
        print(f"\nAverage Holding Time: {(trades_df['exit_time'] - trades_df['entry_time']).mean()}")
        print(f"Average Holding (hours): {((trades_df['exit_time'] - trades_df['entry_time']).mean().total_seconds() / 3600):.1f}h")
        
        # Best hours for entries
        print("\n📅 Best Entry Hours:")
        hourly_performance = trades_df.groupby('hour')['pnl_pct'].agg(['count', 'mean', 'sum'])
        hourly_performance = hourly_performance.sort_values('sum', ascending=False).head(5)
        print(hourly_performance.to_string())
        
        # Win/Loss streaks
        print(f"\nBest Trade: {trades_df['pnl_pct'].max():.2f}%")
        print(f"Worst Trade: {trades_df['pnl_pct'].min():.2f}%")
        print(f"Median Trade: {trades_df['pnl_pct'].median():.2f}%")
        
        # Direction performance
        print("\n📈 Direction Performance:")
        for direction in ['LONG', 'SHORT']:
            dir_trades = trades_df[trades_df['direction'] == direction]
            if len(dir_trades) > 0:
                win_rate = (dir_trades['pnl_pct'] > 0).sum() / len(dir_trades) * 100
                avg_pnl = dir_trades['pnl_pct'].mean()
                print(f"   {direction}: {len(dir_trades)} trades, {win_rate:.1f}% WR, {avg_pnl:.2f}% avg")
    
    return df_signals, results, backtester


def compare_timeframes(ticker: str = "AAPL"):
    """
    Compare 4H vs 1D pattern recognition
    """
    print("\n" + "="*80)
    print(f"⚖️  COMPARING 4H vs 1D TIMEFRAMES - {ticker}")
    print("="*80)
    
    results_comparison = []
    
    # Test 4H
    print("\n" + "="*80)
    print("1️⃣  TESTING 4H TIMEFRAME")
    print("="*80)
    
    df_4h, results_4h, bt_4h = test_4h_pattern_recognition(
        ticker=ticker,
        days=180,  # 6 months
        fib_mode='aggressive'  # Use 2.618 (best from previous tests)
    )
    
    results_comparison.append({
        'Timeframe': '4H',
        'Candles': len(df_4h),
        'Signals': (df_4h['signal'] != 0).sum(),
        'Trades': results_4h.get('total_trades', 0),
        'Win Rate%': results_4h.get('win_rate', 0),
        'Total PnL%': results_4h.get('total_return_pct', 0),
        'Profit Factor': results_4h.get('profit_factor', 0),
        'Max DD%': results_4h.get('max_drawdown', 0),
        'Avg PnL/Trade%': results_4h.get('total_return_pct', 0) / max(1, results_4h.get('total_trades', 1))
    })
    
    # Test 1D for comparison
    print("\n\n" + "="*80)
    print("2️⃣  TESTING 1D TIMEFRAME (for comparison)")
    print("="*80)
    
    from test_pattern_recognition import test_pattern_recognition
    df_1d, results_1d, bt_1d = test_pattern_recognition(
        ticker=ticker,
        timeframe='1D',
        periods=180,  # Same period
        fib_mode='aggressive'
    )
    
    results_comparison.append({
        'Timeframe': '1D',
        'Candles': len(df_1d),
        'Signals': (df_1d['signal'] != 0).sum(),
        'Trades': results_1d.get('total_trades', 0),
        'Win Rate%': results_1d.get('win_rate', 0),
        'Total PnL%': results_1d.get('total_return_pct', 0),
        'Profit Factor': results_1d.get('profit_factor', 0),
        'Max DD%': results_1d.get('max_drawdown', 0),
        'Avg PnL/Trade%': results_1d.get('total_return_pct', 0) / max(1, results_1d.get('total_trades', 1))
    })
    
    # Comparison
    print("\n" + "="*80)
    print("📊 TIMEFRAME COMPARISON")
    print("="*80)
    
    comparison_df = pd.DataFrame(results_comparison)
    print(comparison_df.to_string(index=False))
    
    # Determine winner
    best_timeframe = comparison_df.loc[comparison_df['Total PnL%'].idxmax(), 'Timeframe']
    best_pnl = comparison_df['Total PnL%'].max()
    
    print(f"\n🏆 WINNER: {best_timeframe}")
    print(f"   Total PnL: {best_pnl:.2f}%")
    
    # Annualized returns
    print("\n📅 Annualized Returns (estimated):")
    for _, row in comparison_df.iterrows():
        tf = row['Timeframe']
        pnl = row['Total PnL%']
        # 6 months data, so annualize
        annualized = pnl * 2
        print(f"   {tf}: {annualized:.2f}% per year")
    
    return comparison_df


if __name__ == "__main__":
    # Test 1: 4H with Fibonacci 1.618
    print("\n🧪 TEST 1: 4H Pattern Recognition (Fibonacci 1.618)")
    test_4h_pattern_recognition(
        ticker="AAPL",
        days=180,
        fib_mode='standard'
    )
    
    # Test 2: 4H with Fibonacci 2.618
    print("\n\n🧪 TEST 2: 4H Pattern Recognition (Fibonacci 2.618)")
    test_4h_pattern_recognition(
        ticker="AAPL",
        days=180,
        fib_mode='aggressive'
    )
    
    # Test 3: Compare timeframes
    print("\n\n🧪 TEST 3: Compare 4H vs 1D")
    comparison = compare_timeframes(ticker="AAPL")
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)
