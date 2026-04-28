@echo off
rem TradeWizard BR (Backtest-to-Reality) launcher
rem Runs the deterministic ICT strategy on live MT5 paper, port 8002.
rem Started by the TradeWizardBR scheduled task at boot.

set SYSTEM_MODE=br
set PORT=8002
cd /d C:\TradeWizard
python backend\main.py >> logs\br_stdout.log 2>&1
