"""
Realistic Backtest V3 FIXED - MULTIPLE POSITIONS + TRAILING STOP
- Multiple independent positions (no averaging)
- Trailing stop after TP1
- Lower TP levels: 20/35/50
- Fixed simulation logic (no negative duration!)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from pattern_recognition_strategy import PatternRecognitionStrategy


class RealisticBacktestV3Fixed:
    """Realistic backtest with multiple positions - FIXED VERSION"""

    def __init__(self, spread_points=2.0, commission_points=0.5, swap_per_day=-0.3,
                 trailing_distance=15):
        """
        Args:
            spread_points: Average spread in points (default: 2 for XAUUSD)
            commission_points: Commission per trade in points (default: 0.5)
            swap_per_day: Swap cost per day in points (default: -0.3)
            trailing_distance: Trailing stop distance in points after TP1 (default: 15)
        """
        self.spread = spread_points
        self.commission = commission_points
        self.swap_per_day = swap_per_day
        self.trailing_distance = trailing_distance

        # Daily limits
        self.max_trades_per_day = 10
        self.max_loss_per_day = -5.0  # %
        self.max_positions = 999  # UNLIMITED positions (was 5)
        self.max_consecutive_losses = 5  # Increased from 3 to 5 (like V2)
        self.max_drawdown = -5.0  # Maximum allowed drawdown %

    def backtest(self, df, strategy, tp1=20, tp2=35, tp3=50,
                 close_pct1=0.5, close_pct2=0.3, close_pct3=0.2):
        """
        Run realistic backtest with multiple positions

        Args:
            df: DataFrame with OHLCV data
            strategy: Strategy instance
            tp1, tp2, tp3: Take profit levels in points
            close_pct1, close_pct2, close_pct3: Partial close percentages
        """

        print(f"\n{'='*80}")
        print(f"📊 REALISTIC BACKTEST V3 FIXED - MULTIPLE POSITIONS")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")
        print(f"   TP Levels: {tp1}п / {tp2}п / {tp3}п")
        print(f"   Close %: {close_pct1*100:.0f}% / {close_pct2*100:.0f}% / {close_pct3*100:.0f}%")
        print(f"\n   💰 COSTS:")
        print(f"   Spread: {self.spread}п")
        print(f"   Commission: {self.commission}п")
        print(f"   Swap: {self.swap_per_day}п/day")
        print(f"\n   🛡️ LIMITS:")
        if self.max_positions >= 999:
            print(f"   Max positions: UNLIMITED")
        else:
            print(f"   Max positions: {self.max_positions}")
        print(f"   Max trades/day: {self.max_trades_per_day}")
        print(f"   Max DD: {self.max_drawdown}% 🛡️")
        print(f"\n   📈 FEATURES:")
        print(f"   ✅ Multiple independent positions (no averaging)")
        print(f"   ✅ Trailing stop after TP1: {self.trailing_distance}п")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())

        # Track trades and open positions
        trades = []
        open_positions = []

        # Debug counters
        signals_total = 0
        signals_opened = 0
        skip_max_positions = 0
        skip_daily_limit = 0
        skip_consecutive = 0
        skip_max_dd = 0

        # Track cumulative PnL for DD calculation
        cumulative_pnl = 0.0
        peak_pnl = 0.0

        # Process candles chronologically
        for i in range(len(df_strategy)):
            candle = df_strategy.iloc[i]
            candle_time = df_strategy.index[i]
            high = candle['high']
            low = candle['low']
            close = candle['close']
            signal = candle.get('signal', 0)

            # Check for new signal and open position
            if signal != 0:
                signals_total += 1

                # Calculate current DD
                current_dd = cumulative_pnl - peak_pnl

                # Check daily limits
                current_date = candle_time.date()
                today_trades = [t for t in trades if pd.to_datetime(t['exit_time']).date() == current_date]

                can_open = True
                skip_reason = None

                # Check max drawdown limit
                if current_dd <= self.max_drawdown:
                    can_open = False
                    skip_reason = 'max_drawdown'
                    skip_max_dd += 1

                if len(today_trades) >= self.max_trades_per_day:
                    can_open = False
                    skip_reason = 'daily_limit'
                    skip_daily_limit += 1

                daily_pnl = sum([t['pnl_pct'] for t in today_trades])
                if daily_pnl <= self.max_loss_per_day:
                    can_open = False
                    skip_reason = 'daily_loss'
                    skip_daily_limit += 1

                # Check consecutive losses (DISABLED - too strict!)
                # if len(trades) >= self.max_consecutive_losses:
                #     last_n = trades[-self.max_consecutive_losses:]
                #     if all(t['pnl_pct'] < 0 for t in last_n):
                #         can_open = False
                #         skip_reason = 'consecutive_losses'
                #         skip_consecutive += 1

                # Check max positions
                if len(open_positions) >= self.max_positions:
                    can_open = False
                    skip_reason = 'max_positions'
                    skip_max_positions += 1

                if can_open:
                    # Open new position
                    direction = 'LONG' if signal == 1 else 'SHORT'
                    signal_sl = candle.get('stop_loss', close)

                    if direction == 'LONG':
                        entry_price = close + self.spread / 2
                        sl_distance = close - signal_sl
                        sl_price = entry_price - sl_distance
                    else:
                        entry_price = close - self.spread / 2
                        sl_distance = signal_sl - close
                        sl_price = entry_price + sl_distance

                    # Calculate TPs
                    if direction == 'LONG':
                        tp1_price = entry_price + tp1
                        tp2_price = entry_price + tp2
                        tp3_price = entry_price + tp3
                    else:
                        tp1_price = entry_price - tp1
                        tp2_price = entry_price - tp2
                        tp3_price = entry_price - tp3

                    new_pos = {
                        'entry_time': candle_time,
                        'entry_price': entry_price,
                        'direction': direction,
                        'sl_price': sl_price,
                        'original_sl': sl_price,
                        'tp1_price': tp1_price,
                        'tp2_price': tp2_price,
                        'tp3_price': tp3_price,
                        'tp1_hit': False,
                        'tp2_hit': False,
                        'tp3_hit': False,
                        'trailing_active': False,
                        'trailing_high': entry_price if direction == 'LONG' else 0,
                        'trailing_low': entry_price if direction == 'SHORT' else 999999,
                        'position_remaining': 1.0,
                        'total_pnl_pct': 0.0,
                        'pattern': candle.get('pattern', 'N/A')
                    }

                    open_positions.append(new_pos)
                    signals_opened += 1

            # Update all open positions
            positions_to_close = []

            for pos_idx, pos in enumerate(open_positions):
                entry_time = pos['entry_time']
                entry_price = pos['entry_price']
                direction = pos['direction']

                # Skip if position opened on this candle
                if entry_time == candle_time:
                    continue

                # Check timeout (48 hours)
                hours_in_trade = (candle_time - entry_time).total_seconds() / 3600

                if hours_in_trade >= 48:
                    # Force close
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
                    # Update trailing high
                    if high > pos['trailing_high']:
                        pos['trailing_high'] = high

                    # Update trailing stop if active
                    if pos['trailing_active']:
                        new_trailing_sl = pos['trailing_high'] - self.trailing_distance
                        if new_trailing_sl > pos['sl_price']:
                            pos['sl_price'] = new_trailing_sl

                    # Stop loss
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

                    # TP1
                    if high >= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] - self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct1, hours_in_trade
                        )

                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True

                        # ACTIVATE TRAILING
                        pos['trailing_active'] = True
                        pos['sl_price'] = high - self.trailing_distance

                    # TP2
                    if high >= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] - self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct2, hours_in_trade
                        )

                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    # TP3
                    if high >= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] - self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct3, hours_in_trade
                        )

                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct3
                        pos['tp3_hit'] = True

                    # Close if all TPs hit
                    if pos['position_remaining'] <= 0.01:
                        trade = self._create_trade_record(pos, pos['tp3_price'], 'TP3', candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                else:  # SHORT
                    # Update trailing low
                    if low < pos['trailing_low']:
                        pos['trailing_low'] = low

                    # Update trailing stop if active
                    if pos['trailing_active']:
                        new_trailing_sl = pos['trailing_low'] + self.trailing_distance
                        if new_trailing_sl < pos['sl_price']:
                            pos['sl_price'] = new_trailing_sl

                    # Stop loss
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

                    # TP1
                    if low <= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] + self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct1, hours_in_trade
                        )

                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True

                        # ACTIVATE TRAILING
                        pos['trailing_active'] = True
                        pos['sl_price'] = low + self.trailing_distance

                    # TP2
                    if low <= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] + self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct2, hours_in_trade
                        )

                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    # TP3
                    if low <= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] + self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct3, hours_in_trade
                        )

                        pos['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        pos['position_remaining'] -= close_pct3
                        pos['tp3_hit'] = True

                    # Close if all TPs hit
                    if pos['position_remaining'] <= 0.01:
                        trade = self._create_trade_record(pos, pos['tp3_price'], 'TP3', candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

            # Remove closed positions
            for idx in sorted(positions_to_close, reverse=True):
                del open_positions[idx]

            # Update cumulative PnL and peak after closing positions
            if len(trades) > 0:
                cumulative_pnl = sum([t['pnl_pct'] for t in trades])
                if cumulative_pnl > peak_pnl:
                    peak_pnl = cumulative_pnl

        # Print signal statistics
        print(f"\n{'='*80}")
        print(f"📊 SIGNAL STATISTICS")
        print(f"{'='*80}")
        print(f"   Total signals: {signals_total}")
        print(f"   Signals opened: {signals_opened} ({signals_opened/signals_total*100 if signals_total > 0 else 0:.1f}%)")
        print(f"   Signals skipped: {signals_total - signals_opened}")
        print(f"\n   Skip reasons:")
        print(f"   - Max positions: {skip_max_positions} ({skip_max_positions/signals_total*100 if signals_total > 0 else 0:.1f}%)")
        print(f"   - Daily limits: {skip_daily_limit} ({skip_daily_limit/signals_total*100 if signals_total > 0 else 0:.1f}%)")
        print(f"   - Consecutive losses: {skip_consecutive} ({skip_consecutive/signals_total*100 if signals_total > 0 else 0:.1f}%)")
        print(f"   - Max DD (-5%): {skip_max_dd} ({skip_max_dd/signals_total*100 if signals_total > 0 else 0:.1f}%)")

        # Convert to DataFrame
        if len(trades) == 0:
            print("❌ No completed trades")
            return None

        trades_df = pd.DataFrame(trades)

        # Calculate statistics
        self._print_results(trades_df)

        return trades_df

    def _calculate_pnl_points(self, entry, exit, direction, position_size, hours):
        """Calculate PnL in points with all costs"""

        # Price movement
        if direction == 'LONG':
            price_pnl = exit - entry
        else:
            price_pnl = entry - exit

        # Apply position size
        price_pnl *= position_size

        # Subtract costs
        price_pnl -= self.commission * position_size

        # Subtract swap if held >24h
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
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'stop_loss': pos['original_sl'],
            'tp1_hit': pos['tp1_hit'],
            'tp2_hit': pos['tp2_hit'],
            'tp3_hit': pos['tp3_hit'],
            'trailing_used': pos['trailing_active'],
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
            'pattern': pos['pattern']
        }

    def _print_results(self, trades_df):
        """Print backtest results"""

        print(f"\n{'='*80}")
        print(f"📊 RESULTS V3 FIXED - MULTIPLE POSITIONS")
        print(f"{'='*80}")

        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = trades_df['pnl_pct'].sum()
        total_points = trades_df['pnl_points'].sum()

        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0

        # TP hit rates
        tp1_hits = trades_df['tp1_hit'].sum()
        tp2_hits = trades_df['tp2_hit'].sum()
        tp3_hits = trades_df['tp3_hit'].sum()
        trailing_used = trades_df['trailing_used'].sum()

        print(f"\n📈 Performance:")
        print(f"   Total trades: {total_trades}")
        print(f"   Wins: {wins} ({win_rate:.1f}%)")
        print(f"   Losses: {losses}")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Total Points: {total_points:+.1f}п")
        print(f"   Avg Win: {avg_win:+.2f}%")
        print(f"   Avg Loss: {avg_loss:+.2f}%")

        if avg_loss != 0:
            profit_factor = abs(avg_win * wins / (avg_loss * losses))
            print(f"   Profit Factor: {profit_factor:.2f}")

        print(f"\n🎯 TP Hit Rates:")
        print(f"   TP1: {tp1_hits}/{total_trades} ({tp1_hits/total_trades*100:.1f}%)")
        print(f"   TP2: {tp2_hits}/{total_trades} ({tp2_hits/total_trades*100:.1f}%)")
        print(f"   TP3: {tp3_hits}/{total_trades} ({tp3_hits/total_trades*100:.1f}%)")
        print(f"   Trailing stop used: {trailing_used}/{total_trades} ({trailing_used/total_trades*100:.1f}%)")

        # Exit types
        print(f"\n🚪 Exit Types:")
        for exit_type in trades_df['exit_type'].unique():
            count = len(trades_df[trades_df['exit_type'] == exit_type])
            print(f"   {exit_type}: {count} ({count/total_trades*100:.1f}%)")

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
            'pnl_pct': ['sum', 'mean', 'count'],
            'pnl_points': 'sum'
        })
        monthly.columns = ['Total_PnL_%', 'Avg_PnL_%', 'Trades', 'Total_Points']

        # Calculate win rate by month
        monthly_wins = trades_df[trades_df['pnl_pct'] > 0].groupby('month').size()
        monthly['Wins'] = monthly_wins
        monthly['Wins'] = monthly['Wins'].fillna(0).astype(int)
        monthly['Win_Rate_%'] = (monthly['Wins'] / monthly['Trades'] * 100).round(1)

        print(f"\n📅 Monthly Results:")
        print(f"\n{'Month':<10} {'Trades':<8} {'Wins':<6} {'WR%':<6} {'Total PnL%':<12} {'Avg PnL%':<10} {'Points':<10}")
        print(f"{'='*80}")

        cumulative_pnl = 0
        for month, row in monthly.iterrows():
            cumulative_pnl += row['Total_PnL_%']
            trades_count = int(row['Trades'])
            wins = int(row['Wins'])
            wr = row['Win_Rate_%']
            total_pnl = row['Total_PnL_%']
            avg_pnl = row['Avg_PnL_%']
            points = row['Total_Points']

            print(f"{str(month):<10} {trades_count:<8} {wins:<6} {wr:<6.1f} {total_pnl:+11.2f}% {avg_pnl:+9.2f}% {points:+9.1f}п")

        print(f"{'='*80}")
        print(f"{'TOTAL':<10} {int(monthly['Trades'].sum()):<8} {int(monthly['Wins'].sum()):<6} {win_rate:<6.1f} {total_pnl:+11.2f}% {total_pnl/len(monthly):+9.2f}% {total_points:+9.1f}п")


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description='Realistic Backtest V3 Fixed')

    parser.add_argument('--file', type=str, required=True,
                        help='CSV file with H1 data')

    parser.add_argument('--spread', type=float, default=2.0,
                        help='Spread in points (default: 2)')

    parser.add_argument('--commission', type=float, default=0.5,
                        help='Commission in points (default: 0.5)')

    parser.add_argument('--swap', type=float, default=-0.3,
                        help='Swap per day in points (default: -0.3)')

    parser.add_argument('--trailing', type=float, default=15,
                        help='Trailing stop distance in points (default: 15)')

    args = parser.parse_args()

    # Load data
    print(f"\n📂 Loading data from {args.file}...")
    df = pd.read_csv(args.file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')

    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")

    # Add market hours if not present
    if 'is_active' not in df.columns:
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_overlap'] = df.index.hour.isin(range(13, 16))
        df['is_active'] = df['is_london'] | df['is_ny']
        df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    # Create strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Run backtest
    backtest = RealisticBacktestV3Fixed(
        spread_points=args.spread,
        commission_points=args.commission,
        swap_per_day=args.swap,
        trailing_distance=args.trailing
    )

    trades_df = backtest.backtest(
        df=df,
        strategy=strategy,
        tp1=20, tp2=35, tp3=50,
        close_pct1=0.5, close_pct2=0.3, close_pct3=0.2
    )

    if trades_df is not None:
        # Save results
        output_file = f"backtest_v3_fixed_results.csv"
        trades_df.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to {output_file}")

        print(f"\n{'='*80}")
        print(f"✅ BACKTEST V3 FIXED COMPLETE")
        print(f"{'='*80}")


if __name__ == "__main__":
    # Example:
    # python backtest_v3_fixed.py --file ../XAUUSD_1H_MT5_20241227_20251227.csv --trailing 15
    main()
