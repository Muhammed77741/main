"""
Детектор всех движений на 30 пипсов

Для золота (XAUUSD):
- 1 пипс = $0.10
- 30 пипсов = $3.00
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2


def find_30pip_moves(df, min_pips=30, lookforward_candles=10, pip_value=0.10):
    """
    Находим все движения >= 30 пипсов
    
    Args:
        df: DataFrame с данными
        min_pips: минимальное движение в пипсах (default: 30)
        lookforward_candles: сколько свечей смотрим вперед
        pip_value: стоимость 1 пипса (для XAUUSD = 0.10)
    """
    
    min_price_move = min_pips * pip_value  # 30 * 0.10 = 3.0
    
    print(f"\n🔍 Searching for moves >= {min_pips} pips (${min_price_move})...")
    
    moves = []
    
    for i in range(len(df) - lookforward_candles):
        current_price = df['close'].iloc[i]
        
        # Look forward for LONG moves
        future_highs = df['high'].iloc[i+1:i+lookforward_candles+1]
        max_future_high = future_highs.max()
        
        # Look forward for SHORT moves (если нужно)
        future_lows = df['low'].iloc[i+1:i+lookforward_candles+1]
        min_future_low = future_lows.min()
        
        # LONG move
        long_move_dollars = max_future_high - current_price
        long_move_pips = long_move_dollars / pip_value
        
        if long_move_pips >= min_pips:
            # Find when max was reached
            max_idx_relative = future_highs.argmax()
            max_time = future_highs.index[max_idx_relative]
            candles_to_max = max_idx_relative + 1
            
            entry_time = df.index[i]
            
            moves.append({
                'entry_time': entry_time,
                'direction': 'LONG',
                'entry_price': current_price,
                'max_price': max_future_high,
                'max_time': max_time,
                'move_dollars': long_move_dollars,
                'move_pips': long_move_pips,
                'move_pct': (long_move_dollars / current_price) * 100,
                'candles_to_max': candles_to_max,
                'entry_idx': i
            })
        
        # SHORT move (опционально)
        short_move_dollars = current_price - min_future_low
        short_move_pips = short_move_dollars / pip_value
        
        if short_move_pips >= min_pips:
            # Find when min was reached
            min_idx_relative = future_lows.argmin()
            min_time = future_lows.index[min_idx_relative]
            candles_to_min = min_idx_relative + 1
            
            entry_time = df.index[i]
            
            moves.append({
                'entry_time': entry_time,
                'direction': 'SHORT',
                'entry_price': current_price,
                'max_price': min_future_low,
                'max_time': min_time,
                'move_dollars': short_move_dollars,
                'move_pips': short_move_pips,
                'move_pct': (short_move_dollars / current_price) * 100,
                'candles_to_max': candles_to_min,
                'entry_idx': i
            })
    
    moves_df = pd.DataFrame(moves)
    
    if len(moves_df) > 0:
        long_moves = len(moves_df[moves_df['direction'] == 'LONG'])
        short_moves = len(moves_df[moves_df['direction'] == 'SHORT'])
        
        print(f"   Found {len(moves_df)} moves >= {min_pips} pips:")
        print(f"      LONG:  {long_moves} moves")
        print(f"      SHORT: {short_moves} moves")
        print(f"      Avg move: {moves_df['move_pips'].mean():.1f} pips")
        print(f"      Max move: {moves_df['move_pips'].max():.1f} pips")
    
    return moves_df


def analyze_30pip_moves(df, moves_df):
    """
    Анализ движений на 30 пипсов
    """
    
    print(f"\n" + "="*100)
    print(f"📊 АНАЛИЗ ДВИЖЕНИЙ >= 30 ПИПСОВ")
    print(f"="*100)
    
    if len(moves_df) == 0:
        print("No moves found!")
        return
    
    # Calculate indicators
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    df['rsi'] = rsi
    
    # ATR
    high_low = df['high'] - df['low']
    df['atr'] = high_low.rolling(window=14).mean()
    
    # MA
    df['ma_5'] = df['close'].rolling(window=5).mean()
    df['ma_20'] = df['close'].rolling(window=20).mean()
    df['ma_50'] = df['close'].rolling(window=50).mean()
    
    # Volume
    df['volume_ma20'] = df['volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma20']
    
    # Add indicators to moves
    for idx, move in moves_df.iterrows():
        entry_idx = move['entry_idx']
        
        if entry_idx >= 50:
            moves_df.loc[idx, 'rsi'] = df['rsi'].iloc[entry_idx]
            moves_df.loc[idx, 'atr'] = df['atr'].iloc[entry_idx]
            moves_df.loc[idx, 'volume_ratio'] = df['volume_ratio'].iloc[entry_idx]
            
            # Trend
            if df['ma_5'].iloc[entry_idx] > df['ma_20'].iloc[entry_idx] > df['ma_50'].iloc[entry_idx]:
                moves_df.loc[idx, 'trend'] = 'strong_up'
            elif df['ma_5'].iloc[entry_idx] > df['ma_20'].iloc[entry_idx]:
                moves_df.loc[idx, 'trend'] = 'up'
            elif df['ma_5'].iloc[entry_idx] < df['ma_20'].iloc[entry_idx] < df['ma_50'].iloc[entry_idx]:
                moves_df.loc[idx, 'trend'] = 'strong_down'
            elif df['ma_5'].iloc[entry_idx] < df['ma_20'].iloc[entry_idx]:
                moves_df.loc[idx, 'trend'] = 'down'
            else:
                moves_df.loc[idx, 'trend'] = 'sideways'
    
    # 1. By direction
    print(f"\n📊 По направлению:")
    for direction in ['LONG', 'SHORT']:
        dir_moves = moves_df[moves_df['direction'] == direction]
        if len(dir_moves) > 0:
            avg_pips = dir_moves['move_pips'].mean()
            max_pips = dir_moves['move_pips'].max()
            avg_candles = dir_moves['candles_to_max'].mean()
            
            print(f"   {direction:6s}: {len(dir_moves):4d} moves | "
                  f"Avg: {avg_pips:5.1f} pips | Max: {max_pips:5.1f} pips | "
                  f"Time: {avg_candles:.1f} candles")
    
    # 2. By trend
    print(f"\n📈 По тренду:")
    for trend in ['strong_up', 'up', 'sideways', 'down', 'strong_down']:
        trend_moves = moves_df[moves_df['trend'] == trend]
        if len(trend_moves) > 0:
            avg_pips = trend_moves['move_pips'].mean()
            long_count = len(trend_moves[trend_moves['direction'] == 'LONG'])
            short_count = len(trend_moves[trend_moves['direction'] == 'SHORT'])
            
            print(f"   {trend:15s}: {len(trend_moves):4d} moves (L:{long_count:3d} S:{short_count:3d}) | "
                  f"Avg: {avg_pips:5.1f} pips")
    
    # 3. By hour
    print(f"\n⏰ По часам дня (топ-10):")
    moves_df['hour'] = moves_df['entry_time'].dt.hour
    hour_counts = moves_df.groupby('hour').agg({
        'move_pips': ['count', 'mean', 'max']
    }).round(1)
    hour_counts.columns = ['count', 'avg_pips', 'max_pips']
    hour_counts = hour_counts.sort_values('count', ascending=False).head(10)
    
    for hour, row in hour_counts.iterrows():
        print(f"   {int(hour):02d}:00 - {int(row['count']):3d} moves | "
              f"Avg: {row['avg_pips']:5.1f} pips | Max: {row['max_pips']:5.1f} pips")
    
    # 4. By move size
    print(f"\n📏 По размеру движения:")
    bins = [30, 50, 70, 100, 150, 200, 1000]
    labels = ['30-50', '50-70', '70-100', '100-150', '150-200', '200+']
    moves_df['size_range'] = pd.cut(moves_df['move_pips'], bins=bins, labels=labels)
    
    size_counts = moves_df['size_range'].value_counts().sort_index()
    for size_range, count in size_counts.items():
        pct = count / len(moves_df) * 100
        print(f"   {size_range:10s}: {count:4d} moves ({pct:5.1f}%)")
    
    # 5. TOP 20 biggest moves
    print(f"\n💰 TOP 20 САМЫХ БОЛЬШИХ ДВИЖЕНИЙ:")
    print(f"{'#':<4} {'Date':<20} {'Dir':<6} {'Entry':<10} {'Max':<10} {'Pips':<10} {'%':<8} {'Candles':<10} {'Trend':<15}")
    print("-"*110)
    
    top_moves = moves_df.nlargest(20, 'move_pips')
    for i, (_, move) in enumerate(top_moves.iterrows(), 1):
        print(f"{i:<4} {str(move['entry_time']):<20} {move['direction']:<6} "
              f"{move['entry_price']:<10.2f} {move['max_price']:<10.2f} "
              f"{move['move_pips']:>8.1f}p {move['move_pct']:>6.2f}% "
              f"{move['candles_to_max']:>9.0f} {str(move.get('trend', 'N/A')):<15}")
    
    return moves_df


def compare_with_baseline(df, moves_df):
    """
    Сравниваем с baseline стратегией - сколько поймали
    """
    
    print(f"\n" + "="*100)
    print(f"🎯 СРАВНЕНИЕ С BASELINE СТРАТЕГИЕЙ")
    print(f"="*100)
    
    # Initialize baseline
    print(f"\n🚀 Running baseline strategy...")
    baseline = PatternRecognitionOptimizedV2(
        fib_mode='standard',
        tp_multiplier=1.4,
        long_only=True
    )
    
    df_baseline = baseline.run_strategy(df.copy())
    baseline_signals = df_baseline[df_baseline['signal'] != 0].copy()
    
    print(f"   Baseline signals: {len(baseline_signals)}")
    
    # Check which moves we caught
    moves_df['caught'] = False
    moves_df['signal_time'] = None
    
    caught_long = 0
    caught_short = 0
    missed_long = 0
    missed_short = 0
    
    for idx, move in moves_df.iterrows():
        entry_time = move['entry_time']
        direction = move['direction']
        
        # Check if baseline had signal within 1 hour before
        nearby_signals = baseline_signals[
            (baseline_signals.index >= entry_time - timedelta(hours=1)) &
            (baseline_signals.index <= entry_time)
        ]
        
        if len(nearby_signals) > 0:
            moves_df.loc[idx, 'caught'] = True
            moves_df.loc[idx, 'signal_time'] = nearby_signals.index[0]
            
            if direction == 'LONG':
                caught_long += 1
            else:
                caught_short += 1
        else:
            if direction == 'LONG':
                missed_long += 1
            else:
                missed_short += 1
    
    total_moves = len(moves_df)
    caught_total = caught_long + caught_short
    missed_total = missed_long + missed_short
    
    print(f"\n📊 Результаты:")
    print(f"\n   Всего движений 30+ пипсов: {total_moves}")
    print(f"      LONG:  {len(moves_df[moves_df['direction'] == 'LONG'])}")
    print(f"      SHORT: {len(moves_df[moves_df['direction'] == 'SHORT'])}")
    
    print(f"\n   ✅ Поймано baseline: {caught_total} ({caught_total/total_moves*100:.1f}%)")
    print(f"      LONG:  {caught_long}")
    print(f"      SHORT: {caught_short}")
    
    print(f"\n   ❌ Упущено: {missed_total} ({missed_total/total_moves*100:.1f}%)")
    print(f"      LONG:  {missed_long}")
    print(f"      SHORT: {missed_short}")
    
    # Missed moves stats
    missed_moves = moves_df[moves_df['caught'] == False].copy()
    
    if len(missed_moves) > 0:
        missed_long_moves = missed_moves[missed_moves['direction'] == 'LONG']
        missed_short_moves = missed_moves[missed_moves['direction'] == 'SHORT']
        
        print(f"\n💰 Упущенный потенциал:")
        if len(missed_long_moves) > 0:
            print(f"      LONG:  {len(missed_long_moves)} moves | "
                  f"Avg: {missed_long_moves['move_pips'].mean():.1f} pips | "
                  f"Total: {missed_long_moves['move_pips'].sum():.0f} pips")
        if len(missed_short_moves) > 0:
            print(f"      SHORT: {len(missed_short_moves)} moves | "
                  f"Avg: {missed_short_moves['move_pips'].mean():.1f} pips | "
                  f"Total: {missed_short_moves['move_pips'].sum():.0f} pips")
        
        total_missed_pips = missed_moves['move_pips'].sum()
        print(f"\n      📊 ИТОГО упущено: {total_missed_pips:.0f} пипсов (${total_missed_pips*0.10:.2f})")
    
    return moves_df


def visualize_30pip_moves(df, moves_df):
    """
    Визуализация движений на 30 пипсов
    """
    
    fig = plt.figure(figsize=(20, 12))
    
    # 1. Price chart with moves
    ax1 = plt.subplot(3, 2, 1)
    ax1.plot(df.index, df['close'], color='blue', alpha=0.3, linewidth=1)
    
    # Mark LONG moves
    long_moves = moves_df[moves_df['direction'] == 'LONG']
    if len(long_moves) > 0:
        caught_long = long_moves[long_moves['caught'] == True]
        missed_long = long_moves[long_moves['caught'] == False]
        
        if len(caught_long) > 0:
            ax1.scatter(caught_long['entry_time'], caught_long['entry_price'],
                       color='green', s=50, alpha=0.6, label='Caught LONG', marker='^')
        
        if len(missed_long) > 0:
            ax1.scatter(missed_long['entry_time'], missed_long['entry_price'],
                       color='red', s=50, alpha=0.6, label='Missed LONG', marker='v')
    
    ax1.set_title('Price Chart: 30+ Pip Moves', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price', fontsize=12)
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # 2. Move size distribution
    ax2 = plt.subplot(3, 2, 2)
    if len(moves_df) > 0:
        ax2.hist(moves_df['move_pips'], bins=30, color='#3498db', alpha=0.7, edgecolor='black')
        ax2.axvline(30, color='red', linestyle='--', linewidth=2, label='30 pips threshold')
        ax2.axvline(moves_df['move_pips'].mean(), color='green', linestyle='--', 
                   linewidth=2, label=f'Avg: {moves_df["move_pips"].mean():.1f}p')
    ax2.set_title('Move Size Distribution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Pips', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    # 3. Moves by hour
    ax3 = plt.subplot(3, 2, 3)
    if len(moves_df) > 0:
        moves_df['hour'] = moves_df['entry_time'].dt.hour
        hour_counts = moves_df['hour'].value_counts().sort_index()
        ax3.bar(hour_counts.index, hour_counts.values, color='#2ecc71', alpha=0.7)
    ax3.set_title('Moves by Hour', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Hour of Day', fontsize=12)
    ax3.set_ylabel('Count', fontsize=12)
    ax3.set_xticks(range(0, 24, 2))
    ax3.grid(alpha=0.3)
    
    # 4. Caught vs Missed
    ax4 = plt.subplot(3, 2, 4)
    if len(moves_df) > 0:
        caught = len(moves_df[moves_df['caught'] == True])
        missed = len(moves_df[moves_df['caught'] == False])
        
        colors = ['#2ecc71', '#e74c3c']
        ax4.pie([caught, missed], labels=['Caught', 'Missed'], autopct='%1.1f%%',
               colors=colors, startangle=90)
    ax4.set_title('Caught vs Missed', fontsize=14, fontweight='bold')
    
    # 5. By direction
    ax5 = plt.subplot(3, 2, 5)
    if len(moves_df) > 0:
        direction_counts = moves_df['direction'].value_counts()
        colors_dir = {'LONG': '#2ecc71', 'SHORT': '#e74c3c'}
        colors_list = [colors_dir.get(d, '#95a5a6') for d in direction_counts.index]
        ax5.bar(range(len(direction_counts)), direction_counts.values, color=colors_list, alpha=0.7)
        ax5.set_xticks(range(len(direction_counts)))
        ax5.set_xticklabels(direction_counts.index)
    ax5.set_title('Moves by Direction', fontsize=14, fontweight='bold')
    ax5.set_ylabel('Count', fontsize=12)
    ax5.grid(alpha=0.3)
    
    # 6. Summary stats
    ax6 = plt.subplot(3, 2, 6)
    ax6.axis('off')
    
    total_moves = len(moves_df)
    caught = len(moves_df[moves_df['caught'] == True]) if len(moves_df) > 0 else 0
    missed = len(moves_df[moves_df['caught'] == False]) if len(moves_df) > 0 else 0
    
    avg_pips = moves_df['move_pips'].mean() if len(moves_df) > 0 else 0
    max_pips = moves_df['move_pips'].max() if len(moves_df) > 0 else 0
    total_pips = moves_df['move_pips'].sum() if len(moves_df) > 0 else 0
    
    missed_pips = moves_df[moves_df['caught'] == False]['move_pips'].sum() if missed > 0 else 0
    
    caught_pct = (caught/total_moves*100) if total_moves > 0 else 0
    missed_pct = (missed/total_moves*100) if total_moves > 0 else 0
    top_hour = moves_df['entry_time'].dt.hour.value_counts().index[0] if len(moves_df) > 0 else 0
    
    summary_text = f"""
