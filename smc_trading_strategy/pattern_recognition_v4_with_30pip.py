"""
Pattern Recognition Strategy V4 - With 30-Pip Patterns

Комбинирует:
1. Baseline Optimized V2 (LONG ONLY + TP=1.4)
2. 30-Pip Pattern Detector (HIGH confidence only)

Expected Performance:
- Baseline V2: +386.92%
- 30-Pip Patterns: +4,429 pips (~+44% дополнительно)
- Combined: ~+520% (теоретически)
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2
from detect_30pip_patterns import ThirtyPipMoveDetector


class PatternRecognitionV4With30Pip:
    """
    Комбинированная стратегия V4
    
    = Baseline V2 + 30-Pip Patterns (HIGH confidence)
    """
    
    def __init__(self, 
                 fib_mode='standard',
                 tp_multiplier=1.4,
                 enable_30pip_patterns=True,
                 high_confidence_only=True):
        """
        Args:
            fib_mode: Fibonacci mode
            tp_multiplier: TP multiplier for baseline
            enable_30pip_patterns: Enable 30-pip pattern detection
            high_confidence_only: Use only HIGH confidence 30-pip patterns
        """
        
        # Baseline strategy
        self.baseline_strategy = PatternRecognitionOptimizedV2(
            fib_mode=fib_mode,
            tp_multiplier=tp_multiplier,
            long_only=True
        )
        
        # 30-Pip detector
        self.enable_30pip_patterns = enable_30pip_patterns
        self.high_confidence_only = high_confidence_only
        
        if enable_30pip_patterns:
            self.pip_detector = ThirtyPipMoveDetector(focus_long_only=True)
        else:
            self.pip_detector = None
        
        self.version = "4.0 (With 30-Pip Patterns)"
        
        print(f"\n🚀 Pattern Recognition Strategy V4")
        print(f"   Version: {self.version}")
        print(f"   Components:")
        print(f"      ✅ Baseline Optimized V2 (LONG ONLY + TP={tp_multiplier})")
        if enable_30pip_patterns:
            conf_filter = "HIGH confidence only" if high_confidence_only else "All confidence"
            print(f"      ✅ 30-Pip Patterns ({conf_filter})")
            print(f"         Expected: +4,429 pips from 149 signals")
        
        print(f"\n   📊 Expected Performance:")
        print(f"      - Baseline V2:        ~+387%")
        print(f"      - 30-Pip Patterns:    ~+44% additional")
        print(f"      - Combined:           ~+520-550%")
    
    def run_strategy(self, df):
        """
        Запускаем комбинированную стратегию
        """
        
        print(f"\n🔄 Running Combined Strategy V4...")
        
        # 1. Baseline signals
        print(f"\n1️⃣  Baseline Optimized V2...")
        df_baseline = self.baseline_strategy.run_strategy(df.copy())
        baseline_signals = df_baseline[df_baseline['signal'] != 0].copy()
        
        print(f"   Baseline signals: {len(baseline_signals)}")
        
        # 2. 30-Pip patterns
        pip_signals = pd.DataFrame()
        if self.enable_30pip_patterns and self.pip_detector is not None:
            print(f"\n2️⃣  30-Pip Pattern Detector...")
            pip_signals = self.pip_detector.detect_all_patterns(df.copy())
            
            # Filter HIGH confidence if needed
            if self.high_confidence_only and len(pip_signals) > 0:
                pip_signals = pip_signals[pip_signals['confidence'] == 'HIGH'].copy()
                print(f"   Filtered to HIGH confidence: {len(pip_signals)}")
        
        # 3. Combine signals
        print(f"\n3️⃣  Combining signals...")
        
        combined_signals = []
        
        # Add baseline signals
        for idx in baseline_signals.index:
            signal = baseline_signals.loc[idx]
            combined_signals.append({
                'time': idx,
                'source': 'BASELINE',
                'pattern': 'Pattern Recognition V2',
                'entry_price': signal['entry_price'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'confidence': 'HIGH',
                'type': 'BASELINE'
            })
        
        # Add 30-pip patterns
        if len(pip_signals) > 0:
            for _, signal in pip_signals.iterrows():
                combined_signals.append({
                    'time': signal['time'],
                    'source': '30PIP',
                    'pattern': signal['pattern'],
                    'entry_price': signal['entry_price'],
                    'stop_loss': signal['stop_loss'],
                    'take_profit': signal['take_profit'],
                    'confidence': signal['confidence'],
                    'type': signal['type']
                })
        
        combined_df = pd.DataFrame(combined_signals)
        
        if len(combined_df) > 0:
            combined_df = combined_df.sort_values('time')
            
            # Remove duplicates (signals within 1 hour)
            combined_df['time_group'] = combined_df['time'].dt.floor('1H')
            
            # Keep first signal in each hour (priority: BASELINE > 30PIP)
            combined_df['priority'] = combined_df['source'].map({'BASELINE': 1, '30PIP': 2})
            combined_df = combined_df.sort_values(['time_group', 'priority'])
            combined_df = combined_df.drop_duplicates(subset=['time_group'], keep='first')
            combined_df = combined_df.drop(['time_group', 'priority'], axis=1)
            combined_df = combined_df.sort_values('time')
        
        print(f"\n✅ Combined Strategy Complete:")
        print(f"   Total unique signals: {len(combined_df)}")
        if len(combined_df) > 0:
            print(f"   Baseline: {len(combined_df[combined_df['source'] == 'BASELINE'])}")
            print(f"   30-Pip:   {len(combined_df[combined_df['source'] == '30PIP'])}")
        
        return combined_df
    
    def get_stats(self):
        """Get strategy statistics"""
        return {
            'version': self.version,
            'baseline_expected_pnl_pct': 386.92,
            'pip_patterns_expected_pips': 4429,
            'combined_expected_pnl_pct': 520
        }


def backtest_combined_v4(df, strategy):
    """
    Полный бэктест комбинированной стратегии V4
    """
    
    print(f"\n🔍 Running full backtest...")
    
    # Get signals
    signals_df = strategy.run_strategy(df.copy())
    
    if len(signals_df) == 0:
        print("No signals!")
        return pd.DataFrame()
    
    # Backtest
    trades = []
    
    for idx, signal in signals_df.iterrows():
        entry_time = signal['time']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        # Look forward
        search_end = entry_time + timedelta(hours=48)
        df_future = df[(df.index > entry_time) & (df.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        # Find exit
        exit_price = None
        exit_type = None
        max_profit_pips = 0
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
            # Track max profit
            current_profit_dollars = candle['high'] - entry_price
            current_profit_pips = current_profit_dollars / 0.10
            max_profit_pips = max(max_profit_pips, current_profit_pips)
            
            # Check SL
            if candle['low'] <= stop_loss:
                exit_price = stop_loss
                exit_type = 'SL'
                break
            
            # Check TP
            if candle['high'] >= take_profit:
                exit_price = take_profit
                exit_type = 'TP'
                break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
            exit_type = 'TIMEOUT'
        
        # Calculate PnL
        pnl_dollars = exit_price - entry_price
        pnl_pips = pnl_dollars / 0.10
        pnl_pct = (pnl_dollars / entry_price) * 100
        
        trades.append({
            'entry_time': entry_time,
            'source': signal['source'],
            'pattern': signal['pattern'],
            'type': signal.get('type', 'BASELINE'),
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pips': pnl_pips,
            'pnl_pct': pnl_pct,
            'max_profit_pips': max_profit_pips,
            'reached_30pips': max_profit_pips >= 30
        })
    
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    print(f"\n✅ Backtest Results:")
    print(f"   {'='*80}")
    print(f"   Total Trades:      {len(trades_df)}")
    
    if len(trades_df) > 0:
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        win_rate = wins / len(trades_df) * 100
        
        total_pnl_pct = trades_df['pnl_pct'].sum()
        avg_pnl_pct = trades_df['pnl_pct'].mean()
        
        total_pnl_pips = trades_df['pnl_pips'].sum()
        avg_pnl_pips = trades_df['pnl_pips'].mean()
        
        wins_pnl = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].sum()
        losses_pnl = abs(trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].sum())
        profit_factor = wins_pnl / losses_pnl if losses_pnl > 0 else 0
        
        reached_30 = len(trades_df[trades_df['reached_30pips'] == True])
        
        print(f"   Win Rate:          {win_rate:.1f}%")
        print(f"   Total PnL:         {total_pnl_pct:+.2f}%")
        print(f"   Avg PnL:           {avg_pnl_pct:+.2f}%")
        print(f"   Total PnL (pips):  {total_pnl_pips:+.0f}")
        print(f"   Avg PnL (pips):    {avg_pnl_pips:+.1f}")
        print(f"   Profit Factor:     {profit_factor:.2f}")
        print(f"   Reached 30+ pips:  {reached_30} ({reached_30/len(trades_df)*100:.1f}%)")
        print(f"   {'='*80}")
        
        # By source
        print(f"\n   By Source:")
        for source in ['BASELINE', '30PIP']:
            source_trades = trades_df[trades_df['source'] == source]
            if len(source_trades) > 0:
                source_wr = len(source_trades[source_trades['pnl_pct'] > 0]) / len(source_trades) * 100
                source_pnl_pct = source_trades['pnl_pct'].sum()
                source_pnl_pips = source_trades['pnl_pips'].sum()
                source_avg_pips = source_trades['pnl_pips'].mean()
                
                print(f"      {source:12s}: {len(source_trades):3d} trades | "
                      f"WR {source_wr:5.1f}% | "
                      f"PnL {source_pnl_pct:+7.2f}% | "
                      f"{source_pnl_pips:+6.0f}p | "
                      f"Avg {source_avg_pips:+6.1f}p")
        
        # Top 30-pip patterns
        pip_trades = trades_df[trades_df['source'] == '30PIP']
        if len(pip_trades) > 0:
            print(f"\n   30-Pip Patterns by Type:")
            for pattern_type in pip_trades['type'].unique():
                type_trades = pip_trades[pip_trades['type'] == pattern_type]
                type_wr = len(type_trades[type_trades['pnl_pct'] > 0]) / len(type_trades) * 100
                type_pnl_pips = type_trades['pnl_pips'].sum()
                type_avg_pips = type_trades['pnl_pips'].mean()
                
                print(f"      {pattern_type:15s}: {len(type_trades):3d} trades | "
                      f"WR {type_wr:5.1f}% | "
                      f"Total {type_pnl_pips:+6.0f}p | "
                      f"Avg {type_avg_pips:+6.1f}p")
    
    return trades_df


def compare_all_versions(df):
    """
    Сравнение всех версий стратегии
    """
    
    print(f"\n" + "="*100)
    print("СРАВНЕНИЕ ВСЕХ ВЕРСИЙ СТРАТЕГИИ")
    print("="*100)
    
    results = []
    
    # V2 Optimized (baseline)
    print(f"\n1️⃣  V2 OPTIMIZED (Baseline):")
    v2_strategy = PatternRecognitionOptimizedV2(
        fib_mode='standard',
        tp_multiplier=1.4,
        long_only=True
    )
    
    df_v2 = v2_strategy.run_strategy(df.copy())
    v2_signals = df_v2[df_v2['signal'] != 0].copy()
    
    # Quick backtest V2
    v2_trades = []
    for idx in v2_signals.index:
        signal = v2_signals.loc[idx]
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        entry_time = idx
        
        search_end = entry_time + timedelta(hours=48)
        df_future = df_v2[(df_v2.index > entry_time) & (df_v2.index <= search_end)]
        
        if len(df_future) == 0:
            continue
        
        exit_price = None
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            if candle['low'] <= stop_loss:
                exit_price = stop_loss
                break
            elif candle['high'] >= take_profit:
                exit_price = take_profit
                break
        
        if exit_price is None:
            exit_price = df_future['close'].iloc[-1]
        
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        v2_trades.append({'pnl_pct': pnl_pct})
    
    v2_trades_df = pd.DataFrame(v2_trades)
    
    if len(v2_trades_df) > 0:
        v2_wr = len(v2_trades_df[v2_trades_df['pnl_pct'] > 0]) / len(v2_trades_df) * 100
        v2_pnl = v2_trades_df['pnl_pct'].sum()
        v2_avg = v2_trades_df['pnl_pct'].mean()
        
        results.append({
            'version': 'V2 Optimized',
            'trades': len(v2_trades_df),
            'win_rate': v2_wr,
            'total_pnl': v2_pnl,
            'avg_pnl': v2_avg
        })
        
        print(f"   Trades: {len(v2_trades_df)} | WR: {v2_wr:.1f}% | PnL: {v2_pnl:+.2f}%")
    
    # V4 With 30-Pip
    print(f"\n2️⃣  V4 WITH 30-PIP PATTERNS:")
    v4_strategy = PatternRecognitionV4With30Pip(
        fib_mode='standard',
        tp_multiplier=1.4,
        enable_30pip_patterns=True,
        high_confidence_only=True
    )
    
    v4_trades_df = backtest_combined_v4(df, v4_strategy)
    
    if len(v4_trades_df) > 0:
        v4_wr = len(v4_trades_df[v4_trades_df['pnl_pct'] > 0]) / len(v4_trades_df) * 100
        v4_pnl = v4_trades_df['pnl_pct'].sum()
        v4_avg = v4_trades_df['pnl_pct'].mean()
        
        results.append({
            'version': 'V4 With 30-Pip',
            'trades': len(v4_trades_df),
            'win_rate': v4_wr,
            'total_pnl': v4_pnl,
            'avg_pnl': v4_avg
        })
    
    # Compare
    print(f"\n" + "="*100)
    print("📊 FINAL COMPARISON")
    print("="*100)
    
    if len(results) > 0:
        results_df = pd.DataFrame(results)
        
        print(f"\n{'Version':<25} {'Trades':<10} {'Win Rate':<12} {'Total PnL':<15} {'Avg PnL':<12}")
        print("-"*75)
        
        for _, row in results_df.iterrows():
            print(f"{row['version']:<25} {row['trades']:<10} {row['win_rate']:>10.1f}% "
                  f"{row['total_pnl']:>+13.2f}% {row['avg_pnl']:>+10.2f}%")
        
        # Calculate improvement
        if len(results_df) == 2:
            baseline = results_df[results_df['version'] == 'V2 Optimized'].iloc[0]
            improved = results_df[results_df['version'] == 'V4 With 30-Pip'].iloc[0]
            
            improvement = improved['total_pnl'] - baseline['total_pnl']
            improvement_pct = (improvement / baseline['total_pnl']) * 100
            
            print(f"\n💰 Improvement (V4 over V2):")
            print(f"   Additional Trades: {improved['trades'] - baseline['trades']:+}")
            print(f"   Win Rate:          {improved['win_rate'] - baseline['win_rate']:+.1f}%")
            print(f"   Total PnL:         {improvement:+.2f}% ({improvement_pct:+.1f}%)")
            print(f"   Avg PnL:           {improved['avg_pnl'] - baseline['avg_pnl']:+.2f}%")
            
            if improvement > 0:
                print(f"\n✅ V4 улучшает результаты на {improvement:+.2f}%!")
            else:
                print(f"\n⚠️ V4 не улучшает результаты ({improvement:.2f}%)")
    
    print("="*100)
    
    return results_df, v2_trades_df, v4_trades_df


def main():
    """Example usage"""
    
    print("\n" + "="*100)
    print("PATTERN RECOGNITION STRATEGY V4 - WITH 30-PIP PATTERNS")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Compare all versions
    results_df, v2_trades, v4_trades = compare_all_versions(df)
    
    # Save results
    if len(v4_trades) > 0:
        v4_trades.to_csv('strategy_v4_with_30pip_results.csv', index=False)
        print(f"\n💾 V4 results saved: strategy_v4_with_30pip_results.csv")
    
    return results_df, v2_trades, v4_trades


if __name__ == "__main__":
    results_df, v2_trades, v4_trades = main()
