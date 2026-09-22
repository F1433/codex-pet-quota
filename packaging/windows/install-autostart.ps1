$ErrorActionPreference = 'Stop'
$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = (Resolve-Path -LiteralPath (Join-Path $installRoot 'CodexPetQuota.exe')).Path
$taskName = 'CodexPetQuotaSupervisor'

# Stop the previous source-based watcher during migration.
$legacy = @(
    Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -like '*codex_pet_quota*' }
)
foreach ($process in $legacy) { Stop-Process -Id $process.ProcessId -Force }

# Replace the legacy Startup-folder shortcut with a scheduled task. Tasks are
# launched by Windows, so the supervisor is not killed with the Codex job.
$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'CodexPetQuota.lnk'
if (Test-Path -LiteralPath $shortcutPath) { Remove-Item -LiteralPath $shortcutPath -Force }

$running = @(
    Get-CimInstance Win32_Process -Filter "Name='CodexPetQuota.exe'" |
        Where-Object { [string]::Equals($_.ExecutablePath, $exePath, [System.StringComparison]::OrdinalIgnoreCase) }
)
foreach ($process in $running) { Stop-Process -Id $process.ProcessId -Force }

$userId = "$env:USERDOMAIN\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute $exePath -Argument '--supervisor' -WorkingDirectory $installRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 99 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Output "Scheduled task installed and started: $taskName"
