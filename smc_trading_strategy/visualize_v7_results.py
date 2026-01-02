"""
Визуализация результатов V7 HYBRID
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime

def plot_v7_results():
    """
    Создаёт графики результатов V7 HYBRID
    """
    
    # Load results
    try:
        df = pd.read_csv('pattern_recognition_v7_hybrid_backtest.csv')
        df['entry_time'] = pd.to_datetime(df['entry_time'])
    except:
        print("❌ File not found. Run pattern_recognition_v7_hybrid.py first!")
        return
    
    print(f"📊 Creating visualizations for {len(df)} trades...")
    
    # Create figure
    fig = plt.figure(figsize=(20, 12))
    
    # =====================================
    # 1. Cumulative PnL
    # =====================================
    ax1 = plt.subplot(3, 3, 1)
    
    df_sorted = df.sort_values('entry_time')
    df_sorted['cumulative_pnl'] = df_sorted['pnl_pct'].cumsum()
    
    # Overall
    ax1.plot(df_sorted['entry_time'], df_sorted['cumulative_pnl'], 
             linewidth=2, color='#2E7D32', label='Overall', alpha=0.8)
    
    # By source
    for source, color in [('BASELINE', '#1976D2'), ('30PIP', '#F57C00')]:
        source_df = df_sorted[df_sorted['source'] == source].copy()
        source_df['cumulative_pnl'] = source_df['pnl_pct'].cumsum()
        ax1.plot(source_df['entry_time'], source_df['cumulative_pnl'], 
                linewidth=1.5, color=color, label=source, alpha=0.6)
    
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.3)
    ax1.set_title('Cumulative PnL Over Time', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cumulative PnL (%)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # =====================================
    # 2. Win Rate by Source
    # =====================================
    ax2 = plt.subplot(3, 3, 2)
    
    sources = ['BASELINE', '30PIP', 'Overall']
    win_rates = []
    
    for source in sources:
        if source == 'Overall':
            trades = df
        else:
            trades = df[df['source'] == source]
        
        wr = len(trades[trades['pnl_pct'] > 0]) / len(trades) * 100
        win_rates.append(wr)
    
    colors = ['#1976D2', '#F57C00', '#2E7D32']
    bars = ax2.bar(sources, win_rates, color=colors, alpha=0.7)
    
    # Add value labels
    for i, (bar, wr) in enumerate(zip(bars, win_rates)):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{wr:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    ax2.set_title('Win Rate by Source', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Win Rate (%)')
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # =====================================
    # 3. PnL Distribution
    # =====================================
    ax3 = plt.subplot(3, 3, 3)
    
    wins = df[df['pnl_pct'] > 0]['pnl_pct']
    losses = df[df['pnl_pct'] <= 0]['pnl_pct']
    
    ax3.hist(wins, bins=30, color='#2E7D32', alpha=0.6, label=f'Wins ({len(wins)})')
    ax3.hist(losses, bins=30, color='#C62828', alpha=0.6, label=f'Losses ({len(losses)})')
    
    ax3.axvline(x=0, color='black', linestyle='--', linewidth=2)
    ax3.set_title('PnL Distribution', fontsize=14, fontweight='bold')
    ax3.set_xlabel('PnL (%)')
    ax3.set_ylabel('Frequency')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # =====================================
    # 4. 30-Pip Patterns Performance
    # =====================================
    ax4 = plt.subplot(3, 3, 4)
    
    pip_trades = df[df['source'] == '30PIP']
    
    if len(pip_trades) > 0:
        patterns = pip_trades.groupby('detector_pattern').agg({
            'pnl_pct': ['sum', 'mean', 'count']
        }).reset_index()
        patterns.columns = ['Pattern', 'Total_PnL', 'Avg_PnL', 'Count']
        patterns = patterns.sort_values('Total_PnL', ascending=True)
        
        colors_patterns = ['#C62828' if x < 0 else '#2E7D32' for x in patterns['Total_PnL']]
        
        bars = ax4.barh(patterns['Pattern'], patterns['Total_PnL'], color=colors_patterns, alpha=0.7)
        
        # Add counts
        for i, (bar, count) in enumerate(zip(bars, patterns['Count'])):
            ax4.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    f'n={int(count)}', ha='left', va='center', fontsize=9)
        
        ax4.axvline(x=0, color='black', linestyle='--', linewidth=2)
        ax4.set_title('30-Pip Patterns Performance', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Total PnL (%)')
        ax4.grid(True, alpha=0.3, axis='x')
    
    # =====================================
    # 5. Monthly Performance
    # =====================================
    ax5 = plt.subplot(3, 3, 5)
    
    df_sorted['month'] = df_sorted['entry_time'].dt.to_period('M')
    monthly = df_sorted.groupby('month')['pnl_pct'].sum().reset_index()
    monthly['month_str'] = monthly['month'].astype(str)
    
    colors_monthly = ['#C62828' if x < 0 else '#2E7D32' for x in monthly['pnl_pct']]
    bars = ax5.bar(range(len(monthly)), monthly['pnl_pct'], color=colors_monthly, alpha=0.7)
    
    ax5.set_xticks(range(len(monthly)))
    ax5.set_xticklabels(monthly['month_str'], rotation=45, ha='right')
    ax5.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax5.set_title('Monthly PnL', fontsize=14, fontweight='bold')
    ax5.set_ylabel('PnL (%)')
    ax5.grid(True, alpha=0.3, axis='y')
    
    # =====================================
    # 6. Drawdown
    # =====================================
    ax6 = plt.subplot(3, 3, 6)
    
    cumulative = df_sorted['pnl_pct'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = cumulative - running_max
    
    ax6.fill_between(df_sorted['entry_time'], drawdown, 0, color='#C62828', alpha=0.3)
    ax6.plot(df_sorted['entry_time'], drawdown, color='#C62828', linewidth=2)
    
    max_dd = drawdown.min()
    max_dd_date = df_sorted[drawdown == max_dd]['entry_time'].iloc[0]
    ax6.plot(max_dd_date, max_dd, 'ro', markersize=10, label=f'Max DD: {max_dd:.2f}%')
    
    ax6.set_title('Drawdown Over Time', fontsize=14, fontweight='bold')
    ax6.set_xlabel('Date')
    ax6.set_ylabel('Drawdown (%)')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    # =====================================
    # 7. Trade Duration (estimated)
    # =====================================
    ax7 = plt.subplot(3, 3, 7)
    
    # Count exit types
    exit_types = df['exit_type'].value_counts()
    
    # Simple categorization
    tp_count = sum([count for exit, count in exit_types.items() if 'TP' in exit])
    sl_count = sum([count for exit, count in exit_types.items() if 'SL' in exit])
    timeout_count = sum([count for exit, count in exit_types.items() if 'TIMEOUT' in exit])
    
    categories = ['TP', 'SL', 'TIMEOUT']
    counts = [tp_count, sl_count, timeout_count]
    colors_exit = ['#2E7D32', '#C62828', '#FFA726']
    
    wedges, texts, autotexts = ax7.pie(counts, labels=categories, colors=colors_exit, 
                                        autopct='%1.1f%%', startangle=90, alpha=0.7)
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    ax7.set_title('Exit Type Distribution', fontsize=14, fontweight='bold')
    
    # =====================================
    # 8. Breakeven Impact (30-Pip only)
    # =====================================
    ax8 = plt.subplot(3, 3, 8)
    
    pip_trades = df[df['source'] == '30PIP']
    
    if len(pip_trades) > 0 and 'breakeven_used' in pip_trades.columns:
        be_used = len(pip_trades[pip_trades['breakeven_used'] == True])
        be_not_used = len(pip_trades[pip_trades['breakeven_used'] == False])
        
        categories_be = ['BE Used', 'BE Not Used']
        counts_be = [be_used, be_not_used]
        colors_be = ['#1976D2', '#757575']
        
        bars = ax8.bar(categories_be, counts_be, color=colors_be, alpha=0.7)
        
        # Add percentages
        for bar, count in zip(bars, counts_be):
            pct = count / len(pip_trades) * 100
            ax8.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                    f'{count}\n({pct:.1f}%)', ha='center', va='bottom', fontweight='bold')
        
        ax8.set_title('30-Pip: Breakeven Usage', fontsize=14, fontweight='bold')
        ax8.set_ylabel('Number of Trades')
        ax8.grid(True, alpha=0.3, axis='y')
    
    # =====================================
    # 9. Summary Stats
    # =====================================
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis('off')
    
    # Calculate stats
    total_pnl = df['pnl_pct'].sum()
    win_rate = len(df[df['pnl_pct'] > 0]) / len(df) * 100
    avg_win = df[df['pnl_pct'] > 0]['pnl_pct'].mean()
    avg_loss = df[df['pnl_pct'] < 0]['pnl_pct'].mean()
    
    gross_profit = df[df['pnl_pct'] > 0]['pnl_pct'].sum()
    gross_loss = abs(df[df['pnl_pct'] < 0]['pnl_pct'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    max_dd = drawdown.min()
    
    baseline_trades = len(df[df['source'] == 'BASELINE'])
    pip_trades_count = len(df[df['source'] == '30PIP'])
    
    stats_text = f"""
    ═══════════════════════════════
    V7 HYBRID STRATEGY RESULTS
    ═══════════════════════════════
    
    📊 Overall Performance:
    ─────────────────────────────
    Total PnL:         {total_pnl:+.2f}%
    Win Rate:          {win_rate:.1f}%
    Profit Factor:     {profit_factor:.2f}
    Max Drawdown:      {max_dd:.2f}%
    
    📈 Trade Stats:
    ─────────────────────────────
    Total Trades:      {len(df)}
    Wins:              {len(df[df['pnl_pct'] > 0])}
    Losses:            {len(df[df['pnl_pct'] <= 0])}
    
    Avg Win:           {avg_win:+.3f}%
    Avg Loss:          {avg_loss:+.3f}%
    
    🎯 By Source:
    ─────────────────────────────
    BASELINE:          {baseline_trades} trades
    30-PIP:            {pip_trades_count} trades
    
    ═══════════════════════════════
    Version: 7.0 (HYBRID)
    Date: {datetime.now().strftime('%Y-%m-%d')}
    ═══════════════════════════════
    """
    
    ax9.text(0.5, 0.5, stats_text, 
            ha='center', va='center',
            fontsize=11, family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    # Overall title
    fig.suptitle('Pattern Recognition V7 HYBRID - Performance Analysis', 
                 fontsize=18, fontweight='bold', y=0.995)
    
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    # Save
    plt.savefig('pattern_recognition_v7_hybrid_results.png', dpi=150, bbox_inches='tight')
    print(f"✅ Saved: pattern_recognition_v7_hybrid_results.png")
    
    plt.show()


def print_summary():
    """
    Печатает краткую сводку
    """
    
    try:
        df = pd.read_csv('pattern_recognition_v7_hybrid_backtest.csv')
    except:
        print("❌ File not found!")
        return
    
    print("\n" + "="*100)
    print("📊 V7 HYBRID STRATEGY - SUMMARY")
    print("="*100)
    
    # Overall
    total_pnl = df['pnl_pct'].sum()
    win_rate = len(df[df['pnl_pct'] > 0]) / len(df) * 100
    
    print(f"\n🎯 Overall:")
    print(f"   Total PnL:  {total_pnl:+.2f}%")
    print(f"   Win Rate:   {win_rate:.1f}%")
    print(f"   Trades:     {len(df)}")
    
    # By source
    print(f"\n📊 By Source:")
    for source in ['BASELINE', '30PIP']:
        source_df = df[df['source'] == source]
        source_pnl = source_df['pnl_pct'].sum()
        source_wr = len(source_df[source_df['pnl_pct'] > 0]) / len(source_df) * 100
        
        print(f"   {source:10s}: {len(source_df):3d} trades | WR {source_wr:5.1f}% | PnL {source_pnl:+7.2f}%")
    
    # 30-Pip breakdown
    pip_df = df[df['source'] == '30PIP']
    if len(pip_df) > 0:
        print(f"\n📈 30-Pip Patterns:")
        for pattern in pip_df['detector_pattern'].unique():
            pattern_df = pip_df[pip_df['detector_pattern'] == pattern]
            pattern_pnl = pattern_df['pnl_pct'].sum()
            pattern_wr = len(pattern_df[pattern_df['pnl_pct'] > 0]) / len(pattern_df) * 100
            
            print(f"   {pattern:15s}: {len(pattern_df):3d} trades | WR {pattern_wr:5.1f}% | PnL {pattern_pnl:+7.2f}%")


if __name__ == "__main__":
    print_summary()
    print("\n📊 Creating visualizations...")
    plot_v7_results()
