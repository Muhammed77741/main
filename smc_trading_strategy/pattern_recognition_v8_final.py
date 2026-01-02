"""
Pattern Recognition V8 FINAL

Оптимизированная версия с Breakeven @ 20 pips для 30-pip паттернов

Изменения от V7:
- Breakeven trigger: 25 → 20 pips
- Trailing trigger: 40 → 35 pips

Results: +381.77% (+8.56% от 30-pip), WR 65.3%
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2
from thirty_pip_detector_final_v2 import ThirtyPipDetectorFinalV2


class PatternRecognitionV8Final:
    """
    V8 FINAL - С оптимизированным Breakeven @ 20 pips
    
    Стратегия:
    - BASELINE: БЕЗ breakeven → Max PnL
    - 30-PIP: Breakeven @ 20 pips, Trailing @ 35 pips
    
    Expected:
    - Total PnL: +381.77%
    - Win Rate: 65.3%
    - 30-Pip: +7.71%, WR 70.0%
    """
    
    def __init__(self, 
                 fib_mode='standard',
                 tp_multiplier=1.4,
                 enable_30pip_patterns=True,
                 high_confidence_only=True,
                 pip_breakeven_trigger=20,   # OPTIMIZED!
                 pip_trailing_trigger=35):    # OPTIMIZED!
        
        self.baseline_strategy = PatternRecognitionOptimizedV2(
            fib_mode=fib_mode,
            tp_multiplier=tp_multiplier,
            long_only=True
        )
        
        self.pip_detector = None
        if enable_30pip_patterns:
            self.pip_detector = ThirtyPipDetectorFinalV2(
                focus_long_only=True,
                high_confidence_only=high_confidence_only
            )
        
        self.enable_30pip = enable_30pip_patterns
        self.high_confidence_only = high_confidence_only
        self.pip_breakeven_trigger = pip_breakeven_trigger
        self.pip_trailing_trigger = pip_trailing_trigger
        
        self.version = "V8_FINAL"
        self.description = f"Baseline (no BE) + 30-Pip (BE @ {pip_breakeven_trigger}p, Trail @ {pip_trailing_trigger}p)"
    
    def run_strategy(self, df):
        """Get all signals"""
        
        print(f"\n" + "="*100)
        print(f"🎯 {self.version} - Optimized Breakeven Strategy")
        print("="*100)
        print(f"   {self.description}")
        
        # Baseline signals
        print(f"\n1️⃣  BASELINE strategy...")
        baseline_df = self.baseline_strategy.run_strategy(df.copy())
        
        # Filter rows with signals
        baseline_signals = baseline_df[baseline_df['signal'] == 1].copy()
        
        if len(baseline_signals) == 0:
            print(f"   ✅ Baseline: 0 signals")
            return pd.DataFrame()
        
        # Add required fields
        baseline_signals['time'] = baseline_signals.index
        
        # Get type from signal_type column
        if 'signal_type' in baseline_signals.columns:
            baseline_signals['type'] = baseline_signals['signal_type'].str.upper()
        else:
            # Fallback: All baseline signals are LONG in V2
            baseline_signals['type'] = 'LONG'
        
        # Select needed columns
        cols_to_keep = ['time', 'type', 'entry_price', 'stop_loss', 'take_profit']
        if 'signal_reason' in baseline_signals.columns:
            cols_to_keep.append('signal_reason')
            baseline_signals = baseline_signals[cols_to_keep].copy()
            baseline_signals = baseline_signals.rename(columns={'signal_reason': 'pattern'})
        else:
            baseline_signals['pattern'] = 'Baseline_Signal'
            baseline_signals = baseline_signals[cols_to_keep + ['pattern']].copy()
        
        baseline_signals['source'] = 'BASELINE'
        baseline_signals['detector_pattern'] = baseline_signals['pattern']
        
        print(f"   ✅ Baseline: {len(baseline_signals)} signals")
        
        combined_df = baseline_signals.copy()
        
        # 30-Pip signals
        if self.enable_30pip and self.pip_detector is not None:
            print(f"\n2️⃣  30-PIP DETECTOR...")
            
            pip_signals = self.pip_detector.get_signals(df.copy())
            
            print(f"   ✅ 30-Pip: {len(pip_signals)} signals")
            
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
                
                print(f"\n3️⃣  Combining...")
                combined_df = pd.concat([baseline_signals, pip_df], ignore_index=True)
                combined_df = combined_df.sort_values('time').reset_index(drop=True)
                
                combined_df['hour'] = combined_df['time'].dt.floor('h')
                before = len(combined_df)
                combined_df = combined_df.drop_duplicates(subset=['hour'], keep='first')
                combined_df = combined_df.drop(columns=['hour'])
                
                baseline_count = len(combined_df[combined_df['source'] == 'BASELINE'])
                pip_count = len(combined_df[combined_df['source'] == '30PIP'])
                
                print(f"   Total:    {len(combined_df)} (BASELINE: {baseline_count}, 30PIP: {pip_count})")
        
        return combined_df
    
    def backtest(self, df):
        """Backtest with optimized breakeven"""
        
        print(f"\n" + "="*100)
        print(f"🔍 BACKTESTING {self.version}")
        print("="*100)
        
        signals_df = self.run_strategy(df.copy())
        
        if len(signals_df) == 0:
            return pd.DataFrame()
        
        pattern_settings = {
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
            
            settings = pattern_settings.get(detector_pattern, {}) if source == '30PIP' else {}
            
            stop_loss = original_sl
            if source == '30PIP' and settings.get('sl_multiplier', 1.0) != 1.0:
                sl_distance = entry_price - original_sl
                stop_loss = entry_price - (sl_distance * settings['sl_multiplier'])
            
            # BASELINE: Simple backtest
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
                    'entry_price': entry_price,
                    'pnl_dollars': pnl_dollars,
                    'pnl_pct': pnl_pct,
                    'exit_type': exit_type,
                    'breakeven_used': False,
                    'hit_tp': hit_tp,
                    'hit_sl': hit_sl
                })
            
            # 30-PIP: With optimized breakeven
            else:
                position_size = 1.0
                total_pnl_dollars = 0
                current_sl = stop_loss
                exits = []
                
                partial_tp_price = None
                if settings.get('use_partial_tp', False):
                    partial_tp_price = entry_price + (settings['partial_tp_pips'] * 0.10)
                
                breakeven_activated = False
                trailing_activated = False
                
                for j in range(len(df_future)):
                    candle = df_future.iloc[j]
                    
                    if position_size <= 0:
                        break
                    
                    current_profit_dollars = candle['high'] - entry_price
                    current_profit_pips = current_profit_dollars / 0.10
                    
                    # Partial TP
                    if (settings.get('use_partial_tp', False) and 
                        position_size == 1.0 and 
                        partial_tp_price is not None and 
                        candle['high'] >= partial_tp_price):
                        
                        partial_pnl = (partial_tp_price - entry_price) * settings['partial_tp_size']
                        total_pnl_dollars += partial_pnl
                        position_size = 1.0 - settings['partial_tp_size']
                        
                        exits.append('Partial_TP')
                        current_sl = entry_price
                        breakeven_activated = True
                        continue
                    
                    # Breakeven @ 20p (OPTIMIZED!)
                    if not breakeven_activated and current_profit_pips >= self.pip_breakeven_trigger:
                        current_sl = entry_price
                        breakeven_activated = True
                        exits.append(f'BE@{self.pip_breakeven_trigger}p')
                    
                    # Trailing @ 35p (OPTIMIZED!)
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
                    'exit_type': exit_type,
                    'breakeven_used': breakeven_activated,
                    'hit_tp': 'TP' in exit_type,
                    'hit_sl': 'SL' in exit_type
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
        print(f"   Total PnL:    {total_pnl:+.2f}%  ⭐")
        print(f"   Win Rate:     {win_rate:.1f}%")
        print(f"   Trades:       {total_trades}")
        print(f"   Profit Factor:{profit_factor:.2f}")
        print(f"   Max DD:       {max_drawdown:.2f}%")
        
        # By source
        print(f"\n📊 By Source:")
        for source in ['BASELINE', '30PIP']:
            source_trades = trades_df[trades_df['source'] == source]
            if len(source_trades) > 0:
                source_wins = len(source_trades[source_trades['pnl_pct'] > 0])
                source_wr = (source_wins / len(source_trades) * 100)
                source_pnl = source_trades['pnl_pct'].sum()
                
                be_info = ""
                if source == '30PIP' and 'breakeven_used' in source_trades.columns:
                    be_used = len(source_trades[source_trades['breakeven_used'] == True])
                    be_info = f" | BE: {be_used} ({be_used/len(source_trades)*100:.0f}%)"
                
                print(f"   {source:10s}: {len(source_trades):3d} | WR {source_wr:5.1f}% | PnL {source_pnl:+7.2f}%{be_info}")


def main():
    print("\n" + "="*100)
    print("🚀 PATTERN RECOGNITION V8 FINAL - Optimized Breakeven @ 20p")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Run strategy
    strategy = PatternRecognitionV8Final(
        pip_breakeven_trigger=20,  # OPTIMIZED
        pip_trailing_trigger=35    # OPTIMIZED
    )
    
    trades_df = strategy.backtest(df)
    
    # Save
    trades_df.to_csv('pattern_recognition_v8_final_backtest.csv', index=False)
    print(f"\n💾 Saved: pattern_recognition_v8_final_backtest.csv")
    
    print(f"\n" + "="*100)
    print("🏆 V8 FINAL")
    print("="*100)
    print(f"\n💡 Optimizations:")
    print(f"   ✅ 30-Pip Breakeven: 25p → 20p")
    print(f"   ✅ 30-Pip Trailing:  40p → 35p")
    print(f"   ✅ Защищено больше сделок")
    print(f"   ✅ Baseline: без изменений (max PnL)")


if __name__ == "__main__":
    main()
