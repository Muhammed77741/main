"""
Test 4H Pattern Recognition with Swing Trading (3-7 days hold)
Optimized for stock trading with longer holding periods
"""

import pandas as pd
import numpy as np

from stock_pattern_recognition_strategy import StockPatternRecognitionStrategy
from stock_data_loader import generate_stock_data
from backtester import Backtester


def test_swing_trading_4h(
    ticker: str = "AAPL",
    days: int = 180,
    min_hold_candles: int = 18,  # 3 days * 6 candles/day = 18
    max_hold_candles: int = 42,  # 7 days * 6 candles/day = 42
    fib_mode: str = 'aggressive'
):
    """
    Test 4H with swing trading parameters (3-7 days hold)
    
    Args:
        ticker: Stock ticker
        days: Number of days of data
        min_hold_candles: Minimum candles to hold (18 = 3 days on 4H)
        max_hold_candles: Maximum candles to hold (42 = 7 days on 4H)
        fib_mode: 'standard' or 'aggressive'
    """
    print("\n" + "="*80)
    print(f"📊 4H SWING TRADING TEST - {ticker}")
    print("="*80)
    print(f"   Target Hold Time: 3-7 days")
    print(f"   Min Hold: {min_hold_candles} candles ({min_hold_candles/6:.1f} days)")
    print(f"   Max Hold: {max_hold_candles} candles ({max_hold_candles/6:.1f} days)")
    print(f"   Fibonacci Mode: {fib_mode.upper()}")
    
    # Generate 4H data
    df = generate_stock_data(
        ticker=ticker,
        timeframe='4H',
        periods=days,
        initial_price=150.0,
        volatility=0.015
    )
    
    # Create strategy with swing parameters
    strategy = StockPatternRecognitionStrategy(
        timeframe='4H',
        fib_mode=fib_mode,
        pattern_tolerance=0.02,
        swing_lookback=12,
        pattern_cooldown=3,  # More selective entries
        require_trend_confirmation=False,
        min_candle_quality=25,
        min_volume_ratio=0.8,
        min_risk_pct=0.004,  # 0.4% min risk (tighter for swing)
        long_only=True  # Only LONG for stocks
    )
    
    # Run strategy
    df_signals = strategy.run_strategy(df)
    
    # Add swing trading exit logic
    df_signals = add_swing_exits(
        df_signals, 
        min_hold=min_hold_candles,
        max_hold=max_hold_candles
    )
    
    # Backtest with swing parameters
    backtester = Backtester(
        initial_capital=10000,
        commission=0.001,
        slippage=0.0005,
        risk_per_trade=0.02  # 2% risk per trade
    )
    
    results = backtester.run(df_signals)
    backtester.print_results(results)
    
    # Detailed swing analysis
    if len(backtester.trades) > 0:
        print("\n" + "="*80)
        print("📊 SWING TRADING ANALYSIS")
        print("="*80)
        
        trades_df = pd.DataFrame([t.to_dict() for t in backtester.trades])
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
        trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
        trades_df['hold_duration'] = trades_df['exit_time'] - trades_df['entry_time']
        trades_df['hold_days'] = trades_df['hold_duration'].dt.total_seconds() / 86400
        
        # Hold time distribution
        print("\n⏱️  Holding Time Statistics:")
        print(f"   Average: {trades_df['hold_days'].mean():.1f} days")
        print(f"   Median: {trades_df['hold_days'].median():.1f} days")
        print(f"   Min: {trades_df['hold_days'].min():.1f} days")
        print(f"   Max: {trades_df['hold_days'].max():.1f} days")
        
        # Trades by hold duration
        trades_3_5 = trades_df[(trades_df['hold_days'] >= 3) & (trades_df['hold_days'] <= 5)]
        trades_5_7 = trades_df[(trades_df['hold_days'] >= 5) & (trades_df['hold_days'] <= 7)]
        trades_7plus = trades_df[trades_df['hold_days'] > 7]
        
        print("\n📊 Distribution by Hold Period:")
        print(f"   3-5 days: {len(trades_3_5)} trades, avg PnL: {trades_3_5['pnl_pct'].mean():.2f}%")
        print(f"   5-7 days: {len(trades_5_7)} trades, avg PnL: {trades_5_7['pnl_pct'].mean():.2f}%")
        print(f"   7+ days: {len(trades_7plus)} trades, avg PnL: {trades_7plus['pnl_pct'].mean():.2f}%")
        
        # Exit reasons
        print("\n🚪 Exit Reasons:")
        exit_reasons = trades_df['exit_reason'].value_counts()
        for reason, count in exit_reasons.items():
            pct = count / len(trades_df) * 100
            avg_pnl = trades_df[trades_df['exit_reason'] == reason]['pnl_pct'].mean()
            print(f"   {reason}: {count} ({pct:.1f}%), avg PnL: {avg_pnl:.2f}%")
        
        # Performance by entry day of week
        trades_df['entry_dow'] = trades_df['entry_time'].dt.day_name()
        print("\n📅 Best Entry Days:")
        dow_perf = trades_df.groupby('entry_dow')['pnl_pct'].agg(['count', 'mean', 'sum'])
        dow_perf = dow_perf.sort_values('sum', ascending=False)
        print(dow_perf.to_string())
        
        # Win/Loss by hold period
        print("\n📈 Win Rate by Hold Period:")
        for period, label in [(3, 5, '3-5d'), (5, 7, '5-7d'), (7, 100, '7+d')]:
            period_trades = trades_df[(trades_df['hold_days'] >= period[0] if isinstance(period, tuple) else False)]
            if isinstance(period, tuple):
                period_trades = trades_df[(trades_df['hold_days'] >= period) & (trades_df['hold_days'] <= label)]
                period_label = f"{period}-{label} days"
            if len(period_trades) > 0:
                wr = (period_trades['pnl_pct'] > 0).sum() / len(period_trades) * 100
                print(f"   {label}: {wr:.1f}% ({len(period_trades)} trades)")
        
        # Best trades
        print("\n🏆 Top 5 Trades:")
        top_trades = trades_df.nlargest(5, 'pnl_pct')[['entry_time', 'hold_days', 'pnl_pct', 'exit_reason']]
        top_trades['entry_time'] = top_trades['entry_time'].dt.strftime('%Y-%m-%d')
        print(top_trades.to_string(index=False))
    
    return df_signals, results, backtester


