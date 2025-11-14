"""
Risk Manager - Handles position sizing, risk limits, and capital management
"""
from datetime import datetime, date
from typing import Dict, Tuple, Optional
from config import config
from logger import logger
from database import db

class RiskManager:
    """Manages trading risk and capital"""

    def __init__(self):
        self.current_capital = config.INITIAL_CAPITAL
        self.initial_capital = config.INITIAL_CAPITAL
        self.daily_trades = 0
        self.daily_trade_date = None
        self.peak_capital = config.INITIAL_CAPITAL
        self.current_drawdown = 0.0
        self.positions = {}
        
        logger.info(f"✅ Risk Manager initialized | Capital: ${self.current_capital}")

    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                                side: str) -> Tuple[float, float]:
        """
        Calculate position size based on risk percentage
        Returns: (position_size, risk_amount)
        """
        # Calculate risk amount in USD
        risk_amount = self.current_capital * (config.RISK_PERCENTAGE / 100)
        
        # Calculate stop distance in percentage
        if side == 'BUY':
            stop_distance_pct = abs(entry_price - stop_loss) / entry_price
        else:  # SELL
            stop_distance_pct = abs(stop_loss - entry_price) / entry_price
        
        # Calculate position size with leverage
        # Position Value = Capital * Leverage
        max_position_value = self.current_capital * config.LEVERAGE
        
        # Position Size = Risk Amount / Stop Distance
        if stop_distance_pct > 0:
            position_value = risk_amount / stop_distance_pct
            # Cap at max position value
            position_value = min(position_value, max_position_value)
        else:
            position_value = max_position_value
        
        # Convert to position size in base currency
        position_size = position_value / entry_price
        
        return position_size, risk_amount

    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """Calculate stop loss price based on risk percentage"""
        risk_pct = config.RISK_PERCENTAGE / 100 / config.LEVERAGE
        
        if side == 'BUY':
            stop_loss = entry_price * (1 - risk_pct)
        else:  # SELL
            stop_loss = entry_price * (1 + risk_pct)
        
        return stop_loss

    def calculate_take_profit(self, entry_price: float, stop_loss: float, 
                             side: str) -> float:
        """Calculate take profit based on risk:reward ratio"""
        risk_distance = abs(entry_price - stop_loss)
        reward_distance = risk_distance * config.RISK_REWARD_RATIO
        
        if side == 'BUY':
            take_profit = entry_price + reward_distance
        else:  # SELL
            take_profit = entry_price - reward_distance
        
        return take_profit

    def get_dynamic_risk_percentage(self, confidence: float) -> float:
        """Calculate risk percentage based on signal confidence (NEW)"""
        if not config.USE_DYNAMIC_RISK:
            return config.RISK_PERCENTAGE
        
        # Smart position sizing based on confidence
        if confidence >= 80:
            return config.RISK_HIGH_CONFIDENCE  # 4% for strong signals
        elif confidence >= 75:
            return config.RISK_MEDIUM_CONFIDENCE  # 3% for medium signals
        else:
            return config.RISK_LOW_CONFIDENCE  # 2% for weaker signals
    
    def validate_trade(self, signal: Dict, market_data: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate if trade should be executed
        Returns: (can_trade, reason, trade_params)
        """
        # Check if signal confidence meets threshold
        if signal['confidence'] < config.SIGNAL_THRESHOLD:
            return False, f"Signal confidence {signal['confidence']:.1f}% below threshold", None
        
        # Check daily trade limit
        today = date.today()
        if self.daily_trade_date != today:
            self.daily_trades = 0
            self.daily_trade_date = today
        
        if self.daily_trades >= config.MAX_DAILY_TRADES:
            return False, f"Daily trade limit reached ({config.MAX_DAILY_TRADES})", None
        
        # Check if we have capital
        if self.current_capital <= 0:
            return False, "Insufficient capital", None
        
        # Calculate trade parameters
        entry_price = signal['price']
        side = signal['signal']  # BUY or SELL
        confidence = signal['confidence']
        
        # Get dynamic risk percentage (NEW)
        dynamic_risk = self.get_dynamic_risk_percentage(confidence)
        
        # Calculate stop loss and take profit
        stop_loss = self.calculate_stop_loss(entry_price, side)
        take_profit = self.calculate_take_profit(entry_price, stop_loss, side)
        
        # Calculate position size with dynamic risk
        risk_amount = self.current_capital * (dynamic_risk / 100)
        stop_distance_pct = abs(entry_price - stop_loss) / entry_price
        
        max_position_value = self.current_capital * config.LEVERAGE
        
        if stop_distance_pct > 0:
            position_value = risk_amount / stop_distance_pct
            position_value = min(position_value, max_position_value)
        else:
            position_value = max_position_value
        
        position_size = position_value / entry_price
        
        # Validate position size
        min_position = 0.001  # Minimum position size
        if position_size < min_position:
            return False, f"Position size too small: {position_size:.6f}", None
        
        # Calculate partial take profit levels (NEW)
        partial_tp = None
        if config.USE_PARTIAL_TP:
            risk_distance = abs(entry_price - stop_loss)
            if side == 'BUY':
                partial_tp = entry_price + (risk_distance * config.PARTIAL_TP_LEVEL)
            else:
                partial_tp = entry_price - (risk_distance * config.PARTIAL_TP_LEVEL)
        
        # Create trade parameters
        trade_params = {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'partial_tp': partial_tp,
            'partial_tp_percent': config.PARTIAL_TP_PERCENT if config.USE_PARTIAL_TP else 0,
            'position_size': position_size,
            'risk_amount': risk_amount,
            'dynamic_risk': dynamic_risk,
            'leverage': config.LEVERAGE,
            'side': side
        }
        
        return True, "Trade validated", trade_params

    def calculate_trailing_stop(self, entry_price: float, current_price: float,
                                current_stop: float, take_profit: float, 
                                side: str) -> Tuple[bool, float]:
        """
        Calculate trailing stop loss
        Returns: (should_trail, new_stop_loss)
        """
        if side == 'BUY':
            # Calculate profit in risk:reward ratio
            risk_distance = entry_price - current_stop
            current_profit = current_price - entry_price
            rr_ratio = current_profit / risk_distance if risk_distance > 0 else 0
            
            # Activate trailing stop at configured ratio
            if rr_ratio >= config.TRAILING_STOP_ACTIVATION:
                # Trail at configured distance
                new_stop = current_price - (risk_distance * config.TRAILING_STOP_DISTANCE)
                
                # Only move stop up, never down
                if new_stop > current_stop:
                    return True, new_stop
        
        else:  # SELL
            risk_distance = current_stop - entry_price
            current_profit = entry_price - current_price
            rr_ratio = current_profit / risk_distance if risk_distance > 0 else 0
            
            if rr_ratio >= config.TRAILING_STOP_ACTIVATION:
                new_stop = current_price + (risk_distance * config.TRAILING_STOP_DISTANCE)
                
                # Only move stop down, never up
                if new_stop < current_stop:
                    return True, new_stop
        
        return False, current_stop

    def calculate_pnl(self, entry_price: float, exit_price: float, 
                     position_size: float, side: str) -> Dict:
        """Calculate profit/loss for a trade"""
        if side == 'BUY':
            gross_pnl = (exit_price - entry_price) * position_size
        else:  # SELL
            gross_pnl = (entry_price - exit_price) * position_size
        
        # Calculate fees
        position_value = position_size * entry_price
        maker_fee = position_value * config.MAKER_FEE
        taker_fee = position_value * config.TAKER_FEE
        total_fees = maker_fee + taker_fee
        
        # Add slippage
        slippage_cost = position_value * config.SLIPPAGE
        
        # Net P&L
        net_pnl = gross_pnl - total_fees - slippage_cost
        
        # P&L percentage
        pnl_percentage = (net_pnl / self.current_capital) * 100
        
        return {
            'gross_pnl': gross_pnl,
            'fees': total_fees,
            'slippage': slippage_cost,
            'net_pnl': net_pnl,
            'pnl_percentage': pnl_percentage
        }

    def update_capital(self, new_capital: float):
        """Update current capital"""
        self.current_capital = new_capital
        
        # Update peak capital and drawdown
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = ((self.peak_capital - new_capital) / self.peak_capital) * 100
        
        logger.info(f"💰 Capital updated: ${new_capital:.2f} | Drawdown: {self.current_drawdown:.2f}%")

    def increment_daily_trades(self):
        """Increment daily trade counter"""
        self.daily_trades += 1
        logger.info(f"📊 Daily trades: {self.daily_trades}/{config.MAX_DAILY_TRADES}")

    def check_risk_limits(self) -> Tuple[bool, str]:
        """Check if risk limits are breached"""
        # Check emergency stop loss (circuit breaker)
        if config.EMERGENCY_STOP_LOSS:
            loss_pct = ((self.initial_capital - self.current_capital) / self.initial_capital) * 100
            if loss_pct >= (config.EMERGENCY_STOP_LOSS * 100):
                return False, f"Emergency stop triggered: {loss_pct:.1f}% loss"
        
        # Check max drawdown if configured
        if config.MAX_DRAWDOWN_LIMIT:
            if self.current_drawdown >= config.MAX_DRAWDOWN_LIMIT:
                return False, f"Max drawdown exceeded: {self.current_drawdown:.1f}%"
        
        return True, "Risk limits OK"

    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics"""
        return {
            'current_capital': self.current_capital,
            'initial_capital': self.initial_capital,
            'peak_capital': self.peak_capital,
            'current_drawdown': self.current_drawdown,
            'daily_trades': self.daily_trades,
            'max_daily_trades': config.MAX_DAILY_TRADES,
            'profit_loss': self.current_capital - self.initial_capital,
            'profit_loss_pct': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        }

    def reset_daily_counters(self):
        """Reset daily trade counters (called at start of new day)"""
        self.daily_trades = 0
        self.daily_trade_date = date.today()
        logger.info("📅 Daily counters reset")

# Create global risk manager instance
risk_manager = RiskManager()
