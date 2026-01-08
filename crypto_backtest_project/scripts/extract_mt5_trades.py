"""
Extract last N trades from best strategy (Pattern Recognition 1.618) on MT5 data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from pattern_recognition_strategy import PatternRecognitionStrategy


def load_mt5_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load MT5 XAUUSD data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Add market hours info
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def extract_trades(df, strategy, num_trades=30):
    """Extract last N trades with full details"""

    print("=" * 80)
    print("EXTRACTING LAST TRADES FROM PATTERN RECOGNITION (1.618)")
    print("=" * 80)

    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())

    # Get signals
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    print(f"\n📊 Total signals: {len(df_signals)}")

    # Get last N signals
    signals = df_signals.tail(num_trades)

    print(f"   Extracting last {len(signals)} trades...\n")

    trades = []

    for i in range(len(signals)):
        signal = signals.iloc[i]

        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']

        entry_time = signals.index[i]
        search_end = entry_time + timedelta(hours=48)

        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]

        if len(df_future) == 0:
            continue

        exit_price = None
        exit_type = None
        exit_time = None

        # Find exit
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

        # Calculate PnL
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl_points = exit_price - entry_price
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            pnl_points = entry_price - exit_price

        # Calculate risk/reward
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        # Duration
        duration_hours = (exit_time - entry_time).total_seconds() / 3600

        # Pattern info
        pattern = signal.get('pattern', 'N/A')

        trade = {
            'id': i + 1,
            'entry_time': entry_time,
            'entry_date': entry_time.strftime('%Y-%m-%d'),
            'entry_hour': entry_time.strftime('%H:%M'),
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'exit_time': exit_time,
            'exit_date': exit_time.strftime('%Y-%m-%d'),
            'exit_hour': exit_time.strftime('%H:%M'),
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
            'risk': risk,
            'reward': reward,
            'pattern': pattern,
        }

        trades.append(trade)

    return pd.DataFrame(trades)


def display_trades(trades_df):
    """Display trades in readable format"""

    print("=" * 80)
    print(f"ПОСЛЕДНИЕ {len(trades_df)} СДЕЛОК - PATTERN RECOGNITION (1.618)")
    print("=" * 80)

    # Statistics
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    losses = len(trades_df[trades_df['pnl_pct'] <= 0])
    win_rate = (wins / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    total_pnl = trades_df['pnl_pct'].sum()
    avg_pnl = trades_df['pnl_pct'].mean()

    print(f"\n📊 Статистика:")
    print(f"   Всего сделок: {len(trades_df)}")
    print(f"   Прибыльных: {wins} ({win_rate:.1f}%)")
    print(f"   Убыточных: {losses} ({100-win_rate:.1f}%)")
    print(f"   Общий PnL: {total_pnl:+.2f}%")
    print(f"   Средний PnL: {avg_pnl:+.2f}%")
    print(f"   Средняя длительность: {trades_df['duration_hours'].mean():.1f} часов")

    # Exit type breakdown
    print(f"\n   Типы выходов:")
    exit_counts = trades_df['exit_type'].value_counts()
    for exit_type, count in exit_counts.items():
        pct = (count / len(trades_df)) * 100
        avg_pnl_for_type = trades_df[trades_df['exit_type'] == exit_type]['pnl_pct'].mean()
        print(f"      {exit_type}: {count} сделок ({pct:.1f}%) | Avg PnL: {avg_pnl_for_type:+.2f}%")

    print(f"\n{'='*80}")
    print("ДЕТАЛИ КАЖДОЙ СДЕЛКИ:")
    print(f"{'='*80}\n")

    # Display each trade
    for idx, trade in trades_df.iterrows():
        emoji = "✅" if trade['pnl_pct'] > 0 else "❌"

        print(f"{emoji} Сделка #{trade['id']}")
        print(f"   Направление: {trade['direction']}")
        print(f"   Паттерн: {trade['pattern']}")
        print(f"   ")
        print(f"   Вход:  {trade['entry_date']} {trade['entry_hour']} @ {trade['entry_price']:.2f}")
        print(f"   SL:    {trade['stop_loss']:.2f} (риск: {trade['risk']:.2f})")
        print(f"   TP:    {trade['take_profit']:.2f} (награда: {trade['reward']:.2f})")
        print(f"   R:R:   1:{trade['reward']/trade['risk']:.2f}")
        print(f"   ")
        print(f"   Выход: {trade['exit_date']} {trade['exit_hour']} @ {trade['exit_price']:.2f} ({trade['exit_type']})")
        print(f"   PnL:   {trade['pnl_pct']:+.2f}% ({trade['pnl_points']:+.2f} points)")
        print(f"   Время: {trade['duration_hours']:.1f} hours")
        print()

    return trades_df


def save_to_csv(trades_df, filename='last_30_trades_mt5.csv'):
    """Save trades to CSV"""
    trades_df.to_csv(filename, index=False)
    print(f"\n💾 Сохранено в: {filename}")
    print(f"   Строк: {len(trades_df)}")


def main():
    print("\n" + "=" * 80)
    print("ИЗВЛЕЧЕНИЕ ПОСЛЕДНИХ СДЕЛОК - PATTERN RECOGNITION (1.618)")
    print("=" * 80 + "\n")

    # Load data
    df = load_mt5_data()
    print(f"📊 Загружено {len(df)} свечей")
    print(f"   Период: {df.index[0]} до {df.index[-1]}\n")

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Extract trades
    trades_df = extract_trades(df, strategy, num_trades=30)

    # Display trades
    trades_df = display_trades(trades_df)

    # Save to CSV
    save_to_csv(trades_df)

    print("\n" + "=" * 80)
    print("✅ ГОТОВО!")
    print("=" * 80)


if __name__ == "__main__":
    main()
