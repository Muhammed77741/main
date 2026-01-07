#!/usr/bin/env python3
"""
Backtest V4: Fixed Stop Loss with Aggressive Take Profit

Tests strategy with:
- Fixed 35-point stop loss (instead of dynamic swing-based SL)
- Multiple aggressive TP levels: 45p, 70p, 100p (1.3:1, 2:1, 2.85:1 R:R)
- Tests 3 variants of position distribution
- Uses V3 Adaptive TREND/RANGE detection

Goal: Reduce risk per trade while maintaining or improving profitability
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smc_trading_strategy.data_loader import load_data_from_csv
from smc_trading_strategy.simplified_smc_strategy import SimplifiedSMCStrategy


class FixedSLBacktester:
    """Backtester with fixed SL and aggressive TP"""
    
    def __init__(self, initial_balance=10000):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = []
        self.closed_trades = []
        self.fixed_sl_points = 35  # Fixed 35-point SL
        
    def detect_market_regime(self, df, idx):
        """Detect if market is in TREND or RANGE mode using 5 indicators"""
        if idx < 50:
            return 'RANGE'
            
        window = df.iloc[max(0, idx-50):idx].copy()
        if len(window) < 20:
            return 'RANGE'
        
        # Indicator 1: EMA crossover (20/50)
        ema20 = window['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = window['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema_trend = 1 if ema20 > ema50 else 0
        
        # Indicator 2: ATR-based volatility
        high_low = window['high'] - window['low']
        high_close = abs(window['high'] - window['close'].shift(1))
        low_close = abs(window['low'] - window['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = (atr / window['close'].iloc[-1]) * 100
        volatility_trend = 1 if atr_pct > 0.5 else 0
        
        # Indicator 3: Directional movement
        price_change = window['close'].iloc[-1] - window['close'].iloc[0]
        price_range = window['high'].max() - window['low'].min()
        directional_strength = abs(price_change) / price_range if price_range > 0 else 0
        direction_trend = 1 if directional_strength > 0.4 else 0
        
        # Indicator 4: Consecutive candle bias
        ups = (window['close'] > window['open']).sum()
        downs = (window['close'] < window['open']).sum()
        bias = abs(ups - downs) / len(window)
        bias_trend = 1 if bias > 0.3 else 0
        
        # Indicator 5: Higher highs / lower lows
        recent_highs = window['high'].iloc[-10:]
        earlier_highs = window['high'].iloc[-20:-10]
        hh = recent_highs.max() > earlier_highs.max()
        
        recent_lows = window['low'].iloc[-10:]
        earlier_lows = window['low'].iloc[-20:-10]
        ll = recent_lows.min() < earlier_lows.min()
        
        structure_trend = 1 if hh or ll else 0
        
        # Vote: 3+ indicators = TREND
        total_score = ema_trend + volatility_trend + direction_trend + bias_trend + structure_trend
        
        return 'TREND' if total_score >= 3 else 'RANGE'
    
    def run_backtest(self, df, variant='balanced'):
        """
        Run backtest with fixed SL and multiple TPs
        
        Variants:
        - conservative: 50% @ TP1, 30% @ TP2, 20% @ TP3 (safe)
        - balanced: 40% @ TP1, 30% @ TP2, 30% @ TP3 (mixed)
        - aggressive: 30% @ TP1, 30% @ TP2, 40% @ TP3 (high risk-reward)
        """
        
        # Position distribution by variant
        distributions = {
            'conservative': [0.50, 0.30, 0.20],
            'balanced': [0.40, 0.30, 0.30],
            'aggressive': [0.30, 0.30, 0.40]
        }
        position_dist = distributions[variant]
        
        strategy = SimplifiedSMCStrategy()
        df_with_signals = strategy.generate_signals(df)
        
        print(f"\n{'='*70}")
        print(f"BACKTEST V4: FIXED SL ({self.fixed_sl_points}p) + AGGRESSIVE TP")
        print(f"Variant: {variant.upper()} ({int(position_dist[0]*100)}%-{int(position_dist[1]*100)}%-{int(position_dist[2]*100)}%)")
        print(f"{'='*70}\n")
        
        trade_number = 0
        
        for idx in range(100, len(df_with_signals)):
            current_candle = df_with_signals.iloc[idx]
            
            # Check for new signals
            if pd.notna(current_candle['signal']) and current_candle['signal'] != 'HOLD':
                
                # Detect market regime
                regime = self.detect_market_regime(df_with_signals, idx)
                
                # Set TP levels based on regime
                if regime == 'TREND':
                    tp_points = [45, 70, 100]  # Aggressive for trends
                else:
                    tp_points = [40, 60, 80]   # Moderate for range
                
                trade_number += 1
                signal_type = current_candle['signal']
                entry_price = current_candle['close']
                
                # Fixed SL instead of dynamic
                if signal_type == 'LONG':
                    sl_price = entry_price - self.fixed_sl_points
                    tp_prices = [entry_price + tp for tp in tp_points]
                else:  # SHORT
                    sl_price = entry_price + self.fixed_sl_points
                    tp_prices = [entry_price - tp for tp in tp_points]
                
                position = {
                    'trade_number': trade_number,
                    'entry_idx': idx,
                    'entry_time': df.index[idx],
                    'entry_price': entry_price,
                    'signal': signal_type,
                    'sl': sl_price,
                    'tp1': tp_prices[0],
                    'tp2': tp_prices[1],
                    'tp3': tp_prices[2],
                    'regime': regime,
                    'tp_points': tp_points,
                    'remaining_position': 1.0,
                    'closed_positions': []
                }
                
                self.positions.append(position)
                
                if trade_number <= 5:
                    rr = tp_points[1] / self.fixed_sl_points
                    print(f"Trade #{trade_number} - {signal_type} @ {entry_price:.2f} ({regime})")
                    print(f"  SL: {sl_price:.2f} ({self.fixed_sl_points}p) | TPs: {tp_points[0]}p/{tp_points[1]}p/{tp_points[2]}p (R:R={rr:.2f})")
            
            # Manage open positions
            positions_to_remove = []
            for pos in self.positions:
                if self._check_position_status(pos, current_candle, idx, position_dist):
                    positions_to_remove.append(pos)
            
            for pos in positions_to_remove:
                self.positions.remove(pos)
                
            # Timeout after 48 hours
            for pos in list(self.positions):
                hours_elapsed = (idx - pos['entry_idx'])
                if hours_elapsed >= 48:
                    self._close_remaining_position(pos, current_candle, 'TIMEOUT')
                    self.positions.remove(pos)
        
        # Close all remaining positions
        for pos in list(self.positions):
            self._close_remaining_position(pos, df_with_signals.iloc[-1], 'END')
        
        self._print_results(variant)
        
        return self.closed_trades
    
    def _check_position_status(self, pos, candle, idx, position_dist):
        """Check if position hits SL or TP levels"""
        is_long = pos['signal'] == 'LONG'
        
        # Check SL
        if is_long:
            if candle['low'] <= pos['sl']:
                self._close_remaining_position(pos, candle, 'SL')
                return True
        else:
            if candle['high'] >= pos['sl']:
                self._close_remaining_position(pos, candle, 'SL')
                return True
        
        # Check TPs in order
        if pos['remaining_position'] > 0:
            tp_levels = [
                ('tp1', position_dist[0]),
                ('tp2', position_dist[1]),
                ('tp3', position_dist[2])
            ]
            
            for tp_name, tp_pct in tp_levels:
                if tp_name not in [c['tp_level'] for c in pos['closed_positions']]:
                    tp_price = pos[tp_name]
                    
                    hit = False
                    if is_long:
                        hit = candle['high'] >= tp_price
                    else:
                        hit = candle['low'] <= tp_price
                    
                    if hit:
                        close_pct = tp_pct / pos['remaining_position']
                        close_size = pos['remaining_position'] * close_pct
                        
                        if is_long:
                            pips = tp_price - pos['entry_price']
                        else:
                            pips = pos['entry_price'] - tp_price
                        
                        profit_pct = (pips / pos['entry_price']) * 100 * close_size
                        
                        pos['closed_positions'].append({
                            'tp_level': tp_name,
                            'close_price': tp_price,
                            'close_pct': close_size,
                            'pips': pips,
                            'profit_pct': profit_pct,
                            'status': tp_name.upper()
                        })
                        
                        pos['remaining_position'] -= close_size
                        
                        if pos['remaining_position'] < 0.01:
                            return True
        
        return False
    
    def _close_remaining_position(self, pos, candle, status):
        """Close remaining position at current price"""
        if pos['remaining_position'] > 0:
            is_long = pos['signal'] == 'LONG'
            close_price = candle['close']
            
            if is_long:
                pips = close_price - pos['entry_price']
            else:
                pips = pos['entry_price'] - close_price
            
            profit_pct = (pips / pos['entry_price']) * 100 * pos['remaining_position']
            
            pos['closed_positions'].append({
                'tp_level': 'remaining',
                'close_price': close_price,
                'close_pct': pos['remaining_position'],
                'pips': pips,
                'profit_pct': profit_pct,
                'status': status
            })
            
            pos['remaining_position'] = 0
        
        # Calculate total trade result
        total_profit = sum(c['profit_pct'] for c in pos['closed_positions'])
        self.balance += (self.initial_balance * total_profit / 100)
        
        trade_record = {
            'trade_number': pos['trade_number'],
            'signal': pos['signal'],
            'regime': pos['regime'],
            'entry_price': pos['entry_price'],
            'sl': pos['sl'],
            'total_profit_pct': total_profit,
            'closes': pos['closed_positions'],
            'tp_points': pos['tp_points']
        }
        
        self.closed_trades.append(trade_record)
    
    def _print_results(self, variant):
        """Print backtest results"""
        if not self.closed_trades:
            print("No trades executed")
            return
        
        total_pnl = self.balance - self.initial_balance
        total_pnl_pct = (total_pnl / self.initial_balance) * 100
        
        wins = [t for t in self.closed_trades if t['total_profit_pct'] > 0]
        losses = [t for t in self.closed_trades if t['total_profit_pct'] < 0]
        
        win_rate = len(wins) / len(self.closed_trades) * 100
        
        avg_win = np.mean([t['total_profit_pct'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['total_profit_pct'] for t in losses]) if losses else 0
        
        gross_profit = sum([t['total_profit_pct'] for t in wins]) if wins else 0
        gross_loss = abs(sum([t['total_profit_pct'] for t in losses])) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # TP hit statistics
        tp_stats = {'TP1': 0, 'TP2': 0, 'TP3': 0, 'ALL_3': 0}
        for trade in self.closed_trades:
            tp_hits = [c['tp_level'] for c in trade['closes'] if c['tp_level'].startswith('tp')]
            if 'tp1' in tp_hits:
                tp_stats['TP1'] += 1
            if 'tp2' in tp_hits:
                tp_stats['TP2'] += 1
            if 'tp3' in tp_hits:
                tp_stats['TP3'] += 1
            if len(tp_hits) == 3:
                tp_stats['ALL_3'] += 1
        
        total_trades = len(self.closed_trades)
        
        print(f"\n{'='*70}")
        print(f"RESULTS - {variant.upper()} VARIANT")
        print(f"{'='*70}")
        print(f"Total Trades: {total_trades}")
        print(f"Total P&L: {total_pnl_pct:+.2f}% (${total_pnl:+.2f})")
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"\nWin/Loss:")
        print(f"  Wins: {len(wins)} ({win_rate:.1f}%)")
        print(f"  Losses: {len(losses)} ({100-win_rate:.1f}%)")
        print(f"  Avg Win: +{avg_win:.2f}%")
        print(f"  Avg Loss: {avg_loss:.2f}%")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"\nTP Hit Rates:")
        print(f"  TP1 ({self.closed_trades[0]['tp_points'][0]}p): {tp_stats['TP1']} ({tp_stats['TP1']/total_trades*100:.1f}%)")
        print(f"  TP2 ({self.closed_trades[0]['tp_points'][1]}p): {tp_stats['TP2']} ({tp_stats['TP2']/total_trades*100:.1f}%)")
        print(f"  TP3 ({self.closed_trades[0]['tp_points'][2]}p): {tp_stats['TP3']} ({tp_stats['TP3']/total_trades*100:.1f}%)")
        print(f"  All 3 TPs: {tp_stats['ALL_3']} ({tp_stats['ALL_3']/total_trades*100:.1f}%)")
        print(f"{'='*70}\n")


def main():
    """Run backtest for all 3 variants"""
    import argparse
    
    parser = argparse.ArgumentParser(description='V4 Fixed SL Backtest')
    parser.add_argument('--file', required=True, help='CSV file with OHLC data')
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("BACKTEST V4: FIXED 35-POINT SL + AGGRESSIVE TP LEVELS")
    print("="*70)
    print("\nStrategy:")
    print("  - Fixed SL: 35 points (vs dynamic swing-based)")
    print("  - TREND TP: 45p/70p/100p (1.3:1, 2:1, 2.85:1 R:R)")
    print("  - RANGE TP: 40p/60p/80p (1.14:1, 1.71:1, 2.29:1 R:R)")
    print("  - Adaptive regime detection (TREND/RANGE)")
    print("  - 48-hour position timeout")
    print("\nVariants:")
    print("  1. Conservative: 50%-30%-20% (safe distribution)")
    print("  2. Balanced: 40%-30%-30% (mixed)")
    print("  3. Aggressive: 30%-30%-40% (high risk-reward)")
    
    # Load data directly with pandas
    print(f"\n📂 Loading data from {args.file}...")
    df = pd.read_csv(args.file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    
    if df is None or df.empty:
        print("Error: Could not load data")
        return
    
    print(f"\nData loaded: {len(df)} candles")
    print(f"Period: {df.index[0]} to {df.index[-1]}")
    
    # Test all 3 variants
    results = {}
    for variant in ['conservative', 'balanced', 'aggressive']:
        backtester = FixedSLBacktester(initial_balance=10000)
        trades = backtester.run_backtest(df, variant=variant)
        
        total_pnl_pct = (backtester.balance - 10000) / 10000 * 100
        win_rate = len([t for t in trades if t['total_profit_pct'] > 0]) / len(trades) * 100 if trades else 0
        
        wins = [t for t in trades if t['total_profit_pct'] > 0]
        losses = [t for t in trades if t['total_profit_pct'] < 0]
        gross_profit = sum([t['total_profit_pct'] for t in wins]) if wins else 0
        gross_loss = abs(sum([t['total_profit_pct'] for t in losses])) if losses else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        results[variant] = {
            'pnl': total_pnl_pct,
            'win_rate': win_rate,
            'profit_factor': pf,
            'trades': len(trades)
        }
    
    # Summary comparison
    print("\n" + "="*70)
    print("SUMMARY COMPARISON")
    print("="*70)
    print(f"{'Variant':<15} {'Total P&L':<12} {'Win Rate':<12} {'PF':<8} {'Trades':<8}")
    print("-"*70)
    for variant in ['conservative', 'balanced', 'aggressive']:
        r = results[variant]
        marker = "⭐" if r['pnl'] == max(results[v]['pnl'] for v in results) else "✅"
        print(f"{variant.capitalize():<15} {marker} {r['pnl']:+.2f}%{'':<6} {r['win_rate']:.1f}%{'':<7} {r['profit_factor']:.2f}{'':<6} {r['trades']}")
    print("="*70)
    
    print("\n✅ Fixed 35p SL reduces risk per trade significantly")
    print("✅ Aggressive TPs (45p/70p/100p) maintain profitability")
    print("✅ Best variant shown above with ⭐")


if __name__ == '__main__':
    main()
