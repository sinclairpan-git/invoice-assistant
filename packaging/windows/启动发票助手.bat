@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON_EXE=%ROOT%app\python\python.exe"
set "START_SCRIPT=%ROOT%app\bootstrap\start_server.py"
set "APP_URL=http://127.0.0.1:18080"
set "PID_FILE=%ROOT%runtime\app.pid"
set "URL_FILE=%ROOT%runtime\app.url"
set "STARTUP_LOG=%ROOT%logs\startup.log"

if not exist "%ROOT%data" mkdir "%ROOT%data"
if not exist "%ROOT%data\storage" mkdir "%ROOT%data\storage"
if not exist "%ROOT%data\exports" mkdir "%ROOT%data\exports"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
if not exist "%ROOT%runtime" mkdir "%ROOT%runtime"

call :check_writable "%ROOT%data" 数据目录 || goto :writable_failed
call :check_writable "%ROOT%logs" 日志目录 || goto :writable_failed
call :check_writable "%ROOT%runtime" 运行目录 || goto :writable_failed

if not exist "%PYTHON_EXE%" (
  echo 启动失败：未找到内置 Python 运行时。
  echo 请确认便携包已完整解压，或把这个窗口截图发给维护人员。
  exit /b 1
)

if not exist "%START_SCRIPT%" (
  echo 启动失败：未找到启动入口脚本。
  echo 请确认便携包文件未被误删，或把这个窗口截图发给维护人员。
  exit /b 1
)

if exist "%PID_FILE%" (
  set "RUNNING_PID="
  for /f usebackq %%p in ("%PID_FILE%") do set "RUNNING_PID=%%p"
  if defined RUNNING_PID (
    tasklist /FI "PID eq %RUNNING_PID%" | findstr /R /C:" %RUNNING_PID% " >nul 2>&1
    if not errorlevel 1 (
      call :probe_ready
      if not errorlevel 1 (
        echo 发票助手已在运行，正在为你打开页面...
        if exist "%URL_FILE%" (
          set /p APP_URL=<"%URL_FILE%"
        )
        start "" "%APP_URL%"
        exit /b 0
      )
      echo 检测到旧实例仍在运行，但当前页面不可用，正在尝试重新启动...
      taskkill /PID %RUNNING_PID% /T /F >nul 2>&1
    )
  )
  del "%PID_FILE%" >nul 2>&1
  if exist "%URL_FILE%" del "%URL_FILE%" >nul 2>&1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$conn = Get-NetTCPConnection -LocalPort 18080 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if ($conn) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo 启动失败：127.0.0.1:18080 已被其他程序占用。
  echo 请确认没有重复打开两个发票助手窗口。
  echo 如果还是失败，请把这个窗口截图发给维护人员。
  exit /b 1
)

echo 正在启动发票助手...
start "发票助手服务" /B "%PYTHON_EXE%" "%START_SCRIPT%" --portable-root "%ROOT%" --host 127.0.0.1 --port 18080 > "%STARTUP_LOG%" 2>&1

call :probe_ready
if errorlevel 1 (
  echo 发票助手启动失败。
  echo 请把整个发票助手文件夹移动到桌面或文档这类本地可写位置后再试。
  echo 请确认没有重复打开两个发票助手窗口。
  echo 如果还是失败，请把这个窗口截图发给维护人员。
  echo 日志位置：%STARTUP_LOG%
  exit /b 1
)

if exist "%URL_FILE%" (
  set /p APP_URL=<"%URL_FILE%"
)

start "" "%APP_URL%"
echo 发票助手已启动，页面会自动打开。
exit /b 0

:check_writable
set "TARGET_DIR=%~1"
set "TARGET_LABEL=%~2"
set "PROBE_FILE=%TARGET_DIR%\.__invoice_assistant_write_probe__"
break > "%PROBE_FILE%" 2>nul
if errorlevel 1 (
  echo 启动失败：%TARGET_LABEL% 不可写。
  exit /b 1
)
del "%PROBE_FILE%" >nul 2>&1
exit /b 0

:probe_ready
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ok = $false; for ($i = 0; $i -lt 30; $i++) { try { $health = Invoke-WebRequest 'http://127.0.0.1:18080/health' -UseBasicParsing -TimeoutSec 2; $home = Invoke-WebRequest 'http://127.0.0.1:18080/' -UseBasicParsing -TimeoutSec 2; if ($health.StatusCode -eq 200 -and $home.StatusCode -eq 200) { $ok = $true; break } } catch {}; Start-Sleep -Milliseconds 500 }; if ($ok) { exit 0 } else { exit 1 }"
exit /b %ERRORLEVEL%

:writable_failed
echo 请把整个发票助手文件夹移动到桌面或文档这类本地可写位置后再试。
echo 如果还是失败，请把这个窗口截图发给维护人员。
exit /b 1
