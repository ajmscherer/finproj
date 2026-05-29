@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
  set PYTHON=python
  goto run
)

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
  set PYTHON=py
  goto run
)

echo Error: Python not found. Install Python 3.10+ and try again.
exit /b 1

:run
%PYTHON% -c "import streamlit" >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo Installing GUI dependencies from requirements-gui.txt...
  %PYTHON% -m pip install -r requirements-gui.txt
  if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
)

%PYTHON% -m streamlit run gui/app.py --server.address localhost --server.headless false %*
exit /b %ERRORLEVEL%
