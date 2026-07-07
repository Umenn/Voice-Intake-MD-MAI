@echo off
title Voice Intake v0.0.4 - DEBUG MODE
set "ROOT=%~dp0.."
cd /d "%ROOT%"
color 0C
set "DEBUGLOG=%ROOT%\DEBUG_output.txt"
echo DEBUG run %date% %time% > "%DEBUGLOG%"

echo.
echo  ============================================================
echo   Voice Intake v0.0.4 - DEBUG MODE
echo   Output salvat si in: DEBUG_output.txt
echo  ============================================================
echo.

:: ---- [1] Python ------------------------------------------------------------
echo  [1] Verificare Python...
python --version
python --version >> "%DEBUGLOG%" 2>&1
if errorlevel 1 (
    echo  EROARE: Python nu este in PATH! >> "%DEBUGLOG%"
    echo  EROARE: Python nu este in PATH!
    pause & exit /b 1
)

:: ---- [2] Pachete -----------------------------------------------------------
echo.
echo  [2] Verificare pachete...
for %%P in (fastapi uvicorn openai docx dotenv pystray PIL pdfplumber mutagen) do (
    python -c "import %%P; print('  %%P OK')" 2>&1
    python -c "import %%P; print('  %%P OK')" >> "%DEBUGLOG%" 2>&1
)

:: ---- [3] .env --------------------------------------------------------------
echo.
echo  [3] Verificare .env...
if exist "%ROOT%\.env" (
    echo  .env gasit OK
    echo  .env gasit OK >> "%DEBUGLOG%"
) else (
    echo  EROARE: .env lipseste!
    echo  EROARE: .env lipseste! >> "%DEBUGLOG%"
    pause & exit /b 1
)

:: ---- [4] config.py ---------------------------------------------------------
echo.
echo  [4] Test import config.py...
python -c "import sys; sys.path.insert(0,'_app'); import config; print('  config OK - PORT:', config.PORT, '  MACHINE_CODE:', config.MACHINE_CODE)" 2>&1
python -c "import sys; sys.path.insert(0,'_app'); import config; print('  config OK - PORT:', config.PORT, '  MACHINE_CODE:', config.MACHINE_CODE)" >> "%DEBUGLOG%" 2>&1
if errorlevel 1 (
    echo  EROARE in config.py! >> "%DEBUGLOG%"
    pause & exit /b 1
)

:: ---- [5] auth.py + main.py -------------------------------------------------
echo.
echo  [5] Test import main.py (si auth.py)...
python -c "import sys; sys.path.insert(0,'_app'); import main; print('  main.py OK')" 2>&1
python -c "import sys; sys.path.insert(0,'_app'); import main; print('  main.py OK')" >> "%DEBUGLOG%" 2>&1
if errorlevel 1 (
    echo  EROARE in main.py sau dependente! >> "%DEBUGLOG%"
    echo  Verificati eroarea de mai sus si in DEBUG_output.txt
    pause & exit /b 1
)

:: ---- [6] Pornire server vizibila -------------------------------------------
echo.
echo  [6] Pornire server vizibil (Ctrl+C pentru a opri)...
echo      http://localhost:8000
echo.
echo  [6] Pornire server >> "%DEBUGLOG%"
python _app\main.py 2>&1
python _app\main.py >> "%DEBUGLOG%" 2>&1

echo.
echo  ============================================================
echo   Serverul s-a oprit. Eroarea este mai sus si in DEBUG_output.txt
echo  ============================================================
echo.
pause
