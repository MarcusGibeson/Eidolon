$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$SmokeCheck = Join-Path $ProjectRoot "tools\smoke_check.py"

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "Creating virtual environment..."
    py -m venv (Join-Path $ProjectRoot ".venv")
}

Write-Host "Installing requirements..."
& $Python -m pip install -r $Requirements

Write-Host ""
Write-Host "Running smoke check..."
& $Python $SmokeCheck

Write-Host ""
Write-Host "Useful commands:"
Write-Host "  .\.venv\Scripts\python.exe conscious_agent\main.py --status"
Write-Host "  .\.venv\Scripts\python.exe conscious_agent\main.py --onboarding"
Write-Host "  .\.venv\Scripts\python.exe conscious_agent\main.py --dashboard"
