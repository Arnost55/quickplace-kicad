param([string]$PluginDirectory = [System.IO.Path]::Combine([Environment]::GetFolderPath('MyDocuments'), 'KiCad', '10.0', 'scripting', 'plugins'))
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'quickplace'
if (-not (Test-Path (Join-Path $source '__init__.py'))) { throw 'Run this script from the extracted QuickPlace repository.' }
$destination = Join-Path $PluginDirectory 'quickplace'
if (Test-Path $destination) { throw "Existing installation at $destination. Remove it from the Plugin Directory before reinstalling." }
New-Item -ItemType Directory -Force -Path $PluginDirectory | Out-Null
Copy-Item -Path $source -Destination $destination -Recurse
Write-Host "Installed QuickPlace at $destination. Open a PCB, then use Tools > External Plugins > Refresh Plugins (or the equivalent Plugins menu in your KiCad build). Look for QuickPlace Now; it places footprints and is not an autorouter."
