"""
Simple test for Stock Long-Term Strategy
Простой тест стратегии для акций
"""

import pandas as pd
import numpy as np

from stock_long_term_strategy import StockLongTermStrategy
from stock_data_loader import generate_stock_data
from backtester import Backtester


def simple_daily_test():
    """Simple test for daily strategy"""
    print("\n" + "="*80)
    print("📊 SIMPLE DAILY STRATEGY TEST")
    print("="*80)
    
    # Generate data with lower volatility
    df = generate_stock_data(
        ticker="AAPL",
        timeframe='1D',
        periods=365,  # 1 year
        initial_price=150.0,
        volatility=0.015  # 1.5% volatility
    )
    
    # Create strategy with relaxed parameters
    strategy = StockLongTermStrategy(
        timeframe='1D',
        risk_reward_ratio=2.0,  # Lower R:R
        risk_per_trade=0.02,
        swing_length=10,  # Shorter swings
        volume_lookback=2,  # Less strict volume
        min_candle_quality=25,  # Lower quality threshold
        use_fibonacci_tp=False,  # Use fixed R:R first
        min_volume_ratio=0.8  # More lenient volume
    )
    
    # Generate signals
    df_signals = strategy.run_strategy(df)
    
    # Count signals
    total_signals = (df_signals['signal'] != 0).sum()
    print(f"\n✅ Generated {total_signals} signals")
    
    if total_signals == 0:
        print("⚠️  No signals - strategy too strict. Adjusting parameters...")
        
        # Try even more relaxed
        strategy = StockLongTermStrategy(
            timeframe='1D',
            risk_reward_ratio=1.8,
            risk_per_trade=0.02,
            swing_length=5,
            volume_lookback=1,
            min_candle_quality=20,
            use_fibonacci_tp=False,
            min_volume_ratio=0.5
        )
        
        df_signals = strategy.run_strategy(df)
        total_signals = (df_signals['signal'] != 0).sum()
        print(f"\n✅ Generated {total_signals} signals with relaxed parameters")
    
    if total_signals > 0:
        # Run backtest
        print("\n" + "="*80)
        print("🎯 RUNNING BACKTEST")
        print("="*80)
        
        backtester = Backtester(
            initial_capital=10000,
            commission=0.001,
            slippage=0.0005,
            risk_per_trade=0.02
        )
        
        results = backtester.run(df_signals)
        backtester.print_results(results)
        
        # Show some example signals
        print("\n" + "="*80)
        print("📋 EXAMPLE SIGNALS")
        print("="*80)
        
        signals_df = df_signals[df_signals['signal'] != 0][
            ['signal', 'entry_price', 'stop_loss', 'take_profit', 'signal_reason', 'position_type']
        ].head(10)
        
        print(signals_df.to_string())
        
        # Calculate some metrics
        if len(backtester.trades) > 0:
            trades_df = pd.DataFrame([t.to_dict() for t in backtester.trades])
            
            print("\n" + "="*80)
            print("📊 TRADE ANALYSIS")
            print("="*80)
            
            print(f"\nAverage Trade Duration: {(trades_df['exit_time'] - trades_df['entry_time']).mean()}")
            print(f"Best Trade: {trades_df['pnl_pct'].max():.2f}%")
            print(f"Worst Trade: {trades_df['pnl_pct'].min():.2f}%")
            
            # Exit reasons
            print("\nExit Reasons:")
            print(trades_df['exit_reason'].value_counts())
            
            # Direction breakdown
            print("\nDirection Breakdown:")
            print(trades_df['direction'].value_counts())
        
        return df_signals, results, backtester
    else:
        print("\n❌ Still no signals generated. Check data or strategy logic.")
        return df_signals, None, None


def simple_weekly_test():
    """Simple test for weekly strategy"""
    print("\n" + "="*80)
    print("📊 SIMPLE WEEKLY STRATEGY TEST")
    print("="*80)
    
    # Generate data
    df = generate_stock_data(
        ticker="MSFT",
        timeframe='1W',
        periods=52,  # 1 year
        initial_price=300.0,
        volatility=0.02
    )
    
    # Create strategy with relaxed parameters
    strategy = StockLongTermStrategy(
        timeframe='1W',
        risk_reward_ratio=2.5,
        risk_per_trade=0.02,
        swing_length=5,  # Shorter for weekly
        volume_lookback=1,
        min_candle_quality=20,
        use_fibonacci_tp=False,
        min_volume_ratio=0.7
    )
    
    # Generate signals
    df_signals = strategy.run_strategy(df)
    
    # Count signals
    total_signals = (df_signals['signal'] != 0).sum()
    print(f"\n✅ Generated {total_signals} signals")
    
    if total_signals > 0:
        # Run backtest
        backtester = Backtester(
            initial_capital=10000,
            commission=0.001,
            slippage=0.0005,
            risk_per_trade=0.02
        )
        
        results = backtester.run(df_signals)
        backtester.print_results(results)
        
        return df_signals, results, backtester
    else:
        print("\n⚠️  No signals generated for weekly timeframe")
        return df_signals, None, None


if __name__ == "__main__":
    # Test daily
    print("\n🧪 TEST 1: DAILY STRATEGY")
    daily_df, daily_results, daily_bt = simple_daily_test()
    
    # Test weekly
    print("\n\n🧪 TEST 2: WEEKLY STRATEGY")
    weekly_df, weekly_results, weekly_bt = simple_weekly_test()
    
    # Summary
    print("\n\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    if daily_results:
        print(f"\n✅ Daily Strategy:")
        print(f"   Trades: {daily_results['total_trades']}")
        print(f"   Win Rate: {daily_results['win_rate']:.1f}%")
        print(f"   Total Return: {daily_results['total_return_pct']:.2f}%")
    else:
        print("\n❌ Daily Strategy: No trades")
    
    if weekly_results:
        print(f"\n✅ Weekly Strategy:")
        print(f"   Trades: {weekly_results['total_trades']}")
        print(f"   Win Rate: {weekly_results['win_rate']:.1f}%")
        print(f"   Total Return: {weekly_results['total_return_pct']:.2f}%")
    else:
        print("\n❌ Weekly Strategy: No trades")
    
    print("\n" + "="*80)
    print("✅ TESTS COMPLETED")
    print("="*80)
