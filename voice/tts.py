"""
MirAI OS — Text To Speech
Primary: Sesame CSM (Character AI's open-source conversational speech model)
Fallback: pyttsx3 (offline) or espeak
Outputs OGG/Opus for Telegram voice messages.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

from core.config import cfg

logger = logging.getLogger("mirai.voice.tts")

_csm_model = None
_csm_generator = None


def _load_csm():
    """Load Sesame CSM model (lazily)."""
    global _csm_model, _csm_generator
    if _csm_generator is not None:
        return _csm_generator
    try:
        # Sesame CSM from https://github.com/SesameAILabs/csm
        import sys
        csm_path = Path(cfg.voice.get("tts", {}).get("model_path", "./data/models/csm"))
        if str(csm_path) not in sys.path:
            sys.path.insert(0, str(csm_path))
        from generator import load_csm_1b, Segment
        import torch
        device = "cuda" if _is_cuda_available() else "cpu"
        logger.info(f"Loading Sesame CSM on {device}...")
        _csm_generator = load_csm_1b(device=device)
        logger.info("Sesame CSM loaded.")
        return _csm_generator
    except Exception as e:
        logger.warning(f"Sesame CSM not available: {e}. Using fallback TTS.")
        return None


def _is_cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


async def synthesize(text: str, voice_context: Optional[list] = None) -> Optional[str]:
    """
    Convert text to speech. Returns path to OGG file for Telegram.
    """
    # Truncate very long responses for voice (summarize instead)
    if len(text) > 800:
        text = _truncate_for_voice(text)

    # Try Sesame CSM first
    audio_path = await _synthesize_csm(text)
    if audio_path:
        return audio_path

    # Fallback: pyttsx3
    audio_path = await _synthesize_pyttsx3(text)
    if audio_path:
        return audio_path

    # Fallback: espeak
    audio_path = await _synthesize_espeak(text)
    return audio_path


async def _synthesize_csm(text: str) -> Optional[str]:
    """Synthesize with Sesame CSM."""
    try:
        gen = await asyncio.to_thread(_load_csm)
        if not gen:
            return None

        import torch
        from generator import Segment

        # Generate audio
        audio_tensor = await asyncio.to_thread(
            gen.generate,
            text=text,
            speaker=0,
            context=[],
            max_audio_length_ms=30000,
        )

        sample_rate = gen.sample_rate

        # Save as WAV, then convert to OGG
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        import torchaudio
        torchaudio.save(wav_path, audio_tensor.unsqueeze(0).cpu(), sample_rate)

        ogg_path = wav_path.replace(".wav", ".ogg")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", wav_path,
            "-c:a", "libopus", "-b:a", "24k",
            ogg_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        Path(wav_path).unlink(missing_ok=True)

        if Path(ogg_path).exists():
            return ogg_path
        return None
    except Exception as e:
        logger.debug(f"CSM synthesis error: {e}")
        return None


async def _synthesize_pyttsx3(text: str) -> Optional[str]:
    """Fallback: pyttsx3 local TTS."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        def _generate():
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 160)
            engine.setProperty("volume", 0.9)
            engine.save_to_file(text, wav_path)
            engine.runAndWait()

        await asyncio.to_thread(_generate)

        # Convert to OGG
        ogg_path = wav_path.replace(".wav", ".ogg")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", wav_path,
            "-c:a", "libopus", "-b:a", "24k", ogg_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        Path(wav_path).unlink(missing_ok=True)

        if Path(ogg_path).exists():
            return ogg_path
        return None
    except Exception as e:
        logger.debug(f"pyttsx3 fallback error: {e}")
        return None


async def _synthesize_espeak(text: str) -> Optional[str]:
    """Fallback: espeak-ng."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        proc = await asyncio.create_subprocess_exec(
            "espeak-ng", "-w", wav_path, text,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        ogg_path = wav_path.replace(".wav", ".ogg")
        proc2 = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", wav_path,
            "-c:a", "libopus", "-b:a", "24k", ogg_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc2.wait()
        Path(wav_path).unlink(missing_ok=True)

        if Path(ogg_path).exists():
            return ogg_path
        return None
    except Exception as e:
        logger.debug(f"espeak fallback error: {e}")
        return None


def _truncate_for_voice(text: str, max_chars: int = 800) -> str:
    """Keep voice responses concise — strip markdown and truncate."""
    import re
    # Remove markdown formatting
    clean = re.sub(r"```[\s\S]*?```", "[code block]", text)
    clean = re.sub(r"`[^`]+`", "", clean)
    clean = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", clean)
    clean = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", clean)
    clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
    clean = re.sub(r"#{1,6}\s", "", clean)
    # Truncate
    if len(clean) > max_chars:
        clean = clean[:max_chars].rsplit(".", 1)[0] + "."
    return clean.strip()
