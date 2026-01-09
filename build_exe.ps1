param(
  [string]$Python = "$PSScriptRoot\..\.venv\Scripts\python.exe"
)

$ErrorActionPreference = 'Stop'

$root = Resolve-Path "$PSScriptRoot"
Set-Location $root

# Build a single, self-contained Windows executable
& $Python -m pip install --upgrade pip | Out-Null
& $Python -m pip install pyinstaller | Out-Null

$dist = Join-Path $root 'dist'
$build = Join-Path $root 'build'
if (Test-Path $dist) { Remove-Item -Recurse -Force $dist }
if (Test-Path $build) { Remove-Item -Recurse -Force $build }

& $Python -m PyInstaller `
  --clean `
  --noconsole `
  --onefile `
  --name "HD_Supply_LOCPRIORITY_Builder" `
  "$root\run_app.py"

Write-Host "Built: $root\dist\HD_Supply_LOCPRIORITY_Builder.exe"
