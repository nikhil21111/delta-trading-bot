"""
Backtesting Engine - Test strategy on historical data
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List
from config import config
from logger import logger
from strategy import TradingStrategy
from risk_manager import RiskManager
import asyncio

class Backtester:
    """Backtest trading strategy on historical data"""

    def __init__(self, initial_capital: float = None):
        self.initial_capital = initial_capital or config.INITIAL_CAPITAL
        self.capital = self.initial_capital
        self.strategy = TradingStrategy()
        self.risk_manager = RiskManager()
        self.risk_manager.current_capital = self.capital

        self.trades = []
        self.equity_curve = []
        self.position = None

        logger.info(f"📊 Backtester initialized with ${self.initial_capital}")

    async def run_backtest(self, df: pd.DataFrame) -> Dict:
        """Run backtest on historical data"""

        logger.info(f"🔄 Starting backtest with {len(df)} candles...")

        # Calculate indicators once for all data
        df = self.strategy.calculate_indicators(df)

        # Initialize equity tracking
        self.equity_curve = []
        self.trades = []

        # Iterate through each candle
        for i in range(config.EMA_SLOW, len(df)):
            current_slice = df.iloc[:i+1]
            current_candle = df.iloc[i]
            current_price = current_candle['close']
            current_time = df.index[i]

            # Record equity
            self.equity_curve.append({
                'timestamp': current_time,
                'equity': self.capital
            })

            # Check if we have an open position
            if self.position:
                await self._check_position_exit(current_candle, current_time)
            else:
                # Look for entry signal
                await self._check_entry_signal(current_slice, current_candle, current_time)

            # Update progress
            if i % 1000 == 0:
                progress = (i / len(df)) * 100
                logger.info(f"Backtest progress: {progress:.1f}%")

        # Close any remaining open position
        if self.position:
            final_price = df.iloc[-1]['close']
            await self._close_position(final_price, df.index[-1], 'END_OF_DATA')

        # Calculate statistics
        stats = self._calculate_statistics()

        logger.info("✅ Backtest completed")

        return stats

    async def _check_entry_signal(self, df_slice: pd.DataFrame,
                                  current_candle: pd.Series,
                                  current_time):
        """Check for entry signal"""

        # Create market data dict
        market_data = {
            'ohlcv': df_slice,
            'funding_rate': 0.0,  # Historical funding rate not available
            'open_interest': 0.0,
            'sentiment': {'score': 0.0}
        }

        # Generate signal
        signal = self.strategy.generate_signal(market_data)

        if signal['signal'] == 'HOLD':
            return

        # Validate trade
        can_trade, reason, trade_params = self.risk_manager.validate_trade(signal, market_data)

        if not can_trade:
            return

        # Open position
        self.position = {
            'entry_time': current_time,
            'entry_price': trade_params['entry_price'],
            'side': signal['signal'],
            'size': trade_params['position_size'],
            'stop_loss': trade_params['stop_loss'],
            'take_profit': trade_params['take_profit'],
            'signal_score': signal['confidence'],
            'trailing_stop_active': False
        }

        self.risk_manager.increment_daily_trades()

        logger.debug(
            f"[{current_time}] Entry: {signal['signal']} at ${trade_params['entry_price']:.2f}"
        )

    async def _check_position_exit(self, current_candle: pd.Series, current_time):
        """Check if position should be closed"""

        if not self.position:
            return

        current_price = current_candle['close']
        high = current_candle['high']
        low = current_candle['low']

        # Check trailing stop activation
        if not self.position['trailing_stop_active']:
            should_trail, new_stop = self.risk_manager.calculate_trailing_stop(
                self.position['entry_price'],
                current_price,
                self.position['stop_loss'],
                self.position['take_profit'],
                self.position['side']
            )

            if should_trail:
                self.position['stop_loss'] = new_stop
                self.position['trailing_stop_active'] = True
        else:
            # Update trailing stop if price moved further
            should_trail, new_stop = self.risk_manager.calculate_trailing_stop(
                self.position['entry_price'],
                current_price,
                self.position['stop_loss'],
                self.position['take_profit'],
                self.position['side']
            )

            if should_trail and new_stop != self.position['stop_loss']:
                self.position['stop_loss'] = new_stop

        # Check exit conditions using high/low for realistic simulation
        if self.position['side'] == 'BUY':
            # Check stop loss (use low of candle)
            if low <= self.position['stop_loss']:
                await self._close_position(self.position['stop_loss'], current_time, 'STOP_LOSS')
                return

            # Check take profit (use high of candle)
            if high >= self.position['take_profit']:
                await self._close_position(self.position['take_profit'], current_time, 'TAKE_PROFIT')
                return

        else:  # SELL
            # Check stop loss
            if high >= self.position['stop_loss']:
                await self._close_position(self.position['stop_loss'], current_time, 'STOP_LOSS')
                return

            # Check take profit
            if low <= self.position['take_profit']:
                await self._close_position(self.position['take_profit'], current_time, 'TAKE_PROFIT')
                return

    async def _close_position(self, exit_price: float, exit_time, reason: str):
        """Close the current position"""

        if not self.position:
            return

        # Calculate P&L
        pnl_data = self.risk_manager.calculate_pnl(
            self.position['entry_price'],
            exit_price,
            self.position['size'],
            self.position['side']
        )

        # Update capital
        self.capital += pnl_data['net_pnl']
        self.risk_manager.update_capital(self.capital)

        # Record trade
        trade = {
            'entry_time': self.position['entry_time'],
            'exit_time': exit_time,
            'side': self.position['side'],
            'entry_price': self.position['entry_price'],
            'exit_price': exit_price,
            'size': self.position['size'],
            'pnl': pnl_data['net_pnl'],
            'pnl_percentage': pnl_data['pnl_percentage'],
            'return': pnl_data['roi'],
            'fees': pnl_data['fees'],
            'exit_reason': reason,
            'signal_score': self.position['signal_score'],
            'trailing_stop_used': self.position['trailing_stop_active']
        }

        self.trades.append(trade)

        logger.debug(
            f"[{exit_time}] Exit: {exit_price:.2f} | "
            f"P&L: ${pnl_data['net_pnl']:.2f} | Reason: {reason}"
        )

        # Clear position
        self.position = None

    def _calculate_statistics(self) -> Dict:
        """Calculate backtest statistics"""

        if not self.trades:
            return {
                'error': 'No trades executed',
                'total_trades': 0
            }

        df_trades = pd.DataFrame(self.trades)

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len(df_trades[df_trades['pnl'] > 0])
        losing_trades = len(df_trades[df_trades['pnl'] < 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        # P&L metrics
        total_pnl = df_trades['pnl'].sum()
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df_trades[df_trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0

        best_trade = df_trades['pnl'].max()
        worst_trade = df_trades['pnl'].min()

        # Profit factor
        gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Drawdown
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax'] * 100
        max_drawdown = equity_df['drawdown'].min()

        # Sharpe ratio (simplified - assuming 252 trading periods per year)
        returns = df_trades['pnl'] / self.initial_capital
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

        # Average trade duration
        df_trades['duration'] = pd.to_datetime(df_trades['exit_time']) - pd.to_datetime(df_trades['entry_time'])
        avg_duration = df_trades['duration'].mean()

        # Risk-reward metrics
        avg_rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        stats = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_duration': str(avg_duration),
            'avg_risk_reward': avg_rr,
            'total_fees': df_trades['fees'].sum()
        }

        return stats

    def print_results(self, stats: Dict):
        """Print backtest results"""

        if 'error' in stats:
            print(f"\n❌ {stats['error']}")
            return

        print("\n" + "="*70)
        print("BACKTEST RESULTS")
        print("="*70)
        print(f"\n💰 Capital Performance:")
        print(f"  Initial Capital:     ${stats['initial_capital']:.2f}")
        print(f"  Final Capital:       ${stats['final_capital']:.2f}")
        print(f"  Total P&L:           ${stats['total_pnl']:.2f}")
        print(f"  Total Return:        {stats['total_return']:+.2f}%")

        print(f"\n📊 Trade Statistics:")
        print(f"  Total Trades:        {stats['total_trades']}")
        print(f"  Winning Trades:      {stats['winning_trades']}")
        print(f"  Losing Trades:       {stats['losing_trades']}")
        print(f"  Win Rate:            {stats['win_rate']:.2f}%")

        print(f"\n💵 P&L Analysis:")
        print(f"  Average Win:         ${stats['avg_win']:.2f}")
        print(f"  Average Loss:        ${stats['avg_loss']:.2f}")
        print(f"  Best Trade:          ${stats['best_trade']:.2f}")
        print(f"  Worst Trade:         ${stats['worst_trade']:.2f}")
        print(f"  Profit Factor:       {stats['profit_factor']:.2f}")
        print(f"  Avg Risk:Reward:     1:{stats['avg_risk_reward']:.2f}")

        print(f"\n📈 Risk Metrics:")
        print(f"  Max Drawdown:        {stats['max_drawdown']:.2f}%")
        print(f"  Sharpe Ratio:        {stats['sharpe_ratio']:.2f}")
        print(f"  Total Fees:          ${stats['total_fees']:.2f}")
        print(f"  Avg Duration:        {stats['avg_duration']}")

        print("="*70 + "\n")

    def plot_results(self):
        """Plot backtest results"""

        if not self.trades or not self.equity_curve:
            logger.warning("No data to plot")
            return

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Backtest Results', fontsize=16, fontweight='bold')

        # Equity curve
        equity_df = pd.DataFrame(self.equity_curve)
        axes[0, 0].plot(equity_df['timestamp'], equity_df['equity'], linewidth=2)
        axes[0, 0].axhline(y=self.initial_capital, color='r', linestyle='--', alpha=0.5)
        axes[0, 0].set_title('Equity Curve')
        axes[0, 0].set_ylabel('Capital ($)')
        axes[0, 0].grid(True, alpha=0.3)

        # Drawdown
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax'] * 100
        axes[0, 1].fill_between(equity_df['timestamp'], equity_df['drawdown'], 0,
                                color='red', alpha=0.3)
        axes[0, 1].set_title('Drawdown')
        axes[0, 1].set_ylabel('Drawdown (%)')
        axes[0, 1].grid(True, alpha=0.3)

        # Trade P&L distribution
        df_trades = pd.DataFrame(self.trades)
        axes[1, 0].hist(df_trades['pnl'], bins=30, edgecolor='black', alpha=0.7)
        axes[1, 0].axvline(x=0, color='r', linestyle='--', linewidth=2)
        axes[1, 0].set_title('P&L Distribution')
        axes[1, 0].set_xlabel('P&L ($)')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].grid(True, alpha=0.3)

        # Cumulative P&L
        df_trades['cumulative_pnl'] = df_trades['pnl'].cumsum()
        axes[1, 1].plot(range(len(df_trades)), df_trades['cumulative_pnl'],
                       linewidth=2, marker='o', markersize=3)
        axes[1, 1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        axes[1, 1].set_title('Cumulative P&L')
        axes[1, 1].set_xlabel('Trade Number')
        axes[1, 1].set_ylabel('Cumulative P&L ($)')
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        # Save plot
        filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        logger.info(f"📊 Results chart saved: {filename}")

        plt.show()

# Backtester instance will be created when needed
backtester = None

