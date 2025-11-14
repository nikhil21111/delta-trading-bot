"""
Startup Script - Runs both trading bot and web dashboard
"""
import asyncio
import sys
import os
from multiprocessing import Process
import uvicorn

def run_web_server():
    """Run FastAPI web server"""
    print("🌐 Starting web dashboard on port 8080...")
    uvicorn.run(
        "web_dashboard.app:app",
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )

async def run_trading_bot():
    """Run trading bot"""
    from main import TradingBot
    
    # Get mode from command line argument
    mode = sys.argv[1] if len(sys.argv) > 1 else 'PAPER'
    
    bot = TradingBot(mode=mode)
    await bot.run()

def main():
    """Main startup function"""
    print("=" * 70)
    print("  DELTA EXCHANGE TRADING BOT WITH WEB DASHBOARD")
    print("=" * 70)
    
    # Start web server in separate process
    web_process = Process(target=run_web_server, daemon=True)
    web_process.start()
    
    # Give web server time to start
    import time
    time.sleep(2)
    
    # Run trading bot in main process
    try:
        asyncio.run(run_trading_bot())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        web_process.terminate()
        web_process.join()

if __name__ == "__main__":
    main()
