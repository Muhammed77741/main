"""
Анализ:
1. Месячная производительность - найти аномалии
2. Пропущенные сигналы - какие движения мы не ловим
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def analyze_monthly_performance(trades_df):
    """
    Анализ месячной производительности
    """
    
    print("\n" + "="*100)
    print("📊 МЕСЯЧНАЯ ПРОИЗВОДИТЕЛЬНОСТЬ")
    print("="*100)
    
    trades_df['month'] = trades_df['entry_time'].dt.to_period('M')
    
    monthly = trades_df.groupby('month').agg({
        'pnl_pct': ['sum', 'mean', 'count']
    }).reset_index()
    
    monthly.columns = ['month', 'total_pnl', 'avg_pnl', 'trades']
    monthly['month_str'] = monthly['month'].astype(str)
    
    # Sort by total PnL
    monthly_sorted = monthly.sort_values('total_pnl', ascending=False)
    
    print(f"\n{'Month':<15} {'Total PnL':<12} {'Avg PnL':<12} {'Trades':<10} {'PnL/Trade':<12}")
    print("-"*70)
    
    for _, row in monthly_sorted.iterrows():
        pnl_per_trade = row['total_pnl'] / row['trades'] if row['trades'] > 0 else 0
        print(f"{row['month_str']:<15} {row['total_pnl']:>+10.2f}% {row['avg_pnl']:>+10.3f}% "
              f"{int(row['trades']):<10} {pnl_per_trade:>+10.3f}%")
    
    # Find anomalies
    mean_pnl = monthly['total_pnl'].mean()
    std_pnl = monthly['total_pnl'].std()
    
    anomalies = monthly[monthly['total_pnl'] > mean_pnl + 1.5 * std_pnl]
    
    if len(anomalies) > 0:
        print(f"\n" + "="*100)
        print("🚨 АНОМАЛЬНО ВЫСОКИЕ МЕСЯЦЫ")
        print("="*100)
        print(f"\n   Mean: {mean_pnl:.2f}%, Std: {std_pnl:.2f}%")
        print(f"   Threshold: {mean_pnl + 1.5 * std_pnl:.2f}%")
        
        for _, anomaly in anomalies.iterrows():
            print(f"\n   🔥 {anomaly['month_str']}: {anomaly['total_pnl']:+.2f}%")
            print(f"      Trades: {int(anomaly['trades'])}")
            print(f"      Avg PnL: {anomaly['avg_pnl']:+.3f}%")
            print(f"      Above mean: {anomaly['total_pnl'] - mean_pnl:+.2f}%")
    
    return monthly, anomalies


def analyze_anomaly_month(trades_df, anomaly_month):
    """
    Детальный анализ аномального месяца
    """
    
    print(f"\n" + "="*100)
    print(f"🔍 ДЕТАЛЬНЫЙ АНАЛИЗ: {anomaly_month}")
    print("="*100)
    
    # Filter trades
    trades_df['month'] = trades_df['entry_time'].dt.to_period('M')
    month_trades = trades_df[trades_df['month'].astype(str) == anomaly_month].copy()
    
    print(f"\n📊 Общая статистика:")
    print(f"   Всего сделок: {len(month_trades)}")
    print(f"   Total PnL:    {month_trades['pnl_pct'].sum():+.2f}%")
    print(f"   Avg PnL:      {month_trades['pnl_pct'].mean():+.3f}%")
    
    wins = len(month_trades[month_trades['pnl_pct'] > 0])
    print(f"   Win Rate:     {wins/len(month_trades)*100:.1f}%")
    
    # By source
    print(f"\n📊 По источнику:")
    for source in ['BASELINE', '30PIP']:
        source_trades = month_trades[month_trades['source'] == source]
        if len(source_trades) > 0:
            source_pnl = source_trades['pnl_pct'].sum()
            source_wr = len(source_trades[source_trades['pnl_pct'] > 0]) / len(source_trades) * 100
            
            print(f"   {source:10s}: {len(source_trades):3d} trades | "
                  f"PnL {source_pnl:+7.2f}% | WR {source_wr:5.1f}%")
    
    # Top trades
    print(f"\n🏆 TOP 10 СДЕЛОК:")
    top_trades = month_trades.nlargest(10, 'pnl_pct')
    
    print(f"\n{'Date':<20} {'Source':<10} {'Pattern':<15} {'PnL':<10}")
    print("-"*60)
    
    for _, trade in top_trades.iterrows():
        pattern = str(trade.get('detector_pattern', trade.get('pattern', 'Unknown')))[:13]
        print(f"{str(trade['entry_time']):<20} {trade['source']:<10} "
              f"{pattern:<15} {trade['pnl_pct']:>8.2f}%")
    
    # Why so good?
    print(f"\n💡 ПОЧЕМУ ТАК ХОРОШО?")
    
    # Check if many large wins
    large_wins = month_trades[month_trades['pnl_pct'] > 1.5]
    if len(large_wins) > 0:
        print(f"\n   ✅ Много больших побед:")
        print(f"      {len(large_wins)} trades > 1.5%")
        print(f"      Total from large wins: {large_wins['pnl_pct'].sum():+.2f}%")
    
    # Check few losses
    losses = month_trades[month_trades['pnl_pct'] < 0]
    if len(losses) < len(month_trades) * 0.2:
        print(f"\n   ✅ Мало убытков:")
        print(f"      {len(losses)} losses ({len(losses)/len(month_trades)*100:.1f}%)")
        print(f"      Total losses: {losses['pnl_pct'].sum():+.2f}%")
    
    # Check high win rate
    if wins / len(month_trades) > 0.7:
        print(f"\n   ✅ Высокий Win Rate:")
        print(f"      {wins/len(month_trades)*100:.1f}%")
    
    return month_trades


def find_missed_opportunities(df, trades_df):
    """
    Найти пропущенные возможности
    """
    
    print(f"\n" + "="*100)
    print("🔍 АНАЛИЗ ПРОПУЩЕННЫХ ВОЗМОЖНОСТЕЙ")
    print("="*100)
    
    # Find all strong moves (50+ pips)
    print(f"\n1️⃣  Поиск сильных движений (50+ pips)...")
    
    strong_moves = []
    
    for i in range(len(df) - 20):
        entry_time = df.index[i]
        entry_price = df.iloc[i]['close']
        
        # Look forward 20 candles
        future = df.iloc[i+1:i+21]
        
        if len(future) == 0:
            continue
        
        # Find max high
        max_high = future['high'].max()
        max_profit = (max_high - entry_price) / 0.10  # pips
        
        if max_profit >= 50:
            # When did it reach max?
            max_idx = future['high'].idxmax()
            candles_to_max = len(future[:max_idx])
            
            strong_moves.append({
                'time': entry_time,
                'entry_price': entry_price,
                'max_price': max_high,
                'potential_pips': max_profit,
                'candles_to_max': candles_to_max
            })
    
    moves_df = pd.DataFrame(strong_moves)
    
    print(f"   ✅ Найдено {len(moves_df)} движений 50+ pips")
    
    if len(moves_df) == 0:
        return None
    
    # Check which moves we caught
    print(f"\n2️⃣  Проверка: сколько мы поймали...")
    
    trades_df['entry_hour'] = trades_df['entry_time'].dt.floor('H')
    moves_df['hour'] = moves_df['time'].dt.floor('H')
    
    # Match by hour
    caught_moves = moves_df[moves_df['hour'].isin(trades_df['entry_hour'])]
    missed_moves = moves_df[~moves_df['hour'].isin(trades_df['entry_hour'])]
    
    caught_pct = len(caught_moves) / len(moves_df) * 100
    
    print(f"   ✅ Caught:  {len(caught_moves)} ({caught_pct:.1f}%)")
    print(f"   ❌ Missed:  {len(missed_moves)} ({100-caught_pct:.1f}%)")
    
    # Analyze missed moves
    if len(missed_moves) > 0:
        print(f"\n3️⃣  АНАЛИЗ ПРОПУЩЕННЫХ ДВИЖЕНИЙ:")
        
        print(f"\n   📊 Статистика:")
        print(f"      Total missed: {len(missed_moves)}")
        print(f"      Avg potential: {missed_moves['potential_pips'].mean():.0f} pips")
        print(f"      Total potential: {missed_moves['potential_pips'].sum():.0f} pips")
        print(f"      Max single move: {missed_moves['potential_pips'].max():.0f} pips")
        
        # Analyze market conditions before missed moves
        print(f"\n   🔍 УСЛОВИЯ ПЕРЕД ПРОПУЩЕННЫМИ ДВИЖЕНИЯМИ:")
        
        # Get market data for missed moves
        missed_conditions = []
        
        for _, move in missed_moves.head(50).iterrows():  # Analyze first 50
            move_time = move['time']
            
            # Get previous candles
            try:
                move_idx = df.index.get_loc(move_time)
                
                if move_idx >= 20:
                    prev_candles = df.iloc[move_idx-20:move_idx]
                    
                    # Calculate indicators
                    close_prices = prev_candles['close'].values
                    highs = prev_candles['high'].values
                    lows = prev_candles['low'].values
                    volumes = prev_candles['volume'].values
                    
                    # Simple trend
                    ma5 = close_prices[-5:].mean()
                    ma20 = close_prices.mean()
                    trend = 'UP' if ma5 > ma20 else 'DOWN'
                    
                    # Volatility
                    atr = np.mean(highs - lows)
                    
                    # Price action
                    last_candle = prev_candles.iloc[-1]
                    candle_body = abs(last_candle['close'] - last_candle['open'])
                    candle_range = last_candle['high'] - last_candle['low']
                    body_ratio = candle_body / candle_range if candle_range > 0 else 0
                    
                    # Volume
                    vol_ma = volumes.mean()
                    vol_ratio = volumes[-1] / vol_ma if vol_ma > 0 else 1
                    
                    missed_conditions.append({
                        'time': move_time,
                        'potential_pips': move['potential_pips'],
                        'trend': trend,
                        'atr': atr,
                        'body_ratio': body_ratio,
                        'volume_ratio': vol_ratio,
                        'price': last_candle['close']
                    })
            except:
                continue
        
        if len(missed_conditions) > 0:
            cond_df = pd.DataFrame(missed_conditions)
            
            print(f"\n      Анализ {len(cond_df)} пропущенных:")
            
            # Trend
            trend_counts = cond_df['trend'].value_counts()
            print(f"\n      Тренд:")
            for trend, count in trend_counts.items():
                print(f"         {trend}: {count} ({count/len(cond_df)*100:.1f}%)")
            
            # ATR
            print(f"\n      Волатильность (ATR):")
            print(f"         Avg: {cond_df['atr'].mean():.2f}")
            print(f"         Median: {cond_df['atr'].median():.2f}")
            
            # Volume
            high_vol = len(cond_df[cond_df['volume_ratio'] > 1.5])
            print(f"\n      Объём:")
            print(f"         High volume (>1.5x): {high_vol} ({high_vol/len(cond_df)*100:.1f}%)")
            print(f"         Avg vol ratio: {cond_df['volume_ratio'].mean():.2f}")
            
            # Body ratio
            strong_candles = len(cond_df[cond_df['body_ratio'] > 0.7])
            print(f"\n      Свечи:")
            print(f"         Strong body (>70%): {strong_candles} ({strong_candles/len(cond_df)*100:.1f}%)")
            
            # Top missed
            print(f"\n   🔥 TOP 10 ПРОПУЩЕННЫХ:")
            top_missed = cond_df.nlargest(10, 'potential_pips')
            
            print(f"\n   {'Date':<20} {'Pips':<10} {'Trend':<8} {'ATR':<10} {'Vol Ratio':<12}")
            print("   " + "-"*70)
            
            for _, miss in top_missed.iterrows():
                print(f"   {str(miss['time']):<20} {miss['potential_pips']:>8.0f}p "
                      f"{miss['trend']:<8} {miss['atr']:>8.2f} {miss['volume_ratio']:>10.2f}x")
            
            return missed_moves, cond_df
    
    return missed_moves, None


def suggest_new_patterns(missed_conditions_df):
    """
    Предложить новые паттерны на основе пропущенных
    """
    
    if missed_conditions_df is None or len(missed_conditions_df) == 0:
        return
    
    print(f"\n" + "="*100)
    print("💡 ПРЕДЛОЖЕНИЯ НОВЫХ ПАТТЕРНОВ")
    print("="*100)
    
    # Pattern 1: High Volume Breakout in Uptrend
    uptrend_high_vol = missed_conditions_df[
        (missed_conditions_df['trend'] == 'UP') &
        (missed_conditions_df['volume_ratio'] > 1.5)
    ]
    
    if len(uptrend_high_vol) > 0:
        avg_pips = uptrend_high_vol['potential_pips'].mean()
        print(f"\n1️⃣  HIGH VOLUME UPTREND BREAKOUT:")
        print(f"   Пропущено: {len(uptrend_high_vol)} сделок")
        print(f"   Avg potential: {avg_pips:.0f} pips")
        print(f"   Total potential: {uptrend_high_vol['potential_pips'].sum():.0f} pips")
        print(f"\n   Условия:")
        print(f"      • Тренд: UP (MA5 > MA20)")
        print(f"      • Объём: >1.5x average")
        print(f"      • ATR: {uptrend_high_vol['atr'].mean():.2f} avg")
    
    # Pattern 2: Strong Body Candles
    strong_body = missed_conditions_df[
        missed_conditions_df['body_ratio'] > 0.7
    ]
    
    if len(strong_body) > 0:
        avg_pips = strong_body['potential_pips'].mean()
        print(f"\n2️⃣  STRONG MOMENTUM CANDLE:")
        print(f"   Пропущено: {len(strong_body)} сделок")
        print(f"   Avg potential: {avg_pips:.0f} pips")
        print(f"   Total potential: {strong_body['potential_pips'].sum():.0f} pips")
        print(f"\n   Условия:")
        print(f"      • Body ratio: >70%")
        print(f"      • Сильная направленная свеча")
        print(f"      • Avg ATR: {strong_body['atr'].mean():.2f}")
    
    # Pattern 3: High ATR moves
    high_atr = missed_conditions_df[
        missed_conditions_df['atr'] > missed_conditions_df['atr'].quantile(0.75)
    ]
    
    if len(high_atr) > 0:
        avg_pips = high_atr['potential_pips'].mean()
        print(f"\n3️⃣  HIGH VOLATILITY EXPANSION:")
        print(f"   Пропущено: {len(high_atr)} сделок")
        print(f"   Avg potential: {avg_pips:.0f} pips")
        print(f"   Total potential: {high_atr['potential_pips'].sum():.0f} pips")
        print(f"\n   Условия:")
        print(f"      • ATR > 75th percentile ({missed_conditions_df['atr'].quantile(0.75):.2f})")
        print(f"      • Высокая волатильность")


def main():
    print("\n" + "="*100)
    print("🔍 АНАЛИЗ МЕСЯЧНОЙ ПРОИЗВОДИТЕЛЬНОСТИ И ПРОПУЩЕННЫХ СИГНАЛОВ")
    print("="*100)
    
    # Load data
    print("\n📥 Loading data...")
    
    # Trades
    try:
        trades_df = pd.read_csv('pattern_recognition_v7_hybrid_backtest.csv')
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    except:
        print("❌ Trades file not found!")
        return
    
    # Market data
    try:
        df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
        df['timestamp'] = pd.to_datetime(df['datetime'])
        df = df.set_index('timestamp')
        df = df[['open', 'high', 'low', 'close', 'volume']]
    except:
        print("❌ Market data not found!")
        return
    
    print(f"✅ Loaded {len(trades_df)} trades")
    print(f"✅ Loaded {len(df)} candles")
    
    # 1. Monthly analysis
    monthly, anomalies = analyze_monthly_performance(trades_df)
    
    # 2. Analyze anomaly month
    if len(anomalies) > 0:
        anomaly_month = anomalies.iloc[0]['month_str']
        month_trades = analyze_anomaly_month(trades_df, anomaly_month)
    
    # 3. Find missed opportunities
    missed_moves, missed_conditions = find_missed_opportunities(df, trades_df)
    
    # 4. Suggest new patterns
    if missed_conditions is not None:
        suggest_new_patterns(missed_conditions)
    
    print(f"\n" + "="*100)
    print("✅ АНАЛИЗ ЗАВЕРШЁН")
    print("="*100)


if __name__ == "__main__":
    main()
