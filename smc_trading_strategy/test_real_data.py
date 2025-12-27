"""
Test All Strategies on REAL XAUUSD Data
Compare results with synthetic data performance
"""

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import sys

# Import strategies
from intraday_gold_strategy import MultiSignalGoldStrategy
from fibonacci_1618_strategy import Fibonacci1618Strategy
from pattern_recognition_strategy import PatternRecognitionStrategy


def load_real_xauusd_data(file_path='XAUUSD_historical_data.csv'):
    """
    Load real XAUUSD historical data from CSV

    Expected format:
    Date,Open,High,Low,Close,Change(Pips),Change(%)
    12/26/2025 00:00,4494.87,4497.59,4492.37,4497.13,226,0.05,
    """
    print("=" * 70)
    print("LOADING REAL XAUUSD DATA")
    print("=" * 70)

    # Read CSV (skip first row - it's a title)
    # The CSV has trailing commas which creates an extra empty column
    df = pd.read_csv(file_path, skiprows=1, index_col=0)

    print(f"\n📊 Raw data loaded: {len(df)} rows")

    # The index contains the actual Date values
    # The column 'Date' actually contains Open values
    # Let's reconstruct properly
    df = df.reset_index()

    # Current columns: index, Date, Open, High, Low, Close, Change(Pips), Change(%)
    # Actual meaning: Date, Open, High, Low, Close, ?, ?, ?
    # Let's just keep what we need
    df.columns = ['Date_str', 'Open', 'High', 'Low', 'Close', 'extra1', 'extra2', 'extra3']

    # Keep only OHLC
    df = df[['Date_str', 'Open', 'High', 'Low', 'Close']]

    print(f"   Columns: {list(df.columns)}")
    print(f"   Sample:\n{df.head(3)}")

    # Parse datetime
    # Format: "12/26/2025 00:00"
    df['timestamp'] = pd.to_datetime(df['Date_str'], format='%m/%d/%Y %H:%M')

    # Rename columns to standard format
    df = df.rename(columns={
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close'
    })

    # Add volume (if not present, use dummy values)
    if 'volume' not in df.columns:
        df['volume'] = 10000  # Dummy volume

    # Select required columns
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    # Sort by timestamp (oldest first)
    df = df.sort_values('timestamp')

    # Set timestamp as index
    df.set_index('timestamp', inplace=True)

    # Remove any NaN
    df = df.dropna()

    # Validate OHLC
    invalid_count = 0
    for i in range(len(df)):
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        open_price = df['open'].iloc[i]
        close = df['close'].iloc[i]

        if high < max(open_price, close) or low > min(open_price, close):
            df.loc[df.index[i], 'high'] = max(high, open_price, close)
            df.loc[df.index[i], 'low'] = min(low, open_price, close)
            invalid_count += 1

    if invalid_count > 0:
        print(f"   ⚠️  Fixed {invalid_count} invalid OHLC rows")

    # Add market hours info
    df = add_market_hours_info(df)

    print(f"\n✅ Real data processed:")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    print(f"   Total candles: {len(df)}")
    print(f"   Days: {(df.index[-1] - df.index[0]).days}")
    print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"   Avg hourly range: ${(df['high'] - df['low']).mean():.2f}")
    print(f"   Price start: ${df['close'].iloc[0]:.2f}")
    print(f"   Price end: ${df['close'].iloc[-1]:.2f}")
    print(f"   Total move: ${df['close'].iloc[-1] - df['close'].iloc[0]:.2f}")

    return df


def add_market_hours_info(df):
    """Add market hours and session quality info"""
    df = df.copy()

    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def backtest_strategy(df_strategy, strategy_name):
    """Execute backtest on strategy signals"""
    from datetime import timedelta

    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    if len(df_signals) == 0:
        return None

    trades = []
    wins = 0
    losses = 0
    total_pnl = 0

    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']

        entry_time = df_signals.index[i]
        search_end = entry_time + timedelta(hours=48)

        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]

        if len(df_future) == 0:
            continue

        exit_price = None
        exit_type = None
        exit_time = None

        for j in range(len(df_future)):
            if direction == 1:
                if df_future['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break
            else:
                if df_future['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break

        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'
            exit_time = df_future.index[-1]

        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        total_pnl += pnl_pct

        if pnl_pct > 0:
            wins += 1
        else:
            losses += 1

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'signal_type': signal.get('signal_type', 'unknown')
        })

    return {
        'total_trades': len(trades),
        'wins': wins,
        'losses': losses,
        'win_rate': (wins / len(trades) * 100) if len(trades) > 0 else 0,
        'total_pnl': total_pnl,
        'avg_pnl': total_pnl / len(trades) if len(trades) > 0 else 0,
        'trades': trades,
        'df_signals': df_signals
    }


