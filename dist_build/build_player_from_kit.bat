@echo off
setlocal
rem Run from the translator kit; optional first argument is a full locale code.
set "LOCALE=%~1"
if "%LOCALE%"=="" set "LOCALE=ko-KR"
python "%~dp0release_tools\build_user_release.py" --source "%~dp0." --output "%~dp0player_stage" --locale "%LOCALE%"
if errorlevel 1 exit /b 1
python -m PyInstaller --onefile --name "WSR_%LOCALE%_user" --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" --add-data "%~dp0player_stage\game_files;game_files" --add-data "%~dp0player_stage\payload_manifest.json;." --add-data "%~dp0release_tools\patch_manifest.json;." --console --noconfirm "%~dp0release_tools\install_patch_dist.py"
if errorlevel 1 exit /b 1
echo Done: dist\WSR_%LOCALE%_user.exe
