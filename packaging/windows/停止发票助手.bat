@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PYTHON_EXE=%ROOT%\app\python\python.exe"
set "STOPPER=%ROOT%\app\bootstrap\stop_portable.py"

if not exist "%PYTHON_EXE%" (
  echo Stop failed: missing bundled Python runtime.
  echo Press any key to close...
  pause >nul
  exit /b 1
)

if not exist "%STOPPER%" (
  echo Stop failed: missing stop bootstrap.
  echo Press any key to close...
  pause >nul
  exit /b 1
)

set "PYTHONUTF8=1"
"%PYTHON_EXE%" "%STOPPER%" --portable-root "%ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo Stop failed. Check logs\startup.log.
  echo Press any key to close...
  pause >nul
)

exit /b %EXIT_CODE%
