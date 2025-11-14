"""
Database module for storing trades, signals, and performance data
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json
from logger import logger

class TradingDatabase:
    """SQLite database for trading bot data"""

    def __init__(self, db_path='trading_bot.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.init_database()

    def connect(self):
        """Connect to database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def init_database(self):
        """Initialize database schema"""
        if not self.connect():
            return

        try:
            # Trades table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    size REAL NOT NULL,
                    leverage INTEGER NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    pnl REAL,
                    pnl_percentage REAL,
                    fees REAL,
                    status TEXT NOT NULL,
                    exit_reason TEXT,
                    signal_score REAL,
                    mode TEXT NOT NULL,
                    exit_timestamp TEXT
                )
            ''')

            # Signals table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    total_score REAL NOT NULL,
                    trend_score REAL,
                    momentum_score REAL,
                    volume_score REAL,
                    structure_score REAL,
                    volatility_score REAL,
                    sentiment_score REAL,
                    price REAL NOT NULL,
                    details TEXT,
                    executed INTEGER DEFAULT 0
                )
            ''')

            # Performance table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    avg_win REAL DEFAULT 0,
                    avg_loss REAL DEFAULT 0,
                    profit_factor REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    sharpe_ratio REAL DEFAULT 0,
                    capital REAL NOT NULL
                )
            ''')

            # API logs table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    api_name TEXT NOT NULL,
                    endpoint TEXT,
                    status TEXT NOT NULL,
                    response_time REAL,
                    error_message TEXT
                )
            ''')

            self.conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
        finally:
            self.close()

    def insert_trade(self, trade_data: Dict) -> Optional[int]:
        """Insert new trade"""
        if not self.connect():
            return None

        try:
            self.cursor.execute('''
                INSERT INTO trades (
                    timestamp, pair, side, entry_price, size, leverage,
                    stop_loss, take_profit, status, signal_score, mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data['timestamp'],
                trade_data['pair'],
                trade_data['side'],
                trade_data['entry_price'],
                trade_data['size'],
                trade_data['leverage'],
                trade_data['stop_loss'],
                trade_data['take_profit'],
                'OPEN',
                trade_data.get('signal_score', 0),
                trade_data.get('mode', 'LIVE')
            ))
            self.conn.commit()
            trade_id = self.cursor.lastrowid
            logger.info(f"Trade inserted with ID: {trade_id}")
            return trade_id
        except Exception as e:
            logger.error(f"Failed to insert trade: {e}")
            return None
        finally:
            self.close()

    def update_trade(self, trade_id: int, update_data: Dict) -> bool:
        """Update existing trade"""
        if not self.connect():
            return False

        try:
            fields = ', '.join([f"{k} = ?" for k in update_data.keys()])
            values = list(update_data.values()) + [trade_id]

            self.cursor.execute(f'''
                UPDATE trades SET {fields} WHERE id = ?
            ''', values)
            self.conn.commit()
            logger.info(f"Trade {trade_id} updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update trade: {e}")
            return False
        finally:
            self.close()

    def insert_signal(self, signal_data: Dict) -> Optional[int]:
        """Insert trading signal"""
        if not self.connect():
            return None

        try:
            self.cursor.execute('''
                INSERT INTO signals (
                    timestamp, pair, signal_type, total_score,
                    trend_score, momentum_score, volume_score,
                    structure_score, volatility_score, sentiment_score,
                    price, details, executed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data['timestamp'],
                signal_data['pair'],
                signal_data['signal_type'],
                signal_data['total_score'],
                signal_data.get('trend_score', 0),
                signal_data.get('momentum_score', 0),
                signal_data.get('volume_score', 0),
                signal_data.get('structure_score', 0),
                signal_data.get('volatility_score', 0),
                signal_data.get('sentiment_score', 0),
                signal_data['price'],
                signal_data.get('details', ''),
                signal_data.get('executed', 0)
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to insert signal: {e}")
            return None
        finally:
            self.close()

    def update_daily_performance(self, date: str, performance_data: Dict) -> bool:
        """Update daily performance metrics"""
        if not self.connect():
            return False

        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO performance (
                    date, total_trades, winning_trades, losing_trades,
                    total_pnl, win_rate, avg_win, avg_loss,
                    profit_factor, max_drawdown, sharpe_ratio, capital
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date,
                performance_data['total_trades'],
                performance_data['winning_trades'],
                performance_data['losing_trades'],
                performance_data['total_pnl'],
                performance_data['win_rate'],
                performance_data['avg_win'],
                performance_data['avg_loss'],
                performance_data['profit_factor'],
                performance_data['max_drawdown'],
                performance_data['sharpe_ratio'],
                performance_data['capital']
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update performance: {e}")
            return False
        finally:
            self.close()

    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        if not self.connect():
            return []

        try:
            self.cursor.execute('''
                SELECT * FROM trades WHERE status = 'OPEN'
                ORDER BY timestamp DESC
            ''')
            trades = [dict(row) for row in self.cursor.fetchall()]
            return trades
        except Exception as e:
            logger.error(f"Failed to get open trades: {e}")
            return []
        finally:
            self.close()

    def get_daily_trades_count(self, date: str) -> int:
        """Get number of trades for specific date"""
        if not self.connect():
            return 0

        try:
            self.cursor.execute('''
                SELECT COUNT(*) as count FROM trades
                WHERE DATE(timestamp) = ? AND status != 'CANCELLED'
            ''', (date,))
            result = self.cursor.fetchone()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to get daily trades count: {e}")
            return 0
        finally:
            self.close()

    def get_performance_stats(self, days: int = 30) -> Dict:
        """Get performance statistics for last N days"""
        if not self.connect():
            return {}

        try:
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                    SUM(pnl) as total_pnl,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade
                FROM trades
                WHERE status = 'CLOSED'
                AND DATE(timestamp) >= DATE('now', '-' || ? || ' days')
            ''', (days,))

            row = self.cursor.fetchone()
            if row:
                stats = dict(row)
                stats['win_rate'] = (stats['wins'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
                stats['profit_factor'] = abs(stats['avg_win'] / stats['avg_loss']) if stats['avg_loss'] else 0
                return stats
            return {}
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {}
        finally:
            self.close()

    def log_api_call(self, api_name: str, endpoint: str, status: str,
                     response_time: float = 0, error_message: str = '') -> bool:
        """Log API call"""
        if not self.connect():
            return False

        try:
            self.cursor.execute('''
                INSERT INTO api_logs (
                    timestamp, api_name, endpoint, status, response_time, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                api_name,
                endpoint,
                status,
                response_time,
                error_message
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to log API call: {e}")
            return False
        finally:
            self.close()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

# Create global database instance
db = TradingDatabase()

