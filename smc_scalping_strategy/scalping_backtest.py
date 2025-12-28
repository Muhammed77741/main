"""
Backtest для скальпинг стратегии
Тестирование на M5/M15 данных с маленькими TP
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from pattern_recognition_scalping import PatternRecognitionScalping


def backtest_scalping(df, strategy, tp1=5, tp2=10, tp3=15,
                      close_pct1=0.5, close_pct2=0.3, close_pct3=0.2,
                      position_timeout_hours=4):
    """
    Backtest scalping strategy with 3 TP levels

    Args:
        df: DataFrame with M5/M15 OHLCV data
        strategy: PatternRecognitionScalping instance
        tp1, tp2, tp3: Take profit levels in points (default: 5/10/15)
        close_pct1, close_pct2, close_pct3: Partial close percentages
        position_timeout_hours: Force close after N hours (default: 4)
    """

    print(f"\n{'='*80}")
    print(f"📊 SCALPING BACKTEST")
    print(f"{'='*80}")
    print(f"   Data: {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    print(f"   TP Levels: {tp1}п / {tp2}п / {tp3}п")
    print(f"   Close %: {close_pct1*100:.0f}% / {close_pct2*100:.0f}% / {close_pct3*100:.0f}%")
    print(f"   Timeout: {position_timeout_hours}h")

    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())

    # Get signals
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    print(f"\n📈 Signals found: {len(df_signals)}")

    if len(df_signals) == 0:
        print("❌ No signals, cannot backtest")
        return None

    # Track trades
    trades = []
    open_position = None

    for idx, signal in df_signals.iterrows():
        # Check if we have open position
        if open_position is not None:
            # Don't open new position while one is open
            continue

        # Open new position
        direction = 'LONG' if signal['signal'] == 1 else 'SHORT'
        entry_price = signal['entry_price']
        entry_time = idx

        # Calculate TP levels
        if direction == 'LONG':
            tp1_price = entry_price + tp1
            tp2_price = entry_price + tp2
            tp3_price = entry_price + tp3
            sl_price = signal['stop_loss']
        else:  # SHORT
            tp1_price = entry_price - tp1
            tp2_price = entry_price - tp2
            tp3_price = entry_price - tp3
            sl_price = signal['stop_loss']

        open_position = {
            'entry_time': entry_time,
            'entry_price': entry_price,
            'direction': direction,
            'sl_price': sl_price,
            'tp1_price': tp1_price,
            'tp2_price': tp2_price,
            'tp3_price': tp3_price,
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'position_remaining': 1.0,
            'total_pnl_pct': 0.0,
            'pattern': signal.get('pattern', 'N/A')
        }

        # Simulate position until close
        entry_idx = df.index.get_loc(idx)

        for i in range(entry_idx + 1, len(df)):
            candle = df.iloc[i]
            candle_time = df.index[i]

            # Check timeout
            hours_in_trade = (candle_time - entry_time).total_seconds() / 3600

            if hours_in_trade >= position_timeout_hours:
                # Force close at current close price
                exit_price = candle['close']
                exit_type = 'TIMEOUT'

                if direction == 'LONG':
                    pnl = ((exit_price - entry_price) / entry_price) * 100 * open_position['position_remaining']
                else:
                    pnl = ((entry_price - exit_price) / entry_price) * 100 * open_position['position_remaining']

                open_position['total_pnl_pct'] += pnl

                trades.append({
                    'entry_time': entry_time,
                    'exit_time': candle_time,
                    'direction': direction,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'tp1_hit': open_position['tp1_hit'],
                    'tp2_hit': open_position['tp2_hit'],
                    'tp3_hit': open_position['tp3_hit'],
                    'pnl_pct': open_position['total_pnl_pct'],
                    'duration_minutes': hours_in_trade * 60,
                    'pattern': open_position['pattern']
                })

                open_position = None
                break

            # Check SL/TP
            if direction == 'LONG':
                # Stop loss
                if candle['low'] <= sl_price:
                    pnl = ((sl_price - entry_price) / entry_price) * 100 * open_position['position_remaining']
                    open_position['total_pnl_pct'] += pnl

                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': candle_time,
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': sl_price,
                        'exit_type': 'SL',
                        'tp1_hit': open_position['tp1_hit'],
                        'tp2_hit': open_position['tp2_hit'],
                        'tp3_hit': open_position['tp3_hit'],
                        'pnl_pct': open_position['total_pnl_pct'],
                        'duration_minutes': hours_in_trade * 60,
                        'pattern': open_position['pattern']
                    })

                    open_position = None
                    break

                # Take profits (check in reverse order)
                if candle['high'] >= tp3_price and not open_position['tp3_hit']:
                    pnl = ((tp3_price - entry_price) / entry_price) * 100 * close_pct3
                    open_position['total_pnl_pct'] += pnl
                    open_position['position_remaining'] -= close_pct3
                    open_position['tp3_hit'] = True

                if candle['high'] >= tp2_price and not open_position['tp2_hit']:
                    pnl = ((tp2_price - entry_price) / entry_price) * 100 * close_pct2
                    open_position['total_pnl_pct'] += pnl
                    open_position['position_remaining'] -= close_pct2
                    open_position['tp2_hit'] = True

                if candle['high'] >= tp1_price and not open_position['tp1_hit']:
                    pnl = ((tp1_price - entry_price) / entry_price) * 100 * close_pct1
                    open_position['total_pnl_pct'] += pnl
                    open_position['position_remaining'] -= close_pct1
                    open_position['tp1_hit'] = True

                # If all TPs hit, close position
                if open_position['position_remaining'] <= 0.01:
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': candle_time,
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': tp3_price,
                        'exit_type': 'TP3',
                        'tp1_hit': True,
                        'tp2_hit': True,
                        'tp3_hit': True,
                        'pnl_pct': open_position['total_pnl_pct'],
                        'duration_minutes': hours_in_trade * 60,
                        'pattern': open_position['pattern']
                    })

                    open_position = None
                    break

            else:  # SHORT
                # Stop loss
                if candle['high'] >= sl_price:
                    pnl = ((entry_price - sl_price) / entry_price) * 100 * open_position['position_remaining']
                    open_position['total_pnl_pct'] += pnl

                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': candle_time,
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': sl_price,
                        'exit_type': 'SL',
                        'tp1_hit': open_position['tp1_hit'],
                        'tp2_hit': open_position['tp2_hit'],
                        'tp3_hit': open_position['tp3_hit'],
                        'pnl_pct': open_position['total_pnl_pct'],
                        'duration_minutes': hours_in_trade * 60,
                        'pattern': open_position['pattern']
                    })

                    open_position = None
                    break

                # Take profits
                if candle['low'] <= tp3_price and not open_position['tp3_hit']:
                    pnl = ((entry_price - tp3_price) / entry_price) * 100 * close_pct3
                    open_position['total_pnl_pct'] += pnl
                    open_position['position_remaining'] -= close_pct3
                    open_position['tp3_hit'] = True

                if candle['low'] <= tp2_price and not open_position['tp2_hit']:
                    pnl = ((entry_price - tp2_price) / entry_price) * 100 * close_pct2
                    open_position['total_pnl_pct'] += pnl
                    open_position['position_remaining'] -= close_pct2
                    open_position['tp2_hit'] = True

                if candle['low'] <= tp1_price and not open_position['tp1_hit']:
                    pnl = ((entry_price - tp1_price) / entry_price) * 100 * close_pct1
                    open_position['total_pnl_pct'] += pnl
                    open_position['position_remaining'] -= close_pct1
                    open_position['tp1_hit'] = True

                if open_position['position_remaining'] <= 0.01:
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': candle_time,
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': tp3_price,
                        'exit_type': 'TP3',
                        'tp1_hit': True,
                        'tp2_hit': True,
                        'tp3_hit': True,
                        'pnl_pct': open_position['total_pnl_pct'],
                        'duration_minutes': hours_in_trade * 60,
                        'pattern': open_position['pattern']
                    })

                    open_position = None
                    break

    # Convert to DataFrame
    if len(trades) == 0:
        print("❌ No completed trades")
        return None

    trades_df = pd.DataFrame(trades)

    # Calculate statistics
    print(f"\n{'='*80}")
    print(f"📊 SCALPING RESULTS")
    print(f"{'='*80}")

    total_trades = len(trades_df)
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    total_pnl = trades_df['pnl_pct'].sum()
    avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
    avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0

    # TP hit rates
    tp1_hits = trades_df['tp1_hit'].sum()
    tp2_hits = trades_df['tp2_hit'].sum()
    tp3_hits = trades_df['tp3_hit'].sum()

    print(f"\n📈 Performance:")
    print(f"   Total trades: {total_trades}")
    print(f"   Wins: {wins} ({win_rate:.1f}%)")
    print(f"   Losses: {losses}")
    print(f"   Total PnL: {total_pnl:+.2f}%")
    print(f"   Avg Win: {avg_win:+.2f}%")
    print(f"   Avg Loss: {avg_loss:+.2f}%")

    print(f"\n🎯 TP Hit Rates:")
    print(f"   TP1 hits: {tp1_hits}/{total_trades} ({tp1_hits/total_trades*100:.1f}%)")
    print(f"   TP2 hits: {tp2_hits}/{total_trades} ({tp2_hits/total_trades*100:.1f}%)")
    print(f"   TP3 hits: {tp3_hits}/{total_trades} ({tp3_hits/total_trades*100:.1f}%)")

    # Exit type distribution
    print(f"\n🚪 Exit Types:")
    for exit_type in trades_df['exit_type'].unique():
        count = len(trades_df[trades_df['exit_type'] == exit_type])
        print(f"   {exit_type}: {count} ({count/total_trades*100:.1f}%)")

    # Average duration
    avg_duration = trades_df['duration_minutes'].mean()
    print(f"\n⏱️  Average Duration: {avg_duration:.0f} minutes ({avg_duration/60:.1f}h)")

    # Monthly breakdown
    trades_df['month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
    monthly_stats = trades_df.groupby('month').agg({
        'pnl_pct': 'sum',
        'entry_time': 'count'
    }).rename(columns={'entry_time': 'trades'})

    print(f"\n📅 Monthly Breakdown:")
    print(monthly_stats)

    # Drawdown
    cumulative_pnl = trades_df['pnl_pct'].cumsum()
    running_max = cumulative_pnl.cummax()
    drawdown = (cumulative_pnl - running_max)
    max_drawdown = drawdown.min()

    print(f"\n📉 Risk Metrics:")
    print(f"   Max Drawdown: {max_drawdown:.2f}%")

    return trades_df


def main():
    """Main entry point with CLI arguments"""

    parser = argparse.ArgumentParser(description='Scalping Strategy Backtest')

    parser.add_argument('--file', type=str, required=True,
                        help='CSV file with M5/M15 data')

    parser.add_argument('--tp1', type=int, default=5,
                        help='TP1 in points (default: 5)')

    parser.add_argument('--tp2', type=int, default=10,
                        help='TP2 in points (default: 10)')

    parser.add_argument('--tp3', type=int, default=15,
                        help='TP3 in points (default: 15)')

    parser.add_argument('--timeout', type=int, default=4,
                        help='Position timeout in hours (default: 4)')

    args = parser.parse_args()

    # Load data
    print(f"\n📂 Loading data from {args.file}...")
    df = pd.read_csv(args.file)

    # Parse datetime
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')

    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")

    # Add market hours if not present
    if 'is_active' not in df.columns:
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_overlap'] = df.index.hour.isin(range(13, 16))
        df['is_active'] = df['is_london'] | df['is_ny']
        df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    # Create strategy
    strategy = PatternRecognitionScalping(fib_mode='standard')

    # Run backtest
    trades_df = backtest_scalping(
        df=df,
        strategy=strategy,
        tp1=args.tp1,
        tp2=args.tp2,
        tp3=args.tp3,
        position_timeout_hours=args.timeout
    )

    if trades_df is not None:
        # Save results
        output_file = f"scalping_results_tp{args.tp1}_{args.tp2}_{args.tp3}.csv"
        trades_df.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to {output_file}")


if __name__ == "__main__":
    # Example usage:
    # python scalping_backtest.py --file XAUUSD_M15_data.csv --tp1 5 --tp2 10 --tp3 15
    main()
