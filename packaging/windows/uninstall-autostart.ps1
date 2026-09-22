$ErrorActionPreference = 'Stop'
$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = 'CodexPetQuotaSupervisor'
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'CodexPetQuota.lnk'
& (Join-Path $installRoot 'stop.ps1')
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
if (Test-Path -LiteralPath $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath -Force
}
Write-Output 'Scheduled task and legacy startup shortcut removed. Program files and local quota cache were kept.'
