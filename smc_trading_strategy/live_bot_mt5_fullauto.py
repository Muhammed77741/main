"""
Full-Auto Live Trading Bot for MT5
Uses V3 Adaptive Strategy with TREND/RANGE detection

⚠️ DANGEROUS: Trades automatically without confirmation!
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pattern_recognition_strategy import PatternRecognitionStrategy


class LiveBotMT5FullAuto:
    """
    Full-automatic trading bot for MT5
    
    Features:
    - Uses V3 Adaptive Strategy with TREND/RANGE detection
    - Automatic position opening/closing
    - Adapts TP levels based on market regime
    - Risk management
    - Optional Telegram notifications
    - DRY RUN mode for testing
    """
    
    def __init__(self, telegram_token=None, telegram_chat_id=None,
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1,
                 check_interval=3600, risk_percent=2.0, max_positions=3,
                 dry_run=False):
        """
        Initialize bot
        
        Args:
            telegram_token: Telegram bot token (optional)
            telegram_chat_id: Telegram chat ID (optional)
            symbol: Trading symbol
            timeframe: MT5 timeframe
            check_interval: Check interval in seconds
            risk_percent: Risk per trade (%)
            max_positions: Max simultaneous positions
            dry_run: If True, no real trades
        """
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.check_interval = check_interval
        self.risk_percent = risk_percent
        self.max_positions = max_positions
        self.dry_run = dry_run
        
        # Initialize strategy
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')
        
        # TREND MODE parameters (strong trend)
        self.trend_tp1 = 30
        self.trend_tp2 = 55
        self.trend_tp3 = 90
        
        # RANGE MODE parameters (sideways)
        self.range_tp1 = 20
        self.range_tp2 = 35
        self.range_tp3 = 50
        
        # Current market regime
        self.current_regime = 'RANGE'
        
        # Telegram bot (optional)
        self.telegram_bot = None
        if telegram_token and telegram_chat_id:
            try:
                from telegram import Bot
                self.telegram_bot = Bot(token=telegram_token)
            except Exception as e:
                print(f"⚠️  Telegram init failed: {e}")
        
        self.mt5_connected = False
        
    def connect_mt5(self):
        """Connect to MT5"""
        if not mt5.initialize():
            print("❌ Failed to initialize MT5")
            return False
            
        account_info = mt5.account_info()
        if account_info is None:
            print("❌ Failed to get account info")
            mt5.shutdown()
            return False
            
        self.mt5_connected = True
        print(f"✅ Connected to MT5: {account_info.server} - Account {account_info.login}")
        return True
        
    def disconnect_mt5(self):
        """Disconnect from MT5"""
        if self.mt5_connected:
            mt5.shutdown()
            self.mt5_connected = False
            
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
                
    def get_market_data(self, bars=500):
        """Get historical data from MT5"""
        if not self.mt5_connected:
            return None
            
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, bars)
        
        if rates is None or len(rates) == 0:
            print(f"❌ Failed to get data for {self.symbol}")
            return None
            
        df = pd.DataFrame(rates)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('datetime')
        df = df[['open', 'high', 'low', 'close', 'tick_volume']].copy()
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        
        # Add market hours
        df['is_london'] = df.index.hour.isin(range(7, 12))
        df['is_ny'] = df.index.hour.isin(range(13, 20))
        df['is_overlap'] = df.index.hour.isin(range(13, 16))
        df['is_active'] = df['is_london'] | df['is_ny']
        df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])
        
        return df
        
    def detect_market_regime(self, df, lookback=100):
        """
        Detect market regime: TREND or RANGE
        
        Uses:
        1. EMA crossover (trend determined by crossing)
        2. ATR (volatility)
        3. Directional movement
        4. Consecutive candles in one direction
        """
        if len(df) < lookback:
            return 'RANGE'  # Default to range
        
        # Get recent data
        recent_data = df.iloc[-lookback:]
        
        # 1. EMA CROSSOVER (main trend indicator)
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()
        
        # Current EMA position
        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]
        
        # Difference between EMAs in %
        ema_diff_pct = abs((current_fast - current_slow) / current_slow) * 100
        
        # If EMAs diverge > 0.3% = clear trend
        ema_trend = ema_diff_pct > 0.3
        
        # 2. ATR (volatility - should be above average)
        high_low = recent_data['high'] - recent_data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        avg_atr = high_low.rolling(window=14).mean().mean()
        
        high_volatility = atr > avg_atr * 1.05
        
        # 3. Directional movement (price moves in one direction)
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_range = recent_data['high'].max() - recent_data['low'].min()
        
        directional_move_pct = abs(price_change) / price_range if price_range > 0 else 0
        strong_direction = directional_move_pct > 0.35
        
        # 4. Consecutive movements (candles in one direction)
        closes_arr = recent_data['close'].values
        up_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] > closes_arr[i-1])
        down_moves = sum(1 for i in range(1, len(closes_arr)) if closes_arr[i] < closes_arr[i-1])
        total_moves = up_moves + down_moves
        
        trend_strength = abs(up_moves - down_moves) / total_moves if total_moves > 0 else 0
        directional_bias = trend_strength > 0.15
        
        # 5. Consecutive higher highs / lower lows
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
    
    def analyze_market(self):
        """Analyze market and get signals with adaptive TP levels"""
        try:
            # Get data
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
            
            # Get last signal (most recent)
            signals = result[result['signal'] != 0]
            
            if len(signals) == 0:
                print(f"   ℹ️  No signals detected")
                return None
                
            # Check if last signal is recent (within last 5 candles)
            last_signal = signals.iloc[-1]
            last_signal_time = signals.index[-1]
            current_time = df.index[-1]
            
            time_diff = (current_time - last_signal_time).total_seconds() / 3600
            
            if time_diff > 5:  # More than 5 hours old
                print(f"   ⏰ Last signal is {time_diff:.1f}h old (too old, need <5h)")
                return None
            
            # Adjust TP based on market regime
            if self.current_regime == 'TREND':
                tp1_distance = self.trend_tp1
                tp2_distance = self.trend_tp2
                tp3_distance = self.trend_tp3
            else:
                tp1_distance = self.range_tp1
                tp2_distance = self.range_tp2
                tp3_distance = self.range_tp3
                
            # Calculate adaptive TP (use TP2 as main target)
            entry = last_signal['entry_price']
            sl = last_signal['stop_loss']
            
            if last_signal['signal'] == 1:  # LONG
                tp = entry + tp2_distance
            else:  # SHORT
                tp = entry - tp2_distance
                
            direction = "LONG" if last_signal['signal'] == 1 else "SHORT"
            print(f"\n   ✅ FRESH SIGNAL DETECTED!")
            print(f"      Direction: {direction}")
            print(f"      Market Regime: {self.current_regime}")
            print(f"      Signal time: {last_signal_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"      Age: {time_diff:.1f}h ago")
            print(f"      Entry: ${entry:.2f}")
            print(f"      SL: ${sl:.2f}")
            print(f"      TP (adaptive): ${tp:.2f} ({tp2_distance}p for {self.current_regime})")
            print(f"      Available TPs: {tp1_distance}p / {tp2_distance}p / {tp3_distance}p")
            
            # Calculate risk/reward
            if last_signal['signal'] == 1:
                risk = entry - sl
                reward = tp - entry
            else:
                risk = sl - entry
                reward = entry - tp
                
            rr = reward / risk if risk > 0 else 0
            print(f"      Risk: {risk:.2f} points")
            print(f"      Reward: {reward:.2f} points")
            print(f"      Risk:Reward = 1:{rr:.2f}")
            
            return {
                'direction': last_signal['signal'],
                'entry': entry,
                'sl': sl,
                'tp': tp,
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
        if not self.mt5_connected:
            return 0.0
            
        account_info = mt5.account_info()
        if account_info is None:
            return 0.0
            
        balance = account_info.balance
        risk_amount = balance * (self.risk_percent / 100.0)
        
        # Risk per lot (in account currency)
        risk_per_point = abs(entry - sl)
        
        # For XAUUSD, 1 lot = 100 oz, point value depends on broker
        # Typical: 1 point = $100 for 1 lot
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            return 0.01  # Fallback
            
        # Calculate lot size
        point_value = 100.0  # Approx for gold
        lot_size = risk_amount / (risk_per_point * point_value)
        
        # Round to 0.01
        lot_size = round(lot_size, 2)
        
        # Min/max lot size
        lot_size = max(symbol_info.volume_min, lot_size)
        lot_size = min(symbol_info.volume_max, lot_size)
        
        return lot_size
        
    def get_open_positions(self):
        """Get open positions for symbol"""
        if not self.mt5_connected:
            return []
            
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return []
            
        return list(positions)
        
    def open_position(self, signal):
        """Open a position"""
        direction_str = "BUY" if signal['direction'] == 1 else "SELL"
        
        print(f"\n{'='*60}")
        print(f"📈 OPENING {direction_str} POSITION")
        print(f"{'='*60}")
        
        # Check max positions
        open_positions = self.get_open_positions()
        if len(open_positions) >= self.max_positions:
            print(f"⚠️  Max positions reached ({self.max_positions})")
            return False
            
        # Calculate lot size
        lot_size = self.calculate_position_size(signal['entry'], signal['sl'])
        print(f"   Lot size: {lot_size}")
        
        if self.dry_run:
            print(f"\n🧪 DRY RUN: Would open {direction_str} position:")
            print(f"   Entry: {signal['entry']:.2f}")
            print(f"   SL: {signal['sl']:.2f}")
            print(f"   TP: {signal['tp']:.2f}")
            print(f"   Lot: {lot_size}")
            print(f"   Risk: {self.risk_percent}%")
            return True
            
        # Prepare request
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Symbol info not found")
            return False
            
        point = symbol_info.point
        
        # Get current price
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"❌ Failed to get current price")
            return False
            
        price = tick.ask if signal['direction'] == 1 else tick.bid
        
        # Create request
        regime_code = "T" if signal.get('regime') == 'TREND' else "R"
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY if signal['direction'] == 1 else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": signal['sl'],
            "tp": signal['tp'],
            "deviation": 20,
            "magic": 234000,
            "comment": f"V3_Adaptive_{regime_code}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result is None:
            print(f"❌ Order failed: No result")
            return False
            
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Order failed: {result.retcode}")
            print(f"   Comment: {result.comment}")
            return False
            
        print(f"\n✅ Position opened successfully!")
        print(f"   Order: #{result.order}")
        print(f"   Price: {result.price:.2f}")
        
        # Send Telegram notification
        if self.telegram_bot:
            import asyncio
            regime = signal.get('regime', 'UNKNOWN')
            message = f"🤖 <b>Position Opened</b>\n\n"
            message += f"Direction: {direction_str}\n"
            message += f"Market Regime: {regime}\n"
            message += f"Entry: {result.price:.2f}\n"
            message += f"SL: {signal['sl']:.2f}\n"
            message += f"TP: {signal['tp']:.2f}\n"
            message += f"Lot: {lot_size}\n"
            message += f"Risk: {self.risk_percent}%"
            asyncio.run(self.send_telegram(message))
            
        return True
        
    def run(self):
        """Main bot loop"""
        print(f"\n{'='*80}")
        print(f"🤖 BOT STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"📊 Configuration:")
        print(f"   Symbol: {self.symbol}")
        print(f"   Timeframe: H1")
        print(f"   Strategy: V3 Adaptive (TREND/RANGE detection)")
        print(f"   Check interval: {self.check_interval/60:.0f} minutes")
        print(f"   Risk per trade: {self.risk_percent}%")
        print(f"   Max positions: {self.max_positions}")
        print(f"   Mode: {'🧪 DRY RUN (TEST)' if self.dry_run else '🚀 LIVE TRADING'}")
        print(f"\n🎯 Adaptive TP Levels:")
        print(f"   TREND Mode: {self.trend_tp1}p / {self.trend_tp2}p / {self.trend_tp3}p")
        print(f"   RANGE Mode: {self.range_tp1}p / {self.range_tp2}p / {self.range_tp3}p")
        print(f"{'='*80}\n")
        
        if self.dry_run:
            print("🧪 DRY RUN MODE: All trades will be simulated only")
            print("   ✅ Analysis will run normally")
            print("   ✅ Signals will be detected")
            print("   ✅ Position sizing will be calculated")
            print("   ⚠️  NO real trades will be executed\n")
        else:
            print("🚀 LIVE TRADING MODE: Real trades will be executed!")
            print("   ⚠️  Monitor your account regularly")
            print("   ⚠️  Stop the bot with Ctrl+C\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                print(f"\n{'='*80}")
                print(f"🔄 Iteration #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*80}")
                
                # Check connection
                if not self.mt5_connected:
                    print("❌ MT5 disconnected! Attempting to reconnect...")
                    if not self.connect_mt5():
                        print("❌ Reconnection failed. Waiting 60s...")
                        time.sleep(60)
                        continue
                
                # Check current positions
                open_positions = self.get_open_positions()
                print(f"📊 Open positions: {len(open_positions)}/{self.max_positions}")
                
                if len(open_positions) > 0:
                    for i, pos in enumerate(open_positions, 1):
                        direction = "LONG" if pos.type == mt5.ORDER_TYPE_BUY else "SHORT"
                        profit = pos.profit
                        print(f"   Position #{i}: {direction} @ {pos.price_open:.2f}, "
                              f"SL={pos.sl:.2f}, TP={pos.tp:.2f}, "
                              f"P&L: ${profit:.2f}")
                
                # Analyze market
                print(f"\n🔍 Analyzing market...")
                signal = self.analyze_market()
                
                if signal:
                    print(f"\n✅ Signal detected!")
                    
                    # Check if already have position in same direction
                    has_same_direction = False
                    for pos in open_positions:
                        pos_direction = 1 if pos.type == mt5.ORDER_TYPE_BUY else -1
                        if pos_direction == signal['direction']:
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
                account_info = mt5.account_info()
                if account_info:
                    print(f"\n💰 Account status:")
                    print(f"   Balance: ${account_info.balance:.2f}")
                    print(f"   Equity: ${account_info.equity:.2f}")
                    print(f"   Margin: ${account_info.margin:.2f}")
                    profit_pct = ((account_info.equity - account_info.balance) / account_info.balance * 100) if account_info.balance > 0 else 0
                    print(f"   Floating P&L: ${account_info.equity - account_info.balance:.2f} ({profit_pct:+.2f}%)")
                    
                # Wait before next check
                next_check = datetime.now() + timedelta(seconds=self.check_interval)
                print(f"\n{'='*80}")
                print(f"💤 Sleeping for {self.check_interval/60:.0f} minutes")
                print(f"   Next check at: {next_check.strftime('%H:%M:%S')}")
                print(f"   Press Ctrl+C to stop the bot")
                print(f"{'='*80}\n")
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\n{'='*80}")
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
            print("🔌 Disconnecting from MT5...")
            self.disconnect_mt5()
            print("✅ Shutdown complete")
