@echo off
setlocal
cd /d "%~dp0"
title MusicTagEditor
echo Starting MusicTagEditor (Conda: TTS)...
"C:\Tools\Anaconda3\envs\TTS\python.exe" "%~dp0main.py" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Error] Program exited with code: %ERRORLEVEL%
    pause
)
endlocal
