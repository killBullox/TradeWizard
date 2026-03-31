@echo off
title TradeWizard - Installa Avvio Automatico
echo.
echo  Installazione avvio automatico TradeWizard...
echo.

set "UPDATE_BAT=%~dp0update.bat"

schtasks /delete /tn "TradeWizard" /f >nul 2>&1
schtasks /create /tn "TradeWizard" /tr "\"%UPDATE_BAT%\"" /sc onlogon /delay 0000:30 /rl highest /f

if %errorlevel% equ 0 (
    echo  [OK] TradeWizard (update.bat) si avviera automaticamente al login.
    echo       Percorso: %UPDATE_BAT%
    echo.
    echo  Per disinstallare: esegui autostart_remove.bat
) else (
    echo  [ERRORE] Esegui come Amministratore e riprova.
)
echo.
pause
