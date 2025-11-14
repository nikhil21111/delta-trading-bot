# Fly.io Deployment Guide - Delta Exchange Trading Bot

Complete guide to deploy your trading bot to Fly.io for 24/7 operation with mobile control.

---

## 📋 Prerequisites

1. **Fly.io Account** (FREE)
   - Sign up at https://fly.io/app/sign-up
   - Credit card required for verification (won't be charged on free tier)

2. **Fly.io CLI** installed
   ```powershell
   # Install via PowerShell
   pwsh -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

3. **API Credentials Ready**
   - Delta Exchange API Key & Secret
   - Telegram Bot Token & Chat ID

---

## 🚀 Deployment Steps

### **Step 1: Login to Fly.io**

```powershell
# Open PowerShell in your project folder
cd C:\Users\vekar\Desktop\chatbot

# Login to Fly.io
fly auth login
```

Your browser will open for authentication.

---

### **Step 2: Launch Your App**

```powershell
# Create and configure your app
fly launch --no-deploy

# When prompted:
# - App name: delta-trading-bot (or choose your own)
# - Region: Singapore (sin) or closest to you
# - Postgres database: NO
# - Redis database: NO
```

This creates `fly.toml` (already provided in your project).

---

### **Step 3: Create Persistent Volume**

Your database and logs need persistent storage:

```powershell
# Create 1GB volume for data persistence
fly volumes create data --region sin --size 1
```

---

### **Step 4: Set Environment Variables (Secrets)**

**CRITICAL:** Never commit API keys to code. Set them as secrets:

```powershell
# Delta Exchange API credentials
fly secrets set DELTA_API_KEY="your_delta_api_key_here"
fly secrets set DELTA_API_SECRET="your_delta_api_secret_here"

# Telegram Bot credentials
fly secrets set TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
fly secrets set TELEGRAM_CHAT_ID="your_telegram_chat_id"

# Optional: Additional Telegram accounts
fly secrets set TELEGRAM_BOT_TOKENS_EXTRA="token1,token2"
fly secrets set TELEGRAM_CHAT_IDS_EXTRA="chatid1,chatid2"

# Optional: Sonar API (for sentiment analysis)
fly secrets set SONAR_API_KEY="your_sonar_api_key"

# Trading Configuration (optional - has defaults)
fly secrets set INITIAL_CAPITAL="100.0"
fly secrets set LEVERAGE="10"
fly secrets set RISK_PERCENTAGE="3.0"
fly secrets set TRADING_PAIR="BTCUSD"
```

**View set secrets:**
```powershell
fly secrets list
```

---

### **Step 5: Deploy to Fly.io**

```powershell
# Deploy your bot
fly deploy

# This will:
# 1. Build Docker image
# 2. Push to Fly.io registry
# 3. Start your bot in the cloud
```

Wait 2-3 minutes for deployment to complete.

---

### **Step 6: Verify Deployment**

```powershell
# Check app status
fly status

# View live logs
fly logs

# Check if bot is running
fly ssh console
# Inside VM: ps aux | grep python
# Exit: exit
```

You should receive a Telegram notification: "🤖 Trading Bot Started"

---

## 📱 Remote Control via Telegram

Once deployed, control your bot from anywhere using Telegram commands:

### **Available Commands:**

```
/start    - Show help and available commands
/status   - View bot status (running/paused, open positions)
/balance  - Check account balance
/positions - View all open positions with P&L
/stats    - Trading statistics (win rate, total P&L)
/pause    - Pause trading (stop opening new trades)
/resume   - Resume trading
/emergency - Close ALL positions immediately and pause
/help     - Show command list
```

### **Example Usage:**

1. **On your mobile**, open Telegram
2. Go to your bot chat
3. Type `/status` to check bot status
4. Type `/positions` to see open trades
5. Type `/emergency` if you need to exit all positions NOW

---

## 🔍 Monitoring & Management

### **View Real-time Logs:**
```powershell
# Stream logs (Ctrl+C to stop)
fly logs
```

### **Check Resource Usage:**
```powershell
fly status
fly vm status
```

### **Restart Bot:**
```powershell
fly apps restart delta-trading-bot
```

### **Stop Bot:**
```powershell
fly apps pause delta-trading-bot
```

### **Start Bot:**
```powershell
fly apps resume delta-trading-bot
```

---

## 💾 Database Backup

Your trade history is stored in `/data/trading_bot.db`

### **Download Database:**
```powershell
# SSH into your VM
fly ssh console

# Inside VM, copy database
cat /data/trading_bot.db > /tmp/backup.db

# Exit VM
exit

# Download from your local machine
fly ssh sftp get /data/trading_bot.db ./trading_bot_backup.db
```

### **Automated Backup (Optional):**

Add to your `.env` or create a backup script that runs weekly.

---

## 🛠️ Troubleshooting

### **Bot Not Starting:**

```powershell
# Check logs for errors
fly logs

# Common issues:
# 1. Missing secrets → fly secrets list
# 2. Invalid API keys → Check Delta Exchange dashboard
# 3. Database permission → Verify volume mount
```

### **Out of Memory:**

```powershell
# Upgrade to larger VM (no longer free)
fly scale vm shared-cpu-2x --memory 512
```

### **Bot Not Responding to Telegram:**

1. Check if bot token is correct: `fly secrets list`
2. Verify chat ID matches your Telegram account
3. Make sure bot is started: `/start` in Telegram
4. Check logs: `fly logs`

### **Database Corruption:**

```powershell
# SSH into VM
fly ssh console

# Delete corrupted database (bot will recreate)
rm /data/trading_bot.db

# Restart bot
exit
fly apps restart
```

---

## 💰 Cost Breakdown

### **Fly.io Free Tier:**
- ✅ **3 shared-cpu VMs** (256MB RAM each)
- ✅ **3GB persistent storage**
- ✅ **160GB outbound data/month**

**Your Bot Usage:**
- 1 VM (256MB) = FREE ✅
- 1GB volume = FREE ✅
- API calls ~1GB/month = FREE ✅

**Total Cost: $0/month** (within free tier limits)

### **If You Need More:**
- Upgrade to 512MB RAM: ~$3/month
- Larger volume: ~$0.15/GB/month

---

## 🔄 Updating Your Bot

When you make code changes:

```powershell
# 1. Commit changes to Git (optional but recommended)
git add .
git commit -m "Updated trading strategy"

# 2. Deploy new version
fly deploy

# 3. Check logs to verify
fly logs
```

**Zero-downtime deployment!** Fly.io replaces old instance with new one.

---

## 🔐 Security Best Practices

1. ✅ **Never commit `.env` file** (already in `.gitignore`)
2. ✅ **Use Fly.io secrets** for API keys (not hardcoded)
3. ✅ **Restrict Telegram bot** to your chat ID only
4. ✅ **Enable 2FA** on Delta Exchange account
5. ✅ **Use API key with trading permissions only** (not withdrawal)
6. ✅ **Set IP whitelist** on Delta Exchange (optional)

---

## 📊 Performance Optimization

### **Reduce API Calls:**
```powershell
# Increase check interval (in main.py)
# Change from 60s to 120s for less frequent checks
```

### **Lower Memory Usage:**
- Reduce indicator periods in `config.py`
- Disable unused features

---

## 🆘 Emergency Shutdown

### **From Telegram:**
```
/emergency  (closes all positions + pauses bot)
```

### **From Laptop:**
```powershell
# Immediately stop bot
fly apps pause delta-trading-bot

# Or destroy completely
fly apps destroy delta-trading-bot
```

---

## 📈 Next Steps

Once deployed and running:

1. ✅ **Test with small capital** ($10-50) first
2. ✅ **Monitor for 1 week** in live mode
3. ✅ **Check Telegram alerts** are working
4. ✅ **Practice emergency commands** (`/emergency`)
5. ✅ **Review logs daily** for first week
6. ✅ **Gradually increase capital** if profitable

---

## 🎓 Useful Commands Cheat Sheet

```powershell
# Deployment
fly deploy                          # Deploy/update bot
fly status                          # Check status
fly logs                            # View logs
fly ssh console                     # SSH into VM

# Management
fly apps restart <app-name>         # Restart bot
fly apps pause <app-name>           # Stop bot
fly apps resume <app-name>          # Start bot
fly apps destroy <app-name>         # Delete app

# Secrets
fly secrets set KEY=value           # Set secret
fly secrets list                    # List secrets
fly secrets unset KEY               # Remove secret

# Volumes
fly volumes list                    # List volumes
fly volumes create <name>           # Create volume
fly volumes destroy <id>            # Delete volume

# Scaling
fly scale count 1                   # Number of instances
fly scale vm shared-cpu-2x          # Upgrade VM size
```

---

## 📞 Support

- **Fly.io Docs:** https://fly.io/docs/
- **Fly.io Community:** https://community.fly.io/
- **Bot Issues:** Check `fly logs` first
- **Trading Issues:** Review `trading_bot.log` via SSH

---

## ✅ Deployment Checklist

Before going live:

- [ ] Fly.io account created and CLI installed
- [ ] All API credentials obtained (Delta + Telegram)
- [ ] Secrets configured via `fly secrets set`
- [ ] Volume created for data persistence
- [ ] Bot deployed successfully (`fly deploy`)
- [ ] Telegram commands tested (`/status`, `/balance`)
- [ ] Emergency stop tested (`/emergency`)
- [ ] Logs monitored for errors (`fly logs`)
- [ ] Small test trade executed successfully
- [ ] Daily monitoring plan established

---

**You're ready to trade 24/7 from anywhere! 🚀📈**

Control your bot from your phone while traveling, sleeping, or working. Your automated trading system is now live in the cloud.
