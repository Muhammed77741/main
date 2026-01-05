"""
Тест входов на уровнях Фибоначчи (V12 улучшенный)

ЦЕЛЬ: Проверить работают ли входы на Fibonacci retracement лучше чем обычные SMC входы

ЛОГИКА:
1. SMC генерирует сигнал (BOS, OB, FVG)
2. Проверяем находится ли цена на Fib уровне (38.2%, 50%, 61.8%, 78.6%)
3. Если ДА - принимаем сигнал
4. Если НЕТ - пропускаем

СТАТИСТИКА:
- Сколько сигналов отфильтровано
- Какой уровень Фибо самый прибыльный
- Win rate по каждому уровню
- Сравнение с базовой стратегией (без фильтрации)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simplified_smc_strategy import SimplifiedSMCStrategy
from mt5_data_downloader import MT5DataDownloader


class FibonacciEntryTest:
    """Тест входов на уровнях Фибоначчи"""

    def __init__(self, spread_points=2.0, commission_points=0.5, swap_per_day=-0.3):
        self.spread = spread_points
        self.commission = commission_points
        self.swap_per_day = swap_per_day

        # Fibonacci retracement levels для входа
        self.fib_levels = {
            '38.2%': 0.382,
            '50.0%': 0.500,
            '61.8%': 0.618,  # Золотое сечение
            '78.6%': 0.786,
        }

        # Допуск в пунктах от Fib уровня
        self.fib_tolerance_points = 8.0  # +/- 8 пунктов

        # Swing lookback для расчета Fib уровней
        self.swing_lookback = 50

        # Fixed TP/SL параметры (базовая стратегия)
        self.long_tp = 65
        self.short_tp = 30
        self.trailing = 20
        self.timeout_hours = 48

        # Settings
        self.short_range_enabled = False
        self.max_positions = 5

    def find_swing_range(self, df, current_idx, direction, lookback=50):
        """
        Найти swing range для Fibonacci расчетов

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

    def calculate_fibonacci_levels(self, swing_high, swing_low, direction):
        """
        Рассчитать уровни Фибоначчи для входа

        Args:
            swing_high: Максимум swing
            swing_low: Минимум swing
            direction: 'LONG' или 'SHORT'

        Returns:
            dict с Fib уровнями
        """
        swing_range = swing_high - swing_low
        fib_prices = {}

        if direction == 'LONG':
            # Для LONG: ретрейсмент от HIGH вниз (откат после роста)
            for level_name, level_value in self.fib_levels.items():
                fib_price = swing_high - (swing_range * level_value)
                fib_prices[level_name] = fib_price
        else:  # SHORT
            # Для SHORT: ретрейсмент от LOW вверх (откат после падения)
            for level_name, level_value in self.fib_levels.items():
                fib_price = swing_low + (swing_range * level_value)
                fib_prices[level_name] = fib_price

        return fib_prices

    def check_near_fib_level(self, price, fib_prices, tolerance):
        """
        Проверить находится ли цена рядом с любым Fib уровнем

        Args:
            price: Текущая цена
            fib_prices: Dict с Fib уровнями
            tolerance: Допуск в пунктах

        Returns:
            (bool, level_name) - находится ли на уровне и какой
        """
        for level_name, fib_price in fib_prices.items():
            if abs(price - fib_price) <= tolerance:
                return True, level_name

        return False, None

    def detect_market_regime(self, df, current_idx, lookback=100):
        """Определить режим рынка: TREND или RANGE"""
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

        trend_signals = sum([ema_trend, high_volatility, strong_direction])
        return 'TREND' if trend_signals >= 2 else 'RANGE'

    def backtest(self, df, strategy):
        """Run backtest with Fibonacci entry filtering"""

        print(f"\n{'='*80}")
        print(f"📊 FIBONACCI ENTRY FILTER TEST")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")
        print(f"\n   🎯 FIBONACCI ENTRY LEVELS:")
        print(f"   38.2% - слабый откат")
        print(f"   50.0% - половина движения")
        print(f"   61.8% - золотое сечение ⭐")
        print(f"   78.6% - глубокий откат")
        print(f"   Tolerance: +/- {self.fib_tolerance_points} пунктов")

        # Run strategy to get SMC signals
        df_strategy = strategy.run_strategy(df.copy())

        # Statistics
        stats = {
            'total_signals': 0,
            'fib_accepted': 0,
            'fib_filtered': 0,
            'no_swing_range': 0,
            'trades_by_level': {},
            'wins_by_level': {},
            'pnl_by_level': {},
        }

        for level in self.fib_levels.keys():
            stats['trades_by_level'][level] = 0
            stats['wins_by_level'][level] = 0
            stats['pnl_by_level'][level] = 0.0

        # Track trades
        all_trades = []  # Все возможные SMC сигналы
        fib_trades = []  # Только Fibonacci отфильтрованные

        # Process signals
        for i in range(len(df_strategy)):
            candle = df_strategy.iloc[i]
            candle_time = df_strategy.index[i]
            signal = candle.get('signal', 0)

            if signal == 0:
                continue

            stats['total_signals'] += 1

            regime = self.detect_market_regime(df_strategy, i)
            direction = 'LONG' if signal == 1 else 'SHORT'

            # FILTER SHORT IN RANGE
            if signal == -1 and regime == 'RANGE' and not self.short_range_enabled:
                continue

            entry_price = candle['close']
            signal_sl = candle.get('stop_loss', entry_price)

            # Find swing range
            swing_high, swing_low = self.find_swing_range(df_strategy, i, direction, self.swing_lookback)

            if swing_high is None:
                stats['no_swing_range'] += 1
                continue

            # Calculate Fibonacci levels
            fib_prices = self.calculate_fibonacci_levels(swing_high, swing_low, direction)

            # Check if near Fib level
            near_fib, fib_level = self.check_near_fib_level(entry_price, fib_prices, self.fib_tolerance_points)

            # Log signal for comparison
            signal_data = {
                'time': candle_time,
                'direction': direction,
                'regime': regime,
                'entry': entry_price,
                'sl': signal_sl,
                'swing_range': swing_high - swing_low,
                'near_fib': near_fib,
                'fib_level': fib_level if near_fib else None,
            }

            all_trades.append(signal_data)

            if not near_fib:
                stats['fib_filtered'] += 1
                continue

            # Accept signal
            stats['fib_accepted'] += 1
            stats['trades_by_level'][fib_level] += 1

            # Calculate TP
            if direction == 'LONG':
                tp_price = entry_price + self.long_tp
            else:
                tp_price = entry_price - self.short_tp

            fib_trades.append({
                **signal_data,
                'tp': tp_price,
            })

        # Simulate trades
        print(f"\n{'='*80}")
        print(f"📈 SIMULATING FIBONACCI FILTERED TRADES")
        print(f"{'='*80}")

        completed_trades = self._simulate_trades(df_strategy, fib_trades)

        # Calculate statistics
        self._print_statistics(stats, completed_trades)

        return stats, completed_trades, all_trades

    def _simulate_trades(self, df, trades):
        """Simulate trade execution"""
        completed = []

        for trade in trades:
            entry_time = trade['time']
            entry_price = trade['entry']
            direction = trade['direction']
            sl_price = trade['sl']
            tp_price = trade['tp']

            # Find bars after entry
            entry_idx = df.index.get_loc(entry_time)
            future_bars = df.iloc[entry_idx + 1:entry_idx + 1 + self.timeout_hours]

            if len(future_bars) == 0:
                continue

            # Check SL/TP hit
            exit_price = None
            exit_type = None
            exit_time = None

            for idx, bar in future_bars.iterrows():
                high = bar['high']
                low = bar['low']

                if direction == 'LONG':
                    if low <= sl_price:
                        exit_price = sl_price
                        exit_type = 'SL'
                        exit_time = idx
                        break
                    elif high >= tp_price:
                        exit_price = tp_price
                        exit_type = 'TP'
                        exit_time = idx
                        break
                else:  # SHORT
                    if high >= sl_price:
                        exit_price = sl_price
                        exit_type = 'SL'
                        exit_time = idx
                        break
                    elif low <= tp_price:
                        exit_price = tp_price
                        exit_type = 'TP'
                        exit_time = idx
                        break

            # Timeout exit
            if exit_price is None:
                exit_price = future_bars['close'].iloc[-1]
                exit_type = 'TIMEOUT'
                exit_time = future_bars.index[-1]

            # Calculate PnL
            if direction == 'LONG':
                pnl_points = exit_price - entry_price - self.spread - self.commission
            else:
                pnl_points = entry_price - exit_price - self.spread - self.commission

            pnl_pct = (pnl_points / entry_price) * 100

            completed.append({
                **trade,
                'exit_time': exit_time,
                'exit_price': exit_price,
                'exit_type': exit_type,
                'pnl_points': pnl_points,
                'pnl_pct': pnl_pct,
                'win': pnl_pct > 0,
            })

        return completed

    def _print_statistics(self, stats, completed_trades):
        """Print detailed statistics"""

        print(f"\n{'='*80}")
        print(f"📊 FIBONACCI FILTER STATISTICS")
        print(f"{'='*80}")

        print(f"\n🔍 SIGNAL FILTERING:")
        print(f"   Total SMC signals: {stats['total_signals']}")
        print(f"   ✅ Accepted (near Fib): {stats['fib_accepted']} ({stats['fib_accepted']/stats['total_signals']*100:.1f}%)")
        print(f"   ❌ Filtered (not near Fib): {stats['fib_filtered']} ({stats['fib_filtered']/stats['total_signals']*100:.1f}%)")
        print(f"   ⚠️  No swing range: {stats['no_swing_range']}")

        if len(completed_trades) == 0:
            print("\n❌ No completed trades!")
            return

        # Overall stats
        total_trades = len(completed_trades)
        wins = sum(1 for t in completed_trades if t['win'])
        losses = total_trades - wins
        win_rate = wins / total_trades * 100

        total_pnl_pct = sum(t['pnl_pct'] for t in completed_trades)
        avg_win = sum(t['pnl_pct'] for t in completed_trades if t['win']) / wins if wins > 0 else 0
        avg_loss = sum(t['pnl_pct'] for t in completed_trades if not t['win']) / losses if losses > 0 else 0

        tp_exits = sum(1 for t in completed_trades if t['exit_type'] == 'TP')
        sl_exits = sum(1 for t in completed_trades if t['exit_type'] == 'SL')
        timeout_exits = sum(1 for t in completed_trades if t['exit_type'] == 'TIMEOUT')

        print(f"\n📈 OVERALL RESULTS:")
        print(f"   Total trades: {total_trades}")
        print(f"   Wins: {wins} ({win_rate:.1f}%)")
        print(f"   Losses: {losses} ({100-win_rate:.1f}%)")
        print(f"   Total PnL: {total_pnl_pct:+.2f}%")
        print(f"   Avg Win: {avg_win:+.2f}%")
        print(f"   Avg Loss: {avg_loss:+.2f}%")
        print(f"\n   Exit types:")
        print(f"   🎯 TP: {tp_exits} ({tp_exits/total_trades*100:.1f}%)")
        print(f"   🛑 SL: {sl_exits} ({sl_exits/total_trades*100:.1f}%)")
        print(f"   ⏱️  Timeout: {timeout_exits} ({timeout_exits/total_trades*100:.1f}%)")

        # Stats by Fibonacci level
        print(f"\n🎯 PERFORMANCE BY FIBONACCI LEVEL:")
        print(f"{'─'*80}")
        print(f"{'Level':<15} {'Trades':<10} {'Wins':<10} {'Win Rate':<12} {'Total PnL':<12}")
        print(f"{'─'*80}")

        for level in ['38.2%', '50.0%', '61.8%', '78.6%']:
            level_trades = [t for t in completed_trades if t['fib_level'] == level]
            if len(level_trades) == 0:
                continue

            level_wins = sum(1 for t in level_trades if t['win'])
            level_wr = level_wins / len(level_trades) * 100
            level_pnl = sum(t['pnl_pct'] for t in level_trades)

            emoji = "⭐" if level == '61.8%' else ""
            print(f"{level:<15} {len(level_trades):<10} {level_wins:<10} {level_wr:>6.1f}%     {level_pnl:>+8.2f}% {emoji}")

        print(f"{'─'*80}")

        # Stats by direction
        print(f"\n📊 PERFORMANCE BY DIRECTION:")
        long_trades = [t for t in completed_trades if t['direction'] == 'LONG']
        short_trades = [t for t in completed_trades if t['direction'] == 'SHORT']

        if len(long_trades) > 0:
            long_wins = sum(1 for t in long_trades if t['win'])
            long_wr = long_wins / len(long_trades) * 100
            long_pnl = sum(t['pnl_pct'] for t in long_trades)
            print(f"   🟢 LONG: {len(long_trades)} trades, {long_wr:.1f}% WR, {long_pnl:+.2f}% PnL")

        if len(short_trades) > 0:
            short_wins = sum(1 for t in short_trades if t['win'])
            short_wr = short_wins / len(short_trades) * 100
            short_pnl = sum(t['pnl_pct'] for t in short_trades)
            print(f"   🔴 SHORT: {len(short_trades)} trades, {short_wr:.1f}% WR, {short_pnl:+.2f}% PnL")


