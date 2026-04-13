@echo off
REM Restart ONLY TradeWizard processes (not other Python apps)
echo Stopping TradeWizard...
wmic process where "commandline like '%%backend\\main.py%%'" delete >nul 2>&1
wmic process where "commandline like '%%mt5_bridge.py%%'" delete >nul 2>&1
wmic process where "commandline like '%%watchdog.py%%'" delete >nul 2>&1
timeout /t 3 /nobreak >nul
echo Starting TradeWizard...
schtasks /run /tn "TradeWizard"
echo Done.
