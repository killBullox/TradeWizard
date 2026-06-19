@echo off
REM Restart ONLY TradeWizard processes (not TradeMachine or other Python apps)
echo Stopping TradeWizard...
wmic process where "commandline like '%%TradeWizard%%' and commandline like '%%main.py%%'" delete >nul 2>&1
wmic process where "commandline like '%%TradeWizard%%' and commandline like '%%watchdog.py%%'" delete >nul 2>&1
timeout /t 3 /nobreak >nul
echo Starting TradeWizard...
schtasks /run /tn "TradeWizard"
echo Done.
