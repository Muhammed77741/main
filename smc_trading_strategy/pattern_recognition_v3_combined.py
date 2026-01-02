"""
Pattern Recognition Strategy V3 - Combined

Комбинирует:
1. Baseline Optimized V2 (LONG ONLY + TP=1.4)
2. Profitable Missed Patterns (CONTINUATION + BREAKOUT only)

Expected Performance:
- Baseline: +386.92%
- Additional Patterns: +103% (continuation + breakout)
- Combined: +489.70% (+26.6% improvement)
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2
from missed_patterns_detector import MissedPatternsDetector


class PatternRecognitionV3Combined:
    """
    Комбинированная стратегия V3
    
    = Baseline Optimized V2 + Profitable Missed Patterns
    """
    
    def __init__(self, 
                 fib_mode='standard',
                 tp_multiplier=1.4,
                 enable_missed_patterns=True,
                 enable_continuation=True,
                 enable_breakout=True):
        """
        Args:
            fib_mode: Fibonacci mode
            tp_multiplier: TP multiplier for baseline
            enable_missed_patterns: Enable additional patterns detection
            enable_continuation: Enable continuation patterns (profitable)
            enable_breakout: Enable breakout patterns (profitable)
        """
        
        # Baseline strategy
        self.baseline_strategy = PatternRecognitionOptimizedV2(
            fib_mode=fib_mode,
            tp_multiplier=tp_multiplier,
            long_only=True
        )
        
        # Missed patterns detector (only profitable patterns)
        self.enable_missed_patterns = enable_missed_patterns
        if enable_missed_patterns:
            self.patterns_detector = MissedPatternsDetector(
                enable_continuation=enable_continuation,
                enable_oversold_bounce=False,  # NOT profitable
                enable_rsi_pullback=False,     # NOT profitable
                enable_volume_breakout=enable_breakout
            )
        else:
            self.patterns_detector = None
        
        self.version = "3.0 (Combined)"
        
        print(f"\n🚀 Pattern Recognition Strategy V3 (Combined)")
        print(f"   Version: {self.version}")
        print(f"   Components:")
        print(f"      ✅ Baseline Optimized V2 (LONG ONLY + TP={tp_multiplier})")
        if enable_missed_patterns:
            print(f"      ✅ Additional Patterns:")
            if enable_continuation:
                print(f"         • Continuation (49% WR, +97.90% PnL)")
            if enable_breakout:
                print(f"         • Breakout (51% WR, +5.25% PnL)")
        
        print(f"\n   📊 Expected Performance:")
        print(f"      - Baseline alone:     ~+387% PnL")
        print(f"      - With patterns:      ~+490% PnL")
        print(f"      - Improvement:        ~+26.6%")
    
    def run_strategy(self, df):
        """
        Запускаем комбинированную стратегию
        
        Returns:
            DataFrame с сигналами обеих стратегий
        """
        
        print(f"\n🔄 Running Combined Strategy...")
        
        # 1. Baseline signals
        print(f"\n1️⃣  Baseline Optimized V2...")
        df_baseline = self.baseline_strategy.run_strategy(df.copy())
        baseline_signals = df_baseline[df_baseline['signal'] != 0].copy()
        
        print(f"   Baseline signals: {len(baseline_signals)}")
        
        # 2. Additional patterns
        additional_signals = pd.DataFrame()
        if self.enable_missed_patterns and self.patterns_detector is not None:
            print(f"\n2️⃣  Additional Patterns...")
            additional_signals = self.patterns_detector.detect_all_patterns(df.copy())
            
            if len(additional_signals) > 0:
                print(f"   Additional signals: {len(additional_signals)}")
        
        # 3. Combine signals
        print(f"\n3️⃣  Combining signals...")
        
        # Create unified signal dataframe
        combined_signals = []
        
        # Add baseline signals
        for idx in baseline_signals.index:
            signal = baseline_signals.loc[idx]
            combined_signals.append({
                'time': idx,
                'source': 'BASELINE',
                'pattern': 'Pattern Recognition',
                'entry_price': signal['entry_price'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'confidence': 'HIGH'
            })
        
        # Add additional patterns
        if len(additional_signals) > 0:
            for _, signal in additional_signals.iterrows():
                combined_signals.append({
                    'time': signal['time'],
                    'source': 'ADDITIONAL',
                    'pattern': signal['pattern'],
                    'entry_price': signal['entry_price'],
                    'stop_loss': signal['stop_loss'],
                    'take_profit': signal['take_profit'],
                    'confidence': signal['confidence']
                })
        
        combined_df = pd.DataFrame(combined_signals)
        combined_df = combined_df.sort_values('time')
        
        # Remove duplicates (same time signals)
        combined_df = combined_df.drop_duplicates(subset=['time'], keep='first')
        
        print(f"\n✅ Combined Strategy Complete:")
        print(f"   Total signals: {len(combined_df)}")
        print(f"   Baseline: {len(combined_df[combined_df['source'] == 'BASELINE'])}")
        print(f"   Additional: {len(combined_df[combined_df['source'] == 'ADDITIONAL'])}")
        
        return combined_df
    
    def get_stats(self):
        """Get strategy statistics"""
        return {
            'version': self.version,
            'baseline_expected_pnl': 386.92,
            'additional_expected_pnl': 102.78,
            'combined_expected_pnl': 489.70,
            'improvement_pct': 26.6
        }


def backtest_combined(df, strategy):
    """
    Простой бэктест комбинированной стратегии
    """
    
    print(f"\n🔍 Running backtest...")
    
    # Get signals
    signals_df = strategy.run_strategy(df.copy())
    
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
        
        for j in range(len(df_future)):
            candle = df_future.iloc[j]
            
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
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        
        trades.append({
            'entry_time': entry_time,
            'source': signal['source'],
            'pattern': signal['pattern'],
            'pnl_pct': pnl_pct,
            'exit_type': exit_type
        })
    
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    if len(trades_df) > 0:
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        win_rate = wins / len(trades_df) * 100
        total_pnl = trades_df['pnl_pct'].sum()
        
        wins_pnl = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].sum()
        losses_pnl = abs(trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].sum())
        profit_factor = wins_pnl / losses_pnl if losses_pnl > 0 else 0
        
        print(f"\n✅ Backtest Results:")
        print(f"   {'='*80}")
        print(f"   Total Trades:      {len(trades_df)}")
        print(f"   Win Rate:          {win_rate:.1f}%")
        print(f"   Total PnL:         {total_pnl:+.2f}%")
        print(f"   Avg PnL/Trade:     {total_pnl/len(trades_df):+.2f}%")
        print(f"   Profit Factor:     {profit_factor:.2f}")
        print(f"   {'='*80}")
        
        # By source
        print(f"\n   By Source:")
        for source in ['BASELINE', 'ADDITIONAL']:
            source_trades = trades_df[trades_df['source'] == source]
            if len(source_trades) > 0:
                source_wr = len(source_trades[source_trades['pnl_pct'] > 0]) / len(source_trades) * 100
                source_pnl = source_trades['pnl_pct'].sum()
                print(f"      {source:12s}: {len(source_trades):4d} trades | {source_wr:5.1f}% WR | {source_pnl:+.2f}% PnL")
    
    return trades_df


def main():
    """Example usage"""
    
    print("\n" + "="*100)
    print("PATTERN RECOGNITION STRATEGY V3 - COMBINED")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Initialize combined strategy
    strategy = PatternRecognitionV3Combined(
        fib_mode='standard',
        tp_multiplier=1.4,
        enable_missed_patterns=True,
        enable_continuation=True,
        enable_breakout=True
    )
    
    # Run backtest
    trades_df = backtest_combined(df, strategy)
    
    # Save results
    trades_df.to_csv('combined_strategy_v3_results.csv', index=False)
    print(f"\n💾 Results saved to: combined_strategy_v3_results.csv")
    
    # Compare with expected
    stats = strategy.get_stats()
    actual_pnl = trades_df['pnl_pct'].sum() if len(trades_df) > 0 else 0
    
    print(f"\n📊 Expected vs Actual:")
    print(f"   Expected PnL: {stats['combined_expected_pnl']:.2f}%")
    print(f"   Actual PnL:   {actual_pnl:.2f}%")
    
    diff = actual_pnl - stats['combined_expected_pnl']
    if abs(diff) < 10:
        print(f"   ✅ Results match expected (diff: {diff:+.2f}%)")
    else:
        print(f"   ⚠️ Results differ from expected (diff: {diff:+.2f}%)")
    
    return strategy, trades_df


if __name__ == "__main__":
    strategy, trades_df = main()
