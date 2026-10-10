@echo off
echo ========================================================
echo   SearchPilot AI - Setup and Launch (single address)
echo ========================================================
echo.
echo [1/3] Setting up Python backend...
cd /d %~dp0backend
if not exist venv (
    python -m venv venv
)
call .\venv\Scripts\pip install -r requirements.txt

echo.
echo [2/3] Building the web app...
cd /d %~dp0frontend
if not exist node_modules (
    call npm.cmd install
)
call npm.cmd run build
if errorlevel 1 (
    echo Build failed. Please check the messages above.
    pause
    exit /b 1
)

echo.
echo [3/3] Starting SearchPilot AI...
cd /d %~dp0backend
start "SearchPilot AI" cmd /k "call .\venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000"
timeout /t 4 >nul
start http://localhost:8000
echo.
echo SearchPilot AI is running at: http://localhost:8000
echo Close the "SearchPilot AI" window to stop it.
