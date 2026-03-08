@echo off
:: ═══════════════════════════════════════════════════════════════════════════════
::  MirAI_OS  –  Windows Batch Installer
::  Installs Docker Desktop, WSL2/Kali, and launches the full stack
:: ═══════════════════════════════════════════════════════════════════════════════
title MirAI_OS Installer
color 0A

echo.
echo  ╔═══════════════════════════════════════════════════════════════════╗
echo  ║          MirAI_OS  –  Windows Installer                          ║
echo  ╚═══════════════════════════════════════════════════════════════════╝
echo.

:: ─── Require Admin ────────────────────────────────────────────────────────────
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Please run as Administrator.
    echo     Right-click install.bat ^> Run as administrator
    pause
    exit /b 1
)

:: ─── Check WSL2 ───────────────────────────────────────────────────────────────
echo [1/7] Checking WSL2...
wsl --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Enabling WSL2...
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    wsl --set-default-version 2
    echo [!] Please restart your computer and run this installer again.
    pause
    exit /b 0
)
echo [+] WSL2 OK

:: ─── Install Kali Linux if not present ───────────────────────────────────────
echo [2/7] Checking Kali Linux WSL distro...
wsl -l -v 2>nul | findstr /i "kali" >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Installing Kali Linux from Microsoft Store...
    wsl --install -d kali-linux
    echo [!] After Kali setup completes, re-run this installer.
    pause
    exit /b 0
)
echo [+] Kali Linux found

:: ─── Check / Install Docker Desktop ──────────────────────────────────────────
echo [3/7] Checking Docker Desktop...
docker --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Docker Desktop not found.
    echo [*] Downloading Docker Desktop installer...
    curl -Lo "%TEMP%\DockerDesktopInstaller.exe" ^
        "https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe"
    echo [*] Installing Docker Desktop (follow prompts)...
    "%TEMP%\DockerDesktopInstaller.exe" install --quiet
    echo [!] Please restart your computer and run this installer again after Docker starts.
    pause
    exit /b 0
)
for /f "tokens=*" %%V in ('docker --version 2^>nul') do set docker_version=%%V
echo [+] Docker found: %docker_version%

:: ─── Write .wslconfig for 256 GB swap ────────────────────────────────────────
echo [4/7] Configuring WSL2 memory/swap (.wslconfig)...
if not exist "%USERPROFILE%\.wslconfig" (
    copy /y "%~dp0wslconfig.template" "%USERPROFILE%\.wslconfig" >nul 2>&1
    echo [+] .wslconfig written to %USERPROFILE%\.wslconfig
) else (
    echo [~] .wslconfig already exists - skipping
)

:: ─── Create D-drive directories ───────────────────────────────────────────────
echo [5/7] Creating D-drive storage directories...
if exist "D:\" (
    mkdir "D:\mirai_storage" 2>nul
    mkdir "D:\mirai_swap"    2>nul
    echo [+] D:\mirai_storage and D:\mirai_swap created
) else (
    echo [~] D: drive not found - storage will use default volumes
)

:: ─── Copy .env template ───────────────────────────────────────────────────────
echo [6/7] Setting up environment config...
if not exist "%~dp0.env" (
    copy /y "%~dp0.env.example" "%~dp0.env" >nul
    echo [+] .env created - EDIT IT with your API keys before running!
) else (
    echo [~] .env already exists
)

:: ─── Launch via WSL2 ─────────────────────────────────────────────────────────
echo [7/7] Starting MirAI_OS in WSL2...
for /f "tokens=*" %%W in ('wsl wslpath -u "%~dp0" 2^>nul') do set WSL_DIR=%%W
wsl -d kali-linux -- bash -c "cd '%WSL_DIR%' && chmod +x install.sh && ./install.sh" 2>&1

echo.
echo  ╔═══════════════════════════════════════════════════════════════════╗
echo  ║  MirAI_OS installation complete!                                 ║
echo  ║                                                                   ║
echo  ║  Run start.bat to start the stack after reboot.                  ║
echo  ║  Edit .env with your API keys first!                             ║
echo  ╚═══════════════════════════════════════════════════════════════════╝
echo.
pause
