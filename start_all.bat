@echo off
title OMR Exam Suite - All-In-One Launcher
echo ========================================================
echo         OMR Exam Suite & Scanner Integration
echo ========================================================
echo.
echo 1. Starting Backend Web Application on http://localhost:8000 ...
start "OMR Backend Server" /min cmd /c "cd /d "%~dp0backend" && .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo 2. Starting Local Scanner Bridge on http://127.0.0.1:8765 ...
start "OMR Scanner Bridge" /min cmd /c "cd /d "%~dp0scanner_bridge" && ..\backend\.venv\Scripts\python.exe bridge.py"

echo.
echo Waiting for services to initialize...
timeout /t 3 /nobreak >nul

echo 3. Opening web browser at http://localhost:8000 ...
start http://localhost:8000

echo.
echo ========================================================
echo System is running!
echo - Web App:        http://localhost:8000
echo - Scanner Bridge: http://127.0.0.1:8765
echo.
echo You can keep this window open or close it when done.
echo ========================================================
pause
