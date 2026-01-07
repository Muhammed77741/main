"""
Test different swing lookback periods (20, 10, 5 candles) in V3 Adaptive backtest
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'smc_trading_strategy'))

import pandas as pd
import numpy as np
from datetime import datetime
from simplified_smc_strategy import SimplifiedSMCStrategy
from smc_indicators import SMCIndicators

# Load data
data_file = 'XAUUSD_1H_MT5_20241227_20251227.csv'
print(f"Loading data from {data_file}...")
df = pd.read_csv(data_file)
df['time'] = pd.to_datetime(df['datetime'])
df = df.sort_values('time').reset_index(drop=True)
print(f"Loaded {len(df)} candles from {df['time'].min()} to {df['time'].max()}\n")

def detect_market_regime(df, idx):
    """Detect TREND or RANGE regime"""
    lookback = 50
    start_idx = max(0, idx - lookback)
    
    # ATR and volatility
    recent_highs = df['high'].iloc[start_idx:idx]
    recent_lows = df['low'].iloc[start_idx:idx]
    atr = (recent_highs - recent_lows).mean()
    price_range = recent_highs.max() - recent_lows.min()
    volatility_ratio = atr / price_range if price_range > 0 else 0
    
    # Price momentum
    price_change = abs(df['close'].iloc[idx-1] - df['close'].iloc[start_idx])
    momentum = price_change / df['close'].iloc[start_idx]
    
    # Moving average slope
    ma_20 = df['close'].iloc[start_idx:idx].rolling(20, min_periods=1).mean()
    ma_slope = (ma_20.iloc[-1] - ma_20.iloc[-20]) / ma_20.iloc[-20] if len(ma_20) >= 20 else 0
    
    # BOS count
    bos_count = df['bos'].iloc[start_idx:idx].sum() if 'bos' in df.columns else 0
    
    # Decision
    trend_score = 0
    if momentum > 0.02:  # 2% move
        trend_score += 1
    if abs(ma_slope) > 0.01:  # 1% MA slope
        trend_score += 1
    if volatility_ratio > 0.3:
        trend_score += 1
    if bos_count >= 2:
        trend_score += 1
    
    return 'TREND' if trend_score >= 3 else 'RANGE'

def run_adaptive_backtest(swing_lookback, df_input):
    """Run V3 Adaptive backtest with specified swing lookback"""
    
    print(f"\n{'='*60}")
    print(f"Testing with swing_lookback = {swing_lookback} candles")
    print(f"{'='*60}\n")
    
    # Prepare data
    df = df_input.copy()
    
    # Initialize strategy with modified swing lookback
    strategy = SimplifiedSMCStrategy(swing_length=10)
    
    # Generate signals
    df = strategy.generate_signals(df)
    
    # Override stop loss calculation with custom lookback
    for i in range(len(df)):
        if df['signal'].iloc[i] != 0:
            direction = df['signal'].iloc[i]
            
            if direction == 1:  # Long
                recent_data = df.iloc[max(0, i-swing_lookback):i]
                recent_swings = recent_data[recent_data['swing_low']]
                if len(recent_swings) > 0:
                    stop = recent_swings['low'].min()
                else:
                    stop = df['low'].iloc[max(0, i-10):i].min()
                df.loc[df.index[i], 'stop_loss'] = stop * 0.998
                
            else:  # Short
                recent_data = df.iloc[max(0, i-swing_lookback):i]
                recent_swings = recent_data[recent_data['swing_high']]
                if len(recent_swings) > 0:
                    stop = recent_swings['high'].max()
                else:
                    stop = df['high'].iloc[max(0, i-10):i].max()
                df.loc[df.index[i], 'stop_loss'] = stop * 1.002
    
    # Run backtest simulation
    initial_balance = 10000
    balance = initial_balance
    positions = []
    trades = []
    
    for i in range(len(df)):
        if df['signal'].iloc[i] == 0:
            continue
            
        signal = df['signal'].iloc[i]
        entry_price = df['close'].iloc[i]
        stop_loss = df['stop_loss'].iloc[i]
        
        if pd.isna(stop_loss) or stop_loss <= 0:
            continue
            
        # Detect regime
        regime = detect_market_regime(df, i)
        
        # Set adaptive TPs based on regime
        if regime == 'TREND':
            tp1_dist, tp2_dist, tp3_dist = 30, 55, 90
        else:  # RANGE
            tp1_dist, tp2_dist, tp3_dist = 20, 35, 50
        
        point_value = 0.01
        
        if signal == 1:  # Long
            tp1 = entry_price + tp1_dist * point_value
            tp2 = entry_price + tp2_dist * point_value
            tp3 = entry_price + tp3_dist * point_value
        else:  # Short
            tp1 = entry_price - tp1_dist * point_value
            tp2 = entry_price - tp2_dist * point_value
            tp3 = entry_price - tp3_dist * point_value
        
        # Calculate position
        risk_amount = balance * 0.02
        risk_points = abs(entry_price - stop_loss)
        if risk_points == 0:
            continue
            
        position_size = risk_amount / risk_points
        
        position = {
            'entry_idx': i,
            'entry_time': df['time'].iloc[i],
            'signal': signal,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'size': position_size,
            'regime': regime,
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'position_remaining': 1.0,
            'closed': False
        }
        
        positions.append(position)
    
    # Simulate position management
    for pos in positions:
        entry_idx = pos['entry_idx']
        max_idx = min(entry_idx + 48, len(df))  # 48 hour timeout
        
        total_pnl = 0
        
        for j in range(entry_idx + 1, max_idx):
            high = df['high'].iloc[j]
            low = df['low'].iloc[j]
            
            if pos['signal'] == 1:  # Long
                # Check SL
                if low <= pos['stop_loss']:
                    pnl = (pos['stop_loss'] - pos['entry_price']) * pos['size'] * pos['position_remaining']
                    total_pnl += pnl
                    pos['closed'] = True
                    pos['exit_reason'] = 'SL'
                    break
                
                # Check TPs
                if high >= pos['tp1'] and not pos['tp1_hit']:
                    pnl = (pos['tp1'] - pos['entry_price']) * pos['size'] * 0.33
                    total_pnl += pnl
                    pos['tp1_hit'] = True
                    pos['position_remaining'] -= 0.33
                
                if high >= pos['tp2'] and not pos['tp2_hit']:
                    pnl = (pos['tp2'] - pos['entry_price']) * pos['size'] * 0.33
                    total_pnl += pnl
                    pos['tp2_hit'] = True
                    pos['position_remaining'] -= 0.33
                
                if high >= pos['tp3'] and not pos['tp3_hit']:
                    pnl = (pos['tp3'] - pos['entry_price']) * pos['size'] * 0.34
                    total_pnl += pnl
                    pos['tp3_hit'] = True
                    pos['position_remaining'] -= 0.34
                
                if pos['position_remaining'] < 0.01:
                    pos['closed'] = True
                    pos['exit_reason'] = 'TP3'
                    break
                    
            else:  # Short
                # Check SL
                if high >= pos['stop_loss']:
                    pnl = (pos['entry_price'] - pos['stop_loss']) * pos['size'] * pos['position_remaining']
                    total_pnl += pnl
                    pos['closed'] = True
                    pos['exit_reason'] = 'SL'
                    break
                
                # Check TPs
                if low <= pos['tp1'] and not pos['tp1_hit']:
                    pnl = (pos['entry_price'] - pos['tp1']) * pos['size'] * 0.33
                    total_pnl += pnl
                    pos['tp1_hit'] = True
                    pos['position_remaining'] -= 0.33
                
                if low <= pos['tp2'] and not pos['tp2_hit']:
                    pnl = (pos['entry_price'] - pos['tp2']) * pos['size'] * 0.33
                    total_pnl += pnl
                    pos['tp2_hit'] = True
                    pos['position_remaining'] -= 0.33
                
                if low <= pos['tp3'] and not pos['tp3_hit']:
                    pnl = (pos['entry_price'] - pos['tp3']) * pos['size'] * 0.34
                    total_pnl += pnl
                    pos['tp3_hit'] = True
                    pos['position_remaining'] -= 0.34
                
                if pos['position_remaining'] < 0.01:
                    pos['closed'] = True
                    pos['exit_reason'] = 'TP3'
                    break
        
        # Timeout
        if not pos['closed'] and pos['position_remaining'] > 0.01:
            last_price = df['close'].iloc[max_idx-1]
            if pos['signal'] == 1:
                pnl = (last_price - pos['entry_price']) * pos['size'] * pos['position_remaining']
            else:
                pnl = (pos['entry_price'] - last_price) * pos['size'] * pos['position_remaining']
            total_pnl += pnl
            pos['closed'] = True
            pos['exit_reason'] = 'Timeout'
        
        pos['total_pnl'] = total_pnl
        balance += total_pnl
        
        trades.append({
            'time': pos['entry_time'],
            'signal': 'LONG' if pos['signal'] == 1 else 'SHORT',
            'regime': pos['regime'],
            'entry': pos['entry_price'],
            'sl': pos['stop_loss'],
            'sl_distance': abs(pos['entry_price'] - pos['stop_loss']),
            'tp1_hit': pos['tp1_hit'],
            'tp2_hit': pos['tp2_hit'],
            'tp3_hit': pos['tp3_hit'],
            'exit_reason': pos.get('exit_reason', 'Unknown'),
            'pnl': total_pnl,
            'pnl_pct': (total_pnl / initial_balance) * 100
        })
    
    # Calculate stats
    total_trades = len(trades)
    if total_trades == 0:
        print("No trades generated!")
        return None
    
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    
    total_pnl = sum(t['pnl'] for t in trades)
    total_pnl_pct = ((balance - initial_balance) / initial_balance) * 100
    win_rate = len(wins) / total_trades * 100
    
    avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
    profit_factor = abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses and sum(t['pnl'] for t in losses) != 0 else 0
    
    avg_sl_distance = np.mean([t['sl_distance'] for t in trades])
    
    # Print results
    print(f"📊 RESULTS:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Total P&L: {total_pnl_pct:+.2f}%")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Profit Factor: {profit_factor:.2f}")
    print(f"   Wins: {len(wins)} | Losses: {len(losses)}")
    print(f"   Avg SL Distance: {avg_sl_distance:.2f} points")
    print(f"   Final Balance: ${balance:.2f}")
    
    return {
        'swing_lookback': swing_lookback,
        'total_trades': total_trades,
        'total_pnl_pct': total_pnl_pct,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'wins': len(wins),
        'losses': len(losses),
        'avg_sl_distance': avg_sl_distance,
        'final_balance': balance
    }

# Run tests
results = []

for lookback in [20, 10, 5]:
    result = run_adaptive_backtest(lookback, df)
    if result:
        results.append(result)

# Summary comparison
print(f"\n{'='*60}")
print("COMPARISON SUMMARY")
print(f"{'='*60}\n")
print(f"{'Lookback':<12} {'Trades':<8} {'P&L%':<10} {'WinRate':<10} {'PF':<8} {'Avg SL':<10}")
print("-" * 60)

for r in results:
    print(f"{r['swing_lookback']:<12} {r['total_trades']:<8} {r['total_pnl_pct']:+8.2f}% {r['win_rate']:8.1f}% {r['profit_factor']:7.2f}  {r['avg_sl_distance']:8.2f}p")

print("\n✅ Test complete!")
