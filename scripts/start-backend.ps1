# Window 3: backend API on http://127.0.0.1:8000 (docs at /docs)
Set-Location "$(Split-Path $PSScriptRoot -Parent)\backend"
& .\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000