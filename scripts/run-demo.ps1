$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available in PATH."
}

Write-Host "Starting Enterprise Knowledge Platform Demo..." -ForegroundColor Cyan
docker compose -f compose.demo.yml up --build

