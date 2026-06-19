@echo off
title TradeWizard - Rimuovi Avvio Automatico
echo.
schtasks /delete /tn "TradeWizard" /f >nul 2>&1
powershell -NoProfile -Command "Remove-Item ([Environment]::GetFolderPath('Startup')+'\TradeWizard.lnk') -ErrorAction SilentlyContinue"
echo  [OK] TradeWizard rimosso dall'avvio automatico.
echo.
pause
