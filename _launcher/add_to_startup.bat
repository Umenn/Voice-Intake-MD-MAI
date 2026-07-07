@echo off
title Voice Intake - Adaugare la pornire Windows
set "ROOT=%~dp0.."
set "BAT=%ROOT%\_launcher\start_background.bat"

:: Get the actual Startup folder (works even with OneDrive)
for /f "delims=" %%i in ('powershell -NoProfile -Command "[Environment]::GetFolderPath(\"Startup\")"') do set "STARTUP=%%i"

set "SHORTCUT=%STARTUP%\VoiceIntake - Pornire automata.lnk"

echo.
echo  Adaugare Voice Intake la pornire automata Windows...
echo  Startup folder: %STARTUP%
echo.

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $sc = $ws.CreateShortcut('%SHORTCUT%'); ^
   $sc.TargetPath = '%BAT%'; ^
   $sc.WorkingDirectory = '%ROOT%'; ^
   $sc.Description = 'Voice Intake - pornire server in fundal'; ^
   $sc.Save()"

if exist "%SHORTCUT%" (
    echo  [OK] Shortcut creat in Startup.
    echo  Voice Intake va porni automat la urmatoarea logare Windows.
) else (
    echo  [EROARE] Nu s-a putut crea shortcut-ul.
    echo  Calea manuala: %STARTUP%
    echo  Copiati manual: %BAT%
)

echo.
pause
