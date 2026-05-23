@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
  python code\inv_proj_run.py %*
  exit /b %ERRORLEVEL%
)

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
  py code\inv_proj_run.py %*
  exit /b %ERRORLEVEL%
)

echo Error: Python not found. Install Python 3.8+ and try again.
exit /b 1
