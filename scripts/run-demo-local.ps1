$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}

$demoRoot = Join-Path $projectRoot ".demo"
$env:DEMO_MODE = "true"
$env:SQLITE_PATH = Join-Path $demoRoot "storage\knowledge.db"
$env:UPLOADS_DIR = Join-Path $demoRoot "data\uploads"
$env:PROCESSED_DIR = Join-Path $demoRoot "data\processed"
$env:VECTOR_DIR = Join-Path $demoRoot "storage\vector_db"
$env:API_URL = "http://127.0.0.1:8000"
$env:PUBLIC_API_URL = $env:API_URL
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

New-Item -ItemType Directory -Path (Split-Path -Parent $env:SQLITE_PATH) -Force | Out-Null

$api = Start-Process -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            Invoke-RestMethod -Uri "$env:API_URL/health" -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) {
        throw "Demo API did not become ready."
    }

    Write-Host "Demo is ready at http://localhost:8501" -ForegroundColor Green
    & $python -m streamlit run ui.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true
}
finally {
    if ($api -and -not $api.HasExited) {
        Stop-Process -Id $api.Id -Force
    }
}

