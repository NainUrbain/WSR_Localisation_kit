@echo off
setlocal
set "PYTHON=python"
set "SOURCE=%~dp0..\wsr_package_build"
set "STAGE=%~dp0dist\WSR_KR_translator"

"%PYTHON%" "%~dp0build_translator_release.py" --source "%SOURCE%" --output "%STAGE%"
if errorlevel 1 exit /b 1

"%PYTHON%" -m PyInstaller --onefile --name WSR_KR_translator --distpath "%STAGE%" --workpath "%~dp0build\translator" --specpath "%~dp0build" --add-data "%STAGE%\game_files;game_files" --add-data "%STAGE%\payload_manifest.json;." --add-data "%STAGE%\patch_manifest.json;." --console --noconfirm "%SOURCE%\install_patch.py"
if errorlevel 1 exit /b 1

echo Done: dist\WSR_KR_translator\
