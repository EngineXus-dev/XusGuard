@echo off
REM Uni-Adblock - One-Command Installer & Runner for Windows
REM Downloads and runs Uni-Adblock from GitHub

echo.
echo ========================================
echo   Uni-Adblock - One-Command Installer
echo ========================================
echo.

set SCRIPT_URL=https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.2/uniadblock.py
set SOURCES_URL=https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.2/sources.json

REM Check for Python in PATH first
python --version >nul 2>&1
if %errorlevel% neq 0 (
    REM Check common Python installation locations
    if exist "C:\Python312\python.exe" (
        set "PATH=%PATH%;C:\Python312;C:\Python312\Scripts"
        python --version >nul 2>&1
    )
    if %errorlevel% neq 0 (
        if exist "C:\Program Files\Python312\python.exe" (
            set "PATH=%PATH%;C:\Program Files\Python312;C:\Program Files\Python312\Scripts"
            python --version >nul 2>&1
        )
    )
    if %errorlevel% neq 0 (
        if exist "C:\Program Files (x86)\Python312\python.exe" (
            set "PATH=%PATH%;C:\Program Files (x86)\Python312;C:\Program Files (x86)\Python312\Scripts"
            python --version >nul 2>&1
        )
    )
    if %errorlevel% neq 0 (
        REM Try to find Python in Program Files (any version)
        for /d %%i in ("C:\Program Files\Python*") do (
            if exist "%%i\python.exe" (
                set "PATH=%PATH%;%%i;%%i\Scripts"
                python --version >nul 2>&1
                if %errorlevel% equ 0 goto python_found
            )
        )
        for /d %%i in ("C:\Python*") do (
            if exist "%%i\python.exe" (
                set "PATH=%PATH%;%%i;%%i\Scripts"
                python --version >nul 2>&1
                if %errorlevel% equ 0 goto python_found
            )
        )
        
        REM Python not found, attempt installation
        echo [WARNING] Python is not installed or not in PATH
        echo.
        echo [INSTALL] Attempting to install Python 3...
        echo.
        
        REM Create temporary directory for Python installer
        set PYTHON_TEMP=%TEMP%\python_installer_%RANDOM%
        mkdir "%PYTHON_TEMP%" 2>nul
        
        REM Download Python installer (Windows 64-bit)
        echo [DOWNLOAD] Downloading Python 3 installer...
        powershell -Command "try { $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%PYTHON_TEMP%\python-installer.exe' -UseBasicParsing; Write-Host '[OK] Download complete' } catch { Write-Host '[ERROR] Failed to download Python installer'; Write-Host 'Please install Python 3 manually from: https://www.python.org/downloads/'; exit 1 }"
        
        if %errorlevel% neq 0 (
            echo.
            echo [ERROR] Failed to download Python installer
            echo Please install Python 3 manually from: https://www.python.org/downloads/
            echo Make sure to check "Add Python to PATH" during installation
            rmdir /s /q "%PYTHON_TEMP%" 2>nul
            pause
            exit /b 1
        )
        
        echo.
        echo [INSTALL] Installing Python 3 silently (this may take a few minutes)...
        echo The installer will automatically add Python to your PATH.
        echo.
        
        REM Run Python installer with silent install and add to PATH
        "%PYTHON_TEMP%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        
        REM Wait for installation to complete (check if installer process is still running)
        :wait_install
        timeout /t 2 /nobreak >nul
        tasklist /FI "IMAGENAME eq python-installer.exe" 2>NUL | find /I /N "python-installer.exe">NUL
        if "%ERRORLEVEL%"=="0" goto wait_install
        
        REM Additional wait to ensure PATH is updated
        timeout /t 3 /nobreak >nul
        
        REM Cleanup installer
        del "%PYTHON_TEMP%\python-installer.exe" 2>nul
        rmdir "%PYTHON_TEMP%" 2>nul
        
        REM Try to refresh PATH by checking common Python installation locations
        set "PATH=%PATH%;C:\Python312;C:\Python312\Scripts;C:\Program Files\Python312;C:\Program Files\Python312\Scripts;C:\Program Files (x86)\Python312;C:\Program Files (x86)\Python312\Scripts"
        
        REM Check if Python is now available
        python --version >nul 2>&1
        if %errorlevel% neq 0 (
            REM Try python3 command
            python3 --version >nul 2>&1
            if %errorlevel% equ 0 (
                set PYTHON_CMD=python3
                goto python_found
            ) else (
                echo.
                echo [WARNING] Python installation completed, but may not be in PATH yet
                echo Please close this window and run the installer again, or manually add Python to PATH
                echo.
                echo If Python was installed, you can also run:
                echo   python -m pip install --upgrade pip
                echo   python uniadblock.py
                echo.
                pause
                exit /b 1
            )
        )
        
        echo.
        echo [OK] Python installed successfully!
        echo.
    )
    :python_found
)

echo [OK] Found Python:
python --version

REM Create temporary directory
set TEMP_DIR=%TEMP%\uniadblock_%RANDOM%
mkdir "%TEMP_DIR%" 2>nul

echo.
echo [DOWNLOAD] Downloading Uni-Adblock...

REM Download script using PowerShell (works on Windows 7+)
powershell -Command "try { Invoke-WebRequest -Uri '%SCRIPT_URL%' -OutFile '%TEMP_DIR%\uniadblock.py' -UseBasicParsing } catch { Write-Host '[ERROR] Failed to download uniadblock.py'; exit 1 }"

if %errorlevel% neq 0 (
    echo [ERROR] Failed to download uniadblock.py
    echo Please check your internet connection
    pause
    exit /b 1
)

echo [DOWNLOAD] Downloading sources.json...
powershell -Command "try { Invoke-WebRequest -Uri '%SOURCES_URL%' -OutFile '%TEMP_DIR%\sources.json' -UseBasicParsing } catch { Write-Host '[WARNING] Failed to download sources.json (script will create default)' }"

echo [OK] Download complete
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorlevel% equ 0 (
    echo [ADMIN] Running with administrator privileges
) else (
    echo [WARNING] Not running as administrator
    echo You may need administrator privileges to modify hosts file
    echo Right-click and select "Run as Administrator" if you encounter permission errors
    echo.
)

REM Run the script
cd /d "%TEMP_DIR%"
if defined PYTHON_CMD (
    %PYTHON_CMD% uniadblock.py
) else (
    python uniadblock.py
)

REM Cleanup
cd /d "%TEMP%"
rmdir /s /q "%TEMP_DIR%" 2>nul

pause
