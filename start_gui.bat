@echo off
setlocal
REM XusGuard Desktop - local Tkinter GUI. No download and no auto elevation.
cd /d "%~dp0"
if not exist "xusguard_gui.py" (
  echo [ERROR] Missing xusguard_gui.py. Extract the full repository.
  exit /b 1
)
where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 xusguard_gui.py
  exit /b %errorlevel%
)
where python >nul 2>&1
if %errorlevel% equ 0 (
  python xusguard_gui.py
  exit /b %errorlevel%
)
echo [ERROR] Python 3.10 or newer is required.
exit /b 1
