"""
Pattern Recognition V9 ULTIMATE - Final Combined Strategy

Комбинирует:
1. Baseline V2 (LONG only, TP=1.4)
2. 30-Pip Detector Final V2 (HIGH confidence, pattern-specific)
3. NEW PATTERNS (HIGH confidence):
   - VOLUME_BREAKOUT (WR 47.3%, +23.70%)
   - ATR_EXPANSION (WR 60.6%, +3.32%)

Expected Total: ~+433%
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2
from thirty_pip_detector_final_v2 import ThirtyPipDetectorFinalV2
from new_patterns_detector import NewPatternsDetector


class PatternRecognitionV9Ultimate:
    """
    V9 ULTIMATE - All patterns combined
    
    Sources:
    1. BASELINE (320 trades, +374%, WR 63.4%)
    2. 30-PIP (130 trades, +7.71%, WR 70.0%)
    3. NEW_PATTERNS (179 trades, +27.02%, WR 51.4%)
       - VOLUME_BREAKOUT (146 trades)
       - ATR_EXPANSION (33 trades)
    """
    
    def __init__(self,
                 fib_mode='standard',
                 tp_multiplier=1.4,
                 enable_30pip=True,
                 enable_new_patterns=True,
                 high_confidence_only=True,
                 pip_breakeven_trigger=20,
                 pip_trailing_trigger=35):
        
        # Baseline
        self.baseline_strategy = PatternRecognitionOptimizedV2(
            fib_mode=fib_mode,
            tp_multiplier=tp_multiplier,
            long_only=True
        )
        
        # 30-Pip detector
        self.pip_detector = None
        if enable_30pip:
            self.pip_detector = ThirtyPipDetectorFinalV2(
                focus_long_only=True,
                high_confidence_only=high_confidence_only
            )
        
        # New patterns detector
        self.new_detector = None
        if enable_new_patterns:
            self.new_detector = NewPatternsDetector(
                enable_volume_breakout=True,  # BEST
                enable_atr_expansion=True,     # HIGH WR
                enable_momentum_candle=False,  # Skip (low WR)
                focus_long_only=True
            )
        
        self.enable_30pip = enable_30pip
        self.enable_new_patterns = enable_new_patterns
        self.high_confidence_only = high_confidence_only
        self.pip_breakeven_trigger = pip_breakeven_trigger
        self.pip_trailing_trigger = pip_trailing_trigger
        
        self.version = "V9_ULTIMATE"
        self.description = "Baseline + 30-Pip + New Patterns (VOLUME_BREAKOUT + ATR_EXPANSION)"
    
    def run_strategy(self, df):
        """Get all signals from all sources"""
        
        print(f"\n" + "="*100)
        print(f"🎯 {self.version} - Ultimate Combined Strategy")
        print("="*100)
        print(f"   {self.description}")
        
        all_signals = []
        
        # 1. BASELINE
        print(f"\n1️⃣  BASELINE...")
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
        
        print(f"   ✅ {len(baseline_signals)} signals")
        all_signals.append(baseline_signals)
        
        # 2. 30-PIP
        if self.enable_30pip and self.pip_detector is not None:
            print(f"\n2️⃣  30-PIP DETECTOR...")
            
            pip_signals = self.pip_detector.get_signals(df.copy())
            
            print(f"   ✅ {len(pip_signals)} signals")
            
            if len(pip_signals) > 0:
                pip_converted = []
                for idx, signal in pip_signals.iterrows():
                    pip_converted.append({
                        'time': signal['time'],
                        'pattern': signal['pattern'],
                        'type': 'LONG',
                        'entry_price': signal['entry_price'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit'],
                        'source': '30PIP',
                        'detector_pattern': signal['type']
                    })
                
                all_signals.append(pd.DataFrame(pip_converted))
        
        # 3. NEW PATTERNS
        if self.enable_new_patterns and self.new_detector is not None:
            print(f"\n3️⃣  NEW PATTERNS...")
            
            new_signals = self.new_detector.detect_all_patterns(df.copy())
            
            # Filter HIGH confidence only
            if self.high_confidence_only and len(new_signals) > 0:
                new_signals = new_signals[new_signals['confidence'] == 'HIGH'].copy()
            
            print(f"   ✅ {len(new_signals)} signals (HIGH confidence)")
            
            if len(new_signals) > 0:
                new_converted = []
                for idx, signal in new_signals.iterrows():
                    new_converted.append({
                        'time': signal['time'],
                        'pattern': signal['pattern'],
                        'type': 'LONG',
                        'entry_price': signal['entry_price'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit'],
                        'source': 'NEW_PATTERN',
                        'detector_pattern': signal['type']
                    })
                
                all_signals.append(pd.DataFrame(new_converted))
        
        # Combine all
        print(f"\n4️⃣  COMBINING...")
        combined_df = pd.concat(all_signals, ignore_index=True)
        combined_df = combined_df.sort_values('time').reset_index(drop=True)
        
        # Deduplicate by hour (priority: BASELINE > 30PIP > NEW_PATTERN)
        combined_df['hour'] = combined_df['time'].dt.floor('h')
        
        before = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=['hour'], keep='first')
        combined_df = combined_df.drop(columns=['hour'])
        
        print(f"   Before dedup: {before}")
        print(f"   After dedup:  {len(combined_df)}")
        print(f"   Removed:      {before - len(combined_df)}")
        
        # Count by source
        print(f"\n   📊 Final breakdown:")
        for source in ['BASELINE', '30PIP', 'NEW_PATTERN']:
            count = len(combined_df[combined_df['source'] == source])
            if count > 0:
                print(f"      {source:15s}: {count:3d}")
        print(f"      {'TOTAL':<15s}: {len(combined_df):3d}")
        
        return combined_df
    
    def backtest(self, df):
        """Backtest combined strategy"""
        
        print(f"\n" + "="*100)
        print(f"🔍 BACKTESTING {self.version}")
        print("="*100)
        
        signals_df = self.run_strategy(df.copy())
        
        if len(signals_df) == 0:
            return pd.DataFrame()
        
        # Pattern-specific settings for 30-Pip
        pattern_settings_30pip = {
            'MOMENTUM': {'use_partial_tp': True, 'partial_tp_pips': 30, 'partial_tp_size': 0.5, 'sl_multiplier': 0.75},
            'PULLBACK': {'use_partial_tp': False, 'sl_multiplier': 1.0},
            'VOLATILITY': {'use_partial_tp': False, 'sl_multiplier': 1.0},
            'BOUNCE': {'use_partial_tp': True, 'partial_tp_pips': 30, 'partial_tp_size': 0.5, 'sl_multiplier': 0.9},
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
            
            # Get settings
            settings_30pip = pattern_settings_30pip.get(detector_pattern, {}) if source == '30PIP' else {}
            
            stop_loss = original_sl
            if source == '30PIP' and settings_30pip.get('sl_multiplier', 1.0) != 1.0:
                sl_distance = entry_price - original_sl
                stop_loss = entry_price - (sl_distance * settings_30pip['sl_multiplier'])
            
            # BASELINE: Simple
            if source == 'BASELINE':
                hit_tp = False
                hit_sl = False
                exit_price = None
                exit_type = 'TIMEOUT'
                
                for j in range(len(df_future)):
                    candle = df_future.iloc[j]
                    
                    if candle['low'] <= stop_loss:
                        hit_sl = True
                        exit_price = stop_loss
                        exit_type = 'SL'
                        break
                    
                    if candle['high'] >= take_profit:
                        hit_tp = True
                        exit_price = take_profit
                        exit_type = 'TP'
                        break
                
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
                    'pnl_pct': pnl_pct,
                    'exit_type': exit_type,
                    'breakeven_used': False
                })
            
            # 30-PIP or NEW_PATTERN: With breakeven
            else:
                position_size = 1.0
                total_pnl_dollars = 0
                current_sl = stop_loss
                exits = []
                
                partial_tp_price = None
                if source == '30PIP' and settings_30pip.get('use_partial_tp', False):
                    partial_tp_price = entry_price + (settings_30pip['partial_tp_pips'] * 0.10)
                
                breakeven_activated = False
                trailing_activated = False
                
                for j in range(len(df_future)):
                    candle = df_future.iloc[j]
                    
                    if position_size <= 0:
                        break
                    
                    current_profit_dollars = candle['high'] - entry_price
                    current_profit_pips = current_profit_dollars / 0.10
                    
                    # Partial TP (30-Pip only)
                    if (source == '30PIP' and settings_30pip.get('use_partial_tp', False) and 
                        position_size == 1.0 and partial_tp_price is not None and 
                        candle['high'] >= partial_tp_price):
                        
                        partial_pnl = (partial_tp_price - entry_price) * settings_30pip['partial_tp_size']
                        total_pnl_dollars += partial_pnl
                        position_size = 1.0 - settings_30pip['partial_tp_size']
                        
                        exits.append('Partial_TP')
                        current_sl = entry_price
                        breakeven_activated = True
                        continue
                    
                    # Breakeven
                    if not breakeven_activated and current_profit_pips >= self.pip_breakeven_trigger:
                        current_sl = entry_price
                        breakeven_activated = True
                        exits.append(f'BE@{self.pip_breakeven_trigger}p')
                    
                    # Trailing
                    if breakeven_activated and not trailing_activated:
                        if current_profit_pips >= self.pip_trailing_trigger:
                            trailing_activated = True
                            exits.append(f'Trail@{self.pip_trailing_trigger}p')
                    
                    if trailing_activated:
                        profit_above = current_profit_pips - self.pip_trailing_trigger
                        new_trailing = entry_price + ((self.pip_trailing_trigger + profit_above * 0.5) * 0.10)
                        current_sl = max(current_sl, new_trailing)
                    
                    # Check SL
                    if candle['low'] <= current_sl:
                        exit_pnl = (current_sl - entry_price) * position_size
                        total_pnl_dollars += exit_pnl
                        
                        exits.append('Trail_SL' if trailing_activated else ('BE_SL' if breakeven_activated else 'SL'))
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
                    'pnl_pct': pnl_pct,
                    'exit_type': exit_type,
                    'breakeven_used': breakeven_activated
                })
        
        trades_df = pd.DataFrame(trades)
        self._print_results(trades_df)
        
        return trades_df
    
    def _print_results(self, trades_df):
        """Print results"""
        
        print(f"\n" + "="*100)
        print(f"✅ RESULTS - {self.version}")
        print("="*100)
        
        if len(trades_df) == 0:
            return
        
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        win_rate = (wins / total_trades * 100)
        
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
        
        print(f"\n📊 Overall:")
        print(f"   Total PnL:      {total_pnl:+.2f}%  🚀")
        print(f"   Win Rate:       {win_rate:.1f}%")
        print(f"   Trades:         {total_trades}")
        print(f"   Profit Factor:  {profit_factor:.2f}")
        print(f"   Max Drawdown:   {max_drawdown:.2f}%")
        
        # By source
        print(f"\n📊 By Source:")
        for source in ['BASELINE', '30PIP', 'NEW_PATTERN']:
            source_trades = trades_df[trades_df['source'] == source]
            if len(source_trades) > 0:
                source_wins = len(source_trades[source_trades['pnl_pct'] > 0])
                source_wr = (source_wins / len(source_trades) * 100)
                source_pnl = source_trades['pnl_pct'].sum()
                
                be_info = ""
                if source in ['30PIP', 'NEW_PATTERN'] and 'breakeven_used' in source_trades.columns:
                    be_used = len(source_trades[source_trades['breakeven_used'] == True])
                    be_info = f" | BE: {be_used} ({be_used/len(source_trades)*100:.0f}%)"
                
                print(f"   {source:15s}: {len(source_trades):3d} | WR {source_wr:5.1f}% | PnL {source_pnl:+7.2f}%{be_info}")
        
        # New patterns breakdown
        new_trades = trades_df[trades_df['source'] == 'NEW_PATTERN']
        if len(new_trades) > 0:
            print(f"\n📊 New Patterns Detail:")
            for pattern in new_trades['detector_pattern'].unique():
                p_trades = new_trades[new_trades['detector_pattern'] == pattern]
                p_wins = len(p_trades[p_trades['pnl_pct'] > 0])
                p_wr = p_wins / len(p_trades) * 100
                p_pnl = p_trades['pnl_pct'].sum()
                
                print(f"      {pattern:20s}: {len(p_trades):3d} | WR {p_wr:5.1f}% | PnL {p_pnl:+7.2f}%")


def main():
    print("\n" + "="*100)
    print("🚀 PATTERN RECOGNITION V9 ULTIMATE - All Patterns Combined")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Run V9
    strategy = PatternRecognitionV9Ultimate(
        enable_30pip=True,
        enable_new_patterns=True,
        high_confidence_only=True,
        pip_breakeven_trigger=20,
        pip_trailing_trigger=35
    )
    
    trades_df = strategy.backtest(df)
    
    # Save
    trades_df.to_csv('pattern_recognition_v9_ultimate_backtest.csv', index=False)
    print(f"\n💾 Saved: pattern_recognition_v9_ultimate_backtest.csv")
    
    # Compare with V8
    print(f"\n" + "="*100)
    print("📊 V8 vs V9 COMPARISON")
    print("="*100)
    
    try:
        v8 = pd.read_csv('pattern_recognition_v8_final_backtest.csv')
        
        v8_pnl = v8['pnl_pct'].sum()
        v9_pnl = trades_df['pnl_pct'].sum()
        
        v8_wr = len(v8[v8['pnl_pct'] > 0]) / len(v8) * 100
        v9_wr = len(trades_df[trades_df['pnl_pct'] > 0]) / len(trades_df) * 100
        
        print(f"\n{'Metric':<20} {'V8':<15} {'V9':<15} {'Improvement':<15}")
        print("-"*70)
        print(f"{'Total PnL':<20} {v8_pnl:>+13.2f}% {v9_pnl:>+13.2f}% {v9_pnl-v8_pnl:>+13.2f}%")
        print(f"{'Win Rate':<20} {v8_wr:>12.1f}% {v9_wr:>12.1f}% {v9_wr-v8_wr:>+12.1f}%")
        print(f"{'Trades':<20} {len(v8):>13} {len(trades_df):>13} {len(trades_df)-len(v8):>+13}")
        
        improvement_pct = (v9_pnl / v8_pnl - 1) * 100
        print(f"\n💰 V9 Improvement: {v9_pnl - v8_pnl:+.2f}% ({improvement_pct:+.1f}% relative)")
        
    except:
        print("   Could not load V8 for comparison")
    
    print(f"\n" + "="*100)
    print("🏆 V9 ULTIMATE")
    print("="*100)
    print(f"\n💡 Combined Strategy:")
    print(f"   ✅ Baseline V2 (best LONG signals)")
    print(f"   ✅ 30-Pip Patterns (MOMENTUM/PULLBACK/VOLATILITY)")
    print(f"   ✅ NEW: VOLUME_BREAKOUT + ATR_EXPANSION")
    print(f"   ✅ Breakeven @ 20p for 30-Pip & NEW patterns")


if __name__ == "__main__":
    main()
