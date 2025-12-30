"""
Multi-Timeframe Backtest for Pattern Recognition Strategy
Сравнение: H1 только vs H4+H1 (с фильтром по тренду)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from datetime import datetime

from pattern_recognition_strategy import PatternRecognitionStrategy
from multi_timeframe import MultiTimeframeData
from backtester import Backtester


class MultiTimeframeBacktest:
    """Бэктест с multi-timeframe анализом"""
    
    def __init__(self, htf_multiplier=4):
        """
        Args:
            htf_multiplier: Множитель для HTF (4 = H4 для H1)
        """
        self.htf_multiplier = htf_multiplier
        self.mtf = MultiTimeframeData(htf_multiplier=htf_multiplier)
        
    def detect_h4_trend(self, df_h4, lookback=20):
        """
        Определить тренд на H4
        
        Returns:
            'UP', 'DOWN', или 'SIDEWAYS'
        """
        if len(df_h4) < lookback:
            return 'SIDEWAYS'
        
        recent = df_h4.iloc[-lookback:]
        
        # EMA для тренда
        ema_fast = recent['close'].ewm(span=10, adjust=False).mean()
        ema_slow = recent['close'].ewm(span=20, adjust=False).mean()
        
        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]
        
        # Процентная разница
        diff_pct = ((current_fast - current_slow) / current_slow) * 100
        
        # Направление цены
        price_start = recent['close'].iloc[0]
        price_end = recent['close'].iloc[-1]
        price_change_pct = ((price_end - price_start) / price_start) * 100
        
        # Определение тренда
        if diff_pct > 0.2 and price_change_pct > 1.0:
            return 'UP'
        elif diff_pct < -0.2 and price_change_pct < -1.0:
            return 'DOWN'
        else:
            return 'SIDEWAYS'
    
    def filter_signals_by_h4(self, df_h1, df_h4):
        """
        Фильтровать H1 сигналы по H4 тренду
        
        Args:
            df_h1: DataFrame с H1 сигналами
            df_h4: DataFrame с H4 данными
            
        Returns:
            DataFrame с отфильтрованными сигналами
        """
        df_filtered = df_h1.copy()
        df_filtered['original_signal'] = df_filtered['signal'].copy()
        df_filtered['h4_trend'] = 'SIDEWAYS'
        df_filtered['signal_filtered'] = False
        
        # Для каждой H1 свечи определяем H4 тренд
        for idx in df_h1.index:
            # Найти соответствующую H4 свечу
            h4_candles = df_h4[df_h4.index <= idx]
            
            if len(h4_candles) >= 20:
                h4_trend = self.detect_h4_trend(h4_candles, lookback=20)
                df_filtered.loc[idx, 'h4_trend'] = h4_trend
                
                # Фильтрация сигнала
                h1_signal = df_h1.loc[idx, 'signal']
                
                if h1_signal == 1:  # LONG signal
                    if h4_trend == 'DOWN':
                        # Против тренда - отфильтровать
                        df_filtered.loc[idx, 'signal'] = 0
                        df_filtered.loc[idx, 'signal_filtered'] = True
                    # UP или SIDEWAYS - оставляем
                    
                elif h1_signal == -1:  # SHORT signal
                    if h4_trend == 'UP':
                        # Против тренда - отфильтровать
                        df_filtered.loc[idx, 'signal'] = 0
                        df_filtered.loc[idx, 'signal_filtered'] = True
                    # DOWN или SIDEWAYS - оставляем
        
        return df_filtered
    
    def run_comparison(self, df_h1, strategy):
        """
        Запустить сравнение: H1 только vs H4+H1
        
        Args:
            df_h1: DataFrame с H1 данными
            strategy: PatternRecognitionStrategy instance
            
        Returns:
            dict с результатами обоих бэктестов
        """
        print("\n" + "="*80)
        print("🔍 MULTI-TIMEFRAME BACKTEST COMPARISON")
        print("="*80)
        print(f"Период: {df_h1.index[0]} → {df_h1.index[-1]}")
        print(f"Свечей H1: {len(df_h1)}")
        print(f"HTF multiplier: {self.htf_multiplier} (H{self.htf_multiplier})")
        
        # 1. Создать H4 из H1
        print(f"\n📊 Создание H4 данных из H1...")
        df_h4 = self.mtf.resample_to_htf(df_h1)
        print(f"   ✅ Создано {len(df_h4)} H4 свечей")
        
        # 2. Запустить стратегию на H1
        print(f"\n🎯 Запуск стратегии на H1...")
        df_h1_with_signals = strategy.run_strategy(df_h1.copy())
        h1_signals = df_h1_with_signals[df_h1_with_signals['signal'] != 0]
        print(f"   ✅ Найдено {len(h1_signals)} сигналов на H1")
        
        # 3. Бэктест #1: Только H1 (без фильтра)
        print(f"\n📈 BACKTEST #1: H1 только (без H4 фильтра)")
        print("-" * 80)
        backtester_h1 = Backtester(initial_capital=10000)
        stats_h1 = backtester_h1.run(df_h1_with_signals)
        backtester_h1.print_results(stats_h1)
        
        # 4. Фильтровать сигналы по H4
        print(f"\n🔍 Фильтрация H1 сигналов по H4 тренду...")
        df_h1_filtered = self.filter_signals_by_h4(df_h1_with_signals, df_h4)
        
        # Статистика фильтрации
        filtered_count = df_h1_filtered['signal_filtered'].sum()
        filtered_long = df_h1_filtered[(df_h1_filtered['original_signal'] == 1) & (df_h1_filtered['signal_filtered'])].shape[0]
        filtered_short = df_h1_filtered[(df_h1_filtered['original_signal'] == -1) & (df_h1_filtered['signal_filtered'])].shape[0]
        
        print(f"   📊 Отфильтровано сигналов: {filtered_count}")
        print(f"      LONG: {filtered_long}")
        print(f"      SHORT: {filtered_short}")
        print(f"   ✅ Осталось сигналов: {len(df_h1_filtered[df_h1_filtered['signal'] != 0])}")
        
        # 5. Бэктест #2: H4 + H1 (с фильтром)
        print(f"\n📈 BACKTEST #2: H4 + H1 (с H4 фильтром тренда)")
        print("-" * 80)
        backtester_mtf = Backtester(initial_capital=10000)
        stats_mtf = backtester_mtf.run(df_h1_filtered)
        backtester_mtf.print_results(stats_mtf)
        
        # 6. Сравнение
        print(f"\n" + "="*80)
        print("📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
        print("="*80)
        
        comparison = {
            'Metric': [
                'Total Trades',
                'Win Rate %',
                'Total Return %',
                'Profit Factor',
                'Sharpe Ratio',
                'Max Drawdown %',
                'Avg Win %',
                'Avg Loss %',
                'Filtered Signals'
            ],
            'H1 Only': [
                stats_h1['total_trades'],
                f"{stats_h1.get('win_rate', 0):.2f}",
                f"{stats_h1.get('total_return_pct', 0):.2f}",
                f"{stats_h1.get('profit_factor', 0):.2f}",
                f"{stats_h1.get('sharpe_ratio', 0):.2f}",
                f"{stats_h1.get('max_drawdown', 0):.2f}",
                f"{stats_h1.get('avg_win', 0):.2f}",
                f"{stats_h1.get('avg_loss', 0):.2f}",
                "0"
            ],
            'H4+H1 (MTF)': [
                stats_mtf['total_trades'],
                f"{stats_mtf.get('win_rate', 0):.2f}",
                f"{stats_mtf.get('total_return_pct', 0):.2f}",
                f"{stats_mtf.get('profit_factor', 0):.2f}",
                f"{stats_mtf.get('sharpe_ratio', 0):.2f}",
                f"{stats_mtf.get('max_drawdown', 0):.2f}",
                f"{stats_mtf.get('avg_win', 0):.2f}",
                f"{stats_mtf.get('avg_loss', 0):.2f}",
                str(filtered_count)
            ],
            'Change': []
        }
        
        # Рассчитать изменения
        metrics_for_calc = [
            ('total_trades', 'abs'),
            ('win_rate', 'pct'),
            ('total_return_pct', 'abs'),
            ('profit_factor', 'abs'),
            ('sharpe_ratio', 'abs'),
            ('max_drawdown', 'abs'),
            ('avg_win', 'abs'),
            ('avg_loss', 'abs')
        ]
        
        for metric, calc_type in metrics_for_calc:
            h1_val = stats_h1.get(metric, 0)
            mtf_val = stats_mtf.get(metric, 0)
            
            if calc_type == 'abs':
                change = mtf_val - h1_val
                comparison['Change'].append(f"{change:+.2f}")
            elif calc_type == 'pct':
                if h1_val != 0:
                    change_pct = ((mtf_val - h1_val) / h1_val) * 100
                    comparison['Change'].append(f"{change_pct:+.1f}%")
                else:
                    comparison['Change'].append("N/A")
        
        comparison['Change'].append(f"-{filtered_count}")
        
        df_comparison = pd.DataFrame(comparison)
        print("\n" + df_comparison.to_string(index=False))
        
        # Выводы
        print(f"\n" + "="*80)
        print("🎯 ВЫВОДЫ")
        print("="*80)
        
        wr_improvement = stats_mtf.get('win_rate', 0) - stats_h1.get('win_rate', 0)
        ret_improvement = stats_mtf.get('total_return_pct', 0) - stats_h1.get('total_return_pct', 0)
        
        print(f"\n✅ H4 фильтр:")
        print(f"   • Отфильтровал {filtered_count} сигналов против тренда")
        print(f"   • Win Rate: {stats_h1.get('win_rate', 0):.1f}% → {stats_mtf.get('win_rate', 0):.1f}% ({wr_improvement:+.1f}%)")
        print(f"   • Return: {stats_h1.get('total_return_pct', 0):.1f}% → {stats_mtf.get('total_return_pct', 0):.1f}% ({ret_improvement:+.1f}%)")
        print(f"   • Trades: {stats_h1['total_trades']} → {stats_mtf['total_trades']} ({stats_mtf['total_trades'] - stats_h1['total_trades']})")
        
        if wr_improvement > 0:
            print(f"\n💡 H4 фильтр УЛУЧШИЛ результаты! ✅")
        elif wr_improvement < -2:
            print(f"\n⚠️  H4 фильтр УХУДШИЛ результаты")
        else:
            print(f"\n📊 H4 фильтр дал смешанные результаты")
        
        # Рекомендации
        print(f"\n📌 РЕКОМЕНДАЦИИ:")
        if stats_h1['total_trades'] == 0 and stats_mtf['total_trades'] == 0:
            print(f"   ⚠️  Нет сделок! Причины:")
            print(f"      • Слишком строгие фильтры стратегии")
            print(f"      • Недостаточно данных или низкая волатильность")
            print(f"      • Попробуйте загрузить реальные MT5 данные")
        elif stats_h1['total_trades'] < 20:
            print(f"   ⚠️  Мало сделок ({stats_h1['total_trades']}). Попробуйте:")
            print(f"      • Увеличить период тестирования")
            print(f"      • Использовать H2 вместо H4 (htf_multiplier=2)")
            print(f"      • Загрузить реальные MT5 данные")
        elif stats_mtf.get('win_rate', 0) > stats_h1.get('win_rate', 0) and stats_mtf.get('profit_factor', 0) > stats_h1.get('profit_factor', 0):
            print(f"   ✅ Используйте H4+H1 (MTF) - стабильнее и прибыльнее!")
        elif stats_mtf.get('total_return_pct', 0) > stats_h1.get('total_return_pct', 0) * 1.1:
            print(f"   ✅ Используйте H4+H1 (MTF) - значительно выше доходность!")
        else:
            print(f"   📊 H1 без фильтра дает больше сделок, но H4+H1 стабильнее")
        
        return {
            'h1_only': stats_h1,
            'h4_h1': stats_mtf,
            'df_h1': df_h1_with_signals,
            'df_h1_filtered': df_h1_filtered,
            'df_h4': df_h4,
            'comparison': df_comparison
        }


def plot_comparison(results):
    """Построить графики сравнения"""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Multi-Timeframe Backtest Comparison: H1 vs H4+H1', fontsize=16, fontweight='bold')
    
    # 1. Equity curves
    ax1 = axes[0, 0]
    
    # H1 только
    trades_h1 = results['h1_only']['trades']
    capital_h1 = [10000]
    for trade in trades_h1:
        capital_h1.append(capital_h1[-1] + trade['pnl'])
    
    # H4+H1
    trades_mtf = results['h4_h1']['trades']
    capital_mtf = [10000]
    for trade in trades_mtf:
        capital_mtf.append(capital_mtf[-1] + trade['pnl'])
    
    ax1.plot(capital_h1, label='H1 Only', linewidth=2, color='blue', alpha=0.7)
    ax1.plot(capital_mtf, label='H4+H1 (MTF)', linewidth=2, color='green', alpha=0.7)
    ax1.axhline(y=10000, color='gray', linestyle='--', alpha=0.5)
    ax1.set_title('Equity Curves', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Trade Number')
    ax1.set_ylabel('Equity ($)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Win Rate & Profit Factor
    ax2 = axes[0, 1]
    
    metrics = ['Win Rate\n(%)', 'Profit\nFactor']
    h1_vals = [results['h1_only']['win_rate'], results['h1_only']['profit_factor']]
    mtf_vals = [results['h4_h1']['win_rate'], results['h4_h1']['profit_factor']]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax2.bar(x - width/2, h1_vals, width, label='H1 Only', color='blue', alpha=0.7)
    ax2.bar(x + width/2, mtf_vals, width, label='H4+H1', color='green', alpha=0.7)
    ax2.set_title('Key Metrics Comparison', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics)
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 3. Price with signals (H1 only)
    ax3 = axes[1, 0]
    df_h1 = results['df_h1']
    
    ax3.plot(df_h1.index, df_h1['close'], label='Price', color='black', linewidth=0.8, alpha=0.6)
    
    long_signals = df_h1[df_h1['signal'] == 1]
    short_signals = df_h1[df_h1['signal'] == -1]
    
    ax3.scatter(long_signals.index, long_signals['close'], color='green', marker='^', s=100, label='LONG', zorder=5, alpha=0.7)
    ax3.scatter(short_signals.index, short_signals['close'], color='red', marker='v', s=100, label='SHORT', zorder=5, alpha=0.7)
    
    ax3.set_title('H1 Signals (No Filter)', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Price')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Price with filtered signals (H4+H1)
    ax4 = axes[1, 1]
    df_filtered = results['df_h1_filtered']
    
    ax4.plot(df_filtered.index, df_filtered['close'], label='Price', color='black', linewidth=0.8, alpha=0.6)
    
    long_signals_f = df_filtered[df_filtered['signal'] == 1]
    short_signals_f = df_filtered[df_filtered['signal'] == -1]
    filtered_signals = df_filtered[df_filtered['signal_filtered'] == True]
    
    ax4.scatter(long_signals_f.index, long_signals_f['close'], color='green', marker='^', s=100, label='LONG (passed)', zorder=5, alpha=0.7)
    ax4.scatter(short_signals_f.index, short_signals_f['close'], color='red', marker='v', s=100, label='SHORT (passed)', zorder=5, alpha=0.7)
    ax4.scatter(filtered_signals.index, filtered_signals['close'], color='gray', marker='x', s=80, label='Filtered', zorder=4, alpha=0.5)
    
    ax4.set_title('H4+H1 Signals (With Filter)', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Date')
    ax4.set_ylabel('Price')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('multi_timeframe_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 График сохранен: multi_timeframe_comparison.png")


def main():
    """Main execution"""
    
    print("\n" + "="*80)
    print("🚀 MULTI-TIMEFRAME BACKTEST")
    print("="*80)
    print("\nСравнение:")
    print("  1️⃣  H1 только (без фильтра)")
    print("  2️⃣  H4 + H1 (с фильтром по тренду)")
    print("\nФильтр: Отклоняет сигналы против H4 тренда")
    print("="*80)
    
    # Загрузить реальные данные
    print("\n📥 Загрузка данных...")
    
    try:
        # Попытка загрузить реальные MT5 данные
        from mt5_data_downloader import MT5DataDownloader
        import MetaTrader5 as mt5
        
        downloader = MT5DataDownloader(symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1)
        
        if downloader.connect():
            print("   ✅ MT5 подключен")
            df_h1 = downloader.get_realtime_data(period_hours=2000)  # ~3 месяца
            downloader.disconnect()
            
            if df_h1 is not None and len(df_h1) > 200:
                print(f"   ✅ Загружено {len(df_h1)} H1 свечей XAUUSD")
            else:
                raise Exception("Недостаточно данных")
        else:
            raise Exception("MT5 не подключен")
            
    except Exception as e:
        print(f"   ⚠️  MT5 недоступен: {e}")
        print("   📊 Генерация тестовых данных...")
        
        # Генерация тестовых данных
        from data_loader import generate_sample_data
        df_h1 = generate_sample_data(days=365, start_price=2650, volatility=0.015)
        print(f"   ✅ Сгенерировано {len(df_h1)} тестовых свечей (~{len(df_h1)/24:.0f} дней)")
    
    # Инициализация стратегии
    print("\n🎯 Инициализация стратегии...")
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    print("   ✅ Pattern Recognition Strategy готова")
    
    # Запуск бэктеста
    mtf_backtest = MultiTimeframeBacktest(htf_multiplier=4)  # H4 для H1
    results = mtf_backtest.run_comparison(df_h1, strategy)
    
    # Построение графиков
    if results['h1_only']['total_trades'] > 0:
        print("\n📈 Построение графиков...")
        plot_comparison(results)
    
    # Сохранение результатов
    print("\n💾 Сохранение результатов...")
    
    if results['h1_only']['total_trades'] > 0:
        df_trades_h1 = pd.DataFrame(results['h1_only']['trades'])
        df_trades_h1.to_csv('mtf_trades_h1_only.csv', index=False)
        print("   ✅ H1 сделки: mtf_trades_h1_only.csv")
    
    if results['h4_h1']['total_trades'] > 0:
        df_trades_mtf = pd.DataFrame(results['h4_h1']['trades'])
        df_trades_mtf.to_csv('mtf_trades_h4h1.csv', index=False)
        print("   ✅ H4+H1 сделки: mtf_trades_h4h1.csv")
    
    results['comparison'].to_csv('mtf_comparison.csv', index=False)
    print("   ✅ Сравнение: mtf_comparison.csv")
    
    print("\n✅ Бэктест завершен!")
    print("="*80)


if __name__ == "__main__":
    main()
