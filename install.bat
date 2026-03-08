@echo off
:: ============================================================
:: MirAI_OS – Windows Installer
:: Run as Administrator for best results.
:: ============================================================

echo.
echo ============================================================
echo   MirAI_OS Installer v1.0.0
echo ============================================================
echo.

:: ── Python check ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python not found.
    echo   Download from https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo [OK] Python found.

:: ── pip ───────────────────────────────────────────────────────────────────────
python -m pip install --upgrade pip --quiet
echo [OK] pip ready.

:: ── Python dependencies ───────────────────────────────────────────────────────
echo [INFO] Installing Python dependencies...
python -m pip install -r requirements.txt --quiet
IF ERRORLEVEL 1 (
    echo [WARN] Some dependencies failed to install. Continuing...
)
echo [OK] Dependencies installed.

:: ── Ollama ────────────────────────────────────────────────────────────────────
ollama --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [INFO] Downloading Ollama installer...
    curl -L "https://ollama.com/download/OllamaSetup.exe" -o "%TEMP%\OllamaSetup.exe"
    echo [INFO] Installing Ollama (silent)...
    "%TEMP%\OllamaSetup.exe" /S
    del "%TEMP%\OllamaSetup.exe" 2>nul
    echo [OK] Ollama installed.
) ELSE (
    echo [OK] Ollama already installed.
)

:: ── Ollama model ──────────────────────────────────────────────────────────────
SET OLLAMA_MODEL_NAME=dolphin-mistral
echo [INFO] Pulling Ollama model %OLLAMA_MODEL_NAME%...
ollama pull %OLLAMA_MODEL_NAME% || echo [WARN] Could not pull model.

:: ── .env ─────────────────────────────────────────────────────────────────────
IF NOT EXIST .env (
    echo TELEGRAM_BOT_TOKEN=> .env
    echo TELEGRAM_ADMIN_ID=>> .env
    echo OPENROUTER_API_KEY=>> .env
    echo OLLAMA_MODEL=dolphin-mistral>> .env
    echo MOD2_ENABLED=true>> .env
    echo VOICE_ENABLED=false>> .env
    echo LOG_LEVEL=INFO>> .env
    echo [OK] .env created - edit it to add your API keys.
)

:: ── data / log dirs ───────────────────────────────────────────────────────────
IF NOT EXIST data mkdir data
IF NOT EXIST logs mkdir logs

echo.
echo ============================================================
echo   Installation complete!
echo   To start MirAI_OS:
echo     python main.py              ^(interactive CLI^)
echo     python main.py --mode service
echo     python main.py --mode telegram
echo ============================================================
echo.
pause
