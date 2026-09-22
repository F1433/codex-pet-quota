$ErrorActionPreference = 'Stop'
$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'CodexPetQuota.lnk'
if (Test-Path -LiteralPath $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath -Force
}
& (Join-Path $installRoot 'stop.ps1')
Write-Output 'Startup shortcut removed. Program files and local quota cache were kept.'
