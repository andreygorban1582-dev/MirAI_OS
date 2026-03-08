"""OpenClaw agent API – exposes game-env controls for MirAI agents."""

import subprocess
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="MirAI OpenClaw Agent", version="2.0.0")

OPENCLAW_BIN = "/app/openclaw/build/OpenClaw"


class ActionRequest(BaseModel):
    action: str
    params: dict = {}


@app.get("/health")
async def health() -> dict:
    import os
    return {"status": "ok", "binary": os.path.exists(OPENCLAW_BIN)}


@app.post("/action")
async def action(req: ActionRequest) -> dict:
    """Dispatch a game action (stub – extend for RL loop)."""
    return {"action": req.action, "result": "ok", "params": req.params}


@app.post("/launch")
async def launch() -> dict:
    """Launch OpenClaw with virtual framebuffer."""
    try:
        subprocess.Popen(
            ["Xvfb", ":99", "-screen", "0", "800x600x24"],
            close_fds=True,
        )
        import os
        os.environ["DISPLAY"] = ":99"
        subprocess.Popen([OPENCLAW_BIN], env=os.environ.copy(), close_fds=True)
        return {"status": "launched"}
    except FileNotFoundError:
        return {"status": "binary_not_found"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8200)
