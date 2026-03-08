@echo off
:: ============================================================
:: MirAI_OS – Build installer.exe (Windows)
:: Requires: Python 3.9+ and PyInstaller
:: Run from the project root: .\build_exe.bat
:: ============================================================

echo.
echo ============================================================
echo  MirAI_OS Installer Builder
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python not found. Install Python 3.9+ and add it to PATH.
    pause
    exit /b 1
)
echo [OK] Python found.

:: Ensure pip is available
python -m pip --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] pip not found.
    pause
    exit /b 1
)

:: Install PyInstaller if needed
echo [INFO] Installing/upgrading PyInstaller...
python -m pip install --quiet --upgrade pyinstaller
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)
echo [OK] PyInstaller ready.

:: Install core runtime deps (so they can be bundled)
echo [INFO] Installing runtime dependencies...
python -m pip install --quiet -r requirements.txt
echo [OK] Dependencies installed.

:: Clean previous build artifacts
echo [INFO] Cleaning previous build...
IF EXIST build rmdir /s /q build
IF EXIST dist  rmdir /s /q dist

:: Run PyInstaller
echo [INFO] Building MirAI_OS_Installer.exe ...
python -m PyInstaller --clean --noconfirm mirai_installer.spec

IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] Build failed. Check the output above for details.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Build complete!
echo  Installer: dist\MirAI_OS_Installer.exe
echo ============================================================
echo.
pause
