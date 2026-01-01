"""
Сравнительный бэктест разных методов идентификации сигналов

Сравниваем:
1. Pattern Recognition (текущий метод)
2. Liquidity Sweeps
3. Fair Value Gaps (FVG)
4. Market Structure Breaks (BOS)
5. RSI Divergences
6. Supply/Demand Zones
7. Volatility Breakouts
8. Ensemble (комбинация всех)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from advanced_signal_methods import AdvancedSignalDetector
from pattern_recognition_strategy import PatternRecognitionStrategy


class SimpleBacktester:
    """Простой бэктестер для сравнения методов"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.trades = []
    
    def backtest_signals(self, df, signals_df, tp_pips=50, sl_pips=30, timeout_hours=48):
        """
        Простой бэктест на основе сигналов
        
        Args:
            df: DataFrame с ценами
            signals_df: DataFrame с сигналами
            tp_pips: Take Profit в пунктах
            sl_pips: Stop Loss в пунктах
            timeout_hours: таймаут сделки
        """
        trades = []
        
        for idx, signal in signals_df.iterrows():
            signal_idx = signal['index']
            
            if signal_idx >= len(df) - 1:
                continue
            
            entry_price = df['close'].iloc[signal_idx]
            entry_time = df.index[signal_idx]
            direction = signal['signal']
            
            # Определяем TP и SL
            if direction == 'LONG':
                take_profit = entry_price + tp_pips
                stop_loss = entry_price - sl_pips
            else:  # SHORT
                take_profit = entry_price - tp_pips
                stop_loss = entry_price + sl_pips
            
            # Ищем выход
            search_end = entry_time + timedelta(hours=timeout_hours)
            future_data = df[(df.index > entry_time) & (df.index <= search_end)]
            
            if len(future_data) == 0:
                continue
            
            exit_price = None
            exit_type = None
            exit_time = None
            
            for i in range(len(future_data)):
                candle = future_data.iloc[i]
                
                if direction == 'LONG':
                    if candle['low'] <= stop_loss:
                        exit_price = stop_loss
                        exit_type = 'SL'
                        exit_time = future_data.index[i]
                        break
                    elif candle['high'] >= take_profit:
                        exit_price = take_profit
                        exit_type = 'TP'
                        exit_time = future_data.index[i]
                        break
                else:  # SHORT
                    if candle['high'] >= stop_loss:
                        exit_price = stop_loss
                        exit_type = 'SL'
                        exit_time = future_data.index[i]
                        break
                    elif candle['low'] <= take_profit:
                        exit_price = take_profit
                        exit_type = 'TP'
                        exit_time = future_data.index[i]
                        break
            
            # Timeout
            if exit_price is None:
                exit_price = future_data['close'].iloc[-1]
                exit_type = 'TIMEOUT'
                exit_time = future_data.index[-1]
            
            # Calculate PnL
            if direction == 'LONG':
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            
            trades.append({
                'entry_time': entry_time,
                'exit_time': exit_time,
                'direction': direction,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'duration_hours': (exit_time - entry_time).total_seconds() / 3600
            })
        
        return pd.DataFrame(trades)
    
    def calculate_stats(self, trades_df):
        """Рассчитываем статистику"""
        if len(trades_df) == 0:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_dd': 0
            }
        
        wins = trades_df[trades_df['pnl_pct'] > 0]
        losses = trades_df[trades_df['pnl_pct'] <= 0]
        
        total_pnl = trades_df['pnl_pct'].sum()
        win_rate = len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0
        
        avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
        
        gross_profit = wins['pnl_pct'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['pnl_pct'].sum()) if len(losses) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Max Drawdown
        cumulative = trades_df['pnl_pct'].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_dd = drawdown.min() if len(drawdown) > 0 else 0
        
        return {
            'total_trades': len(trades_df),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_dd': max_dd
        }


