@echo off
setlocal

cd /d "%~dp0"

echo.
echo  ==========================================
echo   TradeWizard Watchdog - Install / Manage
echo  ==========================================
echo.
echo  1) Start watchdog (this window)
echo  2) Start watchdog (background, new window)
echo  3) Install as Windows Scheduled Task (auto-start on login)
echo  4) Remove Scheduled Task
echo.
set /p CHOICE="  Choose [1-4]: "

if "%CHOICE%"=="1" goto :start_foreground
if "%CHOICE%"=="2" goto :start_background
if "%CHOICE%"=="3" goto :install_task
if "%CHOICE%"=="4" goto :remove_task
echo  Invalid choice.
goto :end

:start_foreground
echo.
echo  Starting watchdog in foreground (Ctrl+C to stop)...
python backend\services\watchdog.py
goto :end

:start_background
echo.
echo  Starting watchdog in background window...
start "TradeWizard Watchdog" /D "%~dp0" cmd /k python backend\services\watchdog.py
echo  Watchdog started. Check the new window.
goto :end

:install_task
echo.
echo  Installing watchdog as Scheduled Task...

REM Get full paths
set "PYTHON_PATH="
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    if not defined PYTHON_PATH set "PYTHON_PATH=%%i"
)
if not defined PYTHON_PATH (
    echo  [ERROR] Python not found in PATH!
    goto :end
)

set "WATCHDOG_SCRIPT=%~dp0backend\services\watchdog.py"

REM Remove existing task
schtasks /delete /tn "TradeWizard-Watchdog" /f >nul 2>&1

REM Create task that runs on login with 15 second delay
schtasks /create /tn "TradeWizard-Watchdog" ^
    /tr "\"%PYTHON_PATH%\" \"%WATCHDOG_SCRIPT%\"" ^
    /sc onlogon ^
    /delay 0000:15 ^
    /rl highest ^
    /f

if %errorlevel% equ 0 (
    echo.
    echo  [OK] Watchdog task installed successfully!
    echo       Task name: TradeWizard-Watchdog
    echo       Trigger: On user login (15s delay)
    echo       Script: %WATCHDOG_SCRIPT%
    echo.
    echo  The watchdog will start automatically when you log in.
    echo  To start it now, choose option 1 or 2.
) else (
    echo  [ERROR] Failed to create scheduled task.
    echo  Try running this script as Administrator.
)
goto :end

:remove_task
echo.
schtasks /delete /tn "TradeWizard-Watchdog" /f
echo  Watchdog task removed.
goto :end

:end
echo.
pause
endlocal
