@echo off
title TradeWizard - Aggiornamento e Avvio
color 0A
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
    echo  Assicurati che Python sia installato e aggiunto al PATH di sistema.
    pause
    exit /b 1
)

REM -- Carica variabili .env --
if exist ".env" (
    echo  Carico .env...
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%A:~0,1%"=="#" set "%%A=%%B"
    )
)

REM -- Verifica ANTHROPIC_API_KEY --
if "%ANTHROPIC_API_KEY%"=="" (
    echo  [ATTENZIONE] ANTHROPIC_API_KEY non impostata nel .env
    echo  Il sistema avviera ma le analisi AI non funzioneranno.
    echo.
)

REM -- Fermo il backend precedente --
echo  [1/4] Fermo il backend precedente...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM -- Git pull (salva modifiche locali, scarica, ripristina) --
echo  [2/4] Scarico aggiornamenti...
git stash >nul 2>&1
git pull origin claude/multi-agent-forex-trading-j6mE9
if %errorlevel% neq 0 (
    echo  [ATTENZIONE] git pull fallito - avvio con versione locale
) else (
    echo  Aggiornamento completato.
)
git stash pop >nul 2>&1

REM -- Installa/aggiorna dipendenze --
echo  [3/4] Aggiorno dipendenze Python...
pip install -r backend\requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  [ERRORE] Installazione dipendenze fallita!
    pause
    exit /b 1
)

REM -- Avvio backend --
echo  [4/4] Avvio backend su http://localhost:8000
echo  (Premi Ctrl+C per fermare)
echo.

python backend\main.py

REM -- Se arriva qui c'e' stato un errore --
echo.
echo  [!] Il backend si e' fermato. Vedi errore sopra.
pause
