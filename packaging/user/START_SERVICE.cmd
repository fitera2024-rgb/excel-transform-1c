@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0START_SERVICE.ps1"
set "RESULT=%ERRORLEVEL%"

if not "%RESULT%"=="0" (
  echo.
  echo Запуск не выполнен. Подробности сохранены в startup.log.
  echo Пришлите файл startup.log координатору.
  echo.
  pause
)

exit /b %RESULT%
