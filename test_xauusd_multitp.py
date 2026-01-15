#!/usr/bin/env python3
"""
Test Multi TP Levels on XAUUSD Data
Tests the signal analysis with multi TP levels on historical XAUUSD data
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# Add trading_bots to path
sys.path.insert(0, str(Path(__file__).parent / 'trading_bots'))

from shared.pattern_recognition_strategy import PatternRecognitionStrategy

# TP/SL Configuration for XAUUSD (from signal_analysis_dialog.py)
XAUUSD_TREND_TP = {'tp1': 30, 'tp2': 55, 'tp3': 90}
XAUUSD_RANGE_TP = {'tp1': 20, 'tp2': 35, 'tp3': 50}
XAUUSD_TREND_SL = 16
XAUUSD_RANGE_SL = 12

# Regime Detection Constants
REGIME_LOOKBACK = 100
REGIME_STRUCTURAL_WINDOW = 20
REGIME_STRUCTURAL_THRESHOLD = 12
REGIME_TREND_SIGNALS_REQUIRED = 3


def detect_market_regime(full_df, signal_idx, lookback=REGIME_LOOKBACK):
    """
    Detect market regime at signal time: TREND or RANGE
    Uses same logic as signal_analysis_dialog.py
    """
    # Get data up to and including signal candle
    signal_pos = full_df.index.get_loc(signal_idx)
    start_pos = max(0, signal_pos - lookback + 1)
    recent_data = full_df.iloc[start_pos:signal_pos + 1]

    if len(recent_data) < REGIME_LOOKBACK:
        return 'RANGE'

    # 1. EMA CROSSOVER
    closes = recent_data['close']
    ema_fast = closes.ewm(span=20, adjust=False).mean()
    ema_slow = closes.ewm(span=50, adjust=False).mean()

    current_fast = ema_fast.iloc[-1]
    current_slow = ema_slow.iloc[-1]

    ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
    ema_trend = ema_diff_pct > 0.5

    # 2. ATR (volatility)
    high_low = recent_data['high'] - recent_data['low']
    atr = high_low.rolling(window=14).mean().iloc[-1]
    avg_atr = high_low.rolling(window=14).mean().mean()

    high_volatility = atr > avg_atr * 1.05

    # 3. Directional movement
    price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
    price_range = recent_data['high'].max() - recent_data['low'].min()

    directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
    strong_direction = directional_move_pct > 0.35

    # 4. Consecutive movements
    closes_arr = recent_data['close'].values
    up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
    down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
    total_moves = up_moves + down_moves

    trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
    directional_bias = trend_strength > 0.15

    # 5. Structural trend
    highs = recent_data['high'].values[-REGIME_STRUCTURAL_WINDOW:]
    lows = recent_data['low'].values[-REGIME_STRUCTURAL_WINDOW:]

    higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
    lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])

    structural_trend = (higher_highs > REGIME_STRUCTURAL_THRESHOLD) or (lower_lows > REGIME_STRUCTURAL_THRESHOLD)

    # Count trend signals
    trend_signals = sum([ema_trend, high_volatility, strong_direction, directional_bias, structural_trend])

    # Need 3+ signals for TREND
    return 'TREND' if trend_signals >= REGIME_TREND_SIGNALS_REQUIRED else 'RANGE'


def calculate_multi_tp_outcome(signal_type, entry_price, stop_loss, tp1, tp2, tp3, future_candles):
    """
    Calculate outcome with multiple TP levels
    TP1: close 50%, TP2: close 30%, TP3: close 20%
    SL moves to breakeven after TP1
    """
    remaining_position = 1.0
    total_pnl_pct = 0.0
    tps_hit = []
    outcome = 'Timeout'
    bars = 0

    tp1_hit = False
    tp2_hit = False
    tp3_hit = False

    # Check each candle
    for future_idx, future_candle in future_candles.iterrows():
        bars += 1

        if signal_type == 1:  # BUY signal
            # Check SL first
            if future_candle['low'] <= stop_loss:
                pnl = ((stop_loss - entry_price) / entry_price) * 100
                total_pnl_pct += pnl * remaining_position
                outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                break

            # Check TP levels in order
            if not tp1_hit and future_candle['high'] >= tp1:
                pnl = ((tp1 - entry_price) / entry_price) * 100
                total_pnl_pct += pnl * 0.5
                remaining_position -= 0.5
                tps_hit.append('TP1')
                tp1_hit = True
                stop_loss = entry_price  # Move SL to breakeven

            if tp1_hit and not tp2_hit and future_candle['high'] >= tp2:
                pnl = ((tp2 - entry_price) / entry_price) * 100
                total_pnl_pct += pnl * 0.3
                remaining_position -= 0.3
                tps_hit.append('TP2')
                tp2_hit = True

            if tp2_hit and not tp3_hit and future_candle['high'] >= tp3:
                pnl = ((tp3 - entry_price) / entry_price) * 100
                total_pnl_pct += pnl * 0.2
                remaining_position -= 0.2
                tps_hit.append('TP3')
                tp3_hit = True
                outcome = 'Full Win 🎯'
                break

        else:  # SELL signal
            # Check SL first
            if future_candle['high'] >= stop_loss:
                pnl = ((entry_price - stop_loss) / entry_price) * 100
                total_pnl_pct += pnl * remaining_position
                outcome = 'Loss ❌' if not tp1_hit else 'Partial Win ✅'
                break

            # Check TP levels in order
            if not tp1_hit and future_candle['low'] <= tp1:
                pnl = ((entry_price - tp1) / entry_price) * 100
                total_pnl_pct += pnl * 0.5
                remaining_position -= 0.5
                tps_hit.append('TP1')
                tp1_hit = True
                stop_loss = entry_price  # Move SL to breakeven

            if tp1_hit and not tp2_hit and future_candle['low'] <= tp2:
                pnl = ((entry_price - tp2) / entry_price) * 100
                total_pnl_pct += pnl * 0.3
                remaining_position -= 0.3
                tps_hit.append('TP2')
                tp2_hit = True

            if tp2_hit and not tp3_hit and future_candle['low'] <= tp3:
                pnl = ((entry_price - tp3) / entry_price) * 100
                total_pnl_pct += pnl * 0.2
                remaining_position -= 0.2
                tps_hit.append('TP3')
                tp3_hit = True
                outcome = 'Full Win 🎯'
                break

        # Timeout after 100 bars
        if bars >= 100:
            if tp1_hit:
                outcome = 'Partial Win ✅'
            break

    return {
        'outcome': outcome,
        'profit_pct': total_pnl_pct,
        'bars': bars,
        'tp_levels_hit': ', '.join(tps_hit) if tps_hit else 'None'
    }


def main():
    print("="*80)
    print("🧪 TESTING MULTI TP LEVELS ON XAUUSD DATA")
    print("="*80)

    # Load data
    csv_file = 'XAUUSD_1H_MT5_20241227_20251227.csv'
    print(f"\n📊 Loading data from: {csv_file}")

    # Load CSV - note there are extra columns in the file
    df = pd.read_csv(csv_file, usecols=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    print(f"✅ Loaded {len(df)} candles")

    # Parse datetime
    df['datetime'] = pd.to_datetime(df['datetime'], format='%Y.%m.%d %H:%M')
    df.set_index('datetime', inplace=True)

    # Show date range
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    print(f"   Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")

    # Initialize strategy
    print(f"\n🔍 Running PatternRecognitionStrategy...")
    strategy = PatternRecognitionStrategy(fib_mode='standard')
    df_signals = strategy.run_strategy(df)

    # Find signals
    signals_df = df_signals[df_signals['signal'] != 0].copy()
    print(f"✅ Found {len(signals_df)} signals")

    # Add regime column
    signals_df['regime'] = 'N/A'
    signals_df['tp1_price'] = 0.0
    signals_df['tp2_price'] = 0.0
    signals_df['tp3_price'] = 0.0
    signals_df['sl_price'] = 0.0
    signals_df['outcome'] = ''
    signals_df['profit_pct'] = 0.0
    signals_df['bars_held'] = 0
    signals_df['tp_levels_hit'] = ''

    # Calculate outcomes for each signal
    print(f"\n📊 Calculating outcomes with Multi TP levels...")

    for idx, signal_row in signals_df.iterrows():
        signal_type = signal_row['signal']
        entry_price = signal_row['close']

        # Detect market regime
        regime = detect_market_regime(df_signals, idx)
        signals_df.loc[idx, 'regime'] = regime

        # Get TP configuration based on regime
        if regime == 'TREND':
            tp_config = XAUUSD_TREND_TP
            sl_value = XAUUSD_TREND_SL
        else:
            tp_config = XAUUSD_RANGE_TP
            sl_value = XAUUSD_RANGE_SL

        # Calculate TP and SL prices
        if signal_type == 1:  # BUY
            tp1 = entry_price + tp_config['tp1']
            tp2 = entry_price + tp_config['tp2']
            tp3 = entry_price + tp_config['tp3']
            stop_loss = entry_price - sl_value
        else:  # SELL
            tp1 = entry_price - tp_config['tp1']
            tp2 = entry_price - tp_config['tp2']
            tp3 = entry_price - tp_config['tp3']
            stop_loss = entry_price + sl_value

        signals_df.loc[idx, 'tp1_price'] = tp1
        signals_df.loc[idx, 'tp2_price'] = tp2
        signals_df.loc[idx, 'tp3_price'] = tp3
        signals_df.loc[idx, 'sl_price'] = stop_loss

        # Get future candles
        future_candles = df_signals[df_signals.index > idx]

        if len(future_candles) > 0:
            result = calculate_multi_tp_outcome(
                signal_type, entry_price, stop_loss, tp1, tp2, tp3, future_candles
            )
            signals_df.loc[idx, 'outcome'] = result['outcome']
            signals_df.loc[idx, 'profit_pct'] = result['profit_pct']
            signals_df.loc[idx, 'bars_held'] = result['bars']
            signals_df.loc[idx, 'tp_levels_hit'] = result['tp_levels_hit']

    # Print summary statistics
    print(f"\n{'='*80}")
    print("📊 RESULTS SUMMARY")
    print(f"{'='*80}")

    total_signals = len(signals_df)
    trend_signals = len(signals_df[signals_df['regime'] == 'TREND'])
    range_signals = len(signals_df[signals_df['regime'] == 'RANGE'])

    print(f"\n🔢 Signal Distribution:")
    print(f"   Total signals: {total_signals}")
    print(f"   TREND regime: {trend_signals} ({trend_signals/total_signals*100:.1f}%)")
    print(f"   RANGE regime: {range_signals} ({range_signals/total_signals*100:.1f}%)")

    # Outcome statistics
    full_wins = len(signals_df[signals_df['outcome'] == 'Full Win 🎯'])
    partial_wins = len(signals_df[signals_df['outcome'] == 'Partial Win ✅'])
    losses = len(signals_df[signals_df['outcome'] == 'Loss ❌'])
    timeouts = len(signals_df[signals_df['outcome'] == 'Timeout'])

    print(f"\n🎯 Outcomes:")
    print(f"   Full Win (TP3):    {full_wins} ({full_wins/total_signals*100:.1f}%)")
    print(f"   Partial Win:       {partial_wins} ({partial_wins/total_signals*100:.1f}%)")
    print(f"   Loss:              {losses} ({losses/total_signals*100:.1f}%)")
    print(f"   Timeout:           {timeouts} ({timeouts/total_signals*100:.1f}%)")

    # Win rate
    wins = full_wins + partial_wins
    win_rate = wins / total_signals * 100 if total_signals > 0 else 0
    print(f"\n   Win Rate: {win_rate:.1f}%")

    # TP hits statistics
    tp1_hits = len(signals_df[signals_df['tp_levels_hit'].str.contains('TP1', na=False)])
    tp2_hits = len(signals_df[signals_df['tp_levels_hit'].str.contains('TP2', na=False)])
    tp3_hits = len(signals_df[signals_df['tp_levels_hit'].str.contains('TP3', na=False)])

    print(f"\n📍 TP Levels Hit:")
    print(f"   TP1: {tp1_hits} ({tp1_hits/total_signals*100:.1f}%)")
    print(f"   TP2: {tp2_hits} ({tp2_hits/total_signals*100:.1f}%)")
    print(f"   TP3: {tp3_hits} ({tp3_hits/total_signals*100:.1f}%)")

    # Profit statistics
    total_profit_pct = signals_df['profit_pct'].sum()
    avg_profit_pct = signals_df['profit_pct'].mean()
    winning_trades = signals_df[signals_df['profit_pct'] > 0]
    losing_trades = signals_df[signals_df['profit_pct'] < 0]

    avg_win = winning_trades['profit_pct'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['profit_pct'].mean() if len(losing_trades) > 0 else 0

    print(f"\n💰 Profit Statistics:")
    print(f"   Total Profit: {total_profit_pct:.2f}%")
    print(f"   Average Profit per Trade: {avg_profit_pct:.2f}%")
    print(f"   Average Win: {avg_win:.2f}%")
    print(f"   Average Loss: {avg_loss:.2f}%")
    if avg_loss != 0:
        print(f"   Profit Factor: {abs(avg_win/avg_loss):.2f}")

    # Average bars held
    avg_bars = signals_df['bars_held'].mean()
    print(f"\n⏱️  Average Hold Time: {avg_bars:.1f} bars ({avg_bars:.1f} hours)")

    # Show first 10 trades
    print(f"\n{'='*80}")
    print("📋 FIRST 10 TRADES (Detailed View)")
    print(f"{'='*80}\n")

    for i, (idx, row) in enumerate(signals_df.head(10).iterrows(), 1):
        signal_type = 'BUY 📈' if row['signal'] == 1 else 'SELL 📉'
        print(f"Trade #{i} - {idx.strftime('%Y-%m-%d %H:%M')} - {signal_type}")
        print(f"   Regime: {row['regime']}")
        print(f"   Entry: ${row['close']:.2f}")
        print(f"   SL:    ${row['sl_price']:.2f}")
        print(f"   TP1:   ${row['tp1_price']:.2f}")
        print(f"   TP2:   ${row['tp2_price']:.2f}")
        print(f"   TP3:   ${row['tp3_price']:.2f}")
        print(f"   Outcome: {row['outcome']}")
        print(f"   TP Hits: {row['tp_levels_hit']}")
        print(f"   Profit: {row['profit_pct']:.2f}%")
        print(f"   Bars Held: {row['bars_held']}")
        print()

    # Save results to CSV
    output_file = 'xauusd_multitp_test_results.csv'
    signals_df.to_csv(output_file)
    print(f"💾 Results saved to: {output_file}")

    print(f"\n{'='*80}")
    print("✅ TEST COMPLETE")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
