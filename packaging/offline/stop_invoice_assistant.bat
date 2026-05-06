@echo off
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PYTHON_EXE=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Invoice Assistant is not running.
  exit /b 0
)
"%PYTHON_EXE%" "%ROOT%\app\bootstrap\stop_portable.py" --portable-root "%ROOT%"
