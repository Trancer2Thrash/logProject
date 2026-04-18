# EDR Tool - Environment Setup (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  EDR Tool - Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check conda
Write-Host "Checking Anaconda..." -ForegroundColor Yellow
$conda = Get-Command conda -ErrorAction SilentlyContinue
if (-not $conda) {
    Write-Host "[ERROR] Conda not found. Please install Anaconda/Miniconda first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create environment
Write-Host "Creating virtual environment: edr-tool" -ForegroundColor Yellow
conda create -n edr-tool python=3.10 -y

# Install dependencies
Write-Host ""
Write-Host "Installing server dependencies..." -ForegroundColor Yellow
Push-Location "$PSScriptRoot\server"
conda activate edr-tool
pip install -r requirements.txt -q
Pop-Location

Write-Host "Installing client dependencies..." -ForegroundColor Yellow
Push-Location "$PSScriptRoot\client"
pip install -r requirements.txt -q
Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Run the following to start:" -ForegroundColor White
Write-Host "  .\start_server.ps1  - Start server" -ForegroundColor Yellow
Write-Host "  .\start_client.ps1  - Start client" -ForegroundColor Yellow
Write-Host ""

Read-Host "Press Enter to exit"
