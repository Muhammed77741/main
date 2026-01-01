"""
Финальная визуализация: Baseline vs Optimized V2
"""

import matplotlib.pyplot as plt
import numpy as np

def create_final_comparison():
    """Create final comparison visualization"""
    
    fig = plt.figure(figsize=(18, 10))
    
    # Data
    baseline = {
        'pnl': 349.02,
        'win_rate': 57.4,
        'pf': 3.50,
        'trades': 437,
        'long_trades': 337,
        'short_trades': 100,
        'long_wr': 65.3,
        'short_wr': 31.0
    }
    
    optimized = {
        'pnl': 386.92,
        'win_rate': 65.6,
        'pf': 5.62,
        'trades': 337,
        'long_trades': 337,
        'short_trades': 0,
        'long_wr': 65.6,
        'short_wr': 0
    }
    
    # 1. PnL Comparison
    ax1 = plt.subplot(2, 3, 1)
    bars = ax1.bar(['Baseline', 'Optimized V2'], 
                   [baseline['pnl'], optimized['pnl']], 
                   color=['#3498db', '#2ecc71'], width=0.6)
    ax1.set_ylabel('Total PnL (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Total PnL Comparison', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 450)
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'+{height:.1f}%',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Add improvement
    improvement = optimized['pnl'] - baseline['pnl']
    improvement_pct = (improvement / baseline['pnl']) * 100
    ax1.text(0.5, 420, f'Improvement: +{improvement:.1f}% (+{improvement_pct:.1f}%)',
            ha='center', fontsize=10, color='green', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    
    ax1.grid(axis='y', alpha=0.3)
    
    # 2. Win Rate Comparison
    ax2 = plt.subplot(2, 3, 2)
    bars = ax2.bar(['Baseline', 'Optimized V2'], 
                   [baseline['win_rate'], optimized['win_rate']], 
                   color=['#3498db', '#2ecc71'], width=0.6)
    ax2.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax2.set_title('Win Rate Comparison', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, 80)
    ax2.axhline(50, color='red', linestyle='--', linewidth=1, alpha=0.5)
    
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    improvement_wr = optimized['win_rate'] - baseline['win_rate']
    ax2.text(0.5, 75, f'Improvement: +{improvement_wr:.1f}%',
            ha='center', fontsize=10, color='green', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    
    ax2.grid(axis='y', alpha=0.3)
    
    # 3. Profit Factor Comparison
    ax3 = plt.subplot(2, 3, 3)
    bars = ax3.bar(['Baseline', 'Optimized V2'], 
                   [baseline['pf'], optimized['pf']], 
                   color=['#3498db', '#2ecc71'], width=0.6)
    ax3.set_ylabel('Profit Factor', fontsize=12, fontweight='bold')
    ax3.set_title('Profit Factor Comparison', fontsize=14, fontweight='bold')
    ax3.set_ylim(0, 7)
    ax3.axhline(2, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='Good (2.0)')
    
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    improvement_pf = optimized['pf'] - baseline['pf']
    improvement_pf_pct = (improvement_pf / baseline['pf']) * 100
    ax3.text(0.5, 6.5, f'Improvement: +{improvement_pf:.2f} (+{improvement_pf_pct:.1f}%)',
            ha='center', fontsize=10, color='green', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    
    ax3.legend(loc='upper left', fontsize=9)
    ax3.grid(axis='y', alpha=0.3)
    
    # 4. Trades Breakdown
    ax4 = plt.subplot(2, 3, 4)
    
    x = np.arange(2)
    width = 0.35
    
    long_bars = ax4.bar(x - width/2, [baseline['long_trades'], optimized['long_trades']], 
                       width, label='LONG', color='#2ecc71', alpha=0.8)
    short_bars = ax4.bar(x + width/2, [baseline['short_trades'], optimized['short_trades']], 
                        width, label='SHORT', color='#e74c3c', alpha=0.8)
    
    ax4.set_ylabel('Number of Trades', fontsize=12, fontweight='bold')
    ax4.set_title('Trades Breakdown', fontsize=14, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(['Baseline', 'Optimized V2'])
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bars in [long_bars, short_bars]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # 5. LONG vs SHORT Win Rate
    ax5 = plt.subplot(2, 3, 5)
    
    categories = ['LONG WR', 'SHORT WR']
    baseline_wrs = [baseline['long_wr'], baseline['short_wr']]
    optimized_wrs = [optimized['long_wr'], 0]
    
    x = np.arange(len(categories))
    width = 0.35
    
    ax5.bar(x - width/2, baseline_wrs, width, label='Baseline', color='#3498db', alpha=0.8)
    ax5.bar(x + width/2, optimized_wrs, width, label='Optimized', color='#2ecc71', alpha=0.8)
    
    ax5.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax5.set_title('LONG vs SHORT Win Rate', fontsize=14, fontweight='bold')
    ax5.set_xticks(x)
    ax5.set_xticklabels(categories)
    ax5.legend()
    ax5.axhline(50, color='red', linestyle='--', linewidth=1, alpha=0.5)
    ax5.set_ylim(0, 80)
    ax5.grid(axis='y', alpha=0.3)
    
    # Highlight the problem
    ax5.text(1, 35, 'Problem!\nRemoved in V2', 
            ha='center', fontsize=10, color='red', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#ffcccc', alpha=0.7))
    
    # 6. Key Changes Summary
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    summary_text = """
OPTIMIZATION SUMMARY

Key Changes in V2:
------------------------

1. LONG ONLY
   - Removed all SHORT trades (100)
   - SHORT Win Rate was only 31%
   - Impact: +37% PnL

2. TP Optimization
   - Changed from 1.618 to 1.4
   - Small improvement: +0.9% PnL

Results:
------------------------

Total PnL:       +37.90% (+10.9%)
Win Rate:        +8.2%
Profit Factor:   +2.12 (+60.6%)

Expected Annual Return:
~+387% (vs +349% baseline)

Recommendation:
Use PatternRecognitionOptimizedV2
with long_only=True
"""
    
    ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes,
             fontsize=10, verticalalignment='top',
             fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    # Add winner badge
    ax6.text(0.5, 0.05, 'Optimized V2 WINS!', transform=ax6.transAxes,
             fontsize=16, fontweight='bold', color='green',
             ha='center', va='bottom',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7, pad=0.5))
    
    plt.suptitle('BASELINE vs OPTIMIZED V2: Complete Comparison', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    plt.tight_layout()
    plt.savefig('baseline_vs_optimized_comparison.png', dpi=150, bbox_inches='tight')
    print("\nVisualization saved: baseline_vs_optimized_comparison.png")
    
    return fig


if __name__ == "__main__":
    create_final_comparison()
