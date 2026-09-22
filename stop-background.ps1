$ErrorActionPreference = 'Stop'
$watchers = @(
    Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -like '*codex_pet_quota*' }
)
foreach ($watcher in $watchers) {
    Stop-Process -Id $watcher.ProcessId -Force
}
Write-Output ("Stopped supervisor/watcher count: " + $watchers.Count)
