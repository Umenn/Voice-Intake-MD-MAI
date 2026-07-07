@echo off
title Voice Intake - Configurare tunel Cloudflare permanent
set "ROOT=%~dp0.."

echo.
echo  Verificare Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [EROARE] Python nu este instalat.
    echo  Rulati FIRSTstart.bat mai intai.
    echo.
    pause
    exit /b 1
)

echo  Pornire wizard configurare tunel...
echo.
python "%ROOT%\_tools\setup_tunnel.py"
