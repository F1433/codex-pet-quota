$ErrorActionPreference = 'Stop'
$taskName = 'CodexPetQuotaSupervisor'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $projectRoot 'stop-background.ps1')
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'CodexPetQuota.lnk'
if (Test-Path -LiteralPath $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath -Force
}
Write-Output "Scheduled task and legacy shortcut removed: $taskName"
