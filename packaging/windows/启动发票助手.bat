@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PYTHON_EXE=%ROOT%\app\python\python.exe"
set "LAUNCHER=%ROOT%\app\bootstrap\launch_portable.py"

if not exist "%PYTHON_EXE%" (
  echo Startup failed: missing bundled Python runtime.
  echo Press any key to close...
  pause >nul
  exit /b 1
)

if not exist "%LAUNCHER%" (
  echo Startup failed: missing launcher bootstrap.
  echo Press any key to close...
  pause >nul
  exit /b 1
)

set "PYTHONUTF8=1"
"%PYTHON_EXE%" "%LAUNCHER%" --portable-root "%ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo Startup failed. Check logs\startup.log.
  echo Press any key to close...
  pause >nul
)

exit /b %EXIT_CODE%
