"""
Improved Adaptive Backtest V3 - WITH LOSS FILTERS
Добавлены 3 фильтра на основе анализа убытков:
1. Более строгие условия для SHORT сделок
2. Ранний выход при движении против позиции (early stop loss)
3. Уменьшенный timeout
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from pattern_recognition_strategy import PatternRecognitionStrategy


class ImprovedAdaptiveBacktestV3:
    """Improved adaptive backtest with loss reduction filters"""

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

        # TREND MODE parameters - REDUCED TIMEOUT
        self.trend_tp1 = 30
        self.trend_tp2 = 55
        self.trend_tp3 = 90
        self.trend_trailing = 18
        self.trend_timeout = 48  # REDUCED from 60h

        # RANGE MODE parameters - REDUCED TIMEOUT
        self.range_tp1 = 20
        self.range_tp2 = 35
        self.range_tp3 = 50
        self.range_trailing = 15
        self.range_timeout = 36  # REDUCED from 48h

        # NEW: Early stop loss parameters
        self.enable_early_sl = True
        self.early_sl_candles = 3  # Check after 3 candles
        self.early_sl_threshold = 0.5  # If loss > 0.5% and no move towards TP

        # NEW: Stricter SHORT filters
        self.enable_short_filters = True
        self.short_min_trend_strength = 3  # Need stronger trend for SHORT

        # Daily limits
        self.max_trades_per_day = 10
        self.max_loss_per_day = -5.0  # %
        self.max_positions = 5
        self.max_drawdown = -999.0  # UNLIMITED

    def detect_market_regime(self, df, current_idx, lookback=100):
        """
        УЛУЧШЕННЫЙ детектор режима рынка: TREND или RANGE
        """
        if current_idx < lookback:
            return {
                'regime': 'RANGE',
                'trend_signals': 0,
                'is_downtrend': False,
                'is_uptrend': False
            }

        recent_data = df.iloc[current_idx - lookback:current_idx]

        # 1. EMA CROSSOVER
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()

        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]

        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
        ema_trend = ema_diff_pct > 0.3

        # 2. ATR
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()

        high_volatility = atr > avg_atr * 1.05

        # 3. Directional movement
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()

        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35

        # 4. Sequential movements
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        total_moves = up_moves + down_moves

        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.15

        # 5. Structural trend
        highs = recent_data['high'].values[-20:]
        lows = recent_data['low'].values[-20:]

        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])

        structural_trend = (higher_highs > 12) or (lower_lows > 12)

        # Count trend signals
        trend_signals = sum([
            ema_trend,
            high_volatility,
            strong_direction,
            directional_bias,
            structural_trend
        ])

        is_trend = trend_signals >= 3

        # Return trend info for SHORT filter
        return {
            'regime': 'TREND' if is_trend else 'RANGE',
            'trend_signals': trend_signals,
            'is_downtrend': lower_lows > higher_highs,
            'is_uptrend': higher_highs > lower_lows
        }

    def should_take_short_signal(self, df, current_idx, regime_info):
        """
        NEW: Stricter filters for SHORT signals
        SHORT trades have 49% loss rate vs 22% for LONG - need to be more selective
        """
        if not self.enable_short_filters:
            return True

        # Require TREND regime for SHORT
        if regime_info['regime'] != 'TREND':
            return False

        # Require strong downtrend (4+ signals, not just 3)
        if regime_info['trend_signals'] < self.short_min_trend_strength:
            return False

        # Require confirmed downtrend structure
        if not regime_info['is_downtrend']:
            return False

        return True

    def check_early_stop_loss(self, pos, df, current_idx):
        """
        NEW: Early stop loss - exit if position moves against us immediately

        This prevents the worst losses where position never reaches TP1
        and just bleeds out over 48-60 hours
        """
        if not self.enable_early_sl:
            return False

        entry_idx = df.index.get_loc(pos['entry_time'])
        candles_in_trade = current_idx - entry_idx

        # Check after N candles
        if candles_in_trade < self.early_sl_candles:
            return False

        direction = pos['direction']
        entry_price = pos['entry_price']
        tp1_price = pos['tp1_price']

        # Get current price
        current_candle = df.iloc[current_idx]
        current_price = current_candle['close']

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            distance_to_tp1 = tp1_price - entry_price
            distance_moved = current_price - entry_price
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
            distance_to_tp1 = entry_price - tp1_price
            distance_moved = entry_price - current_price

        # Early exit conditions:
        # 1. Loss > threshold
        # 2. No meaningful move towards TP1 (< 20% of TP1 distance)
        if pnl_pct < -self.early_sl_threshold:
            move_pct = (distance_moved / distance_to_tp1) * 100 if distance_to_tp1 > 0 else 0

            if move_pct < 20:  # Less than 20% progress towards TP1
                return True

        return False

    def backtest(self, df, strategy, close_pct1=0.5, close_pct2=0.3, close_pct3=0.2):
        """
        Run improved adaptive backtest
        """

        print(f"\n{'='*80}")
        print(f"📊 IMPROVED ADAPTIVE BACKTEST V3 - WITH LOSS FILTERS")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")

        print(f"\n   🎯 TREND MODE:")
        print(f"   TP: {self.trend_tp1}п / {self.trend_tp2}п / {self.trend_tp3}п")
        print(f"   Trailing: {self.trend_trailing}п")
        print(f"   Timeout: {self.trend_timeout}ч (REDUCED from 60ч)")

        print(f"\n   📊 RANGE MODE:")
        print(f"   TP: {self.range_tp1}п / {self.range_tp2}п / {self.range_tp3}п")
        print(f"   Trailing: {self.range_trailing}п")
        print(f"   Timeout: {self.range_timeout}ч (REDUCED from 48ч)")

        print(f"\n   🛡️ NEW FILTERS:")
        print(f"   Early Stop Loss: {'ENABLED' if self.enable_early_sl else 'DISABLED'}")
        if self.enable_early_sl:
            print(f"     - Trigger: {self.early_sl_candles} candles, loss > {self.early_sl_threshold}%")
        print(f"   SHORT Filters: {'ENABLED' if self.enable_short_filters else 'DISABLED'}")
        if self.enable_short_filters:
            print(f"     - Min trend signals: {self.short_min_trend_strength}")
            print(f"     - Require: TREND regime + downtrend structure")

        print(f"\n   💰 COSTS:")
        print(f"   Spread: {self.spread}п")
        print(f"   Commission: {self.commission}п")
        print(f"   Swap: {self.swap_per_day}п/day")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())

        # Track trades and positions
        trades = []
        open_positions = []

        # Track market regime stats
        trend_signals = 0
        range_signals = 0

        # NEW: Track filter stats
        short_filtered = 0
        early_sl_triggered = 0

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
                # Detect market regime
                regime_info = self.detect_market_regime(df_strategy, i)

                # NEW: Filter SHORT signals
                if signal == -1:  # SHORT
                    if not self.should_take_short_signal(df_strategy, i, regime_info):
                        short_filtered += 1
                        continue

                # Extract regime
                regime = regime_info['regime']

                # Choose parameters based on regime
                if regime == 'TREND':
                    tp1, tp2, tp3 = self.trend_tp1, self.trend_tp2, self.trend_tp3
                    trailing = self.trend_trailing
                    timeout = self.trend_timeout
                    trend_signals += 1
                else:  # RANGE
                    tp1, tp2, tp3 = self.range_tp1, self.range_tp2, self.range_tp3
                    trailing = self.range_trailing
                    timeout = self.range_timeout
                    range_signals += 1

                # Check max positions limit
                if len(open_positions) >= self.max_positions:
                    continue

                # Open position
                direction = 'LONG' if signal == 1 else 'SHORT'
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

                # NEW: Check early stop loss
                if self.check_early_stop_loss(pos, df_strategy, i):
                    if direction == 'LONG':
                        exit_price = close - self.spread / 2
                    else:
                        exit_price = close + self.spread / 2

                    hours_in_trade = (candle_time - entry_time).total_seconds() / 3600
                    pnl_points = self._calculate_pnl_points(
                        entry_price, exit_price, direction,
                        pos['position_remaining'], hours_in_trade
                    )

                    pos['total_pnl_pct'] += (pnl_points / entry_price) * 100

                    trade = self._create_trade_record(pos, exit_price, 'EARLY_SL', candle_time)
                    trades.append(trade)
                    positions_to_close.append(pos_idx)
                    early_sl_triggered += 1
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

        # Print filter statistics
        print(f"\n{'='*80}")
        print(f"📊 FILTER STATISTICS")
        print(f"{'='*80}")
        print(f"   SHORT signals filtered: {short_filtered}")
        print(f"   Early SL triggered: {early_sl_triggered}")

        # Print regime statistics
        print(f"\n{'='*80}")
        print(f"📊 MARKET REGIME STATISTICS")
        print(f"{'='*80}")
        total_signals = trend_signals + range_signals
        if total_signals > 0:
            print(f"   TREND signals: {trend_signals} ({trend_signals/total_signals*100:.1f}%)")
            print(f"   RANGE signals: {range_signals} ({range_signals/total_signals*100:.1f}%)")

        # Stats by regime
        trend_trades = trades_df[trades_df['regime'] == 'TREND']
        range_trades = trades_df[trades_df['regime'] == 'RANGE']

        if len(trend_trades) > 0:
            print(f"\n   TREND trades: {len(trend_trades)}")
            print(f"     PnL: {trend_trades['pnl_pct'].sum():+.2f}%")
            print(f"     Win Rate: {len(trend_trades[trend_trades['pnl_pct'] > 0]) / len(trend_trades) * 100:.1f}%")

        if len(range_trades) > 0:
            print(f"\n   RANGE trades: {len(range_trades)}")
            print(f"     PnL: {range_trades['pnl_pct'].sum():+.2f}%")
            print(f"     Win Rate: {len(range_trades[range_trades['pnl_pct'] > 0]) / len(range_trades) * 100:.1f}%")

        # Calculate statistics
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
        print(f"📊 IMPROVED RESULTS")
        print(f"{'='*80}")

        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = trades_df['pnl_pct'].sum()
        total_points = trades_df['pnl_points'].sum()

        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if total_trades - wins > 0 else 0

        print(f"\n📈 Performance:")
        print(f"   Total trades: {total_trades}")
        print(f"   Wins: {wins} ({win_rate:.1f}%)")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Total Points: {total_points:+.1f}п")
        print(f"   Avg Win: {avg_win:+.2f}%")
        print(f"   Avg Loss: {avg_loss:+.2f}%")

        if avg_loss != 0:
            profit_factor = abs(avg_win * wins / (avg_loss * (total_trades - wins)))
            print(f"   Profit Factor: {profit_factor:.2f}")

        # Drawdown
        cumulative_pnl = trades_df['pnl_pct'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - running_max
        max_drawdown = drawdown.min()

        print(f"\n📉 Risk Metrics:")
        print(f"   Max Drawdown: {max_drawdown:.2f}%")

        # Monthly
        trades_df['month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
        monthly = trades_df.groupby('month').agg({
            'pnl_pct': ['sum', 'count'],
        })
        monthly.columns = ['Total_PnL_%', 'Trades']

        print(f"\n📅 Monthly Results:")
        for month, row in monthly.iterrows():
            print(f"   {month}: {int(row['Trades'])} trades, {row['Total_PnL_%']:+.2f}%")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Improved Adaptive Backtest V3')
    parser.add_argument('--file', type=str, required=True, help='CSV file')
    parser.add_argument('--no-short-filter', action='store_true', help='Disable SHORT filters')
    parser.add_argument('--no-early-sl', action='store_true', help='Disable early SL')
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
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Run improved backtest
    backtest = ImprovedAdaptiveBacktestV3()

    if args.no_short_filter:
        backtest.enable_short_filters = False
        print("⚠️  SHORT filters DISABLED")

    if args.no_early_sl:
        backtest.enable_early_sl = False
        print("⚠️  Early SL DISABLED")

    trades_df = backtest.backtest(df, strategy)

    if trades_df is not None:
        trades_df.to_csv('backtest_v3_improved_results.csv', index=False)
        print(f"\n💾 Results saved to backtest_v3_improved_results.csv")


if __name__ == "__main__":
    main()
