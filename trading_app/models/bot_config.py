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

    # Position sizing mode: 'auto' (based on risk_percent) or 'fixed' (fixed size)
    position_size_mode: str = 'auto'
    fixed_position_size: float = 0.1  # For 'fixed' mode: lots for XAUUSD, crypto amount for BTC/ETH

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

    def validate(self):
        """
        Validate configuration parameters

        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []

        # TP levels must be in ascending order
        if not (self.trend_tp1 < self.trend_tp2 < self.trend_tp3):
            errors.append(f"TREND TP levels must be ascending: TP1 ({self.trend_tp1}) < TP2 ({self.trend_tp2}) < TP3 ({self.trend_tp3})")

        if not (self.range_tp1 < self.range_tp2 < self.range_tp3):
            errors.append(f"RANGE TP levels must be ascending: TP1 ({self.range_tp1}) < TP2 ({self.range_tp2}) < TP3 ({self.range_tp3})")

        # TP levels must be positive
        if any(tp <= 0 for tp in [self.trend_tp1, self.trend_tp2, self.trend_tp3,
                                    self.range_tp1, self.range_tp2, self.range_tp3]):
            errors.append("All TP levels must be positive")

        # Risk must be reasonable
        if self.risk_percent < 0.1 or self.risk_percent > 10.0:
            errors.append(f"Risk per trade should be between 0.1% and 10% (got: {self.risk_percent}%)")

        # Max positions must be reasonable
        if self.max_positions < 1 or self.max_positions > 50:
            errors.append(f"Max positions should be between 1 and 50 (got: {self.max_positions})")

        # Symbol must not be empty
        if not self.symbol or self.symbol.strip() == '':
            errors.append("Symbol cannot be empty")

        # Position size mode validation
        if self.position_size_mode not in ['auto', 'fixed']:
            errors.append(f"Position size mode must be 'auto' or 'fixed' (got: {self.position_size_mode})")

        # Fixed position size validation
        if self.position_size_mode == 'fixed':
            if self.fixed_position_size <= 0:
                errors.append(f"Fixed position size must be positive (got: {self.fixed_position_size})")

            # Check reasonable ranges based on exchange
            if self.exchange == 'MT5':  # XAUUSD
                if self.fixed_position_size < 0.01 or self.fixed_position_size > 100:
                    errors.append(f"For MT5/XAUUSD, position size should be 0.01-100 lots (got: {self.fixed_position_size})")
            elif self.exchange == 'Binance':  # Crypto
                if self.symbol.startswith('BTC') and (self.fixed_position_size < 0.0001 or self.fixed_position_size > 10):
                    errors.append(f"For BTC, position size should be 0.0001-10 BTC (got: {self.fixed_position_size})")
                elif self.symbol.startswith('ETH') and (self.fixed_position_size < 0.001 or self.fixed_position_size > 100):
                    errors.append(f"For ETH, position size should be 0.001-100 ETH (got: {self.fixed_position_size})")

        return (len(errors) == 0, errors)

    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self):
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        config = cls(**data)
        # Validate after creation
        is_valid, errors = config.validate()
        if not is_valid:
            raise ValueError(f"Invalid configuration:\n" + "\n".join(f"  - {err}" for err in errors))
        return config

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
            position_size_mode='auto',  # Auto by default
            fixed_position_size=0.1,    # 0.1 lot if switched to fixed
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
            position_size_mode='auto',  # Auto by default
            fixed_position_size=0.01,   # 0.01 BTC if switched to fixed (~$900 at $90k BTC)
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
            position_size_mode='auto',  # Auto by default
            fixed_position_size=0.1,    # 0.1 ETH if switched to fixed (~$330 at $3.3k ETH)
            trend_tp1=1.5,  # percent
            trend_tp2=2.75,
            trend_tp3=4.5,
            range_tp1=1.0,
            range_tp2=1.75,
            range_tp3=2.5,
        )
