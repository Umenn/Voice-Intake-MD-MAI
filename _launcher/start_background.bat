@echo off
title Voice Intake v0.0.4 - Server
set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo.
echo  ============================================================
echo   Voice Intake v0.0.4
echo  ============================================================
echo.

:: ---- Verifica Python -------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo  [EROARE] Python nu este instalat. Rulati FIRSTstart.bat.
    pause & exit /b 1
)

:: ---- Verifica .env ---------------------------------------------------------
if not exist "%ROOT%\.env" (
    echo  [EROARE] Fisierul .env lipseste. Rulati FIRSTstart.bat.
    pause & exit /b 1
)

:: ---- Dependente ------------------------------------------------------------
echo  Verificare pachete...
python -c "import pystray, PIL, pdfplumber, mutagen, pytesseract" >nul 2>&1
if errorlevel 1 (
    echo  Instalare dependente v0.0.4...
    python -m pip install -r "%ROOT%\requirements.txt" --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo  [EROARE] Instalare pachete esuata. Verificati conexiunea la internet.
        pause & exit /b 1
    )
)

:: ---- Sabloane --------------------------------------------------------------
if not exist "%ROOT%\templates\pv_retinere.docx" (
    echo  Generare sabloane noi v0.0.4...
    python "%ROOT%\_app\template_builder.py"
)

:: ---- Pornire tray.py in fundal (via Python launcher) ----------------------
echo  Pornire server in fundal...
python "%ROOT%\launch_tray.py"
if errorlevel 1 (
    echo.
    echo  [EROARE] launch_tray.py a esuat. Rulati DEBUG_start.bat pentru detalii.
    pause & exit /b 1
)

timeout /t 6 /nobreak >nul

:: ---- Verifica daca serverul raspunde --------------------------------------
python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [EROARE] Serverul nu raspunde dupa 6 secunde.
    echo  Rulati DEBUG_start.bat pentru a vedea eroarea exacta.
    echo.
    pause & exit /b 1
)

echo.
echo  ============================================================
echo   Server ACTIV in fundal - v0.0.4
echo.
echo   Pictograma verde in bara de sistem (dreapta-jos).
echo   Hover = IP + cod   /   Dublu-click = popup   /   Click-dreapta = meniu
echo.
echo   Loguri: logs\tray\ sau loguri\tray\
echo   Aceasta fereastra o puteti inchide.
echo  ============================================================
echo.
pause
