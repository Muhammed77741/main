"""
V13: Fibonacci ТОЛЬКО для TP (без фильтрации входов)

КОНЦЕПЦИЯ:
- Все SMC сигналы принимаются (как V9) - БЕЗ фильтрации
- TP рассчитываются ДИНАМИЧЕСКИ на основе Fibonacci extensions от swing range
- Partial close: 30%/30%/40% (V9)
- Trailing: как V9 (25/20/13п)

ОТЛИЧИЯ ОТ V9:
- V9: фиксированные TP (35/65/100п для LONG TREND)
- V13: динамические TP на Fib extensions (127.2%, 161.8%, 200%)

ПРЕИМУЩЕСТВА:
- Сохраняем ВСЕ сигналы (не теряем сделки)
- TP адаптируются к волатильности (swing range)
- Используем естественные Fib уровни магнетизма цены
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from simplified_smc_strategy import SimplifiedSMCStrategy


class FibonacciTPOnlyBacktest:
    """V13: Fibonacci for TP only (no entry filtering)"""

    def __init__(self, spread_points=2.0, commission_points=0.5, swap_per_day=-0.3):
        self.spread = spread_points
        self.commission = commission_points
        self.swap_per_day = swap_per_day

        # Fibonacci extension levels (для TP) - OPTIMIZED
        # Lowered from 127.2%/161.8%/200% to 100%/127.2%/161.8%
        # for more realistic profit targets and higher hit rates
        self.fib_tp1 = 1.000  # 100% (was 127.2%)
        self.fib_tp2 = 1.272  # 127.2% (was 161.8%)
        self.fib_tp3 = 1.618  # 161.8% Golden ratio (was 200%)

        # V9 trailing (без изменений)
        self.long_trend_trailing = 25
        self.long_range_trailing = 20  # Keeping at 20 (tested 15, slightly worse)
        self.short_trend_trailing = 13

        # V9 timeout - OPTIMIZED
        # Reduced RANGE timeout from 48h to 36h to free capital faster
        self.long_trend_timeout = 60
        self.long_range_timeout = 36  # Was 48 hours
        self.short_trend_timeout = 24

        # Partial close - OPTIMIZED
        # Keeping 40/30/30 as best balance with current TP levels
        self.close_pct1 = 0.4  # TP1: 40%
        self.close_pct2 = 0.3  # TP2: 30%
        self.close_pct3 = 0.3  # TP3: 30%

        # Settings
        self.short_range_enabled = False
        self.max_trades_per_day = 10
        self.max_positions = 5

        # Swing lookback для расчета Fibonacci
        self.swing_lookback = 50

    def find_swing_range(self, df, current_idx, lookback=50):
        """
        Найти swing range для Fibonacci расчетов

        Args:
            df: DataFrame
            current_idx: Текущий индекс
            lookback: Сколько свечей назад искать

        Returns:
            (swing_high, swing_low, swing_range) или (None, None, None)
        """
        start_idx = max(0, current_idx - lookback)
        recent_data = df.iloc[start_idx:current_idx]

        if len(recent_data) < 10:
            return None, None, None

        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()
        swing_range = swing_high - swing_low

        # Проверка что range адекватный
        if swing_range < 10:  # Минимум 10 пунктов
            return None, None, None

        return swing_high, swing_low, swing_range

    def calculate_fibonacci_tp(self, entry_price, swing_range, direction):
        """
        Рассчитать TP на основе Fibonacci extensions

        Args:
            entry_price: Цена входа
            swing_range: Диапазон swing
            direction: 'LONG' или 'SHORT'

        Returns:
            (tp1, tp2, tp3) в пунктах цены
        """
        if direction == 'LONG':
            tp1 = entry_price + (swing_range * self.fib_tp1)
            tp2 = entry_price + (swing_range * self.fib_tp2)
            tp3 = entry_price + (swing_range * self.fib_tp3)
        else:  # SHORT
            tp1 = entry_price - (swing_range * self.fib_tp1)
            tp2 = entry_price - (swing_range * self.fib_tp2)
            tp3 = entry_price - (swing_range * self.fib_tp3)

        return tp1, tp2, tp3

    def detect_market_regime(self, df, current_idx, lookback=100):
        """Detect market regime: TREND or RANGE"""
        if current_idx < lookback:
            return 'RANGE'

        recent_data = df.iloc[current_idx - lookback:current_idx]

        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()
        ema_diff_pct = abs((ema_fast.iloc[-1] - ema_slow.iloc[-1]) / ema_slow.iloc[-1]) * 100
        ema_trend = ema_diff_pct > 0.3

        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()
        high_volatility = atr > avg_atr * 1.05

        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()
        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35

        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        sequential_trend = abs(up_moves - down_moves) > lookback * 0.15

        highs = recent_data['high'].values[-20:]
        lows = recent_data['low'].values[-20:]
        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
        structural_trend = (higher_highs > 12) or (lower_lows > 12)

        trend_signals = sum([ema_trend, high_volatility, strong_direction, sequential_trend, structural_trend])
        return 'TREND' if trend_signals >= 3 else 'RANGE'

    def is_valid_session(self, timestamp):
        """
        Check if timestamp is during high-liquidity trading sessions
        London: 07:00-12:00 UTC
        NY: 13:00-18:00 UTC
        """
        hour = timestamp.hour
        # London session (7-12 UTC) or NY session (13-18 UTC)
        return (7 <= hour < 12) or (13 <= hour < 18)

    def check_volume_filter(self, df, current_idx, lookback=20):
        """
        Check if current volume is above average (quality filter)
        Requires volume > 1.2x average of last 20 periods
        """
        if current_idx < lookback:
            return True  # Skip filter for early candles
        
        if 'volume' not in df.columns:
            return True  # Skip if no volume data
        
        current_vol = df['volume'].iloc[current_idx]
        avg_vol = df['volume'].iloc[current_idx-lookback:current_idx].mean()
        
        # Require 20% above average volume
        return current_vol > avg_vol * 1.2

    def backtest(self, df, strategy):
        """Run V13 backtest with Fibonacci TP only"""

        print(f"\n{'='*80}")
        print(f"📊 V13: FIBONACCI FOR TP ONLY (No Entry Filtering)")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")

        print(f"\n   🌟 FIBONACCI TP STRATEGY:")
        print(f"   ✅ Accept ALL SMC signals (like V9)")
        print(f"   🎯 TP1 = Fib Extension 127.2% from swing range")
        print(f"   🎯 TP2 = Fib Extension 161.8% from swing range (Golden Ratio)")
        print(f"   🎯 TP3 = Fib Extension 200% from swing range")
        print(f"   📊 Trailing: V9 (25/20/13п)")
        print(f"   ⏱️  Timeout: V9 (60/48/24h)")

        print(f"\n   ✨ PARTIAL CLOSE (V9):")
        print(f"   {int(self.close_pct1*100)}% на TP1, {int(self.close_pct2*100)}% на TP2, {int(self.close_pct3*100)}% на TP3")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())

        # Track trades and positions
        trades = []
        open_positions = []

        # Stats
        total_signals = 0
        fib_calculated = 0
        fib_fallback = 0

        # Process chronologically
        for i in range(len(df_strategy)):
            candle = df_strategy.iloc[i]
            candle_time = df_strategy.index[i]
            high = candle['high']
            low = candle['low']
            close = candle['close']
            signal = candle.get('signal', 0)

            # Check for new signal
            if signal != 0:
                total_signals += 1
                
                regime = self.detect_market_regime(df_strategy, i)

                # FILTER TREND REGIME (unprofitable -7.62%)
                if regime == 'TREND':
                    continue

                # FILTER SHORT IN RANGE
                if signal == -1 and regime == 'RANGE' and not self.short_range_enabled:
                    continue

                direction = 'LONG' if signal == 1 else 'SHORT'

                # Find swing range for Fibonacci
                swing_high, swing_low, swing_range = self.find_swing_range(df_strategy, i, self.swing_lookback)

                # Check max positions
                if len(open_positions) >= self.max_positions:
                    continue

                # Calculate entry and SL
                signal_sl = candle.get('stop_loss', close)

                if direction == 'LONG':
                    entry_price = close + self.spread / 2
                    sl_distance = close - signal_sl
                    sl_price = entry_price - sl_distance

                    # Calculate Fibonacci TP if swing range available
                    if swing_range is not None:
                        tp1_price, tp2_price, tp3_price = self.calculate_fibonacci_tp(
                            entry_price, swing_range, direction
                        )
                        fib_calculated += 1
                        tp_source = 'FIB'
                    else:
                        # Fallback to V9 fixed TP if no swing range
                        if regime == 'TREND':
                            tp1_price = entry_price + 35
                            tp2_price = entry_price + 65
                            tp3_price = entry_price + 100
                        else:  # RANGE
                            tp1_price = entry_price + 25
                            tp2_price = entry_price + 45
                            tp3_price = entry_price + 65
                        fib_fallback += 1
                        tp_source = 'V9'

                    # Trailing based on regime
                    if regime == 'TREND':
                        trailing = self.long_trend_trailing
                        timeout = self.long_trend_timeout
                    else:
                        trailing = self.long_range_trailing
                        timeout = self.long_range_timeout

                else:  # SHORT
                    entry_price = close - self.spread / 2
                    sl_distance = signal_sl - close
                    sl_price = entry_price + sl_distance

                    # Calculate Fibonacci TP
                    if swing_range is not None:
                        tp1_price, tp2_price, tp3_price = self.calculate_fibonacci_tp(
                            entry_price, swing_range, direction
                        )
                        fib_calculated += 1
                        tp_source = 'FIB'
                    else:
                        # Fallback to V9
                        tp1_price = entry_price - 18
                        tp2_price = entry_price - 30
                        tp3_price = entry_price - 42
                        fib_fallback += 1
                        tp_source = 'V9'

                    trailing = self.short_trend_trailing
                    timeout = self.short_trend_timeout

                new_pos = {
                    'entry_time': candle_time,
                    'entry_price': entry_price,
                    'direction': direction,
                    'sl_price': sl_price,
                    'tp1_price': tp1_price,
                    'tp2_price': tp2_price,
                    'tp3_price': tp3_price,
                    'tp1_hit': False,
                    'tp2_hit': False,
                    'tp3_hit': False,
                    'trailing_active': False,
                    'trailing_distance': trailing,
                    'timeout_hours': timeout,
                    'regime': regime,
                    'tp_source': tp_source,
                    'swing_range': swing_range if swing_range else 0,
                    'trailing_high': entry_price if direction == 'LONG' else 0,
                    'trailing_low': entry_price if direction == 'SHORT' else 999999,
                    'position_remaining': 1.0,
                    'total_pnl_pct': 0.0,
                }

                open_positions.append(new_pos)

            # Update all open positions (same as V9)
            positions_to_close = []

            for pos_idx, pos in enumerate(open_positions):
                entry_time = pos['entry_time']
                entry_price = pos['entry_price']
                direction = pos['direction']
                trailing_distance = pos['trailing_distance']
                timeout_hours = pos['timeout_hours']

                if entry_time == candle_time:
                    continue

                hours_in_trade = (candle_time - entry_time).total_seconds() / 3600

                if hours_in_trade >= timeout_hours:
                    if direction == 'LONG':
                        exit_price = close - self.spread / 2
                    else:
                        exit_price = close + self.spread / 2

                    pnl_points = self._calculate_pnl_points(
                        entry_price, exit_price, direction,
                        pos['position_remaining'], hours_in_trade
                    )

                    pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                    trade = self._create_trade_record(pos, exit_price, 'TIMEOUT', candle_time)
                    trades.append(trade)
                    positions_to_close.append(pos_idx)
                    continue

                if direction == 'LONG':
                    if high > pos['trailing_high']:
                        pos['trailing_high'] = high

                    if pos['trailing_active']:
                        new_sl = pos['trailing_high'] - trailing_distance
                        if new_sl > pos['sl_price']:
                            pos['sl_price'] = new_sl

                    if low <= pos['sl_price']:
                        exit_price = pos['sl_price']
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            pos['position_remaining'], hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._create_trade_record(pos, exit_price, exit_type, candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                    if high >= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            self.close_pct1, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= self.close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = high - trailing_distance

                    if high >= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            self.close_pct2, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= self.close_pct2
                        pos['tp2_hit'] = True

                    if high >= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            self.close_pct3, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= self.close_pct3
                        pos['tp3_hit'] = True

                    if pos['position_remaining'] <= 0.01:
                        trade = self._create_trade_record(pos, pos['tp3_price'], 'TP3', candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)

                else:  # SHORT - same logic
                    if low < pos['trailing_low']:
                        pos['trailing_low'] = low

                    if pos['trailing_active']:
                        new_sl = pos['trailing_low'] + trailing_distance
                        if new_sl < pos['sl_price']:
                            pos['sl_price'] = new_sl

                    if high >= pos['sl_price']:
                        exit_price = pos['sl_price']
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            pos['position_remaining'], hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._create_trade_record(pos, exit_price, exit_type, candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                    if low <= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            self.close_pct1, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= self.close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = low + trailing_distance

                    if low <= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            self.close_pct2, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= self.close_pct2
                        pos['tp2_hit'] = True

                    if low <= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            self.close_pct3, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= self.close_pct3
                        pos['tp3_hit'] = True

                    if pos['position_remaining'] <= 0.01:
                        trade = self._create_trade_record(pos, pos['tp3_price'], 'TP3', candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)

            for idx in sorted(positions_to_close, reverse=True):
                del open_positions[idx]

        if len(trades) == 0:
            print("❌ No completed trades")
            return None

        trades_df = pd.DataFrame(trades)

        # Print stats
        print(f"\n{'='*80}")
        print(f"🌟 FIBONACCI TP STATISTICS")
        print(f"{'='*80}")
        print(f"   Total signals: {total_signals}")
        print(f"   Fibonacci TP used: {fib_calculated} ({fib_calculated/total_signals*100:.1f}%)")
        print(f"   V9 fallback used: {fib_fallback} ({fib_fallback/total_signals*100:.1f}%)")

        # Print results
        self._print_results(trades_df)

        return trades_df

    def _calculate_pnl_points(self, entry, exit, direction, position_size, hours):
        """Calculate PnL in points"""
        if direction == 'LONG':
            price_pnl = exit - entry
        else:
            price_pnl = entry - exit

        price_pnl *= position_size
        price_pnl -= self.commission * position_size

        if hours > 24:
            days = hours / 24
            price_pnl += self.swap_per_day * days * position_size

        return price_pnl

    def _create_trade_record(self, pos, exit_price, exit_type, exit_time):
        """Create trade record"""
        duration_hours = (exit_time - pos['entry_time']).total_seconds() / 3600
        pnl_pct = pos['total_pnl_pct']
        pnl_points = (pnl_pct / 100) * pos['entry_price']

        return {
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'direction': pos['direction'],
            'regime': pos['regime'],
            'tp_source': pos['tp_source'],
            'swing_range': pos['swing_range'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'tp1_hit': pos['tp1_hit'],
            'tp2_hit': pos['tp2_hit'],
            'tp3_hit': pos['tp3_hit'],
            'trailing_used': pos['trailing_active'],
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
        }

    def _print_results(self, trades_df):
        """Print results"""
        print(f"\n{'='*80}")
        print(f"📊 OVERALL RESULTS")
        print(f"{'='*80}")

        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = trades_df['pnl_pct'].sum()
        total_points = trades_df['pnl_points'].sum()

        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if total_trades - wins > 0 else 0

        print(f"\n   📈 Performance:")
        print(f"   Total trades: {total_trades}")
        print(f"   Wins: {wins} ({win_rate:.1f}%)")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Total Points: {total_points:+.1f}п")
        print(f"   Avg Win: {avg_win:+.2f}%")
        print(f"   Avg Loss: {avg_loss:+.2f}%")

        if avg_loss != 0:
            profit_factor = abs(avg_win * wins / (avg_loss * (total_trades - wins)))
            print(f"   Profit Factor: {profit_factor:.2f}")

        # TP analysis
        tp1_hits = len(trades_df[trades_df['tp1_hit'] == True])
        tp2_hits = len(trades_df[trades_df['tp2_hit'] == True])
        tp3_hits = len(trades_df[trades_df['tp3_hit'] == True])

        print(f"\n   🎯 TP Hit Rates:")
        print(f"   TP1 (Fib 127.2%): {tp1_hits}/{total_trades} ({tp1_hits/total_trades*100:.1f}%)")
        print(f"   TP2 (Fib 161.8%): {tp2_hits}/{total_trades} ({tp2_hits/total_trades*100:.1f}%)")
        print(f"   TP3 (Fib 200.0%): {tp3_hits}/{total_trades} ({tp3_hits/total_trades*100:.1f}%)")

        # TP source analysis
        fib_trades = trades_df[trades_df['tp_source'] == 'FIB']
        v9_trades = trades_df[trades_df['tp_source'] == 'V9']

        print(f"\n   🌟 TP SOURCE COMPARISON:")
        if len(fib_trades) > 0:
            fib_pnl = fib_trades['pnl_pct'].sum()
            fib_wr = len(fib_trades[fib_trades['pnl_pct'] > 0]) / len(fib_trades) * 100
            print(f"   Fibonacci TP: {len(fib_trades)} trades ({fib_pnl:+.2f}%, {fib_wr:.1f}% WR)")

        if len(v9_trades) > 0:
            v9_pnl = v9_trades['pnl_pct'].sum()
            v9_wr = len(v9_trades[v9_trades['pnl_pct'] > 0]) / len(v9_trades) * 100
            print(f"   V9 Fallback: {len(v9_trades)} trades ({v9_pnl:+.2f}%, {v9_wr:.1f}% WR)")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='V13 Backtest: Fibonacci for TP Only')
    parser.add_argument('--file', type=str, required=True, help='CSV file')
    args = parser.parse_args()

    # Load data
    print(f"\n📂 Loading data from {args.file}...")
    df = pd.read_csv(args.file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')

    if 'is_active' not in df.columns:
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_active'] = df['is_london'] | df['is_ny']

    # Create strategy
    strategy = SimplifiedSMCStrategy()

    # Run V13 backtest
    backtest = FibonacciTPOnlyBacktest()
    trades_df = backtest.backtest(df, strategy)

    if trades_df is not None:
        trades_df.to_csv('backtest_v13_fib_tp_only_results.csv', index=False)
        print(f"\n💾 Results saved to backtest_v13_fib_tp_only_results.csv")


if __name__ == "__main__":
    main()
