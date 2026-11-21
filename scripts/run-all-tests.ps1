
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv313\Scripts\python.exe"
$Blockchain = Join-Path $ProjectRoot "blockchain"

if (-not (Test-Path $Python)) {
    throw "Python executable not found: $Python"
}

if (-not (Test-Path (Join-Path $Blockchain "package.json"))) {
    throw "Blockchain package.json not found."
}

$Failed = $false

Write-Host "== Backend tests (pytest) =="

Push-Location $ProjectRoot
try {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        $Failed = $true
    }
}
finally {
    Pop-Location
}

Write-Host "== Contract tests (Hardhat) =="

Push-Location $Blockchain
try {
    & npm.cmd test
    if ($LASTEXITCODE -ne 0) {
        $Failed = $true
    }
}
finally {
    Pop-Location
}

if ($Failed) {
    Write-Host "SOME TESTS FAILED" -ForegroundColor Red
    exit 1
}

Write-Host "ALL TESTS PASSED" -ForegroundColor Green
