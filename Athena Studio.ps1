$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = "1"
Write-Host "Athena Studio Alpha"
Write-Host "==================="
Write-Host "Project root: $PWD"
if (Get-Command python -ErrorAction SilentlyContinue) {
    python -B Tools\athena_studio.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -B Tools\athena_studio.py
} else {
    Write-Host "Python was not found. Launch Athena Studio from Anaconda Prompt or install Python."
    Read-Host "Press Enter to exit"
}
