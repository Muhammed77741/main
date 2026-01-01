"""
Визуализация сравнения методов идентификации сигналов
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Данные из бэктеста
data = {
    'Method': [
        'Ensemble\n(Combined)',
        'Pattern\nRecognition',
        'Market Structure\nBreaks (BOS)',
        'Fair Value\nGaps (FVG)',
        'Supply/Demand\nZones',
        'Volatility\nBreakouts',
        'Liquidity\nSweeps',
        'RSI\nDivergences'
    ],
    'Trades': [1534, 437, 135, 81, 2619, 68, 354, 1159],
    'Win_Rate': [50.2, 56.5, 66.7, 44.4, 43.6, 35.3, 41.0, 38.7],
    'Total_PnL': [166.73, 85.70, 52.27, 2.19, -6.15, -9.04, -30.00, -115.94],
    'Profit_Factor': [1.30, 1.68, 2.61, 1.06, 0.99, 0.73, 0.81, 0.77],
    'Max_DD': [-47.38, -15.07, -5.89, -9.28, -77.93, -12.79, -43.06, -133.29]
}

df = pd.DataFrame(data)

# Create figure
fig = plt.figure(figsize=(18, 12))

# Define colors
colors_pnl = ['darkgreen' if x > 0 else 'darkred' for x in df['Total_PnL']]
colors_wr = ['green' if x >= 50 else 'orange' if x >= 40 else 'red' for x in df['Win_Rate']]

# ========================================================================
# 1. Total PnL Comparison (главный график)
# ========================================================================
ax1 = plt.subplot(2, 3, 1)
bars = ax1.barh(df['Method'], df['Total_PnL'], color=colors_pnl, alpha=0.8, edgecolor='black', linewidth=1.5)
ax1.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
ax1.set_xlabel('Total PnL (%)', fontsize=11, fontweight='bold')
ax1.set_title('📊 Total PnL Comparison', fontsize=13, fontweight='bold', pad=15)
ax1.grid(True, alpha=0.3, axis='x')

# Add value labels
for i, (bar, val) in enumerate(zip(bars, df['Total_PnL'])):
    width = bar.get_width()
    label_x = width + (5 if width > 0 else -5)
    ha = 'left' if width > 0 else 'right'
    ax1.text(label_x, bar.get_y() + bar.get_height()/2, 
             f'{val:+.1f}%',
             va='center', ha=ha, fontsize=9, fontweight='bold')

# Add medal emojis
best_3 = df.nlargest(3, 'Total_PnL')
for idx in best_3.index:
    if idx == best_3.index[0]:
        emoji = '🥇'
    elif idx == best_3.index[1]:
        emoji = '🥈'
    else:
        emoji = '🥉'
    y_pos = list(df['Method']).index(df.loc[idx, 'Method'])
    ax1.text(-180, y_pos, emoji, fontsize=16, va='center')

# ========================================================================
# 2. Win Rate Comparison
# ========================================================================
ax2 = plt.subplot(2, 3, 2)
bars_wr = ax2.barh(df['Method'], df['Win_Rate'], color=colors_wr, alpha=0.8, edgecolor='black', linewidth=1.5)
ax2.axvline(x=50, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='Target: 50%')
ax2.axvline(x=60, color='darkgreen', linestyle='--', linewidth=1.5, alpha=0.7, label='Excellent: 60%')
ax2.set_xlabel('Win Rate (%)', fontsize=11, fontweight='bold')
ax2.set_title('🎯 Win Rate Comparison', fontsize=13, fontweight='bold', pad=15)
ax2.grid(True, alpha=0.3, axis='x')
ax2.legend(fontsize=8, loc='lower right')

# Add value labels
for bar, val in zip(bars_wr, df['Win_Rate']):
    ax2.text(val + 1, bar.get_y() + bar.get_height()/2, 
             f'{val:.1f}%',
             va='center', ha='left', fontsize=9, fontweight='bold')

# ========================================================================
# 3. Profit Factor Comparison
# ========================================================================
ax3 = plt.subplot(2, 3, 3)
colors_pf = ['darkgreen' if x >= 1.5 else 'green' if x >= 1.0 else 'red' for x in df['Profit_Factor']]
bars_pf = ax3.barh(df['Method'], df['Profit_Factor'], color=colors_pf, alpha=0.8, edgecolor='black', linewidth=1.5)
ax3.axvline(x=1.0, color='orange', linestyle='--', linewidth=1.5, alpha=0.7, label='Break-even: 1.0')
ax3.axvline(x=1.5, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='Good: 1.5')
ax3.set_xlabel('Profit Factor', fontsize=11, fontweight='bold')
ax3.set_title('💰 Profit Factor Comparison', fontsize=13, fontweight='bold', pad=15)
ax3.grid(True, alpha=0.3, axis='x')
ax3.legend(fontsize=8, loc='lower right')

# Add value labels
for bar, val in zip(bars_pf, df['Profit_Factor']):
    ax3.text(val + 0.05, bar.get_y() + bar.get_height()/2, 
             f'{val:.2f}',
             va='center', ha='left', fontsize=9, fontweight='bold')

# ========================================================================
# 4. Number of Trades
# ========================================================================
ax4 = plt.subplot(2, 3, 4)
colors_trades = plt.cm.viridis(np.linspace(0.3, 0.9, len(df)))
bars_trades = ax4.bar(range(len(df)), df['Trades'], color=colors_trades, alpha=0.8, edgecolor='black', linewidth=1.5)
ax4.set_ylabel('Number of Trades', fontsize=11, fontweight='bold')
ax4.set_title('📈 Trading Activity', fontsize=13, fontweight='bold', pad=15)
ax4.set_xticks(range(len(df)))
ax4.set_xticklabels(df['Method'], rotation=45, ha='right', fontsize=8)
ax4.grid(True, alpha=0.3, axis='y')

# Add value labels
for bar, val in zip(bars_trades, df['Trades']):
    ax4.text(bar.get_x() + bar.get_width()/2, val + 50,
             f'{val}',
             ha='center', va='bottom', fontsize=9, fontweight='bold')

# ========================================================================
# 5. Maximum Drawdown
# ========================================================================
ax5 = plt.subplot(2, 3, 5)
colors_dd = ['green' if x > -20 else 'orange' if x > -50 else 'red' for x in df['Max_DD']]
bars_dd = ax5.barh(df['Method'], df['Max_DD'], color=colors_dd, alpha=0.8, edgecolor='black', linewidth=1.5)
ax5.axvline(x=-20, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='Good: -20%')
ax5.axvline(x=-50, color='orange', linestyle='--', linewidth=1.5, alpha=0.7, label='Acceptable: -50%')
ax5.set_xlabel('Maximum Drawdown (%)', fontsize=11, fontweight='bold')
ax5.set_title('📉 Risk Analysis (Max DD)', fontsize=13, fontweight='bold', pad=15)
ax5.grid(True, alpha=0.3, axis='x')
ax5.legend(fontsize=8, loc='lower left')

# Add value labels
for bar, val in zip(bars_dd, df['Max_DD']):
    label_x = val - 5
    ax5.text(label_x, bar.get_y() + bar.get_height()/2, 
             f'{val:.1f}%',
             va='center', ha='right', fontsize=9, fontweight='bold')

# ========================================================================
# 6. Overall Score (composite)
# ========================================================================
ax6 = plt.subplot(2, 3, 6)

# Calculate composite score
# Normalize metrics to 0-1 scale
norm_pnl = (df['Total_PnL'] - df['Total_PnL'].min()) / (df['Total_PnL'].max() - df['Total_PnL'].min())
norm_wr = df['Win_Rate'] / 100
norm_pf = df['Profit_Factor'] / df['Profit_Factor'].max()
norm_dd = 1 - (abs(df['Max_DD']) / abs(df['Max_DD'].max()))  # Inverse (less DD is better)

# Composite score (weighted average)
composite_score = (
    norm_pnl * 0.4 +      # 40% weight on PnL
    norm_wr * 0.25 +      # 25% weight on Win Rate
    norm_pf * 0.20 +      # 20% weight on Profit Factor
    norm_dd * 0.15        # 15% weight on low Drawdown
) * 100

df['Composite_Score'] = composite_score

# Plot
colors_score = plt.cm.RdYlGn(np.linspace(0.2, 0.9, len(df)))
sorted_df = df.sort_values('Composite_Score', ascending=True)
bars_score = ax6.barh(sorted_df['Method'], sorted_df['Composite_Score'], 
                      color=[colors_score[i] for i in range(len(sorted_df))],
                      alpha=0.8, edgecolor='black', linewidth=1.5)
ax6.set_xlabel('Composite Score (0-100)', fontsize=11, fontweight='bold')
ax6.set_title('🏆 Overall Performance Score', fontsize=13, fontweight='bold', pad=15)
ax6.grid(True, alpha=0.3, axis='x')

# Add value labels
for bar, val in zip(bars_score, sorted_df['Composite_Score']):
    ax6.text(val + 1, bar.get_y() + bar.get_height()/2, 
             f'{val:.1f}',
             va='center', ha='left', fontsize=9, fontweight='bold')

# Add medals
for i, idx in enumerate(sorted_df.index[-3:]):
    if i == 2:  # Best
        emoji = '🥇'
    elif i == 1:  # Second
        emoji = '🥈'
    else:  # Third
        emoji = '🥉'
    y_pos = list(sorted_df.index).index(idx)
    ax6.text(-5, y_pos, emoji, fontsize=16, va='center')

# ========================================================================
# Add overall title and description
# ========================================================================
fig.suptitle('🔍 Сравнение методов идентификации торговых сигналов - XAUUSD 1H', 
             fontsize=16, fontweight='bold', y=0.98)

# Add description box
description = (
    "Период: 13 месяцев | Свечи: 5,895 (1H) | TP: 50п | SL: 30п\n"
    "🥇 Ensemble: +166.73% | 🥈 Pattern Recognition: +85.70% | 🥉 BOS: +52.27%"
)
fig.text(0.5, 0.02, description, ha='center', fontsize=10, 
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.tight_layout(rect=[0, 0.03, 1, 0.96])
plt.savefig('signal_methods_comparison.png', dpi=150, bbox_inches='tight')
print("✅ Visualization saved: signal_methods_comparison.png")

# ========================================================================
# Print summary
# ========================================================================
print("\n" + "="*80)
print("ИТОГОВАЯ ТАБЛИЦА")
print("="*80)

sorted_by_score = df.sort_values('Composite_Score', ascending=False)
print(f"\n{'Место':<7} {'Метод':<25} {'Score':<8} {'PnL':<10} {'WR%':<8} {'PF':<8} {'Trades':<8}")
print("-" * 80)

for i, (idx, row) in enumerate(sorted_by_score.iterrows()):
    emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
    method_name = row['Method'].replace('\n', ' ')
    print(f"{emoji} #{i+1:<4} {method_name:<25} {row['Composite_Score']:>6.1f}  "
          f"{row['Total_PnL']:>+8.2f}%  {row['Win_Rate']:>6.1f}%  "
          f"{row['Profit_Factor']:>6.2f}  {row['Trades']:>6}")

print("\n" + "="*80)
print("РЕКОМЕНДАЦИИ")
print("="*80)

best = sorted_by_score.iloc[0]
print(f"\n🥇 ЛУЧШИЙ МЕТОД: {best['Method'].replace(chr(10), ' ')}")
print(f"   Composite Score: {best['Composite_Score']:.1f}/100")
print(f"   Total PnL: {best['Total_PnL']:+.2f}%")
print(f"   Win Rate: {best['Win_Rate']:.1f}%")
print(f"   Profit Factor: {best['Profit_Factor']:.2f}")
print(f"   Max DD: {best['Max_DD']:.2f}%")

print(f"\n💡 ТОП 3 РЕКОМЕНДАЦИИ:")
for i, (idx, row) in enumerate(sorted_by_score.head(3).iterrows()):
    method_name = row['Method'].replace('\n', ' ')
    print(f"   {i+1}. {method_name}: Score {row['Composite_Score']:.1f} (PnL: {row['Total_PnL']:+.2f}%)")

print("\n" + "="*80)
