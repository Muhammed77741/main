"""
Trade Record Model
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TradeRecord:
    """Record of a completed trade"""

    # Identification (required fields)
    trade_id: int
    bot_id: str
    order_id: str

    # Timing (required)
    open_time: datetime

    # Trade details (required)
    trade_type: str  # 'BUY' or 'SELL'
    
    # Symbol (optional but recommended)
    symbol: Optional[str] = None

    # Optional fields with defaults
    # Timing
    close_time: Optional[datetime] = None
    duration_hours: Optional[float] = None

    # Trade details
    amount: float = 0.0
    entry_price: float = 0.0
    close_price: Optional[float] = None

    # Risk management
    stop_loss: float = 0.0
    take_profit: float = 0.0

    # Results
    profit: Optional[float] = None
    profit_percent: Optional[float] = None
    status: str = 'OPEN'  # 'OPEN', 'TP', 'SL', 'CLOSED'

    # Market context
    market_regime: Optional[str] = None  # 'TREND' or 'RANGE'
    comment: Optional[str] = None

    # Phase 2: 3-Position Mode
    position_group_id: Optional[str] = None  # Groups 3 positions from same signal
    position_num: int = 0  # Position number (1, 2, or 3)
