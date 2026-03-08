#Requires -RunAsAdministrator
<#
.SYNOPSIS
    MirAI_OS PowerShell Installer for Windows / WSL2 / Kali Linux
.DESCRIPTION
    Installs and configures the full MirAI_OS container stack on a Legion Go
    (or any Windows 11 machine) running Kali Linux in WSL2.
#>

param(
    [switch]$SkipDocker,
    [switch]$SkipWSL,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "MirAI_OS Installer"

function Write-Header([string]$msg) {
    Write-Host "`n  $msg" -ForegroundColor Cyan
}

function Write-OK([string]$msg) {
    Write-Host "  [+] $msg" -ForegroundColor Green
}

function Write-Warn([string]$msg) {
    Write-Host "  [!] $msg" -ForegroundColor Yellow
}

function Write-Step([string]$msg) {
    Write-Host "  [*] $msg" -ForegroundColor White
}

Write-Host @"

  ╔═══════════════════════════════════════════════════════════════════╗
  ║          MirAI_OS  –  PowerShell Installer                       ║
  ╚═══════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Magenta

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ─── Step 1: WSL2 ────────────────────────────────────────────────────────────
if (-not $SkipWSL) {
    Write-Header "Step 1: WSL2 Setup"
    try {
        $wslVersion = wsl --version 2>&1
        Write-OK "WSL2 found"
    } catch {
        Write-Step "Enabling WSL2..."
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All -NoRestart
        Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
        wsl --set-default-version 2
        Write-Warn "Please restart your PC then re-run this installer."
        exit 0
    }

    # Install Kali if missing
    $distros = wsl -l -v 2>&1
    if ($distros -notmatch "kali") {
        Write-Step "Installing Kali Linux WSL distro..."
        wsl --install -d kali-linux
        Write-Warn "Complete Kali setup, then re-run this installer."
        exit 0
    }
    Write-OK "Kali Linux WSL distro found"
}

# ─── Step 2: Docker Desktop ───────────────────────────────────────────────────
if (-not $SkipDocker) {
    Write-Header "Step 2: Docker Desktop"
    try {
        $dv = docker --version 2>&1
        Write-OK "Docker found: $dv"
    } catch {
        Write-Step "Downloading Docker Desktop..."
        $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
        $dockerPath = "$env:TEMP\DockerDesktopInstaller.exe"
        Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerPath -UseBasicParsing
        Write-Step "Installing Docker Desktop..."
        Start-Process -FilePath $dockerPath -ArgumentList "install", "--quiet" -Wait
        Write-Warn "Restart your PC and re-run this installer after Docker starts."
        exit 0
    }
}

# ─── Step 3: .wslconfig ───────────────────────────────────────────────────────
Write-Header "Step 3: WSL2 Memory / Swap Configuration"
$wslCfgPath = "$env:USERPROFILE\.wslconfig"
$templatePath = Join-Path $ScriptDir "wslconfig.template"

if (-not (Test-Path $wslCfgPath)) {
    if (Test-Path $templatePath) {
        Copy-Item $templatePath $wslCfgPath
        Write-OK ".wslconfig written to $wslCfgPath"
        Write-Warn "WSL2 will be restarted to apply memory settings."
        wsl --shutdown 2>$null
    } else {
        Write-Warn "wslconfig.template not found – skipping .wslconfig"
    }
} else {
    Write-OK ".wslconfig already exists"
}

# ─── Step 4: D-Drive directories ─────────────────────────────────────────────
Write-Header "Step 4: D-Drive Storage"
if (Test-Path "D:\") {
    New-Item -ItemType Directory -Force -Path "D:\mirai_storage" | Out-Null
    New-Item -ItemType Directory -Force -Path "D:\mirai_swap"    | Out-Null
    Write-OK "D:\mirai_storage and D:\mirai_swap created"
} else {
    Write-Warn "D: drive not found – using Docker named volumes instead"
}

# ─── Step 5: .env ────────────────────────────────────────────────────────────
Write-Header "Step 5: Environment Config"
$envFile     = Join-Path $ScriptDir ".env"
$envTemplate = Join-Path $ScriptDir ".env.example"
if (-not (Test-Path $envFile)) {
    Copy-Item $envTemplate $envFile
    Write-OK ".env created"
    Write-Warn "Edit $envFile and set your API keys!"
} else {
    Write-OK ".env already exists"
}

# ─── Step 6: Launch in WSL2 ───────────────────────────────────────────────────
if (-not $NoLaunch) {
    Write-Header "Step 6: Starting MirAI_OS in Kali WSL2"
    # Convert Windows path to WSL path
    $wslPath = wsl wslpath -u $ScriptDir.Replace("\", "\\")
    wsl -d kali-linux -- bash -c "cd '$wslPath' && chmod +x install.sh && ./install.sh"
}

Write-Host @"

  ╔═══════════════════════════════════════════════════════════════════╗
  ║  MirAI_OS installation complete!                                 ║
  ║                                                                   ║
  ║  Web UI:   https://localhost                                      ║
  ║  API:      http://localhost:8080                                  ║
  ║                                                                   ║
  ║  Run start.bat or start.ps1 to start after a reboot.            ║
  ╚═══════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Magenta
