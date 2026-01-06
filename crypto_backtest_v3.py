"""
Crypto Backtest V3 - Advanced Backtest for Bitcoin and Ethereum
Based on v3 advanced backtest with crypto-specific adaptations

ADAPTATIONS FOR CRYPTO:
1. 24/7 market (no session filtering)
2. Higher volatility (adjusted TP/SL parameters)
3. Different spread/commission structure
4. Monthly analysis included
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'smc_trading_strategy'))

from smc_trading_strategy.pattern_recognition_strategy import PatternRecognitionStrategy


class CryptoBacktestV3:
    """Advanced backtest for crypto assets (BTC, ETH)"""

    def __init__(self, spread_pct=0.05, commission_pct=0.1):
        """
        Args:
            spread_pct: Average spread in % (default: 0.05% for major exchanges)
            commission_pct: Commission per trade in % (default: 0.1% for maker/taker)
        """
        self.spread_pct = spread_pct
        self.commission_pct = commission_pct

        # TREND MODE parameters (adjusted for crypto volatility)
        # Crypto is more volatile than gold, so we use larger TPs
        self.trend_tp1_pct = 2.0   # 2% for TP1
        self.trend_tp2_pct = 4.0   # 4% for TP2
        self.trend_tp3_pct = 7.0   # 7% for TP3
        self.trend_trailing_pct = 1.5  # 1.5% trailing
        self.trend_timeout = 72  # 3 days

        # RANGE MODE parameters (tighter for consolidation)
        self.range_tp1_pct = 1.5   # 1.5%
        self.range_tp2_pct = 2.5   # 2.5%
        self.range_tp3_pct = 4.0   # 4%
        self.range_trailing_pct = 1.0  # 1% trailing
        self.range_timeout = 48  # 2 days

        # Position limits
        self.max_positions = 5
        self.max_trades_per_day = 10

    def detect_market_regime(self, df, current_idx, lookback=100):
        """
        Detect market regime: TREND or RANGE
        Same logic as v3 backtest but adapted for crypto
        """
        if current_idx < lookback:
            return 'RANGE'

        recent_data = df.iloc[current_idx - lookback:current_idx]

        # 1. EMA CROSSOVER
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()

        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]

        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
        ema_trend = ema_diff_pct > 0.5  # Higher threshold for crypto

        # 2. ATR (volatility)
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()

        high_volatility = atr > avg_atr * 1.1

        # 3. Directional movement
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()

        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.4

        # 4. Sequential movements
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        total_moves = up_moves + down_moves

        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.2  # Adjusted for crypto

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

        return 'TREND' if is_trend else 'RANGE'

    def backtest(self, df, strategy, close_pct1=0.5, close_pct2=0.3, close_pct3=0.2):
        """
        Run crypto backtest
        """

        print(f"\n{'='*80}")
        print(f"🪙 CRYPTO BACKTEST V3 - ADVANCED")
        print(f"{'='*80}")
        print(f"   Data: {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")

        print(f"\n   📈 TREND MODE:")
        print(f"   TP: {self.trend_tp1_pct}% / {self.trend_tp2_pct}% / {self.trend_tp3_pct}%")
        print(f"   Trailing: {self.trend_trailing_pct}%")
        print(f"   Timeout: {self.trend_timeout}h")

        print(f"\n   📊 RANGE MODE:")
        print(f"   TP: {self.range_tp1_pct}% / {self.range_tp2_pct}% / {self.range_tp3_pct}%")
        print(f"   Trailing: {self.range_trailing_pct}%")
        print(f"   Timeout: {self.range_timeout}h")

        print(f"\n   💰 COSTS:")
        print(f"   Spread: {self.spread_pct}%")
        print(f"   Commission: {self.commission_pct}%")

        # Run strategy
        df_strategy = strategy.run_strategy(df.copy())

        # Track trades and positions
        trades = []
        open_positions = []

        # Track stats
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
                    tp1_pct = self.trend_tp1_pct
                    tp2_pct = self.trend_tp2_pct
                    tp3_pct = self.trend_tp3_pct
                    trailing_pct = self.trend_trailing_pct
                    timeout = self.trend_timeout
                    trend_signals += 1
                else:  # RANGE
                    tp1_pct = self.range_tp1_pct
                    tp2_pct = self.range_tp2_pct
                    tp3_pct = self.range_tp3_pct
                    trailing_pct = self.range_trailing_pct
                    timeout = self.range_timeout
                    range_signals += 1

                # Check max positions limit
                if len(open_positions) >= self.max_positions:
                    continue

                # Open position
                direction = 'LONG' if signal == 1 else 'SHORT'
                signal_sl = candle.get('stop_loss', close)

                if direction == 'LONG':
                    entry_price = close * (1 + self.spread_pct / 100)
                    sl_distance_pct = ((close - signal_sl) / close) * 100
                    sl_price = entry_price * (1 - sl_distance_pct / 100)
                    tp1_price = entry_price * (1 + tp1_pct / 100)
                    tp2_price = entry_price * (1 + tp2_pct / 100)
                    tp3_price = entry_price * (1 + tp3_pct / 100)
                    trailing_distance_pct = trailing_pct
                else:
                    entry_price = close * (1 - self.spread_pct / 100)
                    sl_distance_pct = ((signal_sl - close) / close) * 100
                    sl_price = entry_price * (1 + sl_distance_pct / 100)
                    tp1_price = entry_price * (1 - tp1_pct / 100)
                    tp2_price = entry_price * (1 - tp2_pct / 100)
                    tp3_price = entry_price * (1 - tp3_pct / 100)
                    trailing_distance_pct = trailing_pct

                new_pos = {
                    'entry_time': candle_time,
                    'entry_price': entry_price,
                    'direction': direction,
                    'regime': regime,
                    'sl_price': sl_price,
                    'tp1_price': tp1_price,
                    'tp2_price': tp2_price,
                    'tp3_price': tp3_price,
                    'tp1_hit': False,
                    'tp2_hit': False,
                    'tp3_hit': False,
                    'trailing_active': False,
                    'trailing_distance_pct': trailing_distance_pct,
                    'timeout_hours': timeout,
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
                trailing_distance_pct = pos['trailing_distance_pct']
                timeout_hours = pos['timeout_hours']

                if entry_time == candle_time:
                    continue

                # Check timeout
                hours_in_trade = (candle_time - entry_time).total_seconds() / 3600

                if hours_in_trade >= timeout_hours:
                    if direction == 'LONG':
                        exit_price = close * (1 - self.spread_pct / 100)
                    else:
                        exit_price = close * (1 + self.spread_pct / 100)

                    pnl_pct = self._calculate_pnl_pct(
                        entry_price, exit_price, direction,
                        pos['position_remaining']
                    )

                    pos['total_pnl_pct'] += pnl_pct

                    trade = self._create_trade_record(pos, exit_price, 'TIMEOUT', candle_time)
                    trades.append(trade)
                    positions_to_close.append(pos_idx)
                    continue

                # Check SL/TP for LONG
                if direction == 'LONG':
                    if high > pos['trailing_high']:
                        pos['trailing_high'] = high

                    if pos['trailing_active']:
                        new_sl = pos['trailing_high'] * (1 - trailing_distance_pct / 100)
                        if new_sl > pos['sl_price']:
                            pos['sl_price'] = new_sl

                    if low <= pos['sl_price']:
                        exit_price = pos['sl_price']
                        pnl_pct = self._calculate_pnl_pct(
                            entry_price, exit_price, direction,
                            pos['position_remaining']
                        )
                        pos['total_pnl_pct'] += pnl_pct
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._create_trade_record(pos, exit_price, exit_type, candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                    # TP checks
                    if high >= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] * (1 - self.spread_pct / 100)
                        pnl_pct = self._calculate_pnl_pct(
                            entry_price, exit_price, direction, close_pct1
                        )
                        pos['total_pnl_pct'] += pnl_pct
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = high * (1 - trailing_distance_pct / 100)

                    if high >= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] * (1 - self.spread_pct / 100)
                        pnl_pct = self._calculate_pnl_pct(
                            entry_price, exit_price, direction, close_pct2
                        )
                        pos['total_pnl_pct'] += pnl_pct
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    if high >= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] * (1 - self.spread_pct / 100)
                        pnl_pct = self._calculate_pnl_pct(
                            entry_price, exit_price, direction, close_pct3
                        )
                        pos['total_pnl_pct'] += pnl_pct
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
                        new_sl = pos['trailing_low'] * (1 + trailing_distance_pct / 100)
                        if new_sl < pos['sl_price']:
                            pos['sl_price'] = new_sl

                    if high >= pos['sl_price']:
                        exit_price = pos['sl_price']
                        pnl_pct = self._calculate_pnl_pct(
                            entry_price, exit_price, direction,
                            pos['position_remaining']
                        )
                        pos['total_pnl_pct'] += pnl_pct
                        exit_type = 'TRAILING_SL' if pos['trailing_active'] else 'SL'
                        trade = self._create_trade_record(pos, exit_price, exit_type, candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)
                        continue

                    if low <= pos['tp1_price'] and not pos['tp1_hit']:
                        exit_price = pos['tp1_price'] * (1 + self.spread_pct / 100)
                        pnl_pct = self._calculate_pnl_pct(
                            entry_price, exit_price, direction, close_pct1
                        )
                        pos['total_pnl_pct'] += pnl_pct
                        pos['position_remaining'] -= close_pct1
                        pos['tp1_hit'] = True
                        pos['trailing_active'] = True
                        pos['sl_price'] = low * (1 + trailing_distance_pct / 100)

                    if low <= pos['tp2_price'] and not pos['tp2_hit']:
                        exit_price = pos['tp2_price'] * (1 + self.spread_pct / 100)
                        pnl_pct = self._calculate_pnl_pct(
                            entry_price, exit_price, direction, close_pct2
                        )
                        pos['total_pnl_pct'] += pnl_pct
                        pos['position_remaining'] -= close_pct2
                        pos['tp2_hit'] = True

                    if low <= pos['tp3_price'] and not pos['tp3_hit']:
                        exit_price = pos['tp3_price'] * (1 + self.spread_pct / 100)
                        pnl_pct = self._calculate_pnl_pct(
                            entry_price, exit_price, direction, close_pct3
                        )
                        pos['total_pnl_pct'] += pnl_pct
                        pos['position_remaining'] -= close_pct3
                        pos['tp3_hit'] = True

                    if pos['position_remaining'] <= 0.01:
                        trade = self._create_trade_record(pos, pos['tp3_price'], 'TP3', candle_time)
                        trades.append(trade)
                        positions_to_close.append(pos_idx)

            # Remove closed positions
            for idx in sorted(positions_to_close, reverse=True):
                del open_positions[idx]

        if len(trades) == 0:
            print("❌ No completed trades")
            return None

        trades_df = pd.DataFrame(trades)

        # Print regime statistics
        print(f"\n{'='*80}")
        print(f"📊 MARKET REGIME STATISTICS")
        print(f"{'='*80}")
        total_signals = trend_signals + range_signals
        if total_signals > 0:
            print(f"   TREND signals: {trend_signals} ({trend_signals/total_signals*100:.1f}%)")
            print(f"   RANGE signals: {range_signals} ({range_signals/total_signals*100:.1f}%)")

        # Calculate statistics
        self._print_results(trades_df)

        return trades_df

    def _calculate_pnl_pct(self, entry, exit, direction, position_size):
        """Calculate PnL in percentage"""
        if direction == 'LONG':
            price_pnl_pct = ((exit - entry) / entry) * 100
        else:
            price_pnl_pct = ((entry - exit) / entry) * 100

        price_pnl_pct *= position_size
        price_pnl_pct -= self.commission_pct * position_size

        return price_pnl_pct

    def _create_trade_record(self, pos, exit_price, exit_type, exit_time):
        """Create trade record"""
        duration_hours = (exit_time - pos['entry_time']).total_seconds() / 3600
        pnl_pct = pos['total_pnl_pct']

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
            'duration_hours': duration_hours,
        }

    def _print_results(self, trades_df):
        """Print results with monthly breakdown"""
        print(f"\n{'='*80}")
        print(f"📊 OVERALL RESULTS")
        print(f"{'='*80}")

        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = trades_df['pnl_pct'].sum()

        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if total_trades - wins > 0 else 0

        print(f"\n📈 Performance:")
        print(f"   Total trades: {total_trades}")
        print(f"   Wins: {wins} ({win_rate:.1f}%)")
        print(f"   Total PnL: {total_pnl:+.2f}%")
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

        # Monthly analysis
        trades_df['month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
        monthly = trades_df.groupby('month').agg({
            'pnl_pct': ['sum', 'count', 'mean'],
        })
        monthly.columns = ['Total_PnL_%', 'Trades', 'Avg_PnL_%']

        print(f"\n{'='*80}")
        print(f"📅 MONTHLY RESULTS")
        print(f"{'='*80}")
        for month, row in monthly.iterrows():
            print(f"   {month}: {int(row['Trades'])} trades, Total: {row['Total_PnL_%']:+.2f}%, Avg: {row['Avg_PnL_%']:+.2f}%")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Crypto Backtest V3')
    parser.add_argument('--file', type=str, required=True, help='CSV file with crypto data')
    args = parser.parse_args()

    # Load data
    print(f"\n📂 Loading data from {args.file}...")
    df = pd.read_csv(args.file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')

    # Crypto markets are 24/7, no session filtering needed
    if 'is_active' not in df.columns:
        df['is_active'] = True  # Always active for crypto

    # Create strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Run backtest
    backtest = CryptoBacktestV3()
    trades_df = backtest.backtest(df, strategy)

    if trades_df is not None:
        # Extract crypto name from filename
        crypto_name = os.path.basename(args.file).split('_')[0]
        output_file = f'{crypto_name}_backtest_v3_results.csv'
        trades_df.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
