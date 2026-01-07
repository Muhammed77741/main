"""
Test all 4 strategies on real MT5 XAUUSD data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Import strategies
from intraday_gold_strategy import MultiSignalGoldStrategy
from fibonacci_1618_strategy import Fibonacci1618Strategy
from pattern_recognition_strategy import PatternRecognitionStrategy


def load_mt5_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load MT5 XAUUSD data"""
    print("=" * 70)
    print("LOADING MT5 XAUUSD DATA")
    print("=" * 70)

    df = pd.read_csv(file_path)

    print(f"\n📊 Raw data loaded: {len(df)} rows")
    print(f"   Columns: {list(df.columns)}")

    # Parse datetime
    df['timestamp'] = pd.to_datetime(df['datetime'])

    # Set timestamp as index
    df = df.set_index('timestamp')

    # Keep OHLCV columns
    df = df[['open', 'high', 'low', 'close', 'volume']]

    print(f"\n✅ Data loaded successfully!")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    print(f"   Total candles: {len(df)}")
    print(f"   Price range: {df['low'].min():.2f} - {df['high'].max():.2f}")
    print(f"\n   First candle: {df.index[0]}")
    print(f"      O:{df['open'].iloc[0]:.2f} H:{df['high'].iloc[0]:.2f} L:{df['low'].iloc[0]:.2f} C:{df['close'].iloc[0]:.2f}")
    print(f"\n   Last candle: {df.index[-1]}")
    print(f"      O:{df['open'].iloc[-1]:.2f} H:{df['high'].iloc[-1]:.2f} L:{df['low'].iloc[-1]:.2f} C:{df['close'].iloc[-1]:.2f}")

    # Add market hours info
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def backtest_strategy(df_strategy, strategy_name):
    """Execute backtest on strategy signals"""

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
            if direction == 1:  # LONG
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
            else:  # SHORT
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
    """Test a strategy on MT5 data"""
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

        # Calculate monthly PnL percentage
        monthly_pnl_pct = total_pnl / 12 if total_months >= 12 else total_pnl / total_months if total_months > 0 else 0

        print(f"\n📈 Results:")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Monthly PnL: {monthly_pnl_pct:+.2f}%")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Total Trades: {total_trades}")
        print(f"   Avg Win: {avg_win:.2f}%")
        print(f"   Avg Loss: {avg_loss:.2f}%")
        print(f"   Max Drawdown: {max_dd:.2f}%")
        print(f"   Sharpe Ratio: {sharpe:.2f}")
        print(f"   Profitable Months: {profitable_months}/{total_months}")

        # Exit type breakdown
        print(f"\n   Exit Types:")
        exit_counts = trades_df['exit_type'].value_counts()
        for exit_type, count in exit_counts.items():
            pct = (count / len(trades_df)) * 100
            print(f"      {exit_type}: {count} ({pct:.1f}%)")

        return {
            'name': strategy_name,
            'total_pnl': total_pnl,
            'monthly_pnl': monthly_pnl_pct,
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


def plot_comparison(results):
    """Plot comparison of all strategies"""
    if len(results) == 0:
        print("\n❌ No results to plot")
        return

    # Filter valid results
    valid_results = [r for r in results if r is not None and 'results_df' in r]

    if len(valid_results) == 0:
        print("\n❌ No valid results to plot")
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

    ax1.set_title('Equity Curves - MT5 REAL DATA', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cumulative PnL (%)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Performance metrics comparison
    metrics = ['total_pnl', 'win_rate', 'sharpe']
    metric_names = ['Total PnL (%)', 'Win Rate (%)', 'Sharpe Ratio']

    x = np.arange(len(valid_results))
    width = 0.25

    for i, (metric, name) in enumerate(zip(metrics, metric_names)):
        values = [r[metric] for r in valid_results]
        ax2.bar(x + i*width, values, width, label=name, alpha=0.8)

    ax2.set_title('Performance Metrics Comparison', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Value')
    ax2.set_xticks(x + width)
    ax2.set_xticklabels([r['name'] for r in valid_results], rotation=15, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('mt5_data_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 Chart saved: mt5_data_comparison.png")
    plt.close()


def main():
    print("\n" + "=" * 70)
    print("MT5 REAL DATA BACKTEST - ALL STRATEGIES")
    print("=" * 70)

    # Load MT5 data
    df = load_mt5_data()

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

    # Summary comparison
    if len(results) > 0:
        print(f"\n{'='*70}")
        print("SUMMARY COMPARISON - MT5 REAL DATA")
        print(f"{'='*70}")

        # Sort by total PnL
        results_sorted = sorted(results, key=lambda x: x['total_pnl'], reverse=True)

        print(f"\n{'Rank':<6}{'Strategy':<35}{'Total PnL':<12}{'Monthly':<10}{'WinRate':<10}{'Trades':<8}{'Sharpe':<8}")
        print("-" * 90)

        for i, r in enumerate(results_sorted, 1):
            emoji = "🏆" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"{emoji} {i:<4}{r['name']:<35}{r['total_pnl']:>+10.2f}%  {r['monthly_pnl']:>+8.2f}%  {r['win_rate']:>7.1f}%  {r['total_trades']:>6}  {r['sharpe']:>6.2f}")

        # Plot comparison
        plot_comparison(results)

    print(f"\n{'='*70}")
    print("✅ BACKTEST COMPLETE!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
