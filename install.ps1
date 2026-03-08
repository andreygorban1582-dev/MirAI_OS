# MirAI_OS – PowerShell Installer
# Run in PowerShell:  .\install.ps1
# For unrestricted execution:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

param(
    [string]$OllamaModel = "dolphin-mistral",
    [switch]$SkipOllama,
    [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MirAI_OS Installer v1.0.0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── Python check ──────────────────────────────────────────────────────────────
$python = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") { $python = $cmd; break }
    } catch {}
}
if (-not $python) {
    Write-Host "[ERROR] Python 3 not found." -ForegroundColor Red
    Write-Host "  Download: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] $python found." -ForegroundColor Green

# ── Upgrade pip ───────────────────────────────────────────────────────────────
& $python -m pip install --upgrade pip --quiet
Write-Host "[OK] pip ready." -ForegroundColor Green

# ── Python dependencies ───────────────────────────────────────────────────────
if (-not $SkipDeps) {
    Write-Host "[INFO] Installing Python dependencies..."
    try {
        & $python -m pip install -r requirements.txt --quiet
        Write-Host "[OK] Dependencies installed." -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Some dependencies failed: $_" -ForegroundColor Yellow
    }
}

# ── Ollama ────────────────────────────────────────────────────────────────────
if (-not $SkipOllama) {
    $ollamaInstalled = $null
    try { $ollamaInstalled = & ollama --version 2>&1 } catch {}

    if (-not $ollamaInstalled) {
        Write-Host "[INFO] Downloading Ollama..."
        $ollamaInstaller = Join-Path $env:TEMP "OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" `
                          -OutFile $ollamaInstaller -UseBasicParsing
        Write-Host "[INFO] Installing Ollama (silent)..."
        Start-Process -FilePath $ollamaInstaller -ArgumentList "/S" -Wait
        Remove-Item $ollamaInstaller -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Ollama installed." -ForegroundColor Green
    } else {
        Write-Host "[OK] Ollama already installed." -ForegroundColor Green
    }

    Write-Host "[INFO] Pulling Ollama model '$OllamaModel'..."
    try {
        & ollama pull $OllamaModel
        Write-Host "[OK] Model '$OllamaModel' ready." -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Could not pull model: $_" -ForegroundColor Yellow
    }
}

# ── .env ──────────────────────────────────────────────────────────────────────
$envFile = Join-Path $ScriptDir ".env"
if (-not (Test-Path $envFile)) {
    @"
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_ID=
OPENROUTER_API_KEY=
OLLAMA_MODEL=$OllamaModel
MOD2_ENABLED=true
VOICE_ENABLED=false
LOG_LEVEL=INFO
"@ | Set-Content $envFile
    Write-Host "[OK] .env created – edit it to add your API keys." -ForegroundColor Green
}

# ── data / log dirs ───────────────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path (Join-Path $ScriptDir "data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ScriptDir "logs") | Out-Null

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "  To start MirAI_OS:" -ForegroundColor Cyan
Write-Host "    $python main.py              # interactive CLI"
Write-Host "    $python main.py --mode service"
Write-Host "    $python main.py --mode telegram"
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