30+ PIP MOVES SUMMARY

Total Moves: {total_moves}
------------------------
Caught:  {caught} ({caught_pct:.1f}%)
Missed:  {missed} ({missed_pct:.1f}%)

Move Statistics:
------------------------
Average: {avg_pips:.1f} pips
Maximum: {max_pips:.1f} pips
Total:   {total_pips:.0f} pips

Missed Potential:
------------------------
{missed_pips:.0f} pips (${missed_pips*0.10:.2f})

Top Hour:
------------------------
{top_hour:02d}:00
"""
    
    ax6.text(0.1, 0.5, summary_text, transform=ax6.transAxes,
             fontsize=11, verticalalignment='center',
             fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    plt.suptitle('30+ PIP MOVES ANALYSIS', fontsize=18, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig('30pip_moves_analysis.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ Visualization saved: 30pip_moves_analysis.png")


def main():
    print("\n" + "="*100)
    print("ДЕТЕКТОР ДВИЖЕНИЙ НА 30+ ПИПСОВ")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Find 30 pip moves
    moves_df = find_30pip_moves(df, min_pips=30, lookforward_candles=10)
    
    if len(moves_df) == 0:
        print("\n❌ No 30+ pip moves found!")
        return None, None
    
    # Analyze
    moves_df = analyze_30pip_moves(df, moves_df)
    
    # Compare with baseline
    moves_df = compare_with_baseline(df, moves_df)
    
    # Visualize
    visualize_30pip_moves(df, moves_df)
    
    # Save results
    moves_df.to_csv('30pip_moves_all.csv', index=False)
    
    missed_moves = moves_df[moves_df['caught'] == False].copy()
    missed_moves.to_csv('30pip_moves_missed.csv', index=False)
    
    caught_moves = moves_df[moves_df['caught'] == True].copy()
    caught_moves.to_csv('30pip_moves_caught.csv', index=False)
    
    print(f"\n💾 Results saved:")
    print(f"   - 30pip_moves_all.csv (все движения)")
    print(f"   - 30pip_moves_missed.csv (упущенные)")
    print(f"   - 30pip_moves_caught.csv (пойманные)")
    print(f"   - 30pip_moves_analysis.png (визуализация)")
    
    print("\n" + "="*100)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("="*100)
    
    return moves_df, missed_moves


if __name__ == "__main__":
    moves_df, missed_moves = main()
