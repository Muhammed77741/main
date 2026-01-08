"""
Bot Status Model
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BotStatus:
    """Runtime status of a bot"""

    bot_id: str
    status: str  # 'stopped', 'running', 'error'

    # Account info
    balance: float = 0.0
    equity: float = 0.0
    pnl_today: float = 0.0
    pnl_percent: float = 0.0

    # Position info
    open_positions: int = 0
    max_positions: int = 3

    # Statistics
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0

    # Market info
    current_regime: Optional[str] = None  # 'TREND' or 'RANGE'
    last_signal_time: Optional[datetime] = None
    last_update: datetime = None

    # Error info
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now()
