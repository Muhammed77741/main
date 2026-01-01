"""
Визуализация результатов месячного бэктеста
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Месячные данные из бэктеста
monthly_data = {
    'month': ['2024-12', '2025-01', '2025-02', '2025-03', '2025-04', '2025-05', 
              '2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12'],
    'trades': [1, 33, 29, 40, 32, 31, 39, 34, 49, 48, 37, 23, 41],
    'wins': [1, 23, 13, 29, 15, 14, 20, 11, 37, 27, 19, 18, 24],
    'losses': [0, 10, 16, 11, 17, 17, 19, 23, 12, 21, 18, 5, 17],
    'win_rate': [100.0, 69.7, 44.8, 72.5, 46.9, 45.2, 51.3, 32.4, 75.5, 56.2, 51.4, 78.3, 58.5],
    'pnl': [2.22, 288.30, -3.29, 11.93, -1.01, -6.24, 4.42, -14.10, 20.10, 18.02, 10.90, 9.87, 7.90]
}

df = pd.DataFrame(monthly_data)

# Create figure with subplots
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Pattern Recognition (1.618) - Месячный анализ бэктеста', fontsize=16, fontweight='bold')

# 1. PnL по месяцам
ax1 = axes[0, 0]
colors = ['green' if x > 0 else 'red' for x in df['pnl']]
bars1 = ax1.bar(range(len(df)), df['pnl'], color=colors, alpha=0.7, edgecolor='black')
ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax1.set_xlabel('Месяц')
ax1.set_ylabel('PnL (%)')
ax1.set_title('Месячная прибыльность')
ax1.set_xticks(range(len(df)))
ax1.set_xticklabels(df['month'], rotation=45, ha='right')
ax1.grid(True, alpha=0.3)

# Add value labels
for i, (bar, val) in enumerate(zip(bars1, df['pnl'])):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{val:+.1f}%',
             ha='center', va='bottom' if val > 0 else 'top', fontsize=8)

# 2. Win Rate по месяцам
ax2 = axes[0, 1]
ax2.plot(range(len(df)), df['win_rate'], marker='o', linewidth=2, markersize=8, color='blue')
ax2.axhline(y=60, color='green', linestyle='--', linewidth=1, label='Целевой WR: 60%')
ax2.axhline(y=50, color='orange', linestyle='--', linewidth=1, label='Минимальный WR: 50%')
ax2.fill_between(range(len(df)), 0, df['win_rate'], alpha=0.3, color='blue')
ax2.set_xlabel('Месяц')
ax2.set_ylabel('Win Rate (%)')
ax2.set_title('Win Rate по месяцам')
ax2.set_xticks(range(len(df)))
ax2.set_xticklabels(df['month'], rotation=45, ha='right')
ax2.set_ylim(0, 105)
ax2.grid(True, alpha=0.3)
ax2.legend()

# Add value labels
for i, (x, y) in enumerate(zip(range(len(df)), df['win_rate'])):
    ax2.text(x, y + 2, f'{y:.1f}%', ha='center', fontsize=8)

# 3. Количество сделок по месяцам
ax3 = axes[1, 0]
x = np.arange(len(df))
width = 0.35
bars_wins = ax3.bar(x - width/2, df['wins'], width, label='Wins', color='green', alpha=0.7, edgecolor='black')
bars_losses = ax3.bar(x + width/2, df['losses'], width, label='Losses', color='red', alpha=0.7, edgecolor='black')
ax3.set_xlabel('Месяц')
ax3.set_ylabel('Количество сделок')
ax3.set_title('Распределение прибыльных и убыточных сделок')
ax3.set_xticks(x)
ax3.set_xticklabels(df['month'], rotation=45, ha='right')
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# Add value labels
for bars in [bars_wins, bars_losses]:
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                 f'{int(height)}',
                 ha='center', va='bottom', fontsize=7)

# 4. Кумулятивный PnL
ax4 = axes[1, 1]
cumulative_pnl = df['pnl'].cumsum()
ax4.plot(range(len(df)), cumulative_pnl, marker='o', linewidth=2.5, markersize=10, 
         color='darkgreen', label='Кумулятивный PnL')
ax4.fill_between(range(len(df)), 0, cumulative_pnl, alpha=0.3, color='green')
ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax4.set_xlabel('Месяц')
ax4.set_ylabel('Кумулятивный PnL (%)')
ax4.set_title(f'Накопленная прибыль (Итого: +{cumulative_pnl.iloc[-1]:.2f}%)')
ax4.set_xticks(range(len(df)))
ax4.set_xticklabels(df['month'], rotation=45, ha='right')
ax4.grid(True, alpha=0.3)
ax4.legend()

# Add value labels
for i, (x, y) in enumerate(zip(range(len(df)), cumulative_pnl)):
    ax4.text(x, y + 5, f'{y:.0f}%', ha='center', fontsize=8, fontweight='bold')

plt.tight_layout()
plt.savefig('monthly_backtest_visualization.png', dpi=150, bbox_inches='tight')
print("✅ График сохранен: monthly_backtest_visualization.png")

# Дополнительная статистика
print("\n" + "="*80)
print("ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА")
print("="*80)

print(f"\n📊 Распределение результатов:")
print(f"   Прибыльных месяцев: {len(df[df['pnl'] > 0])} ({len(df[df['pnl'] > 0])/len(df)*100:.1f}%)")
print(f"   Убыточных месяцев: {len(df[df['pnl'] <= 0])} ({len(df[df['pnl'] <= 0])/len(df)*100:.1f}%)")

print(f"\n📈 Анализ волатильности:")
print(f"   Стандартное отклонение PnL: {df['pnl'].std():.2f}%")
print(f"   Максимальная просадка: {df['pnl'].min():.2f}%")
print(f"   Максимальный рост: {df['pnl'].max():.2f}%")

print(f"\n🎯 Win Rate статистика:")
print(f"   Средний Win Rate: {df['win_rate'].mean():.1f}%")
print(f"   Медианный Win Rate: {df['win_rate'].median():.1f}%")
print(f"   Лучший месяц (WR): {df['win_rate'].max():.1f}% ({df.loc[df['win_rate'].idxmax(), 'month']})")
print(f"   Худший месяц (WR): {df['win_rate'].min():.1f}% ({df.loc[df['win_rate'].idxmin(), 'month']})")

print(f"\n💼 Активность торговли:")
print(f"   Всего сделок: {df['trades'].sum()}")
print(f"   Среднее сделок в месяц: {df['trades'].mean():.1f}")
print(f"   Медианное количество: {df['trades'].median():.0f}")
print(f"   Самый активный месяц: {df['trades'].max()} ({df.loc[df['trades'].idxmax(), 'month']})")
print(f"   Самый спокойный месяц: {df['trades'].min()} ({df.loc[df['trades'].idxmin(), 'month']})")

# Анализ streak
print(f"\n🔥 Анализ серий:")
winning_streak = 0
losing_streak = 0
max_winning_streak = 0
max_losing_streak = 0
current_winning = 0
current_losing = 0

for pnl in df['pnl']:
    if pnl > 0:
        current_winning += 1
        current_losing = 0
        max_winning_streak = max(max_winning_streak, current_winning)
    else:
        current_losing += 1
        current_winning = 0
        max_losing_streak = max(max_losing_streak, current_losing)

print(f"   Максимальная серия прибыльных месяцев: {max_winning_streak}")
print(f"   Максимальная серия убыточных месяцев: {max_losing_streak}")

# Квартальный анализ
print(f"\n📅 Квартальный анализ:")
df['quarter'] = pd.to_datetime(df['month']).dt.quarter
quarterly = df.groupby('quarter').agg({
    'pnl': 'sum',
    'trades': 'sum',
    'win_rate': 'mean'
})

for quarter, row in quarterly.iterrows():
    print(f"   Q{quarter}: PnL {row['pnl']:+.2f}% | Сделок: {row['trades']} | Средний WR: {row['win_rate']:.1f}%")

print("\n" + "="*80)
print("✅ АНАЛИЗ ЗАВЕРШЕН!")
print("="*80)
