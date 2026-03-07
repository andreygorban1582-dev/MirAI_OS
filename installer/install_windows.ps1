# ============================================================
#  MirAI OS — Full Windows Installation Script
#  Run as Administrator in PowerShell:
#    Set-ExecutionPolicy Bypass -Scope Process -Force
#    .\installer\install_windows.ps1
#
#  Handles:
#    1. WSL2 enablement
#    2. Kali Linux install
#    3. .wslconfig optimization for Legion Go
#    4. MirAI OS clone + setup inside WSL2
#    5. Desktop shortcut creation
#  El Psy Kongroo.
# ============================================================

param(
    [string]$MiraiRepo  = "https://github.com/YOUR_USERNAME/MirAI_OS.git",
    [string]$WslDistro  = "kali-linux",
    [string]$MiraiDir   = "~/MirAI_OS",
    [switch]$SkipWsl    = $false,
    [switch]$SkipClone  = $false
)

$ErrorActionPreference = "Stop"

function Write-Lab   { Write-Host "[FUTURE GADGET LAB] $args" -ForegroundColor Cyan }
function Write-Ok    { Write-Host "[✓] $args"                  -ForegroundColor Green }
function Write-Warn  { Write-Host "[!] $args"                  -ForegroundColor Yellow }
function Write-Fail  { Write-Host "[✗] $args"                  -ForegroundColor Red }
function Write-Step  { Write-Host "`n── $args ──" -ForegroundColor Magenta }

Write-Host @"

 ███╗   ███╗██╗██████╗  █████╗ ██╗      ██████╗ ███████╗
 ████╗ ████║██║██╔══██╗██╔══██╗██║     ██╔═══██╗██╔════╝
 ██╔████╔██║██║██████╔╝███████║██║     ██║   ██║███████╗
 ██║╚██╔╝██║██║██╔══██╗██╔══██║██║     ██║   ██║╚════██║
 ██║ ╚═╝ ██║██║██║  ██║██║  ██║███████╗╚██████╔╝███████║
 ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝
      MirAI OS Installer v0.1.0  |  El Psy Kongroo.

"@ -ForegroundColor Cyan

# ── Admin check ───────────────────────────────────────────────────────────────
Write-Step "ADMINISTRATOR CHECK"
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Fail "Must run as Administrator! Right-click PowerShell → Run as Administrator"
    exit 1
}
Write-Ok "Running as Administrator."

# ── Windows version ───────────────────────────────────────────────────────────
Write-Step "WINDOWS VERSION CHECK"
$build = [System.Environment]::OSVersion.Version.Build
if ($build -lt 19041) {
    Write-Fail "WSL2 requires Windows 10 build 19041 or later (you have $build)"
    Write-Fail "Please update Windows and retry."
    exit 1
}
Write-Ok "Windows build $build — WSL2 supported."

# ── WSL2 ─────────────────────────────────────────────────────────────────────
if (-not $SkipWsl) {
    Write-Step "WSL2 SETUP"

    # Enable WSL feature
    $wslEnabled = (Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux).State -eq "Enabled"
    $vmpEnabled = (Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform).State -eq "Enabled"

    if (-not $wslEnabled) {
        Write-Lab "Enabling Windows Subsystem for Linux..."
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart | Out-Null
        Write-Ok "WSL feature enabled."
    } else { Write-Ok "WSL already enabled." }

    if (-not $vmpEnabled) {
        Write-Lab "Enabling Virtual Machine Platform..."
        Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart | Out-Null
        Write-Ok "VMP enabled."
    } else { Write-Ok "VMP already enabled." }

    # Set WSL2 as default
    try {
        wsl --set-default-version 2 | Out-Null
        Write-Ok "WSL2 set as default."
    } catch { Write-Warn "Could not set WSL2 default — may need reboot first." }

    # Check if Kali is installed
    $distros = (wsl --list --quiet 2>$null) -join " "
    if ($distros -notlike "*$WslDistro*") {
        Write-Lab "Installing $WslDistro... (this will open a window, set root password)"
        wsl --install -d $WslDistro
        Write-Ok "$WslDistro installed."
    } else {
        Write-Ok "$WslDistro already installed."
    }
}

# ── .wslconfig for Legion Go Z1 Extreme ──────────────────────────────────────
Write-Step "WSL2 CONFIGURATION (LEGION GO OPTIMIZATION)"
$wslconfig = @"
[wsl2]
# MirAI OS — Legion Go Z1 Extreme
memory=14GB
processors=8
localhostForwarding=true
pageReportingEnabled=true
swap=0
nestedVirtualization=true
dnsTunneling=true
firewall=true
"@
$wslconfigPath = "$env:USERPROFILE\.wslconfig"
Set-Content -Path $wslconfigPath -Value $wslconfig
Write-Ok ".wslconfig written: 14GB RAM, 8 cores for Kali."

