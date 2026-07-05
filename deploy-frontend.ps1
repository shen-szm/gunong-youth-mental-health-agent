$ErrorActionPreference = "Stop"

$Server = "ubuntu@<OLD_SERVER_IP>"
$RemoteDist = "/opt/shengyu/frontend/dist"
$FrontendDir = Join-Path $PSScriptRoot "frontend"

if (-not (Test-Path -LiteralPath $FrontendDir)) {
  throw "Frontend directory not found: $FrontendDir"
}

Push-Location $FrontendDir
try {
  $env:VITE_APP_VERSION = (git -C $PSScriptRoot rev-parse --short HEAD).Trim()
  $env:VITE_BUILD_TIME = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

  npm.cmd install
  npm.cmd run build

  ssh $Server "sudo mkdir -p $RemoteDist && sudo chown -R ubuntu:ubuntu /opt/shengyu && rm -rf $RemoteDist/*"
  scp -r ".\dist\*" "${Server}:$RemoteDist/"
  ssh $Server "sudo nginx -t && sudo systemctl reload nginx"

  Write-Host "Frontend deployed to ${Server}:$RemoteDist"
  Write-Host "Version: $env:VITE_APP_VERSION"
  Write-Host "Build time: $env:VITE_BUILD_TIME"
}
finally {
  Pop-Location
}