"""
Paper Trading Simulator - Test strategy without real money
"""
import asyncio
from typing import Dict, Optional
from datetime import datetime
from config import config
from logger import logger, trading_logger
from risk_manager import RiskManager
from trade_executor_delta import TradeExecutorDelta as TradeExecutor

class PaperTrading:
    """Simulates live trading without real capital"""

    def __init__(self, initial_capital: float = None):
        self.initial_capital = initial_capital or config.INITIAL_CAPITAL
        self.virtual_capital = self.initial_capital
        self.risk_manager = RiskManager()
        self.risk_manager.current_capital = self.virtual_capital
        self.trade_executor = TradeExecutor(mode='PAPER')

        self.trades = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        logger.info(f"📝 Paper Trading initialized with ${self.initial_capital}")

    async def execute_signal(self, signal: Dict, market_data: Dict) -> bool:
        """Execute a signal in paper trading mode"""

        if signal['signal'] == 'HOLD':
            return False

        # Validate trade with risk manager
        can_trade, reason, trade_params = self.risk_manager.validate_trade(signal, market_data)

        if not can_trade:
            logger.info(f"⏸️ Paper trade rejected: {reason}")
            return False

        # Execute trade
        position = await self.trade_executor.execute_trade(signal, trade_params)

        if position:
            logger.info(
                f"📝 Paper trade opened: {position['side']} {position['pair']} "
                f"at ${position['entry_price']:.2f}"
            )
            return True

        return False

    async def monitor_positions(self, current_price: float):
        """Monitor and update open positions"""
        await self.trade_executor.monitor_positions(current_price)

    def get_statistics(self) -> Dict:
        """Get paper trading statistics"""

        total_pnl = self.risk_manager.current_capital - self.initial_capital
        total_return = (total_pnl / self.initial_capital) * 100

        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        # Get closed trades from positions
        closed_trades = [p for p in self.trade_executor.positions.values() if p.get('status') == 'CLOSED']

        winning_pnls = [t['pnl_usd'] for t in closed_trades if t.get('pnl_usd', 0) > 0]
        losing_pnls = [t['pnl_usd'] for t in closed_trades if t.get('pnl_usd', 0) < 0]

        avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0

        profit_factor = abs(sum(winning_pnls) / sum(losing_pnls)) if losing_pnls else 0

        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.risk_manager.current_capital,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'open_positions': len(self.trade_executor.get_open_positions())
        }

    def print_summary(self):
        """Print paper trading summary"""
        stats = self.get_statistics()

        print("\n" + "="*60)
        print("PAPER TRADING SUMMARY")
        print("="*60)
        print(f"Initial Capital: ${stats['initial_capital']:.2f}")
        print(f"Current Capital: ${stats['current_capital']:.2f}")
        print(f"Total P&L: ${stats['total_pnl']:.2f} ({stats['total_return']:+.2f}%)")
        print(f"\nTotal Trades: {stats['total_trades']}")
        print(f"Wins: {stats['winning_trades']} | Losses: {stats['losing_trades']}")
        print(f"Win Rate: {stats['win_rate']:.2f}%")
        print(f"\nAverage Win: ${stats['avg_win']:.2f}")
        print(f"Average Loss: ${stats['avg_loss']:.2f}")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")
        print(f"\nOpen Positions: {stats['open_positions']}")
        print("="*60 + "\n")

    async def update_closed_trade(self, position: Dict):
        """Update statistics when trade closes"""
        self.total_trades += 1

        if position.get('pnl', 0) > 0:
            self.winning_trades += 1
        elif position.get('pnl', 0) < 0:
            self.losing_trades += 1

        self.virtual_capital = self.risk_manager.current_capital

        logger.info(
            f"📝 Paper trade closed: P&L ${position['pnl']:.2f} | "
            f"Capital: ${self.virtual_capital:.2f}"
        )

# Create paper trading instance (will be initialized in main if needed)
paper_trading = None

