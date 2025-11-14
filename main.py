"""
Main Trading Bot Application
CoinDCX ETH/USDT Spot Auto-Trader with Advanced Strategy
Direct CoinDCX API Integration (No Binance/CCXT)
"""
import asyncio
import sys
from datetime import datetime
from typing import Optional
import signal as sys_signal

from config import config
from logger import logger, trading_logger
from database import db
from data_manager_delta import DataManagerDelta as DataManager
from strategy import strategy
from risk_manager import risk_manager
from trade_executor_delta import TradeExecutorDelta as TradeExecutor
from telegram_bot import telegram_notifier
from paper_trading import PaperTrading
from backtester import Backtester
from monitor import monitor
from bot_interface import bot_interface

class TradingBot:
    """Main trading bot orchestrator"""

    def __init__(self, mode='LIVE'):
        self.mode = mode.upper()
        self.running = False
        self.trading_enabled = True  # Controls whether new trades can be opened
        self.trade_executor = None
        self.paper_trading = None
        self.backtester = None

        # Setup signal handlers for graceful shutdown
        sys_signal.signal(sys_signal.SIGINT, self._signal_handler)
        sys_signal.signal(sys_signal.SIGTERM, self._signal_handler)

        logger.info(f"🤖 Trading Bot initialized in {self.mode} mode")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received...")
        self.running = False

    async def initialize(self):
        """Initialize bot components"""

        logger.info("Initializing bot components...")

        # Validate configuration
        config_errors = config.validate()
        if config_errors:
            logger.error("Configuration errors:")
            for error in config_errors:
                logger.error(f"  - {error}")
            return False

        # Display configuration
        config.display()
        
        # Initialize data manager
        self.data_manager = DataManager()

        # Initialize appropriate mode
        if self.mode == 'LIVE':
            self.trade_executor = TradeExecutor(mode='LIVE')
        elif self.mode == 'PAPER':
            self.paper_trading = PaperTrading()
            self.trade_executor = self.paper_trading.trade_executor
        elif self.mode == 'BACKTEST':
            self.backtester = Backtester()
        else:
            logger.error(f"Invalid mode: {self.mode}")
            return False

        # Test Telegram connection
        if self.mode != 'BACKTEST':
            await telegram_notifier.test_connection()
            await telegram_notifier.send_startup_message(self.mode)
            
            # Set bot controller and start command handler
            telegram_notifier.set_bot_controller(self)
            await telegram_notifier.start_command_handler()
        
        # Set bot instance for web dashboard
        bot_interface.set_bot(self)

        logger.info("✅ Bot initialized successfully")
        return True

    async def run_live_trading(self):
        """Run live trading mode"""

        logger.info("🚀 Starting live trading...")
        self.running = True

        candle_check_interval = 60  # Check every 60 seconds

        while self.running:
            try:
                # Fetch market data
                market_data = await self.data_manager.get_market_data(config.TRADING_PAIR)

                df = market_data.get('ohlcv')
                if df is None or len(df) == 0:
                    logger.warning("No market data received, retrying...")
                    await asyncio.sleep(candle_check_interval)
                    continue

                # Check if new candle formed
                if self.data_manager.check_new_candle(df):
                    logger.info(f"🕐 New candle - analyzing {config.TRADING_PAIR}...")

                    # Generate signal
                    signal = strategy.generate_signal(market_data)
                    monitor.log_signal(signal)

                    # Send signal to Telegram
                    if signal['signal'] != 'HOLD':
                        await telegram_notifier.send_signal_alert(signal)

                    # Check if we should execute trade
                    if signal['signal'] in ['BUY', 'SELL']:
                        if not self.trading_enabled:
                            logger.info(f"Trading paused - signal ignored: {signal['signal']}")
                            continue
                        
                        can_trade, reason, trade_params = risk_manager.validate_trade(
                            signal, market_data
                        )

                        if can_trade:
                            # Execute trade
                            position = await self.trade_executor.execute_trade(
                                signal, trade_params
                            )

                            if position:
                                trading_logger.log_trade(
                                    'ENTRY',
                                    position['pair'],
                                    position['entry_price'],
                                    position['position_size'],
                                    f"Score: {signal['confidence']:.1f}%"
                                )

                                await telegram_notifier.send_trade_entry(position)
                        else:
                            logger.info(f"Trade rejected: {reason}")

                # Monitor open positions
                current_price = df.iloc[-1]['close']
                await self.trade_executor.monitor_positions(current_price)

                # Check for closed positions and send notifications
                await self._check_closed_positions()

                # Check risk limits
                risk_ok, risk_msg = risk_manager.check_risk_limits()
                if not risk_ok:
                    logger.error(f"⛔ Risk limit breached: {risk_msg}")
                    await telegram_notifier.send_emergency_stop(risk_msg)
                    await self.trade_executor.close_all_positions(current_price)
                    break

                # Display dashboard
                positions = self.trade_executor.get_open_positions()
                risk_metrics = risk_manager.get_risk_metrics()
                monitor.display_dashboard(market_data, signal, positions, risk_metrics)

                # Wait before next check
                await asyncio.sleep(candle_check_interval)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await telegram_notifier.send_error_alert(str(e))
                await asyncio.sleep(candle_check_interval)

        logger.info("🛑 Live trading stopped")

    async def run_paper_trading(self):
        """Run paper trading mode"""

        logger.info("📝 Starting paper trading...")
        self.running = True

        candle_check_interval = 60

        while self.running:
            try:
                # Fetch market data
                market_data = await self.data_manager.get_market_data(config.TRADING_PAIR)

                df = market_data.get('ohlcv')
                if df is None or len(df) == 0:
                    await asyncio.sleep(candle_check_interval)
                    continue

                # Check for new candle
                if self.data_manager.check_new_candle(df):
                    # Generate signal
                    signal = strategy.generate_signal(market_data)
                    monitor.log_signal(signal)

                    # Execute signal in paper mode
                    if signal['signal'] in ['BUY', 'SELL']:
                        await self.paper_trading.execute_signal(signal, market_data)

                # Monitor positions
                current_price = df.iloc[-1]['close']
                await self.paper_trading.monitor_positions(current_price)

                # Display dashboard
                positions = self.trade_executor.get_open_positions()
                risk_metrics = risk_manager.get_risk_metrics()
                monitor.display_dashboard(market_data, signal, positions, risk_metrics)

                await asyncio.sleep(candle_check_interval)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in paper trading: {e}")
                await asyncio.sleep(candle_check_interval)

        # Print summary
        self.paper_trading.print_summary()
        logger.info("📝 Paper trading stopped")

    async def run_backtest(self):
        """Run backtest mode"""

        logger.info("📊 Starting backtest...")

        try:
            # Fetch historical data
            logger.info(f"Fetching historical data from {config.BACKTEST_START_DATE} to {config.BACKTEST_END_DATE}")

            df = await self.data_manager.get_historical_data(
                config.TRADING_PAIR,
                config.BACKTEST_START_DATE,
                config.BACKTEST_END_DATE,
                config.TIMEFRAME
            )

            if df is None or len(df) == 0:
                logger.error("Failed to fetch historical data")
                return

            # Run backtest
            stats = await self.backtester.run_backtest(df)

            # Print results
            self.backtester.print_results(stats)

            # Plot results
            self.backtester.plot_results()

            logger.info("📊 Backtest completed")

        except Exception as e:
            logger.error(f"Backtest failed: {e}", exc_info=True)

    async def _check_closed_positions(self):
        """Check for positions that were closed and send notifications"""
        # This would need to track position states and detect closures
        # For simplicity, we'll rely on the trade executor to handle this
        pass

    async def shutdown(self):
        """Graceful shutdown"""

        logger.info("🛑 Shutting down bot...")

        self.running = False

        # Stop Telegram command handler
        if self.mode != 'BACKTEST':
            await telegram_notifier.stop_command_handler()

        # Close all open positions if in trading mode
        if self.trade_executor and self.mode in ['LIVE', 'PAPER']:
            open_positions = self.trade_executor.get_open_positions()
            if open_positions:
                logger.warning(f"Closing {len(open_positions)} open positions...")

                # Get current price
                try:
                    ticker = await self.data_manager.fetch_ticker()
                    current_price = ticker['last'] if ticker else 0

                    await self.trade_executor.close_all_positions(current_price)
                except:
                    pass

        # Send shutdown notification
        if self.mode != 'BACKTEST':
            await telegram_notifier.send_message("🛑 <b>Bot Shutdown</b>\n\nTrading bot stopped.")

        logger.info("✅ Shutdown complete")

    async def run(self):
        """Main run method"""

        # Initialize
        if not await self.initialize():
            logger.error("Initialization failed")
            return

        try:
            # Run appropriate mode
            if self.mode == 'LIVE':
                await self.run_live_trading()
            elif self.mode == 'PAPER':
                await self.run_paper_trading()
            elif self.mode == 'BACKTEST':
                await self.run_backtest()

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)

        finally:
            await self.shutdown()

    # Bot Control Methods (called by Telegram commands)
    
    def pause_trading(self):
        """Pause trading (stop opening new positions)"""
        self.trading_enabled = False
        logger.info("⏸️ Trading paused")
    
    def resume_trading(self):
        """Resume trading"""
        self.trading_enabled = True
        logger.info("▶️ Trading resumed")
    
    def stop_bot(self):
        """Stop the entire bot (not just pause trading)"""
        logger.info("🛑 Stop command received")
        self.running = False
        self.trading_enabled = False
    
    def get_status(self) -> str:
        """Get bot status"""
        status_emoji = "▶️" if self.trading_enabled else "⏸️"
        status_text = "ACTIVE" if self.trading_enabled else "PAUSED"
        
        open_positions = len(self.trade_executor.get_open_positions()) if self.trade_executor else 0
        
        message = (
            f"{status_emoji} <b>Bot Status</b>\n\n"
            f"Mode: <b>{self.mode}</b>\n"
            f"Trading: <b>{status_text}</b>\n"
            f"Open Positions: <b>{open_positions}</b>\n"
            f"Pair: {config.TRADING_PAIR}\n"
            f"Leverage: {config.LEVERAGE}x\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        return message
    
    async def get_balance(self) -> str:
        """Get account balance"""
        if not self.trade_executor:
            return "❌ Trade executor not available"
        
        try:
            balance = await self.trade_executor.get_account_balance()
            if balance:
                available = balance.get('available_balance', 0)
                total = balance.get('balance', 0)
                
                message = (
                    f"💰 <b>Account Balance</b>\n\n"
                    f"Total Balance: <b>${total:.2f}</b>\n"
                    f"Available: ${available:.2f}\n"
                    f"Capital: ${config.INITIAL_CAPITAL}\n"
                    f"Leverage: {config.LEVERAGE}x\n"
                    f"Time: {datetime.now().strftime('%H:%M:%S')}"
                )
                return message
            else:
                return "❌ Failed to fetch balance"
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return f"❌ Error: {str(e)}"
    
    async def get_positions(self) -> str:
        """Get open positions"""
        if not self.trade_executor:
            return "❌ Trade executor not available"
        
        positions = self.trade_executor.get_open_positions()
        
        if not positions:
            return "📊 <b>Open Positions</b>\n\nNo open positions"
        
        message = f"📊 <b>Open Positions ({len(positions)})</b>\n\n"
        
        for idx, pos in enumerate(positions, 1):
            side_emoji = "🟢" if pos['side'] == 'buy' else "🔴"
            pnl = pos.get('current_pnl', 0)
            pnl_pct = pos.get('current_pnl_pct', 0)
            pnl_emoji = "📈" if pnl > 0 else "📉" if pnl < 0 else "➖"
            
            message += (
                f"{side_emoji} <b>Position #{idx}</b>\n"
                f"Side: {pos['side'].upper()}\n"
                f"Entry: ${pos['entry_price']:.2f}\n"
                f"Contracts: {pos['contracts']}\n"
                f"P&L: {pnl_emoji} ${pnl:.2f} ({pnl_pct:+.1f}%)\n"
                f"SL: ${pos['stop_loss']:.2f} | TP: ${pos['take_profit']:.2f}\n\n"
            )
        
        return message
    
    def get_stats(self) -> str:
        """Get trading statistics"""
        stats = risk_manager.get_risk_metrics()
        
        total_trades = stats.get('total_trades', 0)
        win_rate = stats.get('win_rate', 0)
        total_pnl = stats.get('total_pnl', 0)
        
        message = (
            f"📊 <b>Trading Statistics</b>\n\n"
            f"Total Trades: {total_trades}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Total P&L: ${total_pnl:.2f}\n"
            f"Current Capital: ${config.INITIAL_CAPITAL + total_pnl:.2f}\n"
            f"Return: {(total_pnl/config.INITIAL_CAPITAL)*100:+.2f}%\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        return message
    
    async def emergency_stop(self) -> str:
        """Emergency stop - close all positions"""
        if not self.trade_executor:
            return "❌ Trade executor not available"
        
        try:
            positions = self.trade_executor.get_open_positions()
            if not positions:
                return "✅ No open positions to close"
            
            # Get current price
            ticker = await self.data_manager.fetch_ticker()
            current_price = ticker['last'] if ticker else 0
            
            # Close all positions
            await self.trade_executor.close_all_positions(current_price)
            
            # Pause trading
            self.trading_enabled = False
            
            message = (
                f"🛑 <b>EMERGENCY STOP</b>\n\n"
                f"Closed {len(positions)} position(s)\n"
                f"Trading paused\n\n"
                f"Use /resume to restart trading"
            )
            
            logger.warning("Emergency stop triggered via Telegram")
            return message
            
        except Exception as e:
            logger.error(f"Emergency stop error: {e}")
            return f"❌ Error during emergency stop: {str(e)}"

async def main():
    """Main entry point"""

    # Display banner
    print("\n" + "="*70)
    print("  🤖 CRYPTO FUTURES TRADING BOT v1.0")
    print("  Delta Exchange Futures Automated Trading System")
    print("  Leverage: Up to 100x | Advanced Risk Management")
    print("="*70 + "\n")

    # Parse command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].upper()
    else:
        print("Select mode:")
        print("  1. LIVE - Live trading with real money")
        print("  2. PAPER - Paper trading simulation")
        print("  3. BACKTEST - Historical backtest")

        choice = input("\nEnter choice (1/2/3): ").strip()

        mode_map = {'1': 'LIVE', '2': 'PAPER', '3': 'BACKTEST'}
        mode = mode_map.get(choice, 'PAPER')

    if mode not in ['LIVE', 'PAPER', 'BACKTEST']:
        print(f"Invalid mode: {mode}")
        print("Valid modes: LIVE, PAPER, BACKTEST")
        return

    # Confirm live trading (skip confirmation in production mode)
    if mode == 'LIVE':
        print("\n⚠️  WARNING: You are about to start LIVE trading with real money!")
        print(f"   Capital: ${config.INITIAL_CAPITAL}")
        print(f"   Leverage: {config.LEVERAGE}x")
        print(f"   Risk: {config.RISK_PERCENTAGE}% per trade\n")

        # Auto-confirm in production (cloud deployment)
        if config.PRODUCTION:
            print("Production mode detected - starting automatically...")
            logger.info("Live trading started in production mode")
        else:
            confirm = input("Type 'YES' to confirm: ").strip()
            if confirm != 'YES':
                print("Live trading cancelled")
                return

    # Create and run bot
    bot = TradingBot(mode=mode)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")