def main():
    parser = argparse.ArgumentParser(description='Fibonacci Entry Filter Test')
    parser.add_argument('--symbol', type=str, default='XAUUSD', help='Trading symbol')
    parser.add_argument('--timeframe', type=str, default='H1', help='Timeframe')
    parser.add_argument('--start', type=str, default='2025-01-01', help='Start date')
    parser.add_argument('--end', type=str, default='2025-11-30', help='End date')
    parser.add_argument('--tolerance', type=float, default=8.0, help='Fibonacci tolerance in points')

    args = parser.parse_args()

    print(f"\n🔍 Loading data: {args.symbol} {args.timeframe}")
    print(f"   Period: {args.start} to {args.end}")

    # Load data
    downloader = MT5DataDownloader()
    df = downloader.download_data_csv_fallback(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_date=args.start,
        end_date=args.end
    )

    if df is None or len(df) < 100:
        print("❌ Failed to load data!")
        return

    # Initialize strategy
    strategy = SimplifiedSMCStrategy(
        risk_reward_ratio=2.0,
        risk_per_trade=0.02,
        swing_length=10,
        volume_lookback=2,
        min_candle_quality=50
    )

    # Initialize backtest
    backtest = FibonacciEntryTest(
        spread_points=2.0,
        commission_points=0.5,
        swap_per_day=-0.3
    )
    backtest.fib_tolerance_points = args.tolerance

    # Run backtest
    stats, completed_trades, all_trades = backtest.backtest(df, strategy)

    print(f"\n{'='*80}")
    print(f"✅ BACKTEST COMPLETE!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
