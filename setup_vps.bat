@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo  ============================================================
echo   TradeWizard VPS Setup — Full Automated Installation
echo  ============================================================
echo.
echo  This script installs everything needed on a fresh Windows VPS:
echo    1. Python 3.11+
echo    2. Git
echo    3. Node.js + Claude Code CLI
echo    4. MetaTrader 5
echo    5. TradeWizard (clone + dependencies)
echo    6. Cloudflare Tunnel (remote dashboard access)
echo    7. Scheduled Tasks (autostart + watchdog)
echo.
echo  Run this script AS ADMINISTRATOR on the VPS.
echo.
pause

:: ──────────────────────────────────────────────────────────────
::  Step 1: Check admin rights
:: ──────────────────────────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] This script must be run as Administrator!
    echo  Right-click and select "Run as administrator"
    pause
    exit /b 1
)

:: ──────────────────────────────────────────────────────────────
::  Step 2: Install Python (if missing)
:: ──────────────────────────────────────────────────────────────
echo.
echo  [1/7] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Python not found. Installing Python 3.12...
    echo  Downloading...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    echo  Installing (silent)...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    timeout /t 5 /nobreak >nul
    :: Refresh PATH
    set "PATH=%PATH%;C:\Program Files\Python312;C:\Program Files\Python312\Scripts"
    echo  [OK] Python installed
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK] %%v found
)

:: ──────────────────────────────────────────────────────────────
::  Step 3: Install Git (if missing)
:: ──────────────────────────────────────────────────────────────
echo.
echo  [2/7] Checking Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Git not found. Installing...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.46.0.windows.1/Git-2.46.0-64-bit.exe' -OutFile '%TEMP%\git_installer.exe'"
    "%TEMP%\git_installer.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"
    timeout /t 5 /nobreak >nul
    set "PATH=%PATH%;C:\Program Files\Git\bin"
    echo  [OK] Git installed
) else (
    for /f "tokens=*" %%v in ('git --version 2^>^&1') do echo  [OK] %%v found
)

:: ──────────────────────────────────────────────────────────────
::  Step 4: Install Node.js + Claude Code CLI
:: ──────────────────────────────────────────────────────────────
echo.
echo  [3/7] Checking Node.js + Claude Code...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Node.js not found. Installing Node.js 22 LTS...
    powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v22.12.0/node-v22.12.0-x64.msi' -OutFile '%TEMP%\node_installer.msi'"
    msiexec /i "%TEMP%\node_installer.msi" /quiet /norestart
    timeout /t 10 /nobreak >nul
    set "PATH=%PATH%;C:\Program Files\nodejs"
    echo  [OK] Node.js installed
) else (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo  [OK] Node.js %%v found
)

echo  Installing Claude Code CLI...
call npm install -g @anthropic-ai/claude-code >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Claude Code CLI installed
) else (
    echo  [WARN] Claude Code install failed — install manually later: npm install -g @anthropic-ai/claude-code
)

:: ──────────────────────────────────────────────────────────────
::  Step 5: Clone TradeWizard repo
:: ──────────────────────────────────────────────────────────────
echo.
echo  [4/7] Setting up TradeWizard...
set "TW_DIR=C:\TradeWizard"

if exist "%TW_DIR%\.git" (
    echo  TradeWizard repo already exists at %TW_DIR%
    cd /d "%TW_DIR%"
    git pull origin claude/multi-agent-forex-trading-j6mE9
) else (
    echo  Cloning TradeWizard...
    git clone -b claude/multi-agent-forex-trading-j6mE9 https://github.com/killBullox/TradeWizard.git "%TW_DIR%"
    cd /d "%TW_DIR%"
)

echo  Installing Python dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r backend\requirements.txt
echo  [OK] TradeWizard ready

:: ──────────────────────────────────────────────────────────────
::  Step 6: Configure .env
:: ──────────────────────────────────────────────────────────────
echo.
echo  [5/7] Configuring environment...
if not exist "%TW_DIR%\.env" (
    echo  Creating .env file...
    echo  You will need to fill in your API keys.
    (
        echo ANTHROPIC_API_KEY=your_anthropic_key_here
        echo.
        echo # WhatsApp via Twilio
        echo TWILIO_ACCOUNT_SID=your_twilio_sid
        echo TWILIO_AUTH_TOKEN=your_twilio_token
        echo TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
        echo WHATSAPP_TO=whatsapp:+your_number
        echo.
        echo # MT5 (configured via dashboard Settings page^)
    ) > "%TW_DIR%\.env"
    echo  [IMPORTANT] Edit %TW_DIR%\.env with your API keys!
    echo  Open it with: notepad "%TW_DIR%\.env"
) else (
    echo  [OK] .env already exists
)

