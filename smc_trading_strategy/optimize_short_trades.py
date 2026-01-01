"""
Целевая оптимизация SHORT сделок

SHORT показывают WR всего 31% против 65.3% для LONG
Нужно либо улучшить SHORT, либо исключить их
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pattern_recognition_strategy import PatternRecognitionStrategy


class ShortOptimizedStrategy(PatternRecognitionStrategy):
    """
    Версия с оптимизированными SHORT сделками
    """
    
    def __init__(self, fib_mode='standard', short_mode='selective'):
        """
        short_mode:
        - 'all' - все SHORT (baseline)
        - 'selective' - только при сильном сигнале (RSI > 40)
        - 'improved' - улучшенные TP/SL для SHORT
        - 'none' - только LONG
        """
        super().__init__(fib_mode=fib_mode)
        self.short_mode = short_mode
        self.name = f"Pattern Recognition (SHORT: {short_mode})"
        
        print(f"\n🔧 SHORT Optimization Mode: {short_mode}")
    
    def run_strategy(self, df):
        """Run strategy with SHORT optimization"""
        
        # Run baseline
        df_strategy = super().run_strategy(df.copy())
        
        # Apply SHORT optimization
        if self.short_mode != 'all':
            df_strategy = self._optimize_short(df_strategy)
        
        return df_strategy
    
    def _optimize_short(self, df):
        """Optimize SHORT signals"""
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        df['rsi'] = rsi
        
        # Calculate ATR for improved mode
        high_low = df['high'] - df['low']
        atr = high_low.rolling(window=14).mean()
        df['atr'] = atr
        
        short_signals_before = len(df[df['signal'] == -1])
        filtered = 0
        modified = 0
        
        for idx in df[df['signal'] == -1].index:
            current_rsi = df.loc[idx, 'rsi']
            current_atr = df.loc[idx, 'atr']
            
            if self.short_mode == 'none':
                # Remove all SHORT
                df.loc[idx, 'signal'] = 0
                df.loc[idx, 'entry_price'] = np.nan
                df.loc[idx, 'stop_loss'] = np.nan
                df.loc[idx, 'take_profit'] = np.nan
                filtered += 1
            
            elif self.short_mode == 'selective':
                # Only strong SHORT signals (RSI > 40)
                if current_rsi < 40:
                    df.loc[idx, 'signal'] = 0
                    df.loc[idx, 'entry_price'] = np.nan
                    df.loc[idx, 'stop_loss'] = np.nan
                    df.loc[idx, 'take_profit'] = np.nan
                    filtered += 1
            
            elif self.short_mode == 'improved':
                # Tighter TP для SHORT (более консервативный)
                entry_price = df.loc[idx, 'entry_price']
                stop_loss = df.loc[idx, 'stop_loss']
                
                # Reduce TP to 1.2 R:R instead of 1.618
                sl_distance = abs(entry_price - stop_loss)
                new_tp = entry_price - (sl_distance * 1.2)
                
                df.loc[idx, 'take_profit'] = new_tp
                modified += 1
        
        short_signals_after = len(df[df['signal'] == -1])
        
        if self.short_mode == 'none':
            print(f"   🚫 All SHORT signals removed ({short_signals_before} → 0)")
        elif self.short_mode == 'selective':
            print(f"   ⚡ SHORT filtered: {short_signals_before} → {short_signals_after} (removed {filtered})")
        elif self.short_mode == 'improved':
            print(f"   📉 SHORT TP modified: {modified} signals (1.618 → 1.2 R:R)")
        
        return df


def simple_backtest(df, strategy):
    """Simple backtest"""
    
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
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
            else:  # SHORT
                if candle['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    break
                elif candle['low'] <= take_profit:
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
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'pnl': pnl,
            'exit_type': exit_type
        })
    
    return trades, total_pnl


def compare_short_modes(df):
    """Сравнение разных режимов SHORT"""
    
    print("\n" + "="*100)
    print("СРАВНЕНИЕ РЕЖИМОВ ОБРАБОТКИ SHORT СДЕЛОК")
    print("="*100)
    
    modes = ['all', 'selective', 'improved', 'none']
    results = []
    
    for mode in modes:
        print(f"\n{'='*100}")
        print(f"📊 Режим: {mode.upper()}")
        print(f"{'='*100}")
        
        strategy = ShortOptimizedStrategy(fib_mode='standard', short_mode=mode)
        
        print("\n🔍 Running backtest...")
        df_strategy = strategy.run_strategy(df.copy())
        df_signals = df_strategy[df_strategy['signal'] != 0]
        
        # Run backtest
        trades, total_pnl = simple_backtest(df, strategy)
        
        # Stats
        long_trades = [t for t in trades if t['direction'] == 'LONG']
        short_trades = [t for t in trades if t['direction'] == 'SHORT']
        
        wins = len([t for t in trades if t['pnl'] > 0])
        wr = wins / len(trades) * 100 if len(trades) > 0 else 0
        
        long_wins = len([t for t in long_trades if t['pnl'] > 0])
        long_wr = long_wins / len(long_trades) * 100 if len(long_trades) > 0 else 0
        
        short_wins = len([t for t in short_trades if t['pnl'] > 0])
        short_wr = short_wins / len(short_trades) * 100 if len(short_trades) > 0 else 0
        
        # Profit Factor
        wins_pnl = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        losses_pnl = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        pf = wins_pnl / losses_pnl if losses_pnl > 0 else 0
        
        print(f"\n📈 Results:")
        print(f"   Total Trades: {len(trades)} (LONG: {len(long_trades)}, SHORT: {len(short_trades)})")
        print(f"   Win Rate: {wr:.1f}% (LONG: {long_wr:.1f}%, SHORT: {short_wr:.1f}%)")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Profit Factor: {pf:.2f}")
        
        results.append({
            'mode': mode,
            'trades': len(trades),
            'long_trades': len(long_trades),
            'short_trades': len(short_trades),
            'win_rate': wr,
            'long_wr': long_wr,
            'short_wr': short_wr,
            'pnl': total_pnl,
            'pf': pf
        })
    
    # Summary table
    print("\n" + "="*100)
    print("📊 ИТОГОВАЯ СРАВНИТЕЛЬНАЯ ТАБЛИЦА")
    print("="*100)
    
    results_df = pd.DataFrame(results)
    
    print(f"\n{'Mode':<15} {'Trades':<10} {'LONG':<8} {'SHORT':<8} {'WR':<10} {'LONG WR':<10} {'SHORT WR':<10} {'PnL':<15} {'PF':<10}")
    print("-" * 100)
    
    for _, row in results_df.iterrows():
        print(f"{row['mode']:<15} {row['trades']:<10} {row['long_trades']:<8} {row['short_trades']:<8} "
              f"{row['win_rate']:>8.1f}% {row['long_wr']:>9.1f}% {row['short_wr']:>10.1f}% "
              f"{row['pnl']:>+13.2f}% {row['pf']:>9.2f}")
    
    print("\n" + "="*100)
    
    # Best mode
    best = results_df.loc[results_df['pnl'].idxmax()]
    
    print(f"\n🏆 ЛУЧШИЙ РЕЖИМ: {best['mode'].upper()}")
    print(f"   Total PnL: {best['pnl']:+.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Profit Factor: {best['pf']:.2f}")
    
    baseline = results_df[results_df['mode'] == 'all'].iloc[0]
    improvement = best['pnl'] - baseline['pnl']
    improvement_pct = (improvement / baseline['pnl']) * 100
    
    if best['mode'] != 'all':
        print(f"\n💰 Улучшение над baseline:")
        print(f"   PnL: {improvement:+.2f}% ({improvement_pct:+.1f}%)")
        print(f"   Win Rate: {best['win_rate'] - baseline['win_rate']:+.1f}%")
    
    print("="*100)
    
    return results_df


def main():
    print("\n" + "="*100)
    print("ОПТИМИЗАЦИЯ SHORT СДЕЛОК")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Compare modes
    results = compare_short_modes(df)
    
    return results


if __name__ == "__main__":
    results = main()
