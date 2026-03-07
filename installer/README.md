# MirAI OS — Windows Installer

## Files

| File | Purpose |
|---|---|
| `mirai_launcher.py` | Python source for the Windows GUI launcher |
| `build_exe.py` | Build script — compiles `MirAI_OS.exe` from launcher |
| `MirAI_Setup.iss` | Inno Setup script — creates proper Windows installer |
| `install_windows.ps1` | Full PowerShell installer (alternative to .exe) |

---

## Option A: Quick GUI Launcher (.exe)

### Build on Windows:
```powershell
# Inside your MirAI_OS directory
pip install pyinstaller
python installer/build_exe.py
```
Output: `MirAI_OS.exe` in the root directory

### What it does:
- Opens a Watchdogs-style terminal window
- Shows MirAI's live status (RUNNING / STOPPED)
- START / STOP / RESTART buttons
- Live log streaming from WSL2
- Edit .env shortcut
- Auto-detects WSL2 Kali installation

---

## Option B: Full PowerShell Installer

```powershell
# Run as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force
.\installer\install_windows.ps1
```

### What it does:
- Enables WSL2 features
- Installs Kali Linux
- Configures `.wslconfig` for Legion Go
- Clones MirAI OS into WSL
- Runs `setup_wsl.sh` automatically
- Offers 128GB swap setup
- Creates desktop shortcut
- Optional: auto-start on Windows boot

---

## Option C: Inno Setup Installer

For distributing to others — creates a standard Windows `.exe` installer.

1. Download Inno Setup: https://jrsoftware.org/isdl.php
2. Open `MirAI_Setup.iss` in Inno Setup Compiler
3. Build → Creates `dist/installer/MirAI_OS_Setup_0.1.0.exe`

---

## Requirements

- Windows 10 build 19041 (May 2020 Update) or later
- WSL2 support
- ~20GB free disk for Kali + Python deps
- ~128GB free disk for swap (recommended)

El Psy Kongroo.
