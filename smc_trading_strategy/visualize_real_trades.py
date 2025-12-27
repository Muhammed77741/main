"""
Визуализация реальных сделок с барами (свечами)
Показывает как ведет себя позиция в реальном времени
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import timedelta

# Import strategies
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
    return df


def plot_trade_with_bars(df, trade, context_bars=10):
    """
    Визуализирует сделку с барами (свечами)

    Args:
        df: DataFrame with OHLCV data
        trade: Dict with trade info (entry_time, entry_price, sl, tp, direction, exit_time, exit_price)
        context_bars: Number of bars before/after to show
    """
    entry_time = trade['entry_time']
    exit_time = trade['exit_time']
    entry_price = trade['entry_price']
    sl = trade['stop_loss']
    tp = trade['take_profit']
    direction = trade['direction']
    exit_price = trade['exit_price']
    exit_type = trade['exit_type']

    # Get bars around trade
    entry_idx = df.index.get_loc(entry_time)
    start_idx = max(0, entry_idx - context_bars)

    # Find exit index
    try:
        exit_idx = df.index.get_loc(exit_time)
    except:
        exit_idx = min(len(df)-1, entry_idx + 48)  # 48h timeout

    end_idx = min(len(df)-1, exit_idx + context_bars)

    df_plot = df.iloc[start_idx:end_idx+1].copy()

    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10),
                                    gridspec_kw={'height_ratios': [3, 1]})

    # Plot 1: Candlestick chart
    plot_candlesticks(ax1, df_plot, entry_time, exit_time,
                     entry_price, sl, tp, direction, exit_price, exit_type)

    # Plot 2: Volume
    plot_volume(ax2, df_plot, entry_time, exit_time)

    # Title
    pnl = trade['pnl_pct']
    pnl_sign = '+' if pnl > 0 else ''

    fig.suptitle(
        f"{direction} Trade: {pnl_sign}{pnl:.2f}% | "
        f"Entry: {entry_time.strftime('%Y-%m-%d %H:%M')} @ {entry_price:.2f} | "
        f"Exit: {exit_time.strftime('%Y-%m-%d %H:%M')} @ {exit_price:.2f} ({exit_type})",
        fontsize=14, fontweight='bold'
    )

    plt.tight_layout()

    # Save
    filename = f"trade_{direction}_{entry_time.strftime('%Y%m%d_%H%M')}_{exit_type}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"💾 Saved: {filename}")
    plt.close()


def plot_candlesticks(ax, df, entry_time, exit_time, entry_price, sl, tp,
                     direction, exit_price, exit_type):
    """Plot candlestick chart with trade levels"""

    # Plot candlesticks
    for i, (idx, row) in enumerate(df.iterrows()):
        # Determine color
        color = 'green' if row['close'] >= row['open'] else 'red'
        alpha = 1.0

        # Highlight entry and exit bars
        if idx == entry_time:
            color = 'blue'
            alpha = 0.8
        elif idx == exit_time:
            color = 'orange'
            alpha = 0.8

        # Draw candle body
        body_height = abs(row['close'] - row['open'])
        body_bottom = min(row['open'], row['close'])

        ax.add_patch(
            patches.Rectangle(
                (i, body_bottom),
                0.6,
                body_height,
                facecolor=color,
                edgecolor='black',
                alpha=alpha,
                linewidth=1
            )
        )

        # Draw wicks
        ax.plot([i+0.3, i+0.3], [row['low'], body_bottom],
               color='black', linewidth=1, alpha=alpha)
        ax.plot([i+0.3, i+0.3], [body_bottom+body_height, row['high']],
               color='black', linewidth=1, alpha=alpha)

    # Find entry and exit bar indices for plotting
    entry_idx_plot = df.index.get_loc(entry_time)
    exit_idx_plot = df.index.get_loc(exit_time)

    # Plot Entry level
    ax.axhline(y=entry_price, color='blue', linestyle='--', linewidth=2,
               label=f'Entry: {entry_price:.2f}', alpha=0.7)

    # Plot SL level
    ax.axhline(y=sl, color='red', linestyle='--', linewidth=2,
               label=f'SL: {sl:.2f}', alpha=0.7)

    # Plot TP level
    ax.axhline(y=tp, color='green', linestyle='--', linewidth=2,
               label=f'TP: {tp:.2f}', alpha=0.7)

    # Vertical line at entry
    ax.axvline(x=entry_idx_plot, color='blue', linestyle=':',
              linewidth=1.5, alpha=0.5, label='Entry Time')

    # Vertical line at exit
    ax.axvline(x=exit_idx_plot, color='orange', linestyle=':',
              linewidth=1.5, alpha=0.5, label='Exit Time')

    # Mark exit price
    ax.plot(exit_idx_plot, exit_price, 'o', color='orange',
           markersize=10, label=f'Exit: {exit_price:.2f} ({exit_type})')

    # Annotate bars
    ax.text(entry_idx_plot, entry_price, f'  Entry\n  {direction}',
           fontsize=10, color='blue', fontweight='bold',
           verticalalignment='bottom')

    ax.text(exit_idx_plot, exit_price, f'  Exit\n  {exit_type}',
           fontsize=10, color='orange', fontweight='bold',
           verticalalignment='top')

    # Set labels
    ax.set_ylabel('Price', fontsize=12, fontweight='bold')
    ax.set_title('Candlestick Chart with Trade Levels', fontsize=12)
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)

    # X-axis: time labels
    time_labels = [t.strftime('%m/%d %H:%M') for t in df.index]
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(time_labels, rotation=45, ha='right', fontsize=8)


def plot_volume(ax, df, entry_time, exit_time):
    """Plot volume bars"""
    colors = ['green' if df['close'].iloc[i] >= df['open'].iloc[i] else 'red'
              for i in range(len(df))]

    # Highlight entry/exit
    for i, idx in enumerate(df.index):
        if idx == entry_time:
            colors[i] = 'blue'
        elif idx == exit_time:
            colors[i] = 'orange'

    ax.bar(range(len(df)), df['volume'], color=colors, alpha=0.6, width=0.6)
    ax.set_ylabel('Volume', fontsize=10, fontweight='bold')
    ax.set_title('Volume', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    # X-axis
    ax.set_xticks([])


def analyze_intrabar_execution(df, trade):
    """
    Анализирует внутрисвечное исполнение
    Проверяет был ли случай когда и TP и SL достигнуты на одной свече
    """
    entry_time = trade['entry_time']
    exit_time = trade['exit_time']
    entry_price = trade['entry_price']
    sl = trade['stop_loss']
    tp = trade['take_profit']
    direction = trade['direction']

    # Get bars between entry and exit
    entry_idx = df.index.get_loc(entry_time)
    exit_idx = df.index.get_loc(exit_time)

    df_trade = df.iloc[entry_idx+1:exit_idx+1]

    both_hit_bars = []

    for idx, row in df_trade.iterrows():
        if direction == 'LONG':
            tp_hit = (row['high'] >= tp)
            sl_hit = (row['low'] <= sl)
        else:  # SHORT
            tp_hit = (row['low'] <= tp)
            sl_hit = (row['high'] >= sl)

        if tp_hit and sl_hit:
            # Определяем что сработало первым
            dist_to_sl = abs(row['open'] - sl)
            dist_to_tp = abs(row['open'] - tp)

            first_hit = 'SL' if dist_to_sl < dist_to_tp else 'TP'

            both_hit_bars.append({
                'time': idx,
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'dist_to_sl': dist_to_sl,
                'dist_to_tp': dist_to_tp,
                'first_hit': first_hit
            })

    return both_hit_bars


def main():
    print("=" * 70)
    print("ВИЗУАЛИЗАЦИЯ РЕАЛЬНЫХ СДЕЛОК")
    print("=" * 70)

    # Load data
    print("\n📊 Loading data...")
    df = load_yearly_data()
    print(f"✅ Loaded {len(df)} candles")

    # Add market hours
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    # Run strategy
    print("\n🔍 Running Pattern Recognition strategy...")
    strategy = PatternRecognitionStrategy(fib_mode='aggressive')  # 2.618
    df_signals = strategy.run_strategy(df.copy())

    # Get trades
    signals = df_signals[df_signals['signal'] != 0].copy()
    print(f"✅ Found {len(signals)} signals")

    # Execute backtest to get trades
    print("\n📈 Executing backtest...")
    trades = []

    for i in range(min(len(signals), 50)):  # First 50 signals
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
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        trade = {
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_price': entry_price,
            'stop_loss': sl,
            'take_profit': tp,
            'direction': direction,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct
        }

        trades.append(trade)

    # Find interesting trades to visualize
    print(f"\n🎯 Analyzing {len(trades)} trades...")

    # Best TP trade
    tp_trades = [t for t in trades if t['exit_type'] == 'TP']
    if tp_trades:
        best_tp = max(tp_trades, key=lambda x: x['pnl_pct'])
        print(f"\n📊 Best TP Trade: +{best_tp['pnl_pct']:.2f}%")
        plot_trade_with_bars(df, best_tp, context_bars=5)

        # Analyze intrabar
        both_hit = analyze_intrabar_execution(df, best_tp)
        if both_hit:
            print(f"   ⚠️  Found {len(both_hit)} bars where BOTH TP and SL were hit!")
            for bar in both_hit:
                print(f"      {bar['time']}: {bar['first_hit']} hit first "
                      f"(dist_SL={bar['dist_to_sl']:.2f}, dist_TP={bar['dist_to_tp']:.2f})")

    # Worst SL trade
    sl_trades = [t for t in trades if t['exit_type'] == 'SL']
    if sl_trades:
        worst_sl = min(sl_trades, key=lambda x: x['pnl_pct'])
        print(f"\n📊 Worst SL Trade: {worst_sl['pnl_pct']:.2f}%")
        plot_trade_with_bars(df, worst_sl, context_bars=5)

        # Analyze intrabar
        both_hit = analyze_intrabar_execution(df, worst_sl)
        if both_hit:
            print(f"   ⚠️  Found {len(both_hit)} bars where BOTH TP and SL were hit!")
            for bar in both_hit:
                print(f"      {bar['time']}: {bar['first_hit']} hit first "
                      f"(dist_SL={bar['dist_to_sl']:.2f}, dist_TP={bar['dist_to_tp']:.2f})")

    # Random profitable trade
    profitable = [t for t in trades if t['pnl_pct'] > 0]
    if profitable:
        random_profit = profitable[len(profitable)//2]
        print(f"\n📊 Random Profitable Trade: +{random_profit['pnl_pct']:.2f}%")
        plot_trade_with_bars(df, random_profit, context_bars=5)

    # Random losing trade
    losing = [t for t in trades if t['pnl_pct'] < 0]
    if losing:
        random_loss = losing[len(losing)//2]
        print(f"\n📊 Random Losing Trade: {random_loss['pnl_pct']:.2f}%")
        plot_trade_with_bars(df, random_loss, context_bars=5)

    # Statistics on intrabar execution
    print(f"\n" + "=" * 70)
    print("СТАТИСТИКА ВНУТРИСВЕЧНОГО ИСПОЛНЕНИЯ")
    print("=" * 70)

    total_both_hit = 0
    for trade in trades:
        both_hit = analyze_intrabar_execution(df, trade)
        if both_hit:
            total_both_hit += len(both_hit)

    print(f"\nВсего сделок: {len(trades)}")
    print(f"Случаев когда ОБА уровня достигнуты: {total_both_hit}")
    print(f"Процент: {total_both_hit / len(trades) * 100:.1f}%")

    print(f"\n✅ Визуализация завершена!")


if __name__ == "__main__":
    main()
