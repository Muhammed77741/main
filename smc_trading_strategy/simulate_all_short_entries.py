"""
Симуляция ВСЕХ SHORT входов с детальным контекстом
Цель: найти закономерность почему SHORT плохие
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from pattern_recognition_strategy import PatternRecognitionStrategy


def load_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load H1 data with indicators"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    # Add indicators
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100
    
    # EMAs
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['ema_200'] = df['close'].ewm(span=200).mean()
    
    # Trend
    df['is_uptrend'] = (df['ema_20'] > df['ema_50']) & (df['ema_50'] > df['ema_200'])
    df['is_downtrend'] = (df['ema_20'] < df['ema_50']) & (df['ema_50'] < df['ema_200'])
    
    # Price position relative to EMAs
    df['above_ema_20'] = df['close'] > df['ema_20']
    df['above_ema_50'] = df['close'] > df['ema_50']
    df['above_ema_200'] = df['close'] > df['ema_200']
    
    # Distance from EMAs (%)
    df['dist_from_ema_20'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100
    df['dist_from_ema_50'] = (df['close'] - df['ema_50']) / df['ema_50'] * 100
    df['dist_from_ema_200'] = (df['close'] - df['ema_200']) / df['ema_200'] * 100
    
    # Recent price action
    df['recent_high_5'] = df['high'].rolling(5).max()
    df['recent_low_5'] = df['low'].rolling(5).min()
    df['at_recent_high'] = df['close'] >= df['recent_high_5'] * 0.999
    df['at_recent_low'] = df['close'] <= df['recent_low_5'] * 1.001
    
    # Momentum
    df['roc_5'] = df['close'].pct_change(5) * 100  # Rate of change last 5 bars
    df['roc_10'] = df['close'].pct_change(10) * 100
    
    # Candle type
    df['candle_size'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['open'] * 100
    df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['open'] * 100
    
    return df


def simulate_all_short_entries(df, strategy):
    """Simulate ALL SHORT entries with detailed context"""
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    
    # Get only SHORT signals
    df_short_signals = df_strategy[df_strategy['signal'] == -1].copy()
    
    print(f"\n📊 Найдено SHORT сигналов: {len(df_short_signals)}")
    
    short_trades = []
    
    for i in range(len(df_short_signals)):
        signal = df_short_signals.iloc[i]
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        entry_time = df_short_signals.index[i]
        entry_idx = df.index.get_loc(entry_time) if entry_time in df.index else None
        
        if entry_idx is None:
            continue
        
        # Get market context at entry
        context = {
            'entry_time': entry_time,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'hour': entry_time.hour,
            'day_of_week': entry_time.dayofweek,  # 0=Monday, 6=Sunday
            
            # Trend
            'is_uptrend': df['is_uptrend'].iloc[entry_idx],
            'is_downtrend': df['is_downtrend'].iloc[entry_idx],
            
            # Position relative to EMAs
            'above_ema_20': df['above_ema_20'].iloc[entry_idx],
            'above_ema_50': df['above_ema_50'].iloc[entry_idx],
            'above_ema_200': df['above_ema_200'].iloc[entry_idx],
            'dist_from_ema_20': df['dist_from_ema_20'].iloc[entry_idx],
            'dist_from_ema_50': df['dist_from_ema_50'].iloc[entry_idx],
            
            # Price action
            'at_recent_high': df['at_recent_high'].iloc[entry_idx],
            'at_recent_low': df['at_recent_low'].iloc[entry_idx],
            
            # Momentum
            'roc_5': df['roc_5'].iloc[entry_idx],
            'roc_10': df['roc_10'].iloc[entry_idx],
            
            # Volatility
            'atr': df['atr'].iloc[entry_idx],
            'atr_pct': df['atr_pct'].iloc[entry_idx],
            
            # Candle characteristics
            'candle_size': df['candle_size'].iloc[entry_idx-1] if entry_idx > 0 else 0,
            'upper_shadow': df['upper_shadow'].iloc[entry_idx-1] if entry_idx > 0 else 0,
            'lower_shadow': df['lower_shadow'].iloc[entry_idx-1] if entry_idx > 0 else 0,
        }
        
        # Simulate trade
        search_end = entry_time + timedelta(hours=48)
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        exit_price = None
        exit_type = None
        exit_time = None
        bars_in_trade = 0
        max_drawdown = 0
        max_profit = 0
        
        # Track price movement
        for j in range(len(df_future)):
            bars_in_trade += 1
            
            # Calculate unrealized P&L
            current_price = df_future['close'].iloc[j]
            unrealized_pnl = ((entry_price - current_price) / entry_price) * 100
            
            if unrealized_pnl > max_profit:
                max_profit = unrealized_pnl
            if unrealized_pnl < max_drawdown:
                max_drawdown = unrealized_pnl
            
            # Check exit
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
        
        # Calculate final PnL
        pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        # Add trade results to context
        context.update({
            'exit_time': exit_time,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'bars_in_trade': bars_in_trade,
            'pnl_pct': pnl_pct,
            'max_profit': max_profit,
            'max_drawdown': max_drawdown,
            'is_win': pnl_pct > 0
        })
        
        short_trades.append(context)
    
    return pd.DataFrame(short_trades)


def analyze_patterns(df_trades):
    """Find patterns in SHORT trades"""
    
    print("\n" + "="*100)
    print("🔍 АНАЛИЗ ЗАКОНОМЕРНОСТЕЙ В SHORT СДЕЛКАХ")
    print("="*100)
    
    wins = df_trades[df_trades['is_win'] == True]
    losses = df_trades[df_trades['is_win'] == False]
    
    print(f"\n📊 Базовая статистика:")
    print(f"   Всего SHORT: {len(df_trades)}")
    print(f"   Выигрышные: {len(wins)} ({len(wins)/len(df_trades)*100:.1f}%)")
    print(f"   Проигрышные: {len(losses)} ({len(losses)/len(df_trades)*100:.1f}%)")
    
    # Pattern 1: Trend context
    print("\n" + "="*100)
    print("📊 ЗАКОНОМЕРНОСТЬ #1: ТРЕНД")
    print("="*100)
    
    print(f"\n{'Контекст':<30} | {'Выигрышные':<15} | {'Проигрышные':<15} | {'Win Rate':<10}")
    print("-" * 75)
    
    patterns = [
        ('Uptrend', df_trades[df_trades['is_uptrend'] == True]),
        ('Downtrend', df_trades[df_trades['is_downtrend'] == True]),
        ('Sideways', df_trades[(df_trades['is_uptrend'] == False) & (df_trades['is_downtrend'] == False)])
    ]
    
    for name, subset in patterns:
        if len(subset) > 0:
            wins_count = len(subset[subset['is_win'] == True])
            losses_count = len(subset[subset['is_win'] == False])
            wr = wins_count / len(subset) * 100
            emoji = "✅" if wr >= 50 else "❌"
            print(f"{name:<30} {emoji} | {wins_count:<15} | {losses_count:<15} | {wr:<10.1f}%")
    
    # Pattern 2: Price position relative to EMAs
    print("\n" + "="*100)
    print("📊 ЗАКОНОМЕРНОСТЬ #2: ПОЗИЦИЯ ОТНОСИТЕЛЬНО EMA")
    print("="*100)
    
    print(f"\n{'Позиция':<30} | {'Выигрышные':<15} | {'Проигрышные':<15} | {'Win Rate':<10}")
    print("-" * 75)
    
    ema_patterns = [
        ('Выше EMA20', df_trades[df_trades['above_ema_20'] == True]),
        ('Ниже EMA20', df_trades[df_trades['above_ema_20'] == False]),
        ('Выше EMA50', df_trades[df_trades['above_ema_50'] == True]),
        ('Ниже EMA50', df_trades[df_trades['above_ema_50'] == False]),
        ('Выше EMA200', df_trades[df_trades['above_ema_200'] == True]),
        ('Ниже EMA200', df_trades[df_trades['above_ema_200'] == False]),
    ]
    
    for name, subset in ema_patterns:
        if len(subset) > 0:
            wins_count = len(subset[subset['is_win'] == True])
            losses_count = len(subset[subset['is_win'] == False])
            wr = wins_count / len(subset) * 100
            emoji = "✅" if wr >= 50 else "❌"
            print(f"{name:<30} {emoji} | {wins_count:<15} | {losses_count:<15} | {wr:<10.1f}%")
    
    # Pattern 3: Price action context
    print("\n" + "="*100)
    print("📊 ЗАКОНОМЕРНОСТЬ #3: КОНТЕКСТ ВХОДА")
    print("="*100)
    
    print(f"\n{'Контекст':<30} | {'Выигрышные':<15} | {'Проигрышные':<15} | {'Win Rate':<10}")
    print("-" * 75)
    
    entry_patterns = [
        ('На недавнем хае', df_trades[df_trades['at_recent_high'] == True]),
        ('НЕ на недавнем хае', df_trades[df_trades['at_recent_high'] == False]),
        ('На недавнем лое', df_trades[df_trades['at_recent_low'] == True]),
        ('НЕ на недавнем лое', df_trades[df_trades['at_recent_low'] == False]),
    ]
    
    for name, subset in entry_patterns:
        if len(subset) > 0:
            wins_count = len(subset[subset['is_win'] == True])
            losses_count = len(subset[subset['is_win'] == False])
            wr = wins_count / len(subset) * 100
            emoji = "✅" if wr >= 50 else "❌"
            print(f"{name:<30} {emoji} | {wins_count:<15} | {losses_count:<15} | {wr:<10.1f}%")
    
    # Pattern 4: Momentum
    print("\n" + "="*100)
    print("📊 ЗАКОНОМЕРНОСТЬ #4: MOMENTUM (ROC)")
    print("="*100)
    
    print(f"\n{'Momentum':<30} | {'Выигрышные':<15} | {'Проигрышные':<15} | {'Win Rate':<10}")
    print("-" * 75)
    
    momentum_patterns = [
        ('ROC5 > 0 (растет)', df_trades[df_trades['roc_5'] > 0]),
        ('ROC5 < 0 (падает)', df_trades[df_trades['roc_5'] < 0]),
        ('ROC10 > 0 (растет)', df_trades[df_trades['roc_10'] > 0]),
        ('ROC10 < 0 (падает)', df_trades[df_trades['roc_10'] < 0]),
    ]
    
    for name, subset in momentum_patterns:
        if len(subset) > 0:
            wins_count = len(subset[subset['is_win'] == True])
            losses_count = len(subset[subset['is_win'] == False])
            wr = wins_count / len(subset) * 100
            emoji = "✅" if wr >= 50 else "❌"
            print(f"{name:<30} {emoji} | {wins_count:<15} | {losses_count:<15} | {wr:<10.1f}%")
    
    # Pattern 5: Distance from EMA
    print("\n" + "="*100)
    print("📊 ЗАКОНОМЕРНОСТЬ #5: ДИСТАНЦИЯ ОТ EMA20")
    print("="*100)
    
    print(f"\n{'Дистанция от EMA20':<30} | {'Выигрышные':<15} | {'Проигрышные':<15} | {'Win Rate':<10} | {'Avg Dist':<10}")
    print("-" * 90)
    
    dist_ranges = [
        ('> +1% (далеко сверху)', df_trades[df_trades['dist_from_ema_20'] > 1]),
        ('+0.5% до +1%', df_trades[(df_trades['dist_from_ema_20'] > 0.5) & (df_trades['dist_from_ema_20'] <= 1)]),
        ('0% до +0.5%', df_trades[(df_trades['dist_from_ema_20'] > 0) & (df_trades['dist_from_ema_20'] <= 0.5)]),
        ('-0.5% до 0%', df_trades[(df_trades['dist_from_ema_20'] >= -0.5) & (df_trades['dist_from_ema_20'] <= 0)]),
        ('< -0.5% (далеко снизу)', df_trades[df_trades['dist_from_ema_20'] < -0.5]),
    ]
    
    for name, subset in dist_ranges:
        if len(subset) > 0:
            wins_count = len(subset[subset['is_win'] == True])
            losses_count = len(subset[subset['is_win'] == False])
            wr = wins_count / len(subset) * 100
            avg_dist = subset['dist_from_ema_20'].mean()
            emoji = "✅" if wr >= 50 else "❌"
            print(f"{name:<30} {emoji} | {wins_count:<15} | {losses_count:<15} | {wr:<10.1f}% | {avg_dist:<+10.2f}%")
    
    # Pattern 6: Hour of day
    print("\n" + "="*100)
    print("📊 ЗАКОНОМЕРНОСТЬ #6: ВРЕМЯ ВХОДА")
    print("="*100)
    
    print(f"\n{'Час':<10} | {'Сделок':<10} | {'Выигрышные':<15} | {'Проигрышные':<15} | {'Win Rate':<10}")
    print("-" * 70)
    
    for hour in sorted(df_trades['hour'].unique()):
        subset = df_trades[df_trades['hour'] == hour]
        wins_count = len(subset[subset['is_win'] == True])
        losses_count = len(subset[subset['is_win'] == False])
        wr = wins_count / len(subset) * 100
        emoji = "✅" if wr >= 50 else "❌"
        print(f"{hour:02d}:00 {emoji}   | {len(subset):<10} | {wins_count:<15} | {losses_count:<15} | {wr:<10.1f}%")


def find_best_short_conditions(df_trades):
    """Find the BEST conditions for SHORT"""
    
    print("\n" + "="*100)
    print("🏆 ПОИСК ЛУЧШИХ УСЛОВИЙ ДЛЯ SHORT")
    print("="*100)
    
    # Find combinations with WR > 50%
    best_conditions = []
    
    # Condition 1: Downtrend + Below EMA20
    cond1 = df_trades[
        (df_trades['is_downtrend'] == True) &
        (df_trades['above_ema_20'] == False)
    ]
    if len(cond1) > 0:
        wr1 = len(cond1[cond1['is_win'] == True]) / len(cond1) * 100
        best_conditions.append(('Downtrend + Below EMA20', len(cond1), wr1))
    
    # Condition 2: At recent high + ROC negative
    cond2 = df_trades[
        (df_trades['at_recent_high'] == True) &
        (df_trades['roc_5'] < 0)
    ]
    if len(cond2) > 0:
        wr2 = len(cond2[cond2['is_win'] == True]) / len(cond2) * 100
        best_conditions.append(('At recent high + ROC negative', len(cond2), wr2))
    
    # Condition 3: Far above EMA20 (> +1%) - potential reversal
    cond3 = df_trades[df_trades['dist_from_ema_20'] > 1]
    if len(cond3) > 0:
        wr3 = len(cond3[cond3['is_win'] == True]) / len(cond3) * 100
        best_conditions.append(('Far above EMA20 (>+1%)', len(cond3), wr3))
    
    # Condition 4: Specific hours with WR > 40%
    good_hours = []
    for hour in sorted(df_trades['hour'].unique()):
        subset = df_trades[df_trades['hour'] == hour]
        if len(subset) >= 5:  # At least 5 trades
            wr = len(subset[subset['is_win'] == True]) / len(subset) * 100
            if wr >= 40:
                good_hours.append(hour)
    
    if len(good_hours) > 0:
        cond4 = df_trades[df_trades['hour'].isin(good_hours)]
        wr4 = len(cond4[cond4['is_win'] == True]) / len(cond4) * 100
        best_conditions.append((f'Good hours {good_hours}', len(cond4), wr4))
    
    # Display best conditions
    print(f"\n{'Условие':<50} | {'Сделок':<10} | {'Win Rate':<10}")
    print("-" * 75)
    
    for cond_name, count, wr in sorted(best_conditions, key=lambda x: x[2], reverse=True):
        emoji = "✅" if wr >= 50 else "⚠️" if wr >= 40 else "❌"
        print(f"{cond_name:<50} {emoji} | {count:<10} | {wr:<10.1f}%")
    
    # ULTIMATE test: Combine best conditions
    print(f"\n" + "="*100)
    print("🎯 КОМБИНАЦИЯ ЛУЧШИХ УСЛОВИЙ")
    print("="*100)
    
    ultimate = df_trades[
        (df_trades['is_downtrend'] == True) &
        (df_trades['above_ema_20'] == False) &
        (df_trades['roc_5'] < 0)
    ]
    
    if len(ultimate) > 0:
        ultimate_wr = len(ultimate[ultimate['is_win'] == True]) / len(ultimate) * 100
        print(f"\nУСЛОВИЕ: Downtrend + Below EMA20 + Negative momentum")
        print(f"   Сделок: {len(ultimate)}")
        print(f"   Win Rate: {ultimate_wr:.1f}%")
        
        if ultimate_wr >= 50:
            print(f"   ✅ НАЙДЕНО! Это работает!")
        else:
            print(f"   ❌ Все равно плохо (WR {ultimate_wr:.1f}%)")
    else:
        print(f"\n❌ Такой комбинации условий нет в данных")


def main():
    print("\n" + "="*100)
    print("🔍 СИМУЛЯЦИЯ ВСЕХ SHORT ВХОДОВ")
    print("Цель: найти закономерность")
    print("="*100)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df = load_data()
    print(f"   ✅ {len(df)} H1 свечей")
    
    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Simulate all SHORT entries
    print("\n🔄 Симуляция всех SHORT входов...")
    df_short_trades = simulate_all_short_entries(df, strategy)
    
    if len(df_short_trades) == 0:
        print("❌ Нет SHORT сделок!")
        return
    
    # Analyze patterns
    analyze_patterns(df_short_trades)
    
    # Find best conditions
    find_best_short_conditions(df_short_trades)
    
    # Save detailed results
    output_file = 'short_trades_detailed.csv'
    df_short_trades.to_csv(output_file, index=False)
    print(f"\n💾 Детальные результаты сохранены: {output_file}")
    
    print("\n✅ Анализ завершен!")


if __name__ == "__main__":
    main()
