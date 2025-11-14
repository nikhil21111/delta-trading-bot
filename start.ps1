# PowerShell startup script for Windows
# Run this script to start the trading bot

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  CoinDCX Crypto Futures Trading Bot Launcher  " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found! Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check if .env file exists
if (-Not (Test-Path ".env")) {
    Write-Host "✗ .env file not found!" -ForegroundColor Red
    Write-Host "  Please copy .env.example to .env and configure it" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Configuration file found" -ForegroundColor Green

# Check if requirements are installed
Write-Host ""
Write-Host "Checking dependencies..." -ForegroundColor Yellow

try {
    python -c "import ccxt, pandas, ta" 2>&1 | Out-Null
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Dependencies not installed" -ForegroundColor Red
    Write-Host "  Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
}

# Show menu
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Select Trading Mode:" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  1. PAPER   - Paper trading (simulation)" -ForegroundColor Green
Write-Host "  2. BACKTEST - Historical backtesting" -ForegroundColor Yellow
Write-Host "  3. LIVE    - Live trading (REAL MONEY)" -ForegroundColor Red
Write-Host "  4. EXIT    - Cancel and exit" -ForegroundColor Gray
Write-Host ""

$choice = Read-Host "Enter your choice (1-4)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Starting PAPER TRADING mode..." -ForegroundColor Green
        Write-Host ""
        python main.py PAPER
    }
    "2" {
        Write-Host ""
        Write-Host "Starting BACKTEST mode..." -ForegroundColor Yellow
        Write-Host ""
        python main.py BACKTEST
    }
    "3" {
        Write-Host ""
        Write-Host "================================================" -ForegroundColor Red
        Write-Host "  ⚠️  WARNING: LIVE TRADING MODE ⚠️" -ForegroundColor Red
        Write-Host "================================================" -ForegroundColor Red
        Write-Host "  You are about to trade with REAL MONEY!" -ForegroundColor Red
        Write-Host "  - Ensure you have tested in PAPER mode first" -ForegroundColor Yellow
        Write-Host "  - Review your API keys and permissions" -ForegroundColor Yellow
        Write-Host "  - Monitor the bot regularly" -ForegroundColor Yellow
        Write-Host "  - Only risk what you can afford to lose" -ForegroundColor Yellow
        Write-Host ""
        $confirm = Read-Host "Type 'START' to confirm live trading"

        if ($confirm -eq "START") {
            Write-Host ""
            Write-Host "Starting LIVE TRADING mode..." -ForegroundColor Red
            Write-Host ""
            python main.py LIVE
        } else {
            Write-Host "Live trading cancelled" -ForegroundColor Yellow
        }
    }
    "4" {
        Write-Host "Exiting..." -ForegroundColor Gray
        exit 0
    }
    default {
        Write-Host "Invalid choice" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Bot stopped. Press Enter to exit..." -ForegroundColor Gray
Read-Host

