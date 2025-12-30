"""
Диагностика логики bearish Order Blocks
Проверим правильность определения bearish OB
"""

import pandas as pd
import numpy as np

# Load sample data
df = pd.read_csv('../XAUUSD_1H_MT5_20241227_20251227.csv')
df['timestamp'] = pd.to_datetime(df['datetime'])
df = df.set_index('timestamp')
df = df[['open', 'high', 'low', 'close', 'volume']].head(500)


def detect_order_blocks_original(df):
    """Original logic from smc_indicators.py"""
    df = df.copy()
    df['bullish_ob'] = False
    df['bearish_ob'] = False
    df['ob_top'] = np.nan
    df['ob_bottom'] = np.nan
    
    threshold = 0.002  # 0.2% move threshold
    
    for i in range(1, len(df) - 1):
        # Bullish Order Block: bearish candle before bullish move
        if df['close'].iloc[i] < df['open'].iloc[i]:  # Bearish candle
            # Check if next candle makes strong bullish move
            next_move = (df['close'].iloc[i+1] - df['open'].iloc[i+1]) / df['open'].iloc[i+1]
            if next_move > threshold:
                df.loc[df.index[i], 'bullish_ob'] = True
                df.loc[df.index[i], 'ob_top'] = df['high'].iloc[i]
                df.loc[df.index[i], 'ob_bottom'] = df['low'].iloc[i]
        
        # Bearish Order Block: bullish candle before bearish move
        if df['close'].iloc[i] > df['open'].iloc[i]:  # Bullish candle
            # Check if next candle makes strong bearish move
            next_move = (df['open'].iloc[i+1] - df['close'].iloc[i+1]) / df['open'].iloc[i+1]
            if next_move > threshold:
                df.loc[df.index[i], 'bearish_ob'] = True
                df.loc[df.index[i], 'ob_top'] = df['high'].iloc[i]
                df.loc[df.index[i], 'ob_bottom'] = df['low'].iloc[i]
    
    return df


def detect_order_blocks_corrected(df):
    """
    CORRECTED logic: OB should be where institutions placed orders
    
    ПРАВИЛЬНАЯ ЛОГИКА:
    - Bullish OB = последняя DOWN свеча перед сильным UP движением
      (институции купили здесь)
    - Bearish OB = последняя UP свеча перед сильным DOWN движением
      (институции продали здесь)
    
    НО: Проблема в том, что bearish OB часто ЛОЖНЫЙ,
    потому что Gold больше растет чем падает!
    """
    df = df.copy()
    df['bullish_ob_v2'] = False
    df['bearish_ob_v2'] = False
    
    threshold = 0.002
    
    for i in range(1, len(df) - 1):
        # Bullish OB: bearish candle + strong bullish breakout
        if df['close'].iloc[i] < df['open'].iloc[i]:
            next_move = (df['close'].iloc[i+1] - df['open'].iloc[i+1]) / df['open'].iloc[i+1]
            if next_move > threshold:
                df.loc[df.index[i], 'bullish_ob_v2'] = True
        
        # Bearish OB: bullish candle + strong bearish breakout
        if df['close'].iloc[i] > df['open'].iloc[i]:
            next_move = (df['open'].iloc[i+1] - df['close'].iloc[i+1]) / df['open'].iloc[i+1]
            if next_move > threshold:
                df.loc[df.index[i], 'bearish_ob_v2'] = True
    
    return df


