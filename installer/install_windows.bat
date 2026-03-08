@echo off
REM =============================================================================
REM  MirAI_OS  –  Windows Installer for Lenovo Legion Go
REM  Installs WSL2 + Kali Linux, then runs the Kali installer inside WSL2.
REM =============================================================================
REM
REM  WHAT THIS SCRIPT DOES
REM  ─────────────────────
REM  1. Checks that Windows 11 / WSL2-capable Windows 10 is present
REM  2. Enables WSL2 and the Virtual Machine Platform Windows features
REM  3. Installs Kali Linux from the Microsoft Store (via winget)
REM  4. Sets WSL default version to 2
REM  5. Launches the Kali shell and runs the MirAI Linux installer inside it
REM  6. Creates a Desktop shortcut for quick access
REM
REM  REQUIREMENTS
REM  ────────────
REM  • Windows 11 or Windows 10 Build 19041+ (Legion Go ships with Win11)
REM  • Internet connection
REM  • Run as Administrator
REM
REM  USAGE
REM  ─────
REM  1. Right-click install_windows.bat → Run as administrator
REM     OR open an elevated Command Prompt and type:
REM       installer\install_windows.bat
REM
REM =============================================================================

setlocal EnableDelayedExpansion

REM ── Colour helpers (via PowerShell) ──────────────────────────────────────────
set "PS=powershell -NoProfile -Command"

REM ── Check Administrator ───────────────────────────────────────────────────────
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This installer must be run as Administrator.
    echo Right-click the file and choose "Run as administrator".
    pause
    exit /b 1
)

%PS% "Write-Host '  __  __ _       _    _    ___  ____' -ForegroundColor Cyan"
%PS% "Write-Host ' MirAI_OS  Windows Installer  [Legion Go Edition]' -ForegroundColor Cyan"
%PS% "Write-Host ''"

echo [INFO] Checking Windows version...
for /f "tokens=*" %%v in ('ver') do set WIN_VER=%%v
echo %WIN_VER%

REM ── Enable WSL2 ───────────────────────────────────────────────────────────────
echo.
echo [INFO] Enabling Windows Subsystem for Linux (WSL)...
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARN] WSL feature may already be enabled or requires a reboot.
)

echo [INFO] Enabling Virtual Machine Platform...
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart >nul 2>&1

REM ── Set WSL default version to 2 ─────────────────────────────────────────────
echo [INFO] Setting WSL default version to 2...
wsl --set-default-version 2 >nul 2>&1

REM ── Install Kali Linux via winget ─────────────────────────────────────────────
echo.
echo [INFO] Installing Kali Linux from Microsoft Store (via winget)...
where winget >nul 2>&1
if %errorLevel% equ 0 (
    winget install --id KaliLinux.KaliLinux -e --accept-source-agreements --accept-package-agreements
) else (
    echo [WARN] winget not found. Opening Microsoft Store page for Kali Linux...
    start ms-windows-store://pdp/?ProductId=9PKR34TNCV07
    echo Please install Kali Linux from the Store, then re-run this installer.
    pause
    exit /b 1
)

REM ── Update WSL kernel ─────────────────────────────────────────────────────────
echo.
echo [INFO] Updating WSL2 kernel...
wsl --update >nul 2>&1

REM ── First-time Kali initialisation ────────────────────────────────────────────
echo.
echo [INFO] Performing first-time Kali Linux setup...
echo       This may take a few minutes – a Kali window will open.
wsl -d kali-linux -- bash -c "apt-get update -qq && apt-get install -y -qq curl" 2>nul

REM ── Run the MirAI Linux installer inside WSL2 Kali ───────────────────────────
echo.
echo [INFO] Running MirAI_OS installer inside Kali Linux (WSL2)...
REM SECURITY NOTE: Piping curl directly to bash is convenient but requires
REM trust in the source URL. To verify before executing, run these two steps
REM manually inside Kali:
REM   curl -fsSL https://raw.githubusercontent.com/andreygorban1582-dev/MirAI_OS/main/scripts/install_wsl.sh -o /tmp/mirai_install.sh
REM   bash /tmp/mirai_install.sh
wsl -d kali-linux -- bash -c "curl -fsSL https://raw.githubusercontent.com/andreygorban1582-dev/MirAI_OS/main/scripts/install_wsl.sh -o /tmp/mirai_install.sh && bash /tmp/mirai_install.sh"

if %errorLevel% neq 0 (
    echo.
    echo [ERROR] The MirAI installer encountered an error inside WSL2.
    echo         Open Kali Linux and check the output above.
    pause
    exit /b 1
)

REM ── Create Desktop shortcut ───────────────────────────────────────────────────
echo.
echo [INFO] Creating Desktop shortcut...
set SHORTCUT=%USERPROFILE%\Desktop\MirAI.lnk
%PS% "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%'); $s.TargetPath='wsl.exe'; $s.Arguments='-d kali-linux -- bash -c \"source ~/MirAI_OS/.venv/bin/activate && python ~/MirAI_OS/main.py\"'; $s.Description='Launch MirAI AI Agent'; $s.Save()"
echo [OK] Shortcut created: %SHORTCUT%

REM ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ================================================================
echo   MirAI_OS installed successfully!  El Psy Congroo.
echo ================================================================
echo.
echo   To start MirAI:
echo     Option 1: Double-click the MirAI shortcut on your Desktop
echo     Option 2: Open Kali Linux and run:  mirai
echo     Option 3: Telegram bot:             mirai telegram
echo.
echo   Don't forget to edit ~/MirAI_OS/.env and add your API keys!
echo.
pause
