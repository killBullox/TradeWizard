@echo off
title TradeWizard - Aggiornamento
echo.
echo  Aggiornamento TradeWizard...
echo  ================================

cd /d "%~dp0"

echo  [1/3] Fermo il backend...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo  [2/3] Scarico aggiornamenti...
git pull origin claude/multi-agent-forex-trading-j6mE9
if %errorlevel% neq 0 (
    echo  ERRORE nel git pull!
    pause
    exit /b 1
)

echo  [3/3] Avvio il backend...
start "TradeWizard Backend" python backend/main.py

echo.
echo  Fatto! Apri http://localhost:8000
echo  (questa finestra si chiude da sola tra 5 secondi)
timeout /t 5 /nobreak >nul
