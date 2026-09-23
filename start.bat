@echo off
rem Start API (port 8000) and Web (port 3000), then open the browser
set "ROOT=%~dp0"
if not exist "%ROOT%api\.venv\Scripts\python.exe" (
  echo [ERROR] Please run setup.bat first.
  pause
  exit /b 1
)
if not exist "%ROOT%web\node_modules" (
  echo [ERROR] Please run setup.bat first.
  pause
  exit /b 1
)
start "POS API :8000" /D "%ROOT%api" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
start "POS Web :3000" /D "%ROOT%web" cmd /k "npm.cmd run dev"
echo Starting... the browser will open in a few seconds.
timeout /t 10 /nobreak >nul
start "" http://localhost:3000/login
