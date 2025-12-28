"""
SCALPING BOT - MT5 Version
Fast-paced trading on M5/M15 timeframes with small targets

Отличия от H1 версии:
- Меньшие TP: 5/10/15 пунктов (вместо 30/50/80)
- Короткий timeout: 4 часа (вместо 48)
- Частые проверки: каждые 5-15 минут (вместо часа)
- Таймфрейм: M5 или M15 (вместо H1)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import sys
from dotenv import load_dotenv
import MetaTrader5 as mt5

# Import from parent directory
sys.path.append('../smc_trading_strategy')
from telegram_notifier import TelegramNotifier

# Import scalping strategy
from pattern_recognition_scalping import PatternRecognitionScalping


class ScalpingBotMT5:
    """Scalping bot with MT5 data source"""

    def __init__(self, telegram_token=None, telegram_chat_id=None, check_interval=300,
                 tp1=5, tp2=10, tp3=15, close_pct1=0.5, close_pct2=0.3, close_pct3=0.2,
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_M5, position_timeout=4):
        """
        Initialize scalping bot

        Args:
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            check_interval: Check frequency in seconds (default: 300 = 5 min)
            tp1, tp2, tp3: Take profit levels in points (default: 5/10/15 for scalping)
            close_pct1, close_pct2, close_pct3: Partial close percentages (default: 50%/30%/20%)
            symbol: MT5 symbol (default: 'XAUUSD')
            timeframe: MT5 timeframe (default: M5)
            position_timeout: Hours before force close (default: 4h for scalping)
        """
        self.strategy = PatternRecognitionScalping(fib_mode='standard')
        self.check_interval = check_interval
        self.symbol = symbol
        self.timeframe = timeframe
        self.position_timeout = position_timeout

        # Scalping TP configuration (smaller targets)
        self.tp1 = tp1
        self.tp2 = tp2
        self.tp3 = tp3
        self.close_pct1 = close_pct1
        self.close_pct2 = close_pct2
        self.close_pct3 = close_pct3

        # Telegram notifier
        if telegram_token and telegram_chat_id:
            self.notifier = TelegramNotifier(telegram_token, telegram_chat_id)
        else:
            self.notifier = None
            print("⚠️  Telegram notifications disabled")

        # Tracking
        self.open_positions = []
        self.df = None
        self.last_check = None
        self.closed_trades = []

        print("✅ Scalping Bot (MT5) initialized")
        print(f"   Symbol: {symbol}")
        print(f"   Timeframe: {timeframe}")
        print(f"   TP Scalping: {tp1}п/{tp2}п/{tp3}п")
        print(f"   Close %: {close_pct1*100:.0f}%/{close_pct2*100:.0f}%/{close_pct3*100:.0f}%")
        print(f"   Position timeout: {position_timeout}h")

    def connect_mt5(self, login=None, password=None, server=None):
        """Connect to MT5 terminal"""

        print("🔌 Connecting to MT5...")
        if not mt5.initialize():
            print(f"❌ Failed to initialize MT5: {mt5.last_error()}")
            return False

        if login and password and server:
            authorized = mt5.login(login, password=password, server=server)
            if not authorized:
                print(f"❌ Authorization failed: {mt5.last_error()}")
                mt5.shutdown()
                return False
            print(f"✅ Authorized: {login}")
        else:
            print("✅ Connected to MT5 (no auth)")

        # Check symbol
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Symbol {self.symbol} not found")
            mt5.shutdown()
            return False

        if not symbol_info.visible:
            if not mt5.symbol_select(self.symbol, True):
                print(f"❌ Failed to select {self.symbol}")
                mt5.shutdown()
                return False

        print(f"✅ Symbol {self.symbol} ready")
        return True

    def download_data(self, bars=200):
        """Download data from MT5 for scalping"""

        try:
            print(f"📥 Downloading {self.symbol} data (M5/M15)...")

            rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, bars)

            if rates is None or len(rates) == 0:
                print(f"❌ Failed to download: {mt5.last_error()}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['datetime'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('datetime')

            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            })

            df = df[['open', 'high', 'low', 'close', 'volume']]

            # Add market hours (important for scalping)
            df['is_london'] = df.index.hour.isin(range(7, 12))
            df['is_ny'] = df.index.hour.isin(range(13, 20))
            df['is_overlap'] = df.index.hour.isin(range(13, 16))
            df['is_active'] = df['is_london'] | df['is_ny']
            df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

            print(f"✅ Downloaded {len(df)} candles")
            print(f"   Latest: {df.index[-1]} | Price: {df['close'].iloc[-1]:.2f}")

            return df

        except Exception as e:
            print(f"❌ Error downloading: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_current_price(self):
        """Get current price from MT5"""
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return None
        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last,
            'time': datetime.fromtimestamp(tick.time)
        }

    def check_for_signals(self):
        """Check for scalping signals"""

        print(f"\n{'='*80}")
        print(f"🔍 Scalping check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Download latest data
        df = self.download_data()

        if df is None:
            print("❌ Failed to download data")
            return

        self.df = df

        # Run scalping strategy
        try:
            df_strategy = self.strategy.run_strategy(df.copy())

            # Get signals
            df_signals = df_strategy[df_strategy['signal'] != 0]

            if len(df_signals) == 0:
                print("📊 No scalping signals")
                return

            # Check last signal
            last_signal = df_signals.iloc[-1]
            last_signal_time = df_signals.index[-1]

            # For scalping, signal should be very recent (within last check interval)
            if self.last_check is not None:
                signal_age = (datetime.now() - last_signal_time.to_pydatetime()).total_seconds()

                # Only trigger if signal is fresh (within check interval + 5 min buffer)
                if signal_age > self.check_interval + 300:
                    print(f"📊 Signal too old ({signal_age/60:.1f} min), skipping")
                    return

            print(f"🎯 SCALPING SIGNAL!")
            print(f"   Time: {last_signal_time}")
            print(f"   Direction: {'LONG' if last_signal['signal'] == 1 else 'SHORT'}")
            print(f"   Entry: {last_signal['entry_price']:.2f}")
            print(f"   Pattern: {last_signal.get('pattern', 'N/A')}")

            # Open position
            self.open_position(last_signal, last_signal_time)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

            if self.notifier:
                self.notifier.send_error(f"Scalping error: {str(e)}")

    def open_position(self, signal, timestamp):
        """Open scalping position with 3 TP levels"""

        entry_price = signal['entry_price']
        direction = 'LONG' if signal['signal'] == 1 else 'SHORT'

        # Calculate scalping TPs (much smaller than H1)
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

        print(f"✅ SCALP Position opened: {direction} @ {entry_price:.2f}")
        print(f"   TP1: {tp1_price:.2f} ({self.close_pct1*100:.0f}%) = {self.tp1}п")
        print(f"   TP2: {tp2_price:.2f} ({self.close_pct2*100:.0f}%) = {self.tp2}п")
        print(f"   TP3: {tp3_price:.2f} ({self.close_pct3*100:.0f}%) = {self.tp3}п")
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

    def check_open_positions(self):
        """Check scalping positions (faster timeout)"""

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
                positions_to_close.append((i, pos['entry_price'], 'CLOSED', pos['total_pnl_pct']))
                continue

            # Check timeout (4 hours for scalping, not 48!)
            time_in_trade = (latest_time - pos['entry_time']).total_seconds() / 3600

            if time_in_trade >= self.position_timeout:
                # Force close by timeout
                if pos['direction'] == 'LONG':
                    pnl_pct = ((latest_close - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                else:
                    pnl_pct = ((pos['entry_price'] - latest_close) / pos['entry_price']) * 100 * pos['position_remaining']

                pos['total_pnl_pct'] += pnl_pct
                positions_to_close.append((i, latest_close, 'TIMEOUT', pos['total_pnl_pct']))
                continue

            # Check SL/TP
            if pos['direction'] == 'LONG':
                # SL
                if latest_low <= pos['stop_loss']:
                    pnl_pct = ((pos['stop_loss'] - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    positions_to_close.append((i, pos['stop_loss'], 'SL', pos['total_pnl_pct']))
                    continue

                # TPs
                if latest_high >= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['tp3_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} ({self.close_pct3*100:.0f}%)")

                if latest_high >= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['tp2_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} ({self.close_pct2*100:.0f}%)")

                if latest_high >= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['tp1_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} ({self.close_pct1*100:.0f}%)")

            else:  # SHORT
                # SL
                if latest_high >= pos['stop_loss']:
                    pnl_pct = ((pos['entry_price'] - pos['stop_loss']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    positions_to_close.append((i, pos['stop_loss'], 'SL', pos['total_pnl_pct']))
                    continue

                # TPs
                if latest_low <= pos['tp3_price'] and not pos['tp3_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp3_price']) / pos['entry_price']) * 100 * self.close_pct3
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct3
                    pos['tp3_hit'] = True
                    print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f} ({self.close_pct3*100:.0f}%)")

                if latest_low <= pos['tp2_price'] and not pos['tp2_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp2_price']) / pos['entry_price']) * 100 * self.close_pct2
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct2
                    pos['tp2_hit'] = True
                    print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f} ({self.close_pct2*100:.0f}%)")

                if latest_low <= pos['tp1_price'] and not pos['tp1_hit']:
                    pnl_pct = ((pos['entry_price'] - pos['tp1_price']) / pos['entry_price']) * 100 * self.close_pct1
                    pos['total_pnl_pct'] += pnl_pct
                    pos['position_remaining'] -= self.close_pct1
                    pos['tp1_hit'] = True
                    print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} ({self.close_pct1*100:.0f}%)")

        # Close positions
        for idx, exit_price, exit_type, total_pnl in reversed(positions_to_close):
            self.close_position(idx, exit_price, exit_type, latest_time, total_pnl)

    def close_position(self, position_idx, exit_price, exit_type, exit_time, total_pnl_pct=None):
        """Close scalping position"""

        pos = self.open_positions[position_idx]

        if total_pnl_pct is not None:
            pnl_pct = total_pnl_pct
        else:
            if pos['direction'] == 'LONG':
                pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
            else:
                pnl_pct = ((pos['entry_price'] - exit_price) / pos['entry_price']) * 100

        pnl_points = (pnl_pct / 100) * pos['entry_price']
        duration_minutes = (exit_time - pos['entry_time']).total_seconds() / 60

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
            'duration_minutes': duration_minutes,
            'pattern': pos['pattern']
        }

        self.closed_trades.append(closed_trade)

        emoji = "✅" if pnl_pct > 0 else "❌"
        print(f"\n{emoji} SCALP CLOSED:")
        print(f"   {pos['direction']}: {pos['entry_price']:.2f} → {exit_price:.2f}")
        print(f"   TPs: TP1={pos['tp1_hit']}, TP2={pos['tp2_hit']}, TP3={pos['tp3_hit']}")
        print(f"   Exit: {exit_type}")
        print(f"   PnL: {pnl_pct:+.2f}% ({pnl_points:+.2f}п)")
        print(f"   Duration: {duration_minutes:.0f} min")

        # Telegram notification
        if self.notifier:
            exit_data = {
                'direction': pos['direction'],
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'pnl_points': pnl_points,
                'duration_hours': duration_minutes / 60,
                'tp1_hit': pos['tp1_hit'],
                'tp2_hit': pos['tp2_hit'],
                'tp3_hit': pos['tp3_hit'],
                'timestamp': exit_time
            }
            self.notifier.send_exit_signal(exit_data)

        self.open_positions.pop(position_idx)

    def run(self):
        """Run scalping bot"""

        print("\n" + "="*80)
        print("🤖 SCALPING BOT STARTED (MT5)")
        print("="*80)
        print(f"⏱️  Check interval: {self.check_interval}s ({self.check_interval/60:.0f} min)")
        print(f"📊 Strategy: SMC Scalping")
        print(f"📈 Asset: {self.symbol}")
        print(f"⏰ Timeframe: M5/M15")
        print(f"🎯 TP Levels: {self.tp1}п / {self.tp2}п / {self.tp3}п")
        print(f"⏳ Position timeout: {self.position_timeout}h")
        print("="*80)

        # Test Telegram
        if self.notifier:
            if self.notifier.test_connection():
                self.notifier.send_startup_message()

        try:
            while True:
                # Check for signals
                self.check_for_signals()

                # Check positions
                self.check_open_positions()

                # Update
                self.last_check = datetime.now()

                # Status
                print(f"\n📊 Status:")
                print(f"   Open: {len(self.open_positions)}")
                print(f"   Closed: {len(self.closed_trades)}")
                if len(self.closed_trades) > 0:
                    total_pnl = sum([t['pnl_pct'] for t in self.closed_trades])
                    print(f"   Total PnL: {total_pnl:+.2f}%")

                # Current price
                price = self.get_current_price()
                if price:
                    print(f"\n💰 Price: Bid {price['bid']:.2f} | Ask {price['ask']:.2f}")

                print(f"\n⏳ Next check in {self.check_interval}s ({self.check_interval/60:.0f} min)...")
                print(f"   {(datetime.now() + timedelta(seconds=self.check_interval)).strftime('%H:%M:%S')}")

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\n\n⚠️  Scalping bot stopped")
            print(f"📊 Stats: {len(self.closed_trades)} trades, {len(self.open_positions)} open")
            mt5.shutdown()


def main():
    """Main entry point"""

    print("\n" + "="*80)
    print("🤖 SCALPING BOT SETUP (MT5)")
    print("="*80)

    # Load .env
    load_dotenv()

    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not telegram_token or not telegram_chat_id:
        print("\n⚠️  No Telegram credentials")
        print("   Create .env with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        input("\n   Press Enter to continue...")

    # Settings
    check_interval = int(os.getenv('SCALP_CHECK_INTERVAL', 300))  # 5 min default
    symbol = os.getenv('MT5_SYMBOL', 'XAUUSD')

    # Initialize bot
    bot = ScalpingBotMT5(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        check_interval=check_interval,
        symbol=symbol,
        timeframe=mt5.TIMEFRAME_M5,  # M5 for scalping
        tp1=5, tp2=10, tp3=15,  # Small scalping targets
        position_timeout=4  # 4 hours max
    )

    # Connect MT5
    if not bot.connect_mt5():
        print("\n❌ MT5 connection failed")
        return

    # Run
    bot.run()


if __name__ == "__main__":
    main()
