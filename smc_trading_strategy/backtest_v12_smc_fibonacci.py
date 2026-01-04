"""
V12: SMC + Fibonacci Integration
Комбинация Smart Money Concepts с уровнями Фибоначчи

НОВЫЕ ЭЛЕМЕНТЫ:
1. Fibonacci Retracement для зон входа (38.2%, 50%, 61.8%)
2. Fibonacci Extensions для TP уровней (127.2%, 161.8%, 200%)
3. Вход только если цена на ключевом Fib уровне
4. Динамические TP на основе Fibonacci от swing range

ЛОГИКА:
- SMC определяет НАПРАВЛЕНИЕ (BOS, OB, FVG)
- Fibonacci определяет ТОЧКУ ВХОДА (ретрейсмент от последнего swing)
- Fibonacci Extensions определяют ЦЕЛИ (TP1/TP2/TP3)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from simplified_smc_strategy import SimplifiedSMCStrategy


class SMCFibonacciBacktest:
    """V12: SMC + Fibonacci integration"""

    def __init__(self, spread_points=2.0, commission_points=0.5, swap_per_day=-0.3):
        self.spread = spread_points
        self.commission = commission_points
        self.swap_per_day = swap_per_day

        # Fibonacci retracement levels (для входа)
        self.fib_retracement = {
            '0.236': 0.236,
            '0.382': 0.382,
            '0.500': 0.500,
            '0.618': 0.618,  # Golden ratio
            '0.786': 0.786,
        }

        # Fibonacci extension levels (для TP)
        self.fib_extension = {
            '1.272': 1.272,  # TP1
            '1.618': 1.618,  # TP2 - Golden ratio
            '2.000': 2.000,  # TP3
        }

        # V9 базовые параметры для fallback
        self.long_trend_trailing = 25
        self.long_range_trailing = 20
        self.short_trend_trailing = 13
        self.long_trend_timeout = 60
        self.long_range_timeout = 48
        self.short_trend_timeout = 24

        # Partial close (V9)
        self.close_pct1 = 0.3
        self.close_pct2 = 0.3
        self.close_pct3 = 0.4

        # Fibonacci tolerance (пункты от уровня)
        self.fib_tolerance_points = 5.0  # +/- 5 пунктов от Fib уровня

        # Settings
        self.short_range_enabled = False
        self.max_trades_per_day = 10
        self.max_positions = 5

    def calculate_fibonacci_levels(self, swing_high, swing_low, direction='LONG'):
        """
        Рассчитать уровни Фибоначчи от swing range

        Args:
            swing_high: Максимум swing
            swing_low: Минимум swing
            direction: 'LONG' или 'SHORT'

        Returns:
            dict с Fib уровнями
        """
        swing_range = swing_high - swing_low

        fib_levels = {}

        if direction == 'LONG':
            # Для LONG: ретрейсмент от HIGH вниз
            for level_name, level_value in self.fib_retracement.items():
                fib_price = swing_high - (swing_range * level_value)
                fib_levels[f'ret_{level_name}'] = fib_price

            # Extensions от LOW вверх
            for level_name, level_value in self.fib_extension.items():
                fib_price = swing_low + (swing_range * level_value)
                fib_levels[f'ext_{level_name}'] = fib_price

        else:  # SHORT
            # Для SHORT: ретрейсмент от LOW вверх
            for level_name, level_value in self.fib_retracement.items():
                fib_price = swing_low + (swing_range * level_value)
                fib_levels[f'ret_{level_name}'] = fib_price

            # Extensions от HIGH вниз
            for level_name, level_value in self.fib_extension.items():
                fib_price = swing_high - (swing_range * level_value)
                fib_levels[f'ext_{level_name}'] = fib_price

        return fib_levels

    def is_near_fib_level(self, price, fib_levels, tolerance):
        """
        Проверить находится ли цена рядом с ключевым Fib уровнем

        Args:
            price: Текущая цена
            fib_levels: Dict с Fib уровнями
            tolerance: Допуск в пунктах

        Returns:
            (bool, level_name) - находится ли на уровне и какой
        """
        # Проверяем ключевые уровни ретрейсмента
        key_levels = ['ret_0.382', 'ret_0.500', 'ret_0.618']

        for level_name in key_levels:
            if level_name in fib_levels:
                fib_price = fib_levels[level_name]
                if abs(price - fib_price) <= tolerance:
                    return True, level_name

        return False, None

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

    def find_recent_swing_range(self, df, current_idx, direction, lookback=50):
        """
        Найти последний swing range для Fibonacci расчетов

        Args:
            df: DataFrame
            current_idx: Текущий индекс
            direction: 'LONG' или 'SHORT'
            lookback: Сколько свечей назад искать

        Returns:
            (swing_high, swing_low) или (None, None)
        """
        start_idx = max(0, current_idx - lookback)
        recent_data = df.iloc[start_idx:current_idx]

        if len(recent_data) < 10:
            return None, None

        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()

        # Проверка что range адекватный
        swing_range = swing_high - swing_low
        if swing_range < 10:  # Минимум 10 пунктов
            return None, None

        return swing_high, swing_low

    def backtest(self, df, strategy):
        """Run V12 backtest with SMC + Fibonacci"""

        print(f"\n{'='*80}")
        print(f"📊 V12: SMC + FIBONACCI INTEGRATION")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")

        print(f"\n   🌟 FIBONACCI SETTINGS:")
        print(f"   Entry levels: 38.2%, 50%, 61.8% retracement")
        print(f"   TP levels: 127.2%, 161.8%, 200% extension")
        print(f"   Tolerance: +/- {self.fib_tolerance_points} points")

        print(f"\n   ✨ PARTIAL CLOSE (V9):")
        print(f"   {int(self.close_pct1*100)}% на TP1, {int(self.close_pct2*100)}% на TP2, {int(self.close_pct3*100)}% на TP3")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())

        # Track trades and positions
        trades = []
        open_positions = []

        # Stats
        total_signals = 0
        fib_filtered = 0
        fib_accepted = 0

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

                # FILTER SHORT IN RANGE
                if signal == -1 and regime == 'RANGE' and not self.short_range_enabled:
                    continue

                direction = 'LONG' if signal == 1 else 'SHORT'

                # Find swing range for Fibonacci
                swing_high, swing_low = self.find_recent_swing_range(df_strategy, i, direction)

                if swing_high is None or swing_low is None:
                    fib_filtered += 1
                    continue

                # Calculate Fibonacci levels
                fib_levels = self.calculate_fibonacci_levels(swing_high, swing_low, direction)

                # Check if price is near key Fib level
                near_fib, fib_level_name = self.is_near_fib_level(close, fib_levels, self.fib_tolerance_points)

                if not near_fib:
                    fib_filtered += 1
                    continue

                fib_accepted += 1

                # Check max positions
                if len(open_positions) >= self.max_positions:
                    continue

                # Calculate entry and SL
                signal_sl = candle.get('stop_loss', close)

                if direction == 'LONG':
                    entry_price = close + self.spread / 2
                    sl_distance = close - signal_sl
                    sl_price = entry_price - sl_distance

                    # TP from Fibonacci extensions
                    tp1_price = fib_levels['ext_1.272']
                    tp2_price = fib_levels['ext_1.618']
                    tp3_price = fib_levels['ext_2.000']

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

                    # TP from Fibonacci extensions
                    tp1_price = fib_levels['ext_1.272']
                    tp2_price = fib_levels['ext_1.618']
                    tp3_price = fib_levels['ext_2.000']

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
                    'fib_level': fib_level_name,
                    'swing_high': swing_high,
                    'swing_low': swing_low,
                    'trailing_high': entry_price if direction == 'LONG' else 0,
                    'trailing_low': entry_price if direction == 'SHORT' else 999999,
                    'position_remaining': 1.0,
                    'total_pnl_pct': 0.0,
                }

                open_positions.append(new_pos)

            # Update all open positions
            positions_to_close = []

            for pos_idx, pos in enumerate(open_positions):
                entry_time = pos['entry_time']
                entry_price = pos['entry_price']
                direction = pos['direction']
                trailing_distance = pos['trailing_distance']
                timeout_hours = pos['timeout_hours']

                if entry_time == candle_time:
                    continue

                # Check timeout
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

                # Check SL/TP for LONG
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

                    # TP checks
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

                else:  # SHORT
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

            # Remove closed
            for idx in sorted(positions_to_close, reverse=True):
                del open_positions[idx]

        if len(trades) == 0:
            print("❌ No completed trades")
            return None

        trades_df = pd.DataFrame(trades)

        # Print Fibonacci filter stats
        print(f"\n{'='*80}")
        print(f"🌟 FIBONACCI FILTER STATISTICS")
        print(f"{'='*80}")
        print(f"   Total SMC signals: {total_signals}")
        print(f"   Filtered by Fib: {fib_filtered} ({fib_filtered/total_signals*100:.1f}%)")
        print(f"   Accepted (on Fib level): {fib_accepted} ({fib_accepted/total_signals*100:.1f}%)")

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
            'fib_level': pos['fib_level'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'tp1_price': pos['tp1_price'],
            'tp2_price': pos['tp2_price'],
            'tp3_price': pos['tp3_price'],
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

        # Fib level analysis
        print(f"\n   🌟 ENTRY FIB LEVELS:")
        fib_level_counts = trades_df['fib_level'].value_counts()
        for level, count in fib_level_counts.items():
            level_trades = trades_df[trades_df['fib_level'] == level]
            level_pnl = level_trades['pnl_pct'].sum()
            level_wr = len(level_trades[level_trades['pnl_pct'] > 0]) / len(level_trades) * 100
            print(f"   {level}: {count} trades ({level_pnl:+.2f}%, {level_wr:.1f}% WR)")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='V12 Backtest: SMC + Fibonacci Integration')
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

    # Run V12 backtest
    backtest = SMCFibonacciBacktest()
    trades_df = backtest.backtest(df, strategy)

    if trades_df is not None:
        trades_df.to_csv('backtest_v12_smc_fibonacci_results.csv', index=False)
        print(f"\n💾 Results saved to backtest_v12_smc_fibonacci_results.csv")


if __name__ == "__main__":
    main()
