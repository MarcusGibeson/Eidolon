$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Main = Join-Path $Root "conscious_agent\main.py"
$RuntimeData = if ($env:EIDOLON_DATA_DIR) { $env:EIDOLON_DATA_DIR } else { Join-Path $env:LOCALAPPDATA "Eidolon\data" }
$LogDirectory = Join-Path $RuntimeData "desktop"
$StdoutLog = Join-Path $LogDirectory "desktop-launcher.stdout.log"
$StderrLog = Join-Path $LogDirectory "desktop-launcher.stderr.log"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Eidolon's virtual-environment Python is missing: $Python"
}
if (-not (Test-Path -LiteralPath $Main -PathType Leaf)) {
    throw "Eidolon's desktop entry point is missing: $Main"
}

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
$Process = Start-Process `
    -FilePath $Python `
    -ArgumentList @($Main, "--desktop") `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -PassThru

Start-Sleep -Seconds 3
if ($Process.HasExited -and $Process.ExitCode -ne 0) {
    $ErrorTail = if (Test-Path -LiteralPath $StderrLog) {
        (Get-Content -LiteralPath $StderrLog -Tail 20) -join [Environment]::NewLine
    } else {
        "No error log was written."
    }
    throw "Eidolon Desktop exited during startup.`n$ErrorTail"
}
