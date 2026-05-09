# Deploy the C# port to NinjaTrader 8.
#
# Copies csharp/AddOns/**/*.cs to %USERPROFILE%\Documents\NinjaTrader 8\bin\Custom\AddOns\AlgoTrading\
# and csharp/Strategies/*.cs to %USERPROFILE%\Documents\NinjaTrader 8\bin\Custom\Strategies\
#
# After running, open NT8 and press F5 (or Tools -> Compile NinjaScript).
# Compile errors appear in the Tools -> Output window.

[CmdletBinding()]
param(
    [string]$NtUserDir = "$env:USERPROFILE\Documents\NinjaTrader 8",
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$srcAddOns = Join-Path $repoRoot 'csharp\AddOns'
$srcStrategies = Join-Path $repoRoot 'csharp\Strategies'

if (-not (Test-Path $srcAddOns)) {
    Write-Error "AddOns source not found at $srcAddOns. Run from the AlgoTrading repo on the csharp-port branch."
}

if (-not (Test-Path $NtUserDir)) {
    Write-Warning "NT8 user dir not found at $NtUserDir."
    Write-Warning "Launch NinjaTrader 8 once so it creates this folder, then re-run."
    exit 1
}

$dstAddOns = Join-Path $NtUserDir 'bin\Custom\AddOns\AlgoTrading'
$dstStrategies = Join-Path $NtUserDir 'bin\Custom\Strategies'

Write-Host "Source AddOns:     $srcAddOns"
Write-Host "Source Strategies: $srcStrategies"
Write-Host "Dest   AddOns:     $dstAddOns"
Write-Host "Dest   Strategies: $dstStrategies"
Write-Host ''

if ($DryRun) {
    Write-Host '[dry-run] would copy files. Re-run without -DryRun to apply.'
    exit 0
}

# Mirror AddOns: clean dest first, copy fresh.
if (Test-Path $dstAddOns) { Remove-Item -LiteralPath $dstAddOns -Recurse -Force }
New-Item -ItemType Directory -Path $dstAddOns | Out-Null
Copy-Item -Path "$srcAddOns\*" -Destination $dstAddOns -Recurse -Force
Write-Host 'Copied AddOns.'

# Strategies: copy individual files (don't wipe other strategies the user has).
if (-not (Test-Path $dstStrategies)) { New-Item -ItemType Directory -Path $dstStrategies | Out-Null }
Get-ChildItem -Path $srcStrategies -Filter '*.cs' | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $dstStrategies -Force
    Write-Host "Copied Strategy: $($_.Name)"
}

Write-Host ''
Write-Host 'Done. Now in NinjaTrader 8: Tools -> Compile NinjaScript (F5).'
Write-Host 'Compile errors will appear in Tools -> Output -> NinjaScript.'
