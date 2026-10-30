$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the environment first: python -m venv .venv'
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'backend\.env'))) {
    throw 'Copy backend/.env.example to backend/.env and set DEEPSEEK_API_KEY first.'
}
Push-Location (Join-Path $projectRoot 'backend')
try {
    & $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    if ($LASTEXITCODE -ne 0) { throw "Uvicorn exited with code $LASTEXITCODE" }
} finally {
    Pop-Location
}
