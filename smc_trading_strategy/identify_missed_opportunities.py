"""
Идентификация упущенных возможностей

Находим места где:
1. Было сильное движение (>2%, >3%, >5%)
2. У нас не было сигнала или мы вышли рано
3. Анализируем что было перед этим движением
4. Создаем правила для идентификации таких мест
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2


def find_strong_moves(df, min_move_pct=2.0, lookforward_candles=10):
    """
    Находим все сильные движения в данных
    
    Args:
        df: DataFrame с данными
        min_move_pct: минимальное движение в % для поиска
        lookforward_candles: сколько свечей смотрим вперед
    """
    
    print(f"\n🔍 Searching for strong moves (>{min_move_pct}%)...")
    
    strong_moves = []
    
    for i in range(len(df) - lookforward_candles):
        current_price = df['close'].iloc[i]
        
        # Look forward
        future_prices = df['high'].iloc[i+1:i+lookforward_candles+1]
        max_future_price = future_prices.max()
        
        # Calculate potential profit for LONG
        potential_profit = ((max_future_price - current_price) / current_price) * 100
        
        if potential_profit >= min_move_pct:
            # Find when max was reached
            max_idx_relative = future_prices.argmax()
            max_time = future_prices.index[max_idx_relative]
            candles_to_max = max_idx_relative + 1
            
            # Calculate indicators at entry point
            entry_time = df.index[i]
            
            strong_moves.append({
                'entry_time': entry_time,
                'entry_price': current_price,
                'max_price': max_future_price,
                'max_time': max_time,
                'potential_profit': potential_profit,
                'candles_to_max': candles_to_max,
                'entry_idx': i
            })
    
    print(f"   Found {len(strong_moves)} strong moves (>{min_move_pct}%)")
    
    return pd.DataFrame(strong_moves)


def analyze_market_conditions(df, moves_df):
    """
    Анализируем рыночные условия перед сильными движениями
    """
    
    print(f"\n📊 Analyzing market conditions before strong moves...")
    
    # Calculate indicators
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    df['rsi'] = rsi
    
    # ATR
    high_low = df['high'] - df['low']
    atr = high_low.rolling(window=14).mean()
    df['atr'] = atr
    
    # Volume
    df['volume_ma20'] = df['volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma20']
    
    # Price change
    df['price_change_1h'] = df['close'].pct_change(1) * 100
    df['price_change_3h'] = df['close'].pct_change(3) * 100
    df['price_change_5h'] = df['close'].pct_change(5) * 100
    
    # MA crossovers
    df['ma_5'] = df['close'].rolling(window=5).mean()
    df['ma_20'] = df['close'].rolling(window=20).mean()
    df['ma_50'] = df['close'].rolling(window=50).mean()
    
    # Add conditions to moves
    for idx, move in moves_df.iterrows():
        entry_idx = move['entry_idx']
        
        if entry_idx >= 50:  # Ensure we have enough history
            moves_df.loc[idx, 'rsi'] = df['rsi'].iloc[entry_idx]
            moves_df.loc[idx, 'atr'] = df['atr'].iloc[entry_idx]
            moves_df.loc[idx, 'volume_ratio'] = df['volume_ratio'].iloc[entry_idx]
            moves_df.loc[idx, 'price_change_1h'] = df['price_change_1h'].iloc[entry_idx]
            moves_df.loc[idx, 'price_change_3h'] = df['price_change_3h'].iloc[entry_idx]
            moves_df.loc[idx, 'ma_5'] = df['ma_5'].iloc[entry_idx]
            moves_df.loc[idx, 'ma_20'] = df['ma_20'].iloc[entry_idx]
            moves_df.loc[idx, 'ma_50'] = df['ma_50'].iloc[entry_idx]
            moves_df.loc[idx, 'price_vs_ma5'] = (df['close'].iloc[entry_idx] / df['ma_5'].iloc[entry_idx] - 1) * 100
            moves_df.loc[idx, 'price_vs_ma20'] = (df['close'].iloc[entry_idx] / df['ma_20'].iloc[entry_idx] - 1) * 100
            
            # Trend direction
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
    
    return moves_df


def compare_with_strategy_signals(df, moves_df, strategy):
    """
    Сравниваем упущенные возможности с сигналами стратегии
    """
    
    print(f"\n🎯 Comparing with strategy signals...")
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    print(f"   Strategy generated {len(df_signals)} signals")
    
    # For each strong move, check if we had a signal
    moves_df['had_signal'] = False
    moves_df['signal_time'] = None
    moves_df['days_before_signal'] = None
    
    for idx, move in moves_df.iterrows():
        entry_time = move['entry_time']
        
        # Check if we had signal within 1 hour before this move
        nearby_signals = df_signals[
            (df_signals.index >= entry_time - timedelta(hours=1)) &
            (df_signals.index <= entry_time)
        ]
        
        if len(nearby_signals) > 0:
            moves_df.loc[idx, 'had_signal'] = True
            moves_df.loc[idx, 'signal_time'] = nearby_signals.index[0]
    
    caught = len(moves_df[moves_df['had_signal'] == True])
    missed = len(moves_df[moves_df['had_signal'] == False])
    
    print(f"   Caught: {caught} ({caught/len(moves_df)*100:.1f}%)")
    print(f"   Missed: {missed} ({missed/len(moves_df)*100:.1f}%)")
    
    return moves_df, df_signals


def analyze_missed_patterns(df, missed_moves):
    """
    Анализируем паттерны упущенных возможностей
    """
    
    print(f"\n🔍 ANALYZING MISSED OPPORTUNITIES ({len(missed_moves)} moves)")
    print("="*100)
    
    if len(missed_moves) == 0:
        print("   No missed opportunities!")
        return {}
    
    # 1. RSI analysis
    print(f"\n📊 RSI Distribution:")
    rsi_bins = [0, 30, 40, 50, 60, 70, 100]
    rsi_labels = ['<30', '30-40', '40-50', '50-60', '60-70', '>70']
    missed_moves['rsi_bin'] = pd.cut(missed_moves['rsi'], bins=rsi_bins, labels=rsi_labels)
    
    rsi_counts = missed_moves['rsi_bin'].value_counts().sort_index()
    for label, count in rsi_counts.items():
        pct = count / len(missed_moves) * 100
        avg_profit = missed_moves[missed_moves['rsi_bin'] == label]['potential_profit'].mean()
        print(f"   {label:8s}: {count:3d} moves ({pct:5.1f}%) - Avg profit: {avg_profit:+.2f}%")
    
    # 2. Trend analysis
    print(f"\n📈 Trend Distribution:")
    trend_counts = missed_moves['trend'].value_counts()
    for trend, count in trend_counts.items():
        pct = count / len(missed_moves) * 100
        avg_profit = missed_moves[missed_moves['trend'] == trend]['potential_profit'].mean()
        print(f"   {trend:15s}: {count:3d} moves ({pct:5.1f}%) - Avg profit: {avg_profit:+.2f}%")
    
    # 3. Volume analysis
    print(f"\n📊 Volume Ratio:")
    high_volume = missed_moves[missed_moves['volume_ratio'] > 1.5]
    normal_volume = missed_moves[(missed_moves['volume_ratio'] >= 0.8) & (missed_moves['volume_ratio'] <= 1.5)]
    low_volume = missed_moves[missed_moves['volume_ratio'] < 0.8]
    
    print(f"   High (>1.5):    {len(high_volume):3d} moves - Avg profit: {high_volume['potential_profit'].mean():+.2f}%")
    print(f"   Normal (0.8-1.5): {len(normal_volume):3d} moves - Avg profit: {normal_volume['potential_profit'].mean():+.2f}%")
    print(f"   Low (<0.8):     {len(low_volume):3d} moves - Avg profit: {low_volume['potential_profit'].mean():+.2f}%")
    
    # 4. Price position vs MA
    print(f"\n📍 Price Position vs MA20:")
    above_ma = missed_moves[missed_moves['price_vs_ma20'] > 0]
    below_ma = missed_moves[missed_moves['price_vs_ma20'] < 0]
    
    print(f"   Above MA20: {len(above_ma):3d} moves - Avg profit: {above_ma['potential_profit'].mean():+.2f}%")
    print(f"   Below MA20: {len(below_ma):3d} moves - Avg profit: {below_ma['potential_profit'].mean():+.2f}%")
    
    # 5. Time analysis
    print(f"\n⏰ Hour of Day:")
    missed_moves['hour'] = missed_moves['entry_time'].dt.hour
    hour_counts = missed_moves['hour'].value_counts().sort_index()
    
    # Show top 5 hours
    top_hours = hour_counts.nlargest(5)
    for hour, count in top_hours.items():
        hour_moves = missed_moves[missed_moves['hour'] == hour]
        avg_profit = hour_moves['potential_profit'].mean()
        print(f"   {hour:02d}:00 - {count:3d} moves - Avg profit: {avg_profit:+.2f}%")
    
    # 6. Best opportunities
    print(f"\n💰 TOP 10 MISSED OPPORTUNITIES:")
    print(f"{'Date':<20} {'Entry':<10} {'Max Price':<10} {'Profit':<10} {'Candles':<10} {'RSI':<8} {'Trend':<15}")
    print("-"*100)
    
    top_missed = missed_moves.nlargest(10, 'potential_profit')
    for _, move in top_missed.iterrows():
        print(f"{str(move['entry_time']):<20} "
              f"{move['entry_price']:<10.2f} "
              f"{move['max_price']:<10.2f} "
              f"{move['potential_profit']:>8.2f}% "
              f"{move['candles_to_max']:>9} "
              f"{move['rsi']:>7.1f} "
              f"{move['trend']:<15}")
    
    return {
        'rsi_distribution': rsi_counts,
        'trend_distribution': trend_counts,
        'top_missed': top_missed
    }


def identify_common_patterns(missed_moves):
    """
    Выявляем общие паттерны в упущенных возможностях
    """
    
    print(f"\n" + "="*100)
    print("💡 IDENTIFIED PATTERNS FOR MISSED OPPORTUNITIES")
    print("="*100)
    
    patterns = []
    
    # Pattern 1: RSI pullback in uptrend
    pattern1 = missed_moves[
        (missed_moves['rsi'] < 50) &
        (missed_moves['trend'].isin(['up', 'strong_up'])) &
        (missed_moves['price_vs_ma20'] > -2)
    ]
    
    if len(pattern1) > 0:
        avg_profit = pattern1['potential_profit'].mean()
        patterns.append({
            'name': 'RSI Pullback in Uptrend',
            'description': 'RSI < 50, trend UP, price near MA20',
            'count': len(pattern1),
            'avg_profit': avg_profit,
            'conditions': 'RSI < 50 AND trend = UP AND price > MA20-2%'
        })
        print(f"\n1️⃣  RSI Pullback in Uptrend")
        print(f"   Conditions: RSI < 50 AND trend UP AND price near MA20")
        print(f"   Occurrences: {len(pattern1)}")
        print(f"   Avg Profit: {avg_profit:+.2f}%")
        print(f"   📍 This is a BUY THE DIP opportunity!")
    
    # Pattern 2: Breakout with volume
    pattern2 = missed_moves[
        (missed_moves['volume_ratio'] > 1.5) &
        (missed_moves['price_change_1h'] > 0.3) &
        (missed_moves['rsi'] > 50)
    ]
    
    if len(pattern2) > 0:
        avg_profit = pattern2['potential_profit'].mean()
        patterns.append({
            'name': 'Volume Breakout',
            'description': 'High volume + momentum + RSI > 50',
            'count': len(pattern2),
            'avg_profit': avg_profit,
            'conditions': 'Volume > 1.5x AND price_change_1h > 0.3% AND RSI > 50'
        })
        print(f"\n2️⃣  Volume Breakout")
        print(f"   Conditions: Volume > 1.5x AND momentum > 0.3% AND RSI > 50")
        print(f"   Occurrences: {len(pattern2)}")
        print(f"   Avg Profit: {avg_profit:+.2f}%")
        print(f"   🚀 This is a MOMENTUM opportunity!")
    
    # Pattern 3: Strong uptrend continuation
    pattern3 = missed_moves[
        (missed_moves['trend'] == 'strong_up') &
        (missed_moves['rsi'] > 40) &
        (missed_moves['rsi'] < 65) &
        (missed_moves['price_vs_ma5'] < 1)
    ]
    
    if len(pattern3) > 0:
        avg_profit = pattern3['potential_profit'].mean()
        patterns.append({
            'name': 'Strong Uptrend Continuation',
            'description': 'Strong uptrend, RSI 40-65, price near MA5',
            'count': len(pattern3),
            'avg_profit': avg_profit,
            'conditions': 'trend = strong_up AND RSI 40-65 AND price near MA5'
        })
        print(f"\n3️⃣  Strong Uptrend Continuation")
        print(f"   Conditions: Strong uptrend AND RSI 40-65 AND price near MA5")
        print(f"   Occurrences: {len(pattern3)}")
        print(f"   Avg Profit: {avg_profit:+.2f}%")
        print(f"   📈 This is a TREND FOLLOWING opportunity!")
    
    # Pattern 4: Oversold bounce
    pattern4 = missed_moves[
        (missed_moves['rsi'] < 35) &
        (missed_moves['price_vs_ma20'] < -1) &
        (missed_moves['trend'] != 'strong_down')
    ]
    
    if len(pattern4) > 0:
        avg_profit = pattern4['potential_profit'].mean()
        patterns.append({
            'name': 'Oversold Bounce',
            'description': 'RSI < 35, price below MA20, not in downtrend',
            'count': len(pattern4),
            'avg_profit': avg_profit,
            'conditions': 'RSI < 35 AND price < MA20-1% AND trend != strong_down'
        })
        print(f"\n4️⃣  Oversold Bounce")
        print(f"   Conditions: RSI < 35 AND price below MA20 AND not strong downtrend")
        print(f"   Occurrences: {len(pattern4)}")
        print(f"   Avg Profit: {avg_profit:+.2f}%")
        print(f"   ⚡ This is a MEAN REVERSION opportunity!")
    
    # Summary
    print(f"\n" + "="*100)
    print(f"📊 PATTERNS SUMMARY")
    print(f"="*100)
    
    if len(patterns) > 0:
        patterns_df = pd.DataFrame(patterns)
        patterns_df = patterns_df.sort_values('avg_profit', ascending=False)
        
        print(f"\n{'Pattern':<30} {'Count':<10} {'Avg Profit':<15} {'Total Missed Profit':<20}")
        print("-"*75)
        
        for _, pattern in patterns_df.iterrows():
            total_missed = pattern['count'] * pattern['avg_profit']
            print(f"{pattern['name']:<30} {pattern['count']:<10} {pattern['avg_profit']:>13.2f}% {total_missed:>18.2f}%")
        
        total_opportunities = patterns_df['count'].sum()
        total_missed_profit = (patterns_df['count'] * patterns_df['avg_profit']).sum()
        
        print("-"*75)
        print(f"{'TOTAL':<30} {total_opportunities:<10} {'':15s} {total_missed_profit:>18.2f}%")
        
        print(f"\n💰 If we catch these patterns, we could add ~{total_missed_profit:.0f}% to our PnL!")
    
    return patterns


def visualize_missed_opportunities(df, missed_moves, caught_moves):
    """
    Визуализация упущенных возможностей
    """
    
    fig = plt.figure(figsize=(20, 12))
    
    # 1. Price chart with missed opportunities
    ax1 = plt.subplot(3, 2, 1)
    ax1.plot(df.index, df['close'], color='blue', alpha=0.5, linewidth=1)
    
    # Mark missed opportunities
    if len(missed_moves) > 0:
        ax1.scatter(missed_moves['entry_time'], missed_moves['entry_price'],
                   color='red', s=100, alpha=0.6, label='Missed', marker='v')
    
    # Mark caught opportunities
    if len(caught_moves) > 0:
        ax1.scatter(caught_moves['entry_time'], caught_moves['entry_price'],
                   color='green', s=100, alpha=0.6, label='Caught', marker='^')
    
    ax1.set_title('Price Chart: Caught vs Missed Opportunities', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price', fontsize=12)
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # 2. Profit distribution
    ax2 = plt.subplot(3, 2, 2)
    if len(missed_moves) > 0:
        ax2.hist(missed_moves['potential_profit'], bins=30, color='red', alpha=0.6, label='Missed')
    if len(caught_moves) > 0:
        ax2.hist(caught_moves['potential_profit'], bins=30, color='green', alpha=0.6, label='Caught')
    ax2.set_title('Profit Distribution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Potential Profit (%)', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    # 3. RSI distribution
    ax3 = plt.subplot(3, 2, 3)
    if len(missed_moves) > 0:
        ax3.hist(missed_moves['rsi'], bins=20, color='red', alpha=0.6, label='Missed', range=(0, 100))
    if len(caught_moves) > 0:
        ax3.hist(caught_moves['rsi'], bins=20, color='green', alpha=0.6, label='Caught', range=(0, 100))
    ax3.axvline(30, color='orange', linestyle='--', label='Oversold')
    ax3.axvline(70, color='orange', linestyle='--', label='Overbought')
    ax3.set_title('RSI at Entry', fontsize=14, fontweight='bold')
    ax3.set_xlabel('RSI', fontsize=12)
    ax3.set_ylabel('Frequency', fontsize=12)
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    # 4. Hour distribution
    ax4 = plt.subplot(3, 2, 4)
    if len(missed_moves) > 0:
        missed_hours = missed_moves['entry_time'].dt.hour.value_counts().sort_index()
        ax4.bar(missed_hours.index, missed_hours.values, color='red', alpha=0.6, label='Missed', width=0.8)
    ax4.set_title('Hour Distribution (Missed)', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Hour of Day', fontsize=12)
    ax4.set_ylabel('Count', fontsize=12)
    ax4.set_xticks(range(0, 24, 2))
    ax4.legend()
    ax4.grid(alpha=0.3)
    
    # 5. Trend distribution
    ax5 = plt.subplot(3, 2, 5)
    if len(missed_moves) > 0:
        trend_counts = missed_moves['trend'].value_counts()
        colors = {'strong_up': '#2ecc71', 'up': '#3498db', 'sideways': '#95a5a6', 
                 'down': '#e67e22', 'strong_down': '#e74c3c'}
        trend_colors = [colors.get(t, '#95a5a6') for t in trend_counts.index]
        ax5.bar(range(len(trend_counts)), trend_counts.values, color=trend_colors, alpha=0.7)
        ax5.set_xticks(range(len(trend_counts)))
        ax5.set_xticklabels(trend_counts.index, rotation=45, ha='right')
    ax5.set_title('Trend Distribution (Missed)', fontsize=14, fontweight='bold')
    ax5.set_ylabel('Count', fontsize=12)
    ax5.grid(alpha=0.3)
    
    # 6. Summary stats
    ax6 = plt.subplot(3, 2, 6)
    ax6.axis('off')
    
    total_moves = len(missed_moves) + len(caught_moves)
    missed_pct = len(missed_moves) / total_moves * 100 if total_moves > 0 else 0
    caught_pct = len(caught_moves) / total_moves * 100 if total_moves > 0 else 0
    
    avg_missed_profit = missed_moves['potential_profit'].mean() if len(missed_moves) > 0 else 0
    avg_caught_profit = caught_moves['potential_profit'].mean() if len(caught_moves) > 0 else 0
    
    total_missed_profit = missed_moves['potential_profit'].sum() if len(missed_moves) > 0 else 0
    
    summary_text = f"""
