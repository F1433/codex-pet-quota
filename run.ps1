param(
    [switch]$Once,
    [switch]$DiagnoseWindows
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction Stop

if ($Once -or $DiagnoseWindows) {
    $arguments = @('-m', 'codex_pet_quota')
    if ($Once) { $arguments += '--once' }
    if ($DiagnoseWindows) { $arguments += '--diagnose-windows' }
    Push-Location $projectRoot
    try {
        & $python.Source @arguments
        exit $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

$pythonw = Join-Path (Split-Path -Parent $python.Source) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw "pythonw.exe not found: $pythonw" }
Start-Process -FilePath $pythonw -ArgumentList @('-m', 'codex_pet_quota', '--background') -WorkingDirectory $projectRoot -WindowStyle Hidden
Write-Output 'Codex pet quota background watcher started.'
