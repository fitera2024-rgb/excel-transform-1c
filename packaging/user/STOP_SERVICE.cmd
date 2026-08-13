@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0STOP_SERVICE.ps1"
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