def add_swing_exits(df, min_hold=18, max_hold=42):
    """
    Add swing trading exit logic
    - Min hold: Don't exit before min_hold candles
    - Max hold: Force exit after max_hold candles
    """
    print(f"\n⏱️  Adding Swing Exit Logic:")
    print(f"   Min hold: {min_hold} candles ({min_hold/6:.1f} days)")
    print(f"   Max hold: {max_hold} candles ({max_hold/6:.1f} days)")
    
    # Track position entry index
    df['swing_entry_idx'] = 0
    df['swing_min_hold'] = False
    df['swing_max_hold'] = False
    
    in_position = False
    entry_idx = 0
    
    for i in range(len(df)):
        # New entry
        if df['signal'].iloc[i] != 0 and not in_position:
            in_position = True
            entry_idx = i
            df.loc[df.index[i], 'swing_entry_idx'] = i
        
        # In position
        elif in_position:
            hold_time = i - entry_idx
            df.loc[df.index[i], 'swing_entry_idx'] = entry_idx
            
            # Min hold reached
            if hold_time >= min_hold:
                df.loc[df.index[i], 'swing_min_hold'] = True
            
            # Max hold reached - force exit
            if hold_time >= max_hold:
                df.loc[df.index[i], 'swing_max_hold'] = True
                # Set opposite signal to force exit
                current_pos = 1 if df['signal'].iloc[entry_idx] > 0 else -1
                df.loc[df.index[i], 'signal'] = -current_pos
                in_position = False
            
            # Check if position was closed
            if df['signal'].iloc[i] != 0:
                in_position = False
    
    # Count exits
    max_hold_exits = df['swing_max_hold'].sum()
    print(f"   Added {max_hold_exits} max-hold exits")
    
    return df


