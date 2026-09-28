@echo off
setlocal
rem Usage: this_file.bat [locale]   (default ko-KR)
set "PYTHON=python"
set "SOURCE=%~dp0..\wsr_package_build"
set "STAGE=%~dp0user_release"
set "LOCALE=%~1"
if "%LOCALE%"=="" set "LOCALE=ko-KR"
set "NAME=WSR_%LOCALE%_user"
if /I "%LOCALE%"=="ko-KR" set "NAME=WSR_KR_user"

"%PYTHON%" "%~dp0build_user_release.py" --source "%SOURCE%" --output "%STAGE%" --locale "%LOCALE%"
if errorlevel 1 exit /b 1

"%PYTHON%" -m PyInstaller --onefile --name "%NAME%" --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" --add-data "%STAGE%\game_files;game_files" --add-data "%STAGE%\payload_manifest.json;." --add-data "%~dp0patch_manifest.json;." --console --noconfirm "%~dp0install_patch_dist.py"
if errorlevel 1 exit /b 1

echo Done: dist\%NAME%.exe
