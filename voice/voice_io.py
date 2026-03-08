"""
Voice I/O — MirAI_OS
Speech-to-text (STT) and text-to-speech (TTS) using Sesame CSM voice model.
Optimised for Legion Go's APU (AMD Radeon 780M, ROCm).
"""
from __future__ import annotations

import asyncio
import io
import queue
import threading
from pathlib import Path
from typing import Optional

from config.settings import settings


class VoiceIO:
    """
    Async-friendly voice input/output handler.

    STT: OpenAI Whisper (via transformers or openai-whisper)
    TTS: Sesame CSM or fallback to system TTS (pyttsx3)
    """

    def __init__(
        self,
        sample_rate: int = 22050,
        language: str = "en",
    ) -> None:
        self.sample_rate = sample_rate
        self.language = language
        self._stt_model = None
        self._tts_engine = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._recording = False

    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------

    def _load_stt(self) -> None:
        if self._stt_model is not None:
            return
        try:
            import whisper  # noqa: PLC0415
            # Use small model to stay within Legion Go 16 GB RAM budget
            self._stt_model = whisper.load_model("small")
        except ImportError:
            pass

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file to text."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_transcribe, audio_path)

    def _sync_transcribe(self, audio_path: str) -> str:
        self._load_stt()
        if self._stt_model is None:
            return "[STT not available — install openai-whisper]"
        result = self._stt_model.transcribe(audio_path, language=self.language)
        return result.get("text", "").strip()

    async def record_and_transcribe(self, duration_sec: float = 5.0) -> str:
        """Record microphone audio and transcribe it."""
        audio_path = await self._record(duration_sec)
        return await self.transcribe(audio_path)

    async def _record(self, duration_sec: float) -> str:
        """Record audio from the default microphone and save to a temp file."""
        import tempfile  # noqa: PLC0415
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_record, duration_sec
        )

    def _sync_record(self, duration_sec: float) -> str:
        import tempfile  # noqa: PLC0415
        try:
            import sounddevice as sd  # noqa: PLC0415
            import soundfile as sf  # noqa: PLC0415
            import numpy as np  # noqa: PLC0415
        except ImportError:
            return ""
        frames = sd.rec(
            int(duration_sec * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, frames, self.sample_rate)
            return tmp.name

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    async def speak(self, text: str, output_path: Optional[str] = None) -> Optional[str]:
        """Convert text to speech. Returns path to the audio file if saved."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_speak, text, output_path)

    def _sync_speak(self, text: str, output_path: Optional[str]) -> Optional[str]:
        # Try Sesame CSM first (HuggingFace)
        result = self._sesame_tts(text, output_path)
        if result:
            return result
        # Fallback to pyttsx3
        return self._pyttsx3_speak(text)

    def _sesame_tts(self, text: str, output_path: Optional[str]) -> Optional[str]:
        """Attempt Sesame CSM voice synthesis via HuggingFace pipeline."""
        try:
            from transformers import pipeline  # noqa: PLC0415
            import soundfile as sf  # noqa: PLC0415
            import numpy as np  # noqa: PLC0415
            import tempfile  # noqa: PLC0415

            tts = pipeline(
                "text-to-speech",
                model="sesame/csm-1b",
                token=settings.huggingface_token or None,
                device=self._get_device(),
            )
            output = tts(text)
            audio = output["audio"]
            sr = output.get("sampling_rate", self.sample_rate)
            path = output_path
            if path is None:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    path = tmp.name
            sf.write(path, np.array(audio).squeeze(), sr)
            return path
        except Exception:  # noqa: BLE001
            return None

    def _pyttsx3_speak(self, text: str) -> None:
        try:
            import pyttsx3  # noqa: PLC0415
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception:  # noqa: BLE001
            pass
        return None

    @staticmethod
    def _get_device() -> str:
        """Pick cuda/rocm device if available, else cpu."""
        try:
            import torch  # noqa: PLC0415
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"
