"""
Извлечь последние сделки из годовых данных
Показать детали со временем входа/выхода
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import strategy
from pattern_recognition_strategy import PatternRecognitionStrategy


def load_yearly_data():
    """Load yearly XAUUSD data"""
    df = pd.read_csv('../XAUUSD_1H_20251227_220725.csv', index_col=0)
    df.index = pd.to_datetime(df.index)
    df.index.name = 'timestamp'

    df = df.rename(columns={
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    })

    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Add market hours
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def extract_trades(df, strategy, num_trades=30):
    """Extract last N trades"""
    print("🔍 Running strategy...")
    df_signals = strategy.run_strategy(df.copy())

    signals = df_signals[df_signals['signal'] != 0].copy()
    print(f"✅ Found {len(signals)} signals")

    # Get last N signals
    signals = signals.tail(num_trades)

    print(f"\n📈 Executing backtest for last {len(signals)} signals...")
    trades = []

    for i in range(len(signals)):
        signal = signals.iloc[i]
        entry_time = signals.index[i]
        entry_price = signal['entry_price']
        sl = signal['stop_loss']
        tp = signal['take_profit']
        direction = 'LONG' if signal['signal'] == 1 else 'SHORT'

        # Find exit
        search_end = entry_time + timedelta(hours=48)
        df_future = df_signals[(df_signals.index > entry_time) &
                               (df_signals.index <= search_end)]

        exit_price = None
        exit_type = None
        exit_time = None

        for j in range(len(df_future)):
            if signal['signal'] == 1:  # LONG
                if df_future['low'].iloc[j] <= sl:
                    exit_price = sl
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['high'].iloc[j] >= tp:
                    exit_price = tp
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break
            else:  # SHORT
                if df_future['high'].iloc[j] >= sl:
                    exit_price = sl
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif df_future['low'].iloc[j] <= tp:
                    exit_price = tp
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break

        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'EOD'
            exit_time = df_future.index[-1]

        # Calculate PnL
        if signal['signal'] == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl_points = exit_price - entry_price
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            pnl_points = entry_price - exit_price

        # Calculate duration
        duration_hours = (exit_time - entry_time).total_seconds() / 3600

        # Risk/Reward actual
        risk = abs(entry_price - sl)
        reward = abs(exit_price - entry_price)

        trade = {
            'id': i + 1,
            'entry_time': entry_time,
            'entry_date': entry_time.strftime('%Y-%m-%d'),
            'entry_hour': entry_time.strftime('%H:%M'),
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': sl,
            'take_profit': tp,
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
            'pattern': signal.get('signal_reason', 'N/A')
        }

        trades.append(trade)

    return pd.DataFrame(trades)


def main():
    print("=" * 80)
    print("ПОСЛЕДНИЕ СДЕЛКИ - ДЕТАЛЬНАЯ ИНФОРМАЦИЯ")
    print("=" * 80)

    # Load data
    print("\n📊 Loading data...")
    df = load_yearly_data()
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")

    # Run strategy
    strategy = PatternRecognitionStrategy(fib_mode='aggressive')  # 2.618

    # Extract last 30 trades
    trades_df = extract_trades(df, strategy, num_trades=30)

    print(f"\n✅ Extracted {len(trades_df)} trades")

    # Save to CSV
    csv_filename = 'last_30_trades_details.csv'
    trades_df.to_csv(csv_filename, index=False)
    print(f"\n💾 Saved to: {csv_filename}")

    # Display trades
    print(f"\n{'='*80}")
    print("ПОСЛЕДНИЕ 30 СДЕЛОК:")
    print(f"{'='*80}\n")

    for idx, trade in trades_df.iterrows():
        pnl_sign = '+' if trade['pnl_pct'] > 0 else ''
        result_emoji = '✅' if trade['pnl_pct'] > 0 else '❌'

        print(f"{result_emoji} Сделка #{trade['id']}")
        print(f"   Направление: {trade['direction']}")
        print(f"   Вход:  {trade['entry_date']} {trade['entry_hour']} @ {trade['entry_price']:.2f}")
        print(f"   SL:    {trade['stop_loss']:.2f} (риск: {trade['risk']:.2f})")
        print(f"   TP:    {trade['take_profit']:.2f}")
        print(f"   Выход: {trade['exit_date']} {trade['exit_hour']} @ {trade['exit_price']:.2f} ({trade['exit_type']})")
        print(f"   PnL:   {pnl_sign}{trade['pnl_pct']:.2f}% ({pnl_sign}{trade['pnl_points']:.2f} points)")
        print(f"   Время: {trade['duration_hours']:.1f} hours")
        print()

    # Summary statistics
    print(f"{'='*80}")
    print("СТАТИСТИКА:")
    print(f"{'='*80}")

    wins = trades_df[trades_df['pnl_pct'] > 0]
    losses = trades_df[trades_df['pnl_pct'] <= 0]

    print(f"Всего сделок: {len(trades_df)}")
    print(f"Прибыльных: {len(wins)} ({len(wins)/len(trades_df)*100:.1f}%)")
    print(f"Убыточных: {len(losses)} ({len(losses)/len(trades_df)*100:.1f}%)")
    print(f"Общий PnL: {trades_df['pnl_pct'].sum():+.2f}%")
    print(f"Средний PnL: {trades_df['pnl_pct'].mean():+.2f}%")
    print(f"Лучшая сделка: +{trades_df['pnl_pct'].max():.2f}%")
    print(f"Худшая сделка: {trades_df['pnl_pct'].min():.2f}%")
    print(f"Средняя длительность: {trades_df['duration_hours'].mean():.1f} часов")

    # By exit type
    print(f"\nПо типу выхода:")
    for exit_type in ['TP', 'SL', 'EOD']:
        type_trades = trades_df[trades_df['exit_type'] == exit_type]
        if len(type_trades) > 0:
            print(f"  {exit_type}: {len(type_trades)} ({len(type_trades)/len(trades_df)*100:.1f}%) | "
                  f"Avg PnL: {type_trades['pnl_pct'].mean():+.2f}%")

    print(f"\n{'='*80}")
    print(f"✅ Готово! Файл: {csv_filename}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
