"""faster-whisper-plus  –  REST wrapper for real-time STT."""

import io
import logging
import os
import tempfile
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("mirai.whisper")
logging.basicConfig(level=logging.INFO)

MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
DEVICE     = os.getenv("WHISPER_DEVICE", "auto")
COMPUTE    = os.getenv("WHISPER_COMPUTE", "int8")
MODEL_DIR  = Path("/app/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MirAI Whisper STT", version="2.0.0")

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        # Try faster-whisper-plus first
        import sys
        sys.path.insert(0, "/app/whisper_plus")
        from faster_whisper import WhisperModel  # type: ignore
        device = "cuda" if DEVICE == "auto" and _cuda_available() else "cpu"
        _model = WhisperModel(
            MODEL_SIZE,
            device=device,
            compute_type=COMPUTE,
            download_root=str(MODEL_DIR),
        )
        logger.info("[Whisper] model '%s' loaded on %s", MODEL_SIZE, device)
    except Exception as exc:
        logger.error("[Whisper] load error: %s", exc)
        _model = None
    return _model


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


@app.on_event("startup")
async def startup() -> None:
    _load_model()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "model": MODEL_SIZE}


@app.post("/transcribe")
async def transcribe(request: Request) -> JSONResponse:
    """
    Accepts raw WAV/MP3 bytes in the request body.
    Returns {"text": "<transcription>", "language": "<lang>"}
    """
    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(400, "No audio data")

    model = _load_model()
    if model is None:
        raise HTTPException(503, "Whisper model not loaded")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments, info = model.transcribe(tmp_path, beam_size=5)
        text = " ".join(seg.text for seg in segments).strip()
        return JSONResponse({
            "text": text,
            "language": info.language,
            "probability": info.language_probability,
        })
    except Exception as exc:
        logger.error("[Whisper] transcribe error: %s", exc)
        raise HTTPException(500, str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8400)
