"""
Bot Interface Bridge
Safely connects web dashboard with TradingBot instance
"""
import asyncio
from typing import Optional, Dict, List
from datetime import datetime

class BotInterface:
    """Thread-safe interface between web dashboard and trading bot"""
    
    def __init__(self):
        self.bot = None
        self.lock = asyncio.Lock()
        self._subscribers = []  # WebSocket subscribers for real-time updates
    
    def set_bot(self, bot):
        """Set reference to trading bot instance"""
        self.bot = bot
    
    def get_status(self) -> Dict:
        """Get bot status"""
        if not self.bot:
            return {
                "mode": "NOT_RUNNING",
                "trading_enabled": False,
                "open_positions": 0,
                "error": "Bot not initialized"
            }
        
        try:
            status_text = self.bot.get_status()
            open_positions = len(self.bot.trade_executor.get_open_positions()) if self.bot.trade_executor else 0
            
            return {
                "mode": self.bot.mode,
                "trading_enabled": self.bot.trading_enabled,
                "running": self.bot.running,
                "open_positions": open_positions,
                "status_text": status_text,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_balance(self) -> Dict:
        """Get account balance"""
        if not self.bot or not self.bot.trade_executor:
            return {"error": "Bot not initialized"}
        
        try:
            async with self.lock:
                balance = await self.bot.get_balance()
                return {"balance_text": balance, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_positions(self) -> Dict:
        """Get open positions"""
        if not self.bot or not self.bot.trade_executor:
            return {"positions": [], "error": "Bot not initialized"}
        
        try:
            async with self.lock:
                positions = self.bot.trade_executor.get_open_positions()
                return {
                    "positions": positions,
                    "count": len(positions),
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {"positions": [], "error": str(e)}
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        if not self.bot:
            return {"error": "Bot not initialized"}
        
        try:
            stats_text = self.bot.get_stats()
            return {"stats_text": stats_text, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            return {"error": str(e)}
    
    async def pause_trading(self) -> Dict:
        """Pause trading"""
        if not self.bot:
            return {"success": False, "message": "Bot not initialized"}
        
        try:
            async with self.lock:
                self.bot.pause_trading()
                await self.broadcast_update({"type": "status_change", "status": "paused"})
                return {"success": True, "message": "Trading paused"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    async def resume_trading(self) -> Dict:
        """Resume trading"""
        if not self.bot:
            return {"success": False, "message": "Bot not initialized"}
        
        try:
            async with self.lock:
                self.bot.resume_trading()
                await self.broadcast_update({"type": "status_change", "status": "active"})
                return {"success": True, "message": "Trading resumed"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    async def stop_bot(self) -> Dict:
        """Stop the bot"""
        if not self.bot:
            return {"success": False, "message": "Bot not initialized"}
        
        try:
            async with self.lock:
                self.bot.stop_bot()
                await self.broadcast_update({"type": "status_change", "status": "stopped"})
                return {"success": True, "message": "Bot stopped"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    async def emergency_stop(self) -> Dict:
        """Emergency stop - close all positions"""
        if not self.bot:
            return {"success": False, "message": "Bot not initialized"}
        
        try:
            async with self.lock:
                result = await self.bot.emergency_stop()
                await self.broadcast_update({"type": "emergency_stop", "message": result})
                return {"success": True, "message": result}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """Get recent trades from database"""
        try:
            from database import db
            
            db.cursor.execute('''
                SELECT 
                    id, timestamp, pair, side, entry_price, exit_price,
                    position_size, leverage, stop_loss, take_profit,
                    pnl, pnl_percentage, exit_reason, signal_score
                FROM trades
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            trades = []
            for row in db.cursor.fetchall():
                trades.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "pair": row[2],
                    "side": row[3],
                    "entry_price": row[4],
                    "exit_price": row[5],
                    "size": row[6],
                    "leverage": row[7],
                    "stop_loss": row[8],
                    "take_profit": row[9],
                    "pnl": row[10],
                    "pnl_percentage": row[11],
                    "exit_reason": row[12],
                    "signal_score": row[13]
                })
            
            return trades
            
        except Exception as e:
            print(f"Error getting recent trades: {e}")
            return []
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics from database"""
        try:
            from database import db
            
            # Get latest performance record
            db.cursor.execute('''
                SELECT 
                    total_trades, winning_trades, losing_trades, win_rate,
                    total_pnl, avg_win, avg_loss, profit_factor,
                    max_drawdown, sharpe_ratio, capital
                FROM performance
                ORDER BY date DESC
                LIMIT 1
            ''')
            
            row = db.cursor.fetchone()
            
            if row:
                return {
                    "total_trades": row[0],
                    "winning_trades": row[1],
                    "losing_trades": row[2],
                    "win_rate": row[3],
                    "total_pnl": row[4],
                    "avg_win": row[5],
                    "avg_loss": row[6],
                    "profit_factor": row[7],
                    "max_drawdown": row[8],
                    "sharpe_ratio": row[9],
                    "capital": row[10]
                }
            
            return {}
            
        except Exception as e:
            print(f"Error getting performance stats: {e}")
            return {}
    
    # WebSocket support
    def subscribe(self, websocket):
        """Add WebSocket subscriber for real-time updates"""
        self._subscribers.append(websocket)
    
    def unsubscribe(self, websocket):
        """Remove WebSocket subscriber"""
        if websocket in self._subscribers:
            self._subscribers.remove(websocket)
    
    async def broadcast_update(self, data: Dict):
        """Broadcast update to all WebSocket subscribers"""
        dead_sockets = []
        
        for ws in self._subscribers:
            try:
                await ws.send_json(data)
            except:
                dead_sockets.append(ws)
        
        # Remove dead connections
        for ws in dead_sockets:
            self.unsubscribe(ws)

# Global bot interface instance
bot_interface = BotInterface()
