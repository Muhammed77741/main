"""
V11: Тест разных вариантов частичного закрытия позиции

ТЕСТИРУЕМ:
1. V9 baseline: 30%/30%/40% (текущий чемпион)
2. V11a: 50%/25%/25% - агрессивное взятие прибыли на TP1
3. V11b: 60%/20%/20% - максимально агрессивное на TP1
4. V11c: 40%/35%/25% - сбалансированный вариант

ЦЕЛЬ: Найти оптимальное распределение для максимизации прибыли
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from simplified_smc_strategy import SimplifiedSMCStrategy


class PartialCloseVariationsBacktest:
    """V11: Тест разных вариантов partial close"""

    def __init__(self, spread_points=2.0, commission_points=0.5, swap_per_day=-0.3):
        self.spread = spread_points
        self.commission = commission_points
        self.swap_per_day = swap_per_day

        # V9 базовые параметры (лучшие)
        # LONG TREND
        self.long_trend_tp1 = 35
        self.long_trend_tp2 = 65
        self.long_trend_tp3 = 100
        self.long_trend_trailing = 25
        self.long_trend_timeout = 60

        # LONG RANGE
        self.long_range_tp1 = 25
        self.long_range_tp2 = 45
        self.long_range_tp3 = 65
        self.long_range_trailing = 20
        self.long_range_timeout = 48

        # SHORT TREND
        self.short_trend_tp1 = 18
        self.short_trend_tp2 = 30
        self.short_trend_tp3 = 42
        self.short_trend_trailing = 13
        self.short_trend_timeout = 24

        # SHORT RANGE - DISABLED
        self.short_range_enabled = False

        # Limits
        self.max_trades_per_day = 10
        self.max_positions = 5

    def detect_market_regime(self, df, current_idx, lookback=100):
        """Detect market regime: TREND or RANGE"""
        if current_idx < lookback:
            return 'RANGE'

        recent_data = df.iloc[current_idx - lookback:current_idx]

        # 5-signal system
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

    def backtest(self, df, strategy, close_pct1=0.3, close_pct2=0.3, close_pct3=0.4, variant_name="V9"):
        """Run backtest with specific partial close percentages"""

        print(f"\n{'='*80}")
        print(f"📊 {variant_name}: Partial Close {int(close_pct1*100)}%/{int(close_pct2*100)}%/{int(close_pct3*100)}%")
        print(f"{'='*80}")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())

        # Track trades and positions
        trades = []
        open_positions = []

        # Stats
        trend_signals = 0
        range_signals = 0
        short_filtered_range = 0

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
                regime = self.detect_market_regime(df_strategy, i)

                # FILTER SHORT IN RANGE
                if signal == -1 and regime == 'RANGE' and not self.short_range_enabled:
                    short_filtered_range += 1
                    continue

                direction = 'LONG' if signal == 1 else 'SHORT'

                if direction == 'LONG':
                    if regime == 'TREND':
                        tp1, tp2, tp3 = self.long_trend_tp1, self.long_trend_tp2, self.long_trend_tp3
                        trailing = self.long_trend_trailing
                        timeout = self.long_trend_timeout
                        trend_signals += 1
                    else:
                        tp1, tp2, tp3 = self.long_range_tp1, self.long_range_tp2, self.long_range_tp3
                        trailing = self.long_range_trailing
                        timeout = self.long_range_timeout
                        range_signals += 1
                else:
                    tp1, tp2, tp3 = self.short_trend_tp1, self.short_trend_tp2, self.short_trend_tp3
                    trailing = self.short_trend_trailing
                    timeout = self.short_trend_timeout
                    trend_signals += 1

                if len(open_positions) >= self.max_positions:
                    continue

                signal_sl = candle.get('stop_loss', close)

                if direction == 'LONG':
                    entry_price = close + self.spread / 2
                    sl_distance = close - signal_sl
                    sl_price = entry_price - sl_distance
                    tp1_price = entry_price + tp1
                    tp2_price = entry_price + tp2
                    tp3_price = entry_price + tp3
                else:
                    entry_price = close - self.spread / 2
                    sl_distance = signal_sl - close
                    sl_price = entry_price + sl_distance
                    tp1_price = entry_price - tp1
                    tp2_price = entry_price - tp2
                    tp3_price = entry_price - tp3

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

                    # TP checks (reverse order: TP3, TP2, TP1)
                    if high >= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct1, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = high - trailing_distance

                    if high >= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct2, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    if high >= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] - self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct3, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct3
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
                            close_pct1, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = low + trailing_distance

                    if low <= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct2, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    if low <= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] + self.spread / 2
                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct3, hours_in_trade
                        )
                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct3
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

        # Print results
        self._print_results(trades_df, variant_name)

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

    def _print_results(self, trades_df, variant_name):
        """Print results"""
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = trades_df['pnl_pct'].sum()
        total_points = trades_df['pnl_points'].sum()

        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if total_trades - wins > 0 else 0

        print(f"\n   📈 {variant_name} RESULTS:")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Total Points: {total_points:+.1f}п")
        print(f"   Win Rate: {win_rate:.1f}%")
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
        print(f"   TP1: {tp1_hits}/{total_trades} ({tp1_hits/total_trades*100:.1f}%)")
        print(f"   TP2: {tp2_hits}/{total_trades} ({tp2_hits/total_trades*100:.1f}%)")
        print(f"   TP3: {tp3_hits}/{total_trades} ({tp3_hits/total_trades*100:.1f}%)")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='V11 Backtest: Test different partial close variations')
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

    # Create backtest instance
    backtest = PartialCloseVariationsBacktest()

    # Test all variations
    results = {}

    print(f"\n{'='*80}")
    print(f"🧪 TESTING 4 VARIATIONS OF PARTIAL CLOSE")
    print(f"{'='*80}")

    # V9 baseline (30/30/40)
    results['V9'] = backtest.backtest(df, strategy,
                                      close_pct1=0.3, close_pct2=0.3, close_pct3=0.4,
                                      variant_name="V9 (baseline)")

    # V11a (50/25/25)
    results['V11a'] = backtest.backtest(df, strategy,
                                        close_pct1=0.5, close_pct2=0.25, close_pct3=0.25,
                                        variant_name="V11a (50/25/25)")

    # V11b (60/20/20)
    results['V11b'] = backtest.backtest(df, strategy,
                                        close_pct1=0.6, close_pct2=0.2, close_pct3=0.2,
                                        variant_name="V11b (60/20/20)")

    # V11c (40/35/25)
    results['V11c'] = backtest.backtest(df, strategy,
                                        close_pct1=0.4, close_pct2=0.35, close_pct3=0.25,
                                        variant_name="V11c (40/35/25)")

    # Compare results
    print(f"\n{'='*80}")
    print(f"📊 COMPARISON OF ALL VARIATIONS")
    print(f"{'='*80}")

    comparison = []
    for name, trades_df in results.items():
        if trades_df is not None:
            total_pnl = trades_df['pnl_pct'].sum()
            wins = len(trades_df[trades_df['pnl_pct'] > 0])
            win_rate = wins / len(trades_df) * 100

            avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
            losses = len(trades_df) - wins
            avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0
            pf = abs(avg_win * wins / (avg_loss * losses)) if avg_loss != 0 and losses > 0 else 0

            comparison.append({
                'Variant': name,
                'Total_PnL': total_pnl,
                'Win_Rate': win_rate,
                'Profit_Factor': pf,
                'Trades': len(trades_df)
            })

    comp_df = pd.DataFrame(comparison).sort_values('Total_PnL', ascending=False)

    print("\n" + comp_df.to_string(index=False))

    # Find best
    best = comp_df.iloc[0]
    print(f"\n{'='*80}")
    print(f"🏆 WINNER: {best['Variant']}")
    print(f"{'='*80}")
    print(f"   Total PnL: {best['Total_PnL']:+.2f}%")
    print(f"   Win Rate: {best['Win_Rate']:.1f}%")
    print(f"   Profit Factor: {best['Profit_Factor']:.2f}")

    # Save best result
    best_variant = best['Variant']
    if results[best_variant] is not None:
        results[best_variant].to_csv(f'backtest_v11_{best_variant}_results.csv', index=False)
        print(f"\n💾 Best result saved to backtest_v11_{best_variant}_results.csv")


if __name__ == "__main__":
    main()
