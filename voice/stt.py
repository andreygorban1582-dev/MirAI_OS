"""
MirAI OS — Speech To Text
Uses OpenAI Whisper (local, free) to transcribe voice messages.
Supports OGG (Telegram), WAV, MP3.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

from core.config import cfg

logger = logging.getLogger("mirai.voice.stt")

_whisper_model = None


def _load_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    try:
        import whisper
        model_size = cfg.voice.get("stt", {}).get("model_size", "base")
        device = cfg.voice.get("stt", {}).get("device", "cpu")
        logger.info(f"Loading Whisper model '{model_size}' on {device}...")
        _whisper_model = whisper.load_model(model_size, device=device)
        logger.info("Whisper model loaded.")
        return _whisper_model
    except ImportError:
        logger.error("whisper not installed. Run: pip install openai-whisper")
        return None
    except Exception as e:
        logger.error(f"Whisper load failed: {e}")
        return None


async def transcribe(audio_path: str) -> str:
    """
    Transcribe audio file to text.
    Converts OGG/other formats to WAV via ffmpeg first if needed.
    """
    path = Path(audio_path)
    if not path.exists():
        return ""

    # Convert OGG to WAV if needed (Telegram sends OGG)
    if path.suffix.lower() in (".ogg", ".oga", ".mp3", ".m4a"):
        wav_path = path.with_suffix(".wav")
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-i", str(path), str(wav_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if wav_path.exists():
                path = wav_path
        except FileNotFoundError:
            logger.warning("ffmpeg not found — trying to transcribe OGG directly")

    try:
        model = await asyncio.to_thread(_load_model)
        if not model:
            return await _fallback_transcribe(str(path))

        lang = cfg.voice.get("stt", {}).get("language", "auto")
        kwargs = {} if lang == "auto" else {"language": lang}

        result = await asyncio.to_thread(model.transcribe, str(path), **kwargs)
        text = result.get("text", "").strip()
        logger.info(f"STT result: {text[:100]}")
        return text
    except Exception as e:
        logger.error(f"STT error: {e}")
        return ""
    finally:
        # Cleanup converted file
        if path.suffix == ".wav" and path != Path(audio_path):
            path.unlink(missing_ok=True)


async def _fallback_transcribe(audio_path: str) -> str:
    """Fallback: try using vosk or return empty string."""
    logger.warning("Whisper unavailable, trying vosk fallback...")
    try:
        import vosk
        import wave
        import json
        model = vosk.Model(lang="en-us")
        rec = vosk.KaldiRecognizer(model, 16000)
        with wave.open(audio_path, "rb") as wf:
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                rec.AcceptWaveform(data)
        result = json.loads(rec.FinalResult())
        return result.get("text", "")
    except Exception as e:
        logger.error(f"Vosk fallback failed: {e}")
        return ""
