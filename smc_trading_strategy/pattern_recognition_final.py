"""
Pattern Recognition FINAL - User Choice

Два режима работы:
1. AGGRESSIVE: Без breakeven → Max PnL (+383%)
2. CONSERVATIVE: Breakeven @ 50 pips → High WR (88%), Low DD (-1.72%)

User выбирает режим в зависимости от своего risk tolerance
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pattern_recognition_optimized_v2 import PatternRecognitionOptimizedV2
from thirty_pip_detector_final_v2 import ThirtyPipDetectorFinalV2


class PatternRecognitionFinal:
    """
    Финальная версия стратегии с выбором режима
    
    Modes:
    - 'aggressive': No breakeven, max PnL (+383%), WR 65.6%, DD -7.88%
    - 'conservative': Breakeven @ 50p, high WR (88%), low DD (-1.72%), PnL +324%
    - 'balanced': Breakeven @ 40p, balanced (PnL +301%, WR 89.1%, DD -1.41%)
    """
    
    def __init__(self, 
                 mode='aggressive',
                 fib_mode='standard',
                 tp_multiplier=1.4,
                 enable_30pip_patterns=True,
                 high_confidence_only=True):
        """
        Args:
            mode: 'aggressive', 'conservative', or 'balanced'
        """
        
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
        
        # Mode configuration
        self.mode = mode.lower()
        self.mode_configs = {
            'aggressive': {
                'enable_breakeven': False,
                'breakeven_trigger_pips': 0,
                'lock_profit_pips': 0,
                'expected_pnl': 383.01,
                'expected_wr': 65.6,
                'expected_dd': -7.88,
                'description': 'Max PnL, no breakeven protection'
            },
            'conservative': {
                'enable_breakeven': True,
                'breakeven_trigger_pips': 50,
                'lock_profit_pips': 15,
                'expected_pnl': 323.77,
                'expected_wr': 88.0,
                'expected_dd': -1.72,
                'description': 'High WR, low DD, breakeven @ 50 pips'
            },
            'balanced': {
                'enable_breakeven': True,
                'breakeven_trigger_pips': 40,
                'lock_profit_pips': 10,
                'expected_pnl': 301.17,
                'expected_wr': 89.1,
                'expected_dd': -1.41,
                'description': 'Balanced PnL/WR/DD, breakeven @ 40 pips'
            }
        }
        
        if self.mode not in self.mode_configs:
            raise ValueError(f"Invalid mode: {self.mode}. Choose from: {list(self.mode_configs.keys())}")
        
        self.config = self.mode_configs[self.mode]
        
        # Version info
        self.version = f"FINAL_{self.mode.upper()}"
        self.description = self.config['description']
    
    def run_strategy(self, df):
        """Get all signals"""
        
        print(f"\n" + "="*100)
        print(f"🎯 {self.version} - Combined Strategy")
        print("="*100)
        print(f"   Mode: {self.mode.upper()}")
        print(f"   {self.description}")
        print(f"   Expected: PnL {self.config['expected_pnl']:.2f}%, WR {self.config['expected_wr']:.1f}%, DD {self.config['expected_dd']:.2f}%")
        
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
        Backtest with mode-specific settings
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
                
                # PARTIAL TP (30-Pip patterns only)
                if (source == '30PIP' and 
                    settings.get('use_partial_tp', False) and 
                    position_size == 1.0 and 
                    partial_tp_price is not None and 
                    candle['high'] >= partial_tp_price):
                    
                    partial_pnl = (partial_tp_price - entry_price) * settings['partial_tp_size']
                    total_pnl_dollars += partial_pnl
                    position_size = 1.0 - settings['partial_tp_size']
                    
                    exits.append('Partial_TP')
                    current_sl = entry_price  # Breakeven after Partial TP
                    breakeven_activated = True
                    
                    continue
                
                # BREAKEVEN MANAGEMENT (if enabled in mode)
                if self.config['enable_breakeven'] and not breakeven_activated:
                    if current_profit_pips >= self.config['breakeven_trigger_pips']:
                        current_sl = entry_price
                        breakeven_activated = True
                        exits.append(f'BE@{self.config["breakeven_trigger_pips"]}p')
                
                # PROFIT LOCK
                if self.config['enable_breakeven'] and breakeven_activated and not profit_locked:
                    if current_profit_pips >= 30:
                        current_sl = entry_price + (self.config['lock_profit_pips'] * 0.10)
                        profit_locked = True
                        exits.append(f'Lock@30p')
                
                # TRAILING SL
                if self.config['enable_breakeven'] and profit_locked and not trailing_activated:
                    if current_profit_pips >= 50:
                        trailing_activated = True
                        exits.append('Trail@50p')
                
                if trailing_activated:
                    profit_above_50 = current_profit_pips - 50
                    new_trailing = entry_price + ((50 + profit_above_50 * 0.5) * 0.10)
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
        print(f"   Win Rate:          {win_rate:.1f}%  (Expected: {self.config['expected_wr']:.1f}%)")
        print(f"   ")
        print(f"   Total PnL:         {total_pnl:+.2f}%  (Expected: {self.config['expected_pnl']:.2f}%) ⭐")
        print(f"   Avg Win:           {avg_win:+.3f}%")
        print(f"   Avg Loss:          {avg_loss:+.3f}%")
        print(f"   Profit Factor:     {profit_factor:.2f}")
        print(f"   Max Drawdown:      {max_drawdown:.2f}%  (Expected: {self.config['expected_dd']:.2f}%)")
        
        if self.config['enable_breakeven']:
            breakeven_used = len(trades_df[trades_df['breakeven_used'] == True])
            print(f"\n📊 Breakeven Stats:")
            print(f"   Breakeven used:    {breakeven_used} ({breakeven_used/total_trades*100:.1f}%)")
        
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


def compare_all_modes(df):
    """Compare all three modes"""
    
    print("\n" + "="*100)
    print("📊 COMPARING ALL MODES")
    print("="*100)
    
    results = {}
    
    for mode in ['aggressive', 'balanced', 'conservative']:
        print(f"\n{'='*100}")
        print(f"Testing Mode: {mode.upper()}")
        print(f"{'='*100}")
        
        strategy = PatternRecognitionFinal(
            mode=mode,
            fib_mode='standard',
            tp_multiplier=1.4,
            enable_30pip_patterns=True,
            high_confidence_only=True
        )
        
        trades_df = strategy.backtest(df.copy())
        
        results[mode] = {
            'trades': trades_df,
            'pnl': trades_df['pnl_pct'].sum(),
            'wr': len(trades_df[trades_df['pnl_pct'] > 0]) / len(trades_df) * 100,
            'count': len(trades_df)
        }
        
        # Save
        trades_df.to_csv(f'pattern_recognition_final_{mode}_backtest.csv', index=False)
        print(f"\n💾 Saved: pattern_recognition_final_{mode}_backtest.csv")
    
    # Summary
    print(f"\n" + "="*100)
    print("📊 SUMMARY TABLE")
    print("="*100)
    
    print(f"\n{'Mode':<15} {'Total PnL':<15} {'Win Rate':<12} {'Trades':<10} {'Recommendation':<30}")
    print("-"*90)
    
    for mode, data in results.items():
        rec = ""
        if mode == 'aggressive':
            rec = "Max profit, higher risk"
        elif mode == 'conservative':
            rec = "High WR, low risk"
        elif mode == 'balanced':
            rec = "Best balance"
        
        print(f"{mode.upper():<15} {data['pnl']:>+13.2f}% {data['wr']:>10.1f}% {data['count']:>8} {rec:<30}")
    
    print(f"\n💡 Choose your mode based on risk tolerance:")
    print(f"   • AGGRESSIVE:    Max PnL, accept higher DD")
    print(f"   • BALANCED:      Good PnL + High WR")
    print(f"   • CONSERVATIVE:  Safety first, high WR, low DD")
    
    return results


def main():
    print("\n" + "="*100)
    print("🚀 PATTERN RECOGNITION FINAL - ALL MODES")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Compare all modes
    results = compare_all_modes(df)


if __name__ == "__main__":
    main()
