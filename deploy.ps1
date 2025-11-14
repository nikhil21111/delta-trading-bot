# Fly.io Deployment Script for Trading Bot
# Run this script to deploy your bot to the cloud

Write-Host "`n" -NoNewline
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  FLY.IO DEPLOYMENT WIZARD - Delta Trading Bot" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if fly CLI is installed
Write-Host "Step 1: Checking Fly.io CLI..." -ForegroundColor Yellow
if (-not (Get-Command fly -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Fly.io CLI not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installing Fly.io CLI..." -ForegroundColor Yellow
    iwr https://fly.io/install.ps1 -useb | iex
    Write-Host "SUCCESS: Fly.io CLI installed!" -ForegroundColor Green
    Write-Host "WARNING: Please close and reopen PowerShell, then run this script again." -ForegroundColor Yellow
    exit
} else {
    Write-Host "SUCCESS: Fly.io CLI found!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 2: Login to Fly.io..." -ForegroundColor Yellow
Write-Host "Your browser will open. Please login or create a free account." -ForegroundColor White
Start-Sleep -Seconds 2
fly auth login

Write-Host ""
Write-Host "Step 3: Configure Secrets..." -ForegroundColor Yellow
Write-Host "You need to provide your API credentials." -ForegroundColor White
Write-Host ""

# Check if .env exists
if (Test-Path ".env") {
    Write-Host "Found .env file. Do you want to use credentials from it? (Y/N)" -ForegroundColor Cyan
    $useEnv = Read-Host
    
    if ($useEnv -eq "Y" -or $useEnv -eq "y") {
        Write-Host "Reading from .env file..." -ForegroundColor Yellow
        
        # Read .env file
        $envContent = Get-Content .env
        $secrets = @{}
        
        foreach ($line in $envContent) {
            # Skip comments and empty lines
            if ($line -match '^\s*#' -or $line -match '^\s*$') {
                continue
            }
            
            if ($line -match '^([^=]+)=(.+)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim().Trim('"')
                
                # Only add valid keys (no comments)
                if ($key -notmatch '#') {
                    $secrets[$key] = $value
                }
            }
        }
        
        Write-Host "SUCCESS: Loaded secrets from .env" -ForegroundColor Green
    }
} else {
    Write-Host "WARNING: No .env file found. You'll need to enter credentials manually." -ForegroundColor Yellow
    $secrets = @{}
}

# Prompt for required secrets if not in .env
if (-not $secrets["DELTA_API_KEY"]) {
    $secrets["DELTA_API_KEY"] = Read-Host "Enter DELTA_API_KEY"
}
if (-not $secrets["DELTA_API_SECRET"]) {
    $secrets["DELTA_API_SECRET"] = Read-Host "Enter DELTA_API_SECRET"
}
if (-not $secrets["TELEGRAM_BOT_TOKEN"]) {
    $secrets["TELEGRAM_BOT_TOKEN"] = Read-Host "Enter TELEGRAM_BOT_TOKEN"
}
if (-not $secrets["TELEGRAM_CHAT_ID"]) {
    $secrets["TELEGRAM_CHAT_ID"] = Read-Host "Enter TELEGRAM_CHAT_ID"
}

Write-Host ""
Write-Host "Step 4: Creating Fly.io App..." -ForegroundColor Yellow

# Get app name from fly.toml or prompt for one
if (Test-Path "fly.toml") {
    $appName = (Select-String -Path "fly.toml" -Pattern 'app = "(.+)"').Matches.Groups[1].Value
    Write-Host "Found existing app name: $appName" -ForegroundColor Green
    
    # Check if app exists on Fly.io
    $appExists = fly apps list 2>$null | Select-String -Pattern $appName -Quiet
    
    if (-not $appExists) {
        Write-Host "App doesn't exist on Fly.io. Creating it..." -ForegroundColor Yellow
        fly apps create $appName --org personal
    } else {
        Write-Host "App already exists on Fly.io!" -ForegroundColor Green
    }
} else {
    Write-Host "Creating new app (this will prompt for app name)..." -ForegroundColor White
    fly launch --no-deploy
    
    # Get the app name from newly created fly.toml
    $appName = (Select-String -Path "fly.toml" -Pattern 'app = "(.+)"').Matches.Groups[1].Value
}

Write-Host ""
Write-Host "Step 5: Creating Persistent Volume..." -ForegroundColor Yellow
Write-Host "Creating 1GB volume for database and logs..." -ForegroundColor White

fly volumes create data --region sin --size 1 --app $appName

Write-Host ""
Write-Host "Step 6: Setting Secrets..." -ForegroundColor Yellow
Write-Host "Uploading your API credentials (encrypted)..." -ForegroundColor White

# Filter out important secrets only
$importantKeys = @(
    "DELTA_API_KEY",
    "DELTA_API_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_BOT_TOKENS_EXTRA",
    "TELEGRAM_CHAT_IDS_EXTRA",
    "INITIAL_CAPITAL",
    "LEVERAGE",
    "RISK_PERCENTAGE",
    "TRADING_PAIR"
)

foreach ($key in $importantKeys) {
    if ($secrets.ContainsKey($key) -and $secrets[$key]) {
        Write-Host "  Setting $key..." -ForegroundColor Gray
        fly secrets set "$key=$($secrets[$key])" --app $appName 2>$null
    }
}

Write-Host ""
Write-Host "Step 7: Deploying to Cloud..." -ForegroundColor Yellow
Write-Host "Building Docker image and deploying (this may take 2-3 minutes)..." -ForegroundColor White
Write-Host ""

fly deploy --app $appName

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "SUCCESS: Your bot is now running 24/7 in the cloud!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Control from Telegram:" -ForegroundColor Yellow
Write-Host "   /start      - Get started" -ForegroundColor White
Write-Host "   /status     - Check bot status" -ForegroundColor White
Write-Host "   /balance    - View account balance" -ForegroundColor White
Write-Host "   /positions  - See open positions" -ForegroundColor White
Write-Host "   /emergency  - Close all positions NOW" -ForegroundColor White
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Yellow
Write-Host "   fly status --app $appName" -ForegroundColor White
Write-Host "   fly logs --app $appName" -ForegroundColor White
Write-Host "   fly ssh console --app $appName" -ForegroundColor White
Write-Host ""
Write-Host "Cost: $0/month (Free tier)" -ForegroundColor Green
Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
