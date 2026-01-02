"""
Детальный анализ 30-pip сигналов

Почему некоторые в плюсе, а некоторые в минусе?
"""

import pandas as pd
import numpy as np


def analyze_30pip_trades():
    """
    Анализ всех 30-pip сигналов
    """
    
    print("\n" + "="*100)
    print("🔍 ДЕТАЛЬНЫЙ АНАЛИЗ 30-PIP СИГНАЛОВ")
    print("="*100)
    
    # Load data
    try:
        df = pd.read_csv('pattern_recognition_v7_hybrid_backtest.csv')
        df['entry_time'] = pd.to_datetime(df['entry_time'])
    except:
        print("❌ File not found. Run pattern_recognition_v7_hybrid.py first!")
        return
    
    # Filter 30-pip trades only
    pip_trades = df[df['source'] == '30PIP'].copy()
    
    print(f"\n📊 Всего 30-PIP сигналов: {len(pip_trades)}")
    
    if len(pip_trades) == 0:
        print("No 30-pip trades!")
        return
    
    # Overall stats
    wins = pip_trades[pip_trades['pnl_pct'] > 0]
    losses = pip_trades[pip_trades['pnl_pct'] <= 0]
    
    print(f"\n✅ В ПЛЮСЕ:  {len(wins)} ({len(wins)/len(pip_trades)*100:.1f}%)")
    print(f"❌ В МИНУСЕ: {len(losses)} ({len(losses)/len(pip_trades)*100:.1f}%)")
    
    print(f"\n💰 PnL:")
    print(f"   Wins:   {wins['pnl_pct'].sum():+.2f}% (avg {wins['pnl_pct'].mean():+.2f}%)")
    print(f"   Losses: {losses['pnl_pct'].sum():+.2f}% (avg {losses['pnl_pct'].mean():+.2f}%)")
    print(f"   TOTAL:  {pip_trades['pnl_pct'].sum():+.2f}%")
    
    # By pattern
    print(f"\n" + "="*100)
    print("📊 ПО ПАТТЕРНАМ")
    print("="*100)
    
    for pattern in sorted(pip_trades['detector_pattern'].unique()):
        pattern_trades = pip_trades[pip_trades['detector_pattern'] == pattern]
        
        pattern_wins = pattern_trades[pattern_trades['pnl_pct'] > 0]
        pattern_losses = pattern_trades[pattern_trades['pnl_pct'] <= 0]
        
        wr = len(pattern_wins) / len(pattern_trades) * 100
        total_pnl = pattern_trades['pnl_pct'].sum()
        
        print(f"\n🎯 {pattern} ({len(pattern_trades)} сделок):")
        print(f"   ─────────────────────────────────────────────")
        print(f"   ✅ Wins:   {len(pattern_wins):3d} ({len(pattern_wins)/len(pattern_trades)*100:5.1f}%)")
        print(f"   ❌ Losses: {len(pattern_losses):3d} ({len(pattern_losses)/len(pattern_trades)*100:5.1f}%)")
        print(f"   💰 Total PnL: {total_pnl:+.2f}%")
        print(f"   📈 Avg Win:   {pattern_wins['pnl_pct'].mean():+.3f}%" if len(pattern_wins) > 0 else "")
        print(f"   📉 Avg Loss:  {pattern_losses['pnl_pct'].mean():+.3f}%" if len(pattern_losses) > 0 else "")
    
    # Analyze WHY losses happened
    print(f"\n" + "="*100)
    print("🔍 ПОЧЕМУ УБЫТКИ?")
    print("="*100)
    
    # Analyze exit types
    print(f"\n1️⃣  По типу выхода:")
    
    for exit_type_main in ['TP', 'SL', 'TIMEOUT']:
        # Match any exit containing this type
        exits = pip_trades[pip_trades['exit_type'].str.contains(exit_type_main, na=False)]
        
        if len(exits) > 0:
            exit_wins = len(exits[exits['pnl_pct'] > 0])
            exit_wr = exit_wins / len(exits) * 100
            exit_pnl = exits['pnl_pct'].sum()
            exit_avg = exits['pnl_pct'].mean()
            
            print(f"\n   {exit_type_main:10s}: {len(exits):3d} trades")
            print(f"      Wins:     {exit_wins} ({exit_wr:.1f}%)")
            print(f"      Total PnL: {exit_pnl:+.2f}%")
            print(f"      Avg PnL:   {exit_avg:+.3f}%")
    
    # Breakeven impact
    if 'breakeven_used' in pip_trades.columns:
        print(f"\n2️⃣  Влияние Breakeven:")
        
        be_used = pip_trades[pip_trades['breakeven_used'] == True]
        be_not_used = pip_trades[pip_trades['breakeven_used'] == False]
        
        print(f"\n   Breakeven ИСПОЛЬЗОВАН ({len(be_used)} trades):")
        if len(be_used) > 0:
            be_wins = len(be_used[be_used['pnl_pct'] > 0])
            be_wr = be_wins / len(be_used) * 100
            be_pnl = be_used['pnl_pct'].sum()
            
            print(f"      Wins:     {be_wins} ({be_wr:.1f}%)")
            print(f"      Total PnL: {be_pnl:+.2f}%")
            
            # Count BE saves (closed at breakeven after profit)
            be_saves = be_used[
                (be_used['pnl_pct'] >= -0.1) & 
                (be_used['pnl_pct'] <= 0.1)
            ]
            if len(be_saves) > 0:
                print(f"      💰 BE Saves: {len(be_saves)} (закрылись ~на нуле)")
        
        print(f"\n   Breakeven НЕ использован ({len(be_not_used)} trades):")
        if len(be_not_used) > 0:
            no_be_wins = len(be_not_used[be_not_used['pnl_pct'] > 0])
            no_be_wr = no_be_wins / len(be_not_used) * 100
            no_be_pnl = be_not_used['pnl_pct'].sum()
            
            print(f"      Wins:     {no_be_wins} ({no_be_wr:.1f}%)")
            print(f"      Total PnL: {no_be_pnl:+.2f}%")
    
    # Top losses analysis
    print(f"\n" + "="*100)
    print("❌ TOP 10 УБЫТОЧНЫХ СДЕЛОК")
    print("="*100)
    
    worst_trades = pip_trades.nsmallest(10, 'pnl_pct')
    
    print(f"\n{'Date':<20} {'Pattern':<12} {'PnL':<10} {'Exit Type':<30} {'BE Used':<10}")
    print("-"*100)
    
    for _, trade in worst_trades.iterrows():
        be_status = 'Yes' if trade.get('breakeven_used', False) else 'No'
        exit_type = trade['exit_type'][:28] if len(trade['exit_type']) > 28 else trade['exit_type']
        
        print(f"{str(trade['entry_time']):<20} {trade['detector_pattern']:<12} "
              f"{trade['pnl_pct']:>8.2f}% {exit_type:<30} {be_status:<10}")
    
    # Top wins analysis
    print(f"\n" + "="*100)
    print("✅ TOP 10 ПРИБЫЛЬНЫХ СДЕЛОК")
    print("="*100)
    
    best_trades = pip_trades.nlargest(10, 'pnl_pct')
    
    print(f"\n{'Date':<20} {'Pattern':<12} {'PnL':<10} {'Exit Type':<30} {'BE Used':<10}")
    print("-"*100)
    
    for _, trade in best_trades.iterrows():
        be_status = 'Yes' if trade.get('breakeven_used', False) else 'No'
        exit_type = trade['exit_type'][:28] if len(trade['exit_type']) > 28 else trade['exit_type']
        
        print(f"{str(trade['entry_time']):<20} {trade['detector_pattern']:<12} "
              f"{trade['pnl_pct']:>8.2f}% {exit_type:<30} {be_status:<10}")
    
    # Pattern-specific loss reasons
    print(f"\n" + "="*100)
    print("📊 ПОЧЕМУ КАЖДЫЙ ПАТТЕРН ПРОИГРЫВАЕТ")
    print("="*100)
    
    for pattern in sorted(pip_trades['detector_pattern'].unique()):
        pattern_losses = pip_trades[
            (pip_trades['detector_pattern'] == pattern) & 
            (pip_trades['pnl_pct'] < 0)
        ]
        
        if len(pattern_losses) > 0:
            print(f"\n{pattern} - {len(pattern_losses)} убыточных:")
            
            # Count by exit type
            exit_counts = {}
            for exit_type in ['SL', 'BE_SL', 'Trail_SL', 'TIMEOUT']:
                count = len(pattern_losses[pattern_losses['exit_type'].str.contains(exit_type, na=False)])
                if count > 0:
                    pct = count / len(pattern_losses) * 100
                    exit_counts[exit_type] = (count, pct)
            
            for exit_type, (count, pct) in sorted(exit_counts.items(), key=lambda x: x[1][0], reverse=True):
                print(f"   {exit_type:15s}: {count:3d} ({pct:5.1f}%)")
            
            # Avg loss
            avg_loss = pattern_losses['pnl_pct'].mean()
            print(f"   Avg Loss: {avg_loss:.3f}%")
    
    # Summary & Recommendations
    print(f"\n" + "="*100)
    print("💡 ВЫВОДЫ И РЕКОМЕНДАЦИИ")
    print("="*100)
    
    for pattern in sorted(pip_trades['detector_pattern'].unique()):
        pattern_trades = pip_trades[pip_trades['detector_pattern'] == pattern]
        pattern_wins = pattern_trades[pattern_trades['pnl_pct'] > 0]
        pattern_losses = pattern_trades[pattern_trades['pnl_pct'] <= 0]
        
        wr = len(pattern_wins) / len(pattern_trades) * 100
        total_pnl = pattern_trades['pnl_pct'].sum()
        
        print(f"\n🎯 {pattern}:")
        
        if wr >= 70:
            print(f"   ✅ ХОРОШИЙ паттерн (WR {wr:.1f}%, PnL {total_pnl:+.2f}%)")
            print(f"   👉 Продолжать использовать с текущими настройками")
        elif wr >= 60:
            print(f"   ⚠️  СРЕДНИЙ паттерн (WR {wr:.1f}%, PnL {total_pnl:+.2f}%)")
            print(f"   👉 Можно улучшить:")
            
            # Analyze main loss reason
            sl_losses = len(pattern_losses[pattern_losses['exit_type'].str.contains('SL', na=False) & ~pattern_losses['exit_type'].str.contains('BE_SL|Trail_SL', na=False)])
            timeout_losses = len(pattern_losses[pattern_losses['exit_type'].str.contains('TIMEOUT', na=False)])
            
            if sl_losses > len(pattern_losses) * 0.4:
                print(f"      • Много SL → Попробовать tighter SL или лучший entry timing")
            if timeout_losses > len(pattern_losses) * 0.3:
                print(f"      • Много TIMEOUT → Сигнал слабый, возможно фильтровать")
        else:
            print(f"   ❌ СЛАБЫЙ паттерн (WR {wr:.1f}%, PnL {total_pnl:+.2f}%)")
            print(f"   👉 Рекомендации:")
            print(f"      • Рассмотреть отключение этого паттерна")
            print(f"      • Или добавить дополнительные фильтры (RSI, volume, trend strength)")
    
    return pip_trades


