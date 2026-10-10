# ==============================================================================
# PS-04 : Campaign Anomaly Alerting Without Alert Fatigue
# Unified PowerShell Launcher Script
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  PS-04 : Campaign Anomaly Alerting Without Alert Fatigue" -ForegroundColor Green
Write-Host "  FastAPI Backend + Vite/React Intelligence Dashboard" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

$root = $PSScriptRoot

Write-Host "[1/3] Launching FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 2

Write-Host "[2/3] Launching React/Vite Frontend on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Start-Sleep -Seconds 3

Write-Host "[3/3] Opening browser..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  System is LIVE!" -ForegroundColor Green
Write-Host "  - Frontend Dashboard: http://localhost:5173" -ForegroundColor White
Write-Host "  - Backend API Docs:   http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  - API Health Check:   http://127.0.0.1:8000/api/health" -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Cyan
