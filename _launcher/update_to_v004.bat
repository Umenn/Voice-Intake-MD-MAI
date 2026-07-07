@echo off
title Voice Intake - Actualizare la v0.0.4
set "ROOT=%~dp0.."
cd /d "%ROOT%"
color 0E

echo.
echo  ============================================================
echo   Voice Intake - Actualizare la v0.0.4
echo  ============================================================
echo.
echo  Apasati orice tasta pentru a incepe...
pause >nul

:: ---- PASUL 1: Oprire server existent ----------------------------------------
echo.
echo  [1/4] Oprire server existent (daca ruleaza)...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo       OK.

:: ---- PASUL 2: Directoare noi ------------------------------------------------
echo.
echo  [2/4] Verificare directoare noi...
if not exist "%ROOT%\logs"           mkdir "%ROOT%\logs"
if not exist "%ROOT%\logs\app"       mkdir "%ROOT%\logs\app"
if not exist "%ROOT%\logs\tray"      mkdir "%ROOT%\logs\tray"
if not exist "%ROOT%\logs\ngrok"     mkdir "%ROOT%\logs\ngrok"
if not exist "%ROOT%\logs\errors"    mkdir "%ROOT%\logs\errors"
if not exist "%ROOT%\recordings"     mkdir "%ROOT%\recordings"
echo       OK.

:: ---- PASUL 3: Pachete Python ------------------------------------------------
echo.
echo  [3/4] Verificare pachete Python...
python -c "import pystray, PIL, pdfplumber, mutagen, pytesseract" >nul 2>&1
if errorlevel 1 (
    echo       Instalare pachete lipsa...
    python -m pip install -r "%ROOT%\requirements.txt" --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo.
        echo  [EROARE] Instalare pachete esuata. Verificati conexiunea la internet.
        pause & exit /b 1
    )
) else (
    echo       Toate pachetele sunt prezente.
)

:: ---- PASUL 4: Sabloane v0.0.4 -----------------------------------------------
echo.
echo  [4/4] Verificare sabloane docx v0.0.4...
set "MISSING=0"
if not exist "%ROOT%\templates\decizie_clasare.docx"   set MISSING=1
if not exist "%ROOT%\templates\declaratie.docx"        set MISSING=1
if not exist "%ROOT%\templates\incheiere.docx"         set MISSING=1
if not exist "%ROOT%\templates\interpelare.docx"       set MISSING=1
if not exist "%ROOT%\templates\nota_explicativa.docx"  set MISSING=1
if not exist "%ROOT%\templates\nota_informativa.docx"  set MISSING=1
if not exist "%ROOT%\templates\plangere.docx"          set MISSING=1
if not exist "%ROOT%\templates\prelungire.docx"        set MISSING=1
if not exist "%ROOT%\templates\proces_verbal.docx"     set MISSING=1
if not exist "%ROOT%\templates\raport_cautare.docx"    set MISSING=1
if not exist "%ROOT%\templates\raport_droguri.docx"    set MISSING=1
if not exist "%ROOT%\templates\raport_go.docx"         set MISSING=1
if not exist "%ROOT%\templates\raport_pierdere.docx"   set MISSING=1
if not exist "%ROOT%\templates\raport_transmitere.docx" set MISSING=1
if not exist "%ROOT%\templates\sesizare_penala.docx"   set MISSING=1
if not exist "%ROOT%\templates\raport_serviciu.docx"   set MISSING=1

if "%MISSING%"=="1" (
    echo       Generare sabloane lipsa...
    python "%ROOT%\_app\template_builder.py"
    if errorlevel 1 (
        echo  [AVERTIZARE] template_builder a dat eroare. Verificati manual.
    ) else (
        echo       Sabloane generate OK.
    )
) else (
    echo       Toate cele 15 sabloane sunt prezente.
)

:: ---- REPORNIRE SERVER -------------------------------------------------------
echo.
echo  Repornire server in fundal...
python "%ROOT%\launch_tray.py"
if errorlevel 1 (
    echo.
    echo  [EROARE] launch_tray.py a esuat. Rulati DEBUG_start.bat pentru detalii.
    pause & exit /b 1
)

timeout /t 6 /nobreak >nul

python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)" >nul 2>&1
if errorlevel 1 (
    echo  [AVERTIZARE] Serverul nu raspunde dupa 6 secunde.
    echo  Rulati DEBUG_start.bat pentru eroarea exacta.
) else (
    echo  Server activ. Deschideti browser la: http://localhost:8000
)

echo.
echo  ============================================================
echo   ACTUALIZARE COMPLETA la v0.0.4!
echo.
echo   Nou in v0.0.4:
echo    + Autentificare per-ofiter (coduri personale SANDU01 etc.)
echo    + Pagina Arhiva conectata la contul fiecarui ofiter
echo    + Interfata redesignata dark/light (index + history + login)
echo    + Mod Inregistrare Rapida: inregistrezi mai intai, alegi
echo      documentele dupa transcriere, genereaza mai multe dintr-un
echo      singur transcript, adauga documente suplimentare oricand
echo    + Override ofiter responsabil per-sesiune pe orice document
echo  ============================================================
echo.
pause
