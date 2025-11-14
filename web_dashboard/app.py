"""
FastAPI Web Dashboard Application
Provides web interface for trading bot monitoring and control
"""
from fastapi import FastAPI, Request, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from datetime import timedelta

from web_dashboard.auth import (
    UserManager, create_access_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from bot_interface import bot_interface
from database import db
from config import config

# Create FastAPI app
app = FastAPI(
    title="Trading Bot Dashboard",
    description="Secure web interface for Delta Exchange trading bot",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="web_dashboard/static"), name="static")
templates = Jinja2Templates(directory="web_dashboard/templates")

# Initialize user manager
user_manager = UserManager(db)

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class ControlRequest(BaseModel):
    action: str  # pause, resume, stop, emergency

# ============================================================================
# Authentication Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to login page"""
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/login")
async def login(login_data: LoginRequest):
    """Handle login"""
    user = user_manager.authenticate_user(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"]
    }

@app.get("/logout")
async def logout():
    """Logout (client-side token removal)"""
    return RedirectResponse(url="/login")

# ============================================================================
# Dashboard Pages (Protected)
# ============================================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "trading_pair": config.TRADING_PAIR,
        "timeframe": config.TIMEFRAME
    })

@app.get("/trades", response_class=HTMLResponse)
async def trades_page(request: Request):
    """Trades history page"""
    return templates.TemplateResponse("trades.html", {"request": request})

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics page"""
    return templates.TemplateResponse("analytics.html", {"request": request})

# ============================================================================
# API Endpoints (Protected)
# ============================================================================

@app.get("/api/status")
async def get_status(current_user: dict = Depends(get_current_user)):
    """Get bot status"""
    status_data = bot_interface.get_status()
    return status_data

@app.get("/api/balance")
async def get_balance(current_user: dict = Depends(get_current_user)):
    """Get account balance"""
    balance_data = await bot_interface.get_balance()
    return balance_data

@app.get("/api/positions")
async def get_positions(current_user: dict = Depends(get_current_user)):
    """Get open positions"""
    positions_data = await bot_interface.get_positions()
    return positions_data

@app.get("/api/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """Get trading statistics"""
    stats_data = bot_interface.get_stats()
    performance = bot_interface.get_performance_stats()
    
    return {
        "stats_text": stats_data.get("stats_text", ""),
        "performance": performance,
        "timestamp": stats_data.get("timestamp", "")
    }

@app.get("/api/trades")
async def get_trades(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get recent trades"""
    trades = bot_interface.get_recent_trades(limit)
    return {"trades": trades, "count": len(trades)}

@app.post("/api/control")
async def control_bot(
    control_data: ControlRequest,
    current_user: dict = Depends(get_current_user)
):
    """Control bot (pause, resume, stop, emergency)"""
    action = control_data.action.lower()
    
    if action == "pause":
        result = await bot_interface.pause_trading()
    elif action == "resume":
        result = await bot_interface.resume_trading()
    elif action == "stop":
        result = await bot_interface.stop_bot()
    elif action == "emergency":
        result = await bot_interface.emergency_stop()
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    return result

# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    bot_interface.subscribe(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Send current status on request
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "status": bot_interface.get_status()
                })
                
    except WebSocketDisconnect:
        bot_interface.unsubscribe(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        bot_interface.unsubscribe(websocket)

# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("🌐 Web dashboard starting...")
    
    # Create default admin user if no users exist
    if user_manager.get_user_count() == 0:
        default_username = os.getenv("WEB_USERNAME", "admin")
        default_password = os.getenv("WEB_PASSWORD", "admin123")
        
        if user_manager.create_user(default_username, default_password):
            print(f"✅ Default user created: {default_username}")
        else:
            print("⚠️ Failed to create default user")
    
    print("✅ Web dashboard ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Web dashboard shutting down...")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {"status": "healthy", "service": "trading-bot-dashboard"}
