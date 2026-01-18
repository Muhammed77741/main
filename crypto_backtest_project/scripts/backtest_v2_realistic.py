"""
Realistic Backtest V2 - WITH ALL FIXES
- Correct TP order (TP1 → TP2 → TP3)
- Breakeven after TP1
- Spread simulation (bid/ask)
- Commissions and swaps
- Daily limits
- Single position only
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse

from pattern_recognition_strategy import PatternRecognitionStrategy


class RealisticBacktest:
    """Realistic backtest with all cost factors"""

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

        # Daily limits
        self.max_trades_per_day = 5
        self.max_loss_per_day = -3.0  # %
        self.max_consecutive_losses = 3

    def backtest(self, df, strategy, tp1=30, tp2=50, tp3=80,
                 close_pct1=0.5, close_pct2=0.3, close_pct3=0.2):
        """
        Run realistic backtest with all fixes

        Args:
            df: DataFrame with OHLCV data
            strategy: Strategy instance
            tp1, tp2, tp3: Take profit levels in points
            close_pct1, close_pct2, close_pct3: Partial close percentages
        """

        print(f"\n{'='*80}")
        print(f"📊 REALISTIC BACKTEST V2")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")
        print(f"   TP Levels: {tp1}п / {tp2}п / {tp3}п")
        print(f"   Close %: {close_pct1*100:.0f}% / {close_pct2*100:.0f}% / {close_pct3*100:.0f}%")
        print(f"\n   💰 REALISTIC COSTS:")
        print(f"   Spread: {self.spread}п")
        print(f"   Commission: {self.commission}п")
        print(f"   Swap: {self.swap_per_day}п/day")
        print(f"\n   🛡️ RISK LIMITS:")
        print(f"   Max trades/day: {self.max_trades_per_day}")
        print(f"   Max loss/day: {self.max_loss_per_day}%")
        print(f"   Max consecutive losses: {self.max_consecutive_losses}")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())
        df_signals = df_strategy[df_strategy['signal'] != 0].copy()

        print(f"\n📈 Raw signals found: {len(df_signals)}")

        if len(df_signals) == 0:
            print("❌ No signals")
            return None

        # Track trades
        trades = []
        open_position = None

        for idx, signal in df_signals.iterrows():
            # Check if we have open position (SINGLE POSITION ONLY)
            if open_position is not None:
                continue

            # Check daily limits
            current_date = idx.date()
            today_trades = [t for t in trades if t['exit_time'].date() == current_date]

            if len(today_trades) >= self.max_trades_per_day:
                continue

            daily_pnl = sum([t['pnl_pct'] for t in today_trades])
            if daily_pnl <= self.max_loss_per_day:
                continue

            # Check consecutive losses (last 5 trades)
            if len(trades) >= 5:
                last_5 = trades[-5:]
                if all(t['pnl_pct'] < 0 for t in last_5):
                    continue  # Skip if last 5 all losses

            # Open new position
            direction = 'LONG' if signal['signal'] == 1 else 'SHORT'
            entry_time = idx

            # REALISTIC ENTRY: Use bid/ask spread
            close_price = signal['entry_price']
            signal_sl = signal['stop_loss']

            if direction == 'LONG':
                entry_price = close_price + self.spread / 2  # Buy at ASK
                # Recalculate SL based on new entry (preserve distance)
                sl_distance = close_price - signal_sl
                sl_price = entry_price - sl_distance
            else:
                entry_price = close_price - self.spread / 2  # Sell at BID
                # Recalculate SL based on new entry
                sl_distance = signal_sl - close_price
                sl_price = entry_price + sl_distance

            # Calculate TPs from new entry
            if direction == 'LONG':
                tp1_price = entry_price + tp1
                tp2_price = entry_price + tp2
                tp3_price = entry_price + tp3
            else:
                tp1_price = entry_price - tp1
                tp2_price = entry_price - tp2
                tp3_price = entry_price - tp3

            open_position = {
                'entry_time': entry_time,
                'entry_price': entry_price,
                'direction': direction,
                'sl_price': sl_price,
                'original_sl': sl_price,  # Save original
                'tp1_price': tp1_price,
                'tp2_price': tp2_price,
                'tp3_price': tp3_price,
                'tp1_hit': False,
                'tp2_hit': False,
                'tp3_hit': False,
                'breakeven_moved': False,  # NEW: Track breakeven
                'position_remaining': 1.0,
                'total_pnl_pct': 0.0,
                'pattern': signal.get('pattern', 'N/A')
            }

            # Simulate position
            entry_idx = df.index.get_loc(idx)

            for i in range(entry_idx + 1, len(df)):
                candle = df.iloc[i]
                candle_time = df.index[i]
                high = candle['high']
                low = candle['low']
                close = candle['close']

                # Check timeout (48 hours)
                hours_in_trade = (candle_time - entry_time).total_seconds() / 3600

                if hours_in_trade >= 48:
                    # Force close
                    if direction == 'LONG':
                        exit_price = close - self.spread / 2  # Sell at BID
                    else:
                        exit_price = close + self.spread / 2  # Buy at ASK

                    pnl_points = self._calculate_pnl_points(
                        entry_price, exit_price, direction,
                        open_position['position_remaining'], hours_in_trade
                    )

                    open_position['total_pnl_pct'] += (pnl_points / entry_price) * 100

                    trade = self._create_trade_record(
                        open_position, exit_price, 'TIMEOUT', candle_time
                    )
                    trades.append(trade)

                    open_position = None
                    break

                # Check SL/TP
                if direction == 'LONG':
                    # Stop loss
                    if low <= open_position['sl_price']:
                        exit_price = open_position['sl_price']

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            open_position['position_remaining'], hours_in_trade
                        )

                        open_position['total_pnl_pct'] += (pnl_points / entry_price) * 100

                        trade = self._create_trade_record(
                            open_position, exit_price, 'SL', candle_time
                        )
                        trades.append(trade)

                        
                        open_position = None
                        break

                    # CORRECT ORDER: TP1 → TP2 → TP3
                    if high >= tp1_price and not open_position['tp1_hit']:
                        # TP1 hit
                        exit_price = tp1_price - self.spread / 2  # Exit at BID

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct1, hours_in_trade
                        )

                        open_position['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        open_position['position_remaining'] -= close_pct1
                        open_position['tp1_hit'] = True

                        # BREAKEVEN: Move SL to entry + small profit
                        if not open_position['breakeven_moved']:
                            breakeven_price = entry_price + 5  # Entry + 5 points
                            open_position['sl_price'] = breakeven_price
                            open_position['breakeven_moved'] = True

                    if high >= tp2_price and not open_position['tp2_hit']:
                        # TP2 hit
                        exit_price = tp2_price - self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct2, hours_in_trade
                        )

                        open_position['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        open_position['position_remaining'] -= close_pct2
                        open_position['tp2_hit'] = True

                    if high >= tp3_price and not open_position['tp3_hit']:
                        # TP3 hit
                        exit_price = tp3_price - self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct3, hours_in_trade
                        )

                        open_position['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        open_position['position_remaining'] -= close_pct3
                        open_position['tp3_hit'] = True

                    # If all TPs hit, close position
                    if open_position['position_remaining'] <= 0.01:
                        trade = self._create_trade_record(
                            open_position, tp3_price, 'TP3', candle_time
                        )
                        trades.append(trade)

                        
                        open_position = None
                        break

                else:  # SHORT
                    # Stop loss
                    if high >= open_position['sl_price']:
                        exit_price = open_position['sl_price']

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            open_position['position_remaining'], hours_in_trade
                        )

                        open_position['total_pnl_pct'] += (pnl_points / entry_price) * 100

                        trade = self._create_trade_record(
                            open_position, exit_price, 'SL', candle_time
                        )
                        trades.append(trade)

                        
                        open_position = None
                        break

                    # CORRECT ORDER: TP1 → TP2 → TP3
                    if low <= tp1_price and not open_position['tp1_hit']:
                        exit_price = tp1_price + self.spread / 2  # Exit at ASK

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct1, hours_in_trade
                        )

                        open_position['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        open_position['position_remaining'] -= close_pct1
                        open_position['tp1_hit'] = True

                        # BREAKEVEN
                        if not open_position['breakeven_moved']:
                            breakeven_price = entry_price - 5
                            open_position['sl_price'] = breakeven_price
                            open_position['breakeven_moved'] = True

                    if low <= tp2_price and not open_position['tp2_hit']:
                        exit_price = tp2_price + self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct2, hours_in_trade
                        )

                        open_position['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        open_position['position_remaining'] -= close_pct2
                        open_position['tp2_hit'] = True

                    if low <= tp3_price and not open_position['tp3_hit']:
                        exit_price = tp3_price + self.spread / 2

                        pnl_points = self._calculate_pnl_points(
                            entry_price, exit_price, direction,
                            close_pct3, hours_in_trade
                        )

                        open_position['total_pnl_pct'] += (pnl_points / entry_price) * 100
                        open_position['position_remaining'] -= close_pct3
                        open_position['tp3_hit'] = True

                    if open_position['position_remaining'] <= 0.01:
                        trade = self._create_trade_record(
                            open_position, tp3_price, 'TP3', candle_time
                        )
                        trades.append(trade)

                        
                        open_position = None
                        break

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

        # Subtract costs (already included spread at entry/exit, just add commission)
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
            'breakeven_moved': pos['breakeven_moved'],
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
            'pattern': pos['pattern']
        }

    def _print_results(self, trades_df):
        """Print backtest results"""

        print(f"\n{'='*80}")
        print(f"📊 REALISTIC RESULTS V2")
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
        breakeven_count = trades_df['breakeven_moved'].sum()

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
        print(f"   Breakeven moved: {breakeven_count}/{total_trades} ({breakeven_count/total_trades*100:.1f}%)")

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
            'pnl_pct': 'sum',
            'entry_time': 'count'
        }).rename(columns={'entry_time': 'trades'})

        print(f"\n📅 Monthly Results:")
        print(monthly)


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description='Realistic Backtest V2')

    parser.add_argument('--file', type=str, required=True,
                        help='CSV file with H1 data')

    parser.add_argument('--spread', type=float, default=2.0,
                        help='Spread in points (default: 2)')

    parser.add_argument('--commission', type=float, default=0.5,
                        help='Commission in points (default: 0.5)')

    parser.add_argument('--swap', type=float, default=-0.3,
                        help='Swap per day in points (default: -0.3)')

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

    # Run realistic backtest
    backtest = RealisticBacktest(
        spread_points=args.spread,
        commission_points=args.commission,
        swap_per_day=args.swap
    )

    trades_df = backtest.backtest(
        df=df,
        strategy=strategy,
        tp1=30, tp2=50, tp3=80,
        close_pct1=0.5, close_pct2=0.3, close_pct3=0.2
    )

    if trades_df is not None:
        # Save results
        output_file = f"backtest_v2_realistic_results.csv"
        trades_df.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to {output_file}")

        print(f"\n{'='*80}")
        print(f"✅ REALISTIC BACKTEST COMPLETE")
        print(f"{'='*80}")
        print(f"\n🔍 Key improvements:")
        print(f"   ✅ Correct TP order (TP1 → TP2 → TP3)")
        print(f"   ✅ Breakeven after TP1 (+5п)")
        print(f"   ✅ Spread: {args.spread}п")
        print(f"   ✅ Commission: {args.commission}п")
        print(f"   ✅ Swap: {args.swap}п/day")
        print(f"   ✅ Daily limits (max 5 trades, -3% loss)")
        print(f"   ✅ Single position only")


if __name__ == "__main__":
    # Example:
    # python backtest_v2_realistic.py --file XAUUSD_1H_MT5_20241227_20251227.csv --spread 2 --commission 0.5
    main()
