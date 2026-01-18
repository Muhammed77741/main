"""
Analyze losing trades from Original Strategy
Find patterns in losses to improve the strategy
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy
from intraday_gold_data import generate_intraday_gold_data


def analyze_losing_trades():
    """
    Deep analysis of losing trades
    """
    print("\n" + "="*80)
    print("🔍 ANALYZING LOSING TRADES - Finding Patterns")
    print("="*80)

    # Generate data
    total_days = 11 * 30
    df = generate_intraday_gold_data(days=total_days, timeframe='1H')
    start_date = datetime(2025, 1, 1)
    df.index = pd.date_range(start=start_date, periods=len(df), freq='1h')
    df = df[df.index.dayofweek < 5]
    df = df[(df.index >= '2025-01-01') & (df.index < '2025-12-01')]

    # Run strategy
    strategy = MultiSignalGoldStrategy()
    df_result = strategy.run_strategy(df)

    # Backtest and collect detailed trade info
    trades = []

    for i in range(len(df_result)):
        if df_result['signal'].iloc[i] == 0:
            continue

        entry_price = df_result['entry_price'].iloc[i]
        stop_loss = df_result['stop_loss'].iloc[i]
        take_profit = df_result['take_profit'].iloc[i]
        direction = df_result['signal'].iloc[i]
        signal_type = df_result['signal_type'].iloc[i] if 'signal_type' in df_result.columns else 'unknown'
        entry_time = df_result.index[i]

        if pd.isna(entry_price) or pd.isna(stop_loss):
            continue

        # Look ahead for exit
        for j in range(i+1, min(i+49, len(df_result))):
            exit_price = None
            exit_reason = None

            if direction == 1:  # Long
                if df_result['low'].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                elif df_result['high'].iloc[j] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
            else:  # Short
                if df_result['high'].iloc[j] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                elif df_result['low'].iloc[j] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'

            if exit_price:
                # Calculate PnL
                if direction == 1:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100

                # Additional info
                entry_hour = entry_time.hour
                entry_day = entry_time.dayofweek  # 0=Mon, 4=Fri

                # Market conditions at entry
                recent_volatility = df_result['close'].iloc[max(0, i-20):i].std() / df_result['close'].iloc[i] * 100
                volume_ratio = df_result['volume'].iloc[i] / df_result['volume'].iloc[max(0, i-10):i].mean() if i >= 10 else 1.0

                # Trend context
                sma20 = df_result['close'].iloc[max(0, i-20):i].mean() if i >= 20 else entry_price
                trend = 'up' if entry_price > sma20 else 'down' if entry_price < sma20 else 'neutral'

                trades.append({
                    'entry_time': entry_time,
                    'exit_time': df_result.index[j],
                    'direction': 'LONG' if direction == 1 else 'SHORT',
                    'signal_type': signal_type,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'entry_hour': entry_hour,
                    'entry_day': entry_day,
                    'volatility': recent_volatility,
                    'volume_ratio': volume_ratio,
                    'trend': trend,
                    'entry_price': entry_price
                })
                break

    # Split into winners and losers
    winners = [t for t in trades if t['pnl_pct'] > 0]
    losers = [t for t in trades if t['pnl_pct'] <= 0]

    print(f"\nTotal Trades: {len(trades)}")
    print(f"Winners: {len(winners)} ({len(winners)/len(trades)*100:.1f}%)")
    print(f"Losers: {len(losers)} ({len(losers)/len(trades)*100:.1f}%)")

    # Analyze losers by various factors
    print("\n" + "="*80)
    print("📉 LOSING TRADES ANALYSIS")
    print("="*80)

    # 1. By Hour
    print("\n1️⃣ Loss Rate by Entry Hour:")
    hour_stats = {}
    for h in range(24):
        hour_trades = [t for t in trades if t['entry_hour'] == h]
        if len(hour_trades) > 5:  # Only show hours with enough data
            hour_losers = [t for t in hour_trades if t['pnl_pct'] <= 0]
            loss_rate = len(hour_losers) / len(hour_trades) * 100
            avg_loss = np.mean([t['pnl_pct'] for t in hour_losers]) if hour_losers else 0
            hour_stats[h] = {'loss_rate': loss_rate, 'avg_loss': avg_loss, 'count': len(hour_trades)}

    for h in sorted(hour_stats.keys(), key=lambda x: hour_stats[x]['loss_rate'], reverse=True)[:5]:
        stats = hour_stats[h]
        print(f"   Hour {h:02d}: {stats['loss_rate']:5.1f}% loss rate | Avg loss: {stats['avg_loss']:+.2f}% | {stats['count']} trades")

    # 2. By Day of Week
    print("\n2️⃣ Loss Rate by Day of Week:")
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for d in range(5):
        day_trades = [t for t in trades if t['entry_day'] == d]
        if day_trades:
            day_losers = [t for t in day_trades if t['pnl_pct'] <= 0]
            loss_rate = len(day_losers) / len(day_trades) * 100
            avg_loss = np.mean([t['pnl_pct'] for t in day_losers]) if day_losers else 0
            print(f"   {days[d]:10s}: {loss_rate:5.1f}% loss rate | Avg loss: {avg_loss:+.2f}% | {len(day_trades)} trades")

    # 3. By Volatility
    print("\n3️⃣ Loss Rate by Volatility:")
    vol_low = [t for t in trades if t['volatility'] < 0.8]
    vol_med = [t for t in trades if 0.8 <= t['volatility'] < 1.5]
    vol_high = [t for t in trades if t['volatility'] >= 1.5]

    for name, vol_trades in [('Low (<0.8%)', vol_low), ('Medium (0.8-1.5%)', vol_med), ('High (>1.5%)', vol_high)]:
        if vol_trades:
            vol_losers = [t for t in vol_trades if t['pnl_pct'] <= 0]
            loss_rate = len(vol_losers) / len(vol_trades) * 100
            print(f"   {name:20s}: {loss_rate:5.1f}% loss rate | {len(vol_trades)} trades")

    # 4. By Volume Ratio
    print("\n4️⃣ Loss Rate by Volume Ratio:")
    vol_ratio_low = [t for t in trades if t['volume_ratio'] < 0.8]
    vol_ratio_med = [t for t in trades if 0.8 <= t['volume_ratio'] < 1.3]
    vol_ratio_high = [t for t in trades if t['volume_ratio'] >= 1.3]

    for name, vr_trades in [('Low (<0.8)', vol_ratio_low), ('Medium (0.8-1.3)', vol_ratio_med), ('High (>1.3)', vol_ratio_high)]:
        if vr_trades:
            vr_losers = [t for t in vr_trades if t['pnl_pct'] <= 0]
            loss_rate = len(vr_losers) / len(vr_trades) * 100
            print(f"   {name:20s}: {loss_rate:5.1f}% loss rate | {len(vr_trades)} trades")

    # 5. By Trend Alignment
    print("\n5️⃣ Loss Rate by Trend Alignment:")
    for trend in ['up', 'down', 'neutral']:
        trend_trades = [t for t in trades if t['trend'] == trend]
        if trend_trades:
            # For longs in uptrend and shorts in downtrend
            aligned = [t for t in trend_trades if
                      (t['direction'] == 'LONG' and trend == 'up') or
                      (t['direction'] == 'SHORT' and trend == 'down')]

            counter = [t for t in trend_trades if
                      (t['direction'] == 'LONG' and trend == 'down') or
                      (t['direction'] == 'SHORT' and trend == 'up')]

            if aligned:
                aligned_losers = [t for t in aligned if t['pnl_pct'] <= 0]
                loss_rate = len(aligned_losers) / len(aligned) * 100
                print(f"   Aligned with {trend:7s}: {loss_rate:5.1f}% loss rate | {len(aligned)} trades")

            if counter:
                counter_losers = [t for t in counter if t['pnl_pct'] <= 0]
                loss_rate = len(counter_losers) / len(counter) * 100
                print(f"   Counter {trend:7s}     : {loss_rate:5.1f}% loss rate | {len(counter)} trades")

    # 6. By Signal Type
    print("\n6️⃣ Loss Rate by Signal Type:")
    signal_types = {}
    for t in trades:
        st = str(t['signal_type'])
        if st not in signal_types:
            signal_types[st] = []
        signal_types[st].append(t)

    for st in sorted(signal_types.keys(), key=lambda x: len([t for t in signal_types[x] if t['pnl_pct'] <= 0]) / len(signal_types[x]), reverse=True):
        st_trades = signal_types[st]
        st_losers = [t for t in st_trades if t['pnl_pct'] <= 0]
        if len(st_trades) > 5:
            loss_rate = len(st_losers) / len(st_trades) * 100
            avg_loss = np.mean([t['pnl_pct'] for t in st_losers]) if st_losers else 0
            print(f"   {st:20s}: {loss_rate:5.1f}% loss rate | {len(st_trades)} trades")

    # Generate recommendations
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS FOR IMPROVEMENT")
    print("="*80)

    recommendations = []

    # Check worst hours
    worst_hours = sorted(hour_stats.items(), key=lambda x: x[1]['loss_rate'], reverse=True)[:3]
    if worst_hours and worst_hours[0][1]['loss_rate'] > 50:
        worst_hour_list = [f"{h:02d}:00" for h, _ in worst_hours]
        recommendations.append(f"⚠️  Avoid trading during hours: {', '.join(worst_hour_list)} (high loss rate)")

    # Check counter-trend trades
    counter_trend_trades = [t for t in trades if
                           (t['direction'] == 'LONG' and t['trend'] == 'down') or
                           (t['direction'] == 'SHORT' and t['trend'] == 'up')]
    if counter_trend_trades:
        counter_losers = [t for t in counter_trend_trades if t['pnl_pct'] <= 0]
        counter_loss_rate = len(counter_losers) / len(counter_trend_trades) * 100
        if counter_loss_rate > 50:
            recommendations.append(f"✅ Add trend filter: Only trade WITH the trend (reduces {len(counter_losers)} losses)")

    # Check low volume trades
    low_vol_losers = [t for t in vol_ratio_low if t['pnl_pct'] <= 0]
    if low_vol_losers and len(low_vol_losers) / len(vol_ratio_low) > 0.5:
        recommendations.append(f"✅ Require minimum volume ratio > 0.8 (filters {len(low_vol_losers)} weak signals)")

    # Check high volatility
    high_vol_losers = [t for t in vol_high if t['pnl_pct'] <= 0]
    if high_vol_losers and len(high_vol_losers) / len(vol_high) > 0.45:
        recommendations.append(f"⚠️  Be cautious in high volatility (>1.5%): {len(high_vol_losers)} losses")

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec}")
    else:
        print("\n✅ Strategy is already well-optimized!")

    return {
        'trades': trades,
        'winners': winners,
        'losers': losers,
        'hour_stats': hour_stats,
        'recommendations': recommendations
    }


if __name__ == '__main__':
    analyze_losing_trades()
