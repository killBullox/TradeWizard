@echo off
cd /d C:\TradeWizard
python backend\scripts\audit.py >> logs\audit.log 2>&1
