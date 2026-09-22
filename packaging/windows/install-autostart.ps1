$ErrorActionPreference = 'Stop'
$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = (Resolve-Path -LiteralPath (Join-Path $installRoot 'CodexPetQuota.exe')).Path

# Stop the previous source-based watcher during migration.
$legacy = @(
    Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -like '*codex_pet_quota*' }
)
foreach ($process in $legacy) { Stop-Process -Id $process.ProcessId -Force }

$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'CodexPetQuota.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.Arguments = '--supervisor'
$shortcut.WorkingDirectory = $installRoot
$shortcut.WindowStyle = 7
$shortcut.Description = 'Start Codex Pet Quota with Windows and bind it to the Codex desktop lifecycle.'
$shortcut.Save()

& (Join-Path $installRoot 'start.ps1')
Write-Output "Startup shortcut installed: $shortcutPath"
