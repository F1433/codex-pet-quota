param(
    [Parameter(Mandatory = $true)]
    [string]$Python,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$pythonPath = (Resolve-Path -LiteralPath $Python).Path
$workPath = Join-Path $projectRoot 'tmp\pyinstaller-work'
$specPath = Join-Path $projectRoot 'tmp\pyinstaller-spec'
$distPath = Join-Path $projectRoot 'tmp\pyinstaller-dist'
$launcher = Join-Path $PSScriptRoot 'launcher.py'

New-Item -ItemType Directory -Path $workPath, $specPath, $distPath, $OutputDirectory -Force | Out-Null

Push-Location $projectRoot
try {
    & $pythonPath -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name CodexPetQuota `
        --distpath $distPath `
        --workpath $workPath `
        --specpath $specPath `
        $launcher
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}

Copy-Item -LiteralPath (Join-Path $distPath 'CodexPetQuota.exe') -Destination $OutputDirectory -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'start.ps1') -Destination $OutputDirectory -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'stop.ps1') -Destination $OutputDirectory -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'install-autostart.ps1') -Destination $OutputDirectory -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'uninstall-autostart.ps1') -Destination $OutputDirectory -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.txt') -Destination $OutputDirectory -Force

Get-FileHash -LiteralPath (Join-Path $OutputDirectory 'CodexPetQuota.exe') -Algorithm SHA256
