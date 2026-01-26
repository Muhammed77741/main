"""
Bot Thread - runs trading bot in separate thread
"""
import sys
import os
import io
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from typing import Optional
import traceback
import time
from datetime import datetime

# Add trading_bots to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'trading_bots'))

from models import BotConfig, BotStatus, TradeRecord
from core.mt5_manager import mt5_manager


class StdoutRedirector(io.StringIO):
    """Redirect stdout to GUI log"""

    def __init__(self, log_signal, bot_id):
        super().__init__()
        self.log_signal = log_signal
        self.bot_id = bot_id
        self.buffer = ""

    def write(self, text):
        """Capture print output and emit to GUI - only important messages"""
        if text and text.strip():
            lines = text.split('\n')
            for line in lines:
                line_clean = line.strip()
                if not line_clean:
                    continue

                # Filter: Only show important messages
                # Show these:
                important_keywords = [
                    '🔍 Checking',  # Signal check iteration
                    '❌ No valid signal',  # No signal found
                    '❌',  # All error messages
                    '🎯',  # Signal detected / TP hit
                    '📈 OPENING',  # Opening positions
                    '✅ Position opened',  # Position opened successfully
                    '✅',  # All success messages
                    '✅ Stop-loss updated',  # SL updated
                    '⚠️',  # Warnings
                    '🛑',  # Stop loss hit
                    '📊 Trailing Stop Updated',  # Trailing update
                    'SIGNAL DETECTED',
                    'Position 1 closing',  # TP1 activation
                    'Position 1 closed',  # TP1 activation
                    'Activating trailing',
                    'TP',
                    'HIT',
                    'CLOSED',
                    'ERROR',
                    'Failed',  # All failed messages
                    'order failed',  # Order failures
                    'retcode',  # MT5 error codes
                    'Unsupported filling mode',  # Filling mode errors
                    'Failed to connect',
                    'Connected to',
                    'Bot stopped',
                    'Starting bot'
                ]

                # Skip verbose/debug messages
                skip_patterns = [
                    'Fetching',
                    'Current bar',
                    'OHLCV',
                    'Calculating',
                    'Open positions after',
                    'Verifying positions',
                    'Sleep',
                    'Waiting for',
                    'LIVE: Monitoring',
                    'DRY RUN: Would',
                    'Order ID:',
                    'Size:',
                    'Entry:',
                    'Lot:',
                    'TP:',
                    'Risk:',
                    'Regime:',
                    'Total',
                    'Position size',
                    'Using',
                    'Public API'
                ]

                # Check if line should be skipped
                should_skip = any(pattern.lower() in line_clean.lower() for pattern in skip_patterns)
                if should_skip:
                    continue

                # Check if line is important
                is_important = any(keyword in line_clean for keyword in important_keywords)

                # Show important messages
                if is_important:
                    self.log_signal.emit(line_clean)

        return len(text)

    def flush(self):
        """Flush buffer (required by Python)"""
        pass