:: ──────────────────────────────────────────────────────────────
::  Step 7: Install MetaTrader 5 (if missing)
:: ──────────────────────────────────────────────────────────────
echo.
echo  [6/7] Checking MetaTrader 5...
set "MT5_FOUND=0"
if exist "C:\Program Files\MetaTrader 5\terminal64.exe" set "MT5_FOUND=1"
if exist "C:\Program Files (x86)\MetaTrader 5\terminal64.exe" set "MT5_FOUND=1"

if "%MT5_FOUND%"=="0" (
    echo  MT5 not found. Downloading installer...
    echo  NOTE: You should install MT5 from your broker's website for the correct server.
    echo  Generic MT5 installer will be downloaded — you may need to add your broker's server manually.
    powershell -Command "Invoke-WebRequest -Uri 'https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe' -OutFile '%TEMP%\mt5setup.exe'"
    echo  Launching MT5 installer (follow the prompts)...
    start "" "%TEMP%\mt5setup.exe"
    echo  [ACTION REQUIRED] Complete the MT5 installation, then press any key to continue.
    pause >nul
) else (
    echo  [OK] MetaTrader 5 found
)

:: ──────────────────────────────────────────────────────────────
::  Step 8: Install Cloudflare Tunnel (optional)
:: ──────────────────────────────────────────────────────────────
echo.
echo  [7/7] Cloudflare Tunnel (remote dashboard access)...
cloudflared --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing cloudflared...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi' -OutFile '%TEMP%\cloudflared.msi'"
    msiexec /i "%TEMP%\cloudflared.msi" /quiet /norestart
    timeout /t 5 /nobreak >nul
    echo  [OK] cloudflared installed
    echo.
    echo  To setup the tunnel, run:
    echo    cloudflared tunnel login
    echo    cloudflared tunnel create tradewizard
    echo    cloudflared tunnel route dns tradewizard tradewizard.yourdomain.com
    echo.
    echo  Then create C:\TradeWizard\cloudflared.yml:
    echo    tunnel: ^<tunnel-id^>
    echo    credentials-file: %USERPROFILE%\.cloudflared\^<tunnel-id^>.json
    echo    ingress:
    echo      - hostname: tradewizard.yourdomain.com
    echo        service: http://localhost:8000
    echo      - service: http_status:404
    echo.
    echo  Start tunnel: cloudflared tunnel run tradewizard
) else (
    echo  [OK] cloudflared already installed
)

:: ──────────────────────────────────────────────────────────────
::  Step 9: Install Scheduled Tasks
:: ──────────────────────────────────────────────────────────────
echo.
echo  Installing scheduled tasks...

REM TradeWizard autostart
schtasks /delete /tn "TradeWizard" /f >nul 2>&1
schtasks /create /tn "TradeWizard" /tr "\"%TW_DIR%\update.bat\"" /sc onlogon /delay 0000:30 /rl highest /f
echo  [OK] TradeWizard autostart task installed

REM Watchdog autostart (15s after login)
for /f "tokens=*" %%i in ('where python 2^>nul') do set "PY=%%i"
schtasks /delete /tn "TradeWizard-Watchdog" /f >nul 2>&1
schtasks /create /tn "TradeWizard-Watchdog" /tr "\"%PY%\" \"%TW_DIR%\backend\services\watchdog.py\"" /sc onlogon /delay 0000:15 /rl highest /f
echo  [OK] Watchdog autostart task installed

:: ──────────────────────────────────────────────────────────────
::  Done!
:: ──────────────────────────────────────────────────────────────
echo.
echo  ============================================================
echo   SETUP COMPLETE!
echo  ============================================================
echo.
echo  Next steps:
echo    1. Edit .env with your API keys:
echo       notepad "%TW_DIR%\.env"
echo.
echo    2. Open MT5 and login to your broker account
echo.
echo    3. Start TradeWizard:
echo       "%TW_DIR%\start.bat"
echo.
echo    4. Open dashboard: http://localhost:8000
echo.
echo    5. (Optional) Setup Cloudflare Tunnel for remote access
echo.
echo    6. Configure Git credentials:
echo       git config --global user.name "Your Name"
echo       git config --global user.email "your@email.com"
echo.
echo  The system will auto-start on login (TradeWizard + Watchdog).
echo.
pause
endlocal
