"""
Pattern Recognition V7 - HYBRID (Best of both worlds)

Стратегия:
1. BASELINE: БЕЗ breakeven → Max PnL (как оригинал)
2. 30-PIP паттерны: С breakeven → Защита "почти победителей"

Почему:
- Baseline уже хорошо работает (WR 63.4%, +374%)
- 30-Pip паттерны имеют много "почти побед" → нужна защита

Result: Max PnL от baseline + защита для 30-pip
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2
from thirty_pip_detector_final_v2 import ThirtyPipDetectorFinalV2


class PatternRecognitionV7Hybrid:
    """
    V7 HYBRID - Разные правила для разных источников
    
    BASELINE signals:
    - Оригинальные правила
    - БЕЗ breakeven
    - Максимальная прибыль
    
    30-PIP signals:
    - С breakeven после +25 пипсов
    - Trailing SL после +40 пипсов
    - Защита от "почти побед"
    """
    
    def __init__(self, 
                 fib_mode='standard',
                 tp_multiplier=1.4,
                 enable_30pip_patterns=True,
                 high_confidence_only=True,
                 # 30-Pip protection settings
                 pip_breakeven_trigger=25,  # Breakeven для 30-pip
                 pip_trailing_trigger=40):   # Trailing для 30-pip
        
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
        
        # 30-Pip protection settings
        self.pip_breakeven_trigger = pip_breakeven_trigger
        self.pip_trailing_trigger = pip_trailing_trigger
        
        # Version info
        self.version = "V7_HYBRID"
        self.description = "Baseline (no BE) + 30-Pip (with BE protection)"
    
    def run_strategy(self, df):
        """Get all signals"""
        
        print(f"\n" + "="*100)
        print(f"🎯 {self.version} - Hybrid Strategy")
        print("="*100)
        print(f"   {self.description}")
        print(f"   ")
        print(f"   BASELINE:  No breakeven (max PnL)")
        print(f"   30-PIP:    Breakeven @ {self.pip_breakeven_trigger}p, Trailing @ {self.pip_trailing_trigger}p")
        
        # Get baseline signals
        print(f"\n1️⃣  Running BASELINE strategy (V2)...")
        baseline_df = self.baseline_strategy.run_strategy(df.copy())
        baseline_signals = baseline_df[baseline_df['signal'] == 1].copy()
        baseline_signals['time'] = baseline_signals.index
        baseline_signals['type'] = baseline_signals['signal_type'].str.upper()
        baseline_signals = baseline_signals[[
            'time', 'type', 'entry_price', 'stop_loss', 'take_profit', 'signal_reason'
        ]].copy()
        baseline_signals = baseline_signals.rename(columns={'signal_reason': 'pattern'})
        baseline_signals['source'] = 'BASELINE'
        baseline_signals['detector_pattern'] = baseline_signals['pattern']
        
        print(f"   ✅ Baseline signals: {len(baseline_signals)}")
        
        combined_df = baseline_signals.copy()
        
        # Get 30-Pip signals
        if self.enable_30pip and self.pip_detector is not None:
            print(f"\n2️⃣  Running 30-PIP DETECTOR (Final V2)...")
            
            pip_signals = self.pip_detector.get_signals(df.copy())
            
            print(f"   ✅ 30-Pip signals: {len(pip_signals)}")
            
            if len(pip_signals) > 0:
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
                        'detector_pattern': signal['type']
                    })
                
                pip_df = pd.DataFrame(pip_signals_converted)
                
                # Combine
                print(f"\n3️⃣  Combining signals...")
                combined_df = pd.concat([baseline_signals, pip_df], ignore_index=True)
                combined_df = combined_df.sort_values('time').reset_index(drop=True)
                
                # Deduplicate
                combined_df['hour'] = combined_df['time'].dt.floor('H')
                before_dedup = len(combined_df)
                combined_df = combined_df.drop_duplicates(subset=['hour'], keep='first')
                combined_df = combined_df.drop(columns=['hour'])
                after_dedup = len(combined_df)
                
                print(f"   Before dedup:  {before_dedup}")
                print(f"   After dedup:   {after_dedup}")
                print(f"   Removed:       {before_dedup - after_dedup}")
                
                baseline_count = len(combined_df[combined_df['source'] == 'BASELINE'])
                pip_count = len(combined_df[combined_df['source'] == '30PIP'])
                
                print(f"\n   📊 Final signal breakdown:")
                print(f"      BASELINE: {baseline_count}")
                print(f"      30PIP:    {pip_count}")
                print(f"      TOTAL:    {len(combined_df)}")
        
        return combined_df
    
    def backtest(self, df):
        """
        Backtest with source-specific rules:
        - BASELINE: Standard exit (no breakeven)
        - 30PIP: With breakeven + trailing protection
        """
        
        print(f"\n" + "="*100)
        print(f"🔍 BACKTESTING {self.version}")
        print("="*100)
        
        signals_df = self.run_strategy(df.copy())
        
        if len(signals_df) == 0:
            print("❌ No signals")
            return pd.DataFrame()
        
        # Pattern-specific settings for 30-Pip
        pattern_settings = {
            'MOMENTUM': {
                'use_partial_tp': True,
                'partial_tp_pips': 30,
                'partial_tp_size': 0.5,
                'sl_multiplier': 0.75,
            },
            'PULLBACK': {
                'use_partial_tp': False,
                'sl_multiplier': 1.0,
            },
            'VOLATILITY': {
                'use_partial_tp': False,
                'sl_multiplier': 1.0,
            },
            'BOUNCE': {
                'use_partial_tp': True,
                'partial_tp_pips': 30,
                'partial_tp_size': 0.5,
                'sl_multiplier': 0.9,
            },
        }
        
        trades = []
        
        for idx, signal in signals_df.iterrows():
            entry_time = signal['time']
            entry_price = signal['entry_price']
            original_sl = signal['stop_loss']
            take_profit = signal['take_profit']
            source = signal['source']
            detector_pattern = signal.get('detector_pattern', '')
            
            search_end = entry_time + timedelta(hours=24)
            df_future = df[(df.index > entry_time) & (df.index <= search_end)]
            
            if len(df_future) == 0:
                continue
            
            # Get pattern settings
            settings = pattern_settings.get(detector_pattern, {}) if source == '30PIP' else {}
            
            # Adjust SL for 30-Pip
            stop_loss = original_sl
            if source == '30PIP' and settings.get('sl_multiplier', 1.0) != 1.0:
                sl_distance = entry_price - original_sl
                stop_loss = entry_price - (sl_distance * settings['sl_multiplier'])
            
            # ==========================================
            # BASELINE: Simple backtest (no breakeven)
            # ==========================================
            if source == 'BASELINE':
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
                    'breakeven_used': False,
                    'hit_tp': hit_tp,
                    'hit_sl': hit_sl
                })
            
            # ==========================================
            # 30-PIP: With breakeven + trailing
            # ==========================================
            else:  # source == '30PIP'
                position_size = 1.0
                total_pnl_dollars = 0
                current_sl = stop_loss
                exits = []
                
                partial_tp_price = None
                if settings.get('use_partial_tp', False):
                    partial_tp_price = entry_price + (settings['partial_tp_pips'] * 0.10)
                
                breakeven_activated = False
                trailing_activated = False
                max_profit_pips = 0
                
                for j in range(len(df_future)):
                    candle = df_future.iloc[j]
                    
                    if position_size <= 0:
                        break
                    
                    current_profit_dollars = candle['high'] - entry_price
                    current_profit_pips = current_profit_dollars / 0.10
                    max_profit_pips = max(max_profit_pips, current_profit_pips)
                    
                    # PARTIAL TP
                    if (settings.get('use_partial_tp', False) and 
                        position_size == 1.0 and 
                        partial_tp_price is not None and 
                        candle['high'] >= partial_tp_price):
                        
                        partial_pnl = (partial_tp_price - entry_price) * settings['partial_tp_size']
                        total_pnl_dollars += partial_pnl
                        position_size = 1.0 - settings['partial_tp_size']
                        
                        exits.append('Partial_TP')
                        current_sl = entry_price  # Move to breakeven
                        breakeven_activated = True
                        
                        continue
                    
                    # BREAKEVEN (для 30-PIP)
                    if not breakeven_activated and current_profit_pips >= self.pip_breakeven_trigger:
                        current_sl = entry_price
                        breakeven_activated = True
                        exits.append(f'BE@{self.pip_breakeven_trigger}p')
                    
                    # TRAILING (для 30-PIP)
                    if breakeven_activated and not trailing_activated:
                        if current_profit_pips >= self.pip_trailing_trigger:
                            trailing_activated = True
                            exits.append(f'Trail@{self.pip_trailing_trigger}p')
                    
                    # Update trailing
                    if trailing_activated:
                        profit_above = current_profit_pips - self.pip_trailing_trigger
                        new_trailing = entry_price + ((self.pip_trailing_trigger + profit_above * 0.5) * 0.10)
                        current_sl = max(current_sl, new_trailing)
                    
                    # Check SL
                    if candle['low'] <= current_sl:
                        exit_pnl = (current_sl - entry_price) * position_size
                        total_pnl_dollars += exit_pnl
                        
                        if trailing_activated:
                            exits.append('Trail_SL')
                        elif breakeven_activated:
                            exits.append('BE_SL')
                        else:
                            exits.append('SL')
                        
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
                
                exit_type = '→'.join(exits) if exits else 'TIMEOUT'
                pnl_pct = (total_pnl_dollars / entry_price) * 100
                
                trades.append({
                    'entry_time': entry_time,
                    'pattern': signal['pattern'],
                    'source': source,
                    'detector_pattern': detector_pattern,
                    'entry_price': entry_price,
                    'pnl_dollars': total_pnl_dollars,
                    'pnl_pct': pnl_pct,
                    'max_profit_pips': max_profit_pips,
                    'exit_type': exit_type,
                    'breakeven_used': breakeven_activated,
                    'hit_tp': 'TP' in exit_type,
                    'hit_sl': 'SL' in exit_type
                })
        
        trades_df = pd.DataFrame(trades)
        
        # Print results
        self._print_results(trades_df)
        
        return trades_df
    
    def _print_results(self, trades_df):
        """Print results"""
        
        print(f"\n" + "="*100)
        print(f"✅ BACKTEST RESULTS - {self.version}")
        print("="*100)
        
        if len(trades_df) == 0:
            print("No trades")
            return
        
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = trades_df['pnl_pct'].sum()
        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if (total_trades - wins) > 0 else 0
        
        gross_profit = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].sum()
        gross_loss = abs(trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        cumulative = trades_df['pnl_pct'].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_drawdown = drawdown.min()
        
        print(f"\n📊 Overall Performance:")
        print(f"   Total Trades:      {total_trades}")
        print(f"   Wins / Losses:     {wins} / {total_trades - wins}")
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
                
                be_used = len(source_trades[source_trades['breakeven_used'] == True]) if 'breakeven_used' in source_trades.columns else 0
                be_info = f" | BE: {be_used} ({be_used/len(source_trades)*100:.1f}%)" if source == '30PIP' else ""
                
                print(f"   {source:10s}: {len(source_trades):3d} trades | "
                      f"WR {source_wr:5.1f}% | PnL {source_pnl:+7.2f}%{be_info}")
        
        # 30-Pip breakdown
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
            
            # Breakeven saves for 30-Pip
            be_saves = pip_trades[
                (pip_trades['breakeven_used'] == True) & 
                (pip_trades['pnl_pct'] >= -0.1) &
                (pip_trades['max_profit_pips'] >= 25)
            ]
            
            if len(be_saves) > 0:
                print(f"\n   💰 30-Pip Breakeven SAVES: {len(be_saves)} trades")
                print(f"      Protected from potential losses!")


def compare_with_v5(df):
    """Compare V7 Hybrid with V5 (no breakeven)"""
    
    print("\n" + "="*100)
    print("📊 COMPARISON: V5 vs V7 HYBRID")
    print("="*100)
    
    # V5 (no breakeven anywhere)
    print("\n1️⃣  V5 - No breakeven:")
    try:
        from pattern_recognition_v5_final import PatternRecognitionV5Final
        
        strategy_v5 = PatternRecognitionV5Final(
            fib_mode='standard',
            tp_multiplier=1.4,
            enable_30pip_patterns=True,
            high_confidence_only=True
        )
        
        trades_v5 = strategy_v5.backtest(df.copy())
        
        v5_pnl = trades_v5['pnl_pct'].sum()
        v5_wr = len(trades_v5[trades_v5['pnl_pct'] > 0]) / len(trades_v5) * 100
        v5_count = len(trades_v5)
        
        cumulative = trades_v5['pnl_pct'].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        v5_dd = drawdown.min()
        
        print(f"\n   V5 Results:")
        print(f"   Total PnL:  {v5_pnl:+.2f}%")
        print(f"   Win Rate:   {v5_wr:.1f}%")
        print(f"   Max DD:     {v5_dd:.2f}%")
        print(f"   Trades:     {v5_count}")
        
    except Exception as e:
        print(f"   ❌ Could not load V5: {e}")
        trades_v5 = None
        v5_pnl = 0
        v5_wr = 0
        v5_dd = 0
        v5_count = 0
    
    # V7 Hybrid
    print("\n2️⃣  V7 - HYBRID (Baseline no BE + 30-Pip with BE):")
    
    strategy_v7 = PatternRecognitionV7Hybrid(
        fib_mode='standard',
        tp_multiplier=1.4,
        enable_30pip_patterns=True,
        high_confidence_only=True,
        pip_breakeven_trigger=25,
        pip_trailing_trigger=40
    )
    
    trades_v7 = strategy_v7.backtest(df.copy())
    
    if len(trades_v7) > 0:
        v7_pnl = trades_v7['pnl_pct'].sum()
        v7_wr = len(trades_v7[trades_v7['pnl_pct'] > 0]) / len(trades_v7) * 100
        v7_count = len(trades_v7)
        
        cumulative = trades_v7['pnl_pct'].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        v7_dd = drawdown.min()
        
        if trades_v5 is not None:
            print(f"\n" + "="*100)
            print(f"📊 COMPARISON TABLE")
            print("="*100)
            
            print(f"\n{'Metric':<20} {'V5 (No BE)':<15} {'V7 (Hybrid)':<15} {'Difference':<15}")
            print("-"*70)
            print(f"{'Total PnL':<20} {v5_pnl:>+13.2f}% {v7_pnl:>+13.2f}% {v7_pnl-v5_pnl:>+13.2f}%")
            print(f"{'Win Rate':<20} {v5_wr:>12.1f}% {v7_wr:>12.1f}% {v7_wr-v5_wr:>+12.1f}%")
            print(f"{'Max Drawdown':<20} {v5_dd:>12.2f}% {v7_dd:>12.2f}% {v7_dd-v5_dd:>+12.2f}%")
            print(f"{'Total Trades':<20} {v5_count:>13} {v7_count:>13} {v7_count-v5_count:>+13}")
            
            improvement = v7_pnl - v5_pnl
            improvement_pct = (v7_pnl / v5_pnl - 1) * 100 if v5_pnl != 0 else 0
            
            print(f"\n💰 V7 vs V5:")
            print(f"   PnL:  {improvement:+.2f}% ({improvement_pct:+.1f}% relative)")
            print(f"   WR:   {v7_wr - v5_wr:+.1f}%")
            print(f"   DD:   {v7_dd - v5_dd:+.2f}% ({'better' if v7_dd > v5_dd else 'worse'})")
            
            # Save
            trades_v7.to_csv('pattern_recognition_v7_hybrid_backtest.csv', index=False)
            print(f"\n💾 Saved: pattern_recognition_v7_hybrid_backtest.csv")
        
        return trades_v7, trades_v5
    
    return trades_v7, trades_v5


def main():
    print("\n" + "="*100)
    print("🚀 PATTERN RECOGNITION V7 - HYBRID")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Compare with V5
    trades_v7, trades_v5 = compare_with_v5(df)
    
    print(f"\n" + "="*100)
    print("🏆 FINAL SUMMARY")
    print("="*100)
    
    if trades_v7 is not None and len(trades_v7) > 0:
        v7_pnl = trades_v7['pnl_pct'].sum()
        v7_wr = len(trades_v7[trades_v7['pnl_pct'] > 0]) / len(trades_v7) * 100
        
        print(f"\n✅ V7 HYBRID Performance:")
        print(f"   Total PnL:  {v7_pnl:+.2f}%")
        print(f"   Win Rate:   {v7_wr:.1f}%")
        print(f"   Trades:     {len(trades_v7)}")
        
        print(f"\n💡 V7 Strategy:")
        print(f"   ✅ BASELINE: Без breakeven → Максимальная прибыль")
        print(f"   ✅ 30-PIP:   С breakeven @ 25p → Защита 'почти побед'")
        print(f"   ✅ Best of both worlds!")


if __name__ == "__main__":
    main()
