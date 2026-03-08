"""CSM Speech Synthesis – REST wrapper for Sesame AI CSM."""

import io
import os
import sys
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

logger = logging.getLogger("mirai.csm")
logging.basicConfig(level=logging.INFO)

CSM_DIR = Path("/app/csm")
MODEL_DIR = Path("/app/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Add CSM to path
sys.path.insert(0, str(CSM_DIR))

app = FastAPI(title="MirAI CSM Speech", version="2.0.0")

_pipeline = None


def _load_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    try:
        # CSM uses a generator pattern; try to import
        from generator import load_csm_1b  # type: ignore
        import torchaudio
        device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
        _pipeline = load_csm_1b(device=device)
        logger.info("[CSM] Pipeline loaded on %s", device)
    except ImportError:
        logger.warning("[CSM] CSM generator not found; using edge-tts fallback")
        _pipeline = "edge-tts"
    return _pipeline


class SpeakRequest(BaseModel):
    text: str
    speaker_id: int = 0
    sample_rate: int = 24000


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/speak")
async def speak(req: SpeakRequest) -> Response:
    pipeline = _load_pipeline()

    if pipeline == "edge-tts":
        # Fallback: edge-tts
        try:
            import edge_tts
            import asyncio
            tts = edge_tts.Communicate(req.text, voice="en-US-AriaNeural")
            buf = io.BytesIO()
            async for chunk in tts.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
            return Response(content=buf.getvalue(), media_type="audio/mpeg")
        except Exception as exc:
            raise HTTPException(500, f"TTS error: {exc}")

    # CSM path
    try:
        import torch
        from generator import Segment  # type: ignore
        audio = pipeline.generate(
            text=req.text,
            speaker=req.speaker_id,
            context=[],
            max_audio_length_ms=30000,
        )
        buf = io.BytesIO()
        import torchaudio
        torchaudio.save(buf, audio.unsqueeze(0).cpu(), req.sample_rate, format="wav")
        return Response(content=buf.getvalue(), media_type="audio/wav")
    except Exception as exc:
        logger.error("[CSM] generate error: %s", exc)
        raise HTTPException(500, str(exc))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8300)
