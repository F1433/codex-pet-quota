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
$shortcut.Arguments = '-m codex_pet_quota --background'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.WindowStyle = 7
$shortcut.Description = 'Wait for Codex pet interaction, then read weekly quota.'
$shortcut.Save()
Write-Output "Startup shortcut installed: $shortcutPath"
