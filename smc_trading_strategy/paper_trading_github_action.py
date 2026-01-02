"""
Paper Trading Bot для GitHub Actions
Режим: одна проверка сигналов/позиций, затем выход
Оптимизирован для scheduled runs в CI/CD
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import json
from dotenv import load_dotenv
import MetaTrader5 as mt5

sys.path.append(os.path.dirname(__file__))
from telegram_notifier import TelegramNotifier
from mt5_data_downloader import MT5DataDownloader
from pattern_recognition_strategy import PatternRecognitionStrategy


class GitHubActionPaperTradingBot:
    """
    Paper trading bot оптимизированный для GitHub Actions
    
    Ключевые отличия от обычного бота:
    - Запускается один раз, затем выходит (для scheduled runs)
    - Сохраняет состояние в файл
    - Загружает предыдущее состояние при запуске
    - Подходит для cron-like выполнения
    """

    def __init__(self, telegram_token=None, telegram_chat_id=None,
                 symbol='XAUUSD', timeframe=mt5.TIMEFRAME_H1,
                 max_positions=5, timezone_offset=5,
                 state_file='trading_state.json'):
        """
        Initialize GitHub Actions Paper Trading Bot
        
        Args:
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            symbol: MT5 symbol
            timeframe: MT5 timeframe
            max_positions: Maximum concurrent positions
            timezone_offset: Timezone offset in hours from UTC
            state_file: File to save/load trading state
        """
        self.strategy = PatternRecognitionStrategy(fib_mode='standard')
        self.symbol = symbol
        self.timeframe = timeframe
        
        # LONG TREND MODE parameters (from baseline)
        self.long_trend_tp1 = 30
        self.long_trend_tp2 = 55
        self.long_trend_tp3 = 90
        self.long_trend_trailing = 18
        self.long_trend_timeout = 60
        
        # LONG RANGE MODE parameters (from baseline)
        self.long_range_tp1 = 20
        self.long_range_tp2 = 35
        self.long_range_tp3 = 50
        self.long_range_trailing = 15
        self.long_range_timeout = 48
        
        # SHORT TREND MODE parameters (OPTIMIZED - asymmetric!)
        self.short_trend_tp1 = 15
        self.short_trend_tp2 = 25
        self.short_trend_tp3 = 35
        self.short_trend_trailing = 10
        self.short_trend_timeout = 24
        
        # SHORT RANGE MODE - DISABLED
        self.short_range_enabled = False
        
        # Partial close percentages
        self.close_pct1 = 0.5
        self.close_pct2 = 0.3
        self.close_pct3 = 0.2
        
        # Risk management
        self.max_positions = max_positions
        
        # MT5 data downloader
        self.mt5_downloader = MT5DataDownloader(symbol=symbol, timeframe=timeframe)
        
        # Telegram notifier
        if telegram_token and telegram_chat_id:
            self.notifier = TelegramNotifier(telegram_token, telegram_chat_id, timezone_offset=timezone_offset)
        else:
            self.notifier = None
            print("⚠️  Telegram notifications disabled")
        
        # State management
        self.state_file = state_file
        self.open_positions = []
        self.closed_trades = []
        self.last_processed_signal_time = None
        
        # Statistics file
        self.stats_file = f'live_bot_statistics_{symbol}.csv'
        
        # Load previous state
        self.load_state()
        
        print("✅ GitHub Actions Paper Trading Bot initialized")
        print(f"   Symbol: {symbol}")
        print(f"   State file: {state_file}")
        print(f"   Open positions: {len(self.open_positions)}")
        print(f"   Closed trades: {len(self.closed_trades)}")

    def connect_mt5(self, login=None, password=None, server=None):
        """Connect to MT5 terminal"""
        return self.mt5_downloader.connect(login=login, password=password, server=server)

    def detect_market_regime(self, df, current_idx=None, lookback=100):
        """Detect market regime: TREND or RANGE"""
        if current_idx is None:
            current_idx = len(df) - 1
        
        if current_idx < lookback:
            return 'RANGE'
        
        recent_data = df.iloc[current_idx - lookback:current_idx]
        
        # 1. EMA CROSSOVER
        closes = recent_data['close']
        ema_fast = closes.ewm(span=20, adjust=False).mean()
        ema_slow = closes.ewm(span=50, adjust=False).mean()
        ema_diff_pct = abs((ema_fast.iloc[-1] - ema_slow.iloc[-1]) / ema_slow.iloc[-1]) * 100
        ema_trend = ema_diff_pct > 0.3
        
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
        
        # 4. Sequential movements
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
        
        # TREND if 3+ signals
        trend_signals = sum([ema_trend, high_volatility, strong_direction, directional_bias, structural_trend])
        return 'TREND' if trend_signals >= 3 else 'RANGE'

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
        """Get current price from MT5"""
        return self.mt5_downloader.get_current_price()

    def check_for_signals(self):
        """Check for new trading signals"""
        print(f"\n{'='*80}")
        print(f"🔍 SIGNAL CHECK at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        # Download latest data
        df = self.download_data()
        if df is None:
            print("❌ Failed to download data")
            return
        
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
            
            # Check if already processed
            if self.last_processed_signal_time is not None:
                if last_signal_time == self.last_processed_signal_time:
                    print(f"📊 Signal at {last_signal_time} already processed")
                    return
            
            # Only accept signals on last closed candle
            latest_candle_time = df_strategy.index[-1]
            candles_behind = len(df_strategy) - 1 - df_strategy.index.get_loc(last_signal_time)
            
            if candles_behind > 1:
                print(f"📊 Signal is {candles_behind} candles old - REPAINTING DETECTED")
                return
            
            # Check max positions
            if len(self.open_positions) >= self.max_positions:
                print(f"⚠️  Max positions limit reached ({self.max_positions})")
                return
            
            # Detect regime
            signal_idx = len(df_strategy) - 1
            regime = self.detect_market_regime(df_strategy, signal_idx)
            
            # Filter SHORT in RANGE
            direction = 'LONG' if last_signal['signal'] == 1 else 'SHORT'
            if direction == 'SHORT' and regime == 'RANGE' and not self.short_range_enabled:
                print(f"📊 SHORT signal in RANGE regime - FILTERED")
                return
            
            print(f"🎯 NEW SIGNAL DETECTED!")
            print(f"   Direction: {direction} | Entry: {last_signal['entry_price']:.2f} | Regime: {regime}")
            
            # Open position
            self.open_position(last_signal, last_signal_time, regime)
            self.last_processed_signal_time = last_signal_time
            
        except Exception as e:
            print(f"❌ Error checking signals: {e}")
            import traceback
            traceback.print_exc()

    def open_position(self, signal, timestamp, regime):
        """Open new position"""
        entry_price = signal['entry_price']
        direction = 'LONG' if signal['signal'] == 1 else 'SHORT'
        
        # Choose parameters based on direction and regime
        if direction == 'LONG':
            if regime == 'TREND':
                tp1, tp2, tp3 = self.long_trend_tp1, self.long_trend_tp2, self.long_trend_tp3
                trailing, timeout = self.long_trend_trailing, self.long_trend_timeout
            else:
                tp1, tp2, tp3 = self.long_range_tp1, self.long_range_tp2, self.long_range_tp3
                trailing, timeout = self.long_range_trailing, self.long_range_timeout
        else:
            tp1, tp2, tp3 = self.short_trend_tp1, self.short_trend_tp2, self.short_trend_tp3
            trailing, timeout = self.short_trend_trailing, self.short_trend_timeout
        
        # Calculate TPs
        if direction == 'LONG':
            tp1_price = entry_price + tp1
            tp2_price = entry_price + tp2
            tp3_price = entry_price + tp3
        else:
            tp1_price = entry_price - tp1
            tp2_price = entry_price - tp2
            tp3_price = entry_price - tp3
        
        position = {
            'entry_time': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
            'direction': direction,
            'entry_price': float(entry_price),
            'stop_loss': float(signal['stop_loss']),
            'regime': regime,
            'tp1_price': float(tp1_price),
            'tp2_price': float(tp2_price),
            'tp3_price': float(tp3_price),
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'trailing_active': False,
            'trailing_distance': float(trailing),
            'trailing_high': float(entry_price) if direction == 'LONG' else 0.0,
            'trailing_low': float(entry_price) if direction == 'SHORT' else 999999.0,
            'timeout_hours': float(timeout),
            'position_remaining': 1.0,
            'total_pnl_pct': 0.0,
            'pattern': str(signal.get('pattern', 'N/A'))
        }
        
        self.open_positions.append(position)
        
        print(f"✅ Position opened: {direction} @ {entry_price:.2f} [{regime}]")
        print(f"   TP1: {tp1_price:.2f} | TP2: {tp2_price:.2f} | TP3: {tp3_price:.2f}")
        print(f"   SL: {signal['stop_loss']:.2f} | Trailing: {trailing}п | Timeout: {timeout}h")
        
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
                'regime': regime,
                'trailing': trailing,
                'pattern': position['pattern'],
                'timestamp': timestamp
            }
            self.notifier.send_entry_signal(signal_data)

    def check_open_positions(self):
        """Check open positions"""
        if len(self.open_positions) == 0:
            print("📊 No open positions")
            return
        
        print(f"\n{'='*80}")
        print(f"💰 POSITION CHECK at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Open positions: {len(self.open_positions)}")
        print(f"{'='*80}")
        
        current_price_data = self.get_current_price()
        if current_price_data is None:
            print("⚠️  Could not get current price")
            return
        
        current_time = current_price_data['time']
        current_bid = current_price_data['bid']
        current_ask = current_price_data['ask']
        
        positions_to_close = []
        
        for i, pos in enumerate(self.open_positions):
            if pos['position_remaining'] <= 0:
                positions_to_close.append((i, pos['entry_price'], 'CLOSED', pos['total_pnl_pct']))
                continue
            
            # Parse entry_time
            if isinstance(pos['entry_time'], str):
                entry_time = pd.to_datetime(pos['entry_time'])
            else:
                entry_time = pos['entry_time']
            
            # Check timeout
            time_in_trade = (current_time - entry_time).total_seconds() / 3600
            timeout_hours = pos.get('timeout_hours', 48)
            
            if time_in_trade >= timeout_hours:
                exit_price = current_bid if pos['direction'] == 'LONG' else current_ask
                if pos['direction'] == 'LONG':
                    pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                else:
                    pnl_pct = ((pos['entry_price'] - exit_price) / pos['entry_price']) * 100 * pos['position_remaining']
                pos['total_pnl_pct'] += pnl_pct
                positions_to_close.append((i, exit_price, 'TIMEOUT', pos['total_pnl_pct']))
                continue
            
            # Check SL/TP
            if pos['direction'] == 'LONG':
                exit_price = current_bid
                
                # Update trailing
                if current_bid > pos.get('trailing_high', pos['entry_price']):
                    pos['trailing_high'] = current_bid
                
                if pos.get('trailing_active', False):
                    new_sl = pos['trailing_high'] - pos.get('trailing_distance', 15)
                    if new_sl > pos['stop_loss']:
                        pos['stop_loss'] = new_sl
                
                # Check SL
                if exit_price <= pos['stop_loss']:
                    pnl_pct = ((pos['stop_loss'] - pos['entry_price']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    exit_type = 'TRAILING_SL' if pos.get('trailing_active', False) else 'SL'
                    positions_to_close.append((i, pos['stop_loss'], exit_type, pos['total_pnl_pct']))
                    continue
                
                # Check TPs
                self._check_tp_levels(pos, exit_price, current_time, 'LONG')
            
            else:  # SHORT
                exit_price = current_ask
                
                # Update trailing
                if current_ask < pos.get('trailing_low', 999999):
                    pos['trailing_low'] = current_ask
                
                if pos.get('trailing_active', False):
                    new_sl = pos['trailing_low'] + pos.get('trailing_distance', 15)
                    if new_sl < pos['stop_loss']:
                        pos['stop_loss'] = new_sl
                
                # Check SL
                if exit_price >= pos['stop_loss']:
                    pnl_pct = ((pos['entry_price'] - pos['stop_loss']) / pos['entry_price']) * 100 * pos['position_remaining']
                    pos['total_pnl_pct'] += pnl_pct
                    exit_type = 'TRAILING_SL' if pos.get('trailing_active', False) else 'SL'
                    positions_to_close.append((i, pos['stop_loss'], exit_type, pos['total_pnl_pct']))
                    continue
                
                # Check TPs
                self._check_tp_levels(pos, exit_price, current_time, 'SHORT')
        
        # Close positions
        for idx, exit_price, exit_type, total_pnl in reversed(positions_to_close):
            self.close_position(idx, exit_price, exit_type, current_time, total_pnl)

    def _check_tp_levels(self, pos, exit_price, current_time, direction):
        """Check TP levels and update position"""
        if direction == 'LONG':
            # TP3
            if exit_price >= pos['tp3_price'] and not pos['tp3_hit']:
                pnl_pct = ((pos['tp3_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct3
                pos['total_pnl_pct'] += pnl_pct
                pos['position_remaining'] -= self.close_pct3
                pos['tp3_hit'] = True
                print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f}")
                self._send_partial_close_notification(pos, 'TP3', pnl_pct, current_time)
            
            # TP2
            if exit_price >= pos['tp2_price'] and not pos['tp2_hit']:
                pnl_pct = ((pos['tp2_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct2
                pos['total_pnl_pct'] += pnl_pct
                pos['position_remaining'] -= self.close_pct2
                pos['tp2_hit'] = True
                print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f}")
                self._send_partial_close_notification(pos, 'TP2', pnl_pct, current_time)
            
            # TP1
            if exit_price >= pos['tp1_price'] and not pos['tp1_hit']:
                pnl_pct = ((pos['tp1_price'] - pos['entry_price']) / pos['entry_price']) * 100 * self.close_pct1
                pos['total_pnl_pct'] += pnl_pct
                pos['position_remaining'] -= self.close_pct1
                pos['tp1_hit'] = True
                pos['trailing_active'] = True
                pos['stop_loss'] = exit_price - pos.get('trailing_distance', 15)
                print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} - Trailing activated")
                self._send_partial_close_notification(pos, 'TP1', pnl_pct, current_time, trailing=True)
        
        else:  # SHORT
            # TP3
            if exit_price <= pos['tp3_price'] and not pos['tp3_hit']:
                pnl_pct = ((pos['entry_price'] - pos['tp3_price']) / pos['entry_price']) * 100 * self.close_pct3
                pos['total_pnl_pct'] += pnl_pct
                pos['position_remaining'] -= self.close_pct3
                pos['tp3_hit'] = True
                print(f"   🎯 TP3 HIT @ {pos['tp3_price']:.2f}")
                self._send_partial_close_notification(pos, 'TP3', pnl_pct, current_time)
            
            # TP2
            if exit_price <= pos['tp2_price'] and not pos['tp2_hit']:
                pnl_pct = ((pos['entry_price'] - pos['tp2_price']) / pos['entry_price']) * 100 * self.close_pct2
                pos['total_pnl_pct'] += pnl_pct
                pos['position_remaining'] -= self.close_pct2
                pos['tp2_hit'] = True
                print(f"   🎯 TP2 HIT @ {pos['tp2_price']:.2f}")
                self._send_partial_close_notification(pos, 'TP2', pnl_pct, current_time)
            
            # TP1
            if exit_price <= pos['tp1_price'] and not pos['tp1_hit']:
                pnl_pct = ((pos['entry_price'] - pos['tp1_price']) / pos['entry_price']) * 100 * self.close_pct1
                pos['total_pnl_pct'] += pnl_pct
                pos['position_remaining'] -= self.close_pct1
                pos['tp1_hit'] = True
                pos['trailing_active'] = True
                pos['stop_loss'] = exit_price + pos.get('trailing_distance', 15)
                print(f"   🎯 TP1 HIT @ {pos['tp1_price']:.2f} - Trailing activated")
                self._send_partial_close_notification(pos, 'TP1', pnl_pct, current_time, trailing=True)

    def _send_partial_close_notification(self, pos, tp_level, pnl_pct, current_time, trailing=False):
        """Send partial close notification"""
        if self.notifier:
            pnl_points = (pnl_pct / 100) * pos['entry_price']
            data = {
                'direction': pos['direction'],
                'tp_level': tp_level,
                'tp_price': pos[f'{tp_level.lower()}_price'],
                'entry_price': pos['entry_price'],
                'close_pct': self.close_pct1 if tp_level == 'TP1' else (self.close_pct2 if tp_level == 'TP2' else self.close_pct3),
                'pnl_pct': pnl_pct,
                'pnl_points': pnl_points,
                'position_remaining': pos['position_remaining'],
                'regime': pos.get('regime', 'N/A'),
                'timestamp': current_time
            }
            if trailing:
                data['trailing_activated'] = True
                data['trailing_distance'] = pos.get('trailing_distance', 15)
            self.notifier.send_partial_close(data)

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
        
        # Parse entry_time
        if isinstance(pos['entry_time'], str):
            entry_time = pd.to_datetime(pos['entry_time'])
        else:
            entry_time = pos['entry_time']
        
        duration_hours = (exit_time - entry_time).total_seconds() / 3600
        
        closed_trade = {
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': pos['direction'],
            'regime': pos.get('regime', 'N/A'),
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'stop_loss': pos['stop_loss'],
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_points': pnl_points,
            'duration_hours': duration_hours,
            'pattern': pos['pattern'],
            'trailing_used': pos.get('trailing_active', False)
        }
        
        self.closed_trades.append(closed_trade)
        
        emoji = "✅" if pnl_pct > 0 else "❌"
        print(f"\n{emoji} POSITION CLOSED:")
        print(f"   {pos['direction']}: {pos['entry_price']:.2f} → {exit_price:.2f} [{pos.get('regime', 'N/A')}]")
        print(f"   Exit: {exit_type} | PnL: {pnl_pct:+.2f}% ({pnl_points:+.2f}п) | Duration: {duration_hours:.1f}h")
        
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
        self.save_statistics()

    def save_statistics(self):
        """Save trading statistics"""
        if len(self.closed_trades) == 0:
            return
        
        try:
            df_stats = pd.DataFrame(self.closed_trades)
            df_stats.to_csv(self.stats_file, index=False)
            
            total_trades = len(df_stats)
            wins = len(df_stats[df_stats['pnl_pct'] > 0])
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            total_pnl = df_stats['pnl_pct'].sum()
            
            print(f"💾 Statistics: {total_trades} trades | WR: {win_rate:.1f}% | PnL: {total_pnl:+.2f}%")
        
        except Exception as e:
            print(f"❌ Error saving statistics: {e}")

    def save_state(self):
        """Save bot state to file"""
        try:
            state = {
                'open_positions': self.open_positions,
                'closed_trades': [
                    {**trade, 'entry_time': trade['entry_time'].isoformat() if hasattr(trade['entry_time'], 'isoformat') else str(trade['entry_time']),
                     'exit_time': trade['exit_time'].isoformat() if hasattr(trade['exit_time'], 'isoformat') else str(trade['exit_time'])}
                    for trade in self.closed_trades
                ],
                'last_processed_signal_time': self.last_processed_signal_time.isoformat() if self.last_processed_signal_time else None,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            print(f"💾 State saved: {len(self.open_positions)} open, {len(self.closed_trades)} closed")
        
        except Exception as e:
            print(f"❌ Error saving state: {e}")

    def load_state(self):
        """Load bot state from file"""
        try:
            if not os.path.exists(self.state_file):
                print("📝 No previous state found (first run)")
                return
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.open_positions = state.get('open_positions', [])
            self.closed_trades = state.get('closed_trades', [])
            
            # Parse timestamps
            for trade in self.closed_trades:
                if 'entry_time' in trade:
                    trade['entry_time'] = pd.to_datetime(trade['entry_time'])
                if 'exit_time' in trade:
                    trade['exit_time'] = pd.to_datetime(trade['exit_time'])
            
            if state.get('last_processed_signal_time'):
                self.last_processed_signal_time = pd.to_datetime(state['last_processed_signal_time'])
            
            print(f"📂 State loaded: {len(self.open_positions)} open, {len(self.closed_trades)} closed")
        
        except Exception as e:
            print(f"⚠️  Error loading state: {e}")

    def run_once(self):
        """Run one iteration: check signals and positions"""
        print("\n" + "="*80)
        print("🤖 GITHUB ACTIONS PAPER TRADING BOT - ONE-TIME RUN")
        print("="*80)
        print(f"⏰ Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Symbol: {self.symbol}")
        print(f"📈 Open positions: {len(self.open_positions)}")
        print(f"📉 Closed trades: {len(self.closed_trades)}")
        print("="*80)
        
        # Check signals
        self.check_for_signals()
        
        # Check positions
        self.check_open_positions()
        
        # Save state
        self.save_state()
        
        # Print summary
        print("\n" + "="*80)
        print("📊 RUN SUMMARY")
        print("="*80)
        print(f"✅ Run completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 Open positions: {len(self.open_positions)}")
        print(f"📉 Total closed trades: {len(self.closed_trades)}")
        
        if len(self.closed_trades) > 0:
            recent_trades = self.closed_trades[-5:]
            total_pnl = sum(t['pnl_pct'] for t in recent_trades)
            print(f"💰 Last 5 trades PnL: {total_pnl:+.2f}%")
        
        print("="*80)


def main():
    """Main entry point for GitHub Actions"""
    load_dotenv()
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    # MT5 credentials
    mt5_login = os.getenv('MT5_LOGIN')
    mt5_password = os.getenv('MT5_PASSWORD')
    mt5_server = os.getenv('MT5_SERVER')
    mt5_symbol = os.getenv('MT5_SYMBOL', 'XAUUSD')
    
    # Initialize bot
    bot = GitHubActionPaperTradingBot(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        symbol=mt5_symbol,
        timeframe=mt5.TIMEFRAME_H1,
        state_file='trading_state.json'
    )
    
    # Connect MT5
    if not bot.connect_mt5(login=mt5_login, password=mt5_password, server=mt5_server):
        print("\n❌ MT5 connection failed")
        print("   Возможные причины:")
        print("   1. MT5 терминал не установлен")
        print("   2. Неверные credentials")
        print("   3. Сервер недоступен")
        print("\n   Для GitHub Actions требуется self-hosted runner с MT5!")
        return 1
    
    # Run once
    bot.run_once()
    
    # Disconnect
    bot.mt5_downloader.disconnect()
    
    return 0


if __name__ == "__main__":
    exit(main())
