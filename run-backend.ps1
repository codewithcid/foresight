# Foresight — start the API (http://127.0.0.1:8000)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) { Write-Host "Run .\setup.ps1 first." -ForegroundColor Yellow; exit 1 }
if (-not (Test-Path (Join-Path $root "data\customers.parquet"))) {
  Write-Host "Generating synthetic journeys..." -ForegroundColor Cyan
  & $py (Join-Path $root "data\generate.py")
}

Set-Location (Join-Path $root "backend")
& $py -m uvicorn main:app --host 127.0.0.1 --port 8000
