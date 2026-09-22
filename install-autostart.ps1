$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction Stop
$pythonw = Join-Path (Split-Path -Parent $python.Source) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw "pythonw.exe not found: $pythonw" }

$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'CodexPetQuota.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = '-m codex_pet_quota --supervisor'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.WindowStyle = 7
$shortcut.Description = 'Start and recover the quota watcher with the Codex desktop pet.'
$shortcut.Save()

$running = @(
    Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -like '*codex_pet_quota*' }
)
foreach ($process in $running) {
    Stop-Process -Id $process.ProcessId -Force
}
Start-Process -FilePath $pythonw -ArgumentList @('-m', 'codex_pet_quota', '--supervisor') -WorkingDirectory $projectRoot -WindowStyle Hidden
Write-Output "Startup shortcut installed: $shortcutPath"
Write-Output 'Codex-bound quota supervisor started.'
