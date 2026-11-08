@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\run_delivery_demo.py serve %*
) else (
  py -3.12 scripts\run_delivery_demo.py serve %*
)
set "ECOSCAN_EXIT=%ERRORLEVEL%"
if not "%ECOSCAN_EXIT%"=="0" echo Confira README_EXECUCAO.md e a instalacao Python 3.12.
pause
exit /b %ECOSCAN_EXIT%
