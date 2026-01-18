#!/usr/bin/env python3
"""
Cryptocurrency Backtesting Script with CLI Interface
Supports backtesting trading strategies on crypto price data
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import sys


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Backtest cryptocurrency trading strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input btc_prices.csv --output results.csv --crypto BTC
  %(prog)s --input eth_data.csv --output eth_results.csv --crypto ETH
        """
    )
    
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to input CSV file containing price data'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Path to output CSV file for backtest results'
    )
    
    parser.add_argument(
        '--crypto',
        type=str,
        required=True,
        help='Cryptocurrency symbol (e.g., BTC, ETH, SOL)'
    )
    
    return parser.parse_args()


def load_data(input_path):
    """Load price data from CSV file"""
    try:
        df = pd.read_csv(input_path)
        print(f"✓ Loaded {len(df)} rows from {input_path}")
        return df
    except FileNotFoundError:
        print(f"✗ Error: File '{input_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        sys.exit(1)


def calculate_indicators(df):
    """Calculate technical indicators for trading strategy"""
    # Simple Moving Averages
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    
    # Exponential Moving Average
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df


def generate_signals(df):
    """Generate buy/sell signals based on strategy"""
    df['signal'] = 0
    
    # Buy signal: SMA_20 crosses above SMA_50 and RSI < 70
    df.loc[(df['SMA_20'] > df['SMA_50']) & 
           (df['SMA_20'].shift(1) <= df['SMA_50'].shift(1)) & 
           (df['RSI'] < 70), 'signal'] = 1
    
    # Sell signal: SMA_20 crosses below SMA_50 or RSI > 80
    df.loc[((df['SMA_20'] < df['SMA_50']) & 
            (df['SMA_20'].shift(1) >= df['SMA_50'].shift(1))) | 
           (df['RSI'] > 80), 'signal'] = -1
    
    return df


def backtest_strategy(df, initial_capital=10000):
    """Execute backtest and calculate returns"""
    capital = initial_capital
    position = 0
    trades = []
    
    df['portfolio_value'] = initial_capital
    
    for i in range(len(df)):
        if df['signal'].iloc[i] == 1 and position == 0:
            # Buy
            position = capital / df['close'].iloc[i]
            trades.append({
                'type': 'BUY',
                'price': df['close'].iloc[i],
                'date': df['timestamp'].iloc[i] if 'timestamp' in df.columns else i
            })
        elif df['signal'].iloc[i] == -1 and position > 0:
            # Sell
            capital = position * df['close'].iloc[i]
            trades.append({
                'type': 'SELL',
                'price': df['close'].iloc[i],
                'date': df['timestamp'].iloc[i] if 'timestamp' in df.columns else i
            })
            position = 0
        
        # Calculate current portfolio value
        if position > 0:
            df.loc[df.index[i], 'portfolio_value'] = position * df['close'].iloc[i]
        else:
            df.loc[df.index[i], 'portfolio_value'] = capital
    
    # Calculate metrics
    final_value = df['portfolio_value'].iloc[-1]
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    return df, trades, final_value, total_return


def save_results(df, output_path, crypto, final_value, total_return, trades):
    """Save backtest results to CSV"""
    try:
        # Save main results
        df.to_csv(output_path, index=False)
        
        # Create summary
        summary = {
            'Cryptocurrency': crypto,
            'Initial Capital': 10000,
            'Final Portfolio Value': final_value,
            'Total Return (%)': total_return,
            'Number of Trades': len(trades),
            'Timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        summary_path = output_path.replace('.csv', '_summary.csv')
        pd.DataFrame([summary]).to_csv(summary_path, index=False)
        
        print(f"✓ Results saved to {output_path}")
        print(f"✓ Summary saved to {summary_path}")
        
    except Exception as e:
        print(f"✗ Error saving results: {e}")
        sys.exit(1)


def main():
    """Main execution function"""
    print("=" * 60)
    print("Cryptocurrency Backtesting System")
    print("=" * 60)
    
    # Parse CLI arguments
    args = parse_arguments()
    
    print(f"\nConfiguration:")
    print(f"  Input File: {args.input}")
    print(f"  Output File: {args.output}")
    print(f"  Crypto Symbol: {args.crypto}")
    print()
    
    # Load data
    print("Loading data...")
    df = load_data(args.input)
    
    # Calculate indicators
    print("Calculating technical indicators...")
    df = calculate_indicators(df)
    
    # Generate signals
    print("Generating trading signals...")
    df = generate_signals(df)
    
    # Run backtest
    print("Running backtest...")
    df, trades, final_value, total_return = backtest_strategy(df)
    
    # Display results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Cryptocurrency: {args.crypto}")
    print(f"Initial Capital: $10,000.00")
    print(f"Final Portfolio Value: ${final_value:,.2f}")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Number of Trades: {len(trades)}")
    print("=" * 60)
    
    # Save results
    print("\nSaving results...")
    save_results(df, args.output, args.crypto, final_value, total_return, trades)
    
    print("\n✓ Backtest completed successfully!\n")


if __name__ == "__main__":
    main()
