@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_CMD="
where python.exe >nul 2>nul && set "PYTHON_CMD=python.exe"
if not defined PYTHON_CMD (
  where py.exe >nul 2>nul && set "PYTHON_CMD=py.exe -3.11"
)

if not defined PYTHON_CMD (
  echo.
  echo Python 3.11 или новее не найден.
  echo Установите 64-bit Python 3.11+ и включите опцию Add Python to PATH.
  echo После установки снова запустите START_SERVICE.cmd.
  echo.
  pause
  exit /b 1
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 (
  echo.
  echo Нужен Python версии 3.11 или новее.
  echo.
  pause
  exit /b 1
)

set "VENV_PY=%CD%\.venv\Scripts\python.exe"
set "NEED_INSTALL=0"
if not exist "%VENV_PY%" set "NEED_INSTALL=1"
if not exist "%CD%\.venv\PACKAGE_BUILD.txt" set "NEED_INSTALL=1"
if exist "%CD%\.venv\PACKAGE_BUILD.txt" (
  fc /b "%CD%\PACKAGE_BUILD.txt" "%CD%\.venv\PACKAGE_BUILD.txt" >nul 2>nul
  if errorlevel 1 set "NEED_INSTALL=1"
)

if "%NEED_INSTALL%"=="1" (
  echo.
  echo Подготовка локального окружения. Это выполняется только для новой версии пакета...
  if not exist "%VENV_PY%" (
    %PYTHON_CMD% -m venv "%CD%\.venv"
    if errorlevel 1 goto :install_error
  )
  "%VENV_PY%" -m pip install --no-index --find-links "%CD%\wheels" --upgrade --force-reinstall excel-transform-1c
  if errorlevel 1 goto :install_error
  copy /y "%CD%\PACKAGE_BUILD.txt" "%CD%\.venv\PACKAGE_BUILD.txt" >nul
)

powershell.exe -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 1; if($r.StatusCode -eq 200){ exit 0 } } catch {}; exit 1" >nul 2>nul
if not errorlevel 1 (
  echo.
  echo Порт 8000 уже занят работающим сервисом.
  echo Закройте предыдущее окно сервиса сочетанием Ctrl+C и запустите пакет снова.
  echo.
  pause
  exit /b 1
)

set "EXCEL_TRANSFORM_RUNTIME=%CD%\runtime"
set "PYTHONUTF8=1"
if not exist "%EXCEL_TRANSFORM_RUNTIME%" mkdir "%EXCEL_TRANSFORM_RUNTIME%"

start "" powershell.exe -NoProfile -WindowStyle Hidden -Command "$u='http://127.0.0.1:8000/health'; for($i=0; $i -lt 80; $i++){ try { $r=Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 1; if($r.StatusCode -eq 200){ Start-Process 'http://127.0.0.1:8000'; exit } } catch {}; Start-Sleep -Milliseconds 500 }"

echo.
echo Excel -^> OPIU Light запускается локально.
echo После запуска браузер откроется автоматически: http://127.0.0.1:8000
echo Для остановки сервиса нажмите Ctrl+C в этом окне.
echo Не удаляйте папку runtime: в ней сохраняются справочники и сценарии.
echo.
"%VENV_PY%" -m excel_transform_1c.main
exit /b %errorlevel%

:install_error
echo.
echo Не удалось установить компоненты из локальной папки wheels.
echo Не удаляйте файлы пакета и попробуйте распаковать архив заново.
echo.
pause
exit /b 1
