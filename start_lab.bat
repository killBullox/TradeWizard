@echo off
cd /d C:\TradeWizard
set SYSTEM_MODE=lab
set PORT=8001
python backend\main.py > logs\lab_stderr.log 2>&1
