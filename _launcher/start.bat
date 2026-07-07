@echo off
title Voice Intake v0.0.1 - Politia RM
set "ROOT=%~dp0.."
cd /d "%ROOT%"
color 0A

echo.
echo  ==========================================
echo   Voice Intake v0.0.1 - Politia RM
echo  ==========================================
echo.

:: ---- Python -----------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo  [EROARE] Python nu este instalat.
    echo  Rulati FIRSTstart.bat pentru instalare automata.
    echo.
    pause
    exit /b 1
)

:: ---- .env -------------------------------------------------------------
if not exist "%ROOT%\.env" (
    echo  [EROARE] Fisierul .env lipseste.
    echo  Rulati FIRSTstart.bat pentru configurare initiala.
    echo.
    if exist "%ROOT%\.env.example" (
        copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
        echo  Am creat .env din exemplu - deschideti-l si completati OPENAI_API_KEY.
        notepad "%ROOT%\.env"
        pause
    ) else (
        pause
        exit /b 1
    )
)

:: ---- Sabloane (daca lipsesc) ------------------------------------------
if not exist "%ROOT%\templates\raport_go.docx" (
    echo  Generare sabloane documente...
    python "%ROOT%\_app\template_builder.py" 2>nul
)

:: ---- Pornire server ---------------------------------------------------
echo  Pornire server...
echo.
echo  Deschideti browser la:  http://localhost:8000
echo  Apasati CTRL+C pentru a opri serverul.
echo.
python "%ROOT%\_app\main.py"

:: ===  FEREASTRA RAMANE DESCHISA  =======================================
echo.
echo  ============================================================
echo   Serverul s-a oprit. Cititi eroarea de mai sus.
echo  ============================================================
echo.
echo   Cauze frecvente:
echo     - Portul 8000 ocupat: inchideti alt server sau reporniti PC
echo     - .env gresit: deschideti .env si verificati OPENAI_API_KEY
echo     - Pachete lipsa: rulati FIRSTstart.bat din nou
echo.
pause
