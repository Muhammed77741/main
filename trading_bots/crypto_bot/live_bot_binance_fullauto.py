"""
Full-Auto Live Trading Bot for Binance (BTC/ETH)
Uses V3 Adaptive Strategy with TREND/RANGE detection
Adapted from XAUUSD bot for cryptocurrency trading

⚠️ DANGEROUS: Trades automatically without confirmation!
"""

import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import sys
from pathlib import Path
import csv
import os
import asyncio

# Add parent directory to path to access shared modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.pattern_recognition_strategy import PatternRecognitionStrategy


class LiveBotBinanceFullAuto:
    """
    Full-automatic trading bot for Binance (BTC/ETH)

    Features:
    - Uses V3 Adaptive Strategy with TREND/RANGE detection
    - Automatic position opening/closing
    - Adapts TP levels based on market regime
    - Risk management
    - Optional Telegram notifications
    - DRY RUN mode for testing
    - Multi-symbol support (BTC, ETH)
    """

    def __init__(self, telegram_token=None, telegram_chat_id=None,
                 symbol='BTC/USDT', timeframe='1h',
                 check_interval=3600, risk_percent=2.0, max_positions=3,
                 dry_run=False, testnet=True, api_key=None, api_secret=None,
                 trailing_stop_enabled=True, trailing_stop_percent=1.5):
        """
        Initialize bot

        Args:
            telegram_token: Telegram bot token (optional)
            telegram_chat_id: Telegram chat ID (optional)
            symbol: Trading symbol (BTC/USDT, ETH/USDT)
            timeframe: Binance timeframe (1h, 4h, etc.)
            check_interval: Check interval in seconds
            risk_percent: Risk per trade (%)
            max_positions: Max simultaneous positions
            dry_run: If True, no real trades
            testnet: If True, use Binance testnet
            api_key: Binance API key
            api_secret: Binance API secret
            trailing_stop_enabled: Enable trailing stop
            trailing_stop_percent: Trailing stop activation threshold (%)
        """
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.check_interval = check_interval
        self.risk_percent = risk_percent
        self.max_positions = max_positions
        self.dry_run = dry_run
        self.testnet = testnet
        self.api_key = api_key
        self.api_secret = api_secret

        # Trailing stop settings
        self.trailing_stop_enabled = trailing_stop_enabled
        self.trailing_stop_percent = trailing_stop_percent  # Activate trailing after X% profit
        self.trailing_distance_percent = 0.5  # Trail at 0.5% below peak

        # Initialize strategy
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')

        # TREND MODE parameters (strong trend) - в процентах от цены
        self.trend_tp1_pct = 1.5   # 1.5%
        self.trend_tp2_pct = 2.75  # 2.75%
        self.trend_tp3_pct = 4.5   # 4.5%

        # RANGE MODE parameters (sideways) - в процентах от цены
        self.range_tp1_pct = 1.0   # 1.0%
        self.range_tp2_pct = 1.75  # 1.75%
        self.range_tp3_pct = 2.5   # 2.5%

        # Current market regime
        self.current_regime = 'RANGE'

        # Position tracking
        self.trades_file = f'bot_trades_log_{symbol.replace("/", "_")}.csv'
        self.tp_hits_file = f'bot_tp_hits_log_{symbol.replace("/", "_")}.csv'
        self.positions_tracker = {}  # {order_id: position_data}
        self.position_peaks = {}  # Track highest profit for trailing stop
        self._initialize_trades_log()
        self._initialize_tp_hits_log()

        # Telegram bot (optional)
        self.telegram_bot = None
        if telegram_token and telegram_chat_id:
            try:
                from telegram import Bot
                self.telegram_bot = Bot(token=telegram_token)
            except Exception as e:
                print(f"⚠️  Telegram init failed: {e}")

        # Exchange connection
        self.exchange = None
        self.exchange_connected = False

    def _initialize_trades_log(self):
        """Initialize CSV file for trade logging"""
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Order_ID', 'Open_Time', 'Close_Time', 'Type', 'Amount',
                    'Entry_Price', 'SL', 'TP', 'Close_Price', 'Profit',
                    'Profit_Pct', 'Market_Regime', 'Duration_Hours', 'Status', 'Comment'
                ])
            print(f"📝 Created trade log file: {self.trades_file}")

    def _initialize_tp_hits_log(self):
        """Initialize CSV file for TP hits logging"""
        if not os.path.exists(self.tp_hits_file):
            with open(self.tp_hits_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Order_ID', 'TP_Level', 'Type', 'Amount',
                    'Entry_Price', 'TP_Target', 'Current_Price', 'SL',
                    'Profit', 'Profit_Pct', 'Market_Regime', 'Duration_Minutes', 'Comment'
                ])
            print(f"📝 Created TP hits log file: {self.tp_hits_file}")

    def _log_position_opened(self, order_id, position_type, amount, entry_price,
                             sl, tp, regime, comment=''):
        """Log when position is opened"""
        self.positions_tracker[order_id] = {
            'order_id': order_id,
            'open_time': datetime.now(),
            'close_time': None,
            'type': position_type,
            'amount': amount,
            'entry_price': entry_price,
            'sl': sl,
            'tp': tp,
            'close_price': None,
            'profit': None,
            'profit_pct': None,
            'regime': regime,
            'duration': None,
            'status': 'OPEN',
            'comment': comment
        }
        print(f"📊 Logged opened position: Order={order_id}, Type={position_type}, Entry={entry_price}")

    def _log_position_closed(self, order_id, close_price, profit, status='CLOSED'):
        """Log when position is closed"""
        if order_id not in self.positions_tracker:
            print(f"⚠️  Order {order_id} not found in tracker")
            return

        pos = self.positions_tracker[order_id]
        pos['close_time'] = datetime.now()
        pos['close_price'] = close_price
        pos['profit'] = profit
        pos['status'] = status

        # Calculate duration
        if pos['open_time']:
            duration = (pos['close_time'] - pos['open_time']).total_seconds() / 3600
            pos['duration'] = round(duration, 2)

        # Calculate profit percentage
        if pos['type'] == 'BUY':
            profit_pct = ((close_price - pos['entry_price']) / pos['entry_price']) * 100
        else:
            profit_pct = ((pos['entry_price'] - close_price) / pos['entry_price']) * 100
        pos['profit_pct'] = round(profit_pct, 2)

        # Write to CSV
        self._write_trade_to_csv(pos)

        # Remove from tracker
        del self.positions_tracker[order_id]

        print(f"📊 Logged closed position: Order={order_id}, Profit={profit:.2f} USDT, Profit%={profit_pct:.2f}%, Duration={pos['duration']}h")

    def _write_trade_to_csv(self, trade_data):
        """Write completed trade to CSV file"""
        with open(self.trades_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trade_data['order_id'],
                trade_data['open_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_data['open_time'] else '',
                trade_data['close_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_data['close_time'] else '',
                trade_data['type'],
                trade_data['amount'],
                trade_data['entry_price'],
                trade_data['sl'],
                trade_data['tp'],
                trade_data['close_price'],
                trade_data['profit'],
                trade_data['profit_pct'],
                trade_data['regime'],
                trade_data['duration'],
                trade_data['status'],
                trade_data['comment']
            ])

    def _log_tp_hit(self, order_id, tp_level, current_price):
        """Log when a TP level is hit"""
        if order_id not in self.positions_tracker:
            return

        pos = self.positions_tracker[order_id]

        # Calculate duration in minutes
        duration_minutes = 0
        if pos['open_time']:
            duration_minutes = (datetime.now() - pos['open_time']).total_seconds() / 60

        # Calculate profit percentage
        if pos['type'] == 'BUY':
            profit_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
        else:
            profit_pct = ((pos['entry_price'] - current_price) / pos['entry_price']) * 100

        # Estimate profit in USDT
        profit = profit_pct / 100 * pos['entry_price'] * pos['amount']

        # Write to TP hits log
        with open(self.tp_hits_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                order_id,
                tp_level,
                pos['type'],
                pos['amount'],
                pos['entry_price'],
                pos['tp'],
                current_price,
                pos['sl'],
                round(profit, 2),
                round(profit_pct, 2),
                pos['regime'],
                round(duration_minutes, 1),
                pos['comment']
            ])

        print(f"🎯 TP HIT LOGGED: Order={order_id}, Level={tp_level}, Price={current_price:.2f}, Profit%={profit_pct:.2f}%")

    def connect_exchange(self):
        """Connect to Binance"""
        try:
            # Validate API credentials
            if not self.api_key or not self.api_secret:
                print("❌ Binance API key and secret are required!")
                print("💡 Please configure them in Settings:")
                print("   1. Go to Settings for this bot")
                print("   2. Enter your Binance API Key and API Secret")
                print("   3. Enable 'Use Testnet' for testing (recommended)")
                return False

            if len(self.api_key) < 10 or len(self.api_secret) < 10:
                print("❌ Invalid API credentials format")
                print(f"   API Key length: {len(self.api_key)} (expected 64)")
                print(f"   API Secret length: {len(self.api_secret)} (expected 64)")
                return False

            print(f"🔄 Connecting to Binance {'Testnet' if self.testnet else 'Mainnet'}...")
            print(f"   Symbol: {self.symbol}")
            print(f"   API Key: {self.api_key[:8]}...{self.api_key[-4:]}")

            if self.testnet:
                # Testnet configuration
                print("⚠️  Using TESTNET - no real money will be traded")
                self.exchange = ccxt.binance({
                    'apiKey': self.api_key,
                    'secret': self.api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                        'adjustForTimeDifference': True,
                    },
                    'urls': {
                        'api': {
                            'public': 'https://testnet.binancefuture.com/fapi/v1',
                            'private': 'https://testnet.binancefuture.com/fapi/v1',
                        },
                        'test': {
                            'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                            'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
                        }
                    }
                })
            else:
                # Mainnet configuration
                print("⚠️  Using MAINNET - real money trading!")
                self.exchange = ccxt.binance({
                    'apiKey': self.api_key,
                    'secret': self.api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                        'adjustForTimeDifference': True,  # Auto-adjust for time sync
                    }
                })

            # Test connection
            print("🔄 Testing connection...")
            balance = self.exchange.fetch_balance()

            # Set position mode to One-Way (not Hedge mode) for simpler position tracking
            try:
                # Check current position mode
                position_mode = self.exchange.fapiPrivateGetPositionSideDual()
                is_hedge = position_mode.get('dualSidePosition', True)

                print(f"📊 Position mode: {'Hedge Mode' if is_hedge else 'One-Way Mode'}")

                # If in hedge mode, switch to one-way mode
                if is_hedge:
                    print("🔄 Switching to One-Way position mode...")
                    self.exchange.fapiPrivatePostPositionSideDual({'dualSidePosition': 'false'})
                    print("✅ Switched to One-Way position mode")
            except Exception as e:
                print(f"⚠️  Could not check/set position mode: {e}")

            self.exchange_connected = True

            usdt_free = balance.get('USDT', {}).get('free', 0) or 0
            print(f"✅ Connected to Binance {'Testnet' if self.testnet else 'Mainnet'}")
            print(f"   Available balance: {usdt_free:.2f} USDT")
            return True

        except ccxt.AuthenticationError as e:
            print(f"❌ Authentication Failed: {e}")
            print("\n💡 Troubleshooting:")
            print("   1. Check your API Key and Secret are correct")
            print("   2. Ensure API has 'Enable Futures' permission")
            print("   3. If using Testnet, get keys from: https://testnet.binancefuture.com/")
            print("   4. If using Mainnet, get keys from: https://www.binance.com/")
            print("\n⚠️  Common issues:")
            print("   - Wrong API keys (copy-paste error)")
            print("   - Using Mainnet keys on Testnet (or vice versa)")
            print("   - API doesn't have Futures trading permission")
            return False

        except ccxt.ExchangeError as e:
            error_msg = str(e)
            print(f"❌ Binance Error: {e}")

            if '-1022' in error_msg or 'Signature' in error_msg:
                print("\n💡 Signature Error - Possible causes:")
                print("   1. API Secret is incorrect")
                print("   2. System time is not synchronized")
                print("   3. Wrong Testnet/Mainnet configuration")
                print("\n🔧 Try these fixes:")
                print("   1. Double-check your API Secret (no extra spaces)")
                print("   2. Sync your system time: Settings → Time & Language → Sync now")
                print("   3. Enable 'Use Testnet' in bot settings for testing")
            elif '-1021' in error_msg or 'Timestamp' in error_msg:
                print("\n💡 Time Synchronization Error:")
                print("   Your system time is not synchronized with Binance")
                print("\n🔧 Fix:")
                print("   Windows: Settings → Time & Language → Sync now")
                print("   Or enable automatic time synchronization")

            return False

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            return False

    def disconnect_exchange(self):
        """Disconnect from Binance"""
        if self.exchange_connected:
            self.exchange.close()
            self.exchange_connected = False

    def update_trailing_stops(self):
        """
        Update trailing stops for all open positions

        Logic:
        1. Check each open position's current profit
        2. If profit > threshold (e.g. 1.5%), activate trailing
        3. Track peak profit for this position
        4. Move SL up to lock in profits (peak - trailing_distance%)
        """
        if not self.trailing_stop_enabled or not self.exchange_connected:
            return

        try:
            # Get open positions
            positions = self.exchange.fetch_positions([self.symbol])

            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts <= 0:
                    continue

                # Get position details
                order_id = pos.get('id', '')
                entry_price = float(pos.get('entryPrice', 0))
                current_price = float(pos.get('markPrice', 0))
                side = pos.get('side', '').lower()  # 'long' or 'short'
                unrealized_pnl_pct = float(pos.get('percentage', 0))

                # Skip if no valid data
                if not entry_price or not current_price:
                    continue

                # Calculate profit percentage
                if side == 'long':
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                else:  # short
                    profit_pct = ((entry_price - current_price) / entry_price) * 100

                # Check if trailing should be activated
                if profit_pct < self.trailing_stop_percent:
                    # Not enough profit yet to activate trailing
                    continue

                # Track peak profit
                if order_id not in self.position_peaks:
                    self.position_peaks[order_id] = {
                        'peak_price': current_price,
                        'peak_profit_pct': profit_pct,
                        'entry_price': entry_price,
                        'side': side,
                        'trailing_active': False
                    }
                    print(f"🎯 Trailing stop ACTIVATED for {order_id}: Profit={profit_pct:.2f}%")

                peak_data = self.position_peaks[order_id]

                # Update peak if current profit is higher
                if profit_pct > peak_data['peak_profit_pct']:
                    peak_data['peak_price'] = current_price
                    peak_data['peak_profit_pct'] = profit_pct
                    peak_data['trailing_active'] = True

                    # Calculate new trailing stop level
                    if side == 'long':
                        new_sl = current_price * (1 - self.trailing_distance_percent / 100)
                    else:  # short
                        new_sl = current_price * (1 + self.trailing_distance_percent / 100)

                    # Update stop loss on exchange
                    if not self.dry_run:
                        try:
                            self.exchange.edit_order(
                                order_id,
                                self.symbol,
                                params={'stopLoss': new_sl}
                            )
                            print(f"📈 Trailing SL updated: {order_id}")
                            print(f"   Peak: ${peak_data['peak_price']:.2f} (+{peak_data['peak_profit_pct']:.2f}%)")
                            print(f"   New SL: ${new_sl:.2f} (trailing {self.trailing_distance_percent}%)")
                        except Exception as e:
                            print(f"⚠️  Failed to update SL for {order_id}: {e}")
                    else:
                        print(f"🧪 DRY RUN: Would update SL to ${new_sl:.2f} for {order_id}")

        except Exception as e:
            print(f"⚠️  Error updating trailing stops: {e}")

    def get_market_data(self, bars=500):
        """Get historical data from Binance"""
        if not self.exchange_connected:
            return None

        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=bars)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('datetime')
            df = df[['open', 'high', 'low', 'close', 'volume']].copy()

            # Add market hours (UTC based)
            df['hour'] = df.index.hour
            df['is_active'] = df['hour'].isin(range(0, 24))  # Crypto trades 24/7
            df['is_best_hours'] = df['hour'].isin([8, 9, 10, 13, 14, 15, 16, 17])  # Active trading hours

            return df
        except Exception as e:
            print(f"❌ Failed to get market data: {e}")
            return None

    def detect_market_regime(self, df, lookback=100):
        """
        Detect market regime: TREND or RANGE

        Uses same logic as XAUUSD bot
        """
        if len(df) < lookback:
            return 'RANGE'

        recent_data = df.iloc[-lookback:]

        # 1. EMA CROSSOVER
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()

        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]

        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
        ema_trend = ema_diff_pct > 0.5  # Adjusted for crypto volatility

        # 2. ATR (volatility)
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()

        high_volatility = atr > avg_atr * 1.05

        # 3. Directional movement
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()

        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35

        # 4. Consecutive movements
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

        return 'TREND' if is_trend else 'RANGE'

    def analyze_market(self):
        """Analyze market and get signals with adaptive TP levels"""
        try:
            print(f"   📥 Fetching market data...")
            df = self.get_market_data()
            if df is None:
                print(f"   ❌ Failed to get market data")
                return None

            last_close = df['close'].iloc[-1]
            last_time = df.index[-1]
            print(f"   📊 Got {len(df)} candles, last close: ${last_close:.2f} at {last_time.strftime('%Y-%m-%d %H:%M')}")

            # Detect market regime
            print(f"   🔍 Detecting market regime...")
            self.current_regime = self.detect_market_regime(df)
            print(f"   📊 Market Regime: {self.current_regime}")

            # Run strategy
            print(f"   🧠 Running V3 Adaptive Strategy...")
            result = self.strategy.run_strategy(df)

            signals = result[result['signal'] != 0]

            if len(signals) == 0:
                print(f"   ℹ️  No signals detected")
                return None

            # Check only the most recent signal
            last_signal = signals.iloc[-1]
            last_signal_time = signals.index[-1]
            current_time = df.index[-1]

            time_diff_hours = (current_time - last_signal_time).total_seconds() / 3600

            if time_diff_hours > 1.5:
                print(f"   ⏰ Last signal is {time_diff_hours:.1f}h old (not from latest candle, skipping)")
                return None

            print(f"   ✅ Signal from latest candle (age: {time_diff_hours:.1f}h)")

            # Adjust TP based on market regime (in %)
            if self.current_regime == 'TREND':
                tp1_pct = self.trend_tp1_pct
                tp2_pct = self.trend_tp2_pct
                tp3_pct = self.trend_tp3_pct
            else:
                tp1_pct = self.range_tp1_pct
                tp2_pct = self.range_tp2_pct
                tp3_pct = self.range_tp3_pct

            # Calculate TP levels in price
            entry = last_signal['entry_price']
            sl = last_signal['stop_loss']

            if last_signal['signal'] == 1:  # LONG
                tp1 = entry * (1 + tp1_pct / 100)
                tp2 = entry * (1 + tp2_pct / 100)
                tp3 = entry * (1 + tp3_pct / 100)
            else:  # SHORT
                tp1 = entry * (1 - tp1_pct / 100)
                tp2 = entry * (1 - tp2_pct / 100)
                tp3 = entry * (1 - tp3_pct / 100)

            direction = "LONG" if last_signal['signal'] == 1 else "SHORT"
            print(f"\n   ✅ FRESH SIGNAL FROM LATEST CANDLE!")
            print(f"      Direction: {direction}")
            print(f"      Market Regime: {self.current_regime}")
            print(f"      Entry: ${entry:.2f}")
            print(f"      SL: ${sl:.2f}")
            print(f"      TP1: ${tp1:.2f} ({tp1_pct}%)")
            print(f"      TP2: ${tp2:.2f} ({tp2_pct}%)")
            print(f"      TP3: ${tp3:.2f} ({tp3_pct}%)")

            return {
                'direction': last_signal['signal'],
                'entry': entry,
                'sl': sl,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'tp1_pct': tp1_pct,
                'tp2_pct': tp2_pct,
                'tp3_pct': tp3_pct,
                'time': last_signal_time,
                'regime': self.current_regime
            }

        except Exception as e:
            print(f"   ❌ Strategy analysis error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_position_size(self, entry, sl):
        """Calculate position size based on risk"""
        if not self.exchange_connected:
            return 0.0

        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance['USDT']['free']

            risk_amount = usdt_balance * (self.risk_percent / 100.0)

            # Risk per unit
            risk_per_unit = abs(entry - sl)
            risk_pct = risk_per_unit / entry

            # Position size in base currency
            position_size = risk_amount / risk_per_unit

            # Get minimum trade size
            markets = self.exchange.load_markets()
            
            # Check if symbol exists in markets
            if self.symbol not in markets:
                print(f"⚠️ Symbol {self.symbol} not found in exchange markets")
                print(f"   Available symbols: {', '.join(list(markets.keys())[:5])}...")
                # Use default minimum for this asset type
                min_amount = 0.001 if 'BTC' in self.symbol else 0.01
            else:
                market = markets[self.symbol]
                min_amount = market['limits']['amount']['min']

            # Round to market precision
            position_size = max(min_amount, position_size)

            # Round to appropriate decimals
            if 'BTC' in self.symbol:
                position_size = round(position_size, 3)
            else:
                position_size = round(position_size, 2)

            return position_size

        except KeyError as e:
            print(f"❌ KeyError calculating position size: {e}")
            print(f"   Symbol: {self.symbol}")
            print(f"   Returning minimum fallback position size")
            return 0.001  # Minimum fallback
        except Exception as e:
            print(f"❌ Error calculating position size: {e}")
            print(f"   Error type: {type(e).__name__}")
            return 0.001  # Minimum fallback

    def get_open_positions(self):
        """Get open positions for symbol"""
        if not self.exchange_connected:
            return []

        try:
            positions = self.exchange.fetch_positions([self.symbol])
            # Filter only positions with contracts > 0
            open_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]
            return open_positions
        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            return []

    def open_position(self, signal):
        """Open position with TP/SL"""
        direction_str = "BUY" if signal['direction'] == 1 else "SELL"

        print(f"\n{'='*60}")
        print(f"📈 OPENING {direction_str} POSITION")
        print(f"{'='*60}")

        # Calculate position size
        position_size = self.calculate_position_size(signal['entry'], signal['sl'])

        print(f"   Position size: {position_size}")

        if self.dry_run:
            print(f"\n🧪 DRY RUN: Would open {direction_str} position:")
            print(f"   Symbol: {self.symbol}")
            print(f"   Amount: {position_size}")
            print(f"   Entry: ${signal['entry']:.2f}")
            print(f"   SL: ${signal['sl']:.2f}")
            print(f"   TP1: ${signal['tp1']:.2f} ({signal['tp1_pct']}%)")
            print(f"   TP2: ${signal['tp2']:.2f} ({signal['tp2_pct']}%)")
            print(f"   TP3: ${signal['tp3']:.2f} ({signal['tp3_pct']}%)")
            return True

        try:
            # Place market order
            side = 'buy' if signal['direction'] == 1 else 'sell'

            print(f"   🔄 Placing market order...")
            order = self.exchange.create_order(
                symbol=self.symbol,
                type='market',
                side=side,
                amount=position_size,
                params={
                    'stopLoss': {'triggerPrice': signal['sl']},
                    'takeProfit': {'triggerPrice': signal['tp2']}  # Using TP2 as main target
                }
            )

            print(f"   ✅ Order placed!")
            print(f"      Order ID: {order['id']}")
            print(f"      Status: {order.get('status', 'unknown')}")
            print(f"      Side: {order.get('side', 'unknown')}")
            print(f"      Amount: {order.get('amount', position_size)}")
            print(f"      Filled: {order.get('filled', 0)}")
            print(f"      Entry: ${order.get('average', signal['entry']):.2f}")

            # Verify position was created
            print(f"\n   🔍 Verifying position...")
            import time
            time.sleep(1)  # Wait for position to register
            positions = self.get_open_positions()
            print(f"   📊 Open positions after order: {len(positions)}")
            if positions:
                for pos in positions:
                    print(f"      Position: {pos.get('side')} {pos.get('contracts')} @ ${pos.get('entryPrice', 0):.2f}")

            # Log position
            position_type = 'BUY' if signal['direction'] == 1 else 'SELL'
            regime = signal.get('regime', 'UNKNOWN')
            regime_code = "T" if regime == 'TREND' else "R"

            self._log_position_opened(
                order_id=order['id'],
                position_type=position_type,
                amount=position_size,
                entry_price=order.get('average', signal['entry']),
                sl=signal['sl'],
                tp=signal['tp2'],
                regime=regime,
                comment=f"V3_{regime_code}"
            )

            # Send Telegram notification
            if self.telegram_bot:
                message = f"🤖 <b>Position Opened</b>\n\n"
                message += f"Symbol: {self.symbol}\n"
                message += f"Direction: {direction_str}\n"
                message += f"Regime: {regime}\n"
                message += f"Amount: {position_size}\n"
                message += f"Entry: ${order.get('average', signal['entry']):.2f}\n"
                message += f"SL: ${signal['sl']:.2f}\n"
                message += f"TP: ${signal['tp2']:.2f}\n"
                message += f"Risk: {self.risk_percent}%"
                asyncio.run(self.send_telegram(message))

            return True

        except Exception as e:
            print(f"❌ Failed to open position: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def send_telegram(self, message):
        """Send Telegram notification"""
        if self.telegram_bot and self.telegram_chat_id:
            try:
                await self.telegram_bot.send_message(
                    chat_id=self.telegram_chat_id,
                    text=message,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"⚠️  Telegram send failed: {e}")

    def _check_closed_positions(self):
        """Check for positions that have been closed and log them"""
        if not self.exchange_connected:
            return

        # Get currently open position order IDs
        open_positions = self.get_open_positions()
        current_order_ids = set()
        if open_positions:
            current_order_ids = {str(pos.get('id', '')) for pos in open_positions}

        # Find positions that were tracked but are now closed
        tracked_order_ids = set(self.positions_tracker.keys())
        closed_order_ids = tracked_order_ids - current_order_ids

        # Log closed positions
        for order_id in closed_order_ids:
            try:
                # Fetch order details
                order = self.exchange.fetch_order(order_id, self.symbol)

                if order['status'] == 'closed':
                    self._log_position_closed(
                        order_id=order_id,
                        close_price=order.get('average', 0),
                        profit=order.get('info', {}).get('realizedPnl', 0),
                        status='CLOSED'
                    )
            except Exception as e:
                print(f"⚠️  Error checking closed position {order_id}: {e}")

    def _wait_until_next_hour(self):
        """Wait until the next full hour while monitoring positions"""
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_hour - now).total_seconds()

        if wait_seconds > 0:
            print(f"\n⏰ Waiting until next hour: {next_hour.strftime('%H:%M:%S')}")
            print(f"   Time now: {now.strftime('%H:%M:%S')}")
            print(f"   Wait time: {int(wait_seconds/60)} min {int(wait_seconds%60)} sec")

            monitoring_interval = 30  # Check every 30 seconds
            elapsed = 0

            while elapsed < wait_seconds:
                sleep_time = min(monitoring_interval, wait_seconds - elapsed)
                time.sleep(sleep_time)
                elapsed += sleep_time

                # Check for closed positions
                self._check_closed_positions()

    def run(self):
        """Main bot loop"""
        print(f"\n{'='*80}")
        print(f"🤖 CRYPTO BOT STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"📊 Configuration:")
        print(f"   Symbol: {self.symbol}")
        print(f"   Timeframe: {self.timeframe}")
        print(f"   Strategy: V3 Adaptive (TREND/RANGE detection)")
        print(f"   Check interval: Every hour")
        print(f"   Risk per trade: {self.risk_percent}%")
        print(f"   Max positions: {self.max_positions}")
        print(f"   Mode: {'🧪 DRY RUN (TEST)' if self.dry_run else '🚀 LIVE TRADING'}")
        print(f"   Exchange: {'TESTNET' if self.testnet else 'PRODUCTION'}")
        print(f"\n🎯 Adaptive TP Levels:")
        print(f"   TREND Mode: {self.trend_tp1_pct}% / {self.trend_tp2_pct}% / {self.trend_tp3_pct}%")
        print(f"   RANGE Mode: {self.range_tp1_pct}% / {self.range_tp2_pct}% / {self.range_tp3_pct}%")
        print(f"{'='*80}\n")

        # Wait until next hour before starting
        print("⏰ Bot will start checking at the next full hour...")
        self._wait_until_next_hour()

        iteration = 0

        try:
            while True:
                iteration += 1

                print(f"\n{'='*80}")
                print(f"🔄 Iteration #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*80}")

                # Check connection
                if not self.exchange_connected:
                    print("❌ Exchange disconnected! Attempting to reconnect...")
                    if not self.connect_exchange():
                        print("❌ Reconnection failed. Waiting 60s...")
                        time.sleep(60)
                        continue

                # Check current positions
                open_positions = self.get_open_positions()
                print(f"📊 Open positions: {len(open_positions)}/{self.max_positions}")

                if len(open_positions) > 0:
                    for i, pos in enumerate(open_positions, 1):
                        side = pos.get('side', 'unknown')
                        contracts = pos.get('contracts', 0)
                        entry_price = pos.get('entryPrice', 0)
                        unrealized_pnl = pos.get('unrealizedPnl', 0)
                        print(f"   Position #{i}: {side.upper()} {contracts}, "
                              f"Entry={entry_price:.2f}, "
                              f"PnL: {unrealized_pnl:.2f} USDT")

                # Check for closed positions
                self._check_closed_positions()

                # Update trailing stops for open positions
                if len(open_positions) > 0:
                    self.update_trailing_stops()

                # Analyze market
                print(f"\n🔍 Analyzing market...")
                signal = self.analyze_market()

                if signal:
                    print(f"\n✅ Signal detected!")

                    # Check if already have position in same direction
                    has_same_direction = False
                    for pos in open_positions:
                        pos_side = pos.get('side', '')
                        if (pos_side == 'long' and signal['direction'] == 1) or \
                           (pos_side == 'short' and signal['direction'] == -1):
                            has_same_direction = True
                            break

                    if has_same_direction:
                        direction_str = 'LONG' if signal['direction'] == 1 else 'SHORT'
                        print(f"⚠️  Already have {direction_str} position - skipping")
                    elif len(open_positions) >= self.max_positions:
                        print(f"⚠️  Max positions reached ({self.max_positions}) - skipping")
                    else:
                        # Open position
                        print(f"📈 Attempting to open position...")
                        success = self.open_position(signal)
                        if success:
                            print(f"✅ Position opened successfully!")
                        else:
                            print(f"❌ Failed to open position")
                else:
                    print("   ℹ️  No signals at this time")

                # Account status
                try:
                    balance = self.exchange.fetch_balance()
                    print(f"\n💰 Account status:")
                    print(f"   USDT Balance: {balance['USDT']['free']:.2f}")
                    print(f"   USDT Used: {balance['USDT']['used']:.2f}")
                    print(f"   USDT Total: {balance['USDT']['total']:.2f}")
                except Exception as e:
                    print(f"⚠️  Could not fetch balance: {e}")

                # Wait until next hour
                print(f"\n{'='*80}")
                print(f"💤 Waiting until next full hour...")
                print(f"   Press Ctrl+C to stop the bot")
                print(f"{'='*80}\n")

                self._wait_until_next_hour()

        except KeyboardInterrupt:
            print(f"\n\n{'='*80}")
            print("⚠️  BOT STOPPED BY USER")
            print(f"{'='*80}")
            print(f"Total iterations: {iteration}")
            print(f"Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Show final positions
            open_positions = self.get_open_positions()
            if len(open_positions) > 0:
                print(f"\n⚠️  WARNING: {len(open_positions)} position(s) still open!")
                print("   Remember to close them manually if needed.")
            else:
                print("\n✅ No open positions")

            print(f"{'='*80}\n")

        except Exception as e:
            print(f"\n\n❌ BOT ERROR: {e}")
            import traceback
            traceback.print_exc()

        finally:
            print("🔌 Disconnecting from Binance...")
            self.disconnect_exchange()
            print("✅ Shutdown complete")


if __name__ == "__main__":
    # Example usage - edit .env file for your configuration
    from dotenv import load_dotenv
    load_dotenv()

    bot = LiveBotBinanceFullAuto(
        symbol=os.getenv('SYMBOL', 'BTC/USDT'),
        timeframe=os.getenv('TIMEFRAME', '1h'),
        risk_percent=float(os.getenv('RISK_PERCENT', '2.0')),
        max_positions=int(os.getenv('MAX_POSITIONS', '3')),
        dry_run=os.getenv('DRY_RUN', 'True').lower() == 'true',
        testnet=os.getenv('TESTNET', 'True').lower() == 'true',
        api_key=os.getenv('BINANCE_API_KEY'),
        api_secret=os.getenv('BINANCE_API_SECRET'),
        telegram_token=os.getenv('TELEGRAM_TOKEN'),
        telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID')
    )

    # Connect and run
    if bot.connect_exchange():
        bot.run()
    else:
        print("❌ Failed to connect to exchange. Exiting...")
