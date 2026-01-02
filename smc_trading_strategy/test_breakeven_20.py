"""
Тест: Breakeven @ 20 pips vs 25 pips для 30-pip паттернов
"""

import pandas as pd
from pattern_recognition_v7_hybrid import PatternRecognitionV7Hybrid


def compare_breakeven_levels(df):
    """
    Сравнение разных уровней breakeven для 30-pip паттернов
    """
    
    print("\n" + "="*100)
    print("🔬 ТЕСТ: BREAKEVEN @ 20 vs 25 PIPS")
    print("="*100)
    
    configs = [
        {'trigger': 20, 'trailing': 35, 'name': 'BE @ 20 pips'},
        {'trigger': 25, 'trailing': 40, 'name': 'BE @ 25 pips (current)'},
        {'trigger': 30, 'trailing': 45, 'name': 'BE @ 30 pips'},
        {'trigger': 15, 'trailing': 30, 'name': 'BE @ 15 pips'},
    ]
    
    results = []
    
    for config in configs:
        print(f"\n{'='*100}")
        print(f"Testing: {config['name']}, Trailing @ {config['trailing']}p")
        print(f"{'='*100}")
        
        strategy = PatternRecognitionV7Hybrid(
            fib_mode='standard',
            tp_multiplier=1.4,
            enable_30pip_patterns=True,
            high_confidence_only=True,
            pip_breakeven_trigger=config['trigger'],
            pip_trailing_trigger=config['trailing']
        )
        
        trades_df = strategy.backtest(df.copy())
        
        # Overall stats
        total_pnl = trades_df['pnl_pct'].sum()
        win_rate = len(trades_df[trades_df['pnl_pct'] > 0]) / len(trades_df) * 100
        
        cumulative = trades_df['pnl_pct'].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_dd = drawdown.min()
        
        # 30-Pip specific
        pip_trades = trades_df[trades_df['source'] == '30PIP']
        pip_pnl = pip_trades['pnl_pct'].sum()
        pip_wr = len(pip_trades[pip_trades['pnl_pct'] > 0]) / len(pip_trades) * 100 if len(pip_trades) > 0 else 0
        
        # Breakeven usage
        be_used = len(pip_trades[pip_trades['breakeven_used'] == True]) if 'breakeven_used' in pip_trades.columns else 0
        be_pct = be_used / len(pip_trades) * 100 if len(pip_trades) > 0 else 0
        
        # BE saves (closed near zero after reaching BE)
        be_saves = len(pip_trades[
            (pip_trades['breakeven_used'] == True) & 
            (pip_trades['pnl_pct'] >= -0.1) & 
            (pip_trades['pnl_pct'] <= 0.1)
        ]) if 'breakeven_used' in pip_trades.columns else 0
        
        results.append({
            'name': config['name'],
            'trigger': config['trigger'],
            'trailing': config['trailing'],
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'max_dd': max_dd,
            'pip_pnl': pip_pnl,
            'pip_wr': pip_wr,
            'be_used': be_used,
            'be_pct': be_pct,
            'be_saves': be_saves,
            'total_trades': len(trades_df),
            'pip_trades': len(pip_trades)
        })
    
    # Create comparison table
    results_df = pd.DataFrame(results)
    
    print(f"\n" + "="*100)
    print("📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print("="*100)
    
    print(f"\n{'Config':<25} {'Total PnL':<12} {'WR':<8} {'Max DD':<10} "
          f"{'30-Pip PnL':<12} {'30-Pip WR':<10} {'BE Used':<10}")
    print("-"*100)
    
    for _, row in results_df.iterrows():
        print(f"{row['name']:<25} {row['total_pnl']:>+10.2f}% {row['win_rate']:>6.1f}% {row['max_dd']:>8.2f}% "
              f"{row['pip_pnl']:>+10.2f}% {row['pip_wr']:>8.1f}% {row['be_used']:>3d} ({row['be_pct']:.0f}%)")
    
    # Detailed 30-Pip analysis
    print(f"\n" + "="*100)
    print("📊 30-PIP ДЕТАЛИ")
    print("="*100)
    
    print(f"\n{'Config':<25} {'30-Pip PnL':<12} {'WR':<8} {'BE Used':<15} {'BE Saves':<15}")
    print("-"*80)
    
    for _, row in results_df.iterrows():
        print(f"{row['name']:<25} {row['pip_pnl']:>+10.2f}% {row['pip_wr']:>6.1f}% "
              f"{row['be_used']:>3d}/{row['pip_trades']:<3d} ({row['be_pct']:>5.1f}%) "
              f"{row['be_saves']:>3d} ({row['be_saves']/row['pip_trades']*100 if row['pip_trades'] > 0 else 0:>5.1f}%)")
    
    # Best config
    best_idx = results_df['total_pnl'].idxmax()
    best = results_df.iloc[best_idx]
    
    print(f"\n" + "="*100)
    print("🏆 ЛУЧШАЯ КОНФИГУРАЦИЯ")
    print("="*100)
    
    print(f"\n   {best['name']}")
    print(f"   {'─'*50}")
    print(f"   Total PnL:      {best['total_pnl']:+.2f}%")
    print(f"   Win Rate:       {best['win_rate']:.1f}%")
    print(f"   Max Drawdown:   {best['max_dd']:.2f}%")
    print(f"   ")
    print(f"   30-Pip PnL:     {best['pip_pnl']:+.2f}%")
    print(f"   30-Pip WR:      {best['pip_wr']:.1f}%")
    print(f"   BE Used:        {best['be_used']}/{best['pip_trades']} ({best['be_pct']:.0f}%)")
    print(f"   BE Saves:       {best['be_saves']} trades")
    
    # Analysis & recommendation
    print(f"\n" + "="*100)
    print("💡 АНАЛИЗ")
    print("="*100)
    
    # Compare BE @ 20 vs 25
    be20 = results_df[results_df['trigger'] == 20].iloc[0]
    be25 = results_df[results_df['trigger'] == 25].iloc[0]
    
    print(f"\n📊 BE @ 20 pips vs BE @ 25 pips:")
    print(f"   {'Metric':<25} {'BE @ 20':<15} {'BE @ 25':<15} {'Difference':<15}")
    print(f"   {'-'*70}")
    print(f"   {'Total PnL':<25} {be20['total_pnl']:>+13.2f}% {be25['total_pnl']:>+13.2f}% {be20['total_pnl']-be25['total_pnl']:>+13.2f}%")
    print(f"   {'Win Rate':<25} {be20['win_rate']:>12.1f}% {be25['win_rate']:>12.1f}% {be20['win_rate']-be25['win_rate']:>+12.1f}%")
    print(f"   {'30-Pip PnL':<25} {be20['pip_pnl']:>+13.2f}% {be25['pip_pnl']:>+13.2f}% {be20['pip_pnl']-be25['pip_pnl']:>+13.2f}%")
    print(f"   {'30-Pip WR':<25} {be20['pip_wr']:>12.1f}% {be25['pip_wr']:>12.1f}% {be20['pip_wr']-be25['pip_wr']:>+12.1f}%")
    print(f"   {'BE Usage':<25} {be20['be_pct']:>12.1f}% {be25['be_pct']:>12.1f}% {be20['be_pct']-be25['be_pct']:>+12.1f}%")
    print(f"   {'BE Saves':<25} {be20['be_saves']:>13} {be25['be_saves']:>13} {be20['be_saves']-be25['be_saves']:>+13}")
    
    pnl_diff = be20['total_pnl'] - be25['total_pnl']
    pip_pnl_diff = be20['pip_pnl'] - be25['pip_pnl']
    
    print(f"\n💡 Выводы:")
    
    if pnl_diff > 0:
        print(f"   ✅ BE @ 20 ЛУЧШЕ на {pnl_diff:.2f}%")
        print(f"      • Total PnL: {be20['total_pnl']:+.2f}% vs {be25['total_pnl']:+.2f}%")
        print(f"      • 30-Pip: {be20['pip_pnl']:+.2f}% vs {be25['pip_pnl']:+.2f}%")
        
        if be20['be_used'] > be25['be_used']:
            more_protected = be20['be_used'] - be25['be_used']
            print(f"      • Защищено на {more_protected} сделок больше!")
        
        print(f"\n   👉 РЕКОМЕНДАЦИЯ: Использовать BE @ 20 pips")
        
    elif pnl_diff < -1:
        print(f"   ❌ BE @ 20 ХУЖЕ на {abs(pnl_diff):.2f}%")
        print(f"      • BE @ 20 слишком рано срабатывает")
        print(f"      • Обрезает потенциально большие профиты")
        
        print(f"\n   👉 РЕКОМЕНДАЦИЯ: Оставить BE @ 25 pips")
        
    else:
        print(f"   ⚖️  БЕЗ РАЗНИЦЫ (разница {pnl_diff:.2f}%)")
        print(f"      • Оба варианта дают похожие результаты")
        
        if be20['be_used'] > be25['be_used']:
            print(f"      • BE @ 20 защищает больше сделок ({be20['be_used']} vs {be25['be_used']})")
            print(f"\n   👉 РЕКОМЕНДАЦИЯ: BE @ 20 для большей безопасности")
        else:
            print(f"\n   👉 РЕКОМЕНДАЦИЯ: BE @ 25 (текущая настройка)")
    
    # Save results
    results_df.to_csv('breakeven_comparison_results.csv', index=False)
    print(f"\n💾 Saved: breakeven_comparison_results.csv")
    
    return results_df


def main():
    print("\n" + "="*100)
    print("🚀 ТЕСТИРОВАНИЕ BREAKEVEN @ 20 PIPS")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Test different BE levels
    results = compare_breakeven_levels(df)
    
    print(f"\n" + "="*100)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*100)


if __name__ == "__main__":
    main()
