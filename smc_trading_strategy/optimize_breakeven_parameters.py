"""
Оптимизация параметров Breakeven

Проблема: Breakeven @ 15 pips обрезает прибыли
Решение: Протестируем разные trigger levels и найдем оптимальный
"""

import pandas as pd
import numpy as np
from pattern_recognition_v6_breakeven import PatternRecognitionV6Breakeven


def test_breakeven_parameters(df, breakeven_configs):
    """
    Тестируем разные конфигурации breakeven
    """
    
    print("\n" + "="*100)
    print("🔬 ОПТИМИЗАЦИЯ ПАРАМЕТРОВ BREAKEVEN")
    print("="*100)
    
    results = []
    
    for config in breakeven_configs:
        print(f"\n{'='*100}")
        print(f"Testing: Breakeven @ {config['trigger']}p, Lock @ {config['lock']}p")
        print(f"{'='*100}")
        
        strategy = PatternRecognitionV6Breakeven(
            fib_mode='standard',
            tp_multiplier=1.4,
            enable_30pip_patterns=True,
            high_confidence_only=True,
            enable_breakeven=config['enabled'],
            breakeven_trigger_pips=config['trigger'],
            lock_profit_pips=config['lock']
        )
        
        trades_df = strategy.backtest_with_breakeven(df.copy())
        
        if len(trades_df) > 0:
            total_pnl = trades_df['pnl_pct'].sum()
            win_rate = len(trades_df[trades_df['pnl_pct'] > 0]) / len(trades_df) * 100
            
            gross_profit = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].sum()
            gross_loss = abs(trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].sum())
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
            
            cumulative = trades_df['pnl_pct'].cumsum()
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            max_drawdown = drawdown.min()
            
            breakeven_used = len(trades_df[trades_df['breakeven_used'] == True])
            
            results.append({
                'config': f"BE@{config['trigger']}p, Lock@{config['lock']}p" if config['enabled'] else "No Breakeven",
                'enabled': config['enabled'],
                'trigger': config['trigger'],
                'lock': config['lock'],
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'breakeven_used': breakeven_used,
                'breakeven_pct': breakeven_used / len(trades_df) * 100
            })
    
    return pd.DataFrame(results)


def main():
    print("\n" + "="*100)
    print("🎯 ПОИСК ОПТИМАЛЬНЫХ ПАРАМЕТРОВ BREAKEVEN")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Test configurations
    configs = [
        # Baseline (no breakeven)
        {'enabled': False, 'trigger': 0, 'lock': 0},
        
        # Very aggressive (current)
        {'enabled': True, 'trigger': 15, 'lock': 5},
        
        # Aggressive
        {'enabled': True, 'trigger': 20, 'lock': 5},
        {'enabled': True, 'trigger': 25, 'lock': 5},
        
        # Moderate
        {'enabled': True, 'trigger': 30, 'lock': 10},
        {'enabled': True, 'trigger': 35, 'lock': 10},
        {'enabled': True, 'trigger': 40, 'lock': 10},
        
        # Conservative
        {'enabled': True, 'trigger': 50, 'lock': 15},
        {'enabled': True, 'trigger': 60, 'lock': 20},
    ]
    
    print(f"\n🧪 Testing {len(configs)} configurations...")
    
    results_df = test_breakeven_parameters(df, configs)
    
    # Sort by total PnL
    results_df = results_df.sort_values('total_pnl', ascending=False)
    
    # Print comparison table
    print(f"\n" + "="*100)
    print("📊 RESULTS COMPARISON (sorted by Total PnL)")
    print("="*100)
    
    print(f"\n{'Config':<30} {'PnL':<12} {'WR':<8} {'PF':<8} {'MaxDD':<10} {'BE Used':<10}")
    print("-"*100)
    
    for _, row in results_df.iterrows():
        be_info = f"{row['breakeven_pct']:.1f}%" if row['enabled'] else "N/A"
        
        print(f"{row['config']:<30} {row['total_pnl']:>+10.2f}% {row['win_rate']:>6.1f}% "
              f"{row['profit_factor']:>6.2f} {row['max_drawdown']:>8.2f}% {be_info:>9s}")
    
    # Best config
    best = results_df.iloc[0]
    
    print(f"\n" + "="*100)
    print("🏆 BEST CONFIGURATION")
    print("="*100)
    
    print(f"\n   Config:         {best['config']}")
    print(f"   Total PnL:      {best['total_pnl']:+.2f}%")
    print(f"   Win Rate:       {best['win_rate']:.1f}%")
    print(f"   Profit Factor:  {best['profit_factor']:.2f}")
    print(f"   Max Drawdown:   {best['max_drawdown']:.2f}%")
    
    if best['enabled']:
        print(f"   Breakeven Used: {best['breakeven_used']} ({best['breakeven_pct']:.1f}%)")
    
    # Analysis
    print(f"\n" + "="*100)
    print("💡 ANALYSIS")
    print("="*100)
    
    no_be = results_df[results_df['enabled'] == False].iloc[0]
    best_be = results_df[results_df['enabled'] == True].iloc[0]
    
    pnl_diff = best['total_pnl'] - no_be['total_pnl']
    wr_diff = best['win_rate'] - no_be['win_rate']
    dd_diff = best['max_drawdown'] - no_be['max_drawdown']
    
    print(f"\n   Best Config vs No Breakeven:")
    print(f"   PnL:        {pnl_diff:+.2f}% ({(pnl_diff/no_be['total_pnl']*100):+.1f}%)")
    print(f"   Win Rate:   {wr_diff:+.1f}%")
    print(f"   Max DD:     {dd_diff:+.2f}% ({'better' if dd_diff > 0 else 'worse'})")
    
    if best['enabled']:
        print(f"\n   💡 Recommendation:")
        print(f"      Use Breakeven @ {best['trigger']} pips")
        print(f"      Lock profit:     {best['lock']} pips after 30p")
    else:
        print(f"\n   💡 Recommendation:")
        print(f"      DON'T use Breakeven - it reduces total PnL!")
        print(f"      The strategy works better without early breakeven")
    
    # Save results
    results_df.to_csv('breakeven_optimization_results.csv', index=False)
    print(f"\n💾 Saved: breakeven_optimization_results.csv")
    
    return results_df


if __name__ == "__main__":
    results_df = main()
