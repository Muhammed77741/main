#!/usr/bin/env python3
"""
BTC Signal Analysis Script
Analyzes if BTC signals were generated in the last 7 days
Helps diagnose if the trading bot is working correctly

Usage:
    # Download and analyze live data from Binance (requires internet)
    python check_btc_signals.py --days 7 --symbol BTC/USDT
    
    # Analyze from local CSV file (offline mode)
    python check_btc_signals.py --file BTC_data.csv --symbol BTC/USDT
    
    # Generate sample data for testing (offline mode)
    python check_btc_signals.py --sample --days 7

Purpose:
    This script helps answer the question: "Were there any BTC positions/signals 
    in the last 2 days?" It downloads BTC data, runs the same strategy as the 
    live bot, and shows all generated signals with detailed analysis.
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import ccxt
import os

# Add trading_bots to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_bots'))

from shared.pattern_recognition_strategy import PatternRecognitionStrategy


def generate_sample_btc_data(days=7, start_price=95000):
    """
    Generate sample BTC data for testing (offline mode)
    Creates realistic-looking OHLCV data with trends and patterns
    
    Args:
        days: Number of days to generate
        start_price: Starting BTC price
    
    Returns:
        pandas.DataFrame with OHLCV data
    """
    print(f"\n{'='*80}")
    print(f"🧪 Generating sample BTC data (OFFLINE MODE)")
    print(f"{'='*80}")
    print(f"   Period: {days} days")
    print(f"   Start price: ${start_price:.2f}")
    
    try:
        from datetime import datetime, timedelta
        import pandas as pd
        import numpy as np
        
        # Generate timestamps (1 hour intervals)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        timestamps = pd.date_range(start=start_time, end=end_time, freq='1h')
        
        # Generate price data with trends and volatility
        np.random.seed(42)  # For reproducibility
        num_candles = len(timestamps)
        
        # Create price movements with trend + noise
        trend = np.linspace(0, 5000, num_candles)  # Slow upward trend
        volatility = np.random.randn(num_candles) * 500  # Random volatility
        sine_wave = np.sin(np.linspace(0, 4*np.pi, num_candles)) * 2000  # Cyclical pattern
        
        close_prices = start_price + trend + volatility + sine_wave
        
        # Generate OHLCV
        data = []
        for i in range(num_candles):
            close = close_prices[i]
            
            # Random high/low around close (create candles)
            high = close + np.random.uniform(50, 300)
            low = close - np.random.uniform(50, 300)
            open_price = np.random.uniform(low, high)
            
            # Ensure OHLC logic
            high = max(high, close, open_price)
            low = min(low, close, open_price)
            
            # Random volume
            volume = np.random.uniform(1000, 5000)
            
            data.append({
                'timestamp': timestamps[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        print(f"✅ Generated {len(df)} candles")
        print(f"   First candle: {df.index[0].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Last candle: {df.index[-1].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        print(f"   ⚠️  NOTE: This is SAMPLE data for testing only!")
        
        return df
    
    except Exception as e:
        print(f"❌ Error generating sample data: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_btc_data_from_csv(csv_file):
    """
    Load BTC data from local CSV file (offline mode)
    
    Expected CSV format:
    - timestamp,open,high,low,close,volume
    - OR: date,time,open,high,low,close,volume
    
    Args:
        csv_file: Path to CSV file
    
    Returns:
        pandas.DataFrame with OHLCV data
    """
    print(f"\n{'='*80}")
    print(f"📂 Loading BTC data from CSV (OFFLINE MODE)")
    print(f"{'='*80}")
    print(f"   File: {csv_file}")
    
    try:
        import pandas as pd
        import os
        
        if not os.path.exists(csv_file):
            print(f"❌ File not found: {csv_file}")
            return None
        
        # Try to read CSV
        df = pd.read_csv(csv_file)
        
        # Handle different timestamp formats
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        elif 'date' in df.columns and 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'])
            df.set_index('timestamp', inplace=True)
        elif 'datetime' in df.columns:
            df['timestamp'] = pd.to_datetime(df['datetime'])
            df.set_index('timestamp', inplace=True)
        else:
            # Assume first column is datetime
            df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
            df.set_index(df.columns[0], inplace=True)
            df.index.name = 'timestamp'
        
        # Ensure we have required columns
        required = ['open', 'high', 'low', 'close']
        missing = [col for col in required if col not in df.columns]
        if missing:
            print(f"❌ Missing required columns: {missing}")
            print(f"   Available columns: {df.columns.tolist()}")
            return None
        
        # Add volume if missing
        if 'volume' not in df.columns:
            df['volume'] = 0
            print("⚠️  Volume column missing - using 0")
        
        print(f"✅ Loaded {len(df)} candles")
        print(f"   First candle: {df.index[0].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Last candle: {df.index[-1].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        
        return df
    
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        import traceback
        traceback.print_exc()
        return None


def download_btc_data(symbol='BTC/USDT', timeframe='1h', days=7):
    """
    Download BTC data from Binance
    
    Args:
        symbol: Trading symbol (default: BTC/USDT)
        timeframe: Timeframe (default: 1h)
        days: Number of days to download (default: 7)
    
    Returns:
        pandas.DataFrame with OHLCV data
    """
    print(f"\n{'='*80}")
    print(f"📊 Downloading {symbol} data from Binance")
    print(f"{'='*80}")
    print(f"   Timeframe: {timeframe}")
    print(f"   Period: Last {days} days")
    
    try:
        # Initialize Binance
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Download data
        print("\n🔄 Downloading data...")
        since = int(start_time.timestamp() * 1000)
        
        all_candles = []
        while True:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not candles:
                break
            
            all_candles.extend(candles)
            since = candles[-1][0] + 1
            
            # Stop if we've reached the end time
            if candles[-1][0] >= int(end_time.timestamp() * 1000):
                break
        
        # Convert to DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Filter to exact date range
        df = df[(df.index >= start_time) & (df.index <= end_time)]
        
        print(f"✅ Downloaded {len(df)} candles")
        print(f"   First candle: {df.index[0].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Last candle: {df.index[-1].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        
        return df
    
    except Exception as e:
        print(f"❌ Error downloading data: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_signals(df, symbol='BTC/USDT'):
    """
    Analyze signals using PatternRecognitionStrategy
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Trading symbol
    
    Returns:
        DataFrame with signals
    """
    print(f"\n{'='*80}")
    print(f"🔍 Analyzing signals for {symbol}")
    print(f"{'='*80}")
    
    try:
        # Initialize strategy (same as live bot)
        print("📊 Initializing PatternRecognitionStrategy...")
        strategy = PatternRecognitionStrategy(fib_mode='standard')
        
        # Run strategy
        print("🔄 Running strategy on historical data...")
        df_signals = strategy.run_strategy(df)
        
        # Find signals
        buy_signals = df_signals[df_signals['signal'] == 1]
        sell_signals = df_signals[df_signals['signal'] == -1]
        
        total_signals = len(buy_signals) + len(sell_signals)
        
        print(f"\n{'='*80}")
        print(f"📈 SIGNAL ANALYSIS RESULTS")
        print(f"{'='*80}")
        print(f"   Total signals: {total_signals}")
        print(f"   BUY signals: {len(buy_signals)}")
        print(f"   SELL signals: {len(sell_signals)}")
        
        # Analyze by date
        if total_signals > 0:
            all_signals = pd.concat([buy_signals, sell_signals]).sort_index()
            
            print(f"\n{'='*80}")
            print(f"📅 SIGNALS BY DATE")
            print(f"{'='*80}")
            
            for idx, row in all_signals.iterrows():
                signal_type = "BUY 📈" if row['signal'] == 1 else "SELL 📉"
                print(f"\n   {idx.strftime('%Y-%m-%d %H:%M:%S')} - {signal_type}")
                print(f"      Price: ${row['close']:.2f}")
                if 'sl' in row and not pd.isna(row['sl']):
                    print(f"      Stop Loss: ${row['sl']:.2f}")
                if 'tp' in row and not pd.isna(row['tp']):
                    print(f"      Take Profit: ${row['tp']:.2f}")
                if 'entry_reason' in row and not pd.isna(row['entry_reason']):
                    print(f"      Reason: {row['entry_reason']}")
            
            # Check last 2 days specifically
            print(f"\n{'='*80}")
            print(f"📊 LAST 2 DAYS ANALYSIS")
            print(f"{'='*80}")
            
            two_days_ago = datetime.now() - timedelta(days=2)
            recent_signals = all_signals[all_signals.index >= two_days_ago]
            
            print(f"   Signals in last 2 days: {len(recent_signals)}")
            
            if len(recent_signals) == 0:
                print(f"   ❌ NO SIGNALS in last 2 days!")
                print(f"   Last signal was: {all_signals.index[-1].strftime('%Y-%m-%d %H:%M:%S')}")
                days_since_last = (datetime.now() - all_signals.index[-1]).days
                print(f"   Days since last signal: {days_since_last}")
            else:
                print(f"   ✅ Signals found in last 2 days:")
                for idx, row in recent_signals.iterrows():
                    signal_type = "BUY 📈" if row['signal'] == 1 else "SELL 📉"
                    print(f"      {idx.strftime('%Y-%m-%d %H:%M:%S')} - {signal_type} @ ${row['close']:.2f}")
        else:
            print(f"\n   ❌ NO SIGNALS GENERATED in the entire {len(df_signals)} period!")
            print(f"   This could mean:")
            print(f"      1. Market conditions don't meet strategy criteria")
            print(f"      2. No clear patterns detected")
            print(f"      3. Strategy filters are too strict")
        
        # Market condition summary
        print(f"\n{'='*80}")
        print(f"📊 MARKET CONDITION SUMMARY")
        print(f"{'='*80}")
        
        last_candle = df_signals.iloc[-1]
        print(f"   Current Price: ${last_candle['close']:.2f}")
        print(f"   24h Change: {((last_candle['close'] - df_signals.iloc[-24]['close']) / df_signals.iloc[-24]['close'] * 100):.2f}%")
        
        if 'regime' in df_signals.columns:
            print(f"   Market Regime: {last_candle['regime'] if 'regime' in last_candle and not pd.isna(last_candle['regime']) else 'Unknown'}")
        
        if 'atr' in df_signals.columns:
            print(f"   Volatility (ATR): {last_candle['atr']:.2f}" if not pd.isna(last_candle['atr']) else "   Volatility: N/A")
        
        return df_signals
    
    except Exception as e:
        print(f"❌ Error analyzing signals: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_detailed_report(df_signals, symbol='BTC/USDT', output_file='btc_signal_report.csv'):
    """
    Save detailed report to CSV
    
    Args:
        df_signals: DataFrame with signals
        symbol: Trading symbol
        output_file: Output CSV file
    """
    try:
        # Save all data with signals
        df_signals.to_csv(output_file)
        print(f"\n✅ Detailed report saved to: {output_file}")
        print(f"   Open this file in Excel to analyze all data points")
        
        # Also save just the signals
        signals_only = df_signals[df_signals['signal'] != 0]
        if len(signals_only) > 0:
            signals_file = output_file.replace('.csv', '_signals_only.csv')
            signals_only.to_csv(signals_file)
            print(f"   Signals only saved to: {signals_file}")
    
    except Exception as e:
        print(f"⚠️  Could not save report: {e}")


def plot_signals(df_signals, symbol='BTC/USDT', output_file='btc_signals_chart.png'):
    """
    Plot price chart with signals
    
    Args:
        df_signals: DataFrame with signals
        symbol: Trading symbol
        output_file: Output image file
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        print(f"\n📊 Creating chart visualization...")
        
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Plot price
        ax.plot(df_signals.index, df_signals['close'], label='Price', color='black', linewidth=1)
        
        # Plot buy signals
        buy_signals = df_signals[df_signals['signal'] == 1]
        if len(buy_signals) > 0:
            ax.scatter(buy_signals.index, buy_signals['close'], 
                      color='green', marker='^', s=200, label='BUY Signal', zorder=5)
        
        # Plot sell signals
        sell_signals = df_signals[df_signals['signal'] == -1]
        if len(sell_signals) > 0:
            ax.scatter(sell_signals.index, sell_signals['close'], 
                      color='red', marker='v', s=200, label='SELL Signal', zorder=5)
        
        # Highlight last 2 days
        two_days_ago = datetime.now() - timedelta(days=2)
        ax.axvline(x=two_days_ago, color='blue', linestyle='--', linewidth=2, alpha=0.5, label='Last 2 Days')
        
        # Format
        ax.set_title(f'{symbol} - Signal Analysis (Last 7 Days)', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Price (USDT)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150)
        print(f"✅ Chart saved to: {output_file}")
        
    except Exception as e:
        print(f"⚠️  Could not create chart: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='BTC Signal Analysis Script - Check if BTC signals are being generated',
        epilog='Example: python check_btc_signals.py --days 7 --symbol BTC/USDT'
    )
    
    # Data source options (mutually exclusive)
    data_group = parser.add_mutually_exclusive_group()
    data_group.add_argument('--file', type=str,
                           help='Load data from CSV file (offline mode)')
    data_group.add_argument('--sample', action='store_true',
                           help='Generate sample data for testing (offline mode)')
    
    # Analysis options
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to analyze (default: 7)')
    parser.add_argument('--symbol', type=str, default='BTC/USDT',
                       help='Trading symbol (default: BTC/USDT)')
    parser.add_argument('--output', type=str, default='btc_signal_report',
                       help='Output file prefix (default: btc_signal_report)')
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"🤖 BTC SIGNAL ANALYSIS SCRIPT")
    print(f"{'='*80}")
    print(f"   Symbol: {args.symbol}")
    print(f"   Analysis Period: Last {args.days} days")
    print(f"   Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Get data based on source
    if args.sample:
        print(f"\n   Mode: SAMPLE DATA (offline testing)")
        df = generate_sample_btc_data(days=args.days)
    elif args.file:
        print(f"\n   Mode: CSV FILE (offline)")
        df = load_btc_data_from_csv(args.file)
    else:
        print(f"\n   Mode: LIVE DATA from Binance (online)")
        df = download_btc_data(symbol=args.symbol, timeframe='1h', days=args.days)
    
    if df is None or len(df) == 0:
        print("\n❌ Failed to get data. Exiting.")
        print("\n💡 Try one of these modes:")
        print("   --sample          Generate sample data for testing")
        print("   --file data.csv   Load data from CSV file")
        print("   (no args)         Download live data from Binance (requires internet)")
        sys.exit(1)
    
    # Step 2: Analyze signals
    df_signals = analyze_signals(df, symbol=args.symbol)
    if df_signals is None:
        print("\n❌ Failed to analyze signals. Exiting.")
        sys.exit(1)
    
    # Step 3: Save report
    csv_file = f"{args.output}.csv"
    save_detailed_report(df_signals, symbol=args.symbol, output_file=csv_file)
    
    # Step 4: Plot chart
    chart_file = f"{args.output}_chart.png"
    plot_signals(df_signals, symbol=args.symbol, output_file=chart_file)
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"✅ ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"\n📋 Summary:")
    
    total_signals = len(df_signals[df_signals['signal'] != 0])
    two_days_ago = datetime.now() - timedelta(days=2)
    recent_signals = df_signals[(df_signals['signal'] != 0) & (df_signals.index >= two_days_ago)]
    
    print(f"   Total signals in {args.days} days: {total_signals}")
    print(f"   Signals in last 2 days: {len(recent_signals)}")
    
    if len(recent_signals) == 0 and total_signals > 0:
        last_signal = df_signals[df_signals['signal'] != 0].index[-1]
        print(f"   ⚠️  No signals in last 2 days")
        print(f"   Last signal: {last_signal.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Days ago: {(datetime.now() - last_signal).days}")
        print(f"\n💡 This could mean:")
        print(f"      - Market is in consolidation (no clear patterns)")
        print(f"      - Volatility is too low")
        print(f"      - No breakouts or reversals detected")
    elif len(recent_signals) > 0:
        print(f"   ✅ Bot IS generating signals normally!")
        print(f"\n📊 Recent signals:")
        for idx, row in recent_signals.iterrows():
            signal_type = "BUY 📈" if row['signal'] == 1 else "SELL 📉"
            print(f"      {idx.strftime('%Y-%m-%d %H:%M')} - {signal_type} @ ${row['close']:.2f}")
    else:
        print(f"   ❌ NO signals in entire {args.days}-day period!")
        print(f"\n💡 Possible reasons:")
        print(f"      - Strategy filters are too strict")
        print(f"      - Market conditions don't meet criteria")
        print(f"      - Check strategy settings (fib_mode, tolerances)")
    
    print(f"\n📁 Files created:")
    print(f"   - {csv_file} (detailed data with all indicators)")
    signals_file = csv_file.replace('.csv', '_signals_only.csv')
    if os.path.exists(signals_file):
        print(f"   - {signals_file} (signals only)")
    print(f"   - {chart_file} (price chart with signal markers)")
    
    print(f"\n{'='*80}")
    print(f"📖 HOW TO USE THIS SCRIPT:")
    print(f"{'='*80}")
    print(f"\n1. ONLINE MODE (download live BTC data):")
    print(f"   python check_btc_signals.py --days 7")
    print(f"\n2. OFFLINE MODE (use CSV file):")
    print(f"   python check_btc_signals.py --file your_btc_data.csv")
    print(f"\n3. TEST MODE (generate sample data):")
    print(f"   python check_btc_signals.py --sample --days 7")
    print(f"\n4. Check different symbols:")
    print(f"   python check_btc_signals.py --symbol ETH/USDT --days 7")
    print(f"\n{'='*80}")


if __name__ == "__main__":
    main()
