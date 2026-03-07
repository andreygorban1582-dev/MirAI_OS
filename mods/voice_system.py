"""
MirAI_OS Voice System
Text-to-speech and speech-to-text for hands-free use on the Legion Go.
"""

import logging
import threading
from typing import Callable, Optional


logger = logging.getLogger(__name__)


class VoiceSystem:
    """Handles microphone input (STT) and speaker output (TTS)."""

    def __init__(self, config=None) -> None:
        self.config = config or {}
        self.tts_engine: str = self.config.get("tts_engine", "pyttsx3")
        self.stt_engine: str = self.config.get("stt_engine", "whisper")
        self.whisper_model: str = self.config.get("whisper_model", "base")
        self._tts = None
        self._whisper = None
        self._listening = False
        self._listen_thread: Optional[threading.Thread] = None
        self._on_transcript: Optional[Callable[[str], None]] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._init_tts()
        self._init_stt()
        logger.info("VoiceSystem started (TTS: %s, STT: %s).", self.tts_engine, self.stt_engine)

    def stop(self) -> None:
        self._listening = False
        if self._listen_thread and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=3)
        logger.info("VoiceSystem stopped.")

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    def _init_tts(self) -> None:
        try:
            import pyttsx3  # type: ignore

            self._tts = pyttsx3.init()
            rate = self.config.get("tts_rate", 185)
            self._tts.setProperty("rate", rate)
            logger.info("pyttsx3 TTS ready (rate=%d).", rate)
        except Exception as exc:
            logger.warning("pyttsx3 not available: %s. Install: pip install pyttsx3", exc)

    def speak(self, text: str) -> None:
        """Convert *text* to speech (blocking)."""
        if self._tts:
            try:
                self._tts.say(text)
                self._tts.runAndWait()
            except Exception as exc:
                logger.error("TTS error: %s", exc)
        else:
            print(f"[SPEAK] {text}")

    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------

    def _init_stt(self) -> None:
        if self.stt_engine == "whisper":
            try:
                import whisper  # type: ignore

                self._whisper = whisper.load_model(self.whisper_model)
                logger.info("Whisper STT ready (model=%s).", self.whisper_model)
            except Exception as exc:
                logger.warning(
                    "whisper not available: %s. Install: pip install openai-whisper", exc
                )

    def on_transcript(self, callback: Callable[[str], None]) -> None:
        """Register a callback that receives transcribed text."""
        self._on_transcript = callback

    def listen_async(self) -> None:
        """Start listening in a background thread."""
        if self._listening:
            return
        self._listening = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
        logger.info("Listening for voice input…")

    def _listen_loop(self) -> None:
        try:
            import speech_recognition as sr  # type: ignore

            recogniser = sr.Recognizer()
            mic = sr.Microphone()
            with mic as source:
                recogniser.adjust_for_ambient_noise(source, duration=0.5)
            while self._listening:
                with mic as source:
                    audio = recogniser.listen(source, timeout=5, phrase_time_limit=15)
                transcript = self._transcribe(audio)
                if transcript and self._on_transcript:
                    self._on_transcript(transcript)
        except Exception as exc:
            logger.error("Voice listen loop error: %s", exc)

    def _transcribe(self, audio) -> Optional[str]:
        if self._whisper:
            try:
                import os
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio.get_wav_data())
                    path = f.name
                try:
                    result = self._whisper.transcribe(path)
                    return result.get("text", "").strip()
                finally:
                    os.unlink(path)
            except Exception as exc:
                logger.error("Whisper transcription error: %s", exc)
        return None
