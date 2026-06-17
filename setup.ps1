# Foresight — one-time setup (Windows / PowerShell)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "[1/4] Creating Python venv..." -ForegroundColor Cyan
if (-not (Test-Path $py)) { python -m venv (Join-Path $root ".venv") }

Write-Host "[2/4] Installing Python deps..." -ForegroundColor Cyan
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r (Join-Path $root "requirements.txt")

Write-Host "[3/4] Generating synthetic journeys..." -ForegroundColor Cyan
& $py (Join-Path $root "data\generate.py")

Write-Host "[4/4] Installing frontend deps..." -ForegroundColor Cyan
Push-Location (Join-Path $root "frontend"); npm install; Pop-Location

Write-Host "`nSetup complete. Now run, in two terminals:" -ForegroundColor Green
Write-Host "  .\run-backend.ps1"
Write-Host "  .\run-frontend.ps1   ->  http://localhost:5173"
