@echo off
setlocal

cd /d "%~dp0"

echo.
echo  ==========================================
echo   TradeWizard - Aggiornamento e Avvio
echo  ==========================================
echo.

REM -- Verifica Python --
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRORE] Python non trovato nel PATH!
    pause
    exit /b 1
)

REM -- Fermo il backend precedente --
echo  [1/3] Fermo backend precedente...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM -- Git pull --
echo  [2/3] Scarico aggiornamenti...
git pull origin claude/multi-agent-forex-trading-j6mE9

REM -- Avvia backend in nuova finestra --
echo  [3/3] Avvio backend...
start "TradeWizard Backend" /D "%~dp0" cmd /k python backend\main.py

echo.
echo  Apri http://localhost:8000
timeout /t 3 /nobreak >nul

endlocal
