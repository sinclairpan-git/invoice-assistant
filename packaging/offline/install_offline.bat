@echo off
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PYTHON_CMD=python"
if not "%PYTHON%"=="" set "PYTHON_CMD=%PYTHON%"

"%PYTHON_CMD%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 exit /b 1
"%PYTHON_CMD%" -m venv "%ROOT%\.venv"
if errorlevel 1 exit /b 1
"%ROOT%\.venv\Scripts\python.exe" -m pip install --no-index --find-links "%ROOT%\wheels" -r "%ROOT%\runtime-requirements.txt"
if errorlevel 1 exit /b 1
echo Invoice Assistant offline runtime installed: "%ROOT%\.venv"