def test_strategy(strategy, df, strategy_name):
    """Test a strategy on real data"""
    print(f"\n{'='*70}")
    print(f"Testing: {strategy_name}")
    print(f"{'='*70}")

    try:
        # Run strategy to generate signals
        df_strategy = strategy.run_strategy(df.copy())

        # Execute backtest on signals
        results = backtest_strategy(df_strategy, strategy_name)

        if results is None or results['total_trades'] == 0:
            print(f"❌ No trades generated")
            return None

        # Extract metrics
        total_pnl = results['total_pnl']
        win_rate = results['win_rate']
        total_trades = results['total_trades']
        avg_pnl = results['avg_pnl']

        # Calculate avg win/loss
        trades_df = pd.DataFrame(results['trades'])
        wins_df = trades_df[trades_df['pnl_pct'] > 0]
        losses_df = trades_df[trades_df['pnl_pct'] <= 0]

        avg_win = wins_df['pnl_pct'].mean() if len(wins_df) > 0 else 0
        avg_loss = losses_df['pnl_pct'].mean() if len(losses_df) > 0 else 0

        # Max drawdown
        cum_pnl = trades_df['pnl_pct'].cumsum()
        running_max = cum_pnl.cummax()
        drawdown = running_max - cum_pnl
        max_dd = drawdown.max() if len(drawdown) > 0 else 0

        # Sharpe ratio (simplified)
        if len(trades_df) > 0:
            sharpe = (trades_df['pnl_pct'].mean() / trades_df['pnl_pct'].std()) if trades_df['pnl_pct'].std() > 0 else 0
        else:
            sharpe = 0

        # Monthly profitability
        trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
        monthly_pnl = trades_df.groupby('month')['pnl_pct'].sum()
        profitable_months = (monthly_pnl > 0).sum()
        total_months = len(monthly_pnl)

        print(f"\n📈 Results:")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Total Trades: {total_trades}")
        print(f"   Avg Win: {avg_win:.2f}%")
        print(f"   Avg Loss: {avg_loss:.2f}%")
        print(f"   Max Drawdown: {max_dd:.2f}%")
        print(f"   Sharpe Ratio: {sharpe:.2f}")
        if total_months > 0:
            print(f"   Profitable Months: {profitable_months}/{total_months} ({profitable_months/total_months*100:.0f}%)")

        return {
            'name': strategy_name,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_dd,
            'sharpe': sharpe,
            'profitable_months': profitable_months,
            'total_months': total_months,
            'results_df': trades_df
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def compare_results(results_list):
    """Compare and rank all strategies"""
    print(f"\n{'='*70}")
    print("FINAL COMPARISON - REAL DATA")
    print(f"{'='*70}")

    # Filter out None results
    valid_results = [r for r in results_list if r is not None]

    if not valid_results:
        print("❌ No valid results to compare")
        return

    # Sort by total PnL
    valid_results.sort(key=lambda x: x['total_pnl'], reverse=True)

    print(f"\n{'Rank':<6} {'Strategy':<35} {'PnL':<12} {'WR':<8} {'Trades':<8} {'Sharpe':<8}")
    print("-" * 80)

    medals = ['🥇', '🥈', '🥉', '  ']

    for i, result in enumerate(valid_results):
        medal = medals[i] if i < len(medals) else '  '
        print(f"{medal}  {i+1}  {result['name']:<35} {result['total_pnl']:+8.2f}%  "
              f"{result['win_rate']:5.1f}%  {result['total_trades']:6}  "
              f"{result['sharpe']:6.2f}")

    # Winner
    winner = valid_results[0]
    print(f"\n🏆 WINNER: {winner['name']}")
    print(f"   Total PnL: {winner['total_pnl']:+.2f}%")
    print(f"   Win Rate: {winner['win_rate']:.1f}%")
    print(f"   Trades: {winner['total_trades']}")
    print(f"   Sharpe: {winner['sharpe']:.2f}")
    print(f"   Profitable Months: {winner['profitable_months']}/{winner['total_months']} ({winner['profitable_months']/winner['total_months']*100:.0f}%)")

    return valid_results


def plot_comparison(results_list, df):
    """Plot equity curves comparison"""
    valid_results = [r for r in results_list if r is not None and r['results_df'] is not None]

    if not valid_results:
        print("⚠️  No results to plot")
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: Equity curves
    for result in valid_results:
        trades = result['results_df'].copy()

        if 'entry_time' not in trades.columns:
            continue

        trades = trades.sort_values('entry_time')
        trades['cumulative_pnl'] = trades['pnl_pct'].cumsum()

        ax1.plot(pd.to_datetime(trades['entry_time']),
                trades['cumulative_pnl'],
                label=result['name'],
                linewidth=2)

    ax1.set_title('Equity Curves - REAL DATA', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cumulative PnL (%)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='--', linewidth=1)

    # Plot 2: Performance comparison
    names = [r['name'] for r in valid_results]
    pnls = [r['total_pnl'] for r in valid_results]
    colors = ['green' if p > 0 else 'red' for p in pnls]

    bars = ax2.barh(names, pnls, color=colors, alpha=0.7)
    ax2.set_xlabel('Total PnL (%)')
    ax2.set_title('Strategy Performance Comparison - REAL DATA', fontsize=14, fontweight='bold')
    ax2.axvline(x=0, color='black', linestyle='--', linewidth=1)
    ax2.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for i, (bar, pnl) in enumerate(zip(bars, pnls)):
        ax2.text(pnl, i, f' {pnl:+.2f}%',
                va='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig('real_data_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Chart saved: real_data_comparison.png")
    plt.close()


def main():
    # Load real data
    df = load_real_xauusd_data('/home/user/main/XAUUSD_historical_data.csv')

    # Initialize strategies
    print(f"\n{'='*70}")
    print("INITIALIZING STRATEGIES")
    print(f"{'='*70}")

    strategies = [
        (MultiSignalGoldStrategy(), "Original Multi-Signal"),
        (Fibonacci1618Strategy(fib_extension=1.618), "Fibonacci 1.618"),
        (PatternRecognitionStrategy(fib_mode='standard'), "Pattern Recognition (1.618)"),
        (PatternRecognitionStrategy(fib_mode='aggressive'), "Pattern Recognition (2.618)"),
    ]

    # Test all strategies
    results = []
    for strategy, name in strategies:
        result = test_strategy(strategy, df, name)
        if result:
            results.append(result)

    # Compare results
    if results:
        final_results = compare_results(results)

        # Plot comparison
        plot_comparison(results, df)

        # Save detailed results
        print(f"\n{'='*70}")
        print("SAVING DETAILED RESULTS")
        print(f"{'='*70}")

        with open('real_data_results.txt', 'w') as f:
            f.write("="*70 + "\n")
            f.write("REAL DATA BACKTEST RESULTS\n")
            f.write("="*70 + "\n\n")
            f.write(f"Data Period: {df.index[0]} to {df.index[-1]}\n")
            f.write(f"Total Candles: {len(df)}\n")
            f.write(f"Days: {(df.index[-1] - df.index[0]).days}\n\n")

            for i, result in enumerate(final_results):
                f.write(f"\n{i+1}. {result['name']}\n")
                f.write(f"   Total PnL: {result['total_pnl']:+.2f}%\n")
                f.write(f"   Win Rate: {result['win_rate']:.1f}%\n")
                f.write(f"   Total Trades: {result['total_trades']}\n")
                f.write(f"   Avg Win: {result['avg_win']:.2f}%\n")
                f.write(f"   Avg Loss: {result['avg_loss']:.2f}%\n")
                f.write(f"   Max Drawdown: {result['max_drawdown']:.2f}%\n")
                f.write(f"   Sharpe Ratio: {result['sharpe']:.2f}\n")
                f.write(f"   Profitable Months: {result['profitable_months']}/{result['total_months']}\n")

        print(f"✅ Results saved to: real_data_results.txt")

        print(f"\n{'='*70}")
        print("✅ REAL DATA BACKTEST COMPLETE!")
        print(f"{'='*70}")


if __name__ == "__main__":
    main()
