@echo off
title Voice Intake - Eliminare din pornire Windows

for /f "delims=" %%i in ('powershell -NoProfile -Command "[Environment]::GetFolderPath(\"Startup\")"') do set "STARTUP=%%i"
set "SHORTCUT=%STARTUP%\VoiceIntake - Pornire automata.lnk"

if exist "%SHORTCUT%" (
    del "%SHORTCUT%"
    echo  [OK] Voice Intake eliminat din pornire automata.
) else (
    echo  Nu a fost gasit shortcut-ul in Startup.
)

echo.
pause
