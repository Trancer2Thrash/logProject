# EDR Tool - Client (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  EDR Tool - Client" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot
conda activate edr-tool

$TOKEN = Read-Host "Enter Token"
$SERVER = Read-Host "Server URL (default: ws://localhost:8000/ws)"

if ([string]::IsNullOrWhiteSpace($SERVER)) {
    $SERVER = "ws://localhost:8000/ws"
}

Write-Host ""
Write-Host "Connecting to: $SERVER" -ForegroundColor Yellow
python -m client.main --server $SERVER --token $TOKEN
