"""
Улучшенный Paper Trading Bot с разделением частоты проверок
- Новые сигналы: каждый час (тяжелая операция)
- Открытые позиции: каждые 5 минут (легкая операция)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import sys
from dotenv import load_dotenv
import MetaTrader5 as mt5

sys.path.append('../smc_trading_strategy')
from telegram_notifier import TelegramNotifier
from mt5_data_downloader import MT5DataDownloader
from pattern_recognition_strategy import PatternRecognitionStrategy


class ImprovedPaperTradingBot:
    """
    Paper trading bot с улучшенной частотой проверок

    Ключевое улучшение:
    - Новые сигналы проверяются редко (signal_check_interval, например 1 час)
    - Открытые позиции проверяются часто (position_check_interval, например 5 мин)

    Это решает проблему:
    - TP/SL обнаруживаются в течение 5 минут (не часа!)
    - Новые сигналы ищутся реже (экономия ресурсов)
    """

    def __init__(self, telegram_token=None, telegram_chat_id=None,
                 signal_check_interval=3600,    # 1 час для новых сигналов
                 position_check_interval=300,   # 5 минут для позиций
                 tp1=30, tp2=50, tp3=80,
                 close_pct1=0.5, close_pct2=0.3, close_pct3=0.2,
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1):
        """
        Initialize improved paper trading bot

        Args:
            signal_check_interval: Как часто искать НОВЫЕ сигналы (секунды, default: 3600 = 1 час)
            position_check_interval: Как часто проверять ОТКРЫТЫЕ позиции (секунды, default: 300 = 5 мин)
            tp1, tp2, tp3: Take profit levels in points
            close_pct1, close_pct2, close_pct3: Partial close percentages
            symbol: MT5 symbol
            timeframe: MT5 timeframe
        """
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')
        self.signal_check_interval = signal_check_interval
        self.position_check_interval = position_check_interval
        self.symbol = symbol
        self.timeframe = timeframe

        # TP configuration
        self.tp1 = tp1
        self.tp2 = tp2
        self.tp3 = tp3
        self.close_pct1 = close_pct1
        self.close_pct2 = close_pct2
        self.close_pct3 = close_pct3

        # MT5 data downloader
        self.mt5_downloader = MT5DataDownloader(symbol=symbol, timeframe=timeframe)

        # Telegram notifier
        if telegram_token and telegram_chat_id:
            self.notifier = TelegramNotifier(telegram_token, telegram_chat_id)
        else:
            self.notifier = None
            print("⚠️  Telegram notifications disabled")

        # Tracking
        self.open_positions = []
        self.df = None
        self.last_signal_check = None
        self.last_position_check = None
        self.closed_trades = []

        print("✅ Improved Paper Trading Bot (MT5) initialized")
        print(f"   Symbol: {symbol}")
        print(f"   ⏰ Signal check: every {signal_check_interval}s ({signal_check_interval/60:.0f} min)")
        print(f"   ⏰ Position check: every {position_check_interval}s ({position_check_interval/60:.0f} min)")
        print(f"   🎯 TP: {tp1}п/{tp2}п/{tp3}п (Close: {close_pct1*100:.0f}%/{close_pct2*100:.0f}%/{close_pct3*100:.0f}%)")

    def connect_mt5(self, login=None, password=None, server=None):
        """Connect to MT5 terminal"""
        return self.mt5_downloader.connect(login=login, password=password, server=server)

    def download_data(self, period_hours=120):
        """Download data from MT5"""
        try:
            print(f"📥 Downloading {self.symbol} data...")
            df = self.mt5_downloader.get_realtime_data(period_hours=period_hours)

            if df is None or len(df) == 0:
                print(f"❌ Failed to download data")
                return None

            print(f"✅ Downloaded {len(df)} candles | Latest: {df.index[-1]} | Price: {df['close'].iloc[-1]:.2f}")
            return df

        except Exception as e:
            print(f"❌ Error downloading: {e}")
            return None

    def get_current_price(self):
        """Get current price from MT5 (быстро!)"""
        return self.mt5_downloader.get_current_price()

    def check_for_signals(self):
        """Check for new trading signals (ТЯЖЕЛАЯ операция - делаем редко)"""

        print(f"\n{'='*80}")
        print(f"🔍 SIGNAL CHECK at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Download latest data
        df = self.download_data()

        if df is None:
            print("❌ Failed to download data")
            return

        self.df = df

        # Run strategy
        try:
            df_strategy = self.strategy.run_strategy(df.copy())
            df_signals = df_strategy[df_strategy['signal'] != 0]

            if len(df_signals) == 0:
                print("📊 No signals found")
                return

            # Check last signal
            last_signal = df_signals.iloc[-1]
            last_signal_time = df_signals.index[-1]

            # Check if signal is recent
            if self.last_signal_check is not None:
                time_since_last = (datetime.now() - self.last_signal_check).total_seconds()
                signal_age = (datetime.now() - last_signal_time.to_pydatetime()).total_seconds()

                if signal_age > time_since_last + 3600:
                    print(f"📊 Signal too old ({signal_age/3600:.1f}h), ignoring")
                    return

            print(f"🎯 NEW SIGNAL DETECTED!")
            print(f"   Time: {last_signal_time}")
            print(f"   Direction: {'LONG' if last_signal['signal'] == 1 else 'SHORT'}")
            print(f"   Entry: {last_signal['entry_price']:.2f}")

            # Open position
            self.open_position(last_signal, last_signal_time)

        except Exception as e:
            print(f"❌ Error checking signals: {e}")
            import traceback
            traceback.print_exc()

    def open_position(self, signal, timestamp):
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
            'entry_time': timestamp,
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
            'pattern': signal.get('pattern', 'N/A'),
            'signal_data': signal
        }

        self.open_positions.append(position)

        print(f"✅ Position opened: {direction} @ {entry_price:.2f}")
        print(f"   TP1: {tp1_price:.2f} ({self.close_pct1*100:.0f}%)")
        print(f"   TP2: {tp2_price:.2f} ({self.close_pct2*100:.0f}%)")
        print(f"   TP3: {tp3_price:.2f} ({self.close_pct3*100:.0f}%)")
        print(f"   SL:  {signal['stop_loss']:.2f}")

        # Telegram notification
        if self.notifier:
            signal_data = {
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': signal['stop_loss'],
                'take_profit': tp1_price,
                'tp1': tp1_price,
                'tp2': tp2_price,
                'tp3': tp3_price,
                'pattern': position['pattern'],
                'timestamp': timestamp
            }
            self.notifier.send_entry_signal(signal_data)

    def check_open_positions_fast(self):
        """
        Check open positions using CURRENT PRICE only (БЫСТРО!)
        Не нужно скачивать всю историю, только текущая цена
        """

        if len(self.open_positions) == 0:
            return

        # Get current price (быстро - один тик!)
        current_price_data = self.get_current_price()

        if current_price_data is None:
            print("⚠️  Could not get current price")
            return

        current_time = current_price_data['time']
        current_bid = current_price_data['bid']
        current_ask = current_price_data['ask']

        # Use bid for LONG exits, ask for SHORT exits (realistic)
        positions_to_close = []

        for i, pos in enumerate(self.open_positions):
            if pos['position_remaining'] <= 0:
                positions_to_close.append((i, pos['entry_price'], 'CLOSED', pos['total_pnl_pct']))
                continue

            # Check timeout (48 hours)
            time_in_trade = (current_time - pos['entry_time']).total_seconds() / 3600

            if time_in_trade >= 48:
                # Force close at current price
                exit_price = current_bid if pos['direction'] == 'LONG' else current_ask

                if pos['direction'] == 'LONG':
                    pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                else:
                    pnl_pct = ((pos['entry_price'] - exit_price) / pos['entry_price']) * 100 * pos['position_remaining']

                pos['total_pnl_pct'] += pnl_pct
                positions_to_close.append((i, exit_price, 'TIMEOUT', pos['total_pnl_pct']))
                continue

            # Check SL/TP based on current price
            if pos['direction'] == 'LONG':
                # Use bid for exits
                exit_price = current_bid

                # Check SL
                if exit_price <= pos['stop_loss']:
                    pnl_pct = ((pos['stop_loss'] - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    positions_to_close.append((i, pos['stop_loss'], 'SL', pos['total_pnl_pct']))
                    continue

                # Check TPs (обратный порядок)
                if exit_price >= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['tp3_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} ({self.close_pct3*100:.0f}%)")

                if exit_price >= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['tp2_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} ({self.close_pct2*100:.0f}%)")

                if exit_price >= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['tp1_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} ({self.close_pct1*100:.0f}%)")

            else:  # SHORT
                # Use ask for exits
                exit_price = current_ask

                # Check SL
                if exit_price >= pos['stop_loss']:
                    pnl_pct = ((pos['entry_price'] - pos['stop_loss']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    positions_to_close.append((i, pos['stop_loss'], 'SL', pos['total_pnl_pct']))
                    continue

                # Check TPs
                if exit_price <= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp3_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} ({self.close_pct3*100:.0f}%)")

                if exit_price <= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp2_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} ({self.close_pct2*100:.0f}%)")

                if exit_price <= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp1_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} ({self.close_pct1*100:.0f}%)")

        # Close positions
        for idx, exit_price, exit_type, total_pnl in reversed(positions_to_close):
            self.close_position(idx, exit_price, exit_type, current_time, total_pnl)

    def close_position(self, position_idx, exit_price, exit_type, exit_time, total_pnl_pct=None):
        """Close position"""

        pos = self.open_positions[position_idx]

        if total_pnl_pct is not None:
            pnl_pct = total_pnl_pct
        else:
            if pos['direction'] == 'LONG':
                pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
            else:
                pnl_pct = ((pos['entry_price'] - exit_price) / pos['entry_price']) * 100

        pnl_points = (pnl_pct / 100) * pos['entry_price']
        duration_hours = (exit_time - pos['entry_time']).total_seconds() / 3600

        closed_trade = {
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'stop_loss': pos['stop_loss'],
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
            'pattern': pos['pattern']
        }

        self.closed_trades.append(closed_trade)

        emoji = "✅" if pnl_pct > 0 else "❌"
        print(f"\n{emoji} POSITION CLOSED:")
        print(f"   {pos['direction']}: {pos['entry_price']:.2f} → {exit_price:.2f}")
        print(f"   TPs: TP1={pos['tp1_hit']}, TP2={pos['tp2_hit']}, TP3={pos['tp3_hit']}")
        print(f"   Exit: {exit_type}")
        print(f"   PnL: {pnl_pct:+.2f}% ({pnl_points:+.2f}п)")
        print(f"   Duration: {duration_hours:.1f}h")

        # Telegram notification
        if self.notifier:
            exit_data = {
                'direction': pos['direction'],
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'pnl_points': pnl_points,
                'duration_hours': duration_hours,
                'tp1_hit': pos['tp1_hit'],
                'tp2_hit': pos['tp2_hit'],
                'tp3_hit': pos['tp3_hit'],
                'timestamp': exit_time
            }
            self.notifier.send_exit_signal(exit_data)

        self.open_positions.pop(position_idx)

    def run(self):
        """Run bot with dual-frequency checking"""

        print("\n" + "="*80)
        print("🤖 IMPROVED PAPER TRADING BOT (MT5) - DUAL FREQUENCY")
        print("="*80)
        print(f"📊 Strategy: Pattern Recognition (1.618)")
        print(f"📈 Asset: {self.symbol}")
        print(f"🎯 TP: {self.tp1}п/{self.tp2}п/{self.tp3}п")
        print(f"")
        print(f"⏰ DUAL FREQUENCY CHECKING:")
        print(f"   🔍 New signals: every {self.signal_check_interval}s ({self.signal_check_interval/60:.0f} min)")
        print(f"   💰 Open positions: every {self.position_check_interval}s ({self.position_check_interval/60:.0f} min)")
        print(f"")
        print(f"💡 Benefits:")
        print(f"   ✅ TP/SL detected within {self.position_check_interval/60:.0f} minutes (not {self.signal_check_interval/60:.0f}!)")
        print(f"   ✅ Less load on MT5 (full data only every {self.signal_check_interval/60:.0f} min)")
        print(f"   ✅ Faster reactions to price movements")
        print("="*80)

        # Test Telegram
        if self.notifier:
            if self.notifier.test_connection():
                self.notifier.send_startup_message()

        # Initialize timing
        last_signal_check = datetime.now() - timedelta(seconds=self.signal_check_interval)
        last_position_check = datetime.now()

        try:
            iteration = 0
            while True:
                iteration += 1
                current_time = datetime.now()

                # Check if it's time for signal check
                time_since_signal_check = (current_time - last_signal_check).total_seconds()

                if time_since_signal_check >= self.signal_check_interval:
                    self.check_for_signals()
                    last_signal_check = current_time

                # Check if it's time for position check
                time_since_position_check = (current_time - last_position_check).total_seconds()

                if time_since_position_check >= self.position_check_interval:
                    if len(self.open_positions) > 0:
                        print(f"\n{'='*60}")
                        print(f"💰 POSITION CHECK #{iteration} at {current_time.strftime('%H:%M:%S')}")
                        print(f"{'='*60}")
                        self.check_open_positions_fast()
                    last_position_check = current_time

                # Display status (каждые N итераций)
                if iteration % 5 == 0:
                    print(f"\n📊 Status ({current_time.strftime('%H:%M:%S')}):")
                    print(f"   Open: {len(self.open_positions)} | Closed: {len(self.closed_trades)}")

                    if len(self.closed_trades) > 0:
                        total_pnl = sum([t['pnl_pct'] for t in self.closed_trades])
                        print(f"   Total PnL: {total_pnl:+.2f}%")

                    # Show current price
                    price = self.get_current_price()
                    if price:
                        print(f"   Price: Bid {price['bid']:.2f} | Ask {price['ask']:.2f}")

                    # Next checks
                    next_signal = last_signal_check + timedelta(seconds=self.signal_check_interval)
                    next_position = last_position_check + timedelta(seconds=self.position_check_interval)

                    print(f"\n⏳ Next signal check: {next_signal.strftime('%H:%M:%S')} ({(next_signal - current_time).total_seconds()/60:.0f} min)")
                    print(f"⏳ Next position check: {next_position.strftime('%H:%M:%S')} ({(next_position - current_time).total_seconds()/60:.0f} min)")

                # Sleep for a short time (используем меньший из двух интервалов)
                sleep_time = min(self.position_check_interval, 60)  # Max 1 min sleep
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n\n⚠️  Bot stopped by user")
            print(f"📊 Stats: {len(self.closed_trades)} trades, {len(self.open_positions)} open")
            self.mt5_downloader.disconnect()


def main():
    """Main entry point"""

    load_dotenv()

    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    # Get intervals from env or use defaults
    signal_interval = int(os.getenv('SIGNAL_CHECK_INTERVAL', 3600))      # 1 hour
    position_interval = int(os.getenv('POSITION_CHECK_INTERVAL', 300))   # 5 min

    symbol = os.getenv('MT5_SYMBOL', 'XAUUSD')

    # Initialize bot
    bot = ImprovedPaperTradingBot(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        signal_check_interval=signal_interval,
        position_check_interval=position_interval,
        symbol=symbol,
        timeframe=mt5.TIMEFRAME_H1
    )

    # Connect MT5
    if not bot.connect_mt5():
        print("\n❌ MT5 connection failed")
        return

    # Run
    bot.run()


if __name__ == "__main__":
    main()
