@echo off
setlocal
rem Usage: this_file.bat [locale] [game directory] [new output directory]
if not defined PYTHON for %%P in ("%USERPROFILE%\.local\bin\python3*.exe") do if exist "%%~fP" set "PYTHON=%%~fP"
if not defined PYTHON (
    for %%P in (python.exe python3.exe py.exe) do (
        if not defined PYTHON for /f "delims=" %%F in ('where %%P 2^>nul') do set "PYTHON=%%F"
    )
)
if not defined PYTHON (
    echo Python 3.10 or newer is required. Install Python or set PYTHON to its executable path.
    exit /b 1
)
set "LOCALE=%~1"
if "%LOCALE%"=="" set "LOCALE=ko-KR"
set "OUTPUT=%~3"
if "%OUTPUT%"=="" set "OUTPUT=%~dp0dist\workshop_%LOCALE%"
if "%~2"=="" (
    "%PYTHON%" "%~dp0build_workshop_release.py" --locale "%LOCALE%" --output "%OUTPUT%"
) else (
    "%PYTHON%" "%~dp0build_workshop_release.py" "%~2" --locale "%LOCALE%" --output "%OUTPUT%"
)
if errorlevel 1 exit /b 1
echo Upload this folder: %OUTPUT%\content
