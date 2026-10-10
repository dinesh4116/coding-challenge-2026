@echo off
TITLE PS-04 Campaign Anomaly Alerting System - Launcher
COLOR 0A

echo ==============================================================================
echo   PS-04 : Campaign Anomaly Alerting Without Alert Fatigue
echo   FastAPI Backend + Vite/React Intelligence Dashboard
echo ==============================================================================
echo.

echo [1/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "PS-04 FastAPI Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [2/3] Starting Vite React Frontend on http://localhost:5173 ...
start "PS-04 React Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 3 /nobreak >nul

echo [3/3] Launching web browser...
start http://localhost:5173

echo.
echo ==============================================================================
echo   System is LIVE!
echo   - Web Dashboard:     http://localhost:5173
echo   - Backend API Docs:  http://127.0.0.1:8000/docs
echo   - API Health Check:  http://127.0.0.1:8000/api/health
echo.
echo   Press any key to close this launcher window (services keep running in background)...
echo ==============================================================================
pause >nul
