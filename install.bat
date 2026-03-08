@echo off
:: ============================================================
::  MirAI_OS – Windows Installer
::  Requires: Administrator privileges
::  Installs WSL2, Docker Desktop (if not present), then
::  launches the Linux installer inside WSL2.
:: ============================================================
setlocal EnableDelayedExpansion

title MirAI_OS Installer

:: ── Check Administrator ────────────────────────────────────
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please run this script as Administrator.
    echo Right-click install.bat and choose "Run as administrator".
    pause
    exit /b 1
)

echo.
echo  =====================================================
echo   MirAI_OS Windows Installer
echo  =====================================================
echo.

:: ── Step 1: Enable WSL2 ───────────────────────────────────
echo [INFO] Checking WSL2...
wsl --status >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Enabling WSL2 features. A reboot may be required.
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    echo [WARN] WSL2 features enabled. Please reboot and run this installer again.
    pause
    exit /b 0
)

wsl --set-default-version 2 >nul 2>&1
echo [OK]   WSL2 is available.

:: ── Step 2: Check / install a WSL2 distro ─────────────────
wsl -l -v 2>nul | findstr /i "ubuntu\|debian\|kali" >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] No WSL2 Linux distro found. Installing Ubuntu...
    wsl --install -d Ubuntu
    echo [INFO] Ubuntu installed. Please complete the Ubuntu setup in the new window,
    echo        then re-run this installer.
    pause
    exit /b 0
) else (
    echo [OK]   WSL2 Linux distro found.
)

:: ── Step 3: Check Docker Desktop ──────────────────────────
where docker >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Docker not found. Downloading Docker Desktop...
    set DOCKER_URL=https://desktop.docker.com/win/main/amd64/Docker Desktop Installer.exe
    set DOCKER_INSTALLER=%TEMP%\DockerDesktopInstaller.exe
    powershell -Command "Invoke-WebRequest -Uri 'https://desktop.docker.com/win/main/amd64/Docker Desktop Installer.exe' -OutFile '%DOCKER_INSTALLER%'"
    echo [INFO] Installing Docker Desktop (silent)...
    "%DOCKER_INSTALLER%" install --quiet --accept-license
    echo [OK]   Docker Desktop installed.
    echo [WARN] Please start Docker Desktop, ensure "Use WSL 2 based engine" is enabled,
    echo        then re-run this installer.
    pause
    exit /b 0
) else (
    echo [OK]   Docker is available: 
    docker --version
)

:: ── Step 4: Run the Linux installer inside WSL2 ──────────
echo [INFO] Launching MirAI_OS Linux installer in WSL2...
set MODEL=%1
if "%MODEL%"=="" set MODEL=dolphin-mistral

:: Convert Windows path (e.g. C:\Users\foo\MirAI_OS) to WSL path (/mnt/c/Users/foo/MirAI_OS)
for /f "delims=" %%P in ('wsl wslpath -u "%cd%"') do set WSL_DIR=%%P

wsl bash -c "cd '%WSL_DIR%' && bash install.sh --model %MODEL%"

if %errorLevel% equ 0 (
    echo.
    echo [OK] MirAI_OS installed successfully!
    echo      Open http://localhost:8080 in your browser.
) else (
    echo [ERROR] Installation failed. Review the output above.
)

pause
endlocal
