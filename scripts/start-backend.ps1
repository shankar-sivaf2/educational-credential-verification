
# Window 3: backend API on http://127.0.0.1:8000 (docs at /docs)
$root = Split-Path $PSScriptRoot -Parent
$Python = Join-Path $root ".venv313\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python environment not found: $Python. Run scripts\setup.ps1 first."
}

Set-Location (Join-Path $root "backend")
& $Python -m uvicorn main:app --reload --port 8000
