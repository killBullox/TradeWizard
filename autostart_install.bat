@echo off
title TradeWizard - Installa Avvio Automatico
echo.
echo  Installazione avvio automatico TradeWizard...
echo.

REM -- Percorso assoluto di start.bat --
set "START_BAT=%~dp0start.bat"

REM -- Crea task nel Task Scheduler (parte 30s dopo il login) --
schtasks /delete /tn "TradeWizard" /f >nul 2>&1
schtasks /create /tn "TradeWizard" /tr "\"%START_BAT%\"" /sc onlogon /delay 0000:30 /rl highest /f

if %errorlevel% equ 0 (
    echo  [OK] TradeWizard si avviera automaticamente al login.
    echo       Percorso: %START_BAT%
    echo.
    echo  Per disinstallare: esegui autostart_remove.bat
) else (
    echo  [ERRORE] Task Scheduler fallito. Provo con cartella Startup...
    powershell -NoProfile -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Startup')+'\TradeWizard.lnk');$s.TargetPath='%START_BAT%';$s.WorkingDirectory='%~dp0';$s.WindowStyle=1;$s.Save()"
    if %errorlevel% equ 0 (
        echo  [OK] Shortcut creato nella cartella Startup.
    ) else (
        echo  [ERRORE] Installazione fallita. Esegui come Amministratore.
    )
)
echo.
pause
