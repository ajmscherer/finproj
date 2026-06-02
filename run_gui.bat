@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
  set "SYSTEM_PYTHON=python"
  goto have_python
)

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
  set "SYSTEM_PYTHON=py -3"
  goto have_python
)

echo Error: Python not found. Install Python 3.10+ and try again.
exit /b 1

:have_python
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment in .venv ...
  %SYSTEM_PYTHON% -m venv .venv
  if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
)

call ".venv\Scripts\activate.bat"

python -c "import streamlit" >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo Installing GUI dependencies from requirements-gui.txt ...
  python -m pip install -r requirements-gui.txt
  if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
)

python -m streamlit run gui/app.py --server.address localhost --server.headless false %*
exit /b %ERRORLEVEL%
