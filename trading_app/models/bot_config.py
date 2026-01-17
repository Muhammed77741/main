"""
Bot Configuration Model
"""
from dataclasses import dataclass, asdict
from typing import Optional
import json


@dataclass
class BotConfig:
    """Configuration for a trading bot"""

    # Bot identification
    bot_id: str  # 'xauusd', 'btc', 'eth'
    name: str
    symbol: str
    exchange: str  # 'MT5', 'Binance'

    # API credentials (will be encrypted)
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

    # Trading parameters
    risk_percent: float = 2.0
    max_positions: int = 3
    timeframe: str = '1h'

    # Position sizing (Phase 2)
    total_position_size: Optional[float] = None  # Total position size in base currency
    use_3_position_mode: bool = False  # Enable 3-position trading mode
    min_order_size: Optional[float] = None  # Minimum order size for exchange

    # Strategy parameters
    strategy: str = 'v3_adaptive'

    # TP levels for TREND mode
    trend_tp1: float = 1.5
    trend_tp2: float = 2.75
    trend_tp3: float = 4.5

    # TP levels for RANGE mode
    range_tp1: float = 1.0
    range_tp2: float = 1.75
    range_tp3: float = 2.5

    # Telegram settings
    telegram_enabled: bool = False
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Bot mode
    dry_run: bool = True
    testnet: bool = True

    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self):
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str):
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def default_xauusd(cls):
        """Create default XAUUSD config"""
        return cls(
            bot_id='xauusd',
            name='XAUUSD (Gold)',
            symbol='XAUUSD',
            exchange='MT5',
            trend_tp1=30,  # points
            trend_tp2=55,
            trend_tp3=90,
            range_tp1=20,
            range_tp2=35,
            range_tp3=50,
        )

    @classmethod
    def default_btc(cls):
        """Create default BTC config"""
        return cls(
            bot_id='btc',
            name='Bitcoin',
            symbol='BTC/USDT',
            exchange='Binance',
            trend_tp1=1.5,  # percent
            trend_tp2=2.75,
            trend_tp3=4.5,
            range_tp1=1.0,
            range_tp2=1.75,
            range_tp3=2.5,
        )

    @classmethod
    def default_eth(cls):
        """Create default ETH config"""
        return cls(
            bot_id='eth',
            name='Ethereum',
            symbol='ETH/USDT',
            exchange='Binance',
            trend_tp1=1.5,  # percent
            trend_tp2=2.75,
            trend_tp3=4.5,
            range_tp1=1.0,
            range_tp2=1.75,
            range_tp3=2.5,
        )
