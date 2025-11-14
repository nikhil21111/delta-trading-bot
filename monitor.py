"""
Monitor - Real-time dashboard and performance tracking
"""
from typing import Dict
from datetime import datetime
from tabulate import tabulate
from colorama import Fore, Style
from config import config
from logger import logger

class Monitor:
    """Real-time monitoring and dashboard"""

    def __init__(self):
        self.start_time = datetime.now()
        self.last_signal = None
        self.signal_history = []

    def display_dashboard(self, market_data: Dict, signal: Dict,
                         positions: Dict, risk_metrics: Dict):
        """Display real-time dashboard"""

        # Clear screen (optional)
        # print("\033[2J\033[H")

        print("\n" + "="*80)
        print(f"🤖 CRYPTO FUTURES TRADING BOT - {config.TRADING_PAIR} | {config.TIMEFRAME}")
        print("="*80)

        # Market Info
        df = market_data.get('ohlcv')
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            price = latest['close']
            change = ((price - prev['close']) / prev['close']) * 100

            color = Fore.GREEN if change >= 0 else Fore.RED

            print(f"\n📊 Market Data:")
            print(f"  Price:           ${price:.2f} {color}({change:+.2f}%){Style.RESET_ALL}")
            print(f"  24h High:        ${latest['high']:.2f}")
            print(f"  24h Low:         ${latest['low']:.2f}")
            print(f"  Volume:          {latest['volume']:.2f}")
            print(f"  RSI:             {latest.get('rsi', 0):.1f}")
            print(f"  Funding Rate:    {market_data.get('funding_rate', 0):.4%}")

        # Current Signal
        print(f"\n🎯 Current Signal:")
        if signal:
            signal_type = signal['signal']
            confidence = signal['confidence']

            if signal_type == 'BUY':
                signal_color = Fore.GREEN
                emoji = "📈"
            elif signal_type == 'SELL':
                signal_color = Fore.RED
                emoji = "📉"
            else:
                signal_color = Fore.YELLOW
                emoji = "⏸️"

            print(f"  Signal:          {signal_color}{emoji} {signal_type}{Style.RESET_ALL}")
            print(f"  Confidence:      {confidence:.1f}%")
            print(f"  Threshold:       {config.SIGNAL_THRESHOLD}%")

            # Component scores
            if 'components' in signal:
                print(f"\n  Score Breakdown:")
                for name, data in signal['components'].items():
                    score = data.get('score', 0)
                    score_color = Fore.GREEN if score > 0 else Fore.RED if score < 0 else Fore.YELLOW
                    print(f"    {name.capitalize():12} {score_color}{score:+6.1f}{Style.RESET_ALL}")

        # Open Positions
        print(f"\n💼 Open Positions: {len(positions)}")
        if positions:
            pos_data = []
            for pos_id, pos in positions.items():
                entry = pos['entry_price']
                current = price if df is not None else entry

                if pos['side'] == 'BUY':
                    pnl = (current - entry) * pos['position_size']
                    pnl_pct = ((current - entry) / entry) * 100
                else:
                    pnl = (entry - current) * pos['position_size']
                    pnl_pct = ((entry - current) / entry) * 100

                pnl_color = Fore.GREEN if pnl > 0 else Fore.RED

                pos_data.append([
                    pos_id[:8] + "...",
                    pos['side'],
                    f"${entry:.2f}",
                    f"${pos['stop_loss']:.2f}",
                    f"${pos['take_profit']:.2f}",
                    f"{pnl_color}${pnl:.2f} ({pnl_pct:+.2f}%){Style.RESET_ALL}"
                ])

            print(tabulate(pos_data,
                          headers=['ID', 'Side', 'Entry', 'Stop Loss', 'Take Profit', 'Unrealized P&L'],
                          tablefmt='simple'))

        # Risk & Capital
        print(f"\n💰 Capital & Risk:")
        print(f"  Current Capital: ${risk_metrics.get('current_capital', 0):.2f}")
        
        total_pnl = risk_metrics.get('profit_loss', 0)
        total_pnl_pct = risk_metrics.get('profit_loss_pct', 0)
        print(f"  Total P&L:       ${total_pnl:.2f} ({total_pnl_pct:+.2f}%)")
        
        print(f"  Daily Trades:    {risk_metrics.get('daily_trades', 0)}/{risk_metrics.get('max_daily_trades', 0)}")
        
        risk_per_trade = config.RISK_PERCENTAGE if 'config' in dir() else risk_metrics.get('risk_per_trade', 3.0)
        leverage = config.LEVERAGE if 'config' in dir() else risk_metrics.get('leverage', 10)
        
        print(f"  Risk per Trade:  {risk_per_trade}%")
        print(f"  Leverage:        {leverage}x")

        # Runtime
        runtime = datetime.now() - self.start_time
        hours = runtime.seconds // 3600
        minutes = (runtime.seconds % 3600) // 60

        print(f"\n⏱️ Runtime: {hours}h {minutes}m")
        print(f"🕐 Last Update: {datetime.now().strftime('%H:%M:%S')}")
        print("="*80 + "\n")

    def display_compact_status(self, signal: Dict, positions: Dict, capital: float):
        """Display compact one-line status"""

        signal_emoji = {
            'BUY': '📈',
            'SELL': '📉',
            'HOLD': '⏸️'
        }

        emoji = signal_emoji.get(signal.get('signal', 'HOLD'), '⏸️')
        conf = signal.get('confidence', 0)

        status = (
            f"{emoji} Signal: {signal.get('signal', 'HOLD')} ({conf:.1f}%) | "
            f"Positions: {len(positions)} | "
            f"Capital: ${capital:.2f} | "
            f"{datetime.now().strftime('%H:%M:%S')}"
        )

        print(status)

    def log_signal(self, signal: Dict):
        """Log signal to history"""
        self.last_signal = signal
        self.signal_history.append({
            'timestamp': datetime.now(),
            'signal': signal
        })

    def get_signal_statistics(self) -> Dict:
        """Get signal statistics"""
        if not self.signal_history:
            return {}

        buy_signals = sum(1 for s in self.signal_history if s['signal']['signal'] == 'BUY')
        sell_signals = sum(1 for s in self.signal_history if s['signal']['signal'] == 'SELL')
        hold_signals = sum(1 for s in self.signal_history if s['signal']['signal'] == 'HOLD')

        return {
            'total_signals': len(self.signal_history),
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'hold_signals': hold_signals
        }

    def display_help(self):
        """Display available commands"""
        print("\n" + "="*60)
        print("AVAILABLE COMMANDS")
        print("="*60)
        print("  status    - Show current status")
        print("  positions - Show open positions")
        print("  stats     - Show performance statistics")
        print("  signal    - Show last signal details")
        print("  stop      - Stop the bot")
        print("  help      - Show this help message")
        print("="*60 + "\n")

# Create global monitor instance
monitor = Monitor()

