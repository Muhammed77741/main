"""
Глубокий анализ baseline стратегии и поиск путей оптимизации

Анализируем:
1. Все сделки по месяцам, дням недели, часам
2. Паттерны убыточных сделок
3. Влияние волатильности
4. Влияние объема
5. Качество entry points
6. Эффективность TP/SL уровней
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pattern_recognition_strategy import PatternRecognitionStrategy


def detailed_backtest_with_analysis(df, strategy):
    """Детальный бэктест с сохранением всей информации о сделках"""
    
    print("🔍 Запуск детального бэктеста...")
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    trades = []
    
    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']
        
        entry_time = df_signals.index[i]
        entry_idx = df_strategy.index.get_loc(entry_time)
        search_end = entry_time + timedelta(hours=48)
        
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Собираем данные о рынке на момент входа
        entry_candle = df_strategy.iloc[entry_idx]
        
        # ATR на момент входа
        high_low = df_strategy['high'] - df_strategy['low']
        atr = high_low.rolling(window=14).mean()
        entry_atr = atr.iloc[entry_idx] if entry_idx >= 14 else high_low.iloc[entry_idx]
        
        # Объем
        avg_volume = df_strategy['volume'].rolling(window=20).mean()
        entry_volume = df_strategy['volume'].iloc[entry_idx]
        entry_avg_volume = avg_volume.iloc[entry_idx] if entry_idx >= 20 else entry_volume
        volume_ratio = entry_volume / entry_avg_volume if entry_avg_volume > 0 else 1.0
        
        # RSI
        delta = df_strategy['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        entry_rsi = rsi.iloc[entry_idx] if entry_idx >= 14 else 50
        
        # Час дня
        entry_hour = entry_time.hour
        entry_day = entry_time.dayofweek  # 0=Monday, 6=Sunday
        
        # Расстояние до TP/SL в ATR
        sl_distance = abs(entry_price - stop_loss)
        tp_distance = abs(take_profit - entry_price) if direction == 1 else abs(entry_price - take_profit)
        sl_atr_ratio = sl_distance / entry_atr if entry_atr > 0 else 0
        tp_atr_ratio = tp_distance / entry_atr if entry_atr > 0 else 0
        risk_reward = tp_distance / sl_distance if sl_distance > 0 else 0
        
        # Find exit
        exit_price = None
        exit_type = None
        exit_time = None
        max_profit = 0
        max_loss = 0
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            # Track max profit/loss
            if direction == 1:
                current_profit = candle['high'] - entry_price
                current_loss = entry_price - candle['low']
            else:
                current_profit = entry_price - candle['low']
                current_loss = candle['high'] - entry_price
            
            max_profit = max(max_profit, current_profit)
            max_loss = max(max_loss, current_loss)
            
            # Check exit
            if direction == 1:  # LONG
                if candle['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif candle['high'] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break
            else:  # SHORT
                if candle['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_time = df_future.index[j]
                    break
                elif candle['low'] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_time = df_future.index[j]
                    break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'TIMEOUT'
            exit_time = df_future.index[-1]
        
        # Calculate PnL
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl_points = exit_price - entry_price
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            pnl_points = entry_price - exit_price
        
        max_profit_pct = (max_profit / entry_price) * 100
        max_loss_pct = (max_loss / entry_price) * 100
        
        duration_hours = (exit_time - entry_time).total_seconds() / 3600
        
        # Pattern info
        pattern = signal.get('pattern', 'N/A')
        
        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'month': entry_time.month,
            'day_of_week': entry_day,
            'hour': entry_hour,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
            'pattern': str(pattern),
            'entry_atr': entry_atr,
            'sl_atr_ratio': sl_atr_ratio,
            'tp_atr_ratio': tp_atr_ratio,
            'risk_reward': risk_reward,
            'entry_rsi': entry_rsi,
            'volume_ratio': volume_ratio,
            'max_profit_pct': max_profit_pct,
            'max_loss_pct': max_loss_pct,
            'hit_tp': exit_type == 'TP',
            'hit_sl': exit_type == 'SL'
        })
    
    return pd.DataFrame(trades)


def analyze_losing_trades(trades_df):
    """Анализ убыточных сделок - где теряем деньги?"""
    
    print("\n" + "="*100)
    print("🔍 АНАЛИЗ УБЫТОЧНЫХ СДЕЛОК")
    print("="*100)
    
    losses = trades_df[trades_df['pnl_pct'] < 0].copy()
    wins = trades_df[trades_df['pnl_pct'] > 0].copy()
    
    print(f"\n📊 Общая статистика:")
    print(f"   Всего сделок: {len(trades_df)}")
    print(f"   Прибыльных: {len(wins)} ({len(wins)/len(trades_df)*100:.1f}%)")
    print(f"   Убыточных: {len(losses)} ({len(losses)/len(trades_df)*100:.1f}%)")
    print(f"   Total PnL: {trades_df['pnl_pct'].sum():+.2f}%")
    
    if len(losses) == 0:
        print("\n✅ Нет убыточных сделок!")
        return {}
    
    # 1. По часам дня
    print(f"\n⏰ УБЫТКИ ПО ЧАСАМ ДНЯ:")
    hour_analysis = []
    for hour in range(24):
        hour_trades = trades_df[trades_df['hour'] == hour]
        hour_losses = losses[losses['hour'] == hour]
        
        if len(hour_trades) > 0:
            loss_rate = len(hour_losses) / len(hour_trades) * 100
            avg_pnl = hour_trades['pnl_pct'].mean()
            total_pnl = hour_trades['pnl_pct'].sum()
            
            hour_analysis.append({
                'hour': hour,
                'trades': len(hour_trades),
                'loss_rate': loss_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': total_pnl
            })
    
    hour_df = pd.DataFrame(hour_analysis)
    if len(hour_df) > 0:
        worst_hours = hour_df.nsmallest(5, 'avg_pnl')
        best_hours = hour_df.nlargest(5, 'avg_pnl')
        
        print(f"\n   ❌ ХУДШИЕ часы (по avg PnL):")
        for _, row in worst_hours.iterrows():
            print(f"      {int(row['hour']):02d}:00 - Trades: {int(row['trades']):3d}, Avg PnL: {row['avg_pnl']:+.2f}%, Total: {row['total_pnl']:+.2f}%")
        
        print(f"\n   ✅ ЛУЧШИЕ часы (по avg PnL):")
        for _, row in best_hours.iterrows():
            print(f"      {int(row['hour']):02d}:00 - Trades: {int(row['trades']):3d}, Avg PnL: {row['avg_pnl']:+.2f}%, Total: {row['total_pnl']:+.2f}%")
    
    # 2. По дням недели
    print(f"\n📅 УБЫТКИ ПО ДНЯМ НЕДЕЛИ:")
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day_idx, day_name in enumerate(days):
        day_trades = trades_df[trades_df['day_of_week'] == day_idx]
        day_losses = losses[losses['day_of_week'] == day_idx]
        
        if len(day_trades) > 0:
            loss_rate = len(day_losses) / len(day_trades) * 100
            avg_pnl = day_trades['pnl_pct'].mean()
            total_pnl = day_trades['pnl_pct'].sum()
            
            emoji = "✅" if avg_pnl > 0 else "❌"
            print(f"   {emoji} {day_name:10s} - Trades: {len(day_trades):3d}, Loss Rate: {loss_rate:5.1f}%, "
                  f"Avg PnL: {avg_pnl:+.2f}%, Total: {total_pnl:+.2f}%")
    
    # 3. По направлению
    print(f"\n📈 УБЫТКИ ПО НАПРАВЛЕНИЮ:")
    for direction in ['LONG', 'SHORT']:
        dir_trades = trades_df[trades_df['direction'] == direction]
        dir_losses = losses[losses['direction'] == direction]
        
        if len(dir_trades) > 0:
            loss_rate = len(dir_losses) / len(dir_trades) * 100
            avg_pnl = dir_trades['pnl_pct'].mean()
            win_rate = len(dir_trades[dir_trades['pnl_pct'] > 0]) / len(dir_trades) * 100
            
            print(f"   {direction:5s} - Trades: {len(dir_trades):3d}, Win Rate: {win_rate:5.1f}%, "
                  f"Avg PnL: {avg_pnl:+.2f}%")
    
    # 4. По волатильности (ATR)
    print(f"\n📊 УБЫТКИ ПО ВОЛАТИЛЬНОСТИ:")
    trades_df['atr_level'] = pd.qcut(trades_df['entry_atr'], q=4, labels=['Low', 'Medium', 'High', 'Very High'], duplicates='drop')
    
    for level in ['Low', 'Medium', 'High', 'Very High']:
        level_trades = trades_df[trades_df['atr_level'] == level]
        
        if len(level_trades) > 0:
            avg_pnl = level_trades['pnl_pct'].mean()
            win_rate = len(level_trades[level_trades['pnl_pct'] > 0]) / len(level_trades) * 100
            
            emoji = "✅" if avg_pnl > 0.5 else "⚠️" if avg_pnl > 0 else "❌"
            print(f"   {emoji} {level:10s} - Trades: {len(level_trades):3d}, Win Rate: {win_rate:5.1f}%, "
                  f"Avg PnL: {avg_pnl:+.2f}%")
    
    # 5. По RSI
    print(f"\n📈 УБЫТКИ ПО RSI УРОВНЯМ:")
    rsi_ranges = [
        ('Oversold (<30)', lambda x: x < 30),
        ('Neutral (30-70)', lambda x: (x >= 30) & (x <= 70)),
        ('Overbought (>70)', lambda x: x > 70)
    ]
    
    for range_name, condition in rsi_ranges:
        range_trades = trades_df[condition(trades_df['entry_rsi'])]
        
        if len(range_trades) > 0:
            avg_pnl = range_trades['pnl_pct'].mean()
            win_rate = len(range_trades[range_trades['pnl_pct'] > 0]) / len(range_trades) * 100
            
            emoji = "✅" if avg_pnl > 0.5 else "⚠️" if avg_pnl > 0 else "❌"
            print(f"   {emoji} {range_name:20s} - Trades: {len(range_trades):3d}, Win Rate: {win_rate:5.1f}%, "
                  f"Avg PnL: {avg_pnl:+.2f}%")
    
    # 6. Анализ "почти прибыльных" сделок
    print(f"\n💡 АНАЛИЗ 'ПОЧТИ ПРИБЫЛЬНЫХ' СДЕЛОК:")
    almost_winners = losses[losses['max_profit_pct'] > 0.5]  # Были в прибыли >0.5%
    
    if len(almost_winners) > 0:
        print(f"   Сделок которые были в прибыли: {len(almost_winners)} ({len(almost_winners)/len(losses)*100:.1f}% от убытков)")
        print(f"   Средняя макс. прибыль: {almost_winners['max_profit_pct'].mean():.2f}%")
        print(f"   Средний итоговый убыток: {almost_winners['pnl_pct'].mean():.2f}%")
        print(f"   💡 Упущенная прибыль: {(almost_winners['max_profit_pct'].sum() + almost_winners['pnl_pct'].sum()):.2f}%")
    
    return {
        'worst_hours': worst_hours if 'worst_hours' in locals() else None,
        'best_hours': best_hours if 'best_hours' in locals() else None,
        'almost_winners': almost_winners
    }


def propose_improvements(trades_df, analysis_results):
    """Предлагаем улучшения на основе анализа"""
    
    print("\n" + "="*100)
    print("💡 ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ")
    print("="*100)
    
    improvements = []
    
    # 1. Фильтр по времени
    if 'worst_hours' in analysis_results and analysis_results['worst_hours'] is not None:
        worst_hours = analysis_results['worst_hours']
        worst_hour_list = worst_hours['hour'].tolist()
        
        # Сколько потеряли в худших часах
        worst_hours_trades = trades_df[trades_df['hour'].isin(worst_hour_list)]
        lost_pnl = worst_hours_trades['pnl_pct'].sum()
        
        improvements.append({
            'name': 'Time Filter (исключить худшие часы)',
            'description': f'Не торговать в часы: {worst_hour_list}',
            'potential_gain': abs(lost_pnl) if lost_pnl < 0 else 0,
            'trades_filtered': len(worst_hours_trades)
        })
    
    # 2. Фильтр по волатильности
    low_vol_trades = trades_df[trades_df['atr_level'] == 'Low'] if 'atr_level' in trades_df.columns else pd.DataFrame()
    if len(low_vol_trades) > 0:
        avg_pnl_low_vol = low_vol_trades['pnl_pct'].mean()
        if avg_pnl_low_vol < 0:
            improvements.append({
                'name': 'Volatility Filter (исключить низкую волатильность)',
                'description': 'Не торговать при низком ATR',
                'potential_gain': abs(low_vol_trades['pnl_pct'].sum()),
                'trades_filtered': len(low_vol_trades)
            })
    
    # 3. RSI фильтр
    # LONG в overbought, SHORT в oversold = плохо
    long_overbought = trades_df[(trades_df['direction'] == 'LONG') & (trades_df['entry_rsi'] > 70)]
    short_oversold = trades_df[(trades_df['direction'] == 'SHORT') & (trades_df['entry_rsi'] < 30)]
    
    bad_rsi_trades = pd.concat([long_overbought, short_oversold])
    if len(bad_rsi_trades) > 0:
        avg_pnl_bad_rsi = bad_rsi_trades['pnl_pct'].mean()
        if avg_pnl_bad_rsi < 0:
            improvements.append({
                'name': 'RSI Filter',
                'description': 'Избегать LONG при RSI>70 и SHORT при RSI<30',
                'potential_gain': abs(bad_rsi_trades['pnl_pct'].sum()),
                'trades_filtered': len(bad_rsi_trades)
            })
    
    # 4. Partial Take Profit (для "почти прибыльных")
    if 'almost_winners' in analysis_results:
        almost_winners = analysis_results['almost_winners']
        if len(almost_winners) > 0:
            potential_save = almost_winners['max_profit_pct'].mean() * 0.5 * len(almost_winners)
            improvements.append({
                'name': 'Partial TP (фиксация части прибыли)',
                'description': 'Закрывать 50% на половине пути к TP',
                'potential_gain': potential_save,
                'trades_filtered': 0
            })
    
    # 5. Trailing Stop улучшение
    long_trades = trades_df[trades_df['direction'] == 'LONG']
    if len(long_trades) > 0:
        # Сделки которые достигли хорошей прибыли но закрылись с меньшей
        good_profit_lost = long_trades[
            (long_trades['max_profit_pct'] > 1.0) & 
            (long_trades['pnl_pct'] < long_trades['max_profit_pct'] * 0.7)
        ]
        
        if len(good_profit_lost) > 0:
            lost_profit = (good_profit_lost['max_profit_pct'] - good_profit_lost['pnl_pct']).sum()
            improvements.append({
                'name': 'Tighter Trailing Stop',
                'description': 'Уменьшить дистанцию trailing stop с 18п до 12-15п',
                'potential_gain': lost_profit * 0.3,  # Сможем сохранить ~30%
                'trades_filtered': 0
            })
    
    # Сортируем по потенциальной выгоде
    improvements_df = pd.DataFrame(improvements)
    if len(improvements_df) > 0:
        improvements_df = improvements_df.sort_values('potential_gain', ascending=False)
        
        print(f"\n🎯 TOP IMPROVEMENTS (по потенциальной выгоде):\n")
        for idx, row in improvements_df.iterrows():
            print(f"{idx+1}. {row['name']}")
            print(f"   Описание: {row['description']}")
            print(f"   Потенциальная выгода: +{row['potential_gain']:.2f}%")
            if row['trades_filtered'] > 0:
                print(f"   Отфильтрует сделок: {row['trades_filtered']}")
            print()
        
        total_potential = improvements_df['potential_gain'].sum()
        current_pnl = trades_df['pnl_pct'].sum()
        
        print(f"💰 ИТОГО:")
        print(f"   Текущий PnL: {current_pnl:+.2f}%")
        print(f"   Потенциальное улучшение: +{total_potential:.2f}%")
        print(f"   Возможный PnL: {current_pnl + total_potential:+.2f}%")
        print(f"   Улучшение: +{total_potential/current_pnl*100:.1f}%")
    
    return improvements_df


def main():
    print("\n" + "="*100)
    print("ГЛУБОКИЙ АНАЛИЗ И ОПТИМИЗАЦИЯ BASELINE СТРАТЕГИИ")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Detailed backtest
    trades_df = detailed_backtest_with_analysis(df, strategy)
    
    print(f"\n✅ Проанализировано {len(trades_df)} сделок")
    print(f"   Total PnL: {trades_df['pnl_pct'].sum():+.2f}%")
    print(f"   Win Rate: {len(trades_df[trades_df['pnl_pct'] > 0])/len(trades_df)*100:.1f}%")
    
    # Save detailed trades
    trades_df.to_csv('detailed_trades_analysis.csv', index=False)
    print(f"\n💾 Детальные данные сохранены: detailed_trades_analysis.csv")
    
    # Analyze losing trades
    analysis_results = analyze_losing_trades(trades_df)
    
    # Propose improvements
    improvements = propose_improvements(trades_df, analysis_results)
    
    print("\n" + "="*100)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("="*100)
    
    return trades_df, analysis_results, improvements


if __name__ == "__main__":
    trades_df, analysis_results, improvements = main()
