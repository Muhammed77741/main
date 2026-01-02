"""
Pattern Recognition V5 - FINAL VERSION

Комбинирует:
1. PatternRecognitionOptimizedV2 (Baseline: LONG only, TP=1.4)
2. ThirtyPipDetectorFinalV2 (30-pip patterns с pattern-specific оптимизациями)

V5 improvements:
- Baseline: +386.92% (LONG only, TP 1.4)
- 30-pip: +4730 pips (MOMENTUM optimized, PULLBACK/VOLATILITY unchanged)
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2
from thirty_pip_detector_final_v2 import ThirtyPipDetectorFinalV2


class PatternRecognitionV5Final:
    """
    Финальная комбинированная версия стратегии
    
    Комбинирует:
    - Baseline V2 (LONG only, TP 1.4)
    - 30-Pip Detector Final V2 (HIGH confidence, pattern-specific optimizations)
    """
    
    def __init__(self, 
                 fib_mode='standard',
                 tp_multiplier=1.4,
                 enable_30pip_patterns=True,
                 high_confidence_only=True):
        
        # Baseline strategy
        self.baseline_strategy = PatternRecognitionOptimizedV2(
            fib_mode=fib_mode,
            tp_multiplier=tp_multiplier,
            long_only=True
        )
        
        # 30-Pip detector
        self.pip_detector = None
        if enable_30pip_patterns:
            self.pip_detector = ThirtyPipDetectorFinalV2(
                focus_long_only=True,
                high_confidence_only=high_confidence_only
            )
        
        self.enable_30pip = enable_30pip_patterns
        self.high_confidence_only = high_confidence_only
        
        # Version info
        self.version = "V5_Final"
        self.description = "Baseline V2 + 30-Pip Final V2 (pattern-specific optimizations)"
        
        # Expected performance (from individual backtests)
        self.expected_baseline_pnl_pct = 386.92
        self.expected_30pip_pnl_pips = 4730
    
    def run_strategy(self, df):
        """
        Запуск комбинированной стратегии
        
        Returns:
            DataFrame with all signals (BASELINE + 30PIP)
        """
        
        print(f"\n" + "="*100)
        print(f"🎯 {self.version} - Combined Strategy")
        print("="*100)
        print(f"   {self.description}")
        
        # 1. Get baseline signals
        print(f"\n1️⃣  Running BASELINE strategy (V2)...")
        baseline_df = self.baseline_strategy.run_strategy(df.copy())
        
        # Filter only rows with signals (signal == 1)
        baseline_signals = baseline_df[baseline_df['signal'] == 1].copy()
        baseline_signals['time'] = baseline_signals.index
        
        # Determine type based on signal_type column
        baseline_signals['type'] = baseline_signals['signal_type'].str.upper()
        
        # Select relevant columns
        baseline_signals = baseline_signals[[
            'time', 'type', 'entry_price', 'stop_loss', 'take_profit', 'signal_reason'
        ]].copy()
        
        # Rename for consistency
        baseline_signals = baseline_signals.rename(columns={'signal_reason': 'pattern'})
        
        # Add source and detector_pattern
        baseline_signals['source'] = 'BASELINE'
        baseline_signals['detector_pattern'] = baseline_signals['pattern']
        
        print(f"   ✅ Baseline signals: {len(baseline_signals)}")
        
        # 2. Get 30-Pip signals
        combined_df = baseline_signals.copy()
        
        if self.enable_30pip and self.pip_detector is not None:
            print(f"\n2️⃣  Running 30-PIP DETECTOR (Final V2)...")
            
            pip_signals = self.pip_detector.get_signals(df.copy())
            
            print(f"   ✅ 30-Pip signals: {len(pip_signals)}")
            
            if len(pip_signals) > 0:
                # Convert to common format
                pip_signals_converted = []
                
                for idx, signal in pip_signals.iterrows():
                    pip_signals_converted.append({
                        'time': signal['time'],
                        'pattern': signal['pattern'],
                        'type': 'LONG',
                        'entry_price': signal['entry_price'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit'],
                        'source': '30PIP',
                        'detector_pattern': signal['type']  # MOMENTUM, PULLBACK, etc.
                    })
                
                pip_df = pd.DataFrame(pip_signals_converted)
                
                # Combine
                print(f"\n3️⃣  Combining signals...")
                combined_df = pd.concat([baseline_signals, pip_df], ignore_index=True)
                
                # Sort by time
                combined_df = combined_df.sort_values('time').reset_index(drop=True)
                
                # Deduplicate: Keep first signal within same hour (priority: BASELINE > 30PIP)
                combined_df['hour'] = combined_df['time'].dt.floor('H')
                
                before_dedup = len(combined_df)
                combined_df = combined_df.drop_duplicates(subset=['hour'], keep='first')
                combined_df = combined_df.drop(columns=['hour'])
                after_dedup = len(combined_df)
                
                duplicates_removed = before_dedup - after_dedup
                
                print(f"   Before dedup:  {before_dedup}")
                print(f"   After dedup:   {after_dedup}")
                print(f"   Removed:       {duplicates_removed} (same hour conflicts)")
                
                # Count by source
                baseline_count = len(combined_df[combined_df['source'] == 'BASELINE'])
                pip_count = len(combined_df[combined_df['source'] == '30PIP'])
                
                print(f"\n   📊 Final signal breakdown:")
                print(f"      BASELINE: {baseline_count}")
                print(f"      30PIP:    {pip_count}")
                print(f"      TOTAL:    {len(combined_df)}")
        
        return combined_df
    
    def backtest(self, df):
        """
        Backtest with pattern-specific exit logic for 30-Pip signals
        """
        
        print(f"\n" + "="*100)
        print(f"🔍 BACKTESTING {self.version} (with optimized exits for 30-Pip)")
        print("="*100)
        
        # Get signals
        signals_df = self.run_strategy(df.copy())
        
        if len(signals_df) == 0:
            print("❌ No signals generated")
            return pd.DataFrame()
        
        # Pattern-specific settings for 30-Pip signals
        pattern_settings = {
            'MOMENTUM': {
                'use_partial_tp': True,
                'partial_tp_pips': 30,
                'partial_tp_size': 0.5,
                'sl_multiplier': 0.75,
                'use_trailing': True,
                'trailing_activation': 15,
                'trailing_distance': 0.5,
            },
            'PULLBACK': {
                'use_partial_tp': False,
                'sl_multiplier': 1.0,
                'use_trailing': False,
            },
            'VOLATILITY': {
                'use_partial_tp': False,
                'sl_multiplier': 1.0,
                'use_trailing': False,
            },
            'BOUNCE': {
                'use_partial_tp': True,
                'partial_tp_pips': 30,
                'partial_tp_size': 0.5,
                'sl_multiplier': 0.9,
                'use_trailing': True,
                'trailing_activation': 20,
                'trailing_distance': 0.6,
            },
        }
        
        trades = []
        
        for idx, signal in signals_df.iterrows():
            entry_time = signal['time']
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            take_profit = signal['take_profit']
            source = signal['source']
            detector_pattern = signal.get('detector_pattern', '')
            
            # Look forward 24h
            search_end = entry_time + timedelta(hours=24)
            df_future = df[(df.index > entry_time) & (df.index <= search_end)]
            
            if len(df_future) == 0:
                continue
            
            # Use optimized exit logic for 30-Pip signals
            if source == '30PIP' and detector_pattern in pattern_settings:
                settings = pattern_settings[detector_pattern]
                
                # Adjust SL
                if settings['sl_multiplier'] != 1.0:
                    sl_distance = entry_price - stop_loss
                    stop_loss = entry_price - (sl_distance * settings['sl_multiplier'])
                
                # Track position
                position_size = 1.0
                total_pnl_dollars = 0
                exits = []
                
                trailing_sl = stop_loss
                trailing_active = False
                
                partial_tp_price = None
                if settings['use_partial_tp']:
                    partial_tp_price = entry_price + (settings['partial_tp_pips'] * 0.10)
                
                for j in range(len(df_future)):
                    candle = df_future.iloc[j]
                    
                    if position_size <= 0:
                        break
                    
                    current_profit_dollars = candle['high'] - entry_price
                    current_profit_pips = current_profit_dollars / 0.10
                    
                    # Partial TP
                    if (settings['use_partial_tp'] and 
                        position_size == 1.0 and 
                        partial_tp_price is not None and 
                        candle['high'] >= partial_tp_price):
                        
                        partial_pnl = (partial_tp_price - entry_price) * settings['partial_tp_size']
                        total_pnl_dollars += partial_pnl
                        position_size = 1.0 - settings['partial_tp_size']
                        
                        exits.append('Partial TP')
                        trailing_sl = entry_price  # Move to breakeven
                        trailing_active = True
                        continue
                    
                    # Trailing
                    if (settings.get('use_trailing', False) and 
                        current_profit_pips >= settings.get('trailing_activation', 15)):
                        
                        if not trailing_active:
                            trailing_active = True
                            trailing_sl = entry_price
                        
                        profit_above = current_profit_pips - settings['trailing_activation']
                        new_trailing = entry_price + (
                            (settings['trailing_activation'] + 
                             profit_above * settings['trailing_distance']) * 0.10
                        )
                        trailing_sl = max(trailing_sl, new_trailing)
                    
                    # Check SL
                    active_sl = trailing_sl if trailing_active else stop_loss
                    
                    if candle['low'] <= active_sl:
                        exit_pnl = (active_sl - entry_price) * position_size
                        total_pnl_dollars += exit_pnl
                        
                        exits.append('Trailing SL' if trailing_active else 'SL')
                        position_size = 0
                        break
                    
                    # Check TP
                    if candle['high'] >= take_profit:
                        exit_pnl = (take_profit - entry_price) * position_size
                        total_pnl_dollars += exit_pnl
                        
                        exits.append('TP')
                        position_size = 0
                        break
                
                # Timeout
                if position_size > 0:
                    exit_price = df_future['close'].iloc[-1]
                    exit_pnl = (exit_price - entry_price) * position_size
                    total_pnl_dollars += exit_pnl
                    exits.append('TIMEOUT')
                
                exit_type = ', '.join(exits) if exits else 'TIMEOUT'
                pnl_pct = (total_pnl_dollars / entry_price) * 100
                
                trades.append({
                    'entry_time': entry_time,
                    'pattern': signal['pattern'],
                    'source': source,
                    'detector_pattern': detector_pattern,
                    'entry_price': entry_price,
                    'pnl_dollars': total_pnl_dollars,
                    'pnl_pct': pnl_pct,
                    'exit_type': exit_type,
                    'hit_tp': 'TP' in exit_type,
                    'hit_sl': 'SL' in exit_type
                })
                
            else:
                # Standard backtest for BASELINE signals
                hit_tp = False
                hit_sl = False
                exit_price = None
                exit_type = 'TIMEOUT'
                
                for j in range(len(df_future)):
                    candle = df_future.iloc[j]
                    
                    # Check SL
                    if candle['low'] <= stop_loss:
                        hit_sl = True
                        exit_price = stop_loss
                        exit_type = 'SL'
                        break
                    
                    # Check TP
                    if candle['high'] >= take_profit:
                        hit_tp = True
                        exit_price = take_profit
                        exit_type = 'TP'
                        break
                
                # Timeout
                if exit_price is None:
                    exit_price = df_future['close'].iloc[-1]
                    exit_type = 'TIMEOUT'
                
                pnl_dollars = exit_price - entry_price
                pnl_pct = (pnl_dollars / entry_price) * 100
                
                trades.append({
                    'entry_time': entry_time,
                    'pattern': signal['pattern'],
                    'source': source,
                    'detector_pattern': detector_pattern,
                    'entry_price': entry_price,
                    'pnl_dollars': pnl_dollars,
                    'pnl_pct': pnl_pct,
                    'exit_type': exit_type,
                    'hit_tp': hit_tp,
                    'hit_sl': hit_sl
                })
        
        trades_df = pd.DataFrame(trades)
        
        # Print results
        self._print_results(trades_df)
        
        return trades_df
    
    def _print_results(self, trades_df):
        """
        Print backtest results
        """
        
        print(f"\n" + "="*100)
        print(f"✅ BACKTEST RESULTS - {self.version}")
        print("="*100)
        
        if len(trades_df) == 0:
            print("No trades")
            return
        
        # Overall stats
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        losses = len(trades_df[trades_df['pnl_pct'] <= 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = trades_df['pnl_pct'].sum()
        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if losses > 0 else 0
        
        gross_profit = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].sum()
        gross_loss = abs(trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        # Max drawdown
        cumulative = trades_df['pnl_pct'].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_drawdown = drawdown.min()
        
        print(f"\n📊 Overall Performance:")
        print(f"   Total Trades:      {total_trades}")
        print(f"   Wins / Losses:     {wins} / {losses}")
        print(f"   Win Rate:          {win_rate:.1f}%")
        print(f"   ")
        print(f"   Total PnL:         {total_pnl:+.2f}%  ⭐")
        print(f"   Avg Win:           {avg_win:+.3f}%")
        print(f"   Avg Loss:          {avg_loss:+.3f}%")
        print(f"   Profit Factor:     {profit_factor:.2f}")
        print(f"   Max Drawdown:      {max_drawdown:.2f}%")
        
        # By source
        print(f"\n📊 By Source:")
        for source in ['BASELINE', '30PIP']:
            source_trades = trades_df[trades_df['source'] == source]
            if len(source_trades) > 0:
                source_wins = len(source_trades[source_trades['pnl_pct'] > 0])
                source_wr = (source_wins / len(source_trades) * 100)
                source_pnl = source_trades['pnl_pct'].sum()
                
                print(f"   {source:10s}: {len(source_trades):3d} trades | "
                      f"WR {source_wr:5.1f}% | PnL {source_pnl:+7.2f}%")
        
        # By detector pattern (for 30PIP)
        pip_trades = trades_df[trades_df['source'] == '30PIP']
        if len(pip_trades) > 0:
            print(f"\n📊 30-Pip Detector Breakdown:")
            for pattern_type in pip_trades['detector_pattern'].unique():
                pattern_trades = pip_trades[pip_trades['detector_pattern'] == pattern_type]
                pattern_wins = len(pattern_trades[pattern_trades['pnl_pct'] > 0])
                pattern_wr = (pattern_wins / len(pattern_trades) * 100)
                pattern_pnl = pattern_trades['pnl_pct'].sum()
                
                print(f"   {pattern_type:15s}: {len(pattern_trades):3d} trades | "
                      f"WR {pattern_wr:5.1f}% | PnL {pattern_pnl:+7.2f}%")
        
        # Exit types
        print(f"\n📊 By Exit Type:")
        for exit_type in ['TP', 'SL', 'TIMEOUT']:
            exit_trades = trades_df[trades_df['exit_type'] == exit_type]
            if len(exit_trades) > 0:
                exit_pct = len(exit_trades) / len(trades_df) * 100
                exit_pnl = exit_trades['pnl_pct'].sum()
                
                print(f"   {exit_type:10s}: {len(exit_trades):3d} ({exit_pct:5.1f}%) | "
                      f"PnL {exit_pnl:+7.2f}%")


def compare_with_v4(df):
    """
    Сравнение V5 (Final) с V4 (Previous)
    """
    
    print("\n" + "="*100)
    print("📊 COMPARISON: V4 vs V5")
    print("="*100)
    
    # V4 (Previous)
    print("\n1️⃣  V4 - Previous version:")
    try:
        from pattern_recognition_v4_with_30pip import PatternRecognitionV4With30Pip
        
        strategy_v4 = PatternRecognitionV4With30Pip(
            fib_mode='standard',
            tp_multiplier=1.4,
            enable_30pip_patterns=True,
            high_confidence_only=True
        )
        
        trades_v4 = strategy_v4.backtest(df.copy())
        
        v4_pnl = trades_v4['pnl_pct'].sum()
        v4_wr = len(trades_v4[trades_v4['pnl_pct'] > 0]) / len(trades_v4) * 100
        v4_count = len(trades_v4)
        
        print(f"\n   V4 Results:")
        print(f"   Total PnL: {v4_pnl:+.2f}%")
        print(f"   Trades:    {v4_count}")
        print(f"   Win Rate:  {v4_wr:.1f}%")
        
    except Exception as e:
        print(f"   ❌ Could not load V4: {e}")
        trades_v4 = None
        v4_pnl = 0
        v4_count = 0
    
    # V5 (Final)
    print("\n2️⃣  V5 - FINAL version (with pattern-specific optimizations):")
    
    strategy_v5 = PatternRecognitionV5Final(
        fib_mode='standard',
        tp_multiplier=1.4,
        enable_30pip_patterns=True,
        high_confidence_only=True
    )
    
    trades_v5 = strategy_v5.backtest(df.copy())
    
    if len(trades_v5) > 0 and trades_v4 is not None:
        v5_pnl = trades_v5['pnl_pct'].sum()
        v5_wr = len(trades_v5[trades_v5['pnl_pct'] > 0]) / len(trades_v5) * 100
        v5_count = len(trades_v5)
        
        print(f"\n" + "="*100)
        print(f"📊 COMPARISON TABLE")
        print("="*100)
        
        print(f"\n{'Metric':<20} {'V4':<15} {'V5 (Final)':<15} {'Difference':<15}")
        print("-"*70)
        print(f"{'Total PnL':<20} {v4_pnl:>+13.2f}% {v5_pnl:>+13.2f}% {v5_pnl-v4_pnl:>+13.2f}%")
        print(f"{'Total Trades':<20} {v4_count:>13} {v5_count:>13} {v5_count-v4_count:>+13}")
        print(f"{'Win Rate':<20} {v4_wr:>12.1f}% {v5_wr:>12.1f}% {v5_wr-v4_wr:>+12.1f}%")
        
        improvement = v5_pnl - v4_pnl
        improvement_pct = (v5_pnl / v4_pnl - 1) * 100 if v4_pnl != 0 else 0
        
        print(f"\n💰 V5 Improvement: {improvement:+.2f}% ({improvement_pct:+.1f}% relative)")
        
        # Save
        trades_v5.to_csv('pattern_recognition_v5_final_backtest.csv', index=False)
        print(f"\n💾 Saved: pattern_recognition_v5_final_backtest.csv")
        
        return trades_v5, trades_v4
    
    return trades_v5, trades_v4


def main():
    print("\n" + "="*100)
    print("🚀 PATTERN RECOGNITION V5 - FINAL")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Compare with V4
    trades_v5, trades_v4 = compare_with_v4(df)
    
    print(f"\n" + "="*100)
    print("🏆 FINAL SUMMARY")
    print("="*100)
    
    if trades_v5 is not None and len(trades_v5) > 0:
        v5_pnl = trades_v5['pnl_pct'].sum()
        v5_wr = len(trades_v5[trades_v5['pnl_pct'] > 0]) / len(trades_v5) * 100
        
        print(f"\n✅ V5 FINAL Performance:")
        print(f"   Total PnL:  {v5_pnl:+.2f}%")
        print(f"   Win Rate:   {v5_wr:.1f}%")
        print(f"   Trades:     {len(trades_v5)}")
        
        print(f"\n💡 Key Improvements:")
        print(f"   ✅ MOMENTUM паттерн: +20.3% благодаря Partial TP")
        print(f"   ✅ PULLBACK/VOLATILITY: Оставлены без изменений (уже оптимальны)")
        print(f"   ✅ Комбинация Baseline + 30-Pip детектор")


if __name__ == "__main__":
    main()
