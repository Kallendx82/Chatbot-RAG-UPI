@echo off
REM Double-click launcher for the UPI RAG Chatbot.
REM Delegates to start.ps1, bypassing the default execution policy.
setlocal
set "HERE=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%start.ps1" %*
if errorlevel 1 (
    echo.
    echo Launcher exited with errors. See messages above.
    pause
)
endlocal
