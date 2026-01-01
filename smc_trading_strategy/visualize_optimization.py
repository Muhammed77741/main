"""
Визуализация результатов оптимизации
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def create_optimization_visualization():
    """Create comprehensive visualization"""
    
    # Load results
    results = pd.read_csv('optimization_results.csv')
    
    # Create figure
    fig = plt.figure(figsize=(20, 12))
    
    # 1. PnL Comparison
    ax1 = plt.subplot(2, 3, 1)
    configs = results['config'].tolist()
    pnls = results['pnl'].tolist()
    
    # Color code: green for best, yellow for good, red for bad
    colors = []
    baseline_pnl = 349.02
    for pnl in pnls:
        if pnl > baseline_pnl + 10:
            colors.append('#2ecc71')  # green
        elif pnl > baseline_pnl:
            colors.append('#f39c12')  # orange
        else:
            colors.append('#e74c3c')  # red
    
    # Plot top 8
    top8 = results.nlargest(8, 'pnl')
    ax1.barh(range(len(top8)), top8['pnl'], color=['#2ecc71' if i == 0 else '#3498db' for i in range(len(top8))])
    ax1.set_yticks(range(len(top8)))
    ax1.set_yticklabels(top8['config'])
    ax1.axvline(baseline_pnl, color='red', linestyle='--', linewidth=2, label=f'Baseline: {baseline_pnl:.1f}%')
    ax1.set_xlabel('Total PnL (%)', fontsize=12, fontweight='bold')
    ax1.set_title('📊 PnL Comparison (Top 8)', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(axis='x', alpha=0.3)
    
    # 2. Win Rate
    ax2 = plt.subplot(2, 3, 2)
    top8_wr = top8.sort_values('win_rate', ascending=False)
    colors_wr = ['#2ecc71' if wr > 65 else '#f39c12' if wr > 60 else '#e74c3c' for wr in top8_wr['win_rate']]
    ax2.barh(range(len(top8_wr)), top8_wr['win_rate'], color=colors_wr)
    ax2.set_yticks(range(len(top8_wr)))
    ax2.set_yticklabels(top8_wr['config'])
    ax2.axvline(65, color='green', linestyle='--', linewidth=2, alpha=0.5)
    ax2.set_xlabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax2.set_title('🎯 Win Rate Comparison', fontsize=14, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    # 3. Profit Factor
    ax3 = plt.subplot(2, 3, 3)
    top8_pf = top8.sort_values('pf', ascending=False)
    ax3.barh(range(len(top8_pf)), top8_pf['pf'], color=['#2ecc71' if pf > 6 else '#3498db' for pf in top8_pf['pf']])
    ax3.set_yticks(range(len(top8_pf)))
    ax3.set_yticklabels(top8_pf['config'])
    ax3.axvline(3.5, color='red', linestyle='--', linewidth=2, label='Baseline: 3.50')
    ax3.set_xlabel('Profit Factor', fontsize=12, fontweight='bold')
    ax3.set_title('💰 Profit Factor Comparison', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(axis='x', alpha=0.3)
    
    # 4. Trades Count
    ax4 = plt.subplot(2, 3, 4)
    ax4.bar(range(len(top8)), top8['trades'], color='#3498db', alpha=0.7)
    ax4.set_xticks(range(len(top8)))
    ax4.set_xticklabels(top8['config'], rotation=45, ha='right', fontsize=9)
    ax4.axhline(337, color='red', linestyle='--', linewidth=2, label='Max trades: 337')
    ax4.set_ylabel('Number of Trades', fontsize=12, fontweight='bold')
    ax4.set_title('📈 Trades Count', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)
    
    # 5. Efficiency (PnL per trade)
    ax5 = plt.subplot(2, 3, 5)
    top8_copy = top8.copy()
    top8_copy['pnl_per_trade'] = top8_copy['pnl'] / top8_copy['trades']
    top8_eff = top8_copy.sort_values('pnl_per_trade', ascending=False)
    ax5.barh(range(len(top8_eff)), top8_eff['pnl_per_trade'], color='#9b59b6')
    ax5.set_yticks(range(len(top8_eff)))
    ax5.set_yticklabels(top8_eff['config'])
    ax5.set_xlabel('PnL per Trade (%)', fontsize=12, fontweight='bold')
    ax5.set_title('⚡ Efficiency (PnL/Trade)', fontsize=14, fontweight='bold')
    ax5.grid(axis='x', alpha=0.3)
    
    # 6. Summary Stats
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    best = results.loc[results['pnl'].idxmax()]
    baseline_wr = 57.4
    baseline_pf = 3.50
    
    summary_text = f"""
╔════════════════════════════════════════════╗
║         ОПТИМИЗАЦИЯ ЗАВЕРШЕНА ✅           ║
╚════════════════════════════════════════════╝

🏆 ЛУЧШАЯ КОНФИГУРАЦИЯ: {best['config']}

📊 Результаты:
   • Total PnL:      {best['pnl']:>8.2f}%
   • Win Rate:       {best['win_rate']:>8.1f}%
   • Profit Factor:  {best['pf']:>8.2f}
   • Trades:         {best['trades']:>8}

💰 Улучшения над Baseline:
   • PnL:            {best['pnl'] - baseline_pnl:>+8.2f}% ({(best['pnl'] - baseline_pnl) / baseline_pnl * 100:+.1f}%)
   • Win Rate:       {best['win_rate'] - baseline_wr:>+8.1f}%
   • Profit Factor:  {best['pf'] - baseline_pf:>+8.2f}

🔍 Ключевые находки:
   1. SHORT сделки: WR 31% → Исключить ❌
   2. LONG ONLY: +37% улучшение ✅
   3. TP=1.4 немного лучше 1.618 ✅
   4. Hour фильтр: ↑ качество, ↓ количество
   5. ATR фильтр: не эффективен ❌

🎯 Рекомендация:
   Использовать LONG ONLY + TP=1.4
   для максимизации прибыли!
"""
    
    ax6.text(0.1, 0.5, summary_text, transform=ax6.transAxes,
             fontsize=11, verticalalignment='center',
             fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    plt.suptitle('🚀 РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ BASELINE СТРАТЕГИИ', 
                 fontsize=18, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    plt.savefig('optimization_results.png', dpi=150, bbox_inches='tight')
    print("\n✅ Visualization saved: optimization_results.png")
    
    return fig


if __name__ == "__main__":
    create_optimization_visualization()
