@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
echo relayprobe quickstart
echo Project root: %cd%
echo Output: %cd%\artifacts\quickstart
python -m relayprobe quickstart --out artifacts\quickstart
if errorlevel 1 (
  echo.
  echo relayprobe quickstart failed.
  exit /b 1
)
echo.
echo relayprobe quickstart finished successfully.