# ── Clone MirAI OS into WSL ───────────────────────────────────────────────────
if (-not $SkipClone) {
    Write-Step "CLONING MIRAI OS INTO WSL"
    $checkExist = wsl -d $WslDistro -- bash -c "test -d $MiraiDir && echo yes || echo no"
    if ($checkExist -eq "yes") {
        Write-Warn "MirAI OS already exists. Pulling latest..."
        wsl -d $WslDistro -- bash -c "cd $MiraiDir && git pull"
    } else {
        Write-Lab "Cloning MirAI OS repository..."
        wsl -d $WslDistro -- bash -c "git clone $MiraiRepo $MiraiDir"
    }
    Write-Ok "Repository ready at $MiraiDir"
}

# ── Run WSL setup script ──────────────────────────────────────────────────────
Write-Step "WSL ENVIRONMENT SETUP"
Write-Lab "Running setup_wsl.sh inside $WslDistro (takes a few minutes)..."
wsl -d $WslDistro -- bash -c "cd $MiraiDir && bash scripts/setup_wsl.sh"
Write-Ok "WSL environment configured."

# ── Setup swap ────────────────────────────────────────────────────────────────
Write-Step "128GB SWAP SETUP"
$doSwap = Read-Host "Setup 128GB swap file? Needs ~128GB free disk space. [Y/n]"
if ($doSwap -ne "n" -and $doSwap -ne "N") {
    Write-Lab "Creating 128GB swap (this takes several minutes)..."
    wsl -d $WslDistro -- bash -c "sudo bash $MiraiDir/scripts/setup_swap.sh 128"
    Write-Ok "128GB swap active."
} else {
    Write-Warn "Swap skipped. You can run it later: sudo bash $MiraiDir/scripts/setup_swap.sh 128"
}

# ── .env setup ───────────────────────────────────────────────────────────────
Write-Step "API KEYS CONFIGURATION"
$envPath = "\\wsl$\$WslDistro\root\MirAI_OS\.env"
if (-not (Test-Path $envPath)) {
    wsl -d $WslDistro -- bash -c "cp $MiraiDir/config/.env.example $MiraiDir/.env"
}
Write-Warn "You must edit .env to add your API keys!"
$openEnv = Read-Host "Open .env in Notepad now? [Y/n]"
if ($openEnv -ne "n" -and $openEnv -ne "N") {
    notepad.exe $envPath
}

# ── Desktop shortcut ──────────────────────────────────────────────────────────
Write-Step "DESKTOP SHORTCUT"
$launcherPath = "$PSScriptRoot\..\MirAI_OS.exe"
if (Test-Path $launcherPath) {
    $WshShell = New-Object -ComObject WScript.Shell
    $shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\MirAI OS.lnk")
    $shortcut.TargetPath = (Resolve-Path $launcherPath).Path
    $shortcut.Description = "MirAI OS — Future Gadget Lab"
    $shortcut.Save()
    Write-Ok "Desktop shortcut created."
} else {
    Write-Warn "MirAI_OS.exe not found. Build it with: python installer/build_exe.py"
    # Create a shortcut to the PowerShell start script instead
    $WshShell = New-Object -ComObject WScript.Shell
    $shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\MirAI OS.lnk")
    $shortcut.TargetPath = "wsl.exe"
    $shortcut.Arguments = "-d $WslDistro -- bash -c `"cd $MiraiDir && source venv/bin/activate && screen -S mirai python main.py`""
    $shortcut.Description = "MirAI OS — Start"
    $shortcut.Save()
    Write-Ok "Desktop shortcut (WSL direct) created."
}

# ── Startup task ─────────────────────────────────────────────────────────────
Write-Step "WINDOWS STARTUP (OPTIONAL)"
$doStartup = Read-Host "Add MirAI OS to Windows startup (auto-start on boot)? [Y/n]"
if ($doStartup -ne "n" -and $doStartup -ne "N") {
    $startupScript = @"
wsl -d $WslDistro -- bash -c "cd $MiraiDir && source venv/bin/activate && sudo service redis-server start && screen -dmS mirai python main.py"
"@
    $startupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\MirAI_OS_start.bat"
    Set-Content -Path $startupPath -Value $startupScript
    Write-Ok "MirAI OS will auto-start with Windows."
}

# ── Done ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  MirAI OS Installation Complete!                  ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  ✓ WSL2 + Kali Linux configured                  ║" -ForegroundColor Cyan
Write-Host "║  ✓ MirAI OS cloned and set up                    ║" -ForegroundColor Cyan
Write-Host "║  ✓ Legion Go optimized (.wslconfig)              ║" -ForegroundColor Cyan
Write-Host "║                                                   ║" -ForegroundColor Cyan
Write-Host "║  Next: Edit .env with API keys then run MirAI!   ║" -ForegroundColor Cyan
Write-Host "║                                                   ║" -ForegroundColor Cyan
Write-Host "║  El Psy Kongroo.                                 ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Warn "NOTE: If this is first WSL2 install, REBOOT Windows now then run MirAI_OS.exe"
