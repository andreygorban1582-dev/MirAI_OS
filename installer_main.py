"""
MirAI_OS Installer – GUI installer / launcher.
This file is the entry point compiled into MirAI_OS_Installer.exe via PyInstaller.

Behaviour:
  1. Shows a welcome splash with installation options.
  2. Checks for Python and pip on PATH.
  3. Installs Python dependencies from requirements.txt (bundled or downloaded).
  4. Optionally downloads and configures Ollama.
  5. Writes a .env file with user-supplied API keys.
  6. Launches main.py in the selected mode.
"""

from __future__ import annotations

import os
import platform
import queue
import subprocess  # noqa: S404
import sys
import threading
from pathlib import Path

try:
    import tkinter as tk
    import tkinter.font as tkFont
    from tkinter import messagebox, scrolledtext, ttk

    _TK_AVAILABLE = True
except ImportError:
    _TK_AVAILABLE = False

# ── constants ─────────────────────────────────────────────────────────────────
APP_NAME = "MirAI_OS"
APP_VERSION = "1.0.0"
OLLAMA_DOWNLOAD_URL = {
    "Windows": "https://ollama.com/download/OllamaSetup.exe",
    "Darwin": "https://ollama.com/download/Ollama-darwin.zip",
    "Linux": "https://ollama.com/install.sh",
}
REPO_URL = "https://github.com/andreygorban1582-dev/MirAI_OS"

# Determine base directory (works both for .py and frozen .exe)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent


