"""
Bot Manager - manages all trading bots
"""
from typing import Dict, Optional
from PySide6.QtCore import QObject, Signal
from models import BotConfig, BotStatus
from database import DatabaseManager
from core.bot_thread import BotThread


class BotManager(QObject):
    """Manages all trading bots"""

    # Signals
    bot_started = Signal(str)  # bot_id
    bot_stopped = Signal(str)  # bot_id
    bot_status_updated = Signal(str, BotStatus)  # bot_id, status
    bot_log = Signal(str, str)  # bot_id, message
    bot_error = Signal(str, str)  # bot_id, error

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.bots: Dict[str, BotThread] = {}  # bot_id -> BotThread
        self.configs: Dict[str, BotConfig] = {}  # bot_id -> BotConfig

        # Load configs from database
        self._load_configs()

    def _load_configs(self):
        """Load bot configurations from database"""
        configs = self.db.load_all_configs()

        if not configs:
            # Create default configs if none exist
            self._create_default_configs()
        else:
            for config in configs:
                self.configs[config.bot_id] = config

    def _create_default_configs(self):
        """Create default configurations for all bots (MT5 only)"""
        default_configs = [
            BotConfig.default_xauusd(),
            BotConfig.default_eurusd(),
            BotConfig.default_gbpusd(),
            BotConfig.default_usdjpy(),
            # Binance configs disabled
            # BotConfig.default_btc(),
            # BotConfig.default_eth(),
        ]

        for config in default_configs:
            self.db.save_config(config)
            self.configs[config.bot_id] = config

    def get_config(self, bot_id: str) -> Optional[BotConfig]:
        """Get bot configuration"""
        return self.configs.get(bot_id)

    def update_config(self, config: BotConfig):
        """Update bot configuration"""
        self.configs[config.bot_id] = config
        self.db.save_config(config)

    def start_bot(self, bot_id: str) -> bool:
        """Start a bot"""
        if bot_id in self.bots and self.bots[bot_id].isRunning():
            self.bot_log.emit(bot_id, "Bot is already running")
            return False

        config = self.configs.get(bot_id)
        if not config:
            self.bot_error.emit(bot_id, "Configuration not found")
            return False

        # Validate configuration
        if config.exchange == 'Binance':
            if not config.api_key or not config.api_secret:
                self.bot_error.emit(bot_id, "Binance API keys not configured")
                return False

        # Create bot thread
        bot_thread = BotThread(config, self.db)

        # Connect signals
        bot_thread.log_signal.connect(lambda msg: self.bot_log.emit(bot_id, msg))
        bot_thread.status_signal.connect(lambda status: self._handle_status_update(bot_id, status))
        bot_thread.error_signal.connect(lambda error: self.bot_error.emit(bot_id, error))
        bot_thread.finished.connect(lambda: self._handle_bot_finished(bot_id))

        # Start thread
        self.bots[bot_id] = bot_thread
        bot_thread.start()

        self.bot_started.emit(bot_id)
        self.bot_log.emit(bot_id, "Bot starting...")

        return True

    def stop_bot(self, bot_id: str) -> bool:
        """Stop a bot"""
        if bot_id not in self.bots:
            return False

        bot_thread = self.bots[bot_id]
        if not bot_thread.isRunning():
            return False

        # Request stop
        bot_thread.stop()

        # Wait for thread to finish (max 10 seconds)
        bot_thread.wait(10000)

        if bot_thread.isRunning():
            # Force terminate if still running
            bot_thread.terminate()
            bot_thread.wait()

        return True

    def is_bot_running(self, bot_id: str) -> bool:
        """Check if bot is running"""
        if bot_id not in self.bots:
            return False
        return self.bots[bot_id].isRunning()

    def get_status(self, bot_id: str) -> Optional[BotStatus]:
        """Get bot status from database"""
        return self.db.get_status(bot_id)

    def get_all_bot_ids(self):
        """Get list of all bot IDs"""
        return list(self.configs.keys())

    def _handle_status_update(self, bot_id: str, status: BotStatus):
        """Handle status update from bot"""
        # Save to database
        self.db.update_status(status)

        # Emit signal
        self.bot_status_updated.emit(bot_id, status)

    def _handle_bot_finished(self, bot_id: str):
        """Handle bot thread finished"""
        # Update status in database
        status = BotStatus(bot_id=bot_id, status='stopped')
        self.db.update_status(status)

        self.bot_stopped.emit(bot_id)
        self.bot_log.emit(bot_id, "Bot stopped")

    def stop_all_bots(self):
        """Stop all running bots"""
        for bot_id in list(self.bots.keys()):
            if self.is_bot_running(bot_id):
                self.stop_bot(bot_id)
