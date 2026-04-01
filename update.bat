@echo off
title TradeWizard - Aggiornamento
echo.
echo  ==========================================
echo   TradeWizard - Aggiornamento e Avvio
echo  ==========================================
echo.

cd /d "%~dp0"

REM -- Verifica Python --
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRORE] Python non trovato nel PATH!
    pause
    exit /b 1
)

REM -- Carica variabili .env --
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%A:~0,1%"=="#" set "%%A=%%B"
    )
)

REM -- Fermo il backend precedente --
echo  [1/3] Fermo il backend precedente...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM -- Git pull --
echo  [2/3] Scarico aggiornamenti...
git pull origin claude/multi-agent-forex-trading-j6mE9
if %errorlevel% neq 0 (
    echo  ATTENZIONE: git pull fallito - avvio con versione locale
)

REM -- Installa dipendenze se mancanti --
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installo dipendenze...
    pip install -r backend\requirements.txt
)

REM -- Avvia backend in nuova finestra --
echo  [3/3] Avvio backend...
start "TradeWizard Backend" cmd /k "cd /d "%~dp0" && python backend\main.py"

echo.
echo  Apri http://localhost:8000
echo  (questa finestra si chiude tra 3 secondi)
timeout /t 3 /nobreak >nul