def compare_hold_periods(ticker: str = "AAPL"):
    """
    Compare different holding periods
    """
    print("\n" + "="*80)
    print(f"⚖️  COMPARING HOLD PERIODS - {ticker}")
    print("="*80)
    
    results_comparison = []
    
    # Test 1: 3-5 days (conservative)
    print("\n1️⃣  TESTING 3-5 DAYS HOLD")
    df1, res1, bt1 = test_swing_trading_4h(
        ticker=ticker,
        days=180,
        min_hold_candles=18,  # 3 days
        max_hold_candles=30,  # 5 days
        fib_mode='aggressive'
    )
    
    results_comparison.append({
        'Hold Period': '3-5 days',
        'Trades': res1.get('total_trades', 0),
        'Win Rate%': res1.get('win_rate', 0),
        'Total PnL%': res1.get('total_return_pct', 0),
        'Profit Factor': res1.get('profit_factor', 0),
        'Max DD%': res1.get('max_drawdown', 0),
        'Avg PnL/Trade%': res1.get('total_return_pct', 0) / max(1, res1.get('total_trades', 1))
    })
    
    # Test 2: 3-7 days (target)
    print("\n\n2️⃣  TESTING 3-7 DAYS HOLD")
    df2, res2, bt2 = test_swing_trading_4h(
        ticker=ticker,
        days=180,
        min_hold_candles=18,  # 3 days
        max_hold_candles=42,  # 7 days
        fib_mode='aggressive'
    )
    
    results_comparison.append({
        'Hold Period': '3-7 days',
        'Trades': res2.get('total_trades', 0),
        'Win Rate%': res2.get('win_rate', 0),
        'Total PnL%': res2.get('total_return_pct', 0),
        'Profit Factor': res2.get('profit_factor', 0),
        'Max DD%': res2.get('max_drawdown', 0),
        'Avg PnL/Trade%': res2.get('total_return_pct', 0) / max(1, res2.get('total_trades', 1))
    })
    
    # Test 3: 5-10 days (longer swing)
    print("\n\n3️⃣  TESTING 5-10 DAYS HOLD")
    df3, res3, bt3 = test_swing_trading_4h(
        ticker=ticker,
        days=180,
        min_hold_candles=30,  # 5 days
        max_hold_candles=60,  # 10 days
        fib_mode='aggressive'
    )
    
    results_comparison.append({
        'Hold Period': '5-10 days',
        'Trades': res3.get('total_trades', 0),
        'Win Rate%': res3.get('win_rate', 0),
        'Total PnL%': res3.get('total_return_pct', 0),
        'Profit Factor': res3.get('profit_factor', 0),
        'Max DD%': res3.get('max_drawdown', 0),
        'Avg PnL/Trade%': res3.get('total_return_pct', 0) / max(1, res3.get('total_trades', 1))
    })
    
    # Comparison
    print("\n" + "="*80)
    print("📊 HOLD PERIOD COMPARISON")
    print("="*80)
    
    comparison_df = pd.DataFrame(results_comparison)
    print(comparison_df.to_string(index=False))
    
    # Determine winner
    best_period = comparison_df.loc[comparison_df['Total PnL%'].idxmax(), 'Hold Period']
    best_pnl = comparison_df['Total PnL%'].max()
    best_pf = comparison_df.loc[comparison_df['Profit Factor'].idxmax(), 'Hold Period']
    
    print(f"\n🏆 BEST BY TOTAL PNL: {best_period} ({best_pnl:.2f}%)")
    print(f"🎯 BEST BY PROFIT FACTOR: {best_pf}")
    
    return comparison_df


if __name__ == "__main__":
    # Test 1: 3-7 days (target)
    print("\n🧪 TEST 1: 3-7 Days Swing Trading")
    test_swing_trading_4h(
        ticker="AAPL",
        days=180,
        min_hold_candles=18,
        max_hold_candles=42,
        fib_mode='aggressive'
    )
    
    # Test 2: Compare different hold periods
    print("\n\n🧪 TEST 2: Compare Hold Periods")
    comparison = compare_hold_periods(ticker="AAPL")
    
    print("\n" + "="*80)
    print("✅ ALL SWING TRADING TESTS COMPLETED")
    print("="*80)
