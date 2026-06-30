@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
set "EXTRA="
if "%~1"=="--no-run-detected-live" set "EXTRA=--no-run-detected-live"
echo relayprobe quickstart
echo Project root: %cd%
echo Output: %cd%\artifacts\quickstart
python -m relayprobe quickstart --out artifacts\quickstart %EXTRA%
if errorlevel 1 (
  echo.
  echo relayprobe quickstart failed.
  exit /b 1
)
echo.
echo relayprobe quickstart finished successfully.
