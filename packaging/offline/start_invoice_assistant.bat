@echo off
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PYTHON_EXE=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Missing offline runtime. Run install_offline.bat first.
  exit /b 1
)
"%PYTHON_EXE%" "%ROOT%\app\bootstrap\start_server.py" --portable-root "%ROOT%" --host 127.0.0.1 --port 18080
