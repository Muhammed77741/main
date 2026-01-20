"""
Database Manager for SQLite
"""
import sqlite3
import os
from typing import List, Optional
from datetime import datetime
from models import BotConfig, BotStatus, TradeRecord


class DatabaseManager:
    """Manage SQLite database for bot configs and trade history"""

    def __init__(self, db_path: str = "trading_app.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()

    @staticmethod
    def _parse_datetime(value) -> Optional[datetime]:
        """Parse a datetime value from SQLite, handling both strings and None
        
        Args:
            value: A datetime value that could be a string, datetime object, or None
            
        Returns:
            A datetime object or None
            
        Raises:
            ValueError: If the string cannot be parsed as a datetime
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError as e:
                raise ValueError(f"Failed to parse datetime string '{value}': {e}")
        return value

    def init_database(self):
        """Initialize database with tables"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()

        # Bot configurations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                api_key TEXT,
                api_secret TEXT,
                risk_percent REAL DEFAULT 2.0,
                max_positions INTEGER DEFAULT 3,
                timeframe TEXT DEFAULT '1h',
                strategy TEXT DEFAULT 'v3_adaptive',
                trend_tp1 REAL,
                trend_tp2 REAL,
                trend_tp3 REAL,
                range_tp1 REAL,
                range_tp2 REAL,
                range_tp3 REAL,
                total_position_size REAL,
                use_3_position_mode INTEGER DEFAULT 1,
                min_order_size REAL,
                use_trailing_stops INTEGER DEFAULT 1,
                trailing_stop_pct REAL DEFAULT 0.5,
                use_regime_based_sl INTEGER DEFAULT 0,
                trend_sl REAL DEFAULT 0.8,
                range_sl REAL DEFAULT 0.6,
                telegram_enabled INTEGER DEFAULT 0,
                telegram_token TEXT,
                telegram_chat_id TEXT,
                dry_run INTEGER DEFAULT 1,
                testnet INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Bot status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'stopped',
                balance REAL DEFAULT 0.0,
                equity REAL DEFAULT 0.0,
                pnl_today REAL DEFAULT 0.0,
                pnl_percent REAL DEFAULT 0.0,
                open_positions INTEGER DEFAULT 0,
                max_positions INTEGER DEFAULT 3,
                total_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                profit_factor REAL DEFAULT 0.0,
                current_regime TEXT,
                last_signal_time TIMESTAMP,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
            )
        """)

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT NOT NULL,
                symbol TEXT,
                order_id TEXT,
                open_time TIMESTAMP NOT NULL,
                close_time TIMESTAMP,
                duration_hours REAL,
                trade_type TEXT NOT NULL,
                amount REAL NOT NULL,
                entry_price REAL NOT NULL,
                close_price REAL,
                stop_loss REAL,
                take_profit REAL,
                profit REAL,
                profit_percent REAL,
                status TEXT DEFAULT 'OPEN',
                market_regime TEXT,
                comment TEXT,
                FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
            )
        """)

        # Position Groups table (CRITICAL FIX #4: Persist state across restarts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS position_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT UNIQUE NOT NULL,
                bot_id TEXT NOT NULL,
                tp1_hit INTEGER DEFAULT 0,
                entry_price REAL NOT NULL,
                max_price REAL NOT NULL,
                min_price REAL NOT NULL,
                trade_type TEXT NOT NULL,
                tp1_close_price REAL,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
            )
        """)
        
        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_position_groups_group_id 
            ON position_groups(group_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_position_groups_bot_status 
            ON position_groups(bot_id, status)
        """)

        # App logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                bot_id TEXT,
                message TEXT NOT NULL
            )
        """)

        # Migrate existing tables - add symbol column if it doesn't exist
        try:
            cursor.execute("PRAGMA table_info(trades)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'symbol' not in columns:
                print("📊 Migrating trades table: adding symbol column...")
                cursor.execute("ALTER TABLE trades ADD COLUMN symbol TEXT")
                print("✅ Migration complete")
        except Exception as e:
            print(f"⚠️  Migration warning: {e}")

        # Migrate trades table - add 3-position mode columns
        try:
            cursor.execute("PRAGMA table_info(trades)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'position_group_id' not in columns:
                print("📊 Migrating trades table: adding position_group_id column...")
                cursor.execute("ALTER TABLE trades ADD COLUMN position_group_id TEXT")
                print("✅ position_group_id column added")

            if 'position_num' not in columns:
                print("📊 Migrating trades table: adding position_num column...")
                cursor.execute("ALTER TABLE trades ADD COLUMN position_num INTEGER DEFAULT 0")
                print("✅ position_num column added")

            if 'trailing_stop_active' not in columns:
                print("📊 Migrating trades table: adding trailing_stop_active column...")
                cursor.execute("ALTER TABLE trades ADD COLUMN trailing_stop_active INTEGER DEFAULT 0")
                print("✅ trailing_stop_active column added")

        except Exception as e:
            print(f"⚠️  3-position migration warning: {e}")

        # Migrate bot_configs table - add Phase 2 position sizing columns
        try:
            cursor.execute("PRAGMA table_info(bot_configs)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'total_position_size' not in columns:
                print("📊 Migrating bot_configs: adding total_position_size column...")
                cursor.execute("ALTER TABLE bot_configs ADD COLUMN total_position_size REAL")
                print("✅ total_position_size column added")

            if 'use_3_position_mode' not in columns:
                print("📊 Migrating bot_configs: adding use_3_position_mode column...")
                cursor.execute("ALTER TABLE bot_configs ADD COLUMN use_3_position_mode INTEGER DEFAULT 1")
                print("✅ use_3_position_mode column added")
            else:
                # Update existing records where use_3_position_mode is 0 to default to 1
                print("📊 Updating existing bot_configs: setting use_3_position_mode to 1...")
                cursor.execute("UPDATE bot_configs SET use_3_position_mode = 1 WHERE use_3_position_mode = 0")
                updated_rows = cursor.rowcount
                if updated_rows > 0:
                    print(f"✅ Updated {updated_rows} bot config(s) to enable 3-position mode")


            if 'min_order_size' not in columns:
                print("📊 Migrating bot_configs: adding min_order_size column...")
                cursor.execute("ALTER TABLE bot_configs ADD COLUMN min_order_size REAL")
                print("✅ min_order_size column added")

            if 'trailing_stop_pct' not in columns:
                print("📊 Migrating bot_configs: adding trailing_stop_pct column...")
                cursor.execute("ALTER TABLE bot_configs ADD COLUMN trailing_stop_pct REAL DEFAULT 0.5")
                print("✅ trailing_stop_pct column added")

            if 'use_trailing_stops' not in columns:
                print("📊 Migrating bot_configs: adding use_trailing_stops column...")
                cursor.execute("ALTER TABLE bot_configs ADD COLUMN use_trailing_stops INTEGER DEFAULT 1")
                print("✅ use_trailing_stops column added")

            if 'use_regime_based_sl' not in columns:
                print("📊 Migrating bot_configs: adding use_regime_based_sl column...")
                cursor.execute("ALTER TABLE bot_configs ADD COLUMN use_regime_based_sl INTEGER DEFAULT 0")
                print("✅ use_regime_based_sl column added")

            if 'trend_sl' not in columns:
                print("📊 Migrating bot_configs: adding trend_sl column...")
                cursor.execute("ALTER TABLE bot_configs ADD COLUMN trend_sl REAL DEFAULT 0.8")
                print("✅ trend_sl column added")

            if 'range_sl' not in columns:
                print("📊 Migrating bot_configs: adding range_sl column...")
                cursor.execute("ALTER TABLE bot_configs ADD COLUMN range_sl REAL DEFAULT 0.6")
                print("✅ range_sl column added")


        except Exception as e:
            print(f"⚠️  Phase 2 config migration warning: {e}")

        self.conn.commit()

    def save_config(self, config: BotConfig):
        """Save or update bot configuration"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO bot_configs (
                bot_id, name, symbol, exchange, api_key, api_secret,
                risk_percent, max_positions, timeframe, strategy,
                trend_tp1, trend_tp2, trend_tp3,
                range_tp1, range_tp2, range_tp3,
                total_position_size, use_3_position_mode, min_order_size,
                use_trailing_stops, trailing_stop_pct,
                use_regime_based_sl, trend_sl, range_sl,
                telegram_enabled, telegram_token, telegram_chat_id,
                dry_run, testnet, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            config.bot_id, config.name, config.symbol, config.exchange,
            config.api_key, config.api_secret,
            config.risk_percent, config.max_positions, config.timeframe, config.strategy,
            config.trend_tp1, config.trend_tp2, config.trend_tp3,
            config.range_tp1, config.range_tp2, config.range_tp3,
            getattr(config, 'total_position_size', None),
            1 if getattr(config, 'use_3_position_mode', True) else 0,
            getattr(config, 'min_order_size', None),
            1 if getattr(config, 'use_trailing_stops', True) else 0,
            getattr(config, 'trailing_stop_pct', 0.5),
            1 if getattr(config, 'use_regime_based_sl', False) else 0,
            getattr(config, 'trend_sl', 0.8),
            getattr(config, 'range_sl', 0.6),
            1 if config.telegram_enabled else 0,
            config.telegram_token, config.telegram_chat_id,
            1 if config.dry_run else 0,
            1 if config.testnet else 0,
            datetime.now()
        ))

        self.conn.commit()

    def load_config(self, bot_id: str) -> Optional[BotConfig]:
        """Load bot configuration"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bot_configs WHERE bot_id = ?", (bot_id,))
        row = cursor.fetchone()

        if row:
            # Check which columns exist (for backward compatibility)
            columns = row.keys()

            return BotConfig(
                bot_id=row['bot_id'],
                name=row['name'],
                symbol=row['symbol'],
                exchange=row['exchange'],
                api_key=row['api_key'],
                api_secret=row['api_secret'],
                risk_percent=row['risk_percent'],
                max_positions=row['max_positions'],
                timeframe=row['timeframe'],
                total_position_size=row['total_position_size'] if 'total_position_size' in columns else None,
                use_3_position_mode=bool(row['use_3_position_mode']) if 'use_3_position_mode' in columns else True,
                min_order_size=row['min_order_size'] if 'min_order_size' in columns else None,
                use_trailing_stops=bool(row['use_trailing_stops']) if 'use_trailing_stops' in columns else True,
                trailing_stop_pct=row['trailing_stop_pct'] if 'trailing_stop_pct' in columns else 0.5,
                use_regime_based_sl=bool(row['use_regime_based_sl']) if 'use_regime_based_sl' in columns else False,
                trend_sl=row['trend_sl'] if 'trend_sl' in columns else 0.8,
                range_sl=row['range_sl'] if 'range_sl' in columns else 0.6,
                strategy=row['strategy'],
                trend_tp1=row['trend_tp1'],
                trend_tp2=row['trend_tp2'],
                trend_tp3=row['trend_tp3'],
                range_tp1=row['range_tp1'],
                range_tp2=row['range_tp2'],
                range_tp3=row['range_tp3'],
                telegram_enabled=bool(row['telegram_enabled']),
                telegram_token=row['telegram_token'],
                telegram_chat_id=row['telegram_chat_id'],
                dry_run=bool(row['dry_run']),
                testnet=bool(row['testnet'])
            )
        return None

    def load_all_configs(self) -> List[BotConfig]:
        """Load all bot configurations"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT bot_id FROM bot_configs")
        bot_ids = [row['bot_id'] for row in cursor.fetchall()]
        return [self.load_config(bot_id) for bot_id in bot_ids]

    def update_status(self, status: BotStatus):
        """Update bot status"""
        # Check if connection is still valid
        if not self.conn:
            print(f"⚠️  Warning: Database connection closed, skipping status update for {status.bot_id}")
            return

        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO bot_status (
                    bot_id, status, balance, equity, pnl_today, pnl_percent,
                    open_positions, max_positions, total_trades, win_rate, profit_factor,
                    current_regime, last_signal_time, last_update, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                status.bot_id, status.status, status.balance, status.equity,
                status.pnl_today, status.pnl_percent, status.open_positions, status.max_positions,
                status.total_trades, status.win_rate, status.profit_factor,
                status.current_regime, status.last_signal_time, datetime.now(), status.error_message
            ))

            self.conn.commit()
        except sqlite3.ProgrammingError as e:
            print(f"⚠️  Warning: Database error during status update: {e}")
        except Exception as e:
            print(f"⚠️  Warning: Unexpected error during status update: {e}")

    def get_status(self, bot_id: str) -> Optional[BotStatus]:
        """Get bot status"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bot_status WHERE bot_id = ?", (bot_id,))
        row = cursor.fetchone()

        if row:
            return BotStatus(
                bot_id=row['bot_id'],
                status=row['status'],
                balance=row['balance'],
                equity=row['equity'],
                pnl_today=row['pnl_today'],
                pnl_percent=row['pnl_percent'],
                open_positions=row['open_positions'],
                max_positions=row['max_positions'],
                total_trades=row['total_trades'],
                win_rate=row['win_rate'],
                profit_factor=row['profit_factor'],
                current_regime=row['current_regime'],
                last_signal_time=self._parse_datetime(row['last_signal_time']),
                last_update=self._parse_datetime(row['last_update']),
                error_message=row['error_message']
            )
        return None

    def add_trade(self, trade: TradeRecord):
        """Add a trade record"""
        # Check if connection is still valid
        if not self.conn:
            print(f"⚠️  Warning: Database connection closed, skipping trade record for {trade.bot_id}")
            return

        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO trades (
                    bot_id, symbol, order_id, open_time, close_time, duration_hours,
                    trade_type, amount, entry_price, close_price,
                    stop_loss, take_profit, profit, profit_percent,
                    status, market_regime, comment, position_group_id, position_num, trailing_stop_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.bot_id, trade.symbol, trade.order_id, trade.open_time, trade.close_time, trade.duration_hours,
                trade.trade_type, trade.amount, trade.entry_price, trade.close_price,
                trade.stop_loss, trade.take_profit, trade.profit, trade.profit_percent,
                trade.status, trade.market_regime, trade.comment,
                trade.position_group_id, trade.position_num, 1 if trade.trailing_stop_active else 0
            ))

            self.conn.commit()
        except sqlite3.ProgrammingError as e:
            print(f"⚠️  Warning: Database error during trade add: {e}")
        except Exception as e:
            print(f"⚠️  Warning: Unexpected error during trade add: {e}")

    def get_trades(self, bot_id: str, limit: int = 100) -> List[TradeRecord]:
        """Get recent trades for a bot"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM trades
            WHERE bot_id = ?
            ORDER BY open_time DESC
            LIMIT ?
        """, (bot_id, limit))

        trades = []
        for row in cursor.fetchall():
            columns = row.keys()
            trades.append(TradeRecord(
                trade_id=row['id'],
                bot_id=row['bot_id'],
                symbol=row['symbol'] if 'symbol' in columns else None,
                order_id=row['order_id'],
                open_time=self._parse_datetime(row['open_time']),
                close_time=self._parse_datetime(row['close_time']),
                duration_hours=row['duration_hours'],
                trade_type=row['trade_type'],
                amount=row['amount'],
                entry_price=row['entry_price'],
                close_price=row['close_price'],
                stop_loss=row['stop_loss'],
                take_profit=row['take_profit'],
                profit=row['profit'],
                profit_percent=row['profit_percent'],
                status=row['status'],
                market_regime=row['market_regime'],
                comment=row['comment'],
                position_group_id=row['position_group_id'] if 'position_group_id' in columns else None,
                position_num=row['position_num'] if 'position_num' in columns else 0,
                trailing_stop_active=bool(row['trailing_stop_active']) if 'trailing_stop_active' in columns else False
            ))

        return trades

    def get_open_trades(self, bot_id: str) -> List[TradeRecord]:
        """Get currently open trades for a bot"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM trades
            WHERE bot_id = ? AND status = 'OPEN'
            ORDER BY open_time DESC
        """, (bot_id,))

        trades = []
        for row in cursor.fetchall():
            columns = row.keys()
            trades.append(TradeRecord(
                trade_id=row['id'],
                bot_id=row['bot_id'],
                symbol=row['symbol'] if 'symbol' in columns else None,
                order_id=row['order_id'],
                open_time=self._parse_datetime(row['open_time']),
                close_time=self._parse_datetime(row['close_time']),
                duration_hours=row['duration_hours'],
                trade_type=row['trade_type'],
                amount=row['amount'],
                entry_price=row['entry_price'],
                close_price=row['close_price'],
                stop_loss=row['stop_loss'],
                take_profit=row['take_profit'],
                profit=row['profit'],
                profit_percent=row['profit_percent'],
                status=row['status'],
                market_regime=row['market_regime'],
                comment=row['comment'],
                position_group_id=row['position_group_id'] if 'position_group_id' in columns else None,
                position_num=row['position_num'] if 'position_num' in columns else 0,
                trailing_stop_active=bool(row['trailing_stop_active']) if 'trailing_stop_active' in columns else False
            ))

        return trades

    def update_trade(self, trade: TradeRecord):
        """Update an existing trade record"""
        # Check if connection is still valid
        if not self.conn:
            print(f"⚠️  Warning: Database connection closed, skipping trade update for {trade.bot_id}")
            return

        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                UPDATE trades SET
                    close_time = ?,
                    duration_hours = ?,
                    close_price = ?,
                    profit = ?,
                    profit_percent = ?,
                    status = ?,
                    comment = ?,
                    stop_loss = ?,
                    take_profit = ?,
                    trailing_stop_active = ?
                WHERE bot_id = ? AND order_id = ?
            """, (
                trade.close_time, trade.duration_hours, trade.close_price,
                trade.profit, trade.profit_percent, trade.status, trade.comment,
                trade.stop_loss, trade.take_profit, 1 if trade.trailing_stop_active else 0,
                trade.bot_id, trade.order_id
            ))

            self.conn.commit()
        except sqlite3.ProgrammingError as e:
            print(f"⚠️  Warning: Database error during trade update: {e}")
        except Exception as e:
            print(f"⚠️  Warning: Unexpected error during trade update: {e}")

    def log(self, level: str, message: str, bot_id: str = None):
        """Add a log entry"""
        # Check if connection is still valid
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO app_logs (level, bot_id, message)
                VALUES (?, ?, ?)
            """, (level, bot_id, message))
            self.conn.commit()
        except sqlite3.ProgrammingError:
            pass  # Silently skip if database is closed
        except Exception:
            pass  # Silently skip other errors during logging

    # Position Groups methods (CRITICAL FIX #4)
    def save_position_group(self, group):
        """Save or update a position group"""
        from models.position_group import PositionGroup
        
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO position_groups (
                group_id, bot_id, tp1_hit, entry_price, max_price, min_price,
                trade_type, tp1_close_price, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            group.group_id,
            group.bot_id,
            1 if group.tp1_hit else 0,
            group.entry_price,
            group.max_price,
            group.min_price,
            group.trade_type,
            group.tp1_close_price,
            group.status,
            datetime.now()
        ))
        self.conn.commit()

    def get_position_group(self, group_id: str):
        """Get a position group by ID"""
        from models.position_group import PositionGroup
        
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM position_groups WHERE group_id = ?
        """, (group_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return PositionGroup(
            group_id=row['group_id'],
            bot_id=row['bot_id'],
            tp1_hit=bool(row['tp1_hit']),
            entry_price=row['entry_price'],
            max_price=row['max_price'],
            min_price=row['min_price'],
            trade_type=row['trade_type'],
            tp1_close_price=row['tp1_close_price'],
            status=row['status'],
            created_at=self._parse_datetime(row['created_at']),
            updated_at=self._parse_datetime(row['updated_at'])
        )

    def get_active_position_groups(self, bot_id: str):
        """Get all active position groups for a bot"""
        from models.position_group import PositionGroup
        
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM position_groups 
            WHERE bot_id = ? AND status = 'ACTIVE'
            ORDER BY created_at DESC
        """, (bot_id,))
        
        groups = []
        for row in cursor.fetchall():
            groups.append(PositionGroup(
                group_id=row['group_id'],
                bot_id=row['bot_id'],
                tp1_hit=bool(row['tp1_hit']),
                entry_price=row['entry_price'],
                max_price=row['max_price'],
                min_price=row['min_price'],
                trade_type=row['trade_type'],
                tp1_close_price=row['tp1_close_price'],
                status=row['status'],
                created_at=self._parse_datetime(row['created_at']),
                updated_at=self._parse_datetime(row['updated_at'])
            ))
        
        return groups

    def update_position_group(self, group):
        """Update an existing position group"""
        self.save_position_group(group)  # INSERT OR REPLACE handles update

    def close_position_group(self, group_id: str):
        """Mark a position group as closed"""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE position_groups 
            SET status = 'CLOSED', updated_at = ?
            WHERE group_id = ?
        """, (datetime.now(), group_id))
        self.conn.commit()

    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                self.conn.close()
            except Exception as e:
                print(f"⚠️  Warning: Error closing database: {e}")
            finally:
                self.conn = None
