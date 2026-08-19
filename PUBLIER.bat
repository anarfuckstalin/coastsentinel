@echo off
REM Lance PUBLIER.ps1 sans toucher a la politique d'execution du systeme :
REM -ExecutionPolicy Bypass ne vaut que pour ce processus.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0PUBLIER.ps1"
if errorlevel 1 pause
