param([string]$PluginDirectory = [System.IO.Path]::Combine([Environment]::GetFolderPath('MyDocuments'), 'KiCad', '10.0', 'scripting', 'plugins'))
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'quickplace'
if (-not (Test-Path (Join-Path $source '__init__.py'))) { throw 'Run this script from the extracted QuickPlace repository.' }
$destination = Join-Path $PluginDirectory 'quickplace'
New-Item -ItemType Directory -Force -Path $PluginDirectory | Out-Null
if (Test-Path $destination) { throw "Existing installation at $destination. Move it aside manually before reinstalling." }
Copy-Item -Path $source -Destination $destination -Recurse
Write-Host "Installed QuickPlace at $destination. Restart KiCad PCB Editor and enable the plugin in Preferences > PCB Editor > Plugins."
