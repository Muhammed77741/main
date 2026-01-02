"""
Оптимизированный детектор 30-pip паттернов

Улучшения:
1. MOMENTUM: Tighter SL + Partial TP + Trailing SL
2. PULLBACK: Только Trailing SL (без Partial TP!)
3. VOLATILITY: Aggressive TP
4. BOUNCE: Standard settings
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from detect_30pip_patterns import ThirtyPipMoveDetector


class ThirtyPipDetectorOptimized:
    """
    Оптимизированная версия 30-pip детектора
    
    Индивидуальные настройки для каждого паттерна:
    - MOMENTUM: Partial TP + Tighter SL + Trailing
    - PULLBACK: Только Trailing (большие TP)
    - VOLATILITY: Aggressive TP
    - BOUNCE: Standard + Trailing
    """
    
    def __init__(self, focus_long_only=True, high_confidence_only=True):
        self.detector = ThirtyPipMoveDetector(focus_long_only=focus_long_only)
        self.high_confidence_only = high_confidence_only
        
        # Pattern-specific settings
        self.pattern_settings = {
            'MOMENTUM': {
                'use_partial_tp': True,  # Да, помогает!
                'partial_tp_pips': 30,
                'partial_tp_size': 0.5,
                'sl_multiplier': 0.7,  # Tighter SL
                'use_trailing': True,
                'trailing_activation': 15,
                'trailing_distance': 0.5,
                'move_sl_to_breakeven': True
            },
            'PULLBACK': {
                'use_partial_tp': False,  # НЕТ! Обрезает большие профиты
                'partial_tp_pips': 0,
                'partial_tp_size': 0,
                'sl_multiplier': 1.0,  # Standard SL
                'use_trailing': True,  # Только trailing
                'trailing_activation': 20,  # Позже
                'trailing_distance': 0.6,  # Ближе к цене
                'move_sl_to_breakeven': True
            },
            'VOLATILITY': {
                'use_partial_tp': False,  # Дать расти
                'partial_tp_pips': 0,
                'partial_tp_size': 0,
                'sl_multiplier': 1.0,
                'use_trailing': True,
                'trailing_activation': 30,  # Поздний trailing
                'trailing_distance': 0.7,  # Дальше от цены
                'move_sl_to_breakeven': True
            },
            'BOUNCE': {
                'use_partial_tp': True,
                'partial_tp_pips': 30,
                'partial_tp_size': 0.5,
                'sl_multiplier': 0.9,
                'use_trailing': True,
                'trailing_activation': 15,
                'trailing_distance': 0.5,
                'move_sl_to_breakeven': True
            },
            'BREAKOUT': {
                'use_partial_tp': False,
                'partial_tp_pips': 0,
                'partial_tp_size': 0,
                'sl_multiplier': 1.0,
                'use_trailing': True,
                'trailing_activation': 20,
                'trailing_distance': 0.6,
                'move_sl_to_breakeven': True
            }
        }
    
    def get_signals(self, df):
        """
        Get signals from detector
        """
        signals_df = self.detector.detect_all_patterns(df.copy())
        
        if self.high_confidence_only and len(signals_df) > 0:
            signals_df = signals_df[signals_df['confidence'] == 'HIGH'].copy()
        
        return signals_df
    
    def backtest_optimized(self, df):
        """
        Бэктест с оптимизированными настройками для каждого паттерна
        """
        
        print(f"\n" + "="*100)
        print(f"🔍 ОПТИМИЗИРОВАННЫЙ БЭКТЕСТ (Pattern-Specific Settings)")
        print("="*100)
        
        signals_df = self.get_signals(df)
        
        print(f"\n   Total signals: {len(signals_df)}")
        
        if len(signals_df) == 0:
            return pd.DataFrame()
        
        # Count by pattern
        print(f"\n   By pattern:")
        for pattern_type in signals_df['type'].unique():
            count = len(signals_df[signals_df['type'] == pattern_type])
            print(f"      {pattern_type:15s}: {count:3d} signals")
        
        trades = []
        
        for idx, signal in signals_df.iterrows():
            entry_time = signal['time']
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            take_profit = signal['take_profit']
            pattern_type = signal['type']
            
            # Get pattern-specific settings
            settings = self.pattern_settings.get(pattern_type, self.pattern_settings['MOMENTUM'])
            
            # Adjust SL
            if settings['sl_multiplier'] != 1.0:
                sl_distance = entry_price - stop_loss
                stop_loss = entry_price - (sl_distance * settings['sl_multiplier'])
            
            # Partial TP level
            partial_tp_price = None
            if settings['use_partial_tp']:
                partial_tp_price = entry_price + (settings['partial_tp_pips'] * 0.10)
            
            # Look forward
            search_end = entry_time + timedelta(hours=24)
            df_future = df[(df.index > entry_time) & (df.index <= search_end)]
            
            if len(df_future) == 0:
                continue
            
            # Track position
            position_size = 1.0
            total_pnl_pips = 0
            max_profit_pips = 0
            exits = []
            
            # Trailing SL
            trailing_sl = stop_loss
            trailing_active = False
            
            for j in range(len(df_future)):
                candle = df_future.iloc[j]
                
                if position_size <= 0:
                    break
                
                # Track max profit
                current_profit_dollars = candle['high'] - entry_price
                current_profit_pips = current_profit_dollars / 0.10
                max_profit_pips = max(max_profit_pips, current_profit_pips)
                
                # Partial TP
                if (settings['use_partial_tp'] and 
                    position_size == 1.0 and 
                    partial_tp_price is not None and 
                    candle['high'] >= partial_tp_price):
                    
                    partial_pnl = settings['partial_tp_pips'] * settings['partial_tp_size']
                    total_pnl_pips += partial_pnl
                    position_size = 1.0 - settings['partial_tp_size']
                    
                    exits.append({
                        'type': f'Partial TP ({settings["partial_tp_pips"]}p)',
                        'pips': partial_pnl
                    })
                    
                    # Move SL to breakeven
                    if settings['move_sl_to_breakeven']:
                        trailing_sl = entry_price
                        trailing_active = True
                    
                    continue
                
                # Trailing SL activation
                if (settings['use_trailing'] and 
                    current_profit_pips >= settings['trailing_activation']):
                    
                    if not trailing_active:
                        trailing_active = True
                        trailing_sl = entry_price  # Start at breakeven
                    
                    # Update trailing
                    profit_above_activation = current_profit_pips - settings['trailing_activation']
                    new_trailing = entry_price + (
                        (settings['trailing_activation'] + 
                         profit_above_activation * settings['trailing_distance']) * 0.10
                    )
                    trailing_sl = max(trailing_sl, new_trailing)
                
                # Check SL
                active_sl = trailing_sl if trailing_active else stop_loss
                
                if candle['low'] <= active_sl:
                    exit_pips = (active_sl - entry_price) / 0.10
                    total_pnl_pips += exit_pips * position_size
                    
                    exits.append({
                        'type': 'Trailing SL' if trailing_active else 'SL',
                        'pips': exit_pips * position_size
                    })
                    
                    position_size = 0
                    break
                
                # Check full TP
                if candle['high'] >= take_profit:
                    exit_pips = (take_profit - entry_price) / 0.10
                    total_pnl_pips += exit_pips * position_size
                    
                    exits.append({
                        'type': 'Full TP',
                        'pips': exit_pips * position_size
                    })
                    
                    position_size = 0
                    break
            
            # Timeout
            if position_size > 0:
                exit_price = df_future['close'].iloc[-1]
                exit_pips = (exit_price - entry_price) / 0.10
                total_pnl_pips += exit_pips * position_size
                
                exits.append({
                    'type': 'TIMEOUT',
                    'pips': exit_pips * position_size
                })
            
            partial_hit = any('Partial TP' in e['type'] for e in exits)
            trailing_hit = any('Trailing' in e['type'] for e in exits)
            
            trades.append({
                'entry_time': entry_time,
                'pattern': signal['pattern'],
                'type': pattern_type,
                'pnl_pips': total_pnl_pips,
                'max_profit_pips': max_profit_pips,
                'reached_30pips': max_profit_pips >= 30,
                'partial_tp_hit': partial_hit,
                'trailing_hit': trailing_hit,
                'exits': exits
            })
        
        trades_df = pd.DataFrame(trades)
        
        # Print results
        self._print_results(trades_df, "OPTIMIZED")
        
        return trades_df
    
    def _print_results(self, trades_df, label=""):
        """
        Print backtest results
        """
        
        print(f"\n✅ Результаты {label}:")
        print(f"   {'='*80}")
        print(f"   Total Trades:      {len(trades_df)}")
        
        if len(trades_df) == 0:
            return
        
        wins = len(trades_df[trades_df['pnl_pips'] > 0])
        win_rate = wins / len(trades_df) * 100
        
        total_pnl = trades_df['pnl_pips'].sum()
        avg_pnl = trades_df['pnl_pips'].mean()
        
        partial_hits = len(trades_df[trades_df['partial_tp_hit'] == True])
        trailing_hits = len(trades_df[trades_df['trailing_hit'] == True])
        reached_30 = len(trades_df[trades_df['reached_30pips'] == True])
        
        print(f"   Win Rate:          {win_rate:.1f}%")
        print(f"   Total PnL:         {total_pnl:+.0f} pips")
        print(f"   Avg PnL:           {avg_pnl:+.1f} pips")
        print(f"   Reached 30+ pips:  {reached_30} ({reached_30/len(trades_df)*100:.1f}%)")
        print(f"   Partial TP hit:    {partial_hits} ({partial_hits/len(trades_df)*100:.1f}%)")
        print(f"   Trailing hit:      {trailing_hits} ({trailing_hits/len(trades_df)*100:.1f}%)")
        print(f"   {'='*80}")
        
        # By pattern
        print(f"\n   By Pattern:")
        for pattern_type in sorted(trades_df['type'].unique()):
            type_trades = trades_df[trades_df['type'] == pattern_type]
            type_wr = len(type_trades[type_trades['pnl_pips'] > 0]) / len(type_trades) * 100
            type_avg = type_trades['pnl_pips'].mean()
            type_total = type_trades['pnl_pips'].sum()
            
            print(f"      {pattern_type:15s}: {len(type_trades):3d} trades | "
                  f"WR {type_wr:5.1f}% | Avg {type_avg:+6.1f}p | Total {type_total:+7.0f}p")


def compare_versions(df):
    """
    Сравнение разных версий
    """
    
    print("\n" + "="*100)
    print("📊 СРАВНЕНИЕ ВЕРСИЙ")
    print("="*100)
    
    # 1. Original (HIGH confidence only, no optimizations)
    print("\n1️⃣  ОРИГИНАЛ (HIGH confidence, no optimizations):")
    detector_original = ThirtyPipMoveDetector(focus_long_only=True)
    signals_original = detector_original.detect_all_patterns(df.copy())
    signals_original = signals_original[signals_original['confidence'] == 'HIGH'].copy()
    
    # Simple backtest
    from thirty_pip_detector_final import backtest_high_confidence_only
    trades_original = backtest_high_confidence_only(df, detector_original)
    
    original_pnl = trades_original['pnl_pips'].sum()
    original_avg = trades_original['pnl_pips'].mean()
    original_wr = len(trades_original[trades_original['pnl_pips'] > 0]) / len(trades_original) * 100
    
    print(f"   Total PnL: {original_pnl:+.0f} pips")
    print(f"   Avg PnL:   {original_avg:+.1f} pips")
    print(f"   Win Rate:  {original_wr:.1f}%")
    
    # 2. With generic improvements (from analyze_weak_patterns.py)
    print("\n2️⃣  С БАЗОВЫМИ УЛУЧШЕНИЯМИ (uniform Partial TP + Trailing):")
    
    try:
        trades_generic = pd.read_csv('30pip_patterns_improved.csv')
        trades_generic['entry_time'] = pd.to_datetime(trades_generic['entry_time'])
        
        generic_pnl = trades_generic['pnl_pips'].sum()
        generic_avg = trades_generic['pnl_pips'].mean()
        generic_wr = len(trades_generic[trades_generic['pnl_pips'] > 0]) / len(trades_generic) * 100
        
        print(f"   Total PnL: {generic_pnl:+.0f} pips")
        print(f"   Avg PnL:   {generic_avg:+.1f} pips")
        print(f"   Win Rate:  {generic_wr:.1f}%")
        print(f"   vs Original: {generic_pnl - original_pnl:+.0f} pips ({(generic_pnl/original_pnl-1)*100:+.1f}%)")
        
    except FileNotFoundError:
        print("   (not available)")
        trades_generic = None
        generic_pnl = 0
    
    # 3. Optimized (pattern-specific settings)
    print("\n3️⃣  ОПТИМИЗИРОВАННАЯ ВЕРСИЯ (pattern-specific settings):")
    detector_optimized = ThirtyPipDetectorOptimized(
        focus_long_only=True,
        high_confidence_only=True
    )
    trades_optimized = detector_optimized.backtest_optimized(df)
    
    if len(trades_optimized) > 0:
        optimized_pnl = trades_optimized['pnl_pips'].sum()
        optimized_avg = trades_optimized['pnl_pips'].mean()
        optimized_wr = len(trades_optimized[trades_optimized['pnl_pips'] > 0]) / len(trades_optimized) * 100
        
        print(f"\n   📊 vs Original:")
        print(f"      Difference: {optimized_pnl - original_pnl:+.0f} pips ({(optimized_pnl/original_pnl-1)*100:+.1f}%)")
        print(f"      Avg/trade:  {optimized_avg:+.1f}p vs {original_avg:+.1f}p")
        print(f"      Win Rate:   {optimized_wr:.1f}% vs {original_wr:.1f}%")
        
        if trades_generic is not None:
            print(f"\n   📊 vs Generic improvements:")
            print(f"      Difference: {optimized_pnl - generic_pnl:+.0f} pips ({(optimized_pnl/generic_pnl-1)*100:+.1f}%)")
            print(f"      Avg/trade:  {optimized_avg:+.1f}p vs {generic_avg:+.1f}p")
            print(f"      Win Rate:   {optimized_wr:.1f}% vs {generic_wr:.1f}%")
        
        # Save
        trades_optimized.to_csv('30pip_patterns_optimized.csv', index=False)
        print(f"\n💾 Saved: 30pip_patterns_optimized.csv")
        
        return trades_optimized, trades_original, trades_generic
    
    return None, trades_original, trades_generic


def main():
    print("\n" + "="*100)
    print("🚀 ОПТИМИЗАЦИЯ 30-PIP ДЕТЕКТОРА")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Compare versions
    trades_optimized, trades_original, trades_generic = compare_versions(df)
    
    if trades_optimized is not None:
        print("\n" + "="*100)
        print("🏆 ФИНАЛЬНЫЕ РЕЗУЛЬТАТЫ")
        print("="*100)
        
        print(f"\n💡 Ключевые улучшения:")
        print(f"   ✅ MOMENTUM: Partial TP + Tighter SL → Сохраняет прибыль от 'почти победителей'")
        print(f"   ✅ PULLBACK: Только Trailing SL → Позволяет большим прибылям расти")
        print(f"   ✅ VOLATILITY: Late Trailing → Максимизирует сильные движения")
        
        # Pattern-specific analysis
        print(f"\n📊 По паттернам:")
        
        for pattern in ['MOMENTUM', 'PULLBACK', 'VOLATILITY', 'BOUNCE']:
            opt_pattern = trades_optimized[trades_optimized['type'] == pattern]
            orig_pattern = trades_original[trades_original['type'] == pattern]
            
            if len(opt_pattern) > 0 and len(orig_pattern) > 0:
                opt_pnl = opt_pattern['pnl_pips'].sum()
                orig_pnl = orig_pattern['pnl_pips'].sum()
                diff = opt_pnl - orig_pnl
                diff_pct = (opt_pnl / orig_pnl - 1) * 100 if orig_pnl != 0 else 0
                
                print(f"   {pattern:12s}: {orig_pnl:>7.0f}p → {opt_pnl:>7.0f}p  "
                      f"({diff:+7.0f}p, {diff_pct:+5.1f}%)")


if __name__ == "__main__":
    main()