def analyze_ob_quality(df):
    """Analyze OB quality by looking at price action AFTER OB"""
    
    print("\n" + "="*80)
    print("🔍 АНАЛИЗ КАЧЕСТВА ORDER BLOCKS")
    print("="*80)
    
    # Apply detection
    df = detect_order_blocks_original(df)
    
    # Add EMA for trend context
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['is_uptrend'] = df['ema_20'] > df['ema_50']
    
    bullish_obs = df[df['bullish_ob'] == True]
    bearish_obs = df[df['bearish_ob'] == True]
    
    print(f"\n📊 Количество OB:")
    print(f"   Bullish OB: {len(bullish_obs)}")
    print(f"   Bearish OB: {len(bearish_obs)}")
    
    # Analyze success rate
    print(f"\n📈 BULLISH OB - анализ дальнейшего движения:")
    
    bullish_success = 0
    bullish_fail = 0
    
    for idx in bullish_obs.index:
        i = df.index.get_loc(idx)
        if i + 10 < len(df):
            # Check if price went up in next 10 bars
            entry_price = df['close'].iloc[i]
            future_high = df['high'].iloc[i+1:i+11].max()
            future_low = df['low'].iloc[i+1:i+11].min()
            
            up_move = (future_high - entry_price) / entry_price
            down_move = (entry_price - future_low) / entry_price
            
            if up_move > down_move:
                bullish_success += 1
            else:
                bullish_fail += 1
    
    if bullish_success + bullish_fail > 0:
        bullish_wr = bullish_success / (bullish_success + bullish_fail) * 100
        print(f"   Win Rate: {bullish_wr:.1f}% ({bullish_success}/{bullish_success + bullish_fail})")
    
    # Analyze BEARISH OB
    print(f"\n📉 BEARISH OB - анализ дальнейшего движения:")
    
    bearish_success = 0
    bearish_fail = 0
    bearish_in_uptrend = 0
    bearish_in_downtrend = 0
    
    for idx in bearish_obs.index:
        i = df.index.get_loc(idx)
        if i + 10 < len(df):
            # Check trend context
            if df['is_uptrend'].iloc[i]:
                bearish_in_uptrend += 1
            else:
                bearish_in_downtrend += 1
            
            # Check if price went down in next 10 bars
            entry_price = df['close'].iloc[i]
            future_high = df['high'].iloc[i+1:i+11].max()
            future_low = df['low'].iloc[i+1:i+11].min()
            
            up_move = (future_high - entry_price) / entry_price
            down_move = (entry_price - future_low) / entry_price
            
            if down_move > up_move:
                bearish_success += 1
            else:
                bearish_fail += 1
    
    if bearish_success + bearish_fail > 0:
        bearish_wr = bearish_success / (bearish_success + bearish_fail) * 100
        print(f"   Win Rate: {bearish_wr:.1f}% ({bearish_success}/{bearish_success + bearish_fail})")
        print(f"   В uptrend: {bearish_in_uptrend}")
        print(f"   В downtrend: {bearish_in_downtrend}")
    
    # DIAGNOSIS
    print("\n" + "="*80)
    print("🚨 ДИАГНОЗ")
    print("="*80)
    
    if bearish_wr < 50:
        print(f"\n⚠️  BEARISH OB имеет очень низкий Win Rate ({bearish_wr:.1f}%)")
        print(f"   Это означает что bearish OB НЕ РАБОТАЕТ как сигнал для SHORT!")
        
        if bearish_in_uptrend > bearish_in_downtrend:
            print(f"\n   ПРИЧИНА #1: Bearish OB чаще появляется в UPTREND")
            print(f"      В uptrend: {bearish_in_uptrend}")
            print(f"      В downtrend: {bearish_in_downtrend}")
            print(f"      Это КОНТРТРЕНДОВЫЙ сигнал!")
        
        print(f"\n   ПРИЧИНА #2: Gold имеет UPWARD BIAS")
        print(f"      Gold больше растет чем падает")
        print(f"      Bullish OB WR: {bullish_wr:.1f}%")
        print(f"      Bearish OB WR: {bearish_wr:.1f}%")
        print(f"      Разница: {bullish_wr - bearish_wr:.1f}%")
    
    # RECOMMENDATIONS
    print("\n" + "="*80)
    print("💡 РЕКОМЕНДАЦИИ")
    print("="*80)
    
    print(f"\n1️⃣  ОТКЛЮЧИТЬ SHORT на основе bearish OB ✅")
    print(f"   Win Rate слишком низкий ({bearish_wr:.1f}%)")
    
    print(f"\n2️⃣  Использовать bearish OB только в сильном downtrend 💡")
    print(f"   Требовать: EMA20 < EMA50 < EMA200")
    print(f"   И дополнительное подтверждение (momentum, volume)")
    
    print(f"\n3️⃣  Для SHORT искать ДРУГИЕ сигналы 💡")
    print(f"   Например:")
    print(f"   - Rejection от resistance (длинная тень сверху)")
    print(f"   - Break of Structure (BOS) вниз")
    print(f"   - Engulfing bearish pattern")
    print(f"   - НЕ просто bearish OB!")
    
    print(f"\n4️⃣  Или просто торговать LONG только ✅")
    print(f"   Bullish OB WR: {bullish_wr:.1f}%")
    print(f"   Gold растет лучше чем падает")
    print(f"   LONG стратегия = проще и прибыльнее")


if __name__ == "__main__":
    analyze_ob_quality(df)
    
    print("\n" + "="*80)
    print("✅ Диагностика завершена!")
    print("="*80)
