@echo off
setlocal
REM XusGuard - EngineXus-dev. Local-only launcher; no network execution.
cd /d "%~dp0"
if not exist "uniadblock.py" (
  echo [ERROR] uniadblock.py is missing. Extract the complete XusGuard repository first.
  exit /b 1
)
if not exist "sources.json" (
  echo [ERROR] sources.json is missing. Extract the complete XusGuard repository first.
  exit /b 1
)
where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 --version >nul 2>&1
  if not errorlevel 1 (
    py -3 uniadblock.py
    exit /b %errorlevel%
  )
)
where python >nul 2>&1
if %errorlevel% equ 0 (
  python uniadblock.py
  exit /b %errorlevel%
)
echo [ERROR] Install Python 3.10+ manually from https://www.python.org/downloads/
exit /b 1
