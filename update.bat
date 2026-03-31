@echo off
title TradeWizard - Aggiornamento
echo.
echo  Aggiornamento TradeWizard...
echo  ================================

cd /d "%~dp0"

REM -- Carica variabili .env --
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A:~0,1%"=="#" if not "%%A"=="" set "%%A=%%B"
    )
)

echo  [1/3] Fermo il backend...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo  [2/3] Scarico aggiornamenti...
git pull origin claude/multi-agent-forex-trading-j6mE9
if %errorlevel% neq 0 (
    echo  ERRORE nel git pull - avvio con versione locale...
)

echo  [3/3] Avvio il backend...
start "TradeWizard Backend" cmd /k "python backend\main.py & echo. & echo [!] Backend fermato - vedi errore sopra & pause"

echo.
echo  Fatto! Apri http://localhost:8000
echo  (questa finestra si chiude tra 5 secondi)
timeout /t 5 /nobreak >nul
