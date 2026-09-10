param(
    [switch]$CoreOnly,
    [switch]$ApplyUpgradeMigration
)

$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUNBUFFERED = "1"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PythonCompatibilityCheck = "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 15) else 1)"

function Assert-NativeSuccess {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE. Setup stopped before reporting Ready."
    }
}

function Find-CompatiblePython {
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        foreach ($Version in @("3.11", "3.12", "3.13", "3.14")) {
            & $PyLauncher.Source "-$Version" -c $PythonCompatibilityCheck *> $null
            if ($LASTEXITCODE -eq 0) {
                return [pscustomobject]@{
                    Command = $PyLauncher.Source
                    Arguments = @("-$Version")
                    Version = $Version
                }
            }
        }
    }

    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) {
        & $PythonCommand.Source -c $PythonCompatibilityCheck *> $null
        if ($LASTEXITCODE -eq 0) {
            $DetectedVersion = & $PythonCommand.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
            return [pscustomobject]@{
                Command = $PythonCommand.Source
                Arguments = @()
                Version = $DetectedVersion.Trim()
            }
        }
    }

    throw "Eidolon v1080.0 requires Python 3.11, 3.12, 3.13, or 3.14."
}

if (-not (Test-Path -LiteralPath $Python)) {
    $Launcher = Find-CompatiblePython
    $LauncherCommand = $Launcher.Command
    $LauncherArguments = @($Launcher.Arguments)
    Write-Host "Creating virtual environment with Python $($Launcher.Version)..."
    & $LauncherCommand @LauncherArguments -m venv (Join-Path $ProjectRoot ".venv")
    Assert-NativeSuccess "Virtual environment creation"
}

& $Python -c $PythonCompatibilityCheck *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Existing .venv uses unsupported Python. Eidolon v1080.0 requires Python 3.11, 3.12, 3.13, or 3.14."
}

& $Python -m pip install --upgrade pip
Assert-NativeSuccess "pip upgrade"

$Requirements = if ($CoreOnly) { "requirements-core.txt" } else { "requirements.txt" }
Write-Host "Installing $Requirements..."
& $Python -m pip install -r (Join-Path $ProjectRoot $Requirements)
Assert-NativeSuccess "Dependency installation"

Write-Host ""
if ($ApplyUpgradeMigration) {
    Write-Host "Explicit migration opt-in supplied. Applying reversible retired-evidence quarantine..."
    & $Python (Join-Path $ProjectRoot "tools\upgrade_migrate.py") --apply
    Assert-NativeSuccess "Upgrade evidence migration"
} else {
    Write-Host "Inspecting retired sandbox evidence without changing it..."
    & $Python (Join-Path $ProjectRoot "tools\upgrade_migrate.py")
    Assert-NativeSuccess "Upgrade evidence inspection"
    Write-Host "Migration was NOT applied. Review the inspection above."
    Write-Host "To opt in, rerun setup with -ApplyUpgradeMigration or run:"
    Write-Host "  .\.venv\Scripts\python.exe eidolon.py upgrade-migrate --apply"
}

Write-Host ""
Write-Host "Running authoritative quick release verification..."
& $Python (Join-Path $ProjectRoot "tools\release_verify.py") --profile quick
Assert-NativeSuccess "Quick release verification"

Write-Host ""
Write-Host "Ready. Useful commands:"
Write-Host "  .\run_eidolon.ps1                 # opens the conversation-first dashboard"
Write-Host "  .\.venv\Scripts\python.exe eidolon.py status"
Write-Host "  .\.venv\Scripts\python.exe eidolon.py chat"
Write-Host "  .\.venv\Scripts\python.exe eidolon.py dashboard --open-browser"
Write-Host "  .\.venv\Scripts\python.exe eidolon.py runtime-guide"
Write-Host "  .\.venv\Scripts\python.exe eidolon.py startup-soak --runs 5 --json"
Write-Host "  .\.venv\Scripts\python.exe eidolon.py verify --full"
