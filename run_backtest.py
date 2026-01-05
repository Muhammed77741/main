"""
Unified Backtest Runner
Запускает бэктест на имеющихся данных с выбранной стратегией

Использует V13 стратегию (Fibonacci TP Only) как наиболее современную
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import argparse

# Add smc_trading_strategy to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'smc_trading_strategy'))

from simplified_smc_strategy import SimplifiedSMCStrategy
from backtest_v13_fib_tp_only import FibonacciTPOnlyBacktest


def find_data_files():
    """Find all available CSV data files"""
    data_files = []
    
    # Check root directory
    for file in os.listdir('.'):
        if file.endswith('.csv') and 'XAUUSD' in file:
            size_mb = os.path.getsize(file) / (1024 * 1024)
            data_files.append({
                'path': file,
                'name': file,
                'size_mb': size_mb
            })
    
    # Check smc_trading_strategy directory
    smc_dir = 'smc_trading_strategy'
    if os.path.exists(smc_dir):
        for file in os.listdir(smc_dir):
            if file.endswith('.csv') and 'XAUUSD' in file:
                path = os.path.join(smc_dir, file)
                size_mb = os.path.getsize(path) / (1024 * 1024)
                data_files.append({
                    'path': path,
                    'name': file,
                    'size_mb': size_mb
                })
    
    return sorted(data_files, key=lambda x: x['size_mb'], reverse=True)


def load_and_prepare_data(file_path):
    """Load and prepare data for backtesting"""
    print(f"\n📂 Loading data from {file_path}...")
    
    # Try different encodings
    encodings = ['utf-8', 'utf-16', 'latin-1']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    if df is None:
        raise ValueError(f"Could not read file with any of these encodings: {encodings}")
    
    # Check if we have the expected columns
    if 'datetime' not in df.columns:
        # Might be MT5 format without proper headers
        # First column is datetime, then open, high, low, close, volume
        col_names = df.columns.tolist()
        if len(col_names) >= 6:
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume'] + col_names[6:]
        elif len(col_names) >= 5:
            # If only 5 columns, assume no volume or extra columns
            df.columns = ['datetime', 'open', 'high', 'low', 'close'] + col_names[5:]
    
    # Convert datetime
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    
    # Sort by datetime to ensure chronological order
    df = df.sort_index()
    
    # Add active hours if not present
    if 'is_active' not in df.columns:
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_active'] = df['is_london'] | df['is_ny']
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    print(f"   Duration: {(df.index[-1] - df.index[0]).days} days")
    
    return df


def print_backtest_summary(trades_df, data_file):
    """Print comprehensive backtest summary"""
    
    print(f"\n{'='*80}")
    print(f"📊 BACKTEST SUMMARY")
    print(f"{'='*80}")
    print(f"Data file: {data_file}")
    print(f"Strategy: V13 - Fibonacci TP Only")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if trades_df is None or len(trades_df) == 0:
        print("\n❌ No trades executed")
        return
    
    total_trades = len(trades_df)
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl_pct = trades_df['pnl_pct'].sum()
    total_pnl_points = trades_df['pnl_points'].sum()
    
    avg_pnl = trades_df['pnl_pct'].mean()
    avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
    avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0
    
    max_win = trades_df['pnl_pct'].max()
    max_loss = trades_df['pnl_pct'].min()
    
    avg_duration = trades_df['duration_hours'].mean()
    
    print(f"\n📈 PERFORMANCE METRICS")
    print(f"   Total Trades: {total_trades}")
    print(f"   Wins: {wins} ({win_rate:.1f}%)")
    print(f"   Losses: {losses} ({100-win_rate:.1f}%)")
    print(f"   Total PnL: {total_pnl_pct:+.2f}%")
    print(f"   Total Points: {total_pnl_points:+.1f}п")
    print(f"   Average PnL: {avg_pnl:+.3f}%")
    print(f"   Average Win: {avg_win:+.2f}%")
    print(f"   Average Loss: {avg_loss:+.2f}%")
    print(f"   Max Win: {max_win:+.2f}%")
    print(f"   Max Loss: {max_loss:+.2f}%")
    
    if avg_loss != 0:
        # avg_loss is already negative, so use abs() for proper profit factor
        profit_factor = (avg_win * wins) / (abs(avg_loss) * losses)
        print(f"   Profit Factor: {profit_factor:.2f}")
    
    print(f"\n⏱️  DURATION METRICS")
    print(f"   Average Duration: {avg_duration:.1f} hours ({avg_duration/24:.1f} days)")
    print(f"   Min Duration: {trades_df['duration_hours'].min():.1f} hours")
    print(f"   Max Duration: {trades_df['duration_hours'].max():.1f} hours")
    
    # TP Analysis
    tp1_hits = trades_df['tp1_hit'].sum()
    tp2_hits = trades_df['tp2_hit'].sum()
    tp3_hits = trades_df['tp3_hit'].sum()
    
    print(f"\n🎯 TP HIT RATES")
    print(f"   TP1 (Fib 127.2%): {tp1_hits}/{total_trades} ({tp1_hits/total_trades*100:.1f}%)")
    print(f"   TP2 (Fib 161.8%): {tp2_hits}/{total_trades} ({tp2_hits/total_trades*100:.1f}%)")
    print(f"   TP3 (Fib 200.0%): {tp3_hits}/{total_trades} ({tp3_hits/total_trades*100:.1f}%)")
    
    # Exit type analysis
    print(f"\n🚪 EXIT TYPES")
    exit_counts = trades_df['exit_type'].value_counts()
    for exit_type, count in exit_counts.items():
        pct = (count / total_trades * 100)
        print(f"   {exit_type}: {count} ({pct:.1f}%)")
    
    # Direction analysis
    print(f"\n📊 DIRECTION BREAKDOWN")
    for direction in ['LONG', 'SHORT']:
        dir_trades = trades_df[trades_df['direction'] == direction]
        if len(dir_trades) > 0:
            dir_wins = len(dir_trades[dir_trades['pnl_pct'] > 0])
            dir_wr = (dir_wins / len(dir_trades) * 100)
            dir_pnl = dir_trades['pnl_pct'].sum()
            print(f"   {direction}: {len(dir_trades)} trades, {dir_wr:.1f}% WR, {dir_pnl:+.2f}% PnL")
    
    # Regime analysis
    if 'regime' in trades_df.columns:
        print(f"\n🌊 REGIME BREAKDOWN")
        for regime in ['TREND', 'RANGE']:
            reg_trades = trades_df[trades_df['regime'] == regime]
            if len(reg_trades) > 0:
                reg_wins = len(reg_trades[reg_trades['pnl_pct'] > 0])
                reg_wr = (reg_wins / len(reg_trades) * 100)
                reg_pnl = reg_trades['pnl_pct'].sum()
                print(f"   {regime}: {len(reg_trades)} trades, {reg_wr:.1f}% WR, {reg_pnl:+.2f}% PnL")
    
    # TP Source analysis
    if 'tp_source' in trades_df.columns:
        print(f"\n🌟 TP SOURCE ANALYSIS")
        fib_trades = trades_df[trades_df['tp_source'] == 'FIB']
        v9_trades = trades_df[trades_df['tp_source'] == 'V9']
        
        if len(fib_trades) > 0:
            fib_wins = len(fib_trades[fib_trades['pnl_pct'] > 0])
            fib_wr = (fib_wins / len(fib_trades) * 100)
            fib_pnl = fib_trades['pnl_pct'].sum()
            print(f"   Fibonacci TP: {len(fib_trades)} trades ({fib_wr:.1f}% WR, {fib_pnl:+.2f}% PnL)")
        
        if len(v9_trades) > 0:
            v9_wins = len(v9_trades[v9_trades['pnl_pct'] > 0])
            v9_wr = (v9_wins / len(v9_trades) * 100)
            v9_pnl = v9_trades['pnl_pct'].sum()
            print(f"   V9 Fallback: {len(v9_trades)} trades ({v9_wr:.1f}% WR, {v9_pnl:+.2f}% PnL)")
    
    print(f"\n{'='*80}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run backtest on available data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run on default (largest) data file
  python run_backtest.py
  
  # Run on specific file
  python run_backtest.py --file XAUUSD_MT5_20240425_20260102.csv
  
  # List available data files
  python run_backtest.py --list
        """
    )
    parser.add_argument(
        '--file',
        type=str,
        help='CSV file to use (default: largest available)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available data files and exit'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='backtest_results.csv',
        help='Output file for results (default: backtest_results.csv)'
    )
    
    args = parser.parse_args()
    
    # Find available data files
    data_files = find_data_files()
    
    if len(data_files) == 0:
        print("❌ No data files found!")
        print("   Looking for CSV files with 'XAUUSD' in name")
        return 1
    
    # List files if requested
    if args.list:
        print("\n📂 Available data files:")
        for i, file in enumerate(data_files, 1):
            print(f"   {i}. {file['name']} ({file['size_mb']:.2f} MB)")
        return 0
    
    # Select file to use
    if args.file:
        # Find specified file
        selected_file = None
        for file in data_files:
            if file['name'] == args.file or file['path'] == args.file:
                selected_file = file
                break
        
        if selected_file is None:
            print(f"❌ File not found: {args.file}")
            print("\nAvailable files:")
            for file in data_files:
                print(f"   - {file['name']}")
            return 1
    else:
        # Use largest file by default
        selected_file = data_files[0]
        print(f"\n📊 Using largest data file: {selected_file['name']} ({selected_file['size_mb']:.2f} MB)")
    
    print(f"\n{'='*80}")
    print(f"🚀 STARTING BACKTEST")
    print(f"{'='*80}")
    
    # Load and prepare data
    df = load_and_prepare_data(selected_file['path'])
    
    # Create strategy instance
    print(f"\n🧠 Initializing SMC Strategy...")
    strategy = SimplifiedSMCStrategy()
    
    # Create backtest instance
    print(f"\n🎯 Initializing V13 Backtest (Fibonacci TP Only)...")
    backtest = FibonacciTPOnlyBacktest(
        spread_points=2.0,
        commission_points=0.5,
        swap_per_day=-0.3
    )
    
    # Run backtest
    print(f"\n{'='*80}")
    print(f"▶️  RUNNING BACKTEST")
    print(f"{'='*80}")
    
    trades_df = backtest.backtest(df, strategy)
    
    # Print summary
    print_backtest_summary(trades_df, selected_file['name'])
    
    # Save results
    if trades_df is not None and len(trades_df) > 0:
        trades_df.to_csv(args.output, index=False)
        print(f"\n💾 Results saved to: {args.output}")
        print(f"   Total trades: {len(trades_df)}")
    
    print(f"\n✅ Backtest completed successfully!")
    print(f"{'='*80}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
