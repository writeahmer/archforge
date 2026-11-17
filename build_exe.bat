@echo off
setlocal enabledelayedexpansion

echo =====================================================
echo          ArchForge Windows Executable Builder        
echo =====================================================

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python 3.11+ is required but not found in PATH.
    pause
    exit /b 1
)

if not exist "venv" (
    echo [1/3] Creating Python virtual environment 'venv'...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
)

echo [2/3] Installing dependencies and PyInstaller...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo [3/3] Compiling standalone Windows executable ArchForge.exe...
pyinstaller ArchForge.spec --clean --noconfirm

if exist "dist\ArchForge.exe" (
    echo.
    echo =====================================================
    echo [SUCCESS] Double-click executable generated:
    echo %CD%\dist\ArchForge.exe
    echo =====================================================
) else (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

pause
