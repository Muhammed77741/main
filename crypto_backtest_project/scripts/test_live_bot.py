"""
Тестовый запуск live бота на исторических данных
Симулирует работу в реальном времени
"""

import pandas as pd
from datetime import datetime, timedelta
import time

from pattern_recognition_strategy import PatternRecognitionStrategy


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


class SimplePaperTradingBot:
    """Упрощенный paper trading бот для демонстрации"""

    def __init__(self, tp1=30, tp2=50, tp3=80,
                 close_pct1=0.5, close_pct2=0.3, close_pct3=0.2):
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')

        # Baseline 3TP configuration
        self.tp1 = tp1
        self.tp2 = tp2
        self.tp3 = tp3
        self.close_pct1 = close_pct1
        self.close_pct2 = close_pct2
        self.close_pct3 = close_pct3

        # Open positions
        self.open_positions = []
        self.closed_trades = []

        print("✅ Simple Paper Trading Bot initialized")
        print(f"   TP: {tp1}п/{tp2}п/{tp3}п")
        print(f"   Close: {close_pct1*100:.0f}%/{close_pct2*100:.0f}%/{close_pct3*100:.0f}%")

    def check_for_signals(self, df, current_idx):
        """Check for new signals at current candle"""

        # Run strategy on data up to current point
        df_so_far = df.iloc[:current_idx+1].copy()
        df_strategy = self.strategy.run_strategy(df_so_far)

        # Get signals
        df_signals = df_strategy[df_strategy['signal'] != 0]

        if len(df_signals) == 0:
            return None

        # Get last signal
        last_signal = df_signals.iloc[-1]
        last_signal_time = df_signals.index[-1]

        # Check if it's the current candle (new signal)
        current_time = df.index[current_idx]

        # Signal is new if it's within last 2 candles
        time_diff = (current_time - last_signal_time).total_seconds() / 3600

        if time_diff <= 2:  # Within 2 hours
            return last_signal, last_signal_time

        return None

    def open_position(self, signal, entry_time):
        """Open new position"""

        entry_price = signal['entry_price']
        direction = 'LONG' if signal['signal'] == 1 else 'SHORT'

        # Calculate TPs
        if direction == 'LONG':
            tp1_price = entry_price + self.tp1
            tp2_price = entry_price + self.tp2
            tp3_price = entry_price + self.tp3
        else:
            tp1_price = entry_price - self.tp1
            tp2_price = entry_price - self.tp2
            tp3_price = entry_price - self.tp3

        position = {
            'entry_time': entry_time,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': signal['stop_loss'],
            'tp1_price': tp1_price,
            'tp2_price': tp2_price,
            'tp3_price': tp3_price,
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'position_remaining': 1.0,
            'total_pnl_pct': 0.0,
        }

        self.open_positions.append(position)

        print(f"\n🟢 NEW POSITION OPENED")
        print(f"   Time: {entry_time}")
        print(f"   Direction: {direction}")
        print(f"   Entry: {entry_price:.2f}")
        print(f"   TP1: {tp1_price:.2f} ({self.close_pct1*100:.0f}%)")
        print(f"   TP2: {tp2_price:.2f} ({self.close_pct2*100:.0f}%)")
        print(f"   TP3: {tp3_price:.2f} ({self.close_pct3*100:.0f}%)")
        print(f"   SL:  {signal['stop_loss']:.2f}")

    def check_positions(self, current_candle, current_time):
        """Check if positions hit SL/TP"""

        high = current_candle['high']
        low = current_candle['low']
        close_price = current_candle['close']

        positions_to_close = []

        for i, pos in enumerate(self.open_positions):
            if pos['position_remaining'] <= 0:
                positions_to_close.append(i)
                continue

            # Check timeout (48 hours)
            time_diff = (current_time - pos['entry_time']).total_seconds() / 3600

            if time_diff >= 48:
                # Close by timeout
                if pos['direction'] == 'LONG':
                    pnl_pct = ((close_price - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                else:
                    pnl_pct = ((pos['entry_price'] - close_price) / pos['entry_price']) * 100 * pos['position_remaining']

                pos['total_pnl_pct'] += pnl_pct
                self.close_position(pos, close_price, 'EOD', current_time)
                positions_to_close.append(i)
                continue

            # Check SL/TP
            if pos['direction'] == 'LONG':
                # SL
                if low <= pos['stop_loss']:
                    pnl_pct = ((pos['stop_loss'] - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    self.close_position(pos, pos['stop_loss'], 'SL', current_time)
                    positions_to_close.append(i)
                    continue

                # TPs
                if high >= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['tp3_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} (closed {self.close_pct3*100:.0f}%)")

                if high >= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['tp2_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} (closed {self.close_pct2*100:.0f}%)")

                if high >= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['tp1_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} (closed {self.close_pct1*100:.0f}%)")

            else:  # SHORT
                # SL
                if high >= pos['stop_loss']:
                    pnl_pct = ((pos['entry_price'] - pos['stop_loss']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    self.close_position(pos, pos['stop_loss'], 'SL', current_time)
                    positions_to_close.append(i)
                    continue

                # TPs
                if low <= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp3_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} (closed {self.close_pct3*100:.0f}%)")

                if low <= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp2_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} (closed {self.close_pct2*100:.0f}%)")

                if low <= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp1_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} (closed {self.close_pct1*100:.0f}%)")

        # Remove closed positions
        for idx in reversed(positions_to_close):
            self.open_positions.pop(idx)

    def close_position(self, pos, exit_price, exit_type, exit_time):
        """Close position completely"""

        emoji = "✅" if pos['total_pnl_pct'] > 0 else "❌"

        print(f"\n{emoji} POSITION CLOSED")
        print(f"   Direction: {pos['direction']}")
        print(f"   Entry: {pos['entry_price']:.2f} → Exit: {exit_price:.2f}")
        print(f"   TPs: TP1={pos['tp1_hit']}, TP2={pos['tp2_hit']}, TP3={pos['tp3_hit']}")
        print(f"   Exit: {exit_type}")
        print(f"   PnL: {pos['total_pnl_pct']:+.2f}%")

        self.closed_trades.append({
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'direction': pos['direction'],
            'pnl_pct': pos['total_pnl_pct'],
            'exit_type': exit_type,
            'tp1_hit': pos['tp1_hit'],
            'tp2_hit': pos['tp2_hit'],
            'tp3_hit': pos['tp3_hit'],
        })

    def run_simulation(self, df, start_from_idx=100, num_candles=50):
        """Simulate live trading on historical data"""

        print("\n" + "="*80)
        print("🤖 LIVE BOT SIMULATION (BASELINE 3TP)")
        print("="*80)
        print(f"Симулируем реальный трейдинг на исторических данных")
        print(f"Проверяем {num_candles} свечей начиная с индекса {start_from_idx}")
        print("="*80)

        for i in range(start_from_idx, min(start_from_idx + num_candles, len(df))):
            current_time = df.index[i]
            current_candle = df.iloc[i]

            print(f"\n📊 Candle {i}: {current_time} | Price: {current_candle['close']:.2f}")

            # Check for new signals
            signal_data = self.check_for_signals(df, i)
            if signal_data:
                signal, signal_time = signal_data
                self.open_position(signal, signal_time)

            # Check open positions
            if len(self.open_positions) > 0:
                self.check_positions(current_candle, current_time)

            # Show status
            if len(self.open_positions) > 0:
                print(f"   Open positions: {len(self.open_positions)}")
            if len(self.closed_trades) > 0:
                total_pnl = sum([t['pnl_pct'] for t in self.closed_trades])
                print(f"   Closed trades: {len(self.closed_trades)} | Total PnL: {total_pnl:+.2f}%")

        # Final summary
        print("\n" + "="*80)
        print("📊 SIMULATION COMPLETE")
        print("="*80)

        if len(self.closed_trades) > 0:
            total_pnl = sum([t['pnl_pct'] for t in self.closed_trades])
            wins = len([t for t in self.closed_trades if t['pnl_pct'] > 0])
            win_rate = (wins / len(self.closed_trades)) * 100

            print(f"\nTotal trades: {len(self.closed_trades)}")
            print(f"Win rate: {win_rate:.1f}%")
            print(f"Total PnL: {total_pnl:+.2f}%")

            # Show TP hit stats
            tp1_hits = sum([1 for t in self.closed_trades if t['tp1_hit']])
            tp2_hits = sum([1 for t in self.closed_trades if t['tp2_hit']])
            tp3_hits = sum([1 for t in self.closed_trades if t['tp3_hit']])

            print(f"\nTP hits:")
            print(f"  TP1: {tp1_hits}/{len(self.closed_trades)} ({tp1_hits/len(self.closed_trades)*100:.1f}%)")
            print(f"  TP2: {tp2_hits}/{len(self.closed_trades)} ({tp2_hits/len(self.closed_trades)*100:.1f}%)")
            print(f"  TP3: {tp3_hits}/{len(self.closed_trades)} ({tp3_hits/len(self.closed_trades)*100:.1f}%)")
        else:
            print("No trades closed during simulation")

        print(f"\nOpen positions: {len(self.open_positions)}")


def main():
    # Load data
    df = load_mt5_data()
    print(f"\n📊 Loaded {len(df)} candles")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")

    # Create bot
    bot = SimplePaperTradingBot(tp1=30, tp2=50, tp3=80,
                                close_pct1=0.5, close_pct2=0.3, close_pct3=0.2)

    # Run simulation on recent data (last 100 candles)
    bot.run_simulation(df, start_from_idx=len(df)-200, num_candles=100)


if __name__ == "__main__":
    main()
