"""
Глубокий анализ проблемы SHORT сигналов
Цель: понять ПОЧЕМУ SHORT плохие и КАК их улучшить
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from pattern_recognition_strategy import PatternRecognitionStrategy


def load_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load H1 data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    # Add indicators
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    
    # Trend indicators
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['ema_200'] = df['close'].ewm(span=200).mean()
    
    # Trend strength
    df['trend_strength'] = ((df['ema_20'] - df['ema_50']) / df['close'] * 100).abs()
    
    # Is uptrend/downtrend
    df['is_uptrend'] = (df['ema_20'] > df['ema_50']) & (df['ema_50'] > df['ema_200'])
    df['is_downtrend'] = (df['ema_20'] < df['ema_50']) & (df['ema_50'] < df['ema_200'])
    
    return df


def backtest_with_context(df, strategy):
    """Run backtest with market context"""
    
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
        search_end = entry_time + timedelta(hours=48)
        
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Get market context at entry
        if entry_time in df.index:
            context = {
                'atr': df.loc[entry_time, 'atr'],
                'ema_20': df.loc[entry_time, 'ema_20'],
                'ema_50': df.loc[entry_time, 'ema_50'],
                'ema_200': df.loc[entry_time, 'ema_200'],
                'trend_strength': df.loc[entry_time, 'trend_strength'],
                'is_uptrend': df.loc[entry_time, 'is_uptrend'],
                'is_downtrend': df.loc[entry_time, 'is_downtrend'],
                'close': df.loc[entry_time, 'close']
            }
        else:
            context = None
        
        exit_price = None
        exit_type = None
        exit_time = None
        bars_in_trade = 0
        
        # Find exit
        for j in range(len(df_future)):
            bars_in_trade += 1
            
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
        
        # Calculate PnL %
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        # Calculate R (risk-reward achieved)
        risk = abs(entry_price - stop_loss)
        if direction == 1:
            actual_reward = exit_price - entry_price
        else:
            actual_reward = entry_price - exit_price
        
        r_achieved = actual_reward / risk if risk > 0 else 0
        
        trade = {
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'bars_in_trade': bars_in_trade,
            'r_achieved': r_achieved,
            'hour': entry_time.hour
        }
        
        # Add context
        if context:
            trade.update(context)
        
        trades.append(trade)
    
    return pd.DataFrame(trades)


def analyze_short_problems(df_trades):
    """Deep analysis of SHORT problems"""
    
    print("\n" + "="*80)
    print("🔍 ГЛУБОКИЙ АНАЛИЗ ПРОБЛЕМЫ SHORT СИГНАЛОВ")
    print("="*80)
    
    long_trades = df_trades[df_trades['direction'] == 'LONG']
    short_trades = df_trades[df_trades['direction'] == 'SHORT']
    
    print(f"\n📊 Базовая статистика:")
    print(f"   LONG: {len(long_trades)} сделок, WR {len(long_trades[long_trades['pnl_pct'] > 0]) / len(long_trades) * 100:.1f}%")
    print(f"   SHORT: {len(short_trades)} сделок, WR {len(short_trades[short_trades['pnl_pct'] > 0]) / len(short_trades) * 100:.1f}%")
    
    # Analysis 1: Exit types
    print("\n" + "="*80)
    print("📊 АНАЛИЗ #1: КАК ВЫХОДИМ ИЗ СДЕЛОК")
    print("="*80)
    
    print(f"\n{'Направление':<10} | {'TP':<8} | {'SL':<8} | {'EOD':<8} | {'TP%':<10} | {'SL%':<10}")
    print("-" * 70)
    
    for direction, trades in [('LONG', long_trades), ('SHORT', short_trades)]:
        tp_count = len(trades[trades['exit_type'] == 'TP'])
        sl_count = len(trades[trades['exit_type'] == 'SL'])
        eod_count = len(trades[trades['exit_type'] == 'EOD'])
        
        tp_pct = tp_count / len(trades) * 100 if len(trades) > 0 else 0
        sl_pct = sl_count / len(trades) * 100 if len(trades) > 0 else 0
        
        print(f"{direction:<10} | {tp_count:<8} | {sl_count:<8} | {eod_count:<8} | {tp_pct:<10.1f}% | {sl_pct:<10.1f}%")
    
    print(f"\n💡 ПРОБЛЕМА #1:")
    short_sl_pct = len(short_trades[short_trades['exit_type'] == 'SL']) / len(short_trades) * 100
    long_sl_pct = len(long_trades[long_trades['exit_type'] == 'SL']) / len(long_trades) * 100
    
    if short_sl_pct > long_sl_pct + 10:
        print(f"   ⚠️  SHORT чаще попадает в SL ({short_sl_pct:.1f}% vs LONG {long_sl_pct:.1f}%)")
        print(f"   Возможно: SL слишком близко или направление неправильно определяется")
    
    # Analysis 2: Market context (trend)
    print("\n" + "="*80)
    print("📊 АНАЛИЗ #2: В КАКОМ ТРЕНДЕ ВХОДИМ")
    print("="*80)
    
    print(f"\n{'Направление':<10} | {'В аптренде':<12} | {'В даунтренде':<15} | {'Боковик':<10}")
    print("-" * 60)
    
    for direction, trades in [('LONG', long_trades), ('SHORT', short_trades)]:
        if len(trades) > 0:
            uptrend = len(trades[trades['is_uptrend'] == True])
            downtrend = len(trades[trades['is_downtrend'] == True])
            sideways = len(trades) - uptrend - downtrend
            
            print(f"{direction:<10} | {uptrend:<12} ({uptrend/len(trades)*100:.0f}%) | {downtrend:<15} ({downtrend/len(trades)*100:.0f}%) | {sideways:<10} ({sideways/len(trades)*100:.0f}%)")
    
    print(f"\n💡 ПРОБЛЕМА #2:")
    if len(short_trades) > 0:
        short_in_uptrend = len(short_trades[short_trades['is_uptrend'] == True])
        short_in_downtrend = len(short_trades[short_trades['is_downtrend'] == True])
        
        if short_in_uptrend > short_in_downtrend:
            print(f"   ⚠️  SHORT сигналы чаще появляются в UPTREND ({short_in_uptrend} vs {short_in_downtrend})")
            print(f"   Это КОНТРТРЕНДОВАЯ торговля = низкий Win Rate!")
            print(f"   РЕШЕНИЕ: Фильтровать SHORT в uptrend")
    
    # Analysis 3: Win rate by trend
    print("\n" + "="*80)
    print("📊 АНАЛИЗ #3: WIN RATE ПО ТРЕНДУ")
    print("="*80)
    
    print(f"\n{'Направление':<10} | {'Тренд':<12} | {'Сделок':<8} | {'Win Rate':<10} | {'Avg PnL':<10}")
    print("-" * 60)
    
    for direction, trades in [('LONG', long_trades), ('SHORT', short_trades)]:
        for trend_name, trend_filter in [
            ('Uptrend', trades[trades['is_uptrend'] == True]),
            ('Downtrend', trades[trades['is_downtrend'] == True]),
            ('Sideways', trades[(trades['is_uptrend'] == False) & (trades['is_downtrend'] == False)])
        ]:
            if len(trend_filter) > 0:
                wins = trend_filter[trend_filter['pnl_pct'] > 0]
                wr = len(wins) / len(trend_filter) * 100
                avg_pnl = trend_filter['pnl_pct'].mean()
                
                emoji = "✅" if wr >= 60 else "⚠️" if wr >= 50 else "❌"
                print(f"{direction:<10} | {trend_name:<12} {emoji} | {len(trend_filter):<8} | {wr:<10.1f}% | {avg_pnl:<+10.2f}%")
    
    print(f"\n💡 ПРОБЛЕМА #3:")
    short_uptrend = short_trades[short_trades['is_uptrend'] == True]
    if len(short_uptrend) > 0:
        short_uptrend_wr = len(short_uptrend[short_uptrend['pnl_pct'] > 0]) / len(short_uptrend) * 100
        if short_uptrend_wr < 40:
            print(f"   ⚠️  SHORT в uptrend имеет очень низкий WR {short_uptrend_wr:.1f}%")
            print(f"   РЕШЕНИЕ: НЕ торговать SHORT когда EMA20 > EMA50 > EMA200")
    
    # Analysis 4: R achieved
    print("\n" + "="*80)
    print("📊 АНАЛИЗ #4: RISK-REWARD (R)")
    print("="*80)
    
    print(f"\n{'Направление':<10} | {'Средний R':<12} | {'R на TP':<12} | {'R на SL':<12}")
    print("-" * 50)
    
    for direction, trades in [('LONG', long_trades), ('SHORT', short_trades)]:
        if len(trades) > 0:
            avg_r = trades['r_achieved'].mean()
            
            tp_trades = trades[trades['exit_type'] == 'TP']
            r_on_tp = tp_trades['r_achieved'].mean() if len(tp_trades) > 0 else 0
            
            sl_trades = trades[trades['exit_type'] == 'SL']
            r_on_sl = sl_trades['r_achieved'].mean() if len(sl_trades) > 0 else 0
            
            print(f"{direction:<10} | {avg_r:<+12.2f}R | {r_on_tp:<+12.2f}R | {r_on_sl:<+12.2f}R")
    
    print(f"\n💡 ПРОБЛЕМА #4:")
    if len(short_trades) > 0:
        short_avg_r = short_trades['r_achieved'].mean()
        long_avg_r = long_trades['r_achieved'].mean()
        
        if short_avg_r < -0.5:
            print(f"   ⚠️  SHORT средний R очень плохой ({short_avg_r:+.2f}R vs LONG {long_avg_r:+.2f}R)")
            print(f"   РЕШЕНИЕ: Увеличить TP для SHORT или уменьшить SL")
    
    # Analysis 5: Bars in trade
    print("\n" + "="*80)
    print("📊 АНАЛИЗ #5: СКОЛЬКО ВРЕМЕНИ В СДЕЛКЕ")
    print("="*80)
    
    print(f"\n{'Направление':<10} | {'Средн. баров':<15} | {'На TP':<12} | {'На SL':<12}")
    print("-" * 55)
    
    for direction, trades in [('LONG', long_trades), ('SHORT', short_trades)]:
        if len(trades) > 0:
            avg_bars = trades['bars_in_trade'].mean()
            
            tp_trades = trades[trades['exit_type'] == 'TP']
            bars_tp = tp_trades['bars_in_trade'].mean() if len(tp_trades) > 0 else 0
            
            sl_trades = trades[trades['exit_type'] == 'SL']
            bars_sl = sl_trades['bars_in_trade'].mean() if len(sl_trades) > 0 else 0
            
            print(f"{direction:<10} | {avg_bars:<15.1f} | {bars_tp:<12.1f} | {bars_sl:<12.1f}")
    
    print(f"\n💡 ПРОБЛЕМА #5:")
    if len(short_trades) > 0:
        short_sl_trades = short_trades[short_trades['exit_type'] == 'SL']
        if len(short_sl_trades) > 0:
            short_bars_sl = short_sl_trades['bars_in_trade'].mean()
            if short_bars_sl < 5:
                print(f"   ⚠️  SHORT очень быстро попадает в SL (среднее {short_bars_sl:.1f} баров = {short_bars_sl:.0f} часов)")
                print(f"   РЕШЕНИЕ: Нужен более широкий SL или лучшее качество сигналов")
    
    # Analysis 6: By hour
    print("\n" + "="*80)
    print("📊 АНАЛИЗ #6: SHORT ПО ЧАСАМ")
    print("="*80)
    
    print(f"\n{'Час':<6} | {'SHORT':<8} | {'Win Rate':<10} | {'LONG':<8} | {'Win Rate':<10}")
    print("-" * 50)
    
    for hour in sorted(short_trades['hour'].unique()):
        short_hour = short_trades[short_trades['hour'] == hour]
        long_hour = long_trades[long_trades['hour'] == hour]
        
        if len(short_hour) > 0:
            short_wr = len(short_hour[short_hour['pnl_pct'] > 0]) / len(short_hour) * 100
            long_wr = len(long_hour[long_hour['pnl_pct'] > 0]) / len(long_hour) * 100 if len(long_hour) > 0 else 0
            
            emoji = "✅" if short_wr >= 50 else "❌"
            print(f"{hour:02d}:00 {emoji} | {len(short_hour):<8} | {short_wr:<10.1f}% | {len(long_hour):<8} | {long_wr:<10.1f}%")
    
    print(f"\n💡 ПРОБЛЕМА #6:")
    bad_hours = []
    for hour in sorted(short_trades['hour'].unique()):
        short_hour = short_trades[short_trades['hour'] == hour]
        if len(short_hour) > 0:
            short_wr = len(short_hour[short_hour['pnl_pct'] > 0]) / len(short_hour) * 100
            if short_wr < 40:
                bad_hours.append(hour)
    
    if len(bad_hours) > 0:
        print(f"   ⚠️  SHORT особенно плохие в часы: {bad_hours}")
        print(f"   РЕШЕНИЕ: Отключить SHORT в эти часы")


def main():
    print("\n" + "="*80)
    print("🔍 АНАЛИЗ: ПОЧЕМУ SHORT СИГНАЛЫ ПЛОХИЕ")
    print("="*80)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df = load_data()
    print(f"   ✅ {len(df)} H1 свечей")
    
    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Run backtest with context
    print("\n🔄 Запуск бэктеста с контекстом рынка...")
    df_trades = backtest_with_context(df, strategy)
    
    print(f"\n📊 Всего сделок: {len(df_trades)}")
    
    # Analyze SHORT problems
    analyze_short_problems(df_trades)
    
    # Final recommendations
    print("\n" + "="*80)
    print("🚀 ИТОГОВЫЕ РЕКОМЕНДАЦИИ ДЛЯ УЛУЧШЕНИЯ SHORT")
    print("="*80)
    
    short_trades = df_trades[df_trades['direction'] == 'SHORT']
    
    # Calculate potential improvements
    short_in_uptrend = short_trades[short_trades['is_uptrend'] == True]
    short_in_downtrend = short_trades[short_trades['is_downtrend'] == True]
    
    print(f"\n1️⃣  ФИЛЬТР ПО ТРЕНДУ (КРИТИЧНО) ✅")
    print(f"   Проблема: {len(short_in_uptrend)}/{len(short_trades)} SHORT сигналов в UPTREND")
    if len(short_in_uptrend) > 0:
        uptrend_wr = len(short_in_uptrend[short_in_uptrend['pnl_pct'] > 0]) / len(short_in_uptrend) * 100
        print(f"   Win Rate в uptrend: {uptrend_wr:.1f}% (очень плохо)")
    if len(short_in_downtrend) > 0:
        downtrend_wr = len(short_in_downtrend[short_in_downtrend['pnl_pct'] > 0]) / len(short_in_downtrend) * 100
        print(f"   Win Rate в downtrend: {downtrend_wr:.1f}% (нормально)")
    print(f"   РЕШЕНИЕ: Торговать SHORT только когда EMA20 < EMA50 < EMA200")
    
    print(f"\n2️⃣  УВЕЛИЧИТЬ STOP LOSS ДЛЯ SHORT 💡")
    short_sl = short_trades[short_trades['exit_type'] == 'SL']
    if len(short_sl) > 0:
        avg_bars_sl = short_sl['bars_in_trade'].mean()
        print(f"   Проблема: SHORT попадает в SL слишком быстро ({avg_bars_sl:.1f} часов)")
        print(f"   РЕШЕНИЕ: SL для SHORT = 1.3x от текущего (вместо 1.0x)")
    
    print(f"\n3️⃣  БОЛЕЕ СТРОГИЙ ФИЛЬТР КАЧЕСТВА ДЛЯ SHORT 💡")
    print(f"   РЕШЕНИЕ: Требовать более высокий candle_quality для SHORT")
    print(f"   Например: min_quality для LONG = 25, для SHORT = 40")
    
    print(f"\n4️⃣  АДАПТИВНЫЙ TP ДЛЯ SHORT 💡")
    print(f"   Проблема: R для SHORT хуже чем для LONG")
    print(f"   РЕШЕНИЕ: Использовать Fibonacci 2.0 или 2.618 для SHORT TP")
    
    # Calculate potential effect
    print("\n" + "="*80)
    print("📊 ОЖИДАЕМЫЙ ЭФФЕКТ")
    print("="*80)
    
    # Baseline
    current_wr = len(short_trades[short_trades['pnl_pct'] > 0]) / len(short_trades) * 100
    current_pnl = short_trades['pnl_pct'].sum()
    
    # With trend filter
    filtered_short = short_trades[short_trades['is_downtrend'] == True]
    if len(filtered_short) > 0:
        filtered_wr = len(filtered_short[filtered_short['pnl_pct'] > 0]) / len(filtered_short) * 100
        filtered_pnl = filtered_short['pnl_pct'].sum()
    else:
        filtered_wr = 0
        filtered_pnl = 0
    
    print(f"\nСЕЙЧАС:")
    print(f"   SHORT: {len(short_trades)} сделок")
    print(f"   Win Rate: {current_wr:.1f}%")
    print(f"   Total PnL: {current_pnl:+.2f}%")
    
    print(f"\nС ФИЛЬТРОМ ПО ТРЕНДУ:")
    print(f"   SHORT: {len(filtered_short)} сделок (только в downtrend)")
    print(f"   Win Rate: {filtered_wr:.1f}% ({filtered_wr - current_wr:+.1f}%)")
    print(f"   Total PnL: {filtered_pnl:+.2f}% ({filtered_pnl - current_pnl:+.2f}%)")
    
    if filtered_wr > 50:
        print(f"\n✅ С фильтром по тренду SHORT становится прибыльным!")
        print(f"   Рекомендую: Оставить SHORT, но добавить фильтр по тренду")
    else:
        print(f"\n⚠️  Даже с фильтром SHORT остается слабым")
        print(f"   Рекомендую: Отключить SHORT или требовать очень строгие условия")
    
    print("\n✅ Анализ завершен!")


if __name__ == "__main__":
    main()