MISSED OPPORTUNITIES SUMMARY

Total Strong Moves: {total_moves}
------------------------
Caught:  {len(caught_moves):3d} ({caught_pct:5.1f}%)
Missed:  {len(missed_moves):3d} ({missed_pct:5.1f}%)

Average Profit:
------------------------
Caught:  {avg_caught_profit:+.2f}%
Missed:  {avg_missed_profit:+.2f}%

Total Missed Profit: {total_missed_profit:+.1f}%

Top Missed Hours:
------------------------
{', '.join([f'{h:02d}:00' for h in missed_moves['entry_time'].dt.hour.value_counts().nlargest(3).index.tolist()]) if len(missed_moves) > 0 else 'N/A'}

Most Common Trend:
------------------------
{missed_moves['trend'].value_counts().index[0] if len(missed_moves) > 0 else 'N/A'}
"""
    
    ax6.text(0.1, 0.5, summary_text, transform=ax6.transAxes,
             fontsize=11, verticalalignment='center',
             fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    plt.suptitle('MISSED OPPORTUNITIES ANALYSIS', fontsize=18, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig('missed_opportunities_analysis.png', dpi=150, bbox_inches='tight')
    print("\n✅ Visualization saved: missed_opportunities_analysis.png")


def main():
    print("\n" + "="*100)
    print("IDENTIFICATION OF MISSED OPPORTUNITIES")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Find strong moves (>3%)
    moves_df = find_strong_moves(df, min_move_pct=3.0, lookforward_candles=10)
    
    # Analyze market conditions
    moves_df = analyze_market_conditions(df, moves_df)
    
    # Initialize strategy
    print("\n🚀 Initializing optimized strategy...")
    strategy = PatternRecognitionOptimizedV2(
        fib_mode='standard',
        tp_multiplier=1.4,
        long_only=True
    )
    
    # Compare with strategy signals
    moves_df, df_signals = compare_with_strategy_signals(df, moves_df, strategy)
    
    # Separate caught and missed
    caught_moves = moves_df[moves_df['had_signal'] == True].copy()
    missed_moves = moves_df[moves_df['had_signal'] == False].copy()
    
    # Analyze missed patterns
    analysis_results = analyze_missed_patterns(df, missed_moves)
    
    # Identify common patterns
    patterns = identify_common_patterns(missed_moves)
    
    # Visualize
    visualize_missed_opportunities(df, missed_moves, caught_moves)
    
    # Save results
    missed_moves.to_csv('missed_opportunities.csv', index=False)
    caught_moves.to_csv('caught_opportunities.csv', index=False)
    
    print(f"\n💾 Results saved:")
    print(f"   - missed_opportunities.csv")
    print(f"   - caught_opportunities.csv")
    print(f"   - missed_opportunities_analysis.png")
    
    return moves_df, missed_moves, caught_moves, patterns


if __name__ == "__main__":
    moves_df, missed_moves, caught_moves, patterns = main()
