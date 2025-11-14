# Crypto Futures Trading Bot 🚀

**Advanced Automated Futures Trading System for Delta Exchange**

A high-performance trading bot with multi-indicator confluence strategy, designed for leveraged futures trading on Delta Exchange. Features intelligent risk management, trailing stops, and real-time Telegram notifications.

---

## 🌟 Features

### Trading Capabilities
- ✅ **Futures Trading**: Full support for leveraged futures contracts (1x-100x)
- ✅ **Advanced Strategy**: Multi-indicator confluence system with 70%+ signal threshold
- ✅ **Smart Risk Management**: Position sizing, stop-loss, take-profit automation
- ✅ **Trailing Stops**: Dynamic profit protection with configurable activation
- ✅ **Paper Trading**: Test strategies without risking real capital
- ✅ **Backtesting**: Validate strategies on historical data

### Technical Analysis (100 Point Scoring System)
- **Trend Analysis** (35 points): EMA alignment, ADX, Supertrend
- **Momentum Analysis** (30 points): RSI, MACD, Stochastic
- **Volume Analysis** (15 points): Volume spikes, OBV trends
- **Market Structure** (10 points): Support/resistance, pivot points
- **Volatility Analysis** (5 points): Bollinger Bands, ATR
- **Sentiment Analysis** (5 points): Funding rates, market sentiment

### Risk Management
- Per-trade risk: 3% of capital (configurable)
- Risk:Reward ratio: 1:2.5 minimum
- Max daily trades: 5 high-quality setups
- Trailing stop: Activates at 0.8:1 RR, trails at 40%
- Emergency stop-loss: 15% circuit breaker

---

## 📋 Requirements

### System Requirements
- Python 3.9 or higher
- Windows/Linux/Mac OS
- Stable internet connection
- 4GB RAM minimum

### API Requirements
- **Delta Exchange** API key & secret (required)
- **Telegram Bot** token & chat ID (optional, for notifications)
- **Sonar Perplexity** API key (optional, for sentiment analysis)

---

## 🚀 Quick Start

### 1. Installation

```powershell
# Clone or download the repository
cd chatbot

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file with your API credentials:

```env
# Delta Exchange API
DELTA_API_KEY=your_delta_api_key
DELTA_API_SECRET=your_delta_api_secret

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Sonar API (Optional)
SONAR_API_KEY=your_sonar_api_key

# Trading Settings
INITIAL_CAPITAL=5.0
LEVERAGE=10
RISK_PERCENTAGE=3.0
RISK_REWARD_RATIO=2.5
SIGNAL_THRESHOLD=70.0
MAX_DAILY_TRADES=5

