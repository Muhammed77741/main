"""
Trade Record Model
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TradeRecord:
    """Record of a completed trade"""

    # Identification
    trade_id: int
    bot_id: str
    order_id: str

    # Timing
    open_time: datetime
    close_time: Optional[datetime] = None
    duration_hours: Optional[float] = None

    # Trade details
    trade_type: str  # 'BUY' or 'SELL'
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
