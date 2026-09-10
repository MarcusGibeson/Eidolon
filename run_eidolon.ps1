$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) { $Python = "py" }
$Forward = @($args)
if ($Forward.Count -eq 0) { $Forward = @("start") }
& $Python (Join-Path $Root "eidolon.py") @Forward
exit $LASTEXITCODE
