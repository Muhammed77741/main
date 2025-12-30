"""
Месячное сравнение H1 vs H4+H1
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from pattern_recognition_strategy import PatternRecognitionStrategy
from multi_timeframe import MultiTimeframeData
from backtester import Backtester


def load_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load H1 data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    return df


def create_h4_from_h1(df_h1):
    """Create H4 data from H1 by resampling"""
    print("\n📊 Создание H4 из H1...")
    print(f"   H1 свечей: {len(df_h1)}")
    
    # Resample to 4H
    df_h4 = df_h1.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    print(f"   H4 свечей: {len(df_h4)} (4 H1 → 1 H4)")
    print(f"   Период H4: {df_h4.index[0]} до {df_h4.index[-1]}")
    
    return df_h4


def detect_h4_trend(df_h4, lookback=20):
    """Detect trend on H4"""
    if len(df_h4) < lookback:
        return 'SIDEWAYS'
    
    recent = df_h4.iloc[-lookback:]
    
    # EMA for trend
    ema_fast = recent['close'].ewm(span=10, adjust=False).mean()
    ema_slow = recent['close'].ewm(span=20, adjust=False).mean()
    
    current_fast = ema_fast.iloc[-1]
    current_slow = ema_slow.iloc[-1]
    
    # Percentage difference
    diff_pct = ((current_fast - current_slow) / current_slow) * 100
    
    # Price direction
    price_start = recent['close'].iloc[0]
    price_end = recent['close'].iloc[-1]
    price_change_pct = ((price_end - price_start) / price_start) * 100
    
    # Determine trend
    if diff_pct > 0.2 and price_change_pct > 1.0:
        return 'UP'
    elif diff_pct < -0.2 and price_change_pct < -1.0:
        return 'DOWN'
    else:
        return 'SIDEWAYS'


def run_monthly_backtest(df, strategy, use_h4_filter=False, df_h4=None):
    """Run backtest month by month"""
    
    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    # Apply H4 filter if requested
    if use_h4_filter and df_h4 is not None:
        filtered_signals = []
        
        for idx in df_signals.index:
            signal = df_signals.loc[idx]
            
            # Find corresponding H4 trend
            h4_candles = df_h4[df_h4.index <= idx]
            
            if len(h4_candles) >= 20:
                h4_trend = detect_h4_trend(h4_candles, lookback=20)
                
                # Filter logic
                if signal['signal'] == 1 and h4_trend == 'DOWN':
                    continue  # Skip LONG against DOWN trend
                elif signal['signal'] == -1 and h4_trend == 'UP':
                    continue  # Skip SHORT against UP trend
            
            filtered_signals.append(idx)
        
        df_signals = df_signals.loc[filtered_signals]
    
    # Group by month
    df_signals['month'] = df_signals.index.to_period('M')
    
    monthly_results = []
    
    for month in df_signals['month'].unique():
        month_signals = df_signals[df_signals['month'] == month]
        
        if len(month_signals) == 0:
            continue
        
        # Backtest for this month
        month_start = month_signals.index[0]
        month_end = month_signals.index[-1] + timedelta(days=30)
        
        df_month = df_strategy[(df_strategy.index >= month_start) & (df_strategy.index <= month_end)]
        
        # Create signals dataframe for this month
        df_month_signals = df_month.copy()
        df_month_signals['signal'] = 0
        for idx in month_signals.index:
            if idx in df_month_signals.index:
                df_month_signals.loc[idx, 'signal'] = month_signals.loc[idx, 'signal']
                df_month_signals.loc[idx, 'entry_price'] = month_signals.loc[idx, 'entry_price']
                df_month_signals.loc[idx, 'stop_loss'] = month_signals.loc[idx, 'stop_loss']
                df_month_signals.loc[idx, 'take_profit'] = month_signals.loc[idx, 'take_profit']
        
        # Run backtest
        backtester = Backtester(initial_capital=10000)
        stats = backtester.run(df_month_signals)
        
        monthly_results.append({
            'month': str(month),
            'trades': stats['total_trades'],
            'wins': stats['winning_trades'],
            'losses': stats['losing_trades'],
            'win_rate': stats.get('win_rate', 0),
            'return_pct': stats.get('total_return_pct', 0),
            'profit_factor': stats.get('profit_factor', 0),
            'max_dd': stats.get('max_drawdown', 0)
        })
    
    return pd.DataFrame(monthly_results)


def main():
    print("\n" + "="*80)
    print("📊 МЕСЯЧНОЕ СРАВНЕНИЕ: H1 vs H4+H1")
    print("="*80)
    
    # Load data
    print("\n📥 Загрузка данных...")
    df_h1 = load_data()
    print(f"   ✅ Загружено {len(df_h1)} H1 свечей")
    print(f"   📅 Период: {df_h1.index[0]} до {df_h1.index[-1]}")
    
    # Create H4
    df_h4 = create_h4_from_h1(df_h1)
    
    # Initialize strategy
    print("\n🎯 Инициализация стратегии...")
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    
    # Run H1 only backtest
    print("\n📈 Бэктест #1: H1 только (без фильтра)...")
    df_h1_monthly = run_monthly_backtest(df_h1, strategy, use_h4_filter=False)
    
    # Run H4+H1 backtest
    print("\n📈 Бэктест #2: H4+H1 (с фильтром)...")
    df_h4h1_monthly = run_monthly_backtest(df_h1, strategy, use_h4_filter=True, df_h4=df_h4)
    
    # Merge results
    print("\n" + "="*80)
    print("📊 МЕСЯЧНЫЕ РЕЗУЛЬТАТЫ")
    print("="*80)
    
    # Combine dataframes
    df_comparison = df_h1_monthly.merge(
        df_h4h1_monthly,
        on='month',
        suffixes=('_h1', '_h4h1'),
        how='outer'
    ).fillna(0)
    
    # Calculate differences
    df_comparison['diff_trades'] = df_comparison['trades_h4h1'] - df_comparison['trades_h1']
    df_comparison['diff_wr'] = df_comparison['win_rate_h4h1'] - df_comparison['win_rate_h1']
    df_comparison['diff_return'] = df_comparison['return_pct_h4h1'] - df_comparison['return_pct_h1']
    
    # Print table
    print("\n" + "-"*120)
    print(f"{'Месяц':<10} | {'H1 Сделок':<10} {'H1 WR%':<10} {'H1 Return%':<12} | {'H4+H1 Сделок':<12} {'H4+H1 WR%':<12} {'H4+H1 Return%':<15} | {'Δ Return%':<12}")
    print("-"*120)
    
    total_h1_return = 0
    total_h4h1_return = 0
    
    for _, row in df_comparison.iterrows():
        month = row['month']
        
        h1_trades = int(row['trades_h1'])
        h1_wr = row['win_rate_h1']
        h1_ret = row['return_pct_h1']
        
        h4h1_trades = int(row['trades_h4h1'])
        h4h1_wr = row['win_rate_h4h1']
        h4h1_ret = row['return_pct_h4h1']
        
        diff_ret = row['diff_return']
        
        total_h1_return += h1_ret
        total_h4h1_return += h4h1_ret
        
        emoji = "✅" if diff_ret > 0 else "❌" if diff_ret < 0 else "="
        
        print(f"{month:<10} | {h1_trades:<10} {h1_wr:<10.1f} {h1_ret:>+11.2f}% | {h4h1_trades:<12} {h4h1_wr:<12.1f} {h4h1_ret:>+14.2f}% | {emoji} {diff_ret:>+10.2f}%")
    
    print("-"*120)
    print(f"{'ИТОГО':<10} | {'':<10} {'':<10} {total_h1_return:>+11.2f}% | {'':<12} {'':<12} {total_h4h1_return:>+14.2f}% | {'Δ':>2} {total_h4h1_return-total_h1_return:>+10.2f}%")
    print("="*80)
    
    # Summary
    print("\n📊 СВОДКА:")
    print(f"   H1 только: {total_h1_return:+.2f}%")
    print(f"   H4+H1: {total_h4h1_return:+.2f}%")
    print(f"   Улучшение: {total_h4h1_return - total_h1_return:+.2f}%")
    
    better_months = len(df_comparison[df_comparison['diff_return'] > 0])
    worse_months = len(df_comparison[df_comparison['diff_return'] < 0])
    same_months = len(df_comparison[df_comparison['diff_return'] == 0])
    
    print(f"\n   H4 фильтр лучше: {better_months} месяцев ✅")
    print(f"   H4 фильтр хуже: {worse_months} месяцев ❌")
    print(f"   Без разницы: {same_months} месяцев")
    
    # Create visualization
    print("\n📈 Создание графика...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Месячное сравнение: H1 vs H4+H1', fontsize=16, fontweight='bold')
    
    months = df_comparison['month'].tolist()
    
    # Plot 1: Monthly returns
    ax1 = axes[0, 0]
    x = np.arange(len(months))
    width = 0.35
    
    ax1.bar(x - width/2, df_comparison['return_pct_h1'], width, label='H1 только', alpha=0.7, color='blue')
    ax1.bar(x + width/2, df_comparison['return_pct_h4h1'], width, label='H4+H1', alpha=0.7, color='green')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax1.set_title('Месячная доходность', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Месяц')
    ax1.set_ylabel('Return (%)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(months, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Plot 2: Cumulative returns
    ax2 = axes[0, 1]
    cumulative_h1 = df_comparison['return_pct_h1'].cumsum()
    cumulative_h4h1 = df_comparison['return_pct_h4h1'].cumsum()
    
    ax2.plot(months, cumulative_h1, marker='o', label='H1 только', linewidth=2, color='blue')
    ax2.plot(months, cumulative_h4h1, marker='o', label='H4+H1', linewidth=2, color='green')
    ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax2.set_title('Кумулятивная доходность', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Месяц')
    ax2.set_ylabel('Cumulative Return (%)')
    ax2.tick_params(axis='x', rotation=45)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Win Rate comparison
    ax3 = axes[1, 0]
    ax3.bar(x - width/2, df_comparison['win_rate_h1'], width, label='H1 только', alpha=0.7, color='blue')
    ax3.bar(x + width/2, df_comparison['win_rate_h4h1'], width, label='H4+H1', alpha=0.7, color='green')
    ax3.axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='Breakeven')
    ax3.set_title('Win Rate по месяцам', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Месяц')
    ax3.set_ylabel('Win Rate (%)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(months, rotation=45, ha='right')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Plot 4: Trade count comparison
    ax4 = axes[1, 1]
    ax4.bar(x - width/2, df_comparison['trades_h1'], width, label='H1 только', alpha=0.7, color='blue')
    ax4.bar(x + width/2, df_comparison['trades_h4h1'], width, label='H4+H1', alpha=0.7, color='green')
    ax4.set_title('Количество сделок', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Месяц')
    ax4.set_ylabel('Сделок')
    ax4.set_xticks(x)
    ax4.set_xticklabels(months, rotation=45, ha='right')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('mtf_monthly_comparison_detailed.png', dpi=150, bbox_inches='tight')
    print("   ✅ График сохранен: mtf_monthly_comparison_detailed.png")
    
    # Save CSV
    df_comparison.to_csv('mtf_monthly_comparison.csv', index=False)
    print("   ✅ CSV сохранен: mtf_monthly_comparison.csv")
    
    print("\n✅ Анализ завершен!")


if __name__ == "__main__":
    main()
