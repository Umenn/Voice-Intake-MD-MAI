@echo off
title Voice Intake - Oprire server
echo.
echo  Oprire Voice Intake server...
echo.

:: Kill tray process
taskkill /F /IM pythonw.exe /T >nul 2>&1

:: Kill any uvicorn / python main.py processes on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Kill cloudflared if running
taskkill /F /IM cloudflared.exe /T >nul 2>&1

echo  Serverul a fost oprit.
echo.
timeout /t 2 /nobreak >nul
