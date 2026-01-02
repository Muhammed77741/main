"""
Анализ слабых паттернов: MOMENTUM и PULLBACK

Проблемы:
- MOMENTUM: +10.3p в среднем (слишком мало)
- PULLBACK: +50.8p (неплохо, но можно лучше)

Анализируем почему и как улучшить
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from detect_30pip_patterns import ThirtyPipMoveDetector


def analyze_pattern_trades(df, pattern_type, trades_df):
    """
    Детальный анализ сделок конкретного паттерна
    """
    
    pattern_trades = trades_df[trades_df['type'] == pattern_type].copy()
    
    if len(pattern_trades) == 0:
        print(f"No {pattern_type} trades found!")
        return
    
    print(f"\n" + "="*100)
    print(f"📊 АНАЛИЗ {pattern_type} ПАТТЕРНА")
    print("="*100)
    
    # Overall stats
    wins = len(pattern_trades[pattern_trades['pnl_pips'] > 0])
    losses = len(pattern_trades[pattern_trades['pnl_pips'] <= 0])
    win_rate = wins / len(pattern_trades) * 100
    
    avg_win = pattern_trades[pattern_trades['pnl_pips'] > 0]['pnl_pips'].mean() if wins > 0 else 0
    avg_loss = pattern_trades[pattern_trades['pnl_pips'] < 0]['pnl_pips'].mean() if losses > 0 else 0
    
    print(f"\n📈 Общая статистика:")
    print(f"   Всего сделок: {len(pattern_trades)}")
    print(f"   Прибыльных:   {wins} ({win_rate:.1f}%)")
    print(f"   Убыточных:    {losses} ({100-win_rate:.1f}%)")
    print(f"   Avg Win:      {avg_win:+.1f}p")
    print(f"   Avg Loss:     {avg_loss:+.1f}p")
    print(f"   Total PnL:    {pattern_trades['pnl_pips'].sum():+.0f}p")
    
    # Analyze by exit type
    print(f"\n📊 По типу выхода:")
    for exit_type in ['TP', 'SL', 'TIMEOUT']:
        exit_trades = pattern_trades[pattern_trades['exit_type'] == exit_type]
        if len(exit_trades) > 0:
            exit_pct = len(exit_trades) / len(pattern_trades) * 100
            exit_avg = exit_trades['pnl_pips'].mean()
            exit_total = exit_trades['pnl_pips'].sum()
            
            print(f"   {exit_type:10s}: {len(exit_trades):3d} ({exit_pct:5.1f}%) | "
                  f"Avg {exit_avg:+7.1f}p | Total {exit_total:+8.0f}p")
    
    # Analyze "almost winners" - reached 30+ but closed in loss
    almost_winners = pattern_trades[
        (pattern_trades['reached_30pips'] == True) & 
        (pattern_trades['pnl_pips'] < 0)
    ]
    
    if len(almost_winners) > 0:
        print(f"\n💡 'Почти выигрышные' сделки:")
        print(f"   Достигли 30+ пипсов, но закрылись в убытке: {len(almost_winners)}")
        print(f"   Макс. прибыль в среднем: {almost_winners['max_profit_pips'].mean():.1f}p")
        print(f"   Итоговый убыток в среднем: {almost_winners['pnl_pips'].mean():+.1f}p")
        print(f"   💸 Упущенная прибыль: {almost_winners['max_profit_pips'].sum() - almost_winners['pnl_pips'].sum():.0f}p")
    
    # Analyze by confidence
    if 'confidence' in pattern_trades.columns:
        print(f"\n📊 По уровню уверенности:")
        for conf in ['HIGH', 'MEDIUM']:
            conf_trades = pattern_trades[pattern_trades['confidence'] == conf]
            if len(conf_trades) > 0:
                conf_wr = len(conf_trades[conf_trades['pnl_pips'] > 0]) / len(conf_trades) * 100
                conf_avg = conf_trades['pnl_pips'].mean()
                conf_total = conf_trades['pnl_pips'].sum()
                
                print(f"   {conf:10s}: {len(conf_trades):3d} trades | "
                      f"WR {conf_wr:5.1f}% | Avg {conf_avg:+6.1f}p | Total {conf_total:+7.0f}p")
    
    # Top losses
    print(f"\n❌ TOP 10 УБЫТОЧНЫХ СДЕЛОК:")
    worst_trades = pattern_trades.nsmallest(10, 'pnl_pips')
    print(f"{'Date':<20} {'Exit':<10} {'PnL':<10} {'Max Profit':<12} {'Reached 30p':<12}")
    print("-"*70)
    
    for _, trade in worst_trades.iterrows():
        print(f"{str(trade['entry_time']):<20} {trade['exit_type']:<10} "
              f"{trade['pnl_pips']:>8.1f}p {trade['max_profit_pips']:>10.1f}p "
              f"{'Yes' if trade['reached_30pips'] else 'No':>11s}")
    
    return pattern_trades


def propose_improvements_for_pattern(pattern_type, analysis_trades):
    """
    Предлагаем улучшения для конкретного паттерна
    """
    
    print(f"\n" + "="*100)
    print(f"💡 ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ {pattern_type}")
    print("="*100)
    
    improvements = []
    
    # 1. Partial TP
    almost_winners = analysis_trades[
        (analysis_trades['reached_30pips'] == True) & 
        (analysis_trades['pnl_pips'] < 0)
    ]
    
    if len(almost_winners) > 0:
        potential_save = almost_winners['max_profit_pips'].mean() * 0.5 * len(almost_winners)
        improvements.append({
            'name': 'Partial TP на 30 пипсах',
            'description': 'Закрывать 50% позиции при достижении 30 пипсов',
            'potential_gain': potential_save,
            'affected_trades': len(almost_winners)
        })
    
    # 2. Tighter SL
    sl_losses = analysis_trades[analysis_trades['exit_type'] == 'SL']
    big_sl_losses = sl_losses[sl_losses['pnl_pips'] < -20]
    
    if len(big_sl_losses) > 0:
        potential_save = abs(big_sl_losses['pnl_pips'].sum()) * 0.3
        improvements.append({
            'name': 'Уменьшить SL distance',
            'description': 'Более tight SL (сохранить ~30% убытков)',
            'potential_gain': potential_save,
            'affected_trades': len(big_sl_losses)
        })
    
    # 3. Filter MEDIUM confidence
    if 'confidence' in analysis_trades.columns:
        medium_conf = analysis_trades[analysis_trades['confidence'] == 'MEDIUM']
    else:
        medium_conf = pd.DataFrame()
    
    if len(medium_conf) > 0:
        medium_avg = medium_conf['pnl_pips'].mean()
        if medium_avg < 15:  # Если средняя < 15 пипсов
            potential_gain = len(medium_conf) * (30 - medium_avg)  # Экономим на убытках
            improvements.append({
                'name': 'Фильтровать MEDIUM confidence',
                'description': 'Торговать только HIGH confidence',
                'potential_gain': potential_gain if medium_avg < 0 else 0,
                'affected_trades': len(medium_conf)
            })
    
    # 4. Trailing SL after profit
    timeout_losses = analysis_trades[
        (analysis_trades['exit_type'] == 'TIMEOUT') & 
        (analysis_trades['pnl_pips'] < 0) &
        (analysis_trades['max_profit_pips'] > 15)
    ]
    
    if len(timeout_losses) > 0:
        potential_save = timeout_losses['max_profit_pips'].mean() * 0.4 * len(timeout_losses)
        improvements.append({
            'name': 'Trailing Stop Loss',
            'description': 'Активировать trailing SL после +15 пипсов',
            'potential_gain': potential_save,
            'affected_trades': len(timeout_losses)
        })
    
    # Print improvements
    if len(improvements) > 0:
        improvements_df = pd.DataFrame(improvements)
        improvements_df = improvements_df.sort_values('potential_gain', ascending=False)
        
        print(f"\n🎯 Предложения (по приоритету):\n")
        for i, (_, imp) in enumerate(improvements_df.iterrows(), 1):
            print(f"{i}. {imp['name']}")
            print(f"   Описание: {imp['description']}")
            print(f"   Потенциальная выгода: +{imp['potential_gain']:.0f} пипсов")
            print(f"   Затронет сделок: {imp['affected_trades']}")
            print()
        
        total_potential = improvements_df['potential_gain'].sum()
        current_total = analysis_trades['pnl_pips'].sum()
        
        print(f"💰 ИТОГО:")
        print(f"   Текущий результат: {current_total:+.0f} пипсов")
        print(f"   Потенциальное улучшение: +{total_potential:.0f} пипсов")
        print(f"   Возможный результат: {current_total + total_potential:+.0f} пипсов")
        print(f"   Улучшение: +{(total_potential/abs(current_total) if current_total != 0 else 0)*100:.1f}%")
    
    return improvements


def backtest_with_improvements(df, detector):
    """
    Бэктест с улучшениями
    """
    
    print(f"\n" + "="*100)
    print("🔍 БЭКТЕСТ С УЛУЧШЕНИЯМИ")
    print("="*100)
    
    # Get signals
    signals_df = detector.detect_all_patterns(df.copy())
    signals_df = signals_df[signals_df['confidence'] == 'HIGH'].copy()  # Only HIGH
    
    print(f"\n   Total signals (HIGH confidence): {len(signals_df)}")
    
    if len(signals_df) == 0:
        return pd.DataFrame()
    
    trades = []
    
    for idx, signal in signals_df.iterrows():
        entry_time = signal['time']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        pattern_type = signal['type']
        
        # IMPROVEMENT 1: Tighter SL for MOMENTUM
        if pattern_type == 'MOMENTUM':
            atr = (df.loc[entry_time, 'high'] - df.loc[entry_time, 'low']) * 1.5
            new_sl = entry_price - atr * 0.7  # Tighter (was ~1.0)
            stop_loss = max(stop_loss, new_sl)  # Use tighter if it's higher
        
        # Partial TP level (30 pips)
        partial_tp_price = entry_price + (30 * 0.10)
        
        # Look forward
        search_end = entry_time + timedelta(hours=24)
        df_future = df[(df.index > entry_time) & (df.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Track position
        position_size = 1.0
        total_pnl_pips = 0
        max_profit_pips = 0
        exits = []
        
        # IMPROVEMENT 2: Trailing SL
        trailing_sl = stop_loss
        trailing_active = False
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            if position_size <= 0:
                break
            
            # Track max profit
            current_profit_dollars = candle['high'] - entry_price
            current_profit_pips = current_profit_dollars / 0.10
            max_profit_pips = max(max_profit_pips, current_profit_pips)
            
            # IMPROVEMENT 3: Partial TP at 30 pips
            if position_size == 1.0 and candle['high'] >= partial_tp_price:
                partial_pnl = 30 * 0.5  # 50% at 30 pips
                total_pnl_pips += partial_pnl
                position_size = 0.5
                
                exits.append({
                    'type': 'Partial TP (30p)',
                    'pips': partial_pnl
                })
                
                # IMPROVEMENT 4: Move SL to breakeven
                trailing_sl = entry_price
                trailing_active = True
                continue
            
            # IMPROVEMENT 5: Trailing SL after 15 pips profit
            if trailing_active and position_size > 0:
                if current_profit_pips > 15:
                    # Trail at 50% of profit above 15 pips
                    profit_above_15 = current_profit_pips - 15
                    new_trailing = entry_price + ((15 + profit_above_15 * 0.5) * 0.10)
                    trailing_sl = max(trailing_sl, new_trailing)
            
            # Check SL
            active_sl = trailing_sl if trailing_active else stop_loss
            
            if candle['low'] <= active_sl:
                exit_pips = (active_sl - entry_price) / 0.10
                total_pnl_pips += exit_pips * position_size
                
                exits.append({
                    'type': 'Trailing SL' if trailing_active else 'SL',
                    'pips': exit_pips * position_size
                })
                
                position_size = 0
                break
            
            # Check full TP
            if candle['high'] >= take_profit:
                exit_pips = (take_profit - entry_price) / 0.10
                total_pnl_pips += exit_pips * position_size
                
                exits.append({
                    'type': 'Full TP',
                    'pips': exit_pips * position_size
                })
                
                position_size = 0
                break
        
        # Timeout
        if position_size > 0:
            exit_price = df_future['close'].iloc[-1]
            exit_pips = (exit_price - entry_price) / 0.10
            total_pnl_pips += exit_pips * position_size
            
            exits.append({
                'type': 'TIMEOUT',
                'pips': exit_pips * position_size
            })
        
        partial_hit = any(e['type'].startswith('Partial TP') for e in exits)
        
        trades.append({
            'entry_time': entry_time,
            'pattern': signal['pattern'],
            'type': pattern_type,
            'pnl_pips': total_pnl_pips,
            'max_profit_pips': max_profit_pips,
            'reached_30pips': max_profit_pips >= 30,
            'partial_tp_hit': partial_hit,
            'exits': exits
        })
    
    trades_df = pd.DataFrame(trades)
    
    # Results
    print(f"\n✅ Результаты С УЛУЧШЕНИЯМИ:")
    print(f"   {'='*80}")
    print(f"   Total Trades:      {len(trades_df)}")
    
    if len(trades_df) > 0:
        wins = len(trades_df[trades_df['pnl_pips'] > 0])
        win_rate = wins / len(trades_df) * 100
        
        total_pnl = trades_df['pnl_pips'].sum()
        avg_pnl = trades_df['pnl_pips'].mean()
        
        partial_hits = len(trades_df[trades_df['partial_tp_hit'] == True])
        
        print(f"   Win Rate:          {win_rate:.1f}%")
        print(f"   Total PnL:         {total_pnl:+.0f} pips")
        print(f"   Avg PnL:           {avg_pnl:+.1f} pips")
        print(f"   Partial TP hit:    {partial_hits} ({partial_hits/len(trades_df)*100:.1f}%)")
        print(f"   {'='*80}")
        
        # By pattern
        print(f"\n   By Pattern:")
        for pattern_type in trades_df['type'].unique():
            type_trades = trades_df[trades_df['type'] == pattern_type]
            type_wr = len(type_trades[type_trades['pnl_pips'] > 0]) / len(type_trades) * 100
            type_avg = type_trades['pnl_pips'].mean()
            type_total = type_trades['pnl_pips'].sum()
            
            print(f"      {pattern_type:15s}: {len(type_trades):3d} trades | "
                  f"WR {type_wr:5.1f}% | Avg {type_avg:+6.1f}p | Total {type_total:+7.0f}p")
    
    return trades_df


def main():
    print("\n" + "="*100)
    print("АНАЛИЗ И УЛУЧШЕНИЕ СЛАБЫХ ПАТТЕРНОВ")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Load previous results
    print("\n📂 Loading previous backtest results...")
    
    try:
        trades_df = pd.read_csv('30pip_detector_final_high_conf.csv')
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
        
        print(f"✅ Loaded {len(trades_df)} trades from previous backtest")
        
        # Analyze MOMENTUM
        momentum_trades = analyze_pattern_trades(df, 'MOMENTUM', trades_df)
        momentum_improvements = propose_improvements_for_pattern('MOMENTUM', momentum_trades)
        
        # Analyze PULLBACK
        pullback_trades = analyze_pattern_trades(df, 'PULLBACK', trades_df)
        pullback_improvements = propose_improvements_for_pattern('PULLBACK', pullback_trades)
        
    except FileNotFoundError:
        print("❌ Previous results not found. Run thirty_pip_detector_final.py first.")
        return None, None
    
    # Test improvements
    print(f"\n" + "="*100)
    print("ТЕСТИРОВАНИЕ УЛУЧШЕНИЙ")
    print("="*100)
    
    detector = ThirtyPipMoveDetector(focus_long_only=True)
    
    # Original results
    print(f"\n1️⃣  ОРИГИНАЛ (без улучшений):")
    original_momentum = momentum_trades['pnl_pips'].sum()
    original_pullback = pullback_trades['pnl_pips'].sum()
    original_total = original_momentum + original_pullback
    
    print(f"   MOMENTUM: {len(momentum_trades)} trades, {original_momentum:+.0f} pips")
    print(f"   PULLBACK: {len(pullback_trades)} trades, {original_pullback:+.0f} pips")
    print(f"   TOTAL:    {original_total:+.0f} pips")
    
    # With improvements
    print(f"\n2️⃣  С УЛУЧШЕНИЯМИ:")
    improved_trades = backtest_with_improvements(df, detector)
    
    if len(improved_trades) > 0:
        improved_momentum = improved_trades[improved_trades['type'] == 'MOMENTUM']['pnl_pips'].sum()
        improved_pullback = improved_trades[improved_trades['type'] == 'PULLBACK']['pnl_pips'].sum()
        improved_total = improved_trades['pnl_pips'].sum()
        
        print(f"\n📊 СРАВНЕНИЕ:")
        print(f"   {'Pattern':<15} {'Original':<15} {'Improved':<15} {'Difference':<15}")
        print("-"*60)
        print(f"   {'MOMENTUM':<15} {original_momentum:>+13.0f}p {improved_momentum:>+13.0f}p {improved_momentum-original_momentum:>+13.0f}p")
        print(f"   {'PULLBACK':<15} {original_pullback:>+13.0f}p {improved_pullback:>+13.0f}p {improved_pullback-original_pullback:>+13.0f}p")
        print("-"*60)
        print(f"   {'TOTAL':<15} {original_total:>+13.0f}p {improved_total:>+13.0f}p {improved_total-original_total:>+13.0f}p")
        
        improvement_pct = ((improved_total - original_total) / abs(original_total) * 100) if original_total != 0 else 0
        
        print(f"\n💰 Улучшение: {improved_total-original_total:+.0f} пипсов ({improvement_pct:+.1f}%)")
        
        # Save
        improved_trades.to_csv('30pip_patterns_improved.csv', index=False)
        print(f"\n💾 Saved: 30pip_patterns_improved.csv")
    
    return improved_trades, trades_df


if __name__ == "__main__":
    improved_trades, original_trades = main()
