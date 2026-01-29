"""
Position Group Model
Stores state for 3-position groups to persist across bot restarts
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PositionGroup:
    """State of a 3-position group"""

    # Identification (required fields)
    group_id: str  # UUID of the position group
    bot_id: str    # Bot that owns this group
    
    # State tracking (required)
    tp1_hit: bool  # Whether TP1 has been reached
    entry_price: float  # Entry price for the group
    
    # Price tracking for trailing stop calculation
    max_price: float  # Maximum price reached (for BUY positions)
    min_price: float  # Minimum price reached (for SELL positions)
    
    # Timing
    created_at: datetime
    updated_at: datetime
    
    # Trade type
    trade_type: str  # 'BUY' or 'SELL'
    
    # Optional fields
    group_counter: Optional[int] = None  # Counter for magic number generation (0-99)
    tp1_close_price: Optional[float] = None  # Price at which TP1 was closed
    status: str = 'ACTIVE'  # 'ACTIVE', 'CLOSED'
