"""
MirAI OS — Windows Launcher
A native Windows GUI that manages the MirAI OS process inside WSL2.
Looks like a hacker terminal. El Psy Kongroo.

Built with tkinter (stdlib — zero extra deps for the .exe).
PyInstaller compiles this into MirAI_OS.exe.
"""
import subprocess
import sys
import os
import threading
import time
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk

# ── Constants ─────────────────────────────────────────────────────────────────

APP_NAME  = "MirAI OS"
VERSION   = "0.1.0"
BG        = "#0a0a0a"
FG        = "#00ff88"
FG2       = "#00cc66"
FG_DIM    = "#004422"
FG_WARN   = "#ffaa00"
FG_ERR    = "#ff3333"
FG_TITLE  = "#00ffcc"
FONT_MONO = ("Consolas", 10)
FONT_BIG  = ("Consolas", 18, "bold")
FONT_MED  = ("Consolas", 12, "bold")

WSL_DISTRO   = "kali-linux"   # change if different
MIRAI_DIR    = "~/MirAI_OS"
SCREEN_NAME  = "mirai"
LOG_TAIL_CMD = f"wsl -d {WSL_DISTRO} -- bash -c 'tail -f {MIRAI_DIR}/data/mirai.log 2>/dev/null'"

BOOT_ART = """
 ███╗   ███╗██╗██████╗  █████╗ ██╗
 ████╗ ████║██║██╔══██╗██╔══██╗██║
 ██╔████╔██║██║██████╔╝███████║██║
 ██║╚██╔╝██║██║██╔══██╗██╔══██║██║
 ██║ ╚═╝ ██║██║██║  ██║██║  ██║███████╗
 ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
      OS v{ver}  |  El Psy Kongroo.
""".format(ver=VERSION)


# ── Helpers ───────────────────────────────────────────────────────────────────

