"""
Real-time paper trading bot with Telegram notifications
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import yfinance as yf
import os
from dotenv import load_dotenv

from pattern_recognition_strategy import PatternRecognitionStrategy
from telegram_notifier import TelegramNotifier


class PaperTradingBot:
    """Paper trading bot for Pattern Recognition strategy"""

    def __init__(self, telegram_token=None, telegram_chat_id=None, check_interval=3600):
        """
        Initialize paper trading bot

        Args:
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            check_interval: How often to check for signals (seconds), default 1 hour
        """
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')
        self.check_interval = check_interval

        # Telegram notifier
        if telegram_token and telegram_chat_id:
            self.notifier = TelegramNotifier(telegram_token, telegram_chat_id)
        else:
            self.notifier = None
            print("⚠️  Telegram notifications disabled (no token/chat_id)")

        # Open positions tracking
        self.open_positions = []

        # Historical data
        self.df = None
        self.last_check = None

        # Performance tracking
        self.closed_trades = []

        print("✅ Paper Trading Bot initialized")

    def download_realtime_data(self, symbol='GC=F', period='5d', interval='1h'):
        """
        Download real-time XAUUSD data from Yahoo Finance

        Args:
            symbol: 'GC=F' for Gold Futures (proxy for XAUUSD)
            period: How much history to download
            interval: Data interval (1h, 15m, etc.)
        """
        try:
            print(f"📥 Downloading {symbol} data...")

            # Download data
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df is None or len(df) == 0:
                print(f"❌ No data received from Yahoo Finance")
                return None

            # Rename columns to match our strategy
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # Keep only OHLCV
            df = df[['open', 'high', 'low', 'close', 'volume']]

            # Add market hours
            df['is_london'] = df.index.hour.isin(range(7, 12))
            df['is_ny'] = df.index.hour.isin(range(13, 20))
            df['is_overlap'] = df.index.hour.isin(range(13, 16))
            df['is_active'] = df['is_london'] | df['is_ny']
            df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

            print(f"✅ Downloaded {len(df)} candles")
            print(f"   Latest: {df.index[-1]} | Price: {df['close'].iloc[-1]:.2f}")

            return df

        except Exception as e:
            print(f"❌ Error downloading data: {e}")
            return None

    def check_for_signals(self):
        """Check for new trading signals"""

        print(f"\n{'='*80}")
        print(f"🔍 Checking for signals at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Download latest data
        df = self.download_realtime_data()

        if df is None:
            print("❌ Failed to download data, skipping check")
            return

        self.df = df

        # Run strategy
        try:
            df_strategy = self.strategy.run_strategy(df.copy())

            # Get signals
            df_signals = df_strategy[df_strategy['signal'] != 0]

            if len(df_signals) == 0:
                print("📊 No signals found")
                return

            # Check last signal
            last_signal = df_signals.iloc[-1]
            last_signal_time = df_signals.index[-1]

            # Check if this is a new signal (within last check interval)
            if self.last_check is not None:
                time_since_last = (datetime.now() - self.last_check).total_seconds()
                signal_age = (datetime.now() - last_signal_time.to_pydatetime()).total_seconds()

                # Only trigger if signal is recent (within our check interval)
                if signal_age > time_since_last + 3600:  # Allow 1 hour buffer
                    print(f"📊 Last signal is old ({signal_age/3600:.1f}h ago), ignoring")
                    return

            print(f"🎯 NEW SIGNAL DETECTED!")
            print(f"   Time: {last_signal_time}")
            print(f"   Direction: {'LONG' if last_signal['signal'] == 1 else 'SHORT'}")
            print(f"   Entry: {last_signal['entry_price']:.2f}")
            print(f"   SL: {last_signal['stop_loss']:.2f}")
            print(f"   TP: {last_signal['take_profit']:.2f}")

            # Open position
            self.open_position(last_signal, last_signal_time)

        except Exception as e:
            print(f"❌ Error checking signals: {e}")
            import traceback
            traceback.print_exc()

            if self.notifier:
                self.notifier.send_error(f"Error checking signals: {str(e)}")

    def open_position(self, signal, timestamp):
        """Open a new paper trading position"""

        position = {
            'entry_time': timestamp,
            'direction': 'LONG' if signal['signal'] == 1 else 'SHORT',
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'pattern': signal.get('pattern', 'N/A'),
            'signal_data': signal
        }

        self.open_positions.append(position)

        print(f"✅ Position opened: {position['direction']} @ {position['entry_price']:.2f}")

        # Send Telegram notification
        if self.notifier:
            signal_data = {
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'stop_loss': position['stop_loss'],
                'take_profit': position['take_profit'],
                'pattern': position['pattern'],
                'timestamp': timestamp
            }
            self.notifier.send_entry_signal(signal_data)

    def check_open_positions(self):
        """Check if any open positions hit SL/TP"""

        if len(self.open_positions) == 0:
            return

        if self.df is None:
            return

        # Get latest candle
        latest_candle = self.df.iloc[-1]
        latest_time = self.df.index[-1]
        latest_high = latest_candle['high']
        latest_low = latest_candle['low']
        latest_close = latest_candle['close']

        positions_to_close = []

        for i, pos in enumerate(self.open_positions):
            # Check timeout (48 hours)
            time_in_trade = (latest_time - pos['entry_time']).total_seconds() / 3600

            if time_in_trade >= 48:
                # Close by timeout
                positions_to_close.append((i, latest_close, 'EOD'))
                continue

            # Check SL/TP
            if pos['direction'] == 'LONG':
                if latest_low <= pos['stop_loss']:
                    positions_to_close.append((i, pos['stop_loss'], 'SL'))
                elif latest_high >= pos['take_profit']:
                    positions_to_close.append((i, pos['take_profit'], 'TP'))
            else:  # SHORT
                if latest_high >= pos['stop_loss']:
                    positions_to_close.append((i, pos['stop_loss'], 'SL'))
                elif latest_low <= pos['take_profit']:
                    positions_to_close.append((i, pos['take_profit'], 'TP'))

        # Close positions
        for idx, exit_price, exit_type in reversed(positions_to_close):
            self.close_position(idx, exit_price, exit_type, latest_time)

    def close_position(self, position_idx, exit_price, exit_type, exit_time):
        """Close a position"""

        pos = self.open_positions[position_idx]

        # Calculate PnL
        if pos['direction'] == 'LONG':
            pnl_points = exit_price - pos['entry_price']
            pnl_pct = (pnl_points / pos['entry_price']) * 100
        else:  # SHORT
            pnl_points = pos['entry_price'] - exit_price
            pnl_pct = (pnl_points / pos['entry_price']) * 100

        duration_hours = (exit_time - pos['entry_time']).total_seconds() / 3600

        closed_trade = {
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'stop_loss': pos['stop_loss'],
            'take_profit': pos['take_profit'],
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
            'pattern': pos['pattern']
        }

        self.closed_trades.append(closed_trade)

        emoji = "✅" if pnl_pct > 0 else "❌"
        print(f"\n{emoji} Position closed:")
        print(f"   Direction: {pos['direction']}")
        print(f"   Entry: {pos['entry_price']:.2f} → Exit: {exit_price:.2f}")
        print(f"   Exit type: {exit_type}")
        print(f"   PnL: {pnl_pct:+.2f}% ({pnl_points:+.2f} points)")
        print(f"   Duration: {duration_hours:.1f} hours")

        # Send Telegram notification
        if self.notifier:
            exit_data = {
                'direction': pos['direction'],
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'pnl_points': pnl_points,
                'duration_hours': duration_hours,
                'timestamp': exit_time
            }
            self.notifier.send_exit_signal(exit_data)

        # Remove from open positions
        self.open_positions.pop(position_idx)

    def send_daily_report(self):
        """Send daily summary to Telegram"""

        if not self.notifier:
            return

        if len(self.closed_trades) == 0:
            print("📊 No trades today, skipping daily report")
            return

        # Calculate daily stats
        trades_df = pd.DataFrame(self.closed_trades)

        # Filter today's trades
        today = datetime.now().date()
        trades_df['date'] = pd.to_datetime(trades_df['exit_time']).dt.date
        today_trades = trades_df[trades_df['date'] == today]

        if len(today_trades) == 0:
            print("📊 No trades closed today")
            return

        total_trades = len(today_trades)
        wins = len(today_trades[today_trades['pnl_pct'] > 0])
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        total_pnl = today_trades['pnl_pct'].sum()
        total_pnl_usd = today_trades['pnl_points'].sum() * 0.01  # Assume 0.01 lot

        summary_data = {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_pnl_usd': total_pnl_usd
        }

        self.notifier.send_daily_summary(summary_data)

    def run(self, send_startup_message=True):
        """Start the paper trading bot"""

        print("\n" + "="*80)
        print("🤖 PAPER TRADING BOT STARTED")
        print("="*80)
        print(f"⏱️  Check interval: {self.check_interval}s ({self.check_interval/3600:.1f}h)")
        print(f"📊 Strategy: Pattern Recognition (1.618)")
        print(f"📈 Asset: XAUUSD (Gold Futures - GC=F)")
        print("="*80)

        # Test Telegram connection
        if self.notifier:
            if self.notifier.test_connection():
                if send_startup_message:
                    self.notifier.send_startup_message()
            else:
                print("⚠️  Telegram connection failed, notifications disabled")
                self.notifier = None

        last_daily_report = datetime.now().date()

        try:
            while True:
                # Check for new signals
                self.check_for_signals()

                # Check open positions
                self.check_open_positions()

                # Send daily report (once per day)
                current_date = datetime.now().date()
                if current_date > last_daily_report:
                    self.send_daily_report()
                    last_daily_report = current_date

                # Update last check time
                self.last_check = datetime.now()

                # Display status
                print(f"\n📊 Status:")
                print(f"   Open positions: {len(self.open_positions)}")
                print(f"   Closed trades: {len(self.closed_trades)}")
                if len(self.closed_trades) > 0:
                    total_pnl = sum([t['pnl_pct'] for t in self.closed_trades])
                    print(f"   Total PnL: {total_pnl:+.2f}%")

                print(f"\n⏳ Next check in {self.check_interval}s...")
                print(f"   Next check: {(datetime.now() + timedelta(seconds=self.check_interval)).strftime('%Y-%m-%d %H:%M:%S')}")

                # Wait
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\n\n⚠️  Bot stopped by user")
            print(f"📊 Final stats: {len(self.closed_trades)} trades, {len(self.open_positions)} open")

        except Exception as e:
            print(f"\n❌ Bot crashed: {e}")
            import traceback
            traceback.print_exc()

            if self.notifier:
                self.notifier.send_error(f"Bot crashed: {str(e)}")


def main():
    """Main entry point"""

    print("\n" + "="*80)
    print("🤖 PAPER TRADING BOT SETUP")
    print("="*80)

    # Load environment variables from .env file
    load_dotenv()

    # Get Telegram credentials from environment
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not telegram_token or not telegram_chat_id:
        print("\n⚠️  WARNING: Telegram credentials not found!")
        print("   Create a .env file with:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token")
        print("   TELEGRAM_CHAT_ID=your_chat_id")
        print("\n   Bot will run WITHOUT Telegram notifications.")
        print("\n   Press Enter to continue or Ctrl+C to exit...")
        input()

    # Get check interval
    check_interval = int(os.getenv('CHECK_INTERVAL', 3600))  # Default 1 hour

    # Initialize bot
    bot = PaperTradingBot(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        check_interval=check_interval
    )

    # Run bot
    bot.run()


if __name__ == "__main__":
    main()
