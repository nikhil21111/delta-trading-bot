# Web Dashboard Deployment Guide

## 🌐 Web Dashboard Features

Your trading bot now includes a **secure web dashboard** accessible from any device:

### Features
- ✅ **Secure Login** - Username/password authentication with JWT tokens
- 📊 **Real-time Dashboard** - Live bot status, balance, positions, P&L
- 🎮 **Control Panel** - Pause/resume trading, emergency stop
- 📈 **Trade History** - View all past trades with filters
- 📉 **Analytics** - Win/loss charts, performance metrics
- 📱 **Mobile Responsive** - Works on phone, tablet, laptop
- 🔄 **Auto-refresh** - Live updates via WebSocket every 10 seconds

---

## 🚀 Quick Start

### 1. Local Testing

```powershell
# Install new dependencies
pip install -r requirements.txt

# Run both bot and web dashboard
python start_all.py PAPER

# Access dashboard at:
http://localhost:8080
```

**Default Login:**
- Username: `admin`
- Password: `admin123`

### 2. Render.com Deployment

#### Add Environment Variables

Go to your Render service → Environment tab and add:

```
# Existing variables (already set)
DELTA_API_KEY=your_api_key
DELTA_API_SECRET=your_api_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
PRODUCTION=true

# New web dashboard variables
WEB_USERNAME=admin
WEB_PASSWORD=your_secure_password_here
WEB_SECRET_KEY=random-secret-key-change-this-2024
```

**Important:**
- Change `WEB_PASSWORD` to something secure
- Generate a random `WEB_SECRET_KEY` (any random 32+ character string)

#### Deploy

```powershell
# Commit and push changes
git add .
git commit -m "Add web dashboard with secure login"
git push origin main
```

Render will auto-deploy in 1-2 minutes.

---

## 📱 Accessing the Dashboard

### On Render.com

Your dashboard URL will be:
```
https://delta-trading-bot.onrender.com
```

### Pages

1. **Login** - `/login` - Enter username/password
2. **Dashboard** - `/dashboard` - Main control panel
3. **Trades** - `/trades` - Trade history table
4. **Analytics** - `/analytics` - Charts and statistics

### Mobile Access

1. Open browser on your phone
2. Go to dashboard URL
3. Login with credentials
4. Add to home screen for app-like experience

---

## 🎮 Control Panel Actions

### From Dashboard

- **Resume Trading** - Start accepting new trade signals
- **Pause Trading** - Stop opening new positions (keeps existing ones)
- **Emergency Stop** - Close ALL positions immediately
- **Refresh** - Manually refresh all data

### From Telegram

All telegram commands still work:
- `/status` - Bot status
- `/balance` - Account balance
- `/positions` - Open positions
- `/pause` - Pause trading
- `/resume` - Resume trading
- `/stop` - Stop bot completely
- `/emergency` - Emergency close all

---

## 🔒 Security Features

✅ **JWT Authentication** - Industry-standard token-based auth  
✅ **Password Hashing** - Bcrypt encryption (passwords never stored plain)  
✅ **Session Timeout** - 8-hour auto-logout  
✅ **HTTPS** - Render provides free SSL certificate  
✅ **CORS Protection** - Only authorized origins  
✅ **Secure Cookies** - HttpOnly, SameSite protection  

### Change Password

To change your dashboard password on Render:

1. Go to Environment tab
2. Update `WEB_PASSWORD` variable
3. Click "Save Changes"
4. Service will restart automatically

---

## 📊 Dashboard Features Explained

### Home Dashboard

**Status Cards:**
- Bot Status - ACTIVE/PAUSED
- Balance - Total account balance
- Open Positions - Number of active trades
- Total P&L - Overall profit/loss

**Control Panel:**
- Quick action buttons
- Real-time status updates
- WebSocket live connection indicator

**Positions Table:**
- Live P&L updates every 10 seconds
- Color-coded (green profit, red loss)
- Shows entry price, size, current P&L

**Statistics Panel:**
- Total trades executed
- Win rate percentage
- Total P&L amount
- Profit factor

### Trades Page

Complete history of all trades:
- Date/time of entry and exit
- Pair, side (BUY/SELL)
- Entry/exit prices
- Position size and leverage
- P&L in $ and %
- Exit reason (TP/SL/Manual)

### Analytics Page

**Performance Metrics:**
- Total trades
- Win rate
- Profit factor
- Max drawdown

**Charts:**
- Win/Loss pie chart
- P&L distribution histogram

---

## 🛠️ Troubleshooting

### Can't Access Dashboard

1. **Check Render status** - Service must be "Live" (green)
2. **Check logs** - Look for "Web dashboard ready" message
3. **Check URL** - Use HTTPS (not HTTP)
4. **Clear cache** - Try incognito/private mode

### Login Not Working

1. **Check credentials** - Username/password case-sensitive
2. **Check environment variables** - WEB_USERNAME, WEB_PASSWORD must be set
3. **Clear browser storage** - Clear localStorage
4. **Check logs** - Look for authentication errors

### Data Not Loading

1. **Check WebSocket** - Look for "Connected" indicator (green)
2. **Check bot status** - Bot must be running
3. **Refresh page** - F5 or refresh button
4. **Check console** - F12 → Console tab for errors

### Historical Data Error

The error "Failed to fetch historical data" occurs in BACKTEST mode when:
- Delta Exchange API doesn't have enough historical data
- Symbol format is incorrect (use `ETHUSD` not `ETH/USD`)
- Time range is too large

**Solution:** Use PAPER or LIVE mode instead of BACKTEST

---

## 💡 Pro Tips

### Mobile App Experience

1. Visit dashboard on phone browser
2. Click browser menu → "Add to Home Screen"
3. Icon appears on home screen
4. Opens like a native app!

### Multiple Devices

- Login works from multiple devices simultaneously
- Each device gets its own session token
- All see same real-time data

### Auto-refresh

Dashboard auto-refreshes every 10 seconds:
- Position P&L updates
- Balance updates
- Status changes
- No need to manually refresh!

### WebSocket Real-time

When bot takes action:
- New trade → Instant notification
- Status change → Instant update
- Emergency stop → Instant alert

---

## 🔄 What Changed

### New Files
```
web_dashboard/
├── __init__.py
├── app.py              # FastAPI application
├── auth.py             # Authentication system
├── static/
│   └── css/
│       └── style.css   # Custom styling
└── templates/
    ├── base.html       # Base template
    ├── login.html      # Login page
    ├── dashboard.html  # Main dashboard
    ├── trades.html     # Trade history
    └── analytics.html  # Analytics page

bot_interface.py        # Bridge between bot and web
start_all.py           # Startup script for both services
```

### Modified Files
- `main.py` - Added bot_interface integration
- `requirements.txt` - Added FastAPI, uvicorn, JWT libs
- `Dockerfile` - Runs both bot and web server
- `data_manager_delta.py` - Improved error logging

---

## 📞 Support

If you encounter issues:

1. **Check Render Logs** - Dashboard → Logs tab
2. **Check Browser Console** - F12 → Console
3. **Test Telegram Bot** - Use `/status` command
4. **Restart Service** - Render dashboard → Manual Deploy → Clear cache and deploy

---

## 🎉 You're All Set!

Your trading bot now has:
- ✅ Telegram bot control (mobile notifications)
- ✅ Web dashboard (visual monitoring)
- ✅ 24/7 cloud deployment (Render.com)
- ✅ Secure authentication (password protected)
- ✅ Real-time updates (WebSocket)
- ✅ Mobile responsive (works on phone)

**Access from anywhere, control from mobile and laptop!** 🚀
