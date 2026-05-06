@echo off
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

where pwsh >nul 2>nul
if errorlevel 1 goto windows_powershell

pwsh -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\stop_invoice_assistant.ps1"
exit /b %ERRORLEVEL%

:windows_powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\stop_invoice_assistant.ps1"
exit /b %ERRORLEVEL%
