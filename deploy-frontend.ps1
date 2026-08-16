$ErrorActionPreference = "Stop"

$Server = "$env:DEPLOY_SERVER"
$RemoteDist = "/opt/shengyu/frontend/dist"
$FrontendDir = Join-Path $PSScriptRoot "frontend"
$ReleaseStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RemoteNext = "/opt/shengyu/frontend/dist-next-$ReleaseStamp"
$RemoteBackup = "/opt/shengyu/backups/frontend-dist-$ReleaseStamp"

if (-not (Test-Path -LiteralPath $FrontendDir)) {
  throw "Frontend directory not found: $FrontendDir"
}

Push-Location $FrontendDir
try {
  $pkg = Get-Content -Raw (Join-Path $FrontendDir "package.json") | ConvertFrom-Json
  $pkgVersion = $pkg.version
  $gitSha = (git -C $PSScriptRoot rev-parse --short HEAD).Trim()
  $env:VITE_APP_VERSION = "$pkgVersion+$gitSha"
  $env:VITE_BUILD_TIME = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

  npm.cmd install
  npm.cmd run build

  ssh $Server "mkdir -p '$RemoteNext'"
  scp -r ".\dist\*" "${Server}:$RemoteNext/"
  ssh $Server "test -f '$RemoteNext/index.html' && sudo mkdir -p /opt/shengyu/backups && if [ -d '$RemoteDist' ]; then sudo mv '$RemoteDist' '$RemoteBackup'; fi && sudo mv '$RemoteNext' '$RemoteDist' && sudo nginx -t && sudo systemctl reload nginx"

  Write-Host "Frontend deployed to ${Server}:$RemoteDist"
  Write-Host "Previous frontend backup: $RemoteBackup"
  Write-Host "Version: $env:VITE_APP_VERSION"
  Write-Host "Build time: $env:VITE_BUILD_TIME"
}
finally {
  Pop-Location
}
