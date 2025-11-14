"""
Telegram Bot - Sends trading alerts and notifications with interactive commands
"""
import asyncio
from typing import Optional, Dict
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
from config import config
from logger import logger

class TelegramNotifier:
    """Sends notifications via Telegram - Supports multiple accounts with interactive commands"""

    def __init__(self):
        self.bots = []  # List of (bot, chat_id) tuples
        self.enabled = False
        self.application = None  # Telegram application for command handling
        self.bot_controller = None  # Reference to main bot controller
        self.authorized_chat_ids = set()  # Set of authorized chat IDs

        # Initialize primary account
        if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
            try:
                bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
                self.bots.append((bot, config.TELEGRAM_CHAT_ID))
                self.authorized_chat_ids.add(str(config.TELEGRAM_CHAT_ID))
                logger.info("✅ Primary Telegram bot initialized")
            except Exception as e:
                logger.warning(f"Primary Telegram bot initialization failed: {e}")
        
        # Initialize additional accounts
        extra_tokens = [t.strip() for t in config.TELEGRAM_BOT_TOKENS_EXTRA.split(',') if t.strip()]
        extra_chat_ids = [c.strip() for c in config.TELEGRAM_CHAT_IDS_EXTRA.split(',') if c.strip()]
        
        for idx, (token, chat_id) in enumerate(zip(extra_tokens, extra_chat_ids), start=2):
            try:
                bot = Bot(token=token)
                self.bots.append((bot, chat_id))
                self.authorized_chat_ids.add(str(chat_id))
                logger.info(f"✅ Telegram account #{idx} initialized")
            except Exception as e:
                logger.warning(f"Telegram account #{idx} initialization failed: {e}")
        
        # Enable if at least one bot is configured
        if self.bots:
            self.enabled = True
            logger.info(f"✅ Total {len(self.bots)} Telegram account(s) active")
        else:
            logger.info("Telegram notifications disabled (no credentials)")

    async def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """Send a message to all configured Telegram accounts"""
        if not self.enabled:
            return False

        success_count = 0
        for idx, (bot, chat_id) in enumerate(self.bots, start=1):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode
                )
                success_count += 1
            except TelegramError as e:
                logger.error(f"Failed to send Telegram message to account #{idx}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending Telegram message to account #{idx}: {e}")
        
        return success_count > 0

    async def send_startup_message(self, mode: str):
        """Send bot startup notification"""
        message = (
            f"🤖 <b>Trading Bot Started</b>\n\n"
            f"Mode: <b>{mode}</b>\n"
            f"Pair: {config.TRADING_PAIR}\n"
            f"Timeframe: {config.TIMEFRAME}\n"
            f"Capital: ${config.INITIAL_CAPITAL}\n"
            f"Leverage: {config.LEVERAGE}x\n"
            f"Risk per trade: {config.RISK_PERCENTAGE}%\n"
            f"Risk:Reward: 1:{config.RISK_REWARD_RATIO}\n"
            f"Max daily trades: {config.MAX_DAILY_TRADES}\n"
            f"Signal threshold: {config.SIGNAL_THRESHOLD}%\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await self.send_message(message)

    async def send_signal_alert(self, signal: Dict):
        """Send trading signal notification"""
        if signal['signal'] == 'HOLD':
            return

        emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"

        # Get component scores
        components = signal.get('components', {})

        message = (
            f"{emoji} <b>TRADING SIGNAL: {signal['signal']}</b>\n\n"
            f"Pair: {config.TRADING_PAIR}\n"
            f"Price: ${signal['price']:.2f}\n"
            f"Confidence: <b>{signal['confidence']:.1f}%</b>\n\n"
            f"<b>Score Breakdown:</b>\n"
        )

        if components:
            for name, data in components.items():
                score = data.get('score', 0)
                message += f"  • {name.capitalize()}: {score:+.1f}\n"

        message += f"\nFilter: {signal.get('filter_reason', 'N/A')}\n"
        message += f"Time: {datetime.now().strftime('%H:%M:%S')}"

        await self.send_message(message)

    async def send_trade_entry(self, position: Dict):
        """Send trade entry notification"""
        side_emoji = "📈" if position['side'] == 'BUY' else "📉"

        message = (
            f"{side_emoji} <b>TRADE ENTERED</b>\n\n"
            f"Side: <b>{position['side']}</b>\n"
            f"Pair: {position['pair']}\n"
            f"Entry: ${position['entry_price']:.2f}\n"
            f"Size: {position['position_size']:.4f}\n"
            f"Leverage: {position['leverage']}x\n\n"
            f"Stop Loss: ${position['stop_loss']:.2f}\n"
            f"Take Profit: ${position['take_profit']:.2f}\n\n"
            f"Signal Score: {position['signal_score']:.1f}%\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )

        await self.send_message(message)

    async def send_trade_exit(self, position: Dict):
        """Send trade exit notification"""
        pnl = position.get('pnl', 0)
        pnl_pct = position.get('pnl_percentage', 0)

        if pnl > 0:
            emoji = "✅"
            result = "PROFIT"
        elif pnl < 0:
            emoji = "❌"
            result = "LOSS"
        else:
            emoji = "⚪"
            result = "BREAKEVEN"

        message = (
            f"{emoji} <b>TRADE CLOSED - {result}</b>\n\n"
            f"Pair: {position['pair']}\n"
            f"Side: {position['side']}\n"
            f"Entry: ${position['entry_price']:.2f}\n"
            f"Exit: ${position['exit_price']:.2f}\n\n"
            f"<b>P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)</b>\n\n"
            f"Reason: {position['exit_reason']}\n"
            f"Duration: {self._calculate_duration(position)}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )

        await self.send_message(message)

    async def send_trailing_stop_update(self, position_id: str, old_stop: float,
                                       new_stop: float, current_price: float):
        """Send trailing stop update notification"""
        message = (
            f"🔄 <b>TRAILING STOP UPDATED</b>\n\n"
            f"Position: {position_id[:8]}...\n"
            f"Current Price: ${current_price:.2f}\n"
            f"Old Stop: ${old_stop:.2f}\n"
            f"New Stop: ${new_stop:.2f}\n\n"
            f"Profit locked in! 🎯\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )

        await self.send_message(message)

    async def send_daily_summary(self, stats: Dict):
        """Send daily performance summary"""
        total_trades = stats.get('total_trades', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        win_rate = stats.get('win_rate', 0)
        total_pnl = stats.get('total_pnl', 0)
        capital = stats.get('capital', 0)

        if total_pnl > 0:
            emoji = "📊💚"
        elif total_pnl < 0:
            emoji = "📊💔"
        else:
            emoji = "📊"

        message = (
            f"{emoji} <b>DAILY SUMMARY</b>\n\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"Total Trades: {total_trades}\n"
            f"Wins: {wins} | Losses: {losses}\n"
            f"Win Rate: {win_rate:.1f}%\n\n"
            f"<b>P&L: ${total_pnl:.2f}</b>\n"
            f"Current Capital: ${capital:.2f}\n"
            f"Return: {(total_pnl/config.INITIAL_CAPITAL)*100:+.2f}%\n\n"
        )

        if stats.get('best_trade'):
            message += f"Best Trade: ${stats['best_trade']:.2f}\n"
        if stats.get('worst_trade'):
            message += f"Worst Trade: ${stats['worst_trade']:.2f}\n"

        await self.send_message(message)

    async def send_error_alert(self, error_msg: str):
        """Send error notification"""
        message = (
            f"⚠️ <b>ERROR ALERT</b>\n\n"
            f"{error_msg}\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await self.send_message(message)

    async def send_risk_alert(self, alert_msg: str):
        """Send risk management alert"""
        message = (
            f"🚨 <b>RISK ALERT</b>\n\n"
            f"{alert_msg}\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await self.send_message(message)

    async def send_emergency_stop(self, reason: str):
        """Send emergency stop notification"""
        message = (
            f"🛑 <b>EMERGENCY STOP TRIGGERED</b>\n\n"
            f"Reason: {reason}\n\n"
            f"All positions closed!\n"
            f"Bot stopped for safety.\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await self.send_message(message)

    def _calculate_duration(self, position: Dict) -> str:
        """Calculate position duration"""
        try:
            entry_time = datetime.fromisoformat(position['entry_time'])
            exit_time = datetime.fromisoformat(position['exit_time'])
            duration = exit_time - entry_time

            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60

            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "N/A"

    async def test_connection(self) -> bool:
        """Test Telegram connection for all accounts"""
        if not self.enabled:
            return False

        try:
            message = "✅ Telegram connection test successful!"
            result = await self.send_message(message)
            if result:
                logger.info(f"Telegram connection test passed for {len(self.bots)} account(s)")
            return result
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False

    def set_bot_controller(self, controller):
        """Set reference to main bot controller for command handling"""
        self.bot_controller = controller
        logger.info("Bot controller reference set")

    async def start_command_handler(self):
        """Start Telegram command handler (interactive bot)"""
        if not config.TELEGRAM_BOT_TOKEN:
            logger.info("Command handler not started (no primary bot token)")
            return

        try:
            # Create application
            self.application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

            # Add command handlers
            self.application.add_handler(CommandHandler("start", self._cmd_start))
            self.application.add_handler(CommandHandler("stop", self._cmd_stop))
            self.application.add_handler(CommandHandler("pause", self._cmd_pause))
            self.application.add_handler(CommandHandler("resume", self._cmd_resume))
            self.application.add_handler(CommandHandler("status", self._cmd_status))
            self.application.add_handler(CommandHandler("balance", self._cmd_balance))
            self.application.add_handler(CommandHandler("positions", self._cmd_positions))
            self.application.add_handler(CommandHandler("stats", self._cmd_stats))
            self.application.add_handler(CommandHandler("emergency", self._cmd_emergency))
            self.application.add_handler(CommandHandler("help", self._cmd_help))

            # Start polling in background
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)

            logger.info("✅ Telegram command handler started")

        except Exception as e:
            logger.error(f"Failed to start command handler: {e}")

    async def stop_command_handler(self):
        """Stop Telegram command handler"""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram command handler stopped")
            except Exception as e:
                logger.error(f"Error stopping command handler: {e}")

    def _is_authorized(self, update: Update) -> bool:
        """Check if user is authorized"""
        chat_id = str(update.effective_chat.id)
        return chat_id in self.authorized_chat_ids

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - Show welcome and help"""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        message = (
            "🤖 <b>Trading Bot Control Panel</b>\n\n"
            "Available commands:\n"
            "/status - View bot status\n"
            "/balance - Check account balance\n"
            "/positions - View open positions\n"
            "/stats - Trading statistics\n"
            "/pause - Pause trading\n"
            "/resume - Resume trading\n"
            "/emergency - Close all positions\n"
            "/help - Show this message\n\n"
            "Bot is ready! 🚀"
        )
        await update.message.reply_text(message, parse_mode='HTML')

    async def _cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command - Stop the bot (alias for pause)"""
        await self._cmd_pause(update, context)

    async def _cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command - Pause trading"""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        if self.bot_controller:
            self.bot_controller.pause_trading()
            await update.message.reply_text("⏸️ <b>Trading Paused</b>\n\nNo new trades will be opened.", parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Bot controller not available")

    async def _cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command - Resume trading"""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        if self.bot_controller:
            self.bot_controller.resume_trading()
            await update.message.reply_text("▶️ <b>Trading Resumed</b>\n\nBot is now actively trading.", parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Bot controller not available")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - Show bot status"""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        if self.bot_controller:
            status = self.bot_controller.get_status()
            await update.message.reply_text(status, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Bot controller not available")

    async def _cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command - Show account balance"""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        if self.bot_controller:
            balance = await self.bot_controller.get_balance()
            await update.message.reply_text(balance, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Bot controller not available")

    async def _cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command - Show open positions"""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        if self.bot_controller:
            positions = await self.bot_controller.get_positions()
            await update.message.reply_text(positions, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Bot controller not available")

    async def _cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - Show trading statistics"""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        if self.bot_controller:
            stats = self.bot_controller.get_stats()
            await update.message.reply_text(stats, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Bot controller not available")

    async def _cmd_emergency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /emergency command - Close all positions immediately"""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        if self.bot_controller:
            result = await self.bot_controller.emergency_stop()
            await update.message.reply_text(result, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Bot controller not available")

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command - Show help message"""
        await self._cmd_start(update, context)

# Create global Telegram notifier instance
telegram_notifier = TelegramNotifier()

