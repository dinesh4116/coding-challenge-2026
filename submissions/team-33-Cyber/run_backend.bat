@echo off
echo Starting SearchPilot AI at http://localhost:8000 ...
cd /d %~dp0backend
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
    call .\venv\Scripts\pip install -r requirements.txt
)
if not exist ..\frontend\dist\index.html (
    echo Web app not built yet. Building...
    cd /d %~dp0frontend
    if not exist node_modules call npm.cmd install
    call npm.cmd run build
    cd /d %~dp0backend
)
start http://localhost:8000
call .\venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
