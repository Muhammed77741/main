"""
Финальная оптимизация: LONG ONLY + дополнительные улучшения

Базовое улучшение: LONG ONLY = +386.02% (+37% над baseline)

Пробуем дополнительно:
1. Разные TP уровни (1.618, 2.0, 2.618)
2. Фильтр по времени (лучшие часы)
3. Фильтр по ATR (минимальная волатильность)
4. Комбинации
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pattern_recognition_strategy import PatternRecognitionStrategy


class LongOnlyOptimized(PatternRecognitionStrategy):
    """
    LONG ONLY + дополнительные фильтры
    """
    
    def __init__(self, 
                 fib_mode='standard',
                 tp_multiplier=1.618,
                 hour_filter=None,
                 min_atr_percentile=0):
        """
        tp_multiplier: 1.618, 2.0, 2.618 и т.д.
        hour_filter: список часов для торговли (None = все часы)
        min_atr_percentile: минимальный перцентиль ATR (0 = без фильтра)
        """
        super().__init__(fib_mode=fib_mode)
        self.tp_multiplier = tp_multiplier
        self.hour_filter = hour_filter
        self.min_atr_percentile = min_atr_percentile
        
        self.name = f"LONG ONLY (TP={tp_multiplier})"
        if hour_filter:
            self.name += f" Hours={hour_filter}"
        if min_atr_percentile > 0:
            self.name += f" ATR>{min_atr_percentile}%"
    
    def run_strategy(self, df):
        """Run optimized strategy"""
        
        # Run baseline
        df_strategy = super().run_strategy(df.copy())
        
        # Remove all SHORT
        df_strategy.loc[df_strategy['signal'] == -1, 'signal'] = 0
        df_strategy.loc[df_strategy['signal'] == 0, 'entry_price'] = np.nan
        df_strategy.loc[df_strategy['signal'] == 0, 'stop_loss'] = np.nan
        df_strategy.loc[df_strategy['signal'] == 0, 'take_profit'] = np.nan
        
        # Calculate ATR for filtering
        high_low = df_strategy['high'] - df_strategy['low']
        atr = high_low.rolling(window=14).mean()
        df_strategy['atr'] = atr
        
        # Apply filters
        if self.tp_multiplier != 1.618:
            df_strategy = self._adjust_tp(df_strategy)
        
        if self.hour_filter is not None:
            df_strategy = self._apply_hour_filter(df_strategy)
        
        if self.min_atr_percentile > 0:
            df_strategy = self._apply_atr_filter(df_strategy)
        
        return df_strategy
    
    def _adjust_tp(self, df):
        """Adjust TP based on multiplier"""
        for idx in df[df['signal'] == 1].index:
            entry_price = df.loc[idx, 'entry_price']
            stop_loss = df.loc[idx, 'stop_loss']
            
            sl_distance = abs(entry_price - stop_loss)
            new_tp = entry_price + (sl_distance * self.tp_multiplier)
            
            df.loc[idx, 'take_profit'] = new_tp
        
        return df
    
    def _apply_hour_filter(self, df):
        """Filter signals by hour"""
        filtered = 0
        
        for idx in df[df['signal'] == 1].index:
            hour = idx.hour
            
            if hour not in self.hour_filter:
                df.loc[idx, 'signal'] = 0
                df.loc[idx, 'entry_price'] = np.nan
                df.loc[idx, 'stop_loss'] = np.nan
                df.loc[idx, 'take_profit'] = np.nan
                filtered += 1
        
        return df
    
    def _apply_atr_filter(self, df):
        """Filter signals by ATR"""
        atr_threshold = df['atr'].quantile(self.min_atr_percentile / 100)
        filtered = 0
        
        for idx in df[df['signal'] == 1].index:
            if df.loc[idx, 'atr'] < atr_threshold:
                df.loc[idx, 'signal'] = 0
                df.loc[idx, 'entry_price'] = np.nan
                df.loc[idx, 'stop_loss'] = np.nan
                df.loc[idx, 'take_profit'] = np.nan
                filtered += 1
        
        return df


def simple_backtest(df, strategy, verbose=True):
    """Simple backtest"""
    
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    if verbose:
        print(f"   Signals: {len(df_signals)}")
    
    trades = []
    total_pnl = 0
    
    for i in range(len(df_signals)):
        signal = df_signals.iloc[i]
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        direction = signal['signal']
        
        entry_time = df_signals.index[i]
        search_end = entry_time + timedelta(hours=48)
        
        df_future = df_strategy[(df_strategy.index > entry_time) & (df_strategy.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Find exit
        exit_price = None
        exit_type = None
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            if direction == 1:  # LONG
                if candle['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif candle['high'] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'TIMEOUT'
        
        # Calculate PnL
        if direction == 1:
            pnl = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl = ((entry_price - exit_price) / entry_price) * 100
        
        total_pnl += pnl
        
        trades.append({
            'pnl': pnl,
            'exit_type': exit_type
        })
    
    wins = len([t for t in trades if t['pnl'] > 0])
    wr = wins / len(trades) * 100 if len(trades) > 0 else 0
    
    wins_pnl = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    losses_pnl = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    pf = wins_pnl / losses_pnl if losses_pnl > 0 else 0
    
    if verbose:
        print(f"   Trades: {len(trades)}")
        print(f"   Win Rate: {wr:.1f}%")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Profit Factor: {pf:.2f}")
    
    return {
        'signals': len(df_signals),
        'trades': len(trades),
        'win_rate': wr,
        'pnl': total_pnl,
        'pf': pf
    }


def test_configurations(df):
    """Тестируем разные конфигурации"""
    
    print("\n" + "="*100)
    print("ТЕСТИРОВАНИЕ РАЗЛИЧНЫХ КОНФИГУРАЦИЙ")
    print("="*100)
    
    results = []
    
    # 1. Baseline LONG ONLY
    print(f"\n{'='*100}")
    print("1️⃣  Baseline LONG ONLY (TP=1.618)")
    print(f"{'='*100}")
    
    strategy = LongOnlyOptimized(tp_multiplier=1.618)
    result = simple_backtest(df, strategy)
    result['config'] = 'LONG ONLY (1.618)'
    results.append(result)
    
    # 2. Different TP levels
    print(f"\n{'='*100}")
    print("2️⃣  TP Optimization")
    print(f"{'='*100}")
    
    for tp in [1.4, 1.6, 1.8, 2.0, 2.2, 2.618]:
        print(f"\n   Testing TP={tp}...")
        strategy = LongOnlyOptimized(tp_multiplier=tp)
        result = simple_backtest(df, strategy, verbose=False)
        result['config'] = f'TP={tp}'
        results.append(result)
        print(f"   → PnL: {result['pnl']:+.2f}%, WR: {result['win_rate']:.1f}%")
    
    # 3. Best hours filter
    print(f"\n{'='*100}")
    print("3️⃣  Hour Filter (лучшие часы по анализу)")
    print(f"{'='*100}")
    
    # Из анализа: лучшие часы 8, 9, 10
    best_hours = [8, 9, 10]
    print(f"\n   Testing hours: {best_hours}...")
    strategy = LongOnlyOptimized(tp_multiplier=1.618, hour_filter=best_hours)
    result = simple_backtest(df, strategy)
    result['config'] = f'Hours {best_hours}'
    results.append(result)
    
    # 4. ATR filter
    print(f"\n{'='*100}")
    print("4️⃣  ATR Filter (минимальная волатильность)")
    print(f"{'='*100}")
    
    for atr_pct in [25, 50]:
        print(f"\n   Testing ATR > {atr_pct}%...")
        strategy = LongOnlyOptimized(tp_multiplier=1.618, min_atr_percentile=atr_pct)
        result = simple_backtest(df, strategy)
        result['config'] = f'ATR>{atr_pct}%'
        results.append(result)
    
    # 5. Best combinations
    print(f"\n{'='*100}")
    print("5️⃣  Best Combinations")
    print(f"{'='*100}")
    
    # Best TP from step 2
    results_df = pd.DataFrame(results)
    tp_results = results_df[results_df['config'].str.startswith('TP=')]
    best_tp_row = tp_results.loc[tp_results['pnl'].idxmax()]
    best_tp = float(best_tp_row['config'].split('=')[1])
    
    print(f"\n   Best TP from testing: {best_tp}")
    
    # Combo 1: Best TP + Hours
    print(f"\n   Testing: TP={best_tp} + Hours...")
    strategy = LongOnlyOptimized(tp_multiplier=best_tp, hour_filter=best_hours)
    result = simple_backtest(df, strategy)
    result['config'] = f'TP={best_tp} + Hours'
    results.append(result)
    
    # Combo 2: Best TP + ATR
    print(f"\n   Testing: TP={best_tp} + ATR>25%...")
    strategy = LongOnlyOptimized(tp_multiplier=best_tp, min_atr_percentile=25)
    result = simple_backtest(df, strategy)
    result['config'] = f'TP={best_tp} + ATR>25%'
    results.append(result)
    
    # Summary
    print(f"\n{'='*100}")
    print("📊 ИТОГОВАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    print(f"{'='*100}\n")
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('pnl', ascending=False)
    
    print(f"{'Config':<30} {'Trades':<10} {'WR':<10} {'PnL':<15} {'PF':<10}")
    print("-" * 75)
    
    for _, row in results_df.iterrows():
        print(f"{row['config']:<30} {row['trades']:<10} {row['win_rate']:>8.1f}% {row['pnl']:>+13.2f}% {row['pf']:>9.2f}")
    
    # Best config
    best = results_df.iloc[0]
    baseline = results_df[results_df['config'] == 'LONG ONLY (1.618)'].iloc[0]
    
    print(f"\n{'='*100}")
    print(f"🏆 ЛУЧШАЯ КОНФИГУРАЦИЯ: {best['config']}")
    print(f"{'='*100}")
    print(f"   Trades: {best['trades']}")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Total PnL: {best['pnl']:+.2f}%")
    print(f"   Profit Factor: {best['pf']:.2f}")
    
    improvement = best['pnl'] - baseline['pnl']
    improvement_pct = (improvement / baseline['pnl']) * 100
    
    print(f"\n💰 Улучшение над LONG ONLY baseline:")
    print(f"   PnL: {improvement:+.2f}% ({improvement_pct:+.1f}%)")
    print(f"   Win Rate: {best['win_rate'] - baseline['win_rate']:+.1f}%")
    
    # vs Original baseline
    original_baseline_pnl = 349.02
    total_improvement = best['pnl'] - original_baseline_pnl
    total_improvement_pct = (total_improvement / original_baseline_pnl) * 100
    
    print(f"\n🎯 ИТОГОВОЕ УЛУЧШЕНИЕ НАД ОРИГИНАЛЬНЫМ BASELINE:")
    print(f"   Original Baseline: +{original_baseline_pnl:.2f}%")
    print(f"   Best Config: {best['pnl']:+.2f}%")
    print(f"   Improvement: {total_improvement:+.2f}% ({total_improvement_pct:+.1f}%)")
    
    print(f"{'='*100}\n")
    
    return results_df


def main():
    print("\n" + "="*100)
    print("ФИНАЛЬНАЯ ОПТИМИЗАЦИЯ СТРАТЕГИИ")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Test configurations
    results = test_configurations(df)
    
    # Save results
    results.to_csv('optimization_results.csv', index=False)
    print(f"\n💾 Results saved to: optimization_results.csv")
    
    return results


if __name__ == "__main__":
    results = main()
