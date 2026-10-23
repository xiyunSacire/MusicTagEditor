@echo off
setlocal
title Build Release - MusicTagEditor
cd /d "%~dp0"
echo ============================================================
echo   Starting MusicTagEditor Release Build Pipeline...
echo ============================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed with exit code: %ERRORLEVEL%
)
echo.
pause
endlocal
