"""
Configuration module for CoinDCX Crypto Futures Trading Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Main configuration class"""

    # API Credentials
    COINDCX_API_KEY = os.getenv('COINDCX_API_KEY', '')
    COINDCX_API_SECRET = os.getenv('COINDCX_API_SECRET', '')
    DELTA_API_KEY = os.getenv('DELTA_API_KEY', '')
    DELTA_API_SECRET = os.getenv('DELTA_API_SECRET', '')
    SONAR_API_KEY = os.getenv('SONAR_API_KEY', '')

    # Telegram Bot - Multiple Accounts Support
    # Primary account (original config)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Additional Telegram accounts (comma-separated)
    # Format: "token1,token2,token3"
    TELEGRAM_BOT_TOKENS_EXTRA = os.getenv('TELEGRAM_BOT_TOKENS_EXTRA', '')
    # Format: "chatid1,chatid2,chatid3"
    TELEGRAM_CHAT_IDS_EXTRA = os.getenv('TELEGRAM_CHAT_IDS_EXTRA', '')

    # Trading Parameters (FUTURES TRADING WITH LEVERAGE)
    INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', '5.0'))
    RISK_PERCENTAGE = float(os.getenv('RISK_PERCENTAGE', '3.0'))  # 3% risk per trade (safer with leverage)
    RISK_REWARD_RATIO = float(os.getenv('RISK_REWARD_RATIO', '2.5'))  # 1:2.5 RR (better for futures)
    LEVERAGE = int(os.getenv('LEVERAGE', '10'))  # 10x leverage for futures (adjustable 1-100x)
    MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', '5'))  # Max 5 quality trades/day
    SIGNAL_THRESHOLD = float(os.getenv('SIGNAL_THRESHOLD', '70.0'))  # 70% confidence minimum

    # Trading Pair & Timeframe
    TRADING_PAIR = os.getenv('TRADING_PAIR', 'ETHUSD')  # Delta Exchange format: ETHUSD, BTCUSD, etc.
    TIMEFRAME = os.getenv('TIMEFRAME', '15m')
    
    # Multiple Timeframe Analysis (NEW)
    USE_MULTIPLE_TIMEFRAMES = True  # Enable higher timeframe confirmation
    TIMEFRAME_HIGHER_1 = '1h'  # First higher timeframe for trend confirmation
    TIMEFRAME_HIGHER_2 = '4h'  # Second higher timeframe for overall direction

    # Exchange Configuration
    EXCHANGE_NAME = 'delta'
    EXCHANGE_TYPE = 'futures'  # Delta Exchange - futures trading with leverage

    # Fee Structure (Delta Exchange Futures)
    MAKER_FEE = 0.0005  # 0.05%
    TAKER_FEE = 0.0015  # 0.15%
    SLIPPAGE = 0.0005   # 0.05%

    # Strategy Parameters (Optimized for Futures Trading)
    STRATEGY_WEIGHTS = {
        'trend': 35,      # Trend indicators weight (increased for stronger trend following)
        'momentum': 30,   # Momentum indicators weight (increased for faster entries)
        'volume': 15,     # Volume analysis weight
        'structure': 10,  # Market structure weight
        'volatility': 5,  # Volatility indicators weight (reduced)
        'sentiment': 5    # Market sentiment weight
    }

    # Indicator Settings (Optimized for 15m Futures Trading)
    EMA_FAST = 9        # Faster EMA for quicker signals
    EMA_MEDIUM = 21     # Standard EMA
    EMA_SLOW = 50       # Reduced from 200 for faster trend detection
    RSI_PERIOD = 14
    RSI_OVERSOLD = 35   # Adjusted for futures volatility
    RSI_OVERBOUGHT = 65 # Adjusted for futures volatility
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    ADX_PERIOD = 14
    ADX_THRESHOLD = 25
    STOCH_K = 14
    STOCH_D = 3
    ATR_PERIOD = 14
    BB_PERIOD = 20
    BB_STD = 2
    VOLUME_PERIOD = 20

    # Filter Settings (Optimized)
    MIN_VOLUME_MULTIPLIER = 1.1  # Minimum 10% above average (less restrictive)
    MAX_FUNDING_RATE = 0.015     # Maximum 1.5% funding rate (more flexible)
    LOW_VOLUME_HOURS = [0, 1, 2, 3, 4]  # UTC hours to avoid (reduced)

    # Trailing Stop (Optimized for Futures)
    TRAILING_STOP_ACTIVATION = 0.8  # Activate at 0.8:1 RR (earlier activation)
    TRAILING_STOP_DISTANCE = 0.4    # Trail at 40% of initial risk (tighter)
    
    # Market Regime Detection (NEW)
    USE_MARKET_REGIME_FILTER = True  # Only trade in trending markets
    REGIME_ADX_THRESHOLD = 20  # Minimum ADX for trending market
    
    # Partial Take Profits (NEW)
    USE_PARTIAL_TP = True  # Enable partial profit taking
    PARTIAL_TP_PERCENT = 50  # Close 50% at first TP level
    PARTIAL_TP_LEVEL = 1.0  # First TP at 1:1 RR (break-even)
    
    # Smart Position Sizing (NEW)
    USE_DYNAMIC_RISK = True  # Adjust position size based on signal strength
    RISK_LOW_CONFIDENCE = 2.0  # 2% risk for 70-75% signals
    RISK_MEDIUM_CONFIDENCE = 3.0  # 3% risk for 75-80% signals
    RISK_HIGH_CONFIDENCE = 4.0  # 4% risk for 80%+ signals

    # Risk Management
    MAX_DRAWDOWN_LIMIT = None  # No limit as per user request
    EMERGENCY_STOP_LOSS = 0.15  # 15% circuit breaker for safety

    # Backtesting
    BACKTEST_START_DATE = '2024-05-01'  # 6 months historical data
    BACKTEST_END_DATE = '2024-11-13'

    # Database & Logging (Cloud-ready with production mode detection)
    PRODUCTION = os.getenv('PRODUCTION', 'false').lower() == 'true'
    DB_PATH = '/data/trading_bot.db' if PRODUCTION else 'trading_bot.db'
    LOG_FILE = '/data/trading_bot.log' if PRODUCTION else 'trading_bot.log'
    LOG_LEVEL = 'INFO'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # API Settings
    API_TIMEOUT = 30
    API_RETRY_COUNT = 3
    API_RETRY_DELAY = 2
    WEBSOCKET_RECONNECT_DELAY = 5

    # Data Caching
    CACHE_DURATION = 300  # 5 minutes cache for API optimization

    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []

        if not cls.DELTA_API_KEY or not cls.DELTA_API_SECRET:
            errors.append("Delta Exchange API credentials not set")

        if not cls.SONAR_API_KEY:
            errors.append("Sonar Perplexity API key not set")

        if cls.TELEGRAM_BOT_TOKEN and not cls.TELEGRAM_CHAT_ID:
            errors.append("Telegram chat ID not set")
        
        # Validate extra Telegram accounts
        extra_tokens = [t.strip() for t in cls.TELEGRAM_BOT_TOKENS_EXTRA.split(',') if t.strip()]
        extra_chat_ids = [c.strip() for c in cls.TELEGRAM_CHAT_IDS_EXTRA.split(',') if c.strip()]
        
        if len(extra_tokens) != len(extra_chat_ids):
            errors.append("Number of extra Telegram tokens and chat IDs must match")

        if cls.INITIAL_CAPITAL <= 0:
            errors.append("Initial capital must be positive")

        if cls.RISK_PERCENTAGE <= 0 or cls.RISK_PERCENTAGE > 100:
            errors.append("Risk percentage must be between 0 and 100")

        if cls.LEVERAGE < 1:
            errors.append("Leverage must be at least 1")

        return errors

    @classmethod
    def display(cls):
        """Display current configuration"""
        print("\n" + "="*60)
        print("TRADING BOT CONFIGURATION")
        print("="*60)
        print(f"Trading Pair: {cls.TRADING_PAIR}")
        print(f"Timeframe: {cls.TIMEFRAME}")
        print(f"Initial Capital: ${cls.INITIAL_CAPITAL}")
        print(f"Leverage: {cls.LEVERAGE}x")
        print(f"Position Size: ${cls.INITIAL_CAPITAL * cls.LEVERAGE}")
        print(f"Risk Per Trade: {cls.RISK_PERCENTAGE}% (${cls.INITIAL_CAPITAL * cls.RISK_PERCENTAGE / 100})")
        print(f"Risk:Reward Ratio: 1:{cls.RISK_REWARD_RATIO}")
        print(f"Max Daily Trades: {cls.MAX_DAILY_TRADES}")
        print(f"Signal Threshold: {cls.SIGNAL_THRESHOLD}%")
        print(f"Trailing Stop: Active at 1:1 RR")
        print("="*60 + "\n")

# Create global config instance
config = Config()

