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
    use_3_position_mode: bool = True  # Enable 3-position trading mode (TP1, TP2, TP3)
    min_order_size: Optional[float] = None  # Minimum order size for exchange
    use_trailing_stops: bool = True  # Enable trailing stops for positions 2 and 3
    trailing_stop_pct: float = 0.5  # Trailing stop percentage (0.5 = 50% retracement from max profit)

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

    # Regime-based SL settings
    use_regime_based_sl: bool = False  # Use fixed regime-based SL instead of strategy SL
    trend_sl: float = 0.8  # TREND mode SL: 0.8% for crypto, 16 points for XAUUSD
    range_sl: float = 0.6  # RANGE mode SL: 0.6% for crypto, 12 points for XAUUSD

    # Position timeout settings
    max_hold_bars: int = 100  # Close position after N bars if TP/SL not hit (default: 100 like backtest)

    # Telegram settings
    telegram_enabled: bool = False
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Bot mode
    dry_run: bool = False  # Always disabled, user cannot change
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
            trend_sl=16,  # points
            range_sl=12,  # points
        )

    @classmethod
    def default_eurusd(cls):
        """Create default EURUSD config"""
        return cls(
            bot_id='eurusd',
            name='EURUSD',
            symbol='EURUSD',
            exchange='MT5',
            trend_tp1=30,  # points
            trend_tp2=55,
            trend_tp3=90,
            range_tp1=20,
            range_tp2=35,
            range_tp3=50,
            trend_sl=16,  # points
            range_sl=12,  # points
        )

    @classmethod
    def default_gbpusd(cls):
        """Create default GBPUSD config"""
        return cls(
            bot_id='gbpusd',
            name='GBPUSD',
            symbol='GBPUSD',
            exchange='MT5',
            trend_tp1=35,  # points
            trend_tp2=60,
            trend_tp3=100,
            range_tp1=25,
            range_tp2=40,
            range_tp3=60,
            trend_sl=18,  # points
            range_sl=14,  # points
        )

    @classmethod
    def default_usdjpy(cls):
        """Create default USDJPY config"""
        return cls(
            bot_id='usdjpy',
            name='USDJPY',
            symbol='USDJPY',
            exchange='MT5',
            trend_tp1=30,  # points (для JPY - pips * 100)
            trend_tp2=55,
            trend_tp3=90,
            range_tp1=20,
            range_tp2=35,
            range_tp3=50,
            trend_sl=16,  # points
            range_sl=12,  # points
        )

    @classmethod
    def custom_mt5(cls, symbol: str, name: str = None):
        """Create custom MT5 pair config"""
        if name is None:
            name = symbol

        bot_id = symbol.lower().replace('/', '_')

        return cls(
            bot_id=bot_id,
            name=name,
            symbol=symbol,
            exchange='MT5',
            trend_tp1=30,  # points (adjust based on pair)
            trend_tp2=55,
            trend_tp3=90,
            range_tp1=20,
            range_tp2=35,
            range_tp3=50,
            trend_sl=16,  # points
            range_sl=12,  # points
        )

    # Binance configs disabled
    # @classmethod
    # def default_btc(cls):
    #     """Create default BTC config"""
    #     return cls(
    #         bot_id='btc',
    #         name='Bitcoin',
    #         symbol='BTC/USDT',
    #         exchange='Binance',
    #         trend_tp1=1.5,  # percent
    #         trend_tp2=2.75,
    #         trend_tp3=4.5,
    #         range_tp1=1.0,
    #         range_tp2=1.75,
    #         range_tp3=2.5,
    #     )

    # @classmethod
    # def default_eth(cls):
    #     """Create default ETH config"""
    #     return cls(
    #         bot_id='eth',
    #         name='Ethereum',
    #         symbol='ETH/USDT',
    #         exchange='Binance',
    #         trend_tp1=1.5,  # percent
    #         trend_tp2=2.75,
    #         trend_tp3=4.5,
    #         range_tp1=1.0,
    #         range_tp2=1.75,
    #         range_tp3=2.5,
    #     )
