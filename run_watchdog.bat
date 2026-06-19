@echo off
cd /d C:\TradeWizard
python backend\services\watchdog.py >> logs\watchdog_stdout.log 2>&1
