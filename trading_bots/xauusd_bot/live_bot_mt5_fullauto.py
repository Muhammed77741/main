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
import csv
import os
import asyncio

# Add parent directory to path to access shared modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.pattern_recognition_strategy import PatternRecognitionStrategy
from shared.telegram_helper import check_telegram_bot_import


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
                 check_interval=3600, risk_percent=2.0, max_positions=9,
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
        
        # Position tracking
        self.trades_file = 'bot_trades_log.csv'
        self.tp_hits_file = 'bot_tp_hits_log.csv'
        self.positions_tracker = {}  # {ticket: position_data}
        self._initialize_trades_log()
        self._initialize_tp_hits_log()
        
        # Telegram bot (optional)
        self.telegram_bot = None
        if telegram_token and telegram_chat_id:
            try:
                success, Bot, error_msg = check_telegram_bot_import()
                if not success:
                    print(error_msg)
                else:
                    try:
                        self.telegram_bot = Bot(token=telegram_token)
                    except Exception as bot_error:
                        print(f"⚠️  Failed to initialize Telegram bot: {bot_error}")
                        print("     Check your bot token is valid.")
            except Exception as e:
                print(f"⚠️  Unexpected error during Telegram initialization: {e}")
        
        self.mt5_connected = False
    
    def _initialize_trades_log(self):
        """Initialize CSV file for trade logging"""
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Ticket', 'Open_Time', 'Close_Time', 'Type', 'Volume',
                    'Entry_Price', 'SL', 'TP', 'Close_Price', 'Profit',
                    'Pips', 'Market_Regime', 'Duration_Hours', 'Status', 'Comment'
                ])
            print(f"📝 Created trade log file: {self.trades_file}")
    
    def _initialize_tp_hits_log(self):
        """Initialize CSV file for TP hits logging"""
        if not os.path.exists(self.tp_hits_file):
            with open(self.tp_hits_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Ticket', 'TP_Level', 'Type', 'Volume',
                    'Entry_Price', 'TP_Target', 'Current_Price', 'SL',
                    'Profit', 'Pips', 'Market_Regime', 'Duration_Minutes', 'Comment'
                ])
            print(f"📝 Created TP hits log file: {self.tp_hits_file}")
    
    def _log_position_opened(self, ticket, position_type, volume, entry_price, 
                             sl, tp, regime, comment=''):
        """Log when position is opened"""
        self.positions_tracker[ticket] = {
            'ticket': ticket,
            'open_time': datetime.now(),
            'close_time': None,
            'type': position_type,
            'volume': volume,
            'entry_price': entry_price,
            'sl': sl,
            'tp': tp,
            'close_price': None,
            'profit': None,
            'pips': None,
            'regime': regime,
            'duration': None,
            'status': 'OPEN',
            'comment': comment
        }
        print(f"📊 Logged opened position: Ticket={ticket}, Type={position_type}, Entry={entry_price}")
    
    def _log_position_closed(self, ticket, close_price, profit, status='CLOSED'):
        """Log when position is closed"""
        if ticket not in self.positions_tracker:
            print(f"⚠️  Ticket {ticket} not found in tracker")
            return
        
        pos = self.positions_tracker[ticket]
        pos['close_time'] = datetime.now()
        pos['close_price'] = close_price
        pos['profit'] = profit
        pos['status'] = status
        
        # Calculate duration
        if pos['open_time']:
            duration = (pos['close_time'] - pos['open_time']).total_seconds() / 3600
            pos['duration'] = round(duration, 2)
        
        # Calculate pips
        if pos['type'] == 'BUY':
            pips = (close_price - pos['entry_price']) * 10  # For XAUUSD
        else:
            pips = (pos['entry_price'] - close_price) * 10
        pos['pips'] = round(pips, 1)
        
        # Write to CSV
        self._write_trade_to_csv(pos)
        
        # Remove from tracker
        del self.positions_tracker[ticket]
        
        print(f"📊 Logged closed position: Ticket={ticket}, Profit={profit:.2f}, Pips={pips:.1f}, Duration={pos['duration']}h")
    
    def _write_trade_to_csv(self, trade_data):
        """Write completed trade to CSV file"""
        with open(self.trades_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trade_data['ticket'],
                trade_data['open_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_data['open_time'] else '',
                trade_data['close_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_data['close_time'] else '',
                trade_data['type'],
                trade_data['volume'],
                trade_data['entry_price'],
                trade_data['sl'],
                trade_data['tp'],
                trade_data['close_price'],
                trade_data['profit'],
                trade_data['pips'],
                trade_data['regime'],
                trade_data['duration'],
                trade_data['status'],
                trade_data['comment']
            ])
    
    def _log_tp_hit(self, ticket, tp_level, current_price):
        """Log when a TP level is hit"""
        if ticket not in self.positions_tracker:
            return
        
        pos = self.positions_tracker[ticket]
        
        # Calculate duration in minutes
        duration_minutes = 0
        if pos['open_time']:
            duration_minutes = (datetime.now() - pos['open_time']).total_seconds() / 60
        
        # Calculate pips
        if pos['type'] == 'BUY':
            pips = (current_price - pos['entry_price']) * 10  # For XAUUSD
        else:
            pips = (pos['entry_price'] - current_price) * 10
        
        # Estimate profit (approximation based on pips)
        point_value = 100.0  # For XAUUSD, 1 lot = $100 per point
        profit = pips / 10 * pos['volume'] * point_value
        
        # Write to TP hits log
        with open(self.tp_hits_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ticket,
                tp_level,
                pos['type'],
                pos['volume'],
                pos['entry_price'],
                pos['tp'],
                current_price,
                pos['sl'],
                round(profit, 2),
                round(pips, 1),
                pos['regime'],
                round(duration_minutes, 1),
                pos['comment']
            ])
        
        print(f"🎯 TP HIT LOGGED: Ticket={ticket}, Level={tp_level}, Price={current_price:.2f}, Pips={pips:.1f}")
    
    def _check_tp_levels_realtime(self):
        """Monitor open positions in real-time and check if TP levels are hit"""
        if not self.mt5_connected:
            return
        
        # Get current open positions from MT5
        open_positions = mt5.positions_get(symbol=self.symbol)
        if not open_positions:
            return
        
        for position in open_positions:
            ticket = position.ticket
            
            # Skip if not in our tracker (might be manual position)
            if ticket not in self.positions_tracker:
                continue
            
            tracked_pos = self.positions_tracker[ticket]
            
            # Get current price
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                continue
            
            # Use appropriate price based on position type
            # For BUY: close at bid (sell price), For SELL: close at ask (buy price)
            current_price = tick.bid if tracked_pos['type'] == 'BUY' else tick.ask
            tp_target = tracked_pos['tp']
            
            # Determine which TP level this is from the comment
            tp_level = 'UNKNOWN'
            if 'TP1' in tracked_pos['comment']:
                tp_level = 'TP1'
            elif 'TP2' in tracked_pos['comment']:
                tp_level = 'TP2'
            elif 'TP3' in tracked_pos['comment']:
                tp_level = 'TP3'
            
            # Check if TP is hit (with small tolerance for slippage)
            tolerance = 0.5  # 0.5 point tolerance
            tp_hit = False
            
            if tracked_pos['type'] == 'BUY':
                # For BUY, TP is above entry
                tp_hit = current_price >= (tp_target - tolerance)
            else:
                # For SELL, TP is below entry
                tp_hit = current_price <= (tp_target + tolerance)
            
            # If TP is hit and we haven't logged it yet
            if tp_hit and tracked_pos.get('status') == 'OPEN':
                # Mark as TP hit in tracker
                tracked_pos['status'] = 'TP_HIT_DETECTED'
                tracked_pos['tp_hit_time'] = datetime.now()
                
                # Log the TP hit
                self._log_tp_hit(ticket, tp_level, current_price)
                
                # Send Telegram notification if available
                if self.telegram_bot:
                    message = f"🎯 <b>TP HIT!</b>\n\n"
                    message += f"Ticket: #{ticket}\n"
                    message += f"TP Level: {tp_level}\n"
                    message += f"Type: {tracked_pos['type']}\n"
                    message += f"Entry: ${tracked_pos['entry_price']:.2f}\n"
                    message += f"TP Target: ${tp_target:.2f}\n"
                    message += f"Current Price: ${current_price:.2f}\n"
                    message += f"Volume: {tracked_pos['volume']} lot\n"
                    
                    # Calculate pips
                    if tracked_pos['type'] == 'BUY':
                        pips = (current_price - tracked_pos['entry_price']) * 10
                    else:
                        pips = (tracked_pos['entry_price'] - current_price) * 10
                    message += f"Pips: {pips:.1f}\n"
                    
                    try:
                        asyncio.run(self.send_telegram(message))
                    except Exception as e:
                        print(f"⚠️  Failed to send Telegram notification: {e}")
        
    def connect_mt5(self):
        """Connect to MT5"""
        if not mt5.initialize():
            error_msg = "❌ Failed to initialize MT5"
            print(error_msg)
            
            # Send to Telegram
            if self.telegram_bot:
                try:
                    asyncio.run(self.send_telegram(f"❌ <b>MT5 Connection Error</b>\n\n{error_msg}\n\nPlease ensure:\n1. MetaTrader 5 is installed and running\n2. 'Algo Trading' is enabled\n3. You're logged into an account"))
                except Exception as e:
                    print(f"⚠️  Failed to send Telegram notification: {e}")
            
            return False
            
        account_info = mt5.account_info()
        if account_info is None:
            error_msg = "❌ Failed to get account info"
            print(error_msg)
            mt5.shutdown()
            
            # Send to Telegram
            if self.telegram_bot:
                try:
                    asyncio.run(self.send_telegram(f"❌ <b>MT5 Connection Error</b>\n\n{error_msg}\n\nPlease ensure you're logged into an MT5 account"))
                except Exception as e:
                    print(f"⚠️  Failed to send Telegram notification: {e}")
            
            return False
            
        self.mt5_connected = True
        success_msg = f"✅ Connected to MT5: {account_info.server} - Account {account_info.login}"
        print(success_msg)
        
        # Send success notification to Telegram
        if self.telegram_bot:
            try:
                asyncio.run(self.send_telegram(f"✅ <b>Connected to MT5</b>\n\nServer: {account_info.server}\nAccount: {account_info.login}\nBalance: ${account_info.balance:.2f}"))
            except Exception as e:
                print(f"⚠️  Failed to send Telegram notification: {e}")
        
        return True
        
    def disconnect_mt5(self):
        """Disconnect from MT5"""
        if self.mt5_connected:
            mt5.shutdown()
            self.mt5_connected = False
    
    def _check_closed_positions(self):
        """Check for positions that have been closed and log them"""
        if not self.mt5_connected:
            return
        
        # Get currently open position tickets
        open_positions = mt5.positions_get(symbol=self.symbol)
        current_tickets = set()
        if open_positions:
            current_tickets = {pos.ticket for pos in open_positions}
        
        # Find positions that were tracked but are now closed
        tracked_tickets = set(self.positions_tracker.keys())
        closed_tickets = tracked_tickets - current_tickets
        
        # Log closed positions
        for ticket in closed_tickets:
            # Try to get deal history for this ticket
            from_date = datetime.now() - timedelta(days=7)
            deals = mt5.history_deals_get(from_date, datetime.now())
            
            if deals:
                for deal in deals:
                    if deal.order == ticket and deal.entry == mt5.DEAL_ENTRY_OUT:
                        # Found the closing deal
                        self._log_position_closed(
                            ticket=ticket,
                            close_price=deal.price,
                            profit=deal.profit,
                            status='TP' if deal.comment and 'tp' in deal.comment.lower() else 
                                   'SL' if deal.comment and 'sl' in deal.comment.lower() else 
                                   'CLOSED'
                        )
                        break
            else:
                # If we can't find deal history, mark as closed with unknown status
                pos_data = self.positions_tracker.get(ticket)
                if pos_data:
                    self._log_position_closed(
                        ticket=ticket,
                        close_price=pos_data['entry_price'],
                        profit=0,
                        status='UNKNOWN'
                    )
            
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
                
            # ONLY CHECK THE MOST RECENT CLOSED CANDLE (not historical signals)
            # This ensures we only trade on fresh signals, not old ones
            last_signal = signals.iloc[-1]
            last_signal_time = signals.index[-1]
            current_time = df.index[-1]
            
            # Signal must be from the LAST COMPLETED CANDLE ONLY
            # If signal is older than 1.5 hours, it's from a previous candle - ignore it
            time_diff_hours = (current_time - last_signal_time).total_seconds() / 3600
            
            if time_diff_hours > 1.5:  # More than 1.5 hours old = not from last closed candle
                print(f"   ⏰ Last signal is {time_diff_hours:.1f}h old (not from latest candle, skipping)")
                return None
                
            print(f"   ✅ Signal from latest candle (age: {time_diff_hours:.1f}h)")
            
            # Adjust TP based on market regime
            if self.current_regime == 'TREND':
                tp1_distance = self.trend_tp1
                tp2_distance = self.trend_tp2
                tp3_distance = self.trend_tp3
            else:
                tp1_distance = self.range_tp1
                tp2_distance = self.range_tp2
                tp3_distance = self.range_tp3
                
            # Calculate all 3 TP levels
            entry = last_signal['entry_price']
            sl = last_signal['stop_loss']
            
            if last_signal['signal'] == 1:  # LONG
                tp1 = entry + tp1_distance
                tp2 = entry + tp2_distance
                tp3 = entry + tp3_distance
            else:  # SHORT
                tp1 = entry - tp1_distance
                tp2 = entry - tp2_distance
                tp3 = entry - tp3_distance
                
            direction = "LONG" if last_signal['signal'] == 1 else "SHORT"
            print(f"\n   ✅ FRESH SIGNAL FROM LATEST CANDLE!")
            print(f"      Direction: {direction}")
            print(f"      Market Regime: {self.current_regime}")
            print(f"      Signal time: {last_signal_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"      Age: {time_diff_hours:.1f}h ago")
            print(f"      Entry: ${entry:.2f}")
            print(f"      SL: ${sl:.2f}")
            print(f"      TP1: ${tp1:.2f} ({tp1_distance}p)")
            print(f"      TP2: ${tp2:.2f} ({tp2_distance}p)")
            print(f"      TP3: ${tp3:.2f} ({tp3_distance}p)")
            
            # Calculate risk/reward (for TP2)
            if last_signal['signal'] == 1:
                risk = entry - sl
                reward = tp2 - entry
            else:
                risk = sl - entry
                reward = entry - tp2
                
            rr = reward / risk if risk > 0 else 0
            print(f"      Risk: {risk:.2f} points")
            print(f"      Reward (TP2): {reward:.2f} points")
            print(f"      Risk:Reward = 1:{rr:.2f}")
            
            return {
                'direction': last_signal['signal'],
                'entry': entry,
                'sl': sl,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'tp1_distance': tp1_distance,
                'tp2_distance': tp2_distance,
                'tp3_distance': tp3_distance,
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
        """Open 3 positions with different TP levels (TP1, TP2, TP3)"""
        direction_str = "BUY" if signal['direction'] == 1 else "SELL"
        
        print(f"\n{'='*60}")
        print(f"📈 OPENING 3 {direction_str} POSITIONS (Multi-TP)")
        print(f"{'='*60}")
        
        # Check max positions (need room for 3 positions)
        open_positions = self.get_open_positions()
        if len(open_positions) + 3 > self.max_positions:
            print(f"⚠️  Not enough room for 3 positions (need {3}, have {self.max_positions - len(open_positions)} slots)")
            return False
            
        # Calculate total lot size
        total_lot_size = self.calculate_position_size(signal['entry'], signal['sl'])
        
        # Split into 3 parts: 33%, 33%, 34%
        lot1 = round(total_lot_size * 0.33, 2)
        lot2 = round(total_lot_size * 0.33, 2)
        lot3 = round(total_lot_size * 0.34, 2)
        
        print(f"   Total lot size: {total_lot_size}")
        print(f"   Position 1 (TP1): {lot1} lot")
        print(f"   Position 2 (TP2): {lot2} lot")
        print(f"   Position 3 (TP3): {lot3} lot")
        
        if self.dry_run:
            print(f"\n🧪 DRY RUN: Would open 3 {direction_str} positions:")
            print(f"   Entry: {signal['entry']:.2f}")
            print(f"   SL: {signal['sl']:.2f}")
            print(f"   Position 1: {lot1} lot, TP1: {signal['tp1']:.2f} ({signal['tp1_distance']}p)")
            print(f"   Position 2: {lot2} lot, TP2: {signal['tp2']:.2f} ({signal['tp2_distance']}p)")
            print(f"   Position 3: {lot3} lot, TP3: {signal['tp3']:.2f} ({signal['tp3_distance']}p)")
            print(f"   Total risk: {self.risk_percent}%")
            return True
            
        # Prepare common parameters
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Symbol info not found")
            return False
            
        # Get current price
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"❌ Failed to get current price")
            return False
            
        price = tick.ask if signal['direction'] == 1 else tick.bid
        regime_code = "T" if signal.get('regime') == 'TREND' else "R"
        order_type = mt5.ORDER_TYPE_BUY if signal['direction'] == 1 else mt5.ORDER_TYPE_SELL
        
        # Open 3 positions
        positions_opened = []
        tp_levels = [
            (signal['tp1'], lot1, 'TP1', signal['tp1_distance']),
            (signal['tp2'], lot2, 'TP2', signal['tp2_distance']),
            (signal['tp3'], lot3, 'TP3', signal['tp3_distance'])
        ]
        
        for tp_price, lot_size, tp_name, tp_distance in tp_levels:
            # Ensure minimum lot size
            if lot_size < symbol_info.volume_min:
                print(f"   ⚠️  {tp_name}: lot size {lot_size} < minimum {symbol_info.volume_min}, skipping")
                continue
                
            # Create request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "sl": signal['sl'],
                "tp": tp_price,
                "deviation": 20,
                "magic": 234000,
                "comment": f"V3_{regime_code}_{tp_name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                print(f"   ❌ {tp_name} order failed: No result")
                continue
                
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"   ❌ {tp_name} order failed: {result.retcode} - {result.comment}")
                continue
                
            print(f"   ✅ {tp_name} position opened!")
            print(f"      Order: #{result.order}")
            print(f"      Lot: {lot_size}")
            print(f"      TP: {tp_price:.2f} ({tp_distance}p)")
            
            # Log position
            position_type = 'BUY' if signal['direction'] == 1 else 'SELL'
            regime = signal.get('regime', 'UNKNOWN')
            self._log_position_opened(
                ticket=result.order,
                position_type=position_type,
                volume=lot_size,
                entry_price=result.price,
                sl=signal['sl'],
                tp=tp_price,
                regime=regime,
                comment=f"V3_{regime_code}_{tp_name}"
            )
            
            positions_opened.append((result.order, tp_name, tp_price))
        
        if len(positions_opened) == 0:
            print(f"\n❌ Failed to open any positions!")
            return False
        
        print(f"\n✅ Successfully opened {len(positions_opened)}/3 positions!")
        
        # Send Telegram notification
        if self.telegram_bot:
            import asyncio
            regime = signal.get('regime', 'UNKNOWN')
            message = f"🤖 <b>3 Positions Opened (Multi-TP)</b>\n\n"
            message += f"Direction: {direction_str}\n"
            message += f"Market Regime: {regime}\n"
            message += f"Entry: ~{price:.2f}\n"
            message += f"SL: {signal['sl']:.2f}\n\n"
            message += f"<b>Take Profits:</b>\n"
            for ticket, tp_name, tp_price in positions_opened:
                message += f"  {tp_name}: ${tp_price:.2f} (#{ticket})\n"
            message += f"\nTotal risk: {self.risk_percent}%"
            asyncio.run(self.send_telegram(message))
            
        return True
    
    def generate_report(self):
        """Generate trading report from CSV log"""
        if not os.path.exists(self.trades_file):
            print("❌ No trade log file found")
            return
        
        df = pd.read_csv(self.trades_file)
        
        if len(df) == 0:
            print("📊 No trades recorded yet")
            return
        
        print(f"\n{'='*80}")
        print("📊 TRADING REPORT")
        print(f"{'='*80}")
        print(f"Total trades: {len(df)}")
        
        if 'Status' in df.columns and 'Profit' in df.columns:
            completed = df[df['Status'].isin(['CLOSED', 'TP', 'SL'])]
            if len(completed) > 0:
                wins = completed[completed['Profit'] > 0]
                losses = completed[completed['Profit'] < 0]
                
                print(f"\n💰 P&L Summary:")
                print(f"   Total P&L: ${completed['Profit'].sum():.2f}")
                print(f"   Wins: {len(wins)} ({len(wins)/len(completed)*100:.1f}%)")
                print(f"   Losses: {len(losses)} ({len(losses)/len(completed)*100:.1f}%)")
                
                if len(wins) > 0:
                    print(f"   Avg Win: ${wins['Profit'].mean():.2f}")
                    print(f"   Max Win: ${wins['Profit'].max():.2f}")
                
                if len(losses) > 0:
                    print(f"   Avg Loss: ${losses['Profit'].mean():.2f}")
                    print(f"   Max Loss: ${losses['Profit'].min():.2f}")
                
                if len(losses) > 0 and abs(losses['Profit'].sum()) > 0:
                    pf = abs(wins['Profit'].sum()) / abs(losses['Profit'].sum())
                    print(f"   Profit Factor: {pf:.2f}")
        
        if 'Market_Regime' in df.columns:
            print(f"\n📊 By Market Regime:")
            for regime in df['Market_Regime'].unique():
                regime_trades = df[df['Market_Regime'] == regime]
                if len(regime_trades) > 0:
                    regime_profit = regime_trades['Profit'].sum() if 'Profit' in df.columns else 0
                    print(f"   {regime}: {len(regime_trades)} trades, ${regime_profit:.2f}")
        
        if 'Duration_Hours' in df.columns:
            completed = df[df['Duration_Hours'].notna()]
            if len(completed) > 0:
                print(f"\n⏱️  Duration:")
                print(f"   Avg: {completed['Duration_Hours'].mean():.1f}h")
                print(f"   Min: {completed['Duration_Hours'].min():.1f}h")
                print(f"   Max: {completed['Duration_Hours'].max():.1f}h")
        
        print(f"\n📁 Full log: {self.trades_file}")
        print(f"{'='*80}\n")
        
    def _wait_until_next_hour(self):
        """Wait until the next full hour (01:00, 02:00, etc.)
        While waiting, monitor positions every 10 seconds for TP hits"""
        now = datetime.now()
        
        # Calculate next hour
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_hour - now).total_seconds()
        
        if wait_seconds > 0:
            print(f"\n⏰ Waiting until next hour: {next_hour.strftime('%H:%M:%S')}")
            print(f"   Time now: {now.strftime('%H:%M:%S')}")
            print(f"   Wait time: {int(wait_seconds/60)} min {int(wait_seconds%60)} sec")
            print(f"   🎯 Real-time TP monitoring: Active (checking every 10s)")
            
            # Monitor positions while waiting
            monitoring_interval = 10  # Check every 10 seconds
            elapsed = 0
            
            while elapsed < wait_seconds:
                # Sleep for monitoring interval or remaining time
                sleep_time = min(monitoring_interval, wait_seconds - elapsed)
                time.sleep(sleep_time)
                elapsed += sleep_time
                
                # Check TP levels in real-time
                self._check_tp_levels_realtime()
                
                # Also check for closed positions
                self._check_closed_positions()
            
    def run(self):
        """Main bot loop - runs exactly on the hour (01:00, 02:00, etc.)"""
        print(f"\n{'='*80}")
        print(f"🤖 BOT STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"📊 Configuration:")
        print(f"   Symbol: {self.symbol}")
        print(f"   Timeframe: H1")
        print(f"   Strategy: V3 Adaptive (TREND/RANGE detection)")
        print(f"   Check interval: Every hour on the hour (01:00, 02:00, 03:00...)")
        print(f"   Signal source: ONLY latest closed candle (no historical signals)")
        print(f"   Risk per trade: {self.risk_percent}%")
        print(f"   Max positions: {self.max_positions}")
        print(f"   Mode: {'🧪 DRY RUN (TEST)' if self.dry_run else '🚀 LIVE TRADING'}")
        print(f"   🎯 Real-time TP monitoring: Every 10 seconds")
        print(f"\n🎯 Adaptive TP Levels:")
        print(f"   TREND Mode: {self.trend_tp1}p / {self.trend_tp2}p / {self.trend_tp3}p")
        print(f"   RANGE Mode: {self.range_tp1}p / {self.range_tp2}p / {self.range_tp3}p")
        print(f"\n📁 Log Files:")
        print(f"   Trade log: {self.trades_file}")
        print(f"   TP hits log: {self.tp_hits_file}")
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
        
        # Send startup notification to Telegram
        if self.telegram_bot and self.telegram_chat_id:
            startup_message = f"""
🤖 <b>BOT STARTED</b>

📊 <b>Configuration:</b>
Symbol: {self.symbol}
Timeframe: H1
Strategy: V3 Adaptive (TREND/RANGE)
Risk per trade: {self.risk_percent}%
Max positions: {self.max_positions}
Mode: {'🧪 DRY RUN (TEST)' if self.dry_run else '🚀 LIVE TRADING'}

🎯 <b>TP Levels:</b>
TREND: {self.trend_tp1}p / {self.trend_tp2}p / {self.trend_tp3}p
RANGE: {self.range_tp1}p / {self.range_tp2}p / {self.range_tp3}p

⏰ <b>Started at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ Bot is now active and monitoring the market!
"""
            try:
                asyncio.run(self.send_telegram(startup_message))
                print("📱 Startup notification sent to Telegram")
            except Exception as e:
                print(f"⚠️  Failed to send startup notification: {e}")
        
        # Wait until the next hour before starting
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
                if not self.mt5_connected:
                    print("❌ MT5 disconnected! Attempting to reconnect...")
                    if not self.connect_mt5():
                        print("❌ Reconnection failed. Waiting 60s...")
                        time.sleep(60)
                        continue
                
                # Check current positions
                open_positions = self.get_open_positions()
                
                # Check TP levels in real-time
                self._check_tp_levels_realtime()
                
                # Check for closed positions and log them
                self._check_closed_positions()
                
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
                    
                # Wait until next full hour
                print(f"\n{'='*80}")
                print(f"💤 Waiting until next full hour...")
                print(f"   Press Ctrl+C to stop the bot")
                print(f"{'='*80}\n")
                
                # Wait until next hour (01:00, 02:00, 03:00, etc.)
                self._wait_until_next_hour()
                
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
            
            # Send shutdown notification to Telegram
            if self.telegram_bot and self.telegram_chat_id:
                shutdown_message = f"""
⏹️ <b>BOT STOPPED</b>

📊 <b>Summary:</b>
Total iterations: {iteration}
Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{"⚠️ <b>WARNING:</b> " + str(len(open_positions)) + " position(s) still open!" if len(open_positions) > 0 else "✅ No open positions"}

🛑 Bot has been stopped by user.
"""
                try:
                    asyncio.run(self.send_telegram(shutdown_message))
                    print("📱 Shutdown notification sent to Telegram")
                except Exception as e:
                    print(f"⚠️  Failed to send shutdown notification: {e}")
            
            # Generate trading report
            self.generate_report()
                
            print(f"{'='*80}\n")
        except Exception as e:
            print(f"\n\n❌ BOT ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("🔌 Disconnecting from MT5...")
            self.disconnect_mt5()
            print("✅ Shutdown complete")
