"""
Создание визуализаций месячных результатов
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Данные из monthly_analysis
monthly_data = {
    'Month': ['2024-12', '2025-01', '2025-02', '2025-03', '2025-04', '2025-05', 
              '2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12'],
    'Trades': [1, 33, 29, 40, 32, 31, 39, 34, 49, 48, 37, 23, 41],
    'Wins': [1, 23, 13, 29, 15, 14, 20, 11, 37, 27, 19, 18, 24],
    'Losses': [0, 10, 16, 11, 17, 17, 19, 23, 12, 21, 18, 5, 17],
    'WinRate': [100.0, 69.7, 44.8, 72.5, 46.9, 45.2, 51.3, 32.4, 75.5, 56.2, 51.4, 78.3, 58.5],
    'PnL': [2.22, 288.30, -3.29, 11.93, -1.01, -6.24, 4.42, -14.10, 20.10, 18.02, 10.90, 9.87, 7.90]
}

df = pd.DataFrame(monthly_data)

# Создать фигуру
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Pattern Recognition Strategy - Месячные Результаты (H1 XAUUSD)', 
             fontsize=16, fontweight='bold')

# График 1: Месячный PnL
ax1 = axes[0, 0]
colors = ['green' if pnl > 0 else 'red' for pnl in df['PnL']]
bars = ax1.bar(df['Month'], df['PnL'], color=colors, alpha=0.7, edgecolor='black')
ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
ax1.set_title('Месячный PnL (%)', fontsize=12, fontweight='bold')
ax1.set_xlabel('Месяц')
ax1.set_ylabel('PnL (%)')
ax1.tick_params(axis='x', rotation=45)
ax1.grid(True, alpha=0.3, axis='y')

# Добавить значения на столбцы
for i, bar in enumerate(bars):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:+.1f}%',
             ha='center', va='bottom' if height > 0 else 'top', 
             fontsize=8, fontweight='bold')

# График 2: Кумулятивный PnL
ax2 = axes[0, 1]
df['Cumulative_PnL'] = df['PnL'].cumsum()
ax2.plot(df['Month'], df['Cumulative_PnL'], marker='o', linewidth=2, 
         markersize=8, color='blue', label='Кумулятивный PnL')
ax2.fill_between(range(len(df)), 0, df['Cumulative_PnL'], alpha=0.3, color='blue')
ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax2.set_title('Кумулятивный PnL (%)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Месяц')
ax2.set_ylabel('Кумулятивный PnL (%)')
ax2.tick_params(axis='x', rotation=45)
ax2.grid(True, alpha=0.3)
ax2.legend()

# Добавить финальное значение
final_pnl = df['Cumulative_PnL'].iloc[-1]
ax2.text(len(df)-1, final_pnl, f'{final_pnl:+.1f}%', 
         ha='left', va='bottom', fontsize=10, fontweight='bold', color='blue')

# График 3: Win Rate по месяцам
ax3 = axes[1, 0]
colors_wr = ['green' if wr >= 60 else 'orange' if wr >= 50 else 'red' for wr in df['WinRate']]
bars_wr = ax3.bar(df['Month'], df['WinRate'], color=colors_wr, alpha=0.7, edgecolor='black')
ax3.axhline(y=60, color='green', linestyle='--', alpha=0.5, label='Целевой WR (60%)')
ax3.axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='Безубыток (50%)')
ax3.set_title('Win Rate по месяцам (%)', fontsize=12, fontweight='bold')
ax3.set_xlabel('Месяц')
ax3.set_ylabel('Win Rate (%)')
ax3.tick_params(axis='x', rotation=45)
ax3.grid(True, alpha=0.3, axis='y')
ax3.legend()
ax3.set_ylim(0, 100)

# Добавить значения
for i, bar in enumerate(bars_wr):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.1f}%',
             ha='center', va='bottom', 
             fontsize=8, fontweight='bold')

# График 4: Количество сделок
ax4 = axes[1, 1]
x = np.arange(len(df))
width = 0.35

ax4.bar(x - width/2, df['Wins'], width, label='Wins', color='green', alpha=0.7, edgecolor='black')
ax4.bar(x + width/2, df['Losses'], width, label='Losses', color='red', alpha=0.7, edgecolor='black')
ax4.set_title('Wins vs Losses по месяцам', fontsize=12, fontweight='bold')
ax4.set_xlabel('Месяц')
ax4.set_ylabel('Количество сделок')
ax4.set_xticks(x)
ax4.set_xticklabels(df['Month'], rotation=45)
ax4.legend()
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('monthly_results.png', dpi=150, bbox_inches='tight')
print("📊 График сохранен: monthly_results.png")

# Создать сводку
print("\n" + "="*80)
print("📊 КРАТКАЯ СВОДКА")
print("="*80)
print(f"\nВсего месяцев: {len(df)}")
print(f"Прибыльных: {len(df[df['PnL'] > 0])} ({len(df[df['PnL'] > 0])/len(df)*100:.1f}%)")
print(f"Убыточных: {len(df[df['PnL'] < 0])} ({len(df[df['PnL'] < 0])/len(df)*100:.1f}%)")
print(f"\nОбщий PnL: {df['PnL'].sum():+.2f}%")
print(f"Средний месячный PnL: {df['PnL'].mean():+.2f}%")
print(f"Медианный PnL: {df['PnL'].median():+.2f}%")
print(f"\nЛучший месяц: {df.loc[df['PnL'].idxmax(), 'Month']} ({df['PnL'].max():+.2f}%)")
print(f"Худший месяц: {df.loc[df['PnL'].idxmin(), 'Month']} ({df['PnL'].min():+.2f}%)")
print(f"\nСреднее сделок в месяц: {df['Trades'].mean():.1f}")
print(f"Средний Win Rate: {df['WinRate'].mean():.1f}%")

# Анализ серий
print(f"\n" + "="*80)
print("📈 СЕРИИ")
print("="*80)
streak = 0
max_win_streak = 0
max_loss_streak = 0
current_win_streak = 0
current_loss_streak = 0

for pnl in df['PnL']:
    if pnl > 0:
        current_win_streak += 1
        current_loss_streak = 0
        max_win_streak = max(max_win_streak, current_win_streak)
    else:
        current_loss_streak += 1
        current_win_streak = 0
        max_loss_streak = max(max_loss_streak, current_loss_streak)

print(f"Максимальная серия прибыльных месяцев: {max_win_streak}")
print(f"Максимальная серия убыточных месяцев: {max_loss_streak}")

# Квартальный анализ
print(f"\n" + "="*80)
print("📅 КВАРТАЛЬНЫЙ АНАЛИЗ")
print("="*80)

# Q4 2024
q4_2024 = df[df['Month'].str.startswith('2024')]['PnL'].sum()
print(f"Q4 2024 (Dec): {q4_2024:+.2f}%")

# Q1 2025
q1_2025 = df[df['Month'].isin(['2025-01', '2025-02', '2025-03'])]['PnL'].sum()
print(f"Q1 2025 (Jan-Mar): {q1_2025:+.2f}%")

# Q2 2025
q2_2025 = df[df['Month'].isin(['2025-04', '2025-05', '2025-06'])]['PnL'].sum()
print(f"Q2 2025 (Apr-Jun): {q2_2025:+.2f}%")

# Q3 2025
q3_2025 = df[df['Month'].isin(['2025-07', '2025-08', '2025-09'])]['PnL'].sum()
print(f"Q3 2025 (Jul-Sep): {q3_2025:+.2f}%")

# Q4 2025
q4_2025 = df[df['Month'].isin(['2025-10', '2025-11', '2025-12'])]['PnL'].sum()
print(f"Q4 2025 (Oct-Dec): {q4_2025:+.2f}%")

print(f"\n✅ Анализ завершен!")