def compare_with_without_breakeven():
    """
    Сравнение: что было бы БЕЗ breakeven для 30-pip
    """
    
    print(f"\n" + "="*100)
    print("🔬 ЧТО ЕСЛИ БЫ НЕ БЫЛО BREAKEVEN?")
    print("="*100)
    
    try:
        # Load V5 (without breakeven for 30-pip)
        v5_df = pd.read_csv('pattern_recognition_v5_final_backtest.csv')
        v5_pip = v5_df[v5_df['source'] == '30PIP']
        
        # Load V7 (with breakeven for 30-pip)
        v7_df = pd.read_csv('pattern_recognition_v7_hybrid_backtest.csv')
        v7_pip = v7_df[v7_df['source'] == '30PIP']
        
        print(f"\n📊 Сравнение V5 (No BE) vs V7 (With BE):")
        print(f"{'Metric':<20} {'V5 (No BE)':<15} {'V7 (With BE)':<15} {'Difference':<15}")
        print("-"*70)
        
        v5_pnl = v5_pip['pnl_pct'].sum()
        v7_pnl = v7_pip['pnl_pct'].sum()
        
        v5_wr = len(v5_pip[v5_pip['pnl_pct'] > 0]) / len(v5_pip) * 100
        v7_wr = len(v7_pip[v7_pip['pnl_pct'] > 0]) / len(v7_pip) * 100
        
        print(f"{'Total PnL':<20} {v5_pnl:>+13.2f}% {v7_pnl:>+13.2f}% {v7_pnl-v5_pnl:>+13.2f}%")
        print(f"{'Win Rate':<20} {v5_wr:>12.1f}% {v7_wr:>12.1f}% {v7_wr-v5_wr:>+12.1f}%")
        print(f"{'Trades':<20} {len(v5_pip):>13} {len(v7_pip):>13} {len(v7_pip)-len(v5_pip):>+13}")
        
        print(f"\n💡 Вывод:")
        if v7_pnl > v5_pnl:
            print(f"   ✅ Breakeven ПОМОГ: +{v7_pnl-v5_pnl:.2f}% PnL")
        else:
            print(f"   ❌ Breakeven УХУДШИЛ: {v7_pnl-v5_pnl:.2f}% PnL")
        
        print(f"   ✅ Win Rate вырос на {v7_wr-v5_wr:.1f}% (было {v5_wr:.1f}%, стало {v7_wr:.1f}%)")
        
        if v7_wr > v5_wr + 10:
            print(f"   🎯 Значительное улучшение Win Rate - Breakeven защищает много сделок!")
        
    except FileNotFoundError as e:
        print(f"   ⚠️  Не найден файл для сравнения: {e}")


def main():
    pip_trades = analyze_30pip_trades()
    
    if pip_trades is not None:
        compare_with_without_breakeven()
        
        # Save analysis
        pip_trades.to_csv('30pip_detailed_analysis.csv', index=False)
        print(f"\n💾 Saved: 30pip_detailed_analysis.csv")


if __name__ == "__main__":
    main()
