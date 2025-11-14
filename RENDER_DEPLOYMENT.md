# Render.com Deployment Guide - 100% FREE (No Credit Card!)

Deploy your Delta Exchange trading bot to Render.com for 24/7 operation - completely free, no credit card required.

---

## ✅ Why Render.com?

- ✅ **100% FREE** - No credit card needed
- ✅ **750 hours/month** - Enough for 24/7 running
- ✅ **Easy deployment** - Connect GitHub and deploy
- ✅ **Persistent storage** - Database saved across restarts
- ✅ **Auto-restart** - If bot crashes, it restarts automatically

---

## 🚀 Deployment Steps (5 Minutes)

### **Step 1: Push Code to GitHub**

```powershell
# Initialize git (if not already done)
git init
git add .
git commit -m "Trading bot ready for deployment"

# Create repo on GitHub and push
# Go to: https://github.com/new
# Create repo named: delta-trading-bot
# Then run:

git remote add origin https://github.com/YOUR_USERNAME/delta-trading-bot.git
git branch -M main
git push -u origin main
```

### **Step 2: Sign Up on Render.com**

1. Go to: **https://render.com**
2. Click **"Get Started"**
3. Sign up with **GitHub** (easiest - auto-connects your repos)
4. ✅ No credit card needed!

### **Step 3: Create New Web Service**

1. Click **"New +"** → **"Web Service"**
2. Connect your **delta-trading-bot** repository
3. Configure:
   - **Name:** `delta-trading-bot`
   - **Region:** `Singapore` (closest to markets)
   - **Branch:** `main`
   - **Runtime:** `Docker`
   - **Instance Type:** `Free`

### **Step 4: Add Environment Variables**

In the **Environment** section, add these secrets:

```
DELTA_API_KEY=your_delta_api_key
DELTA_API_SECRET=your_delta_api_secret
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_BOT_TOKENS_EXTRA=token2,token3 (optional)
TELEGRAM_CHAT_IDS_EXTRA=chatid2,chatid3 (optional)
INITIAL_CAPITAL=5.0
LEVERAGE=10
RISK_PERCENTAGE=3.0
TRADING_PAIR=ETHUSD
PRODUCTION=true
```

### **Step 5: Add Persistent Disk**

1. Scroll to **"Disk"** section
2. Click **"Add Disk"**
3. Configure:
   - **Name:** `data`
   - **Mount Path:** `/data`
   - **Size:** `1 GB` (free tier)

### **Step 6: Deploy!**

1. Click **"Create Web Service"**
2. Render will:
   - Build your Docker image
   - Deploy to cloud
   - Start your bot
3. **Wait 3-5 minutes** for first deployment

---

## 📱 Control Your Bot

Once deployed, you'll receive a Telegram message: **"🤖 Trading Bot Started"**

### **Telegram Commands:**
```
/start      - Get started
/status     - Check bot status
/balance    - View account balance
/positions  - See open positions
/pause      - Pause trading
/resume     - Resume trading
/emergency  - Close all positions NOW
/stats      - Trading statistics
```

---

## 🔍 Monitoring

### **View Logs:**
1. Go to your Render dashboard
2. Click on your service
3. Click **"Logs"** tab
4. See real-time bot activity

### **Restart Bot:**
1. Dashboard → Your service
2. Click **"Manual Deploy"** → **"Clear build cache & deploy"**

### **Check Status:**
- Dashboard shows if bot is running
- Green = Running ✅
- Red = Stopped ❌

---

## ⚠️ Important: Free Tier Limitations

### **Auto-Sleep After 15 Minutes:**
Render's free tier **spins down after 15 minutes of inactivity**.

**For trading bot (needs 24/7):**

**Option A: Upgrade to Paid ($7/month)**
- Go to Settings → Instance Type → Select "Starter ($7/mo)"
- Stays on 24/7, never sleeps

**Option B: Use Cron Job (Keep Free Tier Awake)**
- Add a cron job to ping your service every 14 minutes
- Create a health endpoint in your bot
- Use cron-job.org or similar to ping it

**Option C: Accept Sleep (Not Ideal for Trading)**
- Bot sleeps after 15 min inactivity
- Wakes up when needed (but might miss trades)

### **Recommended:**
For serious trading, upgrade to **$7/month Starter plan** for 24/7 operation.

---

## 🔄 Alternative: Keep Free Tier Awake

Add this to your `main.py` to create a health endpoint:

```python
# Add at top of main.py
from aiohttp import web
import asyncio

async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_health_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

# In main() function, add:
asyncio.create_task(start_health_server())
```

Then use **cron-job.org** to ping `https://your-app.onrender.com/health` every 14 minutes.

---

## 💾 Database Backup

### **Download Database:**
1. Render Dashboard → Your service
2. Click **"Shell"** tab
3. Run:
   ```bash
   cat /data/trading_bot.db > /tmp/backup.db
   ```
4. Download from /tmp/backup.db

### **Automated Backup:**
Add a daily cron in your bot to upload database to Google Drive or Dropbox.

---

## 🛠️ Troubleshooting

### **Bot Not Starting:**
1. Check logs in Render dashboard
2. Verify all environment variables are set
3. Check DELTA_API_KEY and TELEGRAM_BOT_TOKEN are correct

### **No Telegram Notifications:**
1. Verify TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
2. Check logs for Telegram connection errors
3. Test locally first: `py main.py`

### **Database Not Persisting:**
1. Verify disk is mounted at `/data`
2. Check disk size (must be > 0 GB)
3. Logs should show: "Database initialized successfully"

### **Bot Sleeping (Free Tier):**
1. Upgrade to Starter plan ($7/mo)
2. OR set up health check + cron job
3. OR accept that bot may miss some signals

---

## 💰 Cost Comparison

| Platform | Free Tier | Always-On Cost | Credit Card Required |
|----------|-----------|----------------|---------------------|
| **Render.com** | ✅ 750hrs/mo | $7/month | ❌ NO |
| Fly.io | ✅ 256MB RAM | $0 (within limits) | ✅ YES |
| Railway.app | ❌ None | $5/month | ✅ YES |
| Heroku | ❌ None | $7/month | ✅ YES |

**Recommendation:** Start with Render.com free tier, upgrade to $7/mo if you want 24/7 trading.

---

## ✅ Quick Start Checklist

- [ ] Code pushed to GitHub
- [ ] Render.com account created (no card needed)
- [ ] Web service created and connected to repo
- [ ] Environment variables added (API keys, etc.)
- [ ] Persistent disk added (1GB at /data)
- [ ] Service deployed successfully
- [ ] Telegram notification received
- [ ] `/status` command tested
- [ ] Consider upgrading to $7/mo for 24/7

---

## 🎯 Next Steps After Deployment

1. **Test Commands:**
   - Send `/status` to your Telegram bot
   - Try `/balance` to verify API connection
   - Test `/emergency` (will close positions)

2. **Monitor First 24 Hours:**
   - Check logs regularly
   - Watch for trading signals
   - Verify positions open/close correctly

3. **Upgrade if Needed:**
   - If bot sleeps → Upgrade to Starter ($7/mo)
   - If need more storage → Increase disk size

4. **Set Up Monitoring:**
   - Enable Telegram notifications for all trades
   - Check dashboard daily
   - Review logs weekly

---

**You're ready to deploy! 🚀**

No credit card needed - just connect GitHub and deploy in 5 minutes!
