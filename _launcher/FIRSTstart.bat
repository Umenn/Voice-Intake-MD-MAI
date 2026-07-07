@echo off
title Voice Intake v0.0.4 - PRIMA CONFIGURARE
set "ROOT=%~dp0.."
cd /d "%ROOT%"
color 0B

echo.
echo  ============================================================
echo   Voice Intake v0.0.4  -  PRIMA CONFIGURARE (First Start)
echo  ============================================================
echo.
echo  Rulati o singura data pe un PC nou.
echo  Data viitoare folositi start_background.bat
echo.
echo  Apasati orice tasta pentru a incepe...
pause >nul

:: ---- COD PC (configurare automata) ----------------------------------------
echo.
echo  ============================================================
echo   Aveti un cod de configurare PC? (ex: PC1, PC2, PC3...)
echo   Apasati ENTER pentru configurare manuala standard.
echo  ============================================================
echo.
set "PC_CODE="
set /p PC_CODE="  Cod PC (optional, ENTER pt skip): "

if not defined PC_CODE goto :step1

:: Normalizeaza codul (uppercase)
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "'%PC_CODE%'.ToUpper()"`) do set PC_CODE=%%i

echo.
echo  Se cauta configuratia pentru codul: %PC_CODE%
echo.

:: Citeste pc_configs.ini cu PowerShell
powershell -NoProfile -Command ^
  "$ini='%~dp0pc_configs.ini';" ^
  "if(!(Test-Path $ini)){Write-Host 'NOTFOUND'; exit}" ^
  "$cfg=Get-Content $ini -Raw;" ^
  "$section=$false; $key=''; $tok=''; $ngrok='';" ^
  "foreach($line in ($cfg -split '\r?\n')) {" ^
  "  if($line -match '^\[(.+)\]$'){$section=($matches[1].ToUpper() -eq '%PC_CODE%')}" ^
  "  if($section -and $line -match '^OPENAI_API_KEY\s*=\s*(.+)$'){$key=$matches[1].Trim()}" ^
  "  if($section -and $line -match '^NGROK_TOKEN\s*=\s*(.+)$'){$ngrok=$matches[1].Trim()}" ^
  "}" ^
  "if($key -and $key -notmatch 'COMPLETATI'){" ^
  "  Write-Host ('KEY='+$key); Write-Host ('NGROK='+$ngrok)" ^
  "} else { Write-Host 'NOTFOUND' }" ^
  > "%TEMP%\vi_pc.txt" 2>nul

set "PC_KEY_FOUND=0"
findstr /i "KEY=sk-" "%TEMP%\vi_pc.txt" >nul 2>&1
if not errorlevel 1 set "PC_KEY_FOUND=1"

if "%PC_KEY_FOUND%"=="0" (
    echo  [AVERTIZARE] Codul "%PC_CODE%" nu a fost gasit sau nu este configurat.
    echo  Continuare cu configurare manuala...
    echo.
    goto :step1
)

:: Extrage valorile
for /f "tokens=1,* delims==" %%a in ('findstr "KEY=" "%TEMP%\vi_pc.txt"') do set "AUTO_OPENAI=%%b"
for /f "tokens=1,* delims==" %%a in ('findstr "NGROK=" "%TEMP%\vi_pc.txt"') do set "AUTO_NGROK=%%b"

echo  Configuratie gasita pentru %PC_CODE%!
echo  Cheie OpenAI: ****...%AUTO_OPENAI:~-8%
if defined AUTO_NGROK echo  Token ngrok:  ****...%AUTO_NGROK:~-8%
echo.

:: Scrie direct in .env
if exist "%ROOT%\.env" (
    :: Sterge liniile vechi daca exista
    powershell -NoProfile -Command ^
      "$env='%ROOT%\.env';" ^
      "$lines=Get-Content $env | Where-Object {$_ -notmatch '^OPENAI_API_KEY=' -and $_ -notmatch '^NGROK_TOKEN='};" ^
      "Set-Content $env $lines"
)
echo OPENAI_API_KEY=%AUTO_OPENAI%>> "%ROOT%\.env"
if defined AUTO_NGROK if not "%AUTO_NGROK%"=="COMPLETATI_TOKENUL_NGROK" (
    echo NGROK_TOKEN=%AUTO_NGROK%>> "%ROOT%\.env"
)
findstr /i "^PORT=" "%ROOT%\.env" >nul 2>&1
if errorlevel 1 echo PORT=8000>> "%ROOT%\.env"
findstr /i "^HOST=" "%ROOT%\.env" >nul 2>&1
if errorlevel 1 echo HOST=0.0.0.0>> "%ROOT%\.env"

echo  .env configurat automat. Pasul cheii OpenAI va fi sarit.
set "NEED_KEY=0"
echo.


:step1
:: ---- PASUL 1: Structura directoare ----------------------------------------
echo.
echo  [1/6] Creare directoare...
if not exist "%ROOT%\data"        mkdir "%ROOT%\data"
if not exist "%ROOT%\templates"   mkdir "%ROOT%\templates"
if not exist "%ROOT%\cases"       mkdir "%ROOT%\cases"
if not exist "%ROOT%\uploads"     mkdir "%ROOT%\uploads"
if not exist "%ROOT%\logs"        mkdir "%ROOT%\logs"
if not exist "%ROOT%\logs\app"    mkdir "%ROOT%\logs\app"
if not exist "%ROOT%\logs\tray"   mkdir "%ROOT%\logs\tray"
if not exist "%ROOT%\logs\errors" mkdir "%ROOT%\logs\errors"
if not exist "%ROOT%\static"      mkdir "%ROOT%\static"
if not exist "%ROOT%\recordings"  mkdir "%ROOT%\recordings"
echo       OK.

:: ---- PASUL 2: Python -------------------------------------------------------
echo.
echo  [2/6] Verificare Python...

python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo       Gasit: %%v
    set PYEXE=python
    goto :step3
)

echo       Python nu este instalat.
echo       Instalare automata in curs (2-5 minute, asteptati)...
echo.

winget --version >nul 2>&1
if not errorlevel 1 (
    echo       Metoda: winget
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 goto :py_find
    echo       winget a esuat, se incearca descarcarea directa...
)

echo       Metoda: descarcare directa python.org
powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue';" ^
  "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'" ^
  " -OutFile '%ROOT%\_py_installer.exe' -UseBasicParsing"

if not exist "%ROOT%\_py_installer.exe" (
    echo.
    echo  [EROARE] Nu s-a putut descarca Python.
    echo  Descarcati manual: https://www.python.org/downloads/
    echo  Bifati "Add Python to PATH", instalati, apoi rulati FIRSTstart.bat din nou.
    echo.
    pause & exit /b 1
)

echo       Instalare silentioasa Python 3.12...
"%ROOT%\_py_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 ^
    Include_test=0 Include_doc=0 Include_launcher=1
del "%ROOT%\_py_installer.exe" >nul 2>&1

:py_find
python --version >nul 2>&1
if not errorlevel 1 ( set PYEXE=python & goto :step3 )

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :step3
)
if exist "%ProgramFiles%\Python312\python.exe" (
    set "PYEXE=%ProgramFiles%\Python312\python.exe"
    goto :step3
)

echo  Python instalat - PATH nu s-a actualizat. Relansare...
timeout /t 3 /nobreak >nul
start "" "%~f0"
exit /b 0

:: ---- PASUL 3: Pachete Python -----------------------------------------------
:step3
if not defined PYEXE set PYEXE=python
echo.
echo  [3/6] Instalare pachete Python...
echo  (openai, fastapi, uvicorn, pdfplumber, pytesseract etc.)
echo  Poate dura 2-5 minute:
echo.

"%PYEXE%" -m pip install --upgrade pip --quiet --disable-pip-version-check
"%PYEXE%" -m pip install -r "%ROOT%\requirements.txt" --disable-pip-version-check

if errorlevel 1 (
    echo.
    echo  [EROARE] Instalarea pachetelor a ESUAT.
    echo  Verificati conexiunea la internet si cititi erorile de mai sus.
    echo.
    pause & exit /b 1
)
echo.
echo       Toate pachetele instalate cu succes.

:: ---- PASUL 4: Tesseract OCR ------------------------------------------------
echo.
echo  [4/6] Instalare Tesseract OCR (pentru modul Scanat/PDF)...

where tesseract >nul 2>&1
if not errorlevel 1 (
    echo       Tesseract deja instalat. Se verifica limbile...
    goto :tess_langs
)

echo       Tesseract nu este instalat. Instalare automata...
echo.

winget --version >nul 2>&1
if not errorlevel 1 (
    echo       Metoda: winget
    winget install UB-Mannheim.TesseractOCR -e --silent ^
        --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 (
        echo       winget: Tesseract instalat.
        goto :tess_langs
    )
    echo       winget a esuat, se incearca descarcarea directa...
)

echo       Metoda: descarcare directa UB-Mannheim
powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue';" ^
  "$url='https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe';" ^
  "Invoke-WebRequest -Uri $url -OutFile '%ROOT%\_tess_setup.exe' -UseBasicParsing"

if exist "%ROOT%\_tess_setup.exe" (
    echo       Instalare Tesseract silentios...
    "%ROOT%\_tess_setup.exe" /S
    del "%ROOT%\_tess_setup.exe" >nul 2>&1
    echo       Tesseract instalat.
) else (
    echo       [AVERTIZARE] Nu s-a putut descarca Tesseract.
    echo       Modul "Scanat/PDF" pe imagini nu va functiona.
    goto :step5
)

:tess_langs
echo       Descarcare pachete de limba: Romana + Rusa...

set "TESSDATA="
if exist "C:\Program Files\Tesseract-OCR\tessdata"       set "TESSDATA=C:\Program Files\Tesseract-OCR\tessdata"
if exist "C:\Program Files (x86)\Tesseract-OCR\tessdata" set "TESSDATA=C:\Program Files (x86)\Tesseract-OCR\tessdata"
for /f "tokens=*" %%i in ('where tesseract 2^>nul') do (
    for %%j in ("%%~dpi") do set "TESSDATA=%%~dpjtessdata"
)

if not defined TESSDATA (
    echo       [AVERTIZARE] Nu s-a gasit directorul tessdata.
    goto :tess_env
)

if not exist "%TESSDATA%\ron.traineddata" (
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata/raw/main/ron.traineddata' -OutFile '%TESSDATA%\ron.traineddata' -UseBasicParsing" 2>nul
    if exist "%TESSDATA%\ron.traineddata" (echo       ron.traineddata OK.) else (echo       [AVERTIZARE] ron.traineddata nu s-a putut descarca.)
) else ( echo       ron.traineddata deja prezent. )

if not exist "%TESSDATA%\rus.traineddata" (
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata/raw/main/rus.traineddata' -OutFile '%TESSDATA%\rus.traineddata' -UseBasicParsing" 2>nul
    if exist "%TESSDATA%\rus.traineddata" (echo       rus.traineddata OK.) else (echo       [AVERTIZARE] rus.traineddata nu s-a putut descarca.)
) else ( echo       rus.traineddata deja prezent. )

:tess_env
set "TESS_EXE="
for /f "tokens=*" %%i in ('where tesseract 2^>nul') do set "TESS_EXE=%%i"
if not defined TESS_EXE if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESS_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe"
if defined TESS_EXE (
    findstr /i "TESSERACT_CMD" "%ROOT%\.env" >nul 2>&1
    if errorlevel 1 echo TESSERACT_CMD=%TESS_EXE%>> "%ROOT%\.env"
    echo       TESSERACT_CMD salvat in .env
)

:: ---- PASUL 5: Cheie OpenAI -------------------------------------------------
:step5
echo.
echo  [5/6] Configurare cheie OpenAI API...
echo.

:: Verifica daca cheia lipseste sau e placeholder (indiferent daca .env exista)
set "NEED_KEY=1"
if exist "%ROOT%\.env" (
    findstr /i "OPENAI_API_KEY=sk-" "%ROOT%\.env" >nul 2>&1
    if not errorlevel 1 (
        :: Verifica ca nu e placeholder
        findstr /i "PUNETI\|YOUR.*KEY\|EXAMPLE\|sk-PUNETI" "%ROOT%\.env" >nul 2>&1
        if errorlevel 1 (
            echo       Cheie OpenAI gasita in .env - OK.
            set "NEED_KEY=0"
        )
    )
)

if "%NEED_KEY%"=="1" (
    :: Asigura-te ca variabilele de baza exista in .env
    if not exist "%ROOT%\.env" (
        echo OPENAI_API_KEY=> "%ROOT%\.env"
        echo PORT=8000>> "%ROOT%\.env"
        echo HOST=0.0.0.0>> "%ROOT%\.env"
    )
    findstr /i "OPENAI_API_KEY" "%ROOT%\.env" >nul 2>&1
    if errorlevel 1 echo OPENAI_API_KEY=>> "%ROOT%\.env"
    findstr /i "^PORT=" "%ROOT%\.env" >nul 2>&1
    if errorlevel 1 echo PORT=8000>> "%ROOT%\.env"
    findstr /i "^HOST=" "%ROOT%\.env" >nul 2>&1
    if errorlevel 1 echo HOST=0.0.0.0>> "%ROOT%\.env"

    echo  ======================================================
    echo    ACTIUNE NECESARA - Completati cheia OpenAI
    echo  ======================================================
    echo.
    echo    Fisierul .env se deschide acum in Notepad.
    echo.
    echo    Gasiti linia:   OPENAI_API_KEY=
    echo    Adaugati cheia: OPENAI_API_KEY=sk-proj-...
    echo.
    echo    Cheia o gasiti la: https://platform.openai.com/api-keys
    echo.
    echo    Salvati cu Ctrl+S, inchideti Notepad,
    echo    apoi apasati orice tasta AICI pentru a continua.
    echo  ======================================================
    echo.
    notepad "%ROOT%\.env"
    pause >nul

    findstr /i "OPENAI_API_KEY=sk-" "%ROOT%\.env" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [AVERTIZARE] Cheia OpenAI pare inca goala.
        echo  Transcrierea vocala NU va functiona fara ea.
        echo  Puteti adauga cheia mai tarziu in fisierul .env
        echo.
    ) else (
        echo       Cheie OpenAI salvata. OK.
    )
)

:: ---- PASUL 6: Sabloane documente -------------------------------------------
:step6
echo.
echo  [6/6] Generare sabloane documente (.docx)...
"%PYEXE%" "%ROOT%\_app\template_builder.py"
if errorlevel 1 (
    echo  [AVERTIZARE] template_builder a dat eroare - continuam oricum.
) else (
    echo       Toate cele 15 sabloane generate.
)

:: ---- PORNIRE SERVER --------------------------------------------------------
echo.
echo  ============================================================
echo   CONFIGURARE COMPLETA v0.0.4!
echo.
echo   Pornire server in fundal...
echo  ============================================================
echo.

python "%ROOT%\launch_tray.py"
if errorlevel 1 (
    echo  [EROARE] launch_tray.py a esuat. Rulati DEBUG_start.bat pentru detalii.
    pause & exit /b 1
)

timeout /t 6 /nobreak >nul

python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)" >nul 2>&1
if errorlevel 1 (
    echo  [AVERTIZARE] Serverul nu raspunde. Rulati DEBUG_start.bat.
) else (
    echo  Server activ. Pictograma verde in bara de sistem (dreapta-jos).
)

echo.
echo  Deschideti browser la:  http://localhost:8000
echo.
echo  ============================================================
echo   Conturi ofiteri (coduri de acces):
echo    SANDU01  -  Sandu Alexandru
echo    MOCAN02  -  Nikita Mocan
echo    CEBAN03  -  Dorin Ceban
echo    ROSCA04  -  Daniel Rosca
echo    MARTEA05 -  Lucian Martea
echo  ============================================================
echo.
echo  Data viitoare folositi start_background.bat (pornire rapida).
echo.
pause