def _find_python() -> str | None:
    """Return the path to a usable Python interpreter."""
    candidates = ["python", "python3", sys.executable]
    for candidate in candidates:
        try:
            result = subprocess.run(  # noqa: S603,S607
                [candidate, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and "Python 3" in result.stdout + result.stderr:
                return candidate
        except Exception:
            continue
    return None


def _find_main() -> Path | None:
    """Locate main.py relative to installer or on PATH."""
    candidates = [
        BASE_DIR / "main.py",
        BASE_DIR / "MirAI_OS" / "main.py",
        Path.cwd() / "main.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _find_requirements() -> Path | None:
    candidates = [
        BASE_DIR / "requirements.txt",
        BASE_DIR / "MirAI_OS" / "requirements.txt",
        Path.cwd() / "requirements.txt",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


# ── GUI ───────────────────────────────────────────────────────────────────────

class InstallerApp:
    """Main installer GUI window."""

    DARK_BG = "#0d1117"
    PANEL_BG = "#161b22"
    ACCENT = "#58a6ff"
    GREEN = "#3fb950"
    RED = "#f85149"
    TEXT = "#e6edf3"
    SUBTEXT = "#8b949e"

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION} – Installer")
        self.root.geometry("760x560")
        self.root.resizable(False, False)
        self.root.configure(bg=self.DARK_BG)
        self._center_window()

        self._log_queue: queue.Queue = queue.Queue()
        self._install_thread: threading.Thread | None = None

        # StringVars for user input
        self.var_tg_token = tk.StringVar()
        self.var_tg_admin = tk.StringVar()
        self.var_openrouter = tk.StringVar()
        self.var_ollama_model = tk.StringVar(value="dolphin-mistral")
        self.var_mode = tk.StringVar(value="cli")
        self.var_install_deps = tk.BooleanVar(value=True)
        self.var_install_ollama = tk.BooleanVar(value=False)
        self.var_mod2 = tk.BooleanVar(value=True)

        self._build_ui()
        self.root.after(100, self._poll_log)

    def _center_window(self) -> None:
        self.root.update_idletasks()
        w = self.root.winfo_width() or 760
        h = self.root.winfo_height() or 560
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        title_font = tkFont.Font(family="Consolas", size=18, weight="bold")
        sub_font = tkFont.Font(family="Consolas", size=10)
        label_font = tkFont.Font(family="Consolas", size=10)
        entry_font = tkFont.Font(family="Consolas", size=10)

        # ── header ────────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=self.PANEL_BG, pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text=f"⚡ {APP_NAME}", font=title_font,
            bg=self.PANEL_BG, fg=self.ACCENT,
        ).pack()
        tk.Label(
            header,
            text=f"Version {APP_VERSION}  |  El Psy Kongroo",
            font=sub_font, bg=self.PANEL_BG, fg=self.SUBTEXT,
        ).pack()

        # ── notebook ──────────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=self.DARK_BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.PANEL_BG,
            foreground=self.TEXT,
            padding=[12, 6],
            font=("Consolas", 10),
        )
        style.map("TNotebook.Tab", background=[("selected", self.DARK_BG)])

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=(5, 0))

        # ── Tab 1: Configuration ──────────────────────────────────────────────
        cfg_tab = tk.Frame(nb, bg=self.DARK_BG)
        nb.add(cfg_tab, text="  Configuration  ")
        self._build_config_tab(cfg_tab, label_font, entry_font)

        # ── Tab 2: Install Log ────────────────────────────────────────────────
        log_tab = tk.Frame(nb, bg=self.DARK_BG)
        nb.add(log_tab, text="  Install Log  ")
        self.log_text = scrolledtext.ScrolledText(
            log_tab, bg="#0a0e13", fg=self.TEXT,
            font=("Consolas", 9), state="disabled", wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.log_text.tag_configure("ok", foreground=self.GREEN)
        self.log_text.tag_configure("err", foreground=self.RED)
        self.log_text.tag_configure("info", foreground=self.ACCENT)

        # ── status bar + buttons ──────────────────────────────────────────────
        bottom = tk.Frame(self.root, bg=self.DARK_BG, pady=8)
        bottom.pack(fill="x", padx=10)

        self.progress = ttk.Progressbar(bottom, mode="indeterminate", length=380)
        self.progress.pack(side="left", padx=(0, 12))

        tk.Button(
            bottom, text="Install & Launch",
            bg=self.ACCENT, fg=self.DARK_BG, font=("Consolas", 11, "bold"),
            relief="flat", padx=14, pady=6,
            command=self._on_install_launch,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            bottom, text="Launch Only",
            bg=self.PANEL_BG, fg=self.TEXT, font=("Consolas", 10),
            relief="flat", padx=12, pady=6,
            command=self._on_launch_only,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            bottom, text="Quit",
            bg=self.PANEL_BG, fg=self.RED, font=("Consolas", 10),
            relief="flat", padx=12, pady=6,
            command=self.root.destroy,
        ).pack(side="right")

    def _build_config_tab(
        self, parent: tk.Frame, label_font: tkFont.Font, entry_font: tkFont.Font
    ) -> None:
        pad = {"padx": 16, "pady": 4}

        def row(lbl: str, var: tk.Variable, show: str = "") -> None:
            f = tk.Frame(parent, bg=self.DARK_BG)
            f.pack(fill="x", **pad)
            tk.Label(
                f, text=lbl, font=label_font,
                bg=self.DARK_BG, fg=self.SUBTEXT, width=22, anchor="w",
            ).pack(side="left")
            tk.Entry(
                f, textvariable=var, font=entry_font,
                bg=self.PANEL_BG, fg=self.TEXT,
                insertbackground=self.TEXT, relief="flat",
                show=show, width=42,
            ).pack(side="left")

        # Separator
        tk.Label(
            parent, text="── API Keys & Tokens ──────────────────────────",
            font=("Consolas", 9), bg=self.DARK_BG, fg=self.SUBTEXT,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        row("Telegram Bot Token:", self.var_tg_token, show="*")
        row("Telegram Admin ID:", self.var_tg_admin)
        row("OpenRouter API Key:", self.var_openrouter, show="*")

        tk.Label(
            parent, text="── Model & Mode ───────────────────────────────",
            font=("Consolas", 9), bg=self.DARK_BG, fg=self.SUBTEXT,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        row("Ollama Model:", self.var_ollama_model)

        mode_frame = tk.Frame(parent, bg=self.DARK_BG)
        mode_frame.pack(fill="x", padx=16, pady=4)
        tk.Label(
            mode_frame, text="Launch Mode:", font=label_font,
            bg=self.DARK_BG, fg=self.SUBTEXT, width=22, anchor="w",
        ).pack(side="left")
        for m in ("cli", "service", "telegram"):
            tk.Radiobutton(
                mode_frame, text=m, variable=self.var_mode, value=m,
                bg=self.DARK_BG, fg=self.TEXT, selectcolor=self.PANEL_BG,
                font=("Consolas", 10), activebackground=self.DARK_BG,
            ).pack(side="left", padx=8)

        tk.Label(
            parent, text="── Options ────────────────────────────────────",
            font=("Consolas", 9), bg=self.DARK_BG, fg=self.SUBTEXT,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        for text, var in [
            ("Install Python dependencies", self.var_install_deps),
            ("Download & install Ollama", self.var_install_ollama),
            ("Enable Mod 2 (memory + web search)", self.var_mod2),
        ]:
            tk.Checkbutton(
                parent, text=text, variable=var,
                bg=self.DARK_BG, fg=self.TEXT, selectcolor=self.PANEL_BG,
                font=("Consolas", 10), activebackground=self.DARK_BG,
            ).pack(anchor="w", padx=30, pady=2)

    # ── actions ───────────────────────────────────────────────────────────────

    def _on_install_launch(self) -> None:
        if self._install_thread and self._install_thread.is_alive():
            return
        self._install_thread = threading.Thread(
            target=self._run_install_and_launch, daemon=True
        )
        self._install_thread.start()
        self.progress.start(10)

    def _on_launch_only(self) -> None:
        self._write_env()
        self._launch_app()

    # ── install worker (background thread) ───────────────────────────────────

    def _run_install_and_launch(self) -> None:
        try:
            self._log("=== MirAI_OS Installer ===", "info")
            self._log(f"Platform: {platform.system()} {platform.release()}", "info")

            python = _find_python()
            if not python:
                self._log("ERROR: Python 3 not found. Please install Python 3.9+.", "err")
                self._stop_progress()
                return
            self._log(f"Python: {python}", "ok")

            # Install pip deps
            if self.var_install_deps.get():
                req = _find_requirements()
                if req:
                    self._log(f"Installing dependencies from {req}…", "info")
                    self._run_cmd(
                        [python, "-m", "pip", "install", "-r", str(req), "--quiet"],
                        "Dependencies installed.",
                    )
                else:
                    self._log("requirements.txt not found – skipping.", "err")

            # Install Ollama
            if self.var_install_ollama.get():
                self._install_ollama()

            # Write .env
            self._write_env()
            self._log(".env written.", "ok")

            # Pull Ollama model
            if self.var_install_ollama.get() or self._ollama_running():
                model = self.var_ollama_model.get().strip() or "dolphin-mistral"
                self._log(f"Pulling Ollama model '{model}'…", "info")
                self._run_cmd(["ollama", "pull", model], f"Model '{model}' ready.")

            self._log("Installation complete!", "ok")
            self._stop_progress()
            self._launch_app()
        except Exception as exc:
            self._log(f"Fatal error: {exc}", "err")
            self._stop_progress()

    def _install_ollama(self) -> None:
        system = platform.system()
        url = OLLAMA_DOWNLOAD_URL.get(system, "")
        if not url:
            self._log(f"Ollama auto-install not supported on {system}.", "err")
            return
        self._log(f"Downloading Ollama from {url}…", "info")
        if system == "Linux":
            self._run_cmd(
                ["bash", "-c", f"curl -fsSL {url} | sh"],
                "Ollama installed (Linux).",
            )
        elif system == "Windows":
            import urllib.request

            dest = Path.home() / "OllamaSetup.exe"
            try:
                urllib.request.urlretrieve(url, str(dest))  # noqa: S310
                self._run_cmd([str(dest), "/S"], "Ollama installed (Windows).")
            except Exception as exc:
                self._log(f"Ollama download failed: {exc}", "err")
        elif system == "Darwin":
            self._log("Please install Ollama manually from https://ollama.com", "err")

    def _write_env(self) -> None:
        env_lines = [
            f"TELEGRAM_BOT_TOKEN={self.var_tg_token.get().strip()}",
            f"TELEGRAM_ADMIN_ID={self.var_tg_admin.get().strip()}",
            f"OPENROUTER_API_KEY={self.var_openrouter.get().strip()}",
            f"OLLAMA_MODEL={self.var_ollama_model.get().strip() or 'dolphin-mistral'}",
            f"MOD2_ENABLED={'true' if self.var_mod2.get() else 'false'}",
        ]
        env_path = BASE_DIR / ".env"
        env_path.write_text("\n".join(env_lines) + "\n")

    def _ollama_running(self) -> bool:
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(  # noqa: S310
                "http://localhost:11434/api/tags", timeout=2
            ) as r:
                return r.status == 200
        except Exception:
            return False

    def _launch_app(self) -> None:
        python = _find_python()
        main_py = _find_main()
        if not python:
            messagebox.showerror("Error", "Python 3 not found.")
            return
        if not main_py:
            messagebox.showerror("Error", "main.py not found.")
            return
        mode = self.var_mode.get()
        self._log(f"Launching MirAI_OS in '{mode}' mode…", "info")
        try:
            if mode == "cli":
                # Open in a new terminal window
                self._open_terminal(python, main_py, mode)
            else:
                subprocess.Popen(  # noqa: S603
                    [python, str(main_py), "--mode", mode],
                    cwd=str(main_py.parent),
                )
            self._log("MirAI_OS launched!", "ok")
        except Exception as exc:
            self._log(f"Launch error: {exc}", "err")

    def _open_terminal(self, python: str, main_py: Path, mode: str) -> None:
        """Open a terminal window running MirAI_OS."""
        system = platform.system()
        cmd = [python, str(main_py), "--mode", mode]
        if system == "Windows":
            subprocess.Popen(  # noqa: S603
                ["cmd", "/c", "start", "cmd", "/k"] + cmd,
                cwd=str(main_py.parent),
            )
        elif system == "Darwin":
            script = " ".join(cmd)
            subprocess.Popen(  # noqa: S603
                ["osascript", "-e",
                 f'tell app "Terminal" to do script "{script}"'],
            )
        else:
            for term in ("x-terminal-emulator", "gnome-terminal", "xterm"):
                try:
                    subprocess.Popen(  # noqa: S603,S607
                        [term, "--"] + cmd,
                        cwd=str(main_py.parent),
                    )
                    return
                except FileNotFoundError:
                    continue
            # Fallback: run in background
            subprocess.Popen(cmd, cwd=str(main_py.parent))  # noqa: S603

    # ── helpers ───────────────────────────────────────────────────────────────

    def _run_cmd(self, cmd: list, success_msg: str) -> bool:
        self._log(f"$ {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                self._log(line.rstrip())
            proc.wait()
            if proc.returncode == 0:
                self._log(success_msg, "ok")
                return True
            self._log(f"Command failed (exit {proc.returncode})", "err")
            return False
        except FileNotFoundError:
            self._log(f"Command not found: {cmd[0]}", "err")
            return False

    def _log(self, msg: str, tag: str = "") -> None:
        self._log_queue.put((msg, tag))

    def _poll_log(self) -> None:
        try:
            while True:
                msg, tag = self._log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n", tag or None)
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log)

    def _stop_progress(self) -> None:
        self.root.after(0, self.progress.stop)

    def run(self) -> None:
        self.root.mainloop()


# ── entry point ───────────────────────────────────────────────────────────────

def _cli_install() -> None:
    """Minimal CLI fallback for headless / non-GUI environments."""
    print(f"\n{'='*60}")
    print(f"  {APP_NAME} – CLI Installer")
    print(f"{'='*60}\n")

    python = _find_python()
    if not python:
        print("[ERROR] Python 3 not found. Install Python 3.9+ first.")
        sys.exit(1)
    print(f"[OK] Python: {python}")

    req = _find_requirements()
    if req:
        print(f"[INFO] Installing dependencies from {req}…")
        result = subprocess.run(  # noqa: S603
            [python, "-m", "pip", "install", "-r", str(req), "--quiet"],
            check=False,
        )
        if result.returncode == 0:
            print("[OK] Dependencies installed.")
        else:
            print("[WARN] Some dependencies failed to install.")
    else:
        print("[WARN] requirements.txt not found – skipping.")

    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        env_example = BASE_DIR / ".env.example"
        if env_example.exists():
            import shutil
            shutil.copy(str(env_example), str(env_path))
        else:
            env_path.write_text(
                "TELEGRAM_BOT_TOKEN=\nTELEGRAM_ADMIN_ID=\n"
                "OPENROUTER_API_KEY=\nOLLAMA_MODEL=dolphin-mistral\n"
                "MOD2_ENABLED=true\nLOG_LEVEL=INFO\n"
            )
        print(f"[OK] .env written to {env_path}")

    main_py = _find_main()
    if not main_py:
        print("[ERROR] main.py not found.")
        sys.exit(1)

    print(f"\n[INFO] Launching MirAI_OS (CLI mode)…\n")
    try:
        result = subprocess.run(  # noqa: S603
            [python, str(main_py), "--mode", "cli"],
            cwd=str(main_py.parent),
            check=False,
        )
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        pass


def main() -> None:
    if _TK_AVAILABLE:
        app = InstallerApp()
        app.run()
    else:
        _cli_install()


if __name__ == "__main__":
    main()
