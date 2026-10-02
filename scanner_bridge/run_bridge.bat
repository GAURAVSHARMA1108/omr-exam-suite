@echo off
title OMR Local Scanner Bridge (Port 8765)
echo ===================================================
echo     OMR Web Exam Suite - Local Scanner Bridge
echo ===================================================
echo Listening on http://127.0.0.1:8765
echo Connecting to Windows WIA Drivers (Flatbed & Feeder)...
echo.

cd /d "%~dp0"
..\backend\.venv\Scripts\python.exe bridge.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bridge exited with code %ERRORLEVEL%.
    pause
)
