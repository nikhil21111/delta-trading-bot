"""
Quick test script to verify Telegram bot configuration
"""
import asyncio
from telegram_bot import telegram_notifier

async def test_telegram():
    """Test Telegram bot connection"""
    print("🧪 Testing Telegram Bot...")
    print("=" * 50)
    
    # Test connection
    print("\n1️⃣ Testing connection...")
    connected = await telegram_notifier.test_connection()
    
    if connected:
        print("✅ Connection successful!")
        
        # Send test message
        print("\n2️⃣ Sending test notification...")
        await telegram_notifier.send_message(
            "🎉 <b>Test Notification</b>\n\n"
            "✅ Your trading bot is connected!\n"
            "📱 Telegram notifications are working perfectly.\n\n"
            "Ready to start trading! 🚀"
        )
        print("✅ Test message sent to Telegram!")
        print("\n📱 Check your Telegram app for the message!")
    else:
        print("❌ Connection failed!")
        print("\nPlease check:")
        print("  - Bot token is correct")
        print("  - Chat ID is correct")
        print("  - Bot is started (send /start to your bot)")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(test_telegram())
