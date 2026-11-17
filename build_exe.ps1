# ArchForge Windows Executable Builder (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "         ArchForge Windows Executable Builder         " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python 3.11+ is required but not found in PATH."
    exit 1
}

if (-not (Test-Path "venv")) {
    Write-Host "[1/3] Creating virtual environment 'venv'..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "[2/3] Installing requirements and PyInstaller..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

Write-Host "[3/3] Building ArchForge.exe via PyInstaller..." -ForegroundColor Yellow
pyinstaller ArchForge.spec --clean --noconfirm

if (Test-Path "dist\ArchForge.exe") {
    Write-Host "`n=====================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Double-click executable generated:" -ForegroundColor Green
    Write-Host (Resolve-Path "dist\ArchForge.exe").Path -ForegroundColor White
    Write-Host "=====================================================" -ForegroundColor Green
} else {
    Write-Error "PyInstaller build failed. dist\ArchForge.exe was not created."
    exit 1
}
