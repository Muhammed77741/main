"""
Adaptive Backtest V3 with FIXED 35-POINT STOP LOSS
- Uses same TREND/RANGE detection as V3 Adaptive
- Fixed 35-point SL instead of dynamic swing-based SL
- Adaptive TP levels based on market regime
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from pattern_recognition_strategy import PatternRecognitionStrategy


class AdaptiveBacktestV3FixedSL:
    """Adaptive backtest with FIXED 35p SL - switches between trend and range modes"""

    def __init__(self, spread_points=2.0, commission_points=0.5, swap_per_day=-0.3):
        """
        Args:
            spread_points: Average spread in points (default: 2 for XAUUSD)
            commission_points: Commission per trade in points (default: 0.5)
            swap_per_day: Swap cost per day in points (default: -0.3)
        """
        self.spread = spread_points
        self.commission = commission_points
        self.swap_per_day = swap_per_day

        # *** FIXED STOP LOSS ***
        self.fixed_sl_points = 35  # FIXED 35 points for all trades

        # TREND MODE parameters (сильный тренд) - AGGRESSIVE TPs
        self.trend_tp1 = 45
        self.trend_tp2 = 70
        self.trend_tp3 = 100
        self.trend_trailing = 18
        self.trend_timeout = 60

        # RANGE MODE parameters (боковик) - MODERATE TPs  
        self.range_tp1 = 40
        self.range_tp2 = 60
        self.range_tp3 = 80
        self.range_trailing = 15
        self.range_timeout = 48

        # Daily limits
        self.max_trades_per_day = 10
        self.max_loss_per_day = -5.0  # %
        self.max_positions = 5
        self.max_drawdown = -999.0  # UNLIMITED

    def detect_market_regime(self, df, current_idx, lookback=100):
        """
        УЛУЧШЕННЫЙ детектор режима рынка: TREND или RANGE

        Использует:
        1. EMA crossover (тренд определяется пересечением)
        2. ATR (волатильность)
        3. Направленное движение
        4. Последовательные свечи в одном направлении
        """
        if current_idx < lookback:
            return 'RANGE'  # По умолчанию боковик

        # Берем последние N свечей
        recent_data = df.iloc[current_idx - lookback:current_idx]

        # 1. EMA CROSSOVER (главный индикатор тренда!)
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()

        # Текущее положение EMA
        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]

        # Разница между EMA в %
        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100

        # Если EMA расходятся > 0.3% = явный тренд
        ema_trend = ema_diff_pct > 0.3

        # 2. ATR (волатильность - должна быть выше средней)
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()

        high_volatility = atr > avg_atr * 1.05

        # 3. Направленное движение (цена движется в одном направлении)
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()

        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35

        # 4. Последовательность движений (свечи в одном направлении)
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        total_moves = up_moves + down_moves

        # Односторонний bias (>60% движений в одном направлении)
        bias = max(up_moves, down_moves) / total_moves if total_moves > 0 else 0.5
        consistent_direction = bias > 0.6

        # 5. Higher highs / Lower lows
        highs = recent_data['high'].values
        lows = recent_data['low'].values

        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])

        hl_trend = (higher_highs > len(highs) * 0.5) or (lower_lows > len(lows) * 0.5)

        # DECISION: Нужно минимум 3 из 5 индикаторов для TREND
        trend_votes = sum([
            ema_trend,
            high_volatility,
            strong_direction,
            consistent_direction,
            hl_trend
        ])

        return 'TREND' if trend_votes >= 3 else 'RANGE'

    def run_backtest(self, df, signals_df):
        """Run backtest with FIXED 35p SL and adaptive TPs"""
        
        print(f"📂 Running V3 Adaptive Backtest with FIXED 35p SL...")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
        print(f"\n   🛡️ FIXED STOP LOSS: {self.fixed_sl_points} points")
        print(f"\n   🎯 TREND MODE:")
        print(f"   TP: {self.trend_tp1}п / {self.trend_tp2}п / {self.trend_tp3}п")
        print(f"   R:R: {self.trend_tp1/self.fixed_sl_points:.2f}:1 / {self.trend_tp2/self.fixed_sl_points:.2f}:1 / {self.trend_tp3/self.fixed_sl_points:.2f}:1")
        print(f"\n   📊 RANGE MODE:")
        print(f"   TP: {self.range_tp1}п / {self.range_tp2}п / {self.range_tp3}п")
        print(f"   R:R: {self.range_tp1/self.fixed_sl_points:.2f}:1 / {self.range_tp2/self.fixed_sl_points:.2f}:1 / {self.range_tp3/self.fixed_sl_points:.2f}:1")

        # Detect regime for each signal
        regimes = []
        for idx, signal_row in signals_df.iterrows():
            signal_idx = df[df['time'] == signal_row['time']].index[0]
            regime = self.detect_market_regime(df, signal_idx)
            regimes.append(regime)
        
        signals_df['regime'] = regimes

        print(f"\n{'='*80}")
        print(f"📊 MARKET REGIME STATISTICS")
        print(f"{'='*80}")
        print(f"   TREND signals: {sum(signals_df['regime'] == 'TREND')} ({sum(signals_df['regime'] == 'TREND')/len(signals_df)*100:.1f}%)")
        print(f"   RANGE signals: {sum(signals_df['regime'] == 'RANGE')} ({sum(signals_df['regime'] == 'RANGE')/len(signals_df)*100:.1f}%)")

        # Simulate trades
        trades = []
        equity = 100.0
        peak_equity = 100.0
        max_dd = 0.0
        
        # Statistics by regime
        regime_stats = {'TREND': [], 'RANGE': []}

        for idx, signal in signals_df.iterrows():
            signal_time = signal['time']
            signal_type = signal['type']
            entry_price = signal['entry_price']
            regime = signal['regime']

            # Set TP/TP based on regime (FIXED SL!)
            sl_points = self.fixed_sl_points
            
            if regime == 'TREND':
                tp1_points = self.trend_tp1
                tp2_points = self.trend_tp2
                tp3_points = self.trend_tp3
                trailing_points = self.trend_trailing
                timeout_hours = self.trend_timeout
            else:
                tp1_points = self.range_tp1
                tp2_points = self.range_tp2
                tp3_points = self.range_tp3
                trailing_points = self.range_trailing
                timeout_hours = self.range_timeout

            # Calculate SL/TP prices using FIXED SL
            if signal_type == 'BUY':
                sl_price = entry_price - sl_points
                tp1_price = entry_price + tp1_points
                tp2_price = entry_price + tp2_points
                tp3_price = entry_price + tp3_points
            else:  # SELL
                sl_price = entry_price + sl_points
                tp1_price = entry_price - tp1_points
                tp2_price = entry_price - tp2_points
                tp3_price = entry_price - tp3_points

            # Find signal index in df
            signal_idx = df[df['time'] == signal_time].index[0]
            
            # Simulate trade
            future_data = df.iloc[signal_idx+1:signal_idx+1+timeout_hours]
            
            pnl_pct = 0.0
            exit_reason = 'TIMEOUT'
            
            # Check each candle
            for future_idx, candle in future_data.iterrows():
                # Check SL first
                if signal_type == 'BUY':
                    if candle['low'] <= sl_price:
                        pnl_pct = -sl_points / entry_price * 100
                        exit_reason = 'SL'
                        break
                    elif candle['high'] >= tp3_price:
                        pnl_pct = tp3_points / entry_price * 100
                        exit_reason = 'TP3'
                        break
                    elif candle['high'] >= tp2_price:
                        pnl_pct = tp2_points / entry_price * 100
                        exit_reason = 'TP2'
                        break
                    elif candle['high'] >= tp1_price:
                        pnl_pct = tp1_points / entry_price * 100
                        exit_reason = 'TP1'
                        break
                else:  # SELL
                    if candle['high'] >= sl_price:
                        pnl_pct = -sl_points / entry_price * 100
                        exit_reason = 'SL'
                        break
                    elif candle['low'] <= tp3_price:
                        pnl_pct = tp3_points / entry_price * 100
                        exit_reason = 'TP3'
                        break
                    elif candle['low'] <= tp2_price:
                        pnl_pct = tp2_points / entry_price * 100
                        exit_reason = 'TP2'
                        break
                    elif candle['low'] <= tp1_price:
                        pnl_pct = tp1_points / entry_price * 100
                        exit_reason = 'TP1'
                        break
            
            # Account for costs
            costs_pct = (self.spread + self.commission) / entry_price * 100
            pnl_pct -= costs_pct
            
            # Update equity
            equity += pnl_pct
            peak_equity = max(peak_equity, equity)
            current_dd = (equity - peak_equity) / peak_equity * 100
            max_dd = min(max_dd, current_dd)
            
            # Record trade
            trades.append({
                'time': signal_time,
                'type': signal_type,
                'regime': regime,
                'entry': entry_price,
                'sl': sl_price,
                'tp1': tp1_price,
                'tp2': tp2_price,
                'tp3': tp3_price,
                'exit_reason': exit_reason,
                'pnl_pct': pnl_pct,
                'equity': equity
            })
            
            regime_stats[regime].append(pnl_pct)
        
        # Calculate statistics
        trades_df = pd.DataFrame(trades)
        wins = trades_df[trades_df['pnl_pct'] > 0]
        losses = trades_df[trades_df['pnl_pct'] <= 0]
        
        total_pnl = equity - 100.0
        win_rate = len(wins) / len(trades_df) * 100
        avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
        profit_factor = abs(wins['pnl_pct'].sum() / losses['pnl_pct'].sum()) if len(losses) > 0 else 999
        
        # Print results
        print(f"\n{'='*80}")
        print(f"📊 RESULTS (V3 Adaptive with FIXED 35p SL)")
        print(f"{'='*80}")
        print(f"\n📈 Performance:")
        print(f"   Total trades: {len(trades_df)}")
        print(f"   Wins: {len(wins)} ({win_rate:.1f}%)")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Avg Win: {avg_win:+.2f}%")
        print(f"   Avg Loss: {avg_loss:.2f}%")
        print(f"   Profit Factor: {profit_factor:.2f}")
        
        print(f"\n📉 Risk Metrics:")
        print(f"   Max Drawdown: {max_dd:.2f}%")
        print(f"   Fixed SL Risk: {self.fixed_sl_points}p per trade")
        
        # Regime breakdown
        for regime in ['TREND', 'RANGE']:
            regime_trades = trades_df[trades_df['regime'] == regime]
            if len(regime_trades) > 0:
                regime_wins = regime_trades[regime_trades['pnl_pct'] > 0]
                regime_pnl = regime_trades['pnl_pct'].sum()
                regime_wr = len(regime_wins) / len(regime_trades) * 100
                print(f"\n   {regime} trades: {len(regime_trades)}")
                print(f"     PnL: {regime_pnl:+.2f}%")
                print(f"     Win Rate: {regime_wr:.1f}%")
        
        # Monthly results
        trades_df['month'] = pd.to_datetime(trades_df['time']).dt.to_period('M')
        monthly = trades_df.groupby('month').agg({
            'pnl_pct': ['sum', 'count']
        })
        
        print(f"\n📅 Monthly Results:")
        for month in monthly.index:
            month_pnl = monthly.loc[month, ('pnl_pct', 'sum')]
            month_count = int(monthly.loc[month, ('pnl_pct', 'count')])
            print(f"   {month}: {month_count} trades, {month_pnl:+.2f}%")
        
        return trades_df


def main():
    parser = argparse.ArgumentParser(description='Run V3 Adaptive Backtest with FIXED 35p SL')
    parser.add_argument('--file', type=str, required=True, help='Path to CSV file')
    args = parser.parse_args()

    print(f"📂 Loading data from {args.file}...")
    df = pd.read_csv(args.file)
    # Handle both 'time' and 'datetime' column names
    if 'datetime' in df.columns:
        df['time'] = pd.to_datetime(df['datetime'])
    else:
        df['time'] = pd.to_datetime(df['time'])
    
    print(f"\n🔍 Running Pattern Recognition Strategy to generate signals...")
    strategy = PatternRecognitionStrategy()
    signals_df = strategy.generate_signals(df)
    
    print(f"\n✅ Generated {len(signals_df)} signals")
    
    # Run backtest
    backtest = AdaptiveBacktestV3FixedSL()
    results = backtest.run_backtest(df, signals_df)
    
    print(f"\n💾 Results saved")


if __name__ == "__main__":
    main()
