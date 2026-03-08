#Requires -RunAsAdministrator
<#
.SYNOPSIS
    MirAI_OS PowerShell Installer for Windows

.DESCRIPTION
    Installs WSL2, Docker Desktop (if needed), then runs the Linux installer
    inside WSL2 to set up the full MirAI_OS Docker stack including Ollama LLM.

.PARAMETER Model
    Ollama model to pull (default: dolphin-mistral)

.PARAMETER SkipDocker
    Skip Docker Desktop installation check

.PARAMETER SkipWSL
    Skip WSL2 installation check

.PARAMETER NoLaunch
    Do not open the browser after installation

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1
    powershell -ExecutionPolicy Bypass -File install.ps1 -Model llama3:8b
#>

param(
    [string]$Model     = "dolphin-mistral",
    [switch]$SkipDocker,
    [switch]$SkipWSL,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"

function Write-Info    ($msg) { Write-Host "[INFO]  $msg" -ForegroundColor Cyan    }
function Write-Ok      ($msg) { Write-Host "[OK]    $msg" -ForegroundColor Green   }
function Write-Warn    ($msg) { Write-Host "[WARN]  $msg" -ForegroundColor Yellow  }
function Write-Err     ($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  =====================================================" -ForegroundColor Magenta
Write-Host "   MirAI_OS Installer" -ForegroundColor Magenta
Write-Host "  =====================================================" -ForegroundColor Magenta
Write-Host ""

# ── Step 1: WSL2 ──────────────────────────────────────────────
if (-not $SkipWSL) {
    Write-Info "Checking WSL2..."
    try {
        $wslStatus = wsl --status 2>&1
        Write-Ok "WSL2 is available."
    } catch {
        Write-Info "Enabling WSL2 features (reboot may be required)..."
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Null
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Null
        Write-Warn "WSL2 features enabled. Please REBOOT and re-run this installer."
        exit 0
    }

    wsl --set-default-version 2 | Out-Null

    $distros = wsl -l -v 2>$null
    if ($distros -notmatch "Ubuntu|Debian|Kali") {
        Write-Info "No WSL2 distro found. Installing Ubuntu..."
        wsl --install -d Ubuntu
        Write-Warn "Complete the Ubuntu first-run setup, then re-run this installer."
        exit 0
    }
    Write-Ok "WSL2 distro available."
}

# ── Step 2: Docker Desktop ────────────────────────────────────
if (-not $SkipDocker) {
    Write-Info "Checking Docker..."
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCmd) {
        Write-Info "Docker not found. Downloading Docker Desktop..."
        $installerPath = Join-Path $env:TEMP "DockerDesktopInstaller.exe"
        Invoke-WebRequest `
            -Uri "https://desktop.docker.com/win/main/amd64/Docker Desktop Installer.exe" `
            -OutFile $installerPath `
            -UseBasicParsing
        Write-Info "Running Docker Desktop installer (silent)..."
        Start-Process -FilePath $installerPath -ArgumentList "install --quiet --accept-license" -Wait
        Write-Ok "Docker Desktop installed."
        Write-Warn "Please start Docker Desktop, enable 'Use WSL 2 based engine', then re-run."
        exit 0
    } else {
        $v = & docker --version
        Write-Ok "Docker is available: $v"
    }
}

# ── Step 3: Convert Windows path to WSL path ──────────────────
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$driveLetter = $scriptDir.Substring(0,1).ToLower()
$wslPath    = "/mnt/$driveLetter" + ($scriptDir.Substring(2) -replace '\\','/')

Write-Info "Repository path (WSL): $wslPath"

# ── Step 4: Run Linux installer in WSL2 ──────────────────────
Write-Info "Launching MirAI_OS Linux installer inside WSL2..."
Write-Info "Model: $Model"

$wslCmd = "cd '$wslPath' && bash install.sh --model $Model"
wsl bash -c $wslCmd

if ($LASTEXITCODE -ne 0) {
    Write-Err "Installation failed (exit code $LASTEXITCODE). Review output above."
}

Write-Ok "MirAI_OS installation complete!"

# ── Step 5: Open browser ─────────────────────────────────────
if (-not $NoLaunch) {
    Write-Info "Opening MirAI_OS dashboard..."
    Start-Process "http://localhost:8080"
}

Write-Host ""
Write-Host "  Services available at:" -ForegroundColor Cyan
Write-Host "    Orchestrator API  →  http://localhost:8080" -ForegroundColor White
Write-Host "    Ollama LLM        →  http://localhost:11434" -ForegroundColor White
Write-Host "    N8n automation    →  http://localhost:5678" -ForegroundColor White
Write-Host "    Flowise builder   →  http://localhost:3001" -ForegroundColor White
Write-Host "    Nginx gateway     →  http://localhost:80" -ForegroundColor White
Write-Host ""
Write-Host "El Psy Kongroo." -ForegroundColor Magenta
