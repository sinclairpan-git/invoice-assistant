@echo off
setlocal

set "ROOT=%~dp0"
set "PID_FILE=%ROOT%runtime\app.pid"

if not exist "%PID_FILE%" (
  echo 当前未检测到运行中的发票助手。
  exit /b 0
)

set "RUNNING_PID="
for /f usebackq %%p in ("%PID_FILE%") do set "RUNNING_PID=%%p"

if not defined RUNNING_PID goto :not_running

tasklist /FI "PID eq %RUNNING_PID%" | findstr /R /C:" %RUNNING_PID% " >nul 2>&1
if errorlevel 1 goto :not_running

taskkill /PID %RUNNING_PID% /T /F >nul 2>&1
if errorlevel 1 (
  echo 停止发票助手失败，请手动检查进程 %RUNNING_PID%。
  echo 日志位置：%ROOT%logs\startup.log
  exit /b 1
)

if exist "%PID_FILE%" del "%PID_FILE%"
if exist "%ROOT%runtime\app.url" del "%ROOT%runtime\app.url"

echo 发票助手已停止。
exit /b 0

:not_running
if exist "%PID_FILE%" del "%PID_FILE%" >nul 2>&1
if exist "%ROOT%runtime\app.url" del "%ROOT%runtime\app.url" >nul 2>&1
echo 当前未检测到运行中的发票助手。
exit /b 0
