@echo off
setlocal
title Install Certificate - MusicTagEditor
cd /d "%~dp0"
echo ============================================================
echo   Installing MusicTagEditor Code Signing Certificate...
echo   Please click [Yes] if Windows displays a Security Warning.
echo ============================================================
echo.
certutil.exe -addstore -user root "%~dp0MusicTagEditor.cer"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo [SUCCESS] Certificate installed to Trusted Root Authorities!
    echo Running MusicTagEditor.exe will no longer trigger warnings.
    echo ============================================================
) else (
    echo.
    echo [NOTE] Certificate installation was canceled or failed.
)
echo.
pause
endlocal
