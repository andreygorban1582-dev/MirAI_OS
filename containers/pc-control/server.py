"""
MirAI PC Control  –  Full desktop control via pynput + pyautogui
REST API for mouse, keyboard, screen-capture, and application launch.
"""

import base64
import io
import logging
import os
import subprocess

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mirai.pc_control")

DISPLAY = os.getenv("DISPLAY", ":0")
os.environ.setdefault("DISPLAY", DISPLAY)

app = FastAPI(title="MirAI PC Control", version="2.0.0")

# ─── pynput controllers ───────────────────────────────────────────────────────
try:
    from pynput import keyboard as kb
    from pynput import mouse as ms
    _keyboard  = kb.Controller()
    _mouse     = ms.Controller()
    _pynput_ok = True
except Exception as exc:
    logger.warning("[PCControl] pynput unavailable: %s", exc)
    _pynput_ok = False


# ─── Request models ───────────────────────────────────────────────────────────

class MouseMoveReq(BaseModel):
    x: int
    y: int
    absolute: bool = True


class MouseClickReq(BaseModel):
    button: str = "left"
    double: bool = False


class MouseScrollReq(BaseModel):
    dx: int = 0
    dy: int = -3


class KeyPressReq(BaseModel):
    key: str
    modifiers: list[str] = []


class TypeTextReq(BaseModel):
    text: str


class RunCmdReq(BaseModel):
    command: str
    shell: bool = True


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "pynput": _pynput_ok, "display": DISPLAY}


@app.post("/mouse/move")
async def mouse_move(req: MouseMoveReq) -> dict:
    if not _pynput_ok:
        raise HTTPException(503, "pynput not available")
    if req.absolute:
        _mouse.position = (req.x, req.y)
    else:
        _mouse.move(req.x, req.y)
    return {"moved": [req.x, req.y]}


@app.post("/mouse/click")
async def mouse_click(req: MouseClickReq) -> dict:
    if not _pynput_ok:
        raise HTTPException(503, "pynput not available")
    btn_map = {
        "left":   ms.Button.left,
        "right":  ms.Button.right,
        "middle": ms.Button.middle,
    }
    btn = btn_map.get(req.button, ms.Button.left)
    if req.double:
        _mouse.click(btn, 2)
    else:
        _mouse.click(btn)
    return {"clicked": req.button}


@app.post("/mouse/scroll")
async def mouse_scroll(req: MouseScrollReq) -> dict:
    if not _pynput_ok:
        raise HTTPException(503, "pynput not available")
    _mouse.scroll(req.dx, req.dy)
    return {"scrolled": [req.dx, req.dy]}


@app.post("/keyboard/press")
async def key_press(req: KeyPressReq) -> dict:
    if not _pynput_ok:
        raise HTTPException(503, "pynput not available")
    mod_map = {
        "ctrl":  kb.Key.ctrl,
        "shift": kb.Key.shift,
        "alt":   kb.Key.alt,
        "super": kb.Key.cmd,
    }
    mods = [mod_map[m] for m in req.modifiers if m in mod_map]
    try:
        key = getattr(kb.Key, req.key, req.key)
    except Exception:
        key = req.key
    with _keyboard.pressed(*mods):
        _keyboard.press(key)
        _keyboard.release(key)
    return {"pressed": req.key, "modifiers": req.modifiers}


@app.post("/keyboard/type")
async def type_text(req: TypeTextReq) -> dict:
    if not _pynput_ok:
        raise HTTPException(503, "pynput not available")
    _keyboard.type(req.text)
    return {"typed": len(req.text)}


@app.get("/screen/capture")
async def screen_capture() -> Response:
    """Returns a PNG screenshot encoded as base64."""
    try:
        import pyautogui
        buf = io.BytesIO()
        screenshot = pyautogui.screenshot()
        screenshot.save(buf, format="PNG")
        data = base64.b64encode(buf.getvalue()).decode()
        return Response(
            content=data,
            media_type="text/plain",
            headers={"X-Image-Format": "png-base64"},
        )
    except Exception as exc:
        raise HTTPException(500, f"Screenshot failed: {exc}")


@app.post("/run")
async def run_command(req: RunCmdReq) -> dict:
    try:
        result = subprocess.run(
            req.command,
            shell=req.shell,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-4096:],
            "stderr": result.stderr[-2048:],
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Command timed out")
    except Exception as exc:
        raise HTTPException(500, str(exc))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8500)
