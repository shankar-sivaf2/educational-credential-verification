# One-time setup: Python venv + packages, Hardhat packages, frontend packages, .env file.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

Write-Host "== Backend ==" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path "venv")) { python -m venv venv }
& .\venv\Scripts\python.exe -m pip install --upgrade pip
& .\venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path ".env")) { Copy-Item .env.example .env; Write-Host "Created backend\.env" }

Write-Host "== Blockchain ==" -ForegroundColor Cyan
Set-Location "$root\blockchain"
npm install
npx hardhat compile

Write-Host "== Frontend ==" -ForegroundColor Cyan
Set-Location "$root\frontend"
npm install

Set-Location $root
Write-Host "Setup finished. Next: scripts\start-blockchain.ps1" -ForegroundColor Green