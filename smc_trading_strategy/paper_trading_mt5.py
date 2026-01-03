"""
Real-time paper trading bot with MT5 data source
ВАЖНО: Работает только на Windows с установленным MT5
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv
import MetaTrader5 as mt5

from pattern_recognition_strategy import PatternRecognitionStrategy
from telegram_notifier import TelegramNotifier
from mt5_data_downloader import MT5DataDownloader


class PaperTradingBotMT5:
    """Paper trading bot with MT5 data source"""

    def __init__(self, telegram_token=None, telegram_chat_id=None, check_interval=3600,
                 tp1=30, tp2=50, tp3=80, close_pct1=0.5, close_pct2=0.3, close_pct3=0.2,
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1):
        """
        Initialize paper trading bot with MT5 data (baseline 3TP configuration)

        Args:
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            check_interval: How often to check for signals (seconds), default 1 hour
            tp1, tp2, tp3: Take profit levels in points (default: 30/50/80)
            close_pct1, close_pct2, close_pct3: Percentage to close at each TP (default: 50%/30%/20%)
            symbol: MT5 symbol (default: 'XAUUSD')
            timeframe: MT5 timeframe (default: mt5.TIMEFRAME_H1)
        """
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')
        self.check_interval = check_interval
        self.symbol = symbol
        self.timeframe = timeframe

        # Baseline 3TP configuration
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
            print("⚠️  Telegram notifications disabled (no token/chat_id)")

        # Open positions tracking
        self.open_positions = []

        # Historical data
        self.df = None
        self.last_check = None

        # Performance tracking
        self.closed_trades = []

        print("✅ Paper Trading Bot (MT5) initialized")
        print(f"   Symbol: {symbol}")
        print(f"   Timeframe: {timeframe}")
        print(f"   TP Configuration: {tp1}п/{tp2}п/{tp3}п")
        print(f"   Close %: {close_pct1*100:.0f}%/{close_pct2*100:.0f}%/{close_pct3*100:.0f}%")

    def connect_mt5(self, login=None, password=None, server=None):
        """
        Connect to MT5 terminal

        Args:
            login: Account number (optional)
            password: Password (optional)
            server: Broker server (optional)

        Returns:
            bool: True if connected successfully
        """
        return self.mt5_downloader.connect(login=login, password=password, server=server)

    def download_realtime_data(self, period_hours=120):
        """
        Download real-time data from MT5

        Args:
            period_hours: How many hours of history to download (default: 120 = 5 days)

        Returns:
            pd.DataFrame: OHLCV data with market hours
        """
        try:
            print(f"📥 Downloading {self.symbol} data from MT5...")

            # Download data using MT5 downloader
            df = self.mt5_downloader.get_realtime_data(period_hours=period_hours)

            if df is None or len(df) == 0:
                print(f"❌ Failed to download data from MT5")
                return None

            print(f"✅ Downloaded {len(df)} candles from MT5")
            print(f"   Latest: {df.index[-1]} | Price: {df['close'].iloc[-1]:.2f}")

            return df

        except Exception as e:
            print(f"❌ Error downloading MT5 data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_current_price(self):
        """Get current price from MT5"""
        return self.mt5_downloader.get_current_price()

    def check_for_signals(self):
        """Check for new trading signals"""

        print(f"\n{'='*80}")
        print(f"🔍 Checking for signals at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Download latest data from MT5
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
        """Open a new paper trading position with 3 TP levels"""

        entry_price = signal['entry_price']
        direction = 'LONG' if signal['signal'] == 1 else 'SHORT'

        # Calculate 3 TP levels
        if direction == 'LONG':
            tp1_price = entry_price + self.tp1
            tp2_price = entry_price + self.tp2
            tp3_price = entry_price + self.tp3
        else:  # SHORT
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
            'position_remaining': 1.0,  # 100% of position still open
            'total_pnl_pct': 0.0,  # Accumulated PnL from partial closes
            'pattern': signal.get('pattern', 'N/A'),
            'signal_data': signal
        }

        self.open_positions.append(position)

        print(f"✅ Position opened: {direction} @ {entry_price:.2f}")
        print(f"   TP1: {tp1_price:.2f} ({self.close_pct1*100:.0f}%)")
        print(f"   TP2: {tp2_price:.2f} ({self.close_pct2*100:.0f}%)")
        print(f"   TP3: {tp3_price:.2f} ({self.close_pct3*100:.0f}%)")
        print(f"   SL:  {signal['stop_loss']:.2f}")

        # Send Telegram notification
        if self.notifier:
            signal_data = {
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': signal['stop_loss'],
                'take_profit': tp1_price,  # Show first TP
                'tp1': tp1_price,
                'tp2': tp2_price,
                'tp3': tp3_price,
                'pattern': position['pattern'],
                'timestamp': timestamp
            }
            self.notifier.send_entry_signal(signal_data)

    def check_open_positions(self):
        """Check if any open positions hit SL/TP (3 TP levels with partial close)"""

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
            if pos['position_remaining'] <= 0:
                # Position fully closed
                positions_to_close.append((i, pos['entry_price'], 'CLOSED', pos['total_pnl_pct']))
                continue

            # Check timeout (48 hours)
            time_in_trade = (latest_time - pos['entry_time']).total_seconds() / 3600

            if time_in_trade >= 48:
                # Close remaining position by timeout
                if pos['direction'] == 'LONG':
                    pnl_pct = ((latest_close - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                else:
                    pnl_pct = ((pos['entry_price'] - latest_close) / pos['entry_price']) * 100 * pos['position_remaining']

                pos['total_pnl_pct'] += pnl_pct
                positions_to_close.append((i, latest_close, 'EOD', pos['total_pnl_pct']))
                continue

            # Check SL/TP
            if pos['direction'] == 'LONG':
                # Check SL first - closes entire remaining position
                if latest_low <= pos['stop_loss']:
                    pnl_pct = ((pos['stop_loss'] - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    positions_to_close.append((i, pos['stop_loss'], 'SL', pos['total_pnl_pct']))
                    continue

                # Check TPs in reverse order (TP3, TP2, TP1)
                if latest_high >= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['tp3_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} (closed {self.close_pct3*100:.0f}%, remaining {pos['position_remaining']*100:.0f}%)")

                if latest_high >= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['tp2_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} (closed {self.close_pct2*100:.0f}%, remaining {pos['position_remaining']*100:.0f}%)")

                if latest_high >= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['tp1_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} (closed {self.close_pct1*100:.0f}%, remaining {pos['position_remaining']*100:.0f}%)")

            else:  # SHORT
                # Check SL first - closes entire remaining position
                if latest_high >= pos['stop_loss']:
                    pnl_pct = ((pos['entry_price'] - pos['stop_loss']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    positions_to_close.append((i, pos['stop_loss'], 'SL', pos['total_pnl_pct']))
                    continue

                # Check TPs in reverse order
                if latest_low <= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp3_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} (closed {self.close_pct3*100:.0f}%, remaining {pos['position_remaining']*100:.0f}%)")

                if latest_low <= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp2_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} (closed {self.close_pct2*100:.0f}%, remaining {pos['position_remaining']*100:.0f}%)")

                if latest_low <= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp1_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} (closed {self.close_pct1*100:.0f}%, remaining {pos['position_remaining']*100:.0f}%)")

        # Close fully closed positions
        for idx, exit_price, exit_type, total_pnl in reversed(positions_to_close):
            self.close_position(idx, exit_price, exit_type, latest_time, total_pnl)

    def close_position(self, position_idx, exit_price, exit_type, exit_time, total_pnl_pct=None):
        """Close a position (full or partial close has been tracked)"""

        pos = self.open_positions[position_idx]

        # Use accumulated PnL from partial closes if provided
        if total_pnl_pct is not None:
            pnl_pct = total_pnl_pct
        else:
            # Calculate PnL for full position close
            if pos['direction'] == 'LONG':
                pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
            else:  # SHORT
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
            'tp1_price': pos['tp1_price'],
            'tp2_price': pos['tp2_price'],
            'tp3_price': pos['tp3_price'],
            'tp1_hit': pos['tp1_hit'],
            'tp2_hit': pos['tp2_hit'],
            'tp3_hit': pos['tp3_hit'],
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
            'pattern': pos['pattern']
        }

        self.closed_trades.append(closed_trade)

        emoji = "✅" if pnl_pct > 0 else "❌"
        print(f"\n{emoji} Position FULLY CLOSED:")
        print(f"   Direction: {pos['direction']}")
        print(f"   Entry: {pos['entry_price']:.2f} → Final Exit: {exit_price:.2f}")
        print(f"   TPs Hit: TP1={pos['tp1_hit']}, TP2={pos['tp2_hit']}, TP3={pos['tp3_hit']}")
        print(f"   Exit type: {exit_type}")
        print(f"   Total PnL: {pnl_pct:+.2f}% ({pnl_points:+.2f} points)")
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
                'tp1_hit': pos['tp1_hit'],
                'tp2_hit': pos['tp2_hit'],
                'tp3_hit': pos['tp3_hit'],
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
        print("🤖 PAPER TRADING BOT STARTED - BASELINE 3TP (MT5)")
        print("="*80)
        print(f"⏱️  Check interval: {self.check_interval}s ({self.check_interval/3600:.1f}h)")
        print(f"📊 Strategy: Pattern Recognition (1.618)")
        print(f"📈 Asset: {self.symbol}")
        print(f"🎯 TP Levels: {self.tp1}п / {self.tp2}п / {self.tp3}п")
        print(f"   Close %: {self.close_pct1*100:.0f}% / {self.close_pct2*100:.0f}% / {self.close_pct3*100:.0f}%")
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

                # Get current price
                current_price = self.get_current_price()
                if current_price:
                    print(f"\n💰 Current price:")
                    print(f"   Bid: {current_price['bid']:.2f}")
                    print(f"   Ask: {current_price['ask']:.2f}")

                print(f"\n⏳ Next check in {self.check_interval}s...")
                print(f"   Next check: {(datetime.now() + timedelta(seconds=self.check_interval)).strftime('%Y-%m-%d %H:%M:%S')}")

                # Wait
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\n\n⚠️  Bot stopped by user")
            print(f"📊 Final stats: {len(self.closed_trades)} trades, {len(self.open_positions)} open")
            self.mt5_downloader.disconnect()

        except Exception as e:
            print(f"\n❌ Bot crashed: {e}")
            import traceback
            traceback.print_exc()

            if self.notifier:
                self.notifier.send_error(f"Bot crashed: {str(e)}")

            self.mt5_downloader.disconnect()


def main():
    """Main entry point"""

    print("\n" + "="*80)
    print("🤖 PAPER TRADING BOT SETUP (MT5)")
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

    # Get MT5 settings
    symbol = os.getenv('MT5_SYMBOL', 'XAUUSD')
    mt5_login = os.getenv('MT5_LOGIN')
    mt5_password = os.getenv('MT5_PASSWORD')
    mt5_server = os.getenv('MT5_SERVER')

    # Initialize bot
    bot = PaperTradingBotMT5(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        check_interval=check_interval,
        symbol=symbol,
        timeframe=mt5.TIMEFRAME_H1
    )

    # Connect to MT5
    print("\n" + "="*80)
    print("🔌 Connecting to MT5...")
    print("="*80)

    if not bot.connect_mt5(login=mt5_login, password=mt5_password, server=mt5_server):
        print("\n❌ Failed to connect to MT5!")
        print("\n💡 Make sure:")
        print("   1. MT5 terminal is running")
        print("   2. You are on Windows")
        print("   3. MetaTrader5 module is installed: pip install MetaTrader5")
        print("\n   Optionally add to .env:")
        print("   MT5_LOGIN=your_account_number")
        print("   MT5_PASSWORD=your_password")
        print("   MT5_SERVER=your_broker_server")
        return

    # Run bot
    bot.run()


if __name__ == "__main__":
    main()
