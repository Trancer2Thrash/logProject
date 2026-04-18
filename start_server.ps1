# EDR Tool - Server (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  EDR Tool - Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot
conda activate edr-tool

Write-Host "Starting server..." -ForegroundColor Yellow
Write-Host "Web UI: http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""

python -m server.main
