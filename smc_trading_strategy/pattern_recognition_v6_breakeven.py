"""
Pattern Recognition V6 - WITH BREAKEVEN

Улучшения:
1. Baseline V2 (LONG only, TP=1.4)
2. 30-Pip Detector Final V2 (pattern-specific optimizations)
3. **NEW**: Breakeven после достижения цели для ВСЕХ сигналов

Breakeven Strategy:
- После +15 пипсов прибыли → SL на breakeven
- После +30 пипсов → SL на breakeven + 5 пипсов
- После +50 пипсов → Trailing SL активируется
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2
from thirty_pip_detector_final_v2 import ThirtyPipDetectorFinalV2


class PatternRecognitionV6Breakeven:
    """
    V6 с автоматическим переводом в безубыток
    
    Breakeven rules (для всех сигналов):
    1. Profit >= 15 pips → SL = entry (breakeven)
    2. Profit >= 30 pips → SL = entry + 5 pips (lock small profit)
    3. Profit >= 50 pips → Trailing SL (lock 50% of profit above 50p)
    
    Дополнительно для 30-Pip паттернов:
    - MOMENTUM: Partial TP + aggressive breakeven
    - PULLBACK/VOLATILITY: Только breakeven (без Partial TP)
    """
    
    def __init__(self, 
                 fib_mode='standard',
                 tp_multiplier=1.4,
                 enable_30pip_patterns=True,
                 high_confidence_only=True,
                 enable_breakeven=True,
                 breakeven_trigger_pips=15,
                 lock_profit_pips=5):
        
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
        
        # Breakeven settings
        self.enable_breakeven = enable_breakeven
        self.breakeven_trigger_pips = breakeven_trigger_pips  # 15 pips default
        self.lock_profit_pips = lock_profit_pips  # +5 pips after breakeven
        
        # Version info
        self.version = "V6_Breakeven"
        self.description = "V5 + Breakeven after profit target"
    
    def run_strategy(self, df):
        """Get all signals"""
        
        print(f"\n" + "="*100)
        print(f"🎯 {self.version} - Combined Strategy with Breakeven")
        print("="*100)
        print(f"   {self.description}")
        print(f"   Breakeven: After +{self.breakeven_trigger_pips} pips → SL to entry")
        print(f"   Lock Profit: After +30 pips → SL to entry +{self.lock_profit_pips} pips")
        
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
                
                duplicates_removed = before_dedup - after_dedup
                
                print(f"   Before dedup:  {before_dedup}")
                print(f"   After dedup:   {after_dedup}")
                print(f"   Removed:       {duplicates_removed} (same hour conflicts)")
                
                baseline_count = len(combined_df[combined_df['source'] == 'BASELINE'])
                pip_count = len(combined_df[combined_df['source'] == '30PIP'])
                
                print(f"\n   📊 Final signal breakdown:")
                print(f"      BASELINE: {baseline_count}")
                print(f"      30PIP:    {pip_count}")
                print(f"      TOTAL:    {len(combined_df)}")
        
        return combined_df
    
    def backtest_with_breakeven(self, df):
        """
        Backtest с переводом в безубыток после достижения цели
        """
        
        print(f"\n" + "="*100)
        print(f"🔍 BACKTESTING {self.version} (with Breakeven Management)")
        print("="*100)
        
        signals_df = self.run_strategy(df.copy())
        
        if len(signals_df) == 0:
            print("❌ No signals")
            return pd.DataFrame()
        
        # Pattern-specific settings for 30-Pip (in addition to breakeven)
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
            
            # Get pattern settings (for 30-Pip)
            settings = pattern_settings.get(detector_pattern, {}) if source == '30PIP' else {}
            
            # Adjust SL for 30-Pip patterns
            stop_loss = original_sl
            if source == '30PIP' and settings.get('sl_multiplier', 1.0) != 1.0:
                sl_distance = entry_price - original_sl
                stop_loss = entry_price - (sl_distance * settings['sl_multiplier'])
            
            # Track position
            position_size = 1.0
            total_pnl_dollars = 0
            current_sl = stop_loss
            exits = []
            
            partial_tp_price = None
            if source == '30PIP' and settings.get('use_partial_tp', False):
                partial_tp_price = entry_price + (settings['partial_tp_pips'] * 0.10)
            
            breakeven_activated = False
            profit_locked = False
            trailing_activated = False
            
            max_profit_pips = 0
            
            for j in range(len(df_future)):
                candle = df_future.iloc[j]
                
                if position_size <= 0:
                    break
                
                current_profit_dollars = candle['high'] - entry_price
                current_profit_pips = current_profit_dollars / 0.10
                max_profit_pips = max(max_profit_pips, current_profit_pips)
                
                # PARTIAL TP (only for 30-Pip patterns with this setting)
                if (source == '30PIP' and 
                    settings.get('use_partial_tp', False) and 
                    position_size == 1.0 and 
                    partial_tp_price is not None and 
                    candle['high'] >= partial_tp_price):
                    
                    partial_pnl = (partial_tp_price - entry_price) * settings['partial_tp_size']
                    total_pnl_dollars += partial_pnl
                    position_size = 1.0 - settings['partial_tp_size']
                    
                    exits.append('Partial_TP')
                    
                    # Move to breakeven after Partial TP
                    current_sl = entry_price
                    breakeven_activated = True
                    
                    continue
                
                # BREAKEVEN MANAGEMENT (for ALL signals if enabled)
                if self.enable_breakeven and not breakeven_activated:
                    # Level 1: Profit >= breakeven_trigger_pips → SL to entry
                    if current_profit_pips >= self.breakeven_trigger_pips:
                        current_sl = entry_price
                        breakeven_activated = True
                        exits.append(f'Breakeven@{self.breakeven_trigger_pips}p')
                
                # PROFIT LOCK (for ALL signals)
                if self.enable_breakeven and breakeven_activated and not profit_locked:
                    # Level 2: Profit >= 30 pips → SL to entry + lock_profit_pips
                    if current_profit_pips >= 30:
                        current_sl = entry_price + (self.lock_profit_pips * 0.10)
                        profit_locked = True
                        exits.append(f'Lock_Profit@30p')
                
                # TRAILING SL (for ALL signals with large profit)
                if self.enable_breakeven and profit_locked and not trailing_activated:
                    # Level 3: Profit >= 50 pips → Trailing SL
                    if current_profit_pips >= 50:
                        trailing_activated = True
                        exits.append('Trailing_Start@50p')
                
                # Update trailing SL
                if trailing_activated:
                    # Lock 50% of profit above 50 pips
                    profit_above_50 = current_profit_pips - 50
                    new_trailing = entry_price + ((50 + profit_above_50 * 0.5) * 0.10)
                    current_sl = max(current_sl, new_trailing)
                
                # Check SL
                if candle['low'] <= current_sl:
                    exit_pnl = (current_sl - entry_price) * position_size
                    total_pnl_dollars += exit_pnl
                    
                    if trailing_activated:
                        exits.append('Trailing_SL')
                    elif breakeven_activated:
                        exits.append('Breakeven_SL')
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
                'original_sl': original_sl,
                'final_sl': current_sl,
                'pnl_dollars': total_pnl_dollars,
                'pnl_pct': pnl_pct,
                'max_profit_pips': max_profit_pips,
                'exit_type': exit_type,
                'breakeven_used': breakeven_activated,
                'profit_locked': profit_locked,
                'trailing_used': trailing_activated,
                'hit_tp': 'TP' in exit_type,
                'hit_sl': 'SL' in exit_type
            })
        
        trades_df = pd.DataFrame(trades)
        
        # Print results
        self._print_results(trades_df)
        
        return trades_df
    
    def _print_results(self, trades_df):
        """Print backtest results"""
        
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
        
        # Breakeven stats
        breakeven_used = len(trades_df[trades_df['breakeven_used'] == True])
        profit_locked_count = len(trades_df[trades_df['profit_locked'] == True])
        trailing_used = len(trades_df[trades_df['trailing_used'] == True])
        
        print(f"\n📊 Breakeven Management:")
        print(f"   Breakeven activated:  {breakeven_used} ({breakeven_used/total_trades*100:.1f}%)")
        print(f"   Profit locked:        {profit_locked_count} ({profit_locked_count/total_trades*100:.1f}%)")
        print(f"   Trailing activated:   {trailing_used} ({trailing_used/total_trades*100:.1f}%)")
        
        # Breakeven saves (reached profit but closed near breakeven instead of big loss)
        breakeven_saves = trades_df[
            (trades_df['breakeven_used'] == True) & 
            (trades_df['pnl_pct'] >= -0.1) & 
            (trades_df['pnl_pct'] <= 0.1) &
            (trades_df['max_profit_pips'] >= 15)
        ]
        
        if len(breakeven_saves) > 0:
            potential_losses = (breakeven_saves['original_sl'] - breakeven_saves['entry_price']) / breakeven_saves['entry_price'] * 100
            saved_pct = abs(potential_losses.sum())
            
            print(f"\n   💰 Breakeven SAVES:")
            print(f"      Trades saved:      {len(breakeven_saves)}")
            print(f"      Potential losses:  {saved_pct:.2f}%")
            print(f"      Impact:            Prevented losses! 🎯")
        
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


def compare_with_v5(df):
    """
    Сравнение V6 (с breakeven) vs V5 (без breakeven)
    """
    
    print("\n" + "="*100)
    print("📊 COMPARISON: V5 vs V6")
    print("="*100)
    
    # V5 (без breakeven)
    print("\n1️⃣  V5 - Without Breakeven:")
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
        
        print(f"\n   V5 Results:")
        print(f"   Total PnL: {v5_pnl:+.2f}%")
        print(f"   Trades:    {v5_count}")
        print(f"   Win Rate:  {v5_wr:.1f}%")
        
    except Exception as e:
        print(f"   ❌ Could not load V5: {e}")
        trades_v5 = None
        v5_pnl = 0
        v5_count = 0
        v5_wr = 0
    
    # V6 (с breakeven)
    print("\n2️⃣  V6 - WITH BREAKEVEN MANAGEMENT:")
    
    strategy_v6 = PatternRecognitionV6Breakeven(
        fib_mode='standard',
        tp_multiplier=1.4,
        enable_30pip_patterns=True,
        high_confidence_only=True,
        enable_breakeven=True,
        breakeven_trigger_pips=15,
        lock_profit_pips=5
    )
    
    trades_v6 = strategy_v6.backtest_with_breakeven(df.copy())
    
    if len(trades_v6) > 0:
        v6_pnl = trades_v6['pnl_pct'].sum()
        v6_wr = len(trades_v6[trades_v6['pnl_pct'] > 0]) / len(trades_v6) * 100
        v6_count = len(trades_v6)
        
        if trades_v5 is not None:
            print(f"\n" + "="*100)
            print(f"📊 COMPARISON TABLE")
            print("="*100)
            
            print(f"\n{'Metric':<25} {'V5 (No BE)':<15} {'V6 (With BE)':<15} {'Difference':<15}")
            print("-"*75)
            print(f"{'Total PnL':<25} {v5_pnl:>+13.2f}% {v6_pnl:>+13.2f}% {v6_pnl-v5_pnl:>+13.2f}%")
            print(f"{'Total Trades':<25} {v5_count:>13} {v6_count:>13} {v6_count-v5_count:>+13}")
            print(f"{'Win Rate':<25} {v5_wr:>12.1f}% {v6_wr:>12.1f}% {v6_wr-v5_wr:>+12.1f}%")
            
            improvement = v6_pnl - v5_pnl
            improvement_pct = (v6_pnl / v5_pnl - 1) * 100 if v5_pnl != 0 else 0
            
            print(f"\n💰 V6 Improvement: {improvement:+.2f}% ({improvement_pct:+.1f}% relative)")
            
            # Save
            trades_v6.to_csv('pattern_recognition_v6_breakeven_backtest.csv', index=False)
            print(f"\n💾 Saved: pattern_recognition_v6_breakeven_backtest.csv")
        
        return trades_v6, trades_v5
    
    return trades_v6, trades_v5


def main():
    print("\n" + "="*100)
    print("🚀 PATTERN RECOGNITION V6 - WITH BREAKEVEN")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Compare with V5
    trades_v6, trades_v5 = compare_with_v5(df)
    
    print(f"\n" + "="*100)
    print("🏆 FINAL SUMMARY")
    print("="*100)
    
    if trades_v6 is not None and len(trades_v6) > 0:
        v6_pnl = trades_v6['pnl_pct'].sum()
        v6_wr = len(trades_v6[trades_v6['pnl_pct'] > 0]) / len(trades_v6) * 100
        
        print(f"\n✅ V6 WITH BREAKEVEN Performance:")
        print(f"   Total PnL:  {v6_pnl:+.2f}%")
        print(f"   Win Rate:   {v6_wr:.1f}%")
        print(f"   Trades:     {len(trades_v6)}")
        
        print(f"\n💡 Key Features:")
        print(f"   ✅ Автоматический перевод в безубыток после +15 пипсов")
        print(f"   ✅ Фиксация прибыли +5 пипсов после +30 пипсов")
        print(f"   ✅ Trailing SL после +50 пипсов")
        print(f"   ✅ Pattern-specific optimizations для 30-pip паттернов")


if __name__ == "__main__":
    main()