class BotThread(QThread):
    """Thread for running a trading bot"""

    # Signals for GUI updates
    log_signal = Signal(str)  # Log message
    status_signal = Signal(BotStatus)  # Status update
    error_signal = Signal(str)  # Error message

    def __init__(self, config: BotConfig, db=None):
        super().__init__()
        self.config = config
        self.db = db
        self.running = False
        self.bot = None
        self._stop_requested = False

    def run(self):
        """Main bot loop"""
        self.running = True
        self._stop_requested = False

        # Redirect stdout to capture all print() calls from bot
        old_stdout = sys.stdout
        stdout_redirector = StdoutRedirector(self.log_signal, self.config.bot_id)

        try:
            # Start redirecting stdout
            sys.stdout = stdout_redirector

            self.log_signal.emit(f"[{self.config.bot_id}] Starting bot...")

            # Initialize bot based on exchange
            if self.config.exchange == 'MT5':
                self._init_mt5_bot()
            elif self.config.exchange == 'Binance':
                self._init_binance_bot()
            else:
                raise ValueError(f"Unknown exchange: {self.config.exchange}")

            # Connect to exchange (different method names for different exchanges)
            if self.config.exchange == 'MT5':
                if not self.bot.connect_mt5():
                    self.error_signal.emit("Failed to connect to MT5")
                    return
            else:  # Binance
                if not self.bot.connect_exchange():
                    self.error_signal.emit("Failed to connect to Binance")
                    return

            self.log_signal.emit(f"[{self.config.bot_id}] Connected to {self.config.exchange}")

            # Run bot (this will block)
            self._run_bot_loop()

        except Exception as e:
            error_msg = f"Bot error: {str(e)}\n{traceback.format_exc()}"
            self.error_signal.emit(error_msg)
            self.log_signal.emit(f"[{self.config.bot_id}] ERROR: {str(e)}")

        finally:
            # Restore original stdout
            sys.stdout = old_stdout

            self.running = False
            if self.bot:
                try:
                    # Call appropriate disconnect method based on exchange
                    if self.config.exchange == 'MT5':
                        self.bot.disconnect_mt5()
                    else:  # Binance
                        self.bot.disconnect_exchange()
                except:
                    pass
            self.log_signal.emit(f"[{self.config.bot_id}] Bot stopped")

    def _init_mt5_bot(self):
        """Initialize MT5 bot"""
        from xauusd_bot.live_bot_mt5_fullauto import LiveBotMT5FullAuto

        self.bot = LiveBotMT5FullAuto(
            telegram_token=self.config.telegram_token if self.config.telegram_enabled else None,
            telegram_chat_id=self.config.telegram_chat_id if self.config.telegram_enabled else None,
            symbol=self.config.symbol,
            timeframe=self._get_mt5_timeframe(self.config.timeframe),
            check_interval=self._get_timeframe_seconds(self.config.timeframe),  # Match timeframe
            risk_percent=self.config.risk_percent,
            max_positions=self.config.max_positions,
            dry_run=self.config.dry_run,
            bot_id=self.config.bot_id,  # Pass bot_id from config
            use_database=bool(self.db),  # Enable database if available
            use_3_position_mode=self.config.use_3_position_mode,
            total_position_size=self.config.total_position_size,
            min_order_size=self.config.min_order_size,
            use_trailing_stops=self.config.use_trailing_stops,
            trailing_stop_pct=self.config.trailing_stop_pct,
            use_regime_based_sl=self.config.use_regime_based_sl,
            trend_sl=self.config.trend_sl,
            range_sl=self.config.range_sl,
            max_hold_bars=self.config.max_hold_bars
        )

        # Set TP levels
        self.bot.trend_tp1 = self.config.trend_tp1
        self.bot.trend_tp2 = self.config.trend_tp2
        self.bot.trend_tp3 = self.config.trend_tp3
        self.bot.range_tp1 = self.config.range_tp1
        self.bot.range_tp2 = self.config.range_tp2
        self.bot.range_tp3 = self.config.range_tp3
        
        # Set database if available
        if self.db:
            self.bot.db = self.db

    def _init_binance_bot(self):
        """Initialize Binance bot"""
        from crypto_bot.live_bot_binance_fullauto import LiveBotBinanceFullAuto

        self.bot = LiveBotBinanceFullAuto(
            telegram_token=self.config.telegram_token if self.config.telegram_enabled else None,
            telegram_chat_id=self.config.telegram_chat_id if self.config.telegram_enabled else None,
            symbol=self.config.symbol,
            timeframe=self.config.timeframe,
            risk_percent=self.config.risk_percent,
            max_positions=self.config.max_positions,
            dry_run=self.config.dry_run,
            testnet=self.config.testnet,
            api_key=self.config.api_key,
            api_secret=self.config.api_secret,
            bot_id=self.config.bot_id,  # Pass bot_id from config
            use_database=bool(self.db),  # Enable database if available
            use_3_position_mode=self.config.use_3_position_mode,
            total_position_size=self.config.total_position_size,
            min_order_size=self.config.min_order_size,
            use_trailing_stops=self.config.use_trailing_stops,
            trailing_stop_pct=self.config.trailing_stop_pct,
            use_regime_based_sl=self.config.use_regime_based_sl,
            trend_sl=self.config.trend_sl,
            range_sl=self.config.range_sl
        )

        # Set TP levels (in percent)
        self.bot.trend_tp1_pct = self.config.trend_tp1
        self.bot.trend_tp2_pct = self.config.trend_tp2
        self.bot.trend_tp3_pct = self.config.trend_tp3
        self.bot.range_tp1_pct = self.config.range_tp1
        self.bot.range_tp2_pct = self.config.range_tp2
        self.bot.range_tp3_pct = self.config.range_tp3
        
        # Set database if available
        if self.db:
            self.bot.db = self.db

    def _run_bot_loop(self):
        """Run bot loop with periodic status updates"""
        # Custom run loop to allow stopping
        iteration = 0

        # Wait until next candle close before starting
        self._wait_for_next_candle_close()

        while not self._stop_requested:
            iteration += 1

            try:
                # Log iteration check
                self.log_signal.emit(f"🔍 Checking for signals... (iteration #{iteration})")

                # Get market data and analyze
                signal = self.bot.analyze_market()

                # Update status
                status = self._get_bot_status()
                self.status_signal.emit(status)

                # Check if should trade
                if signal and not self._stop_requested:
                    # Signal found - opening position message will be shown by bot
                    success = self.bot.open_position(signal)
                    if success:
                        self.log_signal.emit(f"✅ Position opened successfully")

                        # Save DRY RUN trade to database
                        if self.config.dry_run and self.db:
                            self._save_dry_run_trade(signal)
                else:
                    # No signal found
                    if not self._stop_requested:
                        self.log_signal.emit(f"❌ No valid signal found")

                # Wait until next candle close (with position monitoring every 5 seconds)
                self._wait_for_next_candle_with_monitoring()

            except Exception as e:
                self.log_signal.emit(f"[{self.config.bot_id}] Error in loop: {str(e)}")
                time.sleep(60)  # Wait before retrying

    def _get_bot_status(self) -> BotStatus:
        """Get current bot status (with caching to reduce MT5 API calls)"""
        try:
            # Get account info from bot
            if self.config.exchange == 'MT5':
                import MetaTrader5 as mt5

                # Ensure MT5 connection before making API calls
                if not mt5_manager.ensure_connection():
                    # Return cached values or zeros if connection failed
                    balance = getattr(self, '_cached_balance', 0)
                    equity = getattr(self, '_cached_equity', 0)
                    pnl = equity - balance
                    pnl_pct = (pnl / balance * 100) if balance > 0 else 0
                    open_positions = getattr(self, '_cached_positions_count', 0)
                else:
                    # Cache account info for 60 seconds to reduce MT5 API calls
                    current_time = time.time()
                    if not hasattr(self, '_last_account_update') or (current_time - self._last_account_update) > 60:
                        account_info = mt5.account_info()
                        if account_info:
                            self._cached_balance = account_info.balance
                            self._cached_equity = account_info.equity
                            self._last_account_update = current_time
                        else:
                            self._cached_balance = self._cached_equity = 0
                            self._last_account_update = current_time

                    balance = getattr(self, '_cached_balance', 0)
                    equity = getattr(self, '_cached_equity', 0)
                    pnl = equity - balance
                    pnl_pct = (pnl / balance * 100) if balance > 0 else 0

                    # Get open positions (cache for 30 seconds)
                    if not hasattr(self, '_last_positions_update') or (current_time - self._last_positions_update) > 30:
                        positions = mt5.positions_get(symbol=self.config.symbol)
                        self._cached_positions_count = len(positions) if positions else 0
                        self._last_positions_update = current_time

                    open_positions = getattr(self, '_cached_positions_count', 0)

            else:  # Binance
                try:
                    balance_info = self.bot.exchange.fetch_balance()
                    balance = balance_info['USDT']['total']
                    equity = balance
                    pnl = 0  # TODO: calculate from positions
                    pnl_pct = 0

                    # Get open positions
                    positions = self.bot.exchange.fetch_positions([self.config.symbol])
                    open_positions = len([p for p in positions if float(p.get('contracts', 0)) > 0])
                except:
                    balance = equity = pnl = pnl_pct = 0
                    open_positions = 0

            return BotStatus(
                bot_id=self.config.bot_id,
                status='running',
                balance=balance,
                equity=equity,
                pnl_today=pnl,
                pnl_percent=pnl_pct,
                open_positions=open_positions,
                max_positions=self.config.max_positions,
                current_regime=getattr(self.bot, 'current_regime', None)
            )

        except Exception as e:
            return BotStatus(
                bot_id=self.config.bot_id,
                status='error',
                error_message=str(e)
            )

    def _get_mt5_timeframe(self, tf_str: str):
        """Convert timeframe string to MT5 constant"""
        import MetaTrader5 as mt5

        tf_map = {
            '1m': mt5.TIMEFRAME_M1,
            '5m': mt5.TIMEFRAME_M5,
            '15m': mt5.TIMEFRAME_M15,
            '30m': mt5.TIMEFRAME_M30,
            '1h': mt5.TIMEFRAME_H1,
            '4h': mt5.TIMEFRAME_H4,
            '1d': mt5.TIMEFRAME_D1,
        }
        return tf_map.get(tf_str.lower(), mt5.TIMEFRAME_H1)

    def _get_timeframe_seconds(self, tf_str: str) -> int:
        """Convert timeframe string to seconds"""
        tf_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400,
        }
        return tf_map.get(tf_str.lower(), 3600)  # Default to 1 hour

    def _calculate_seconds_until_next_candle_close(self) -> tuple:
        """
        Calculate seconds until next candle close with precise timing

        Returns:
            tuple: (seconds_until_close, next_close_datetime)
        """
        # Get timeframe in seconds
        timeframe_seconds = self._get_timeframe_seconds(self.config.timeframe)

        # Use cached NTP time offset to avoid slow NTP requests on every check
        # Only sync NTP time once per session, then use system time with offset
        if not hasattr(self, '_ntp_offset'):
            try:
                import ntplib
                from datetime import timezone
                ntp_client = ntplib.NTPClient()
                response = ntp_client.request('pool.ntp.org', version=3, timeout=2)
                system_time = time.time()
                ntp_time = response.tx_time
                self._ntp_offset = ntp_time - system_time
                self.log_signal.emit(f"[{self.config.bot_id}] NTP time synced (offset: {self._ntp_offset:.2f}s)")
            except Exception:
                # No NTP available, use system time directly
                self._ntp_offset = 0
                self.log_signal.emit(f"[{self.config.bot_id}] Using system time (NTP unavailable)")

        # Use system time with cached NTP offset for fast lookups
        now = datetime.fromtimestamp(time.time() + self._ntp_offset)
        current_timestamp = int(now.timestamp())

        # Calculate seconds since the last candle close
        seconds_since_close = current_timestamp % timeframe_seconds

        # Calculate seconds until next candle close
        seconds_until_close = timeframe_seconds - seconds_since_close

        # Start 5 seconds BEFORE the candle close to allow strategy processing time
        # This ensures signals are ready exactly when the candle closes
        seconds_until_close -= 5

        # Ensure we don't go negative
        if seconds_until_close < 0:
            seconds_until_close += timeframe_seconds

        # Calculate next close datetime
        next_close = datetime.fromtimestamp(current_timestamp + seconds_until_close + 5)  # +5 to show actual candle close time

        return seconds_until_close, next_close

    def _wait_for_next_candle_close(self):
        """Wait until the next candle close time to ensure signal checks happen only after candle closes"""
        seconds_until_close, next_close = self._calculate_seconds_until_next_candle_close()
        
        if seconds_until_close > 60:  # Only wait if more than 1 minute
            self.log_signal.emit(
                f"[{self.config.bot_id}] Waiting for next candle close at {next_close.strftime('%H:%M:%S')} "
                f"({seconds_until_close} seconds)..."
            )
            
            # Wait in small increments to allow stopping
            elapsed = 0
            while elapsed < seconds_until_close and not self._stop_requested:
                time.sleep(10)
                elapsed += 10
                
                # Update status periodically during wait
                if elapsed % 30 == 0:
                    status = self._get_bot_status()
                    self.status_signal.emit(status)
        else:
            self.log_signal.emit(
                f"[{self.config.bot_id}] Candle just closed, starting signal check immediately"
            )

    def _wait_for_next_candle_with_monitoring(self):
        """Wait until next candle close while monitoring positions every 10 seconds"""
        seconds_until_close, _ = self._calculate_seconds_until_next_candle_close()
        
        # Wait with position monitoring every 10 seconds (keeping original interval for stability)
        elapsed = 0
        while elapsed < seconds_until_close and not self._stop_requested:
            time.sleep(10)  # Check every 10 seconds for position monitoring
            elapsed += 10

            # Update status every 10 seconds for real-time monitoring
            status = self._get_bot_status()
            self.status_signal.emit(status)

            # ✅ Check TP/SL levels in real-time (every 10 seconds)
            if hasattr(self.bot, '_check_tp_sl_realtime'):
                try:
                    self.bot._check_tp_sl_realtime()
                except Exception as e:
                    self.log_signal.emit(f"[{self.config.bot_id}] Error checking TP/SL: {str(e)}")

            # ✅ Check for manually closed positions (sync with exchange)
            if hasattr(self.bot, '_sync_positions_with_exchange'):
                try:
                    self.bot._sync_positions_with_exchange()
                except Exception as e:
                    self.log_signal.emit(f"[{self.config.bot_id}] Error syncing positions: {str(e)}")

            # Update trailing stops for crypto bots
            if hasattr(self.bot, 'update_trailing_stops') and elapsed % 60 == 0:
                self.bot.update_trailing_stops()

    def _save_dry_run_trade(self, signal):
        """Save DRY RUN trade to database - supports 3-position mode"""
        try:
            from datetime import datetime
            import uuid
            
            # Get current timestamp for consistency
            now = datetime.now()
            
            # Calculate total position size
            if hasattr(self.bot, 'calculate_position_size'):
                total_position_size = self.bot.calculate_position_size(signal['entry'], signal['sl'])
            elif hasattr(self.bot, 'total_position_size') and self.bot.total_position_size:
                total_position_size = self.bot.total_position_size
            else:
                # Fallback estimate
                total_position_size = 0.01
            
            # Determine trade type
            trade_type = 'BUY' if signal['direction'] == 1 else 'SELL'
            
            # Check if 3-position mode is enabled
            use_3_pos = getattr(self.config, 'use_3_position_mode', False)
            
            if use_3_pos:
                # Save 3 separate position records
                group_id = str(uuid.uuid4())[:8]  # Short group ID
                positions_data = [
                    {'num': 1, 'size': total_position_size * 0.33, 'tp': signal.get('tp1', 0)},
                    {'num': 2, 'size': total_position_size * 0.33, 'tp': signal.get('tp2', 0)},
                    {'num': 3, 'size': total_position_size * 0.34, 'tp': signal.get('tp3', 0)}
                ]
                
                for pos_data in positions_data:
                    trade = TradeRecord(
                        trade_id=0,  # Will be assigned by database
                        bot_id=self.config.bot_id,
                        symbol=self.config.symbol,
                        order_id=f"DRY-{now.strftime('%Y%m%d%H%M%S')}-P{pos_data['num']}-{group_id}",
                        open_time=now,
                        trade_type=trade_type,
                        amount=pos_data['size'],
                        entry_price=signal['entry'],
                        stop_loss=signal['sl'],
                        take_profit=pos_data['tp'],
                        status='OPEN',
                        market_regime=signal.get('regime', 'UNKNOWN'),
                        comment=f"DRY RUN - Pos {pos_data['num']}/3 (Group: {group_id})"
                    )
                    self.db.add_trade(trade)
                
                self.log_signal.emit(f"[{self.config.bot_id}] DRY RUN: Saved 3 positions to database")
                print(f"💾 Saved DRY RUN trade to database: {trade_type} 3 positions (total: {total_position_size:.6f}) @ ${signal['entry']:.2f}")
            else:
                # Save single position record (original behavior)
                take_profit = signal.get('tp2') or signal.get('tp') or 0
                
                trade = TradeRecord(
                    trade_id=0,  # Will be assigned by database
                    bot_id=self.config.bot_id,
                    symbol=self.config.symbol,
                    order_id=f"DRY-{now.strftime('%Y%m%d%H%M%S')}",
                    open_time=now,
                    trade_type=trade_type,
                    amount=total_position_size,
                    entry_price=signal['entry'],
                    stop_loss=signal['sl'],
                    take_profit=take_profit,
                    status='OPEN',
                    market_regime=signal.get('regime', 'UNKNOWN'),
                    comment='DRY RUN'
                )
                
                self.db.add_trade(trade)
                self.log_signal.emit(f"[{self.config.bot_id}] DRY RUN trade saved to database")
                print(f"💾 Saved DRY RUN trade to database: {trade_type} {total_position_size} @ ${signal['entry']:.2f}")
            
        except Exception as e:
            self.log_signal.emit(f"[{self.config.bot_id}] Warning: Could not save DRY RUN trade: {str(e)}")
            print(f"⚠️  Could not save DRY RUN trade: {e}")

    def stop(self):
        """Request bot to stop"""
        self._stop_requested = True
        self.log_signal.emit(f"[{self.config.bot_id}] Stop requested...")
