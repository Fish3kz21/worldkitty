# WORLDKITTY Infinite Charge — Windows install (no admin)
# Right-click → Run with PowerShell, or:  irm <this-url> | iex
$ErrorActionPreference = 'Stop'
$url = 'https://worldkitty.vercel.app'
$dir = Join-Path $env:LOCALAPPDATA 'WorldKitty'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$shortcut = @"
[InternetShortcut]
URL=$url
IconIndex=0
"@
Set-Content -Path (Join-Path $dir 'WORLDKITTY.url') -Value $shortcut -Encoding ASCII
$desk = [Environment]::GetFolderPath('Desktop')
if ($desk) {
  Set-Content -Path (Join-Path $desk 'WORLDKITTY.url') -Value $shortcut -Encoding ASCII
}
Start-Process $url
Write-Host "WORLDKITTY installed. Desktop shortcut created. Loop is live." -ForegroundColor Cyan
