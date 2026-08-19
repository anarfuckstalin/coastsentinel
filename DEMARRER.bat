@echo off
REM ====================================================================
REM  CoastSentinel - demarrage local (Windows)
REM  Lance l'API FastAPI et le serveur de developpement Vite.
REM ====================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title CoastSentinel

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
  echo Python est introuvable. Installez-le depuis python.org
  echo en cochant "Add python.exe to PATH", puis relancez.
  pause & exit /b 1
)
where node >nul 2>nul || (
  echo Node.js est introuvable. Installez-le depuis https://nodejs.org
  pause & exit /b 1
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/3] Creation de l'environnement Python...
  %PY% -m venv backend\.venv
  backend\.venv\Scripts\python.exe -m pip install --upgrade pip -q
  backend\.venv\Scripts\python.exe -m pip install -q -e "backend[science]"
) else (
  echo [1/3] Environnement Python deja pret.
)

if not exist "frontend\node_modules" (
  echo [2/3] Installation des dependances du frontend ^(quelques minutes^)...
  pushd frontend && npm install --no-audit --no-fund && popd
) else (
  echo [2/3] Dependances frontend deja installees.
)

echo [3/3] Demarrage...
start "CoastSentinel API" cmd /k backend\.venv\Scripts\python.exe -m uvicorn coastsentinel.api:app --app-dir backend --reload --port 8000
timeout /t 4 >nul
start "CoastSentinel Web" cmd /k "cd frontend && npm run dev"
timeout /t 6 >nul
start "" http://localhost:5173

echo.
echo  Application  : http://localhost:5173
echo  API + docs   : http://localhost:8000/api/docs
echo.
echo  Fermez les deux fenetres ouvertes pour arreter les serveurs.
pause
