<#
.SYNOPSIS
  Install tactile — a terminal-based touch-typing trainer.
.DESCRIPTION
  Installs tactile via uv tool install from GitHub. If uv is not present,
  installs uv first via the official installer.
#>
$ErrorActionPreference = "Stop"

Write-Host "Installing tactile..." -ForegroundColor Cyan

# Check if uv is installed
$uvInstalled = $false
try { $null = Get-Command uv -ErrorAction Stop; $uvInstalled = $true } catch {}

if (-not $uvInstalled) {
    Write-Host "uv not found. Installing uv..." -ForegroundColor Yellow
    & ([scriptblock]::Create((irm https://astral.sh/uv/install.ps1))) $args
    # Refresh PATH for current session
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

# Install tactile
Write-Host "Installing tactile from GitHub..." -ForegroundColor Yellow
uv tool install git+https://github.com/Zurybr/tactile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "tactile installed successfully!" -ForegroundColor Green
    Write-Host "Run 'tactile' to start practicing." -ForegroundColor Green
    Write-Host "Run 'tactile update' to update to the latest version." -ForegroundColor Green
} else {
    Write-Host "Installation failed. Please check the output above." -ForegroundColor Red
    exit 1
}
