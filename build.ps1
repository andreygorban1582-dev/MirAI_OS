<#
.SYNOPSIS
    Build MirAI_OS_Setup.exe for Lenovo Legion Go.

.DESCRIPTION
    1. Creates/activates a Python virtual environment
    2. Installs all dependencies from requirements.txt
    3. Bundles the app with PyInstaller (UAC elevation, single-file distribution)
    4. Compiles the Inno Setup script to produce MirAI_OS_Setup.exe

.NOTES
    Requirements (must be on PATH before running):
      - Python 3.10+  : https://www.python.org/downloads/
      - Inno Setup 6  : https://jrsoftware.org/isinfo.php  (iscc.exe)
      - (Optional) UPX: https://upx.github.io/  (for smaller binaries)

    Run from the repository root:
        .\build.ps1
#>

#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root      = $PSScriptRoot
$VenvDir   = Join-Path $Root ".venv"
$DistDir   = Join-Path $Root "dist"
$BuildDir  = Join-Path $Root "build"
$SpecFile  = Join-Path $Root "MirAI_OS.spec"
$IssFile   = Join-Path $Root "installer\setup.iss"
$AssetsDir = Join-Path $Root "assets"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
function Write-Step { param([string]$msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }

# ---------------------------------------------------------------------------
# Step 1 – Ensure Python is available
# ---------------------------------------------------------------------------
Write-Step "Checking Python"
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue)?.Source
if (-not $pythonExe) {
    Write-Error "Python not found on PATH. Install from https://www.python.org/downloads/"
    exit 1
}
Write-Host "Found Python: $pythonExe" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 2 – Create / update virtual environment
# ---------------------------------------------------------------------------
Write-Step "Setting up virtual environment"
if (-not (Test-Path $VenvDir)) {
    & python -m venv $VenvDir
}
$pip    = Join-Path $VenvDir "Scripts\pip.exe"
$python = Join-Path $VenvDir "Scripts\python.exe"

& $pip install --upgrade pip --quiet
& $pip install -r (Join-Path $Root "requirements.txt") --quiet
& $pip install pyinstaller --quiet

# ---------------------------------------------------------------------------
# Step 3 – Clean previous build artefacts
# ---------------------------------------------------------------------------
Write-Step "Cleaning previous build artefacts"
@($DistDir, $BuildDir) | ForEach-Object {
    if (Test-Path $_) { Remove-Item $_ -Recurse -Force }
}

# ---------------------------------------------------------------------------
# Step 4 – Create placeholder icon if missing; compile with icon if present
# ---------------------------------------------------------------------------
$iconPath   = Join-Path $AssetsDir "icon.ico"
$iconDefine = if (Test-Path $iconPath) { "/DUseCustomIcon" } else {
    Write-Host "assets/icon.ico not found – installer will use the default icon." -ForegroundColor Yellow
    ""
}

# ---------------------------------------------------------------------------
# Step 5 – Bundle with PyInstaller
# ---------------------------------------------------------------------------
Write-Step "Bundling application with PyInstaller"
& $python -m PyInstaller $SpecFile --clean --noconfirm

# ---------------------------------------------------------------------------
# Step 6 – Compile Inno Setup installer
# ---------------------------------------------------------------------------
Write-Step "Compiling Inno Setup installer"
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) {
    # Try common install location
    $isccPath = "C:\Program Files (x86)\Inno Setup 6\iscc.exe"
    if (Test-Path $isccPath) { $iscc = $isccPath } else {
        Write-Warning "iscc.exe not found – skipping installer compilation."
        Write-Warning "Install Inno Setup 6 from https://jrsoftware.org/isinfo.php"
        exit 0
    }
} else {
    $isccPath = $iscc.Source
}

if ($iconDefine) {
    & $isccPath $iconDefine $IssFile
} else {
    & $isccPath $IssFile
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
$installer = Join-Path $DistDir "MirAI_OS_Setup.exe"
if (Test-Path $installer) {
    Write-Host "`n✅  Installer ready: $installer" -ForegroundColor Green
} else {
    Write-Error "Installer file not found after build. Check the output above for errors."
}
