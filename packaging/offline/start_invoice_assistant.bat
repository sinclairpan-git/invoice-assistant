@echo off
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

where pwsh >nul 2>nul
if errorlevel 1 goto windows_powershell

pwsh -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\start_invoice_assistant.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
goto finish

:windows_powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\start_invoice_assistant.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

:finish
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Startup failed. Check logs\startup.log, then send it to support.
  if /i not "%CI%"=="true" pause
)
exit /b %EXIT_CODE%
