"""
Logging module for Trading Bot
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama for Windows
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)

class TradingLogger:
    """Trading bot logger with file and console handlers"""

    def __init__(self, name='TradingBot', log_file='trading_bot.log', level='INFO'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        self.logger.handlers = []  # Clear existing handlers

        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        """Get logger instance"""
        return self.logger

    def log_trade(self, trade_type, pair, price, size, reason=''):
        """Log trade execution"""
        self.logger.info(
            f"🔔 TRADE {trade_type.upper()} | {pair} | "
            f"Price: ${price:.2f} | Size: {size:.4f} | {reason}"
        )

    def log_signal(self, signal_type, pair, score, details=''):
        """Log trading signal"""
        emoji = "📈" if signal_type == "BUY" else "📉" if signal_type == "SELL" else "⏸️"
        self.logger.info(
            f"{emoji} SIGNAL {signal_type} | {pair} | "
            f"Score: {score:.1f}% | {details}"
        )

    def log_performance(self, trades, wins, pnl, win_rate):
        """Log performance metrics"""
        self.logger.info(
            f"📊 PERFORMANCE | Trades: {trades} | Wins: {wins} | "
            f"Win Rate: {win_rate:.1f}% | P&L: ${pnl:.2f}"
        )

    def log_error(self, error_msg, exception=None):
        """Log error with optional exception"""
        if exception:
            self.logger.error(f"❌ ERROR: {error_msg}", exc_info=True)
        else:
            self.logger.error(f"❌ ERROR: {error_msg}")

    def log_warning(self, warning_msg):
        """Log warning"""
        self.logger.warning(f"⚠️ WARNING: {warning_msg}")

    def log_info(self, info_msg):
        """Log info"""
        self.logger.info(f"ℹ️ {info_msg}")

    def log_debug(self, debug_msg):
        """Log debug"""
        self.logger.debug(f"🔍 {debug_msg}")

# Create global logger instance
trading_logger = TradingLogger()
logger = trading_logger.get_logger()

