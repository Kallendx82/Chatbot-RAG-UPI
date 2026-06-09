@echo off
REM Convenience: stop backend + frontend.
setlocal
set "HERE=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%start.ps1" -Stop
endlocal
pause
