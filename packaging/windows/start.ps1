$ErrorActionPreference = 'Stop'
$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = (Resolve-Path -LiteralPath (Join-Path $installRoot 'CodexPetQuota.exe')).Path
$running = @(
    Get-CimInstance Win32_Process -Filter "Name='CodexPetQuota.exe'" |
        Where-Object { [string]::Equals($_.ExecutablePath, $exePath, [System.StringComparison]::OrdinalIgnoreCase) }
)
$supervisor = @($running | Where-Object { $_.CommandLine -like '*--supervisor*' })
if ($supervisor.Count -eq 0) {
    foreach ($process in $running) { Stop-Process -Id $process.ProcessId -Force }
    Start-Process -FilePath $exePath -ArgumentList @('--supervisor') -WorkingDirectory $installRoot -WindowStyle Hidden
    Write-Output 'Codex Pet Quota started.'
} else {
    Write-Output 'Codex Pet Quota is already running.'
}
