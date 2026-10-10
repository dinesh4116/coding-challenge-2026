@echo off
echo DEVELOPER MODE ONLY: hot-reload web app on port 3000 (needs the backend running on port 8000).
echo For normal use, run run_backend.bat and open http://localhost:8000
cd /d %~dp0frontend
if not exist node_modules call npm.cmd install
call npm.cmd run dev
pause