def compare_all_methods(df):
    """Сравниваем все методы"""
    
    print("\n" + "="*100)
    print("СРАВНИТЕЛЬНЫЙ БЭКТЕСТ МЕТОДОВ ИДЕНТИФИКАЦИИ СИГНАЛОВ")
    print("="*100 + "\n")
    
    detector = AdvancedSignalDetector()
    backtester = SimpleBacktester()
    
    results = []
    
    # ========================================================================
    # 1. Pattern Recognition (baseline)
    # ========================================================================
    print("📊 1. Pattern Recognition (1.618) - Baseline")
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()
    
    pattern_signals = pd.DataFrame({
        'index': range(len(df_signals)),
        'signal': ['LONG' if x == 1 else 'SHORT' for x in df_signals['signal'].values],
        'price': df_signals['entry_price'].values,
        'confidence': 0.8
    })
    pattern_signals['index'] = [df_strategy.index.get_loc(idx) for idx in df_signals.index]
    
    trades = backtester.backtest_signals(df, pattern_signals)
    stats = backtester.calculate_stats(trades)
    stats['method'] = 'Pattern Recognition'
    results.append(stats)
    print(f"   Сигналов: {len(pattern_signals)} | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | PnL: {stats['total_pnl']:+.2f}%")
    
    # ========================================================================
    # 2. Liquidity Sweeps
    # ========================================================================
    print("\n📊 2. Liquidity Sweeps")
    liquidity_signals = detector.detect_liquidity_sweeps(df)
    liquidity_df = pd.DataFrame(liquidity_signals) if liquidity_signals else pd.DataFrame()
    
    if len(liquidity_df) > 0:
        trades = backtester.backtest_signals(df, liquidity_df)
        stats = backtester.calculate_stats(trades)
        stats['method'] = 'Liquidity Sweeps'
        results.append(stats)
        print(f"   Сигналов: {len(liquidity_df)} | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | PnL: {stats['total_pnl']:+.2f}%")
    
    # ========================================================================
    # 3. Fair Value Gaps (FVG)
    # ========================================================================
    print("\n📊 3. Fair Value Gaps (FVG)")
    fvg_signals = detector.detect_order_flow_imbalances(df)
    fvg_df = pd.DataFrame(fvg_signals) if fvg_signals else pd.DataFrame()
    
    if len(fvg_df) > 0:
        trades = backtester.backtest_signals(df, fvg_df)
        stats = backtester.calculate_stats(trades)
        stats['method'] = 'Fair Value Gaps'
        results.append(stats)
        print(f"   Сигналов: {len(fvg_df)} | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | PnL: {stats['total_pnl']:+.2f}%")
    
    # ========================================================================
    # 4. Market Structure Breaks (BOS)
    # ========================================================================
    print("\n📊 4. Market Structure Breaks (BOS)")
    bos_signals = detector.detect_market_structure_breaks(df)
    bos_df = pd.DataFrame(bos_signals) if bos_signals else pd.DataFrame()
    
    if len(bos_df) > 0:
        trades = backtester.backtest_signals(df, bos_df)
        stats = backtester.calculate_stats(trades)
        stats['method'] = 'Market Structure Breaks'
        results.append(stats)
        print(f"   Сигналов: {len(bos_df)} | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | PnL: {stats['total_pnl']:+.2f}%")
    
    # ========================================================================
    # 5. RSI Divergences
    # ========================================================================
    print("\n📊 5. RSI Divergences")
    div_signals = detector.detect_momentum_divergences(df)
    div_df = pd.DataFrame(div_signals) if div_signals else pd.DataFrame()
    
    if len(div_df) > 0:
        trades = backtester.backtest_signals(df, div_df)
        stats = backtester.calculate_stats(trades)
        stats['method'] = 'RSI Divergences'
        results.append(stats)
        print(f"   Сигналов: {len(div_df)} | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | PnL: {stats['total_pnl']:+.2f}%")
    
    # ========================================================================
    # 6. Supply/Demand Zones
    # ========================================================================
    print("\n📊 6. Supply/Demand Zones")
    sd_signals = detector.detect_supply_demand_zones(df)
    sd_df = pd.DataFrame(sd_signals) if sd_signals else pd.DataFrame()
    
    if len(sd_df) > 0:
        trades = backtester.backtest_signals(df, sd_df)
        stats = backtester.calculate_stats(trades)
        stats['method'] = 'Supply/Demand Zones'
        results.append(stats)
        print(f"   Сигналов: {len(sd_df)} | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | PnL: {stats['total_pnl']:+.2f}%")
    
    # ========================================================================
    # 7. Volatility Breakouts
    # ========================================================================
    print("\n📊 7. Volatility Breakouts")
    vol_signals = detector.detect_volatility_breakouts(df)
    vol_df = pd.DataFrame(vol_signals) if vol_signals else pd.DataFrame()
    
    if len(vol_df) > 0:
        trades = backtester.backtest_signals(df, vol_df)
        stats = backtester.calculate_stats(trades)
        stats['method'] = 'Volatility Breakouts'
        results.append(stats)
        print(f"   Сигналов: {len(vol_df)} | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | PnL: {stats['total_pnl']:+.2f}%")
    
    # ========================================================================
    # 8. Ensemble (комбинация с фильтрацией)
    # ========================================================================
    print("\n📊 8. Ensemble (All Methods Combined)")
    all_signals = detector.detect_all_signals(df, methods=['all'])
    ensemble_signals = detector.ensemble_signals(all_signals, min_confidence=0.75, min_confirmations=2)
    
    if len(ensemble_signals) > 0:
        trades = backtester.backtest_signals(df, ensemble_signals)
        stats = backtester.calculate_stats(trades)
        stats['method'] = 'Ensemble (Combined)'
        results.append(stats)
        print(f"   Сигналов: {len(ensemble_signals)} | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | PnL: {stats['total_pnl']:+.2f}%")
    
    # ========================================================================
    # СРАВНИТЕЛЬНАЯ ТАБЛИЦА
    # ========================================================================
    print("\n" + "="*100)
    print("СРАВНИТЕЛЬНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    print("="*100 + "\n")
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('total_pnl', ascending=False)
    
    print(f"{'Метод':<30} {'Trades':<8} {'Wins':<6} {'WR%':<8} {'PnL%':<12} {'Avg Win':<10} {'Avg Loss':<10} {'PF':<8} {'Max DD':<10}")
    print("-" * 100)
    
    for _, row in results_df.iterrows():
        emoji = "🥇" if _ == results_df.index[0] else "🥈" if _ == results_df.index[1] else "🥉" if _ == results_df.index[2] else "  "
        print(f"{emoji} {row['method']:<28} {row['total_trades']:<8} {row['wins']:<6} {row['win_rate']:>6.1f}% "
              f"{row['total_pnl']:>+10.2f}%  {row['avg_win']:>+8.2f}%  {row['avg_loss']:>+8.2f}%  "
              f"{row['profit_factor']:>6.2f}  {row['max_dd']:>+8.2f}%")
    
    # ========================================================================
    # ВЫВОДЫ
    # ========================================================================
    print("\n" + "="*100)
    print("ВЫВОДЫ И РЕКОМЕНДАЦИИ")
    print("="*100 + "\n")
    
    best_method = results_df.iloc[0]
    
    print(f"🥇 ЛУЧШИЙ МЕТОД: {best_method['method']}")
    print(f"   Total PnL: {best_method['total_pnl']:+.2f}%")
    print(f"   Win Rate: {best_method['win_rate']:.1f}%")
    print(f"   Profit Factor: {best_method['profit_factor']:.2f}")
    print(f"   Total Trades: {best_method['total_trades']}")
    
    print(f"\n📊 TOP 3 МЕТОДОВ ПО PnL:")
    for i, (_, row) in enumerate(results_df.head(3).iterrows()):
        print(f"   {i+1}. {row['method']}: {row['total_pnl']:+.2f}% (WR: {row['win_rate']:.1f}%)")
    
    print(f"\n📊 TOP 3 МЕТОДОВ ПО WIN RATE:")
    top_wr = results_df.nlargest(3, 'win_rate')
    for i, (_, row) in enumerate(top_wr.iterrows()):
        print(f"   {i+1}. {row['method']}: {row['win_rate']:.1f}% (PnL: {row['total_pnl']:+.2f}%)")
    
    print(f"\n📊 TOP 3 МЕТОДОВ ПО PROFIT FACTOR:")
    top_pf = results_df.nlargest(3, 'profit_factor')
    for i, (_, row) in enumerate(top_pf.iterrows()):
        print(f"   {i+1}. {row['method']}: PF {row['profit_factor']:.2f} (PnL: {row['total_pnl']:+.2f}%)")
    
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    print(f"   1. Используйте метод '{best_method['method']}' для максимальной прибыльности")
    print(f"   2. Комбинируйте несколько методов для подтверждения сигналов")
    print(f"   3. Ensemble подход дает стабильность через диверсификацию")
    print(f"   4. Рассмотрите гибридный подход: основной + фильтрующий методы")
    
    return results_df


def main():
    # Load data
    print("\n📥 Loading data...")
    df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")
    
    # Compare methods
    results = compare_all_methods(df)
    
    # Save results
    results.to_csv('signal_methods_comparison.csv', index=False)
    print(f"\n💾 Results saved to: signal_methods_comparison.csv")
    
    print("\n" + "="*100)
    print("✅ АНАЛИЗ ЗАВЕРШЕН!")
    print("="*100)


if __name__ == "__main__":
    main()
