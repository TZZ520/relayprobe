param(
  [switch]$RunDetectedLive,
  [switch]$NoRunDetectedLive
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "src"
$Out = Join-Path $Root "artifacts\quickstart"
$Extra = @()
if ($NoRunDetectedLive) {
  $Extra += "--no-run-detected-live"
}
Write-Host "relayprobe quickstart"
Write-Host "Project root: $Root"
Write-Host "Output: $Out"
python -m relayprobe quickstart --out $Out @Extra
