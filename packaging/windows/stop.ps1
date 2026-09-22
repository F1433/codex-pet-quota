$ErrorActionPreference = 'Stop'
$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = (Resolve-Path -LiteralPath (Join-Path $installRoot 'CodexPetQuota.exe')).Path
$running = @(
    Get-CimInstance Win32_Process -Filter "Name='CodexPetQuota.exe'" |
        Where-Object { [string]::Equals($_.ExecutablePath, $exePath, [System.StringComparison]::OrdinalIgnoreCase) }
)
foreach ($process in $running) { Stop-Process -Id $process.ProcessId -Force }
Write-Output ("Stopped process count: " + $running.Count)
