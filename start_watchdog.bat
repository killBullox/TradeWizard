@echo off
rem Resilient watchdog launcher: respawns watchdog.py whenever it exits.
rem Started by the TradeWizardWatchdog scheduled task at boot, runs as SYSTEM.

:loop
cd /d C:\TradeWizard
python backend\services\watchdog.py >> logs\watchdog_stdout.log 2>&1
echo [%date% %time%] watchdog exited with %errorlevel% — respawning in 10s >> logs\watchdog_stdout.log
timeout /t 10 /nobreak >nul
goto loop
