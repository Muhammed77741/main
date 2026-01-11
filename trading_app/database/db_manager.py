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
                telegram_enabled, telegram_token, telegram_chat_id,
                dry_run, testnet, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            config.bot_id, config.name, config.symbol, config.exchange,
            config.api_key, config.api_secret,
            config.risk_percent, config.max_positions, config.timeframe, config.strategy,
            config.trend_tp1, config.trend_tp2, config.trend_tp3,
            config.range_tp1, config.range_tp2, config.range_tp3,
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
                last_signal_time=row['last_signal_time'],
                last_update=row['last_update'],
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
                    bot_id, order_id, open_time, close_time, duration_hours,
                    trade_type, amount, entry_price, close_price,
                    stop_loss, take_profit, profit, profit_percent,
                    status, market_regime, comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.bot_id, trade.order_id, trade.open_time, trade.close_time, trade.duration_hours,
                trade.trade_type, trade.amount, trade.entry_price, trade.close_price,
                trade.stop_loss, trade.take_profit, trade.profit, trade.profit_percent,
                trade.status, trade.market_regime, trade.comment
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
            trades.append(TradeRecord(
                trade_id=row['id'],
                bot_id=row['bot_id'],
                order_id=row['order_id'],
                open_time=row['open_time'],
                close_time=row['close_time'],
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
                comment=row['comment']
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
            trades.append(TradeRecord(
                trade_id=row['id'],
                bot_id=row['bot_id'],
                order_id=row['order_id'],
                open_time=row['open_time'],
                close_time=row['close_time'],
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
                comment=row['comment']
            ))

        return trades

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

    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                self.conn.close()
            except Exception as e:
                print(f"⚠️  Warning: Error closing database: {e}")
            finally:
                self.conn = None