def run_wsl(cmd: str, capture: bool = True) -> tuple[int, str]:
    full = ["wsl", "-d", WSL_DISTRO, "--", "bash", "-c", cmd]
    try:
        r = subprocess.run(
            full, capture_output=capture, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return -1, str(e)


def is_wsl_installed() -> bool:
    try:
        r = subprocess.run(
            ["wsl", "--list", "--quiet"], capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return WSL_DISTRO.lower() in r.stdout.lower()
    except Exception:
        return False


def is_mirai_running() -> bool:
    code, out = run_wsl(f"screen -list | grep {SCREEN_NAME}")
    return code == 0 and SCREEN_NAME in out


# ── Main App Window ───────────────────────────────────────────────────────────

class MirAILauncher(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(f"MirAI OS {VERSION} — Future Gadget Lab")
        self.configure(bg=BG)
        self.geometry("900x650")
        self.resizable(True, True)
        self.minsize(700, 500)

        # Try to set window icon
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self._log_thread = None
        self._log_proc   = None
        self._status_var = tk.StringVar(value="CHECKING...")
        self._running    = False

        self._build_ui()
        self._print(BOOT_ART, color=FG_TITLE)
        self._print(f"  Platform: Windows {sys.getwindowsversion().major}.{sys.getwindowsversion().minor}"
                    if sys.platform == "win32" else "  Platform: Linux")
        self._check_status()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        # Title bar
        title_frame = tk.Frame(self, bg=BG)
        title_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(title_frame, text="▸ MIRAI OS", font=FONT_BIG,
                 bg=BG, fg=FG_TITLE).pack(side="left")
        self._status_badge = tk.Label(
            title_frame, textvariable=self._status_var,
            font=FONT_MONO, bg=BG, fg=FG_WARN,
        )
        self._status_badge.pack(side="right", padx=10)

        # Separator
        tk.Frame(self, bg=FG_DIM, height=1).pack(fill="x", padx=10, pady=4)

        # Button row
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=10, pady=4)
        self._btn_start = self._btn(btn_frame, "⚡ START", self._start_mirai, FG)
        self._btn_stop  = self._btn(btn_frame, "■ STOP",  self._stop_mirai,  FG_ERR)
        self._btn(btn_frame, "↺ RESTART",  self._restart_mirai, FG_WARN)
        self._btn(btn_frame, "📋 LOGS",    self._toggle_logs,   FG2)
        self._btn(btn_frame, "⚙ INSTALL",  self._run_install,   FG_TITLE)
        self._btn(btn_frame, "✎ EDIT .ENV", self._open_env,    FG_DIM)
        self._btn(btn_frame, "↻ REFRESH",  self._check_status,  FG_DIM)

        # Log terminal
        self._log = scrolledtext.ScrolledText(
            self, bg="#050505", fg=FG, font=FONT_MONO,
            insertbackground=FG, selectbackground=FG_DIM,
            relief="flat", borderwidth=0, wrap="word",
        )
        self._log.pack(fill="both", expand=True, padx=10, pady=(4, 0))
        self._log.config(state="disabled")

        # Tag colours
        for tag, colour in [("title", FG_TITLE), ("ok", FG), ("warn", FG_WARN),
                             ("err", FG_ERR), ("dim", FG_DIM)]:
            self._log.tag_config(tag, foreground=colour)

        # Status bar
        status_frame = tk.Frame(self, bg="#111111")
        status_frame.pack(fill="x")
        tk.Label(status_frame, text=f"  Future Gadget Lab #8  |  Legion Go Node  |  El Psy Kongroo.",
                 font=FONT_MONO, bg="#111111", fg=FG_DIM).pack(side="left", pady=2)

    def _btn(self, parent, text, cmd, colour=FG) -> tk.Button:
        b = tk.Button(
            parent, text=text, command=cmd,
            bg="#111111", fg=colour, font=FONT_MONO,
            activebackground=FG_DIM, activeforeground=BG,
            relief="flat", bd=0, padx=8, pady=4, cursor="hand2",
        )
        b.pack(side="left", padx=(0, 4))
        return b

    # ── Logging ───────────────────────────────────────────────────────────────

    def _print(self, text: str, color: str = FG, newline: bool = True):
        self._log.config(state="normal")
        tag = {FG_TITLE: "title", FG: "ok", FG_WARN: "warn",
               FG_ERR: "err", FG_DIM: "dim"}.get(color, "ok")
        self._log.insert("end", text + ("\n" if newline else ""), tag)
        self._log.see("end")
        self._log.config(state="disabled")

    def _ts(self) -> str:
        return time.strftime("[%H:%M:%S]")

    # ── Status check ─────────────────────────────────────────────────────────

    def _check_status(self):
        self._print(f"{self._ts()} Checking system status...", FG_DIM)
        threading.Thread(target=self._check_status_bg, daemon=True).start()

    def _check_status_bg(self):
        if not is_wsl_installed():
            self.after(0, lambda: self._set_status("WSL NOT FOUND", FG_ERR))
            self.after(0, lambda: self._print(
                f"{self._ts()} WSL '{WSL_DISTRO}' not installed!\n"
                "  Run installer first: click ⚙ INSTALL", FG_ERR
            ))
            return
        running = is_mirai_running()
        if running:
            self.after(0, lambda: self._set_status("● RUNNING", FG))
        else:
            self.after(0, lambda: self._set_status("○ STOPPED", FG_WARN))
        self.after(0, lambda: self._print(
            f"{self._ts()} MirAI OS {'is RUNNING' if running else 'is STOPPED'}.",
            FG if running else FG_WARN,
        ))

    def _set_status(self, text: str, colour: str):
        self._status_var.set(text)
        self._status_badge.config(fg=colour)

    # ── Controls ──────────────────────────────────────────────────────────────

    def _start_mirai(self):
        self._print(f"{self._ts()} Starting MirAI OS...", FG_TITLE)
        def _bg():
            code, out = run_wsl(
                f"cd {MIRAI_DIR} && "
                f"source venv/bin/activate 2>/dev/null; "
                f"sudo service redis-server start 2>/dev/null; "
                f"screen -dmS {SCREEN_NAME} python main.py"
            )
            self.after(0, lambda: self._print(
                f"{self._ts()} {'Started!' if code == 0 else 'Error: ' + out}",
                FG if code == 0 else FG_ERR,
            ))
            self.after(1000, self._check_status)
            if code == 0:
                self.after(2000, self._start_log_tail)
        threading.Thread(target=_bg, daemon=True).start()

    def _stop_mirai(self):
        self._print(f"{self._ts()} Stopping MirAI OS...", FG_WARN)
        self._stop_log_tail()
        def _bg():
            run_wsl(f"screen -S {SCREEN_NAME} -X quit 2>/dev/null || true")
            self.after(0, lambda: self._print(f"{self._ts()} Stopped.", FG_WARN))
            self.after(500, self._check_status)
        threading.Thread(target=_bg, daemon=True).start()

    def _restart_mirai(self):
        self._stop_mirai()
        self.after(3000, self._start_mirai)

    def _toggle_logs(self):
        if self._log_thread and self._log_thread.is_alive():
            self._stop_log_tail()
        else:
            self._start_log_tail()

    def _start_log_tail(self):
        if self._log_thread and self._log_thread.is_alive():
            return
        self._print(f"{self._ts()} Streaming MirAI logs (live)...", FG_DIM)
        self._running = True
        self._log_thread = threading.Thread(target=self._log_tail_bg, daemon=True)
        self._log_thread.start()

    def _stop_log_tail(self):
        self._running = False
        if self._log_proc:
            try:
                self._log_proc.terminate()
            except Exception:
                pass
            self._log_proc = None

    def _log_tail_bg(self):
        try:
            cmd = ["wsl", "-d", WSL_DISTRO, "--", "bash", "-c",
                   f"tail -f {MIRAI_DIR}/data/mirai.log 2>/dev/null"]
            self._log_proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            for line in self._log_proc.stdout:
                if not self._running:
                    break
                colour = FG_ERR if "ERROR" in line else FG_WARN if "WARNING" in line else FG2
                self.after(0, lambda l=line, c=colour: self._print(l.rstrip(), c))
        except Exception as e:
            self.after(0, lambda: self._print(f"Log stream error: {e}", FG_ERR))

    def _run_install(self):
        self._print(f"{self._ts()} Launching installer...", FG_TITLE)
        threading.Thread(target=self._install_bg, daemon=True).start()

    def _install_bg(self):
        steps = [
            ("Updating WSL Kali...", f"wsl -d {WSL_DISTRO} -- bash -c 'sudo apt-get update -qq && sudo apt-get upgrade -y -qq'"),
            ("Installing deps...", f"wsl -d {WSL_DISTRO} -- bash -c 'cd {MIRAI_DIR} && bash scripts/setup_wsl.sh'"),
        ]
        for desc, cmd in steps:
            self.after(0, lambda d=desc: self._print(f"  ▸ {d}", FG_DIM))
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                ok = result.returncode == 0
                self.after(0, lambda o=ok, d=desc: self._print(
                    f"  {'✓' if o else '✗'} {d}", FG if o else FG_ERR
                ))
            except Exception as e:
                self.after(0, lambda ex=e: self._print(f"  ✗ Error: {ex}", FG_ERR))
        self.after(0, lambda: self._print(f"{self._ts()} Install complete. Edit .env then click START.", FG))

    def _open_env(self):
        code, home = run_wsl("echo $HOME")
        env_path = f"\\\\wsl$\\{WSL_DISTRO}{home.strip()}/MirAI_OS/.env"
        try:
            os.startfile(env_path)
        except Exception:
            self._print(f"  Open manually: {env_path}", FG_DIM)

    def _on_close(self):
        self._stop_log_tail()
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    # Request admin rights on Windows (needed for WSL operations)
    if sys.platform == "win32":
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False
        # Don't force admin — just warn if not present

    app = MirAILauncher()
    app.protocol("WM_DELETE_WINDOW", app._on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
