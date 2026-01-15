"""
Adaptive Backtest V3 - FIXED VERSION (3 separate positions)
- Автоматически определяет тренд или боковик
- Открывает 3 ОТДЕЛЬНЫЕ позиции с разными TP (как в live)
- Все 3 позиции имеют общий SL
- Учитывает 3x комиссии (для каждой позиции)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from pattern_recognition_strategy import PatternRecognitionStrategy


class AdaptiveBacktestV3Fixed:
    """Adaptive backtest - 3 separate positions matching live bot logic"""

    def __init__(self, spread_points=4.0, commission_points=0.5, swap_per_day=-0.3):
        """
        Args:
            spread_points: Average spread in points (REALISTIC: 4 for XAUUSD)
            commission_points: Commission per position in points (default: 0.5)
            swap_per_day: Swap cost per day in points (default: -0.3)
        """
        self.spread = spread_points  # Increased to realistic 4 points
        self.commission = commission_points
        self.swap_per_day = swap_per_day

        # TREND MODE parameters (сильный тренд)
        self.trend_tp1 = 30
        self.trend_tp2 = 55
        self.trend_tp3 = 90
        self.trend_trailing = 18
        self.trend_trailing_activation = 30  # Activate after 30p profit
        self.trend_timeout = 60

        # RANGE MODE parameters (боковик)
        self.range_tp1 = 20
        self.range_tp2 = 35
        self.range_tp3 = 50
        self.range_trailing = 15
        self.range_trailing_activation = 20  # Activate after 20p profit
        self.range_timeout = 48

        # Position splits (matching live bot)
        self.pos1_pct = 0.33  # 33% for TP1
        self.pos2_pct = 0.33  # 33% for TP2
        self.pos3_pct = 0.34  # 34% for TP3

        # Daily limits
        self.max_trades_per_day = 10
        self.max_loss_per_day = -5.0  # %
        self.max_positions = 5  # Max position groups (each group = 3 positions)
        self.max_drawdown = -999.0  # UNLIMITED

    def detect_market_regime(self, df, current_idx, lookback=100):
        """
        УЛУЧШЕННЫЙ детектор режима рынка: TREND или RANGE

        Использует:
        1. EMA crossover (тренд определяется пересечением)
        2. ATR (волатильность)
        3. Направленное движение
        4. Последовательные свечи в одном направлении
        5. Higher highs / Lower lows
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

        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.15

        # 5. Последовательные higher highs / lower lows
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

        # TREND if 3+ signals out of 5
        is_trend = trend_signals >= 3

        return 'TREND' if is_trend else 'RANGE'

    def backtest(self, df, strategy):
        """
        Run adaptive backtest with 3 separate positions (matching live bot)
        """

        print(f"\n{'='*80}")
        print(f"📊 ADAPTIVE BACKTEST V3 - FIXED (3 SEPARATE POSITIONS)")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")

        print(f"\n   🎯 TREND MODE:")
        print(f"   TP: {self.trend_tp1}п / {self.trend_tp2}п / {self.trend_tp3}п")
        print(f"   Trailing: {self.trend_trailing}п (after {self.trend_trailing_activation}п profit)")
        print(f"   Timeout: {self.trend_timeout}ч")

        print(f"\n   📊 RANGE MODE:")
        print(f"   TP: {self.range_tp1}п / {self.range_tp2}п / {self.range_tp3}п")
        print(f"   Trailing: {self.range_trailing}п (after {self.range_trailing_activation}п profit)")
        print(f"   Timeout: {self.range_timeout}ч")

        print(f"\n   💰 COSTS (per position):")
        print(f"   Spread: {self.spread}п")
        print(f"   Commission: {self.commission}п")
        print(f"   Swap: {self.swap_per_day}п/day")
        print(f"   Total entry cost: {self.spread + self.commission}п × 3 = {(self.spread + self.commission) * 3}п")

        print(f"\n   📦 POSITION STRUCTURE:")
        print(f"   3 positions per signal: {self.pos1_pct*100:.0f}% / {self.pos2_pct*100:.0f}% / {self.pos3_pct*100:.0f}%")

        print(f"\n   🛡️ RISK LIMITS:")
        print(f"   Max position groups: {self.max_positions} (= {self.max_positions * 3} individual positions)")
        print(f"   Max trades/day: {self.max_trades_per_day}")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())

        # Track trades and positions
        completed_trades = []
        open_positions = []  # List of individual positions
        position_groups = []  # Track groups (for max positions limit)

        # Track market regime stats
        trend_signals = 0
        range_signals = 0

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
                regime = self.detect_market_regime(df_strategy, i)

                # Choose parameters based on regime
                if regime == 'TREND':
                    tp1, tp2, tp3 = self.trend_tp1, self.trend_tp2, self.trend_tp3
                    trailing = self.trend_trailing
                    trailing_activation = self.trend_trailing_activation
                    timeout = self.trend_timeout
                    trend_signals += 1
                else:  # RANGE
                    tp1, tp2, tp3 = self.range_tp1, self.range_tp2, self.range_tp3
                    trailing = self.range_trailing
                    trailing_activation = self.range_trailing_activation
                    timeout = self.range_timeout
                    range_signals += 1

                # Check max positions limit (groups, not individual positions)
                num_groups = len([g for g in position_groups if g['status'] == 'OPEN'])
                if num_groups >= self.max_positions:
                    continue  # Skip if at max position groups

                # Open 3 positions
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

                # Create group ID
                group_id = f"{candle_time.strftime('%Y%m%d%H%M')}_{len(position_groups)}"

                # Create 3 separate positions
                positions_in_group = []

                # Position 1: TP1
                pos1 = {
                    'group_id': group_id,
                    'position_id': f"{group_id}_TP1",
                    'entry_time': candle_time,
                    'entry_price': entry_price,
                    'direction': direction,
                    'sl_price': sl_price,
                    'original_sl': sl_price,
                    'tp_price': tp1_price,
                    'tp_level': 'TP1',
                    'size': self.pos1_pct,
                    'status': 'OPEN',
                    'trailing_active': False,
                    'trailing_distance': trailing,
                    'trailing_activation': trailing_activation,
                    'timeout_hours': timeout,
                    'regime': regime,
                    'best_price': entry_price,
                }
                open_positions.append(pos1)
                positions_in_group.append(pos1)

                # Position 2: TP2
                pos2 = {
                    'group_id': group_id,
                    'position_id': f"{group_id}_TP2",
                    'entry_time': candle_time,
                    'entry_price': entry_price,
                    'direction': direction,
                    'sl_price': sl_price,
                    'original_sl': sl_price,
                    'tp_price': tp2_price,
                    'tp_level': 'TP2',
                    'size': self.pos2_pct,
                    'status': 'OPEN',
                    'trailing_active': False,
                    'trailing_distance': trailing,
                    'trailing_activation': trailing_activation,
                    'timeout_hours': timeout,
                    'regime': regime,
                    'best_price': entry_price,
                }
                open_positions.append(pos2)
                positions_in_group.append(pos2)

                # Position 3: TP3
                pos3 = {
                    'group_id': group_id,
                    'position_id': f"{group_id}_TP3",
                    'entry_time': candle_time,
                    'entry_price': entry_price,
                    'direction': direction,
                    'sl_price': sl_price,
                    'original_sl': sl_price,
                    'tp_price': tp3_price,
                    'tp_level': 'TP3',
                    'size': self.pos3_pct,
                    'status': 'OPEN',
                    'trailing_active': False,
                    'trailing_distance': trailing,
                    'trailing_activation': trailing_activation,
                    'timeout_hours': timeout,
                    'regime': regime,
                    'best_price': entry_price,
                }
                open_positions.append(pos3)
                positions_in_group.append(pos3)

                # Track group
                position_groups.append({
                    'group_id': group_id,
                    'status': 'OPEN',
                    'positions': positions_in_group,
                    'entry_time': candle_time,
                    'regime': regime
                })

            # Update all open positions
            positions_to_close = []

            for pos_idx, pos in enumerate(open_positions):
                if pos['status'] != 'OPEN':
                    continue

                entry_time = pos['entry_time']
                entry_price = pos['entry_price']
                direction = pos['direction']
                trailing_distance = pos['trailing_distance']
                trailing_activation = pos['trailing_activation']
                timeout_hours = pos['timeout_hours']

                if entry_time == candle_time:
                    continue

                # Check timeout
                hours_in_trade = (candle_time - entry_time).total_seconds() / 3600

                if hours_in_trade >= timeout_hours:
                    # Force close
                    if direction == 'LONG':
                        exit_price = close - self.spread / 2
                    else:
                        exit_price = close + self.spread / 2

                    trade = self._close_position(pos, exit_price, 'TIMEOUT', candle_time, hours_in_trade)
                    completed_trades.append(trade)
                    positions_to_close.append(pos_idx)
                    continue

                # Update best price and check trailing activation
                if direction == 'LONG':
                    if high > pos['best_price']:
                        pos['best_price'] = high

                    profit = pos['best_price'] - entry_price
                    if profit >= trailing_activation and not pos['trailing_active']:
                        pos['trailing_active'] = True
                        # Move SL to breakeven + small buffer when trailing activates
                        pos['sl_price'] = entry_price + 1

                    # Update trailing SL
                    if pos['trailing_active']:
                        new_sl = pos['best_price'] - trailing_distance
                        if new_sl > pos['sl_price']:
                            pos['sl_price'] = new_sl

                    # Check SL first (most important!)
                    if low <= pos['sl_price']:
                        exit_price = pos['sl_price']
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._close_position(pos, exit_price, exit_type, candle_time, hours_in_trade)
                        completed_trades.append(trade)
                        positions_to_close.append(pos_idx)

                        # If SL hit, close ALL positions in the same group!
                        self._close_group_on_sl(pos['group_id'], open_positions, candle_time,
                                               completed_trades, positions_to_close, pos_idx)
                        continue

                    # Check TP
                    if high >= pos['tp_price']:
                        exit_price = pos['tp_price'] - self.spread / 2
                        trade = self._close_position(pos, exit_price, pos['tp_level'], candle_time, hours_in_trade)
                        completed_trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                else:  # SHORT
                    if low < pos['best_price']:
                        pos['best_price'] = low

                    profit = entry_price - pos['best_price']
                    if profit >= trailing_activation and not pos['trailing_active']:
                        pos['trailing_active'] = True
                        pos['sl_price'] = entry_price - 1

                    if pos['trailing_active']:
                        new_sl = pos['best_price'] + trailing_distance
                        if new_sl < pos['sl_price']:
                            pos['sl_price'] = new_sl

                    # Check SL first
                    if high >= pos['sl_price']:
                        exit_price = pos['sl_price']
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._close_position(pos, exit_price, exit_type, candle_time, hours_in_trade)
                        completed_trades.append(trade)
                        positions_to_close.append(pos_idx)

                        # If SL hit, close ALL positions in the same group!
                        self._close_group_on_sl(pos['group_id'], open_positions, candle_time,
                                               completed_trades, positions_to_close, pos_idx)
                        continue

                    # Check TP
                    if low <= pos['tp_price']:
                        exit_price = pos['tp_price'] + self.spread / 2
                        trade = self._close_position(pos, exit_price, pos['tp_level'], candle_time, hours_in_trade)
                        completed_trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

            # Remove closed positions
            for idx in sorted(set(positions_to_close), reverse=True):
                if idx < len(open_positions):
                    open_positions[idx]['status'] = 'CLOSED'

            # Update position groups status
            for group in position_groups:
                if group['status'] == 'OPEN':
                    all_closed = all(p['status'] == 'CLOSED' for p in group['positions'])
                    if all_closed:
                        group['status'] = 'CLOSED'

        if len(completed_trades) == 0:
            print("❌ No completed trades")
            return None

        trades_df = pd.DataFrame(completed_trades)

        # Print regime statistics
        print(f"\n{'='*80}")
        print(f"📊 MARKET REGIME STATISTICS")
        print(f"{'='*80}")
        if trend_signals + range_signals > 0:
            print(f"   TREND signals: {trend_signals} ({trend_signals/(trend_signals+range_signals)*100:.1f}%)")
            print(f"   RANGE signals: {range_signals} ({range_signals/(trend_signals+range_signals)*100:.1f}%)")

        # Stats by regime
        if 'regime' in trades_df.columns:
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

    def _close_group_on_sl(self, group_id, open_positions, candle_time, completed_trades, positions_to_close, current_idx):
        """When SL hits, close ALL remaining positions in the group"""
        for idx, pos in enumerate(open_positions):
            if idx == current_idx:
                continue  # Already closed
            if pos['status'] != 'OPEN':
                continue
            if pos['group_id'] != group_id:
                continue

            # Close this position at current SL
            hours_in_trade = (candle_time - pos['entry_time']).total_seconds() / 3600
            exit_price = pos['sl_price']
            trade = self._close_position(pos, exit_price, 'SL_GROUP', candle_time, hours_in_trade)
            completed_trades.append(trade)
            positions_to_close.append(idx)
            pos['status'] = 'CLOSED'

    def _close_position(self, pos, exit_price, exit_type, exit_time, hours):
        """Close position and calculate PnL"""
        entry_price = pos['entry_price']
        direction = pos['direction']
        size = pos['size']

        # Calculate price PnL
        if direction == 'LONG':
            price_pnl = exit_price - entry_price
        else:
            price_pnl = entry_price - exit_price

        # Apply costs
        price_pnl -= (self.spread + self.commission)  # Entry + exit costs

        # Apply swap if held > 24h
        if hours > 24:
            days = hours / 24
            price_pnl += self.swap_per_day * days

        # Scale by position size
        total_pnl_points = price_pnl * size
        pnl_pct = (total_pnl_points / entry_price) * 100

        return {
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'direction': direction,
            'regime': pos['regime'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'sl_price': pos['sl_price'],
            'original_sl': pos['original_sl'],
            'tp_price': pos['tp_price'],
            'tp_level': pos['tp_level'],
            'exit_type': exit_type,
            'duration_hours': hours,
            'pnl_points': total_pnl_points,
            'pnl_pct': pnl_pct,
            'position_size': size,
            'group_id': pos['group_id'],
            'position_id': pos['position_id'],
            'trailing_active': pos['trailing_active']
        }

    def _print_results(self, trades_df):
        """Print backtest results"""
        print(f"\n{'='*80}")
        print(f"📈 BACKTEST RESULTS")
        print(f"{'='*80}")

        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl_pct'] > 0])
        losing_trades = len(trades_df[trades_df['pnl_pct'] < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        total_pnl_pct = trades_df['pnl_pct'].sum()
        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0
        profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 and avg_loss != 0 else float('inf')

        print(f"   Total Trades: {total_trades}")
        print(f"   Winning: {winning_trades} ({win_rate:.1f}%)")
        print(f"   Losing: {losing_trades} ({100-win_rate:.1f}%)")
        print(f"\n   Total PnL: {total_pnl_pct:+.2f}%")
        print(f"   Average Win: {avg_win:+.2f}%")
        print(f"   Average Loss: {avg_loss:+.2f}%")
        print(f"   Profit Factor: {profit_factor:.2f}")

        # Exit type breakdown
        print(f"\n   📊 Exit Type Breakdown:")
        exit_counts = trades_df['exit_type'].value_counts()
        for exit_type, count in exit_counts.items():
            pct = (count / total_trades * 100)
            avg_pnl = trades_df[trades_df['exit_type'] == exit_type]['pnl_pct'].mean()
            print(f"      {exit_type}: {count} ({pct:.1f}%) | Avg PnL: {avg_pnl:+.2f}%")

        # TP level breakdown
        if 'tp_level' in trades_df.columns:
            print(f"\n   🎯 TP Level Breakdown:")
            tp_counts = trades_df[trades_df['exit_type'].str.startswith('TP', na=False)].groupby('tp_level')
            for tp_level, group in tp_counts:
                count = len(group)
                pct = (count / total_trades * 100)
                avg_pnl = group['pnl_pct'].mean()
                print(f"      {tp_level}: {count} hits ({pct:.1f}%) | Avg PnL: {avg_pnl:+.2f}%")

        # Drawdown
        cumulative_pnl = trades_df['pnl_pct'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        max_dd = drawdown.min()

        print(f"\n   💧 Maximum Drawdown: {max_dd:.2f}%")

        # Average duration
        avg_duration = trades_df['duration_hours'].mean()
        print(f"   ⏱️  Average Duration: {avg_duration:.1f} hours ({avg_duration/24:.1f} days)")


def load_mt5_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load MT5 XAUUSD data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Add market hours
    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Backtest V3 Adaptive - FIXED')
    parser.add_argument('--data', type=str, default='../XAUUSD_1H_MT5_20241227_20251227.csv',
                       help='Path to CSV data file')
    parser.add_argument('--spread', type=float, default=4.0,
                       help='Spread in points (default: 4.0)')
    parser.add_argument('--commission', type=float, default=0.5,
                       help='Commission per position in points (default: 0.5)')
    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"🚀 BACKTEST V3 ADAPTIVE - FIXED VERSION")
    print(f"   (3 separate positions matching live bot)")
    print(f"{'='*80}")

    # Load data
    print(f"\n📥 Loading data from {args.data}...")
    df = load_mt5_data(args.data)
    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Initialize backtest
    backtest = AdaptiveBacktestV3Fixed(
        spread_points=args.spread,
        commission_points=args.commission
    )

    # Run backtest
    trades_df = backtest.backtest(df, strategy)

    if trades_df is not None:
        # Save results
        output_file = 'backtest_v3_adaptive_fixed_results.csv'
        trades_df.to_csv(output_file, index=False)
        print(f"\n✅ Results saved to: {output_file}")

    print(f"\n{'='*80}")
    print(f"✅ BACKTEST COMPLETED!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
