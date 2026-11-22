
# One-time setup: Python venv + packages, Hardhat packages, frontend packages, .env file.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$Python = Join-Path $root ".venv313\Scripts\python.exe"

Write-Host "== Backend ==" -ForegroundColor Cyan

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $root ".venv313")
}

& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

& $Python -m pip install -r (Join-Path $root "backend\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed" }

if (-not (Test-Path (Join-Path $root "backend\.env"))) {
    Copy-Item (Join-Path $root "backend\.env.example") (Join-Path $root "backend\.env")
    Write-Host "Created backend\.env"
}

Write-Host "== Blockchain ==" -ForegroundColor Cyan
Set-Location (Join-Path $root "blockchain")
npm install
if ($LASTEXITCODE -ne 0) { throw "Blockchain npm install failed" }

npx hardhat compile
if ($LASTEXITCODE -ne 0) { throw "Hardhat compilation failed" }

Write-Host "== Frontend ==" -ForegroundColor Cyan
Set-Location (Join-Path $root "frontend")
npm install
if ($LASTEXITCODE -ne 0) { throw "Frontend npm install failed" }

Set-Location $root
Write-Host "Setup finished. Next: scripts\start-blockchain.ps1" -ForegroundColor Green
