@echo off
title TradeWizard Backend
color 0A
echo.
echo  ==========================================
echo   TradeWizard Backend
echo  ==========================================
echo.

cd /d "%~dp0"

REM -- Verifica Python --
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRORE] Python non trovato nel PATH!
    echo  Assicurati che Python sia installato e aggiunto al PATH di sistema.
    echo  Oppure apri questo bat dalla cartella di Anaconda/Python.
    pause
    exit /b 1
)

REM -- Carica variabili .env se esiste --
if exist ".env" (
    echo  Carico .env...
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%A:~0,1%"=="#" set "%%A=%%B"
    )
)

REM -- Verifica ANTHROPIC_API_KEY --
if "%ANTHROPIC_API_KEY%"=="" (
    echo  [ATTENZIONE] ANTHROPIC_API_KEY non impostata nel file .env
    echo  Il sistema partira ma le analisi AI non funzioneranno.
    echo.
)

REM -- Installa dipendenze se mancanti --
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installo dipendenze...
    pip install -r backend\requirements.txt
    if %errorlevel% neq 0 (
        echo  [ERRORE] Installazione dipendenze fallita!
        pause
        exit /b 1
    )
)

echo  Avvio backend su http://localhost:8000
echo  (Premi Ctrl+C per fermare)
echo.

python backend\main.py

REM -- Se arriva qui c'e' stato un errore --
echo.
echo  [!] Il backend si e' fermato. Vedi errore sopra.
pause