# Trading Pair & Timeframe
TRADING_PAIR=ETHUSD
TIMEFRAME=15m
```

### 3. Run the Bot

#### Paper Trading (Recommended First)
```powershell
python main.py
# Select: 2. PAPER - Paper trading simulation
```

#### Backtesting
```powershell
python main.py
# Select: 3. BACKTEST - Historical backtest
```

#### Live Trading
```powershell
python main.py
# Select: 1. LIVE - Live trading with real money
# Confirm with: YES
```

---

## ⚙️ Configuration Guide

### Key Parameters

#### Leverage Settings
- **1x-5x**: Conservative, lower risk
- **10x-20x**: Moderate, balanced approach
- **25x-50x**: Aggressive, higher risk
- **50x-100x**: Very aggressive, expert only

⚠️ **Higher leverage = Higher risk & reward**

#### Risk Settings
```env
RISK_PERCENTAGE=3.0      # 3% risk per trade (safer with leverage)
RISK_REWARD_RATIO=2.5    # 1:2.5 minimum (2.5x profit per 1x risk)
SIGNAL_THRESHOLD=70.0    # 70% confidence minimum
MAX_DAILY_TRADES=5       # Maximum trades per day
```

#### Trading Pairs (Delta Exchange)
```env
TRADING_PAIR=ETHUSD      # Ethereum futures
TRADING_PAIR=BTCUSD      # Bitcoin futures
TRADING_PAIR=SOLUSD      # Solana futures
# ... and more
```

#### Timeframes
```env
TIMEFRAME=5m    # 5 minutes (scalping)
TIMEFRAME=15m   # 15 minutes (recommended)
TIMEFRAME=1h    # 1 hour (swing trading)
TIMEFRAME=4h    # 4 hours (position trading)
```

---

## 📊 Strategy Explanation

### Signal Generation
The bot uses a **100-point scoring system** across 6 categories:

1. **Trend (35%)**: Are we in a strong trend?
   - EMA alignment (9, 21, 50)
   - ADX strength
   - Supertrend direction

2. **Momentum (30%)**: Is momentum in our favor?
   - RSI (neutral zone preferred)
   - MACD histogram
   - Stochastic crossovers

3. **Volume (15%)**: Is there strong volume?
   - Volume spikes (1.1x+ average)
   - OBV trend

4. **Structure (10%)**: Are we at good S/R levels?
   - Pivot points
   - Higher highs/lows pattern

5. **Volatility (5%)**: Favorable conditions?
   - Bollinger Bands position
   - BB expansion/contraction

6. **Sentiment (5%)**: Market sentiment check
   - Funding rates
   - External sentiment data

### Entry Rules
- **BUY Signal**: Confidence ≥ 70% + All filters passed
- **SELL Signal**: Confidence ≤ -70% + All filters passed
- **HOLD**: Everything else

### Exit Rules
1. **Stop Loss**: Hit predefined SL price
2. **Take Profit**: Hit predefined TP price (1:2.5 RR)
3. **Trailing Stop**: Activates at 0.8:1 RR, trails 40% below price
4. **Emergency Stop**: 15% account loss circuit breaker

---

## 📈 Performance Optimization

### Strategy Optimizations Applied
- ✅ Faster EMAs (9/21/50 instead of 20/50/200)
- ✅ Adjusted RSI thresholds (35/65 instead of 30/70)
- ✅ Increased trend & momentum weight
- ✅ Earlier trailing stop activation (0.8 vs 1.0 RR)
- ✅ Tighter trailing distance (40% vs 50%)
- ✅ Lower signal threshold (70% vs 75%)
- ✅ More flexible filters (10% volume vs 20%)
- ✅ More daily trade opportunities (5 vs 3)

### Result
- **More signals**: Reduced threshold from 75% to 70%
- **Faster entries**: Optimized indicators for 15m timeframe
- **Better exits**: Earlier trailing stop activation
- **More opportunities**: Increased daily trade limit

---

## 📁 Project Structure

```
chatbot/
├── main.py                     # Main entry point
├── config.py                   # Configuration & settings
├── strategy.py                 # Trading strategy logic
├── delta_exchange.py           # Delta Exchange API
├── data_manager_delta.py       # Market data management
├── trade_executor_delta.py     # Trade execution
├── risk_manager.py             # Risk & position sizing
├── paper_trading.py            # Paper trading simulator
├── backtester.py               # Backtesting engine
├── telegram_bot.py             # Telegram notifications
├── monitor.py                  # Dashboard & monitoring
├── logger.py                   # Logging system
├── database.py                 # Trade history DB
├── requirements.txt            # Dependencies
├── .env                        # API credentials (create this)
└── README.md                   # This file
```

---

## 🔔 Telegram Notifications

The bot sends real-time alerts:
- 🚀 **Startup notifications**
- 🎯 **Signal alerts** (BUY/SELL with confidence)
- 📊 **Trade entries** (position details)
- 💰 **Trade exits** (P&L results)
- ⚠️ **Error alerts**
- 🛑 **Emergency stops**

---

## 🛡️ Risk Warnings

⚠️ **IMPORTANT DISCLAIMERS:**

1. **Leverage Risk**: Futures trading with leverage can result in rapid losses
2. **Market Risk**: Crypto markets are highly volatile
3. **Bot Risk**: Automated trading carries technical risks
4. **Capital Risk**: Only trade with capital you can afford to lose
5. **No Guarantees**: Past performance does not guarantee future results

**Recommended:**
- Start with paper trading
- Use low leverage (5-10x) initially
- Set small position sizes
- Monitor the bot regularly
- Have emergency stop-loss in place

---

## 🐛 Troubleshooting

### Common Issues

**1. API Connection Failed**
- Check your Delta Exchange API credentials
- Ensure API keys have trading permissions
- Verify internet connection

**2. No Signals Generated**
- Market conditions may not meet 70% threshold
- Check if filters are too restrictive
- Adjust `SIGNAL_THRESHOLD` if needed

**3. Position Size Too Small**
- Increase `INITIAL_CAPITAL`
- Adjust `RISK_PERCENTAGE`
- Check leverage settings

**4. Import Errors**
- Run: `pip install -r requirements.txt`
- Ensure Python 3.9+

---

## 📞 Support

For issues, questions, or contributions:
- Check the logs: `trading_bot.log`
- Review configuration: `config.py`
- Test connection: Run in PAPER mode first

---

## 📜 License

This project is for educational purposes. Use at your own risk.

---

## 🎯 Next Steps

1. ✅ Test in paper trading mode
2. ✅ Analyze backtesting results
3. ✅ Start with low leverage (5-10x)
4. ✅ Monitor performance daily
5. ✅ Adjust parameters based on results

**Happy Trading! 🚀📈**

