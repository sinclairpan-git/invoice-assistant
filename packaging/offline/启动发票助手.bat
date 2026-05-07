@echo off
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

call "%ROOT%\start_invoice_assistant.bat"
exit /b %ERRORLEVEL%
