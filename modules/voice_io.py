"""
Voice I/O Module – Speech recognition + text-to-speech for MirAI_OS.
Supports pyttsx3 (offline) and gTTS (online) for output,
and SpeechRecognition for input.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Optional

import config

logger = logging.getLogger(__name__)


class VoiceIO:
    """Provides push-to-talk input and TTS output."""

    def __init__(self) -> None:
        self.enabled = config.VOICE_ENABLED
        self._tts_engine: Optional[object] = None
        self._listen_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._audio_queue: queue.Queue = queue.Queue()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self, on_speech: Callable[[str], None]) -> None:
        """Start background listening thread."""
        if not self.enabled:
            logger.info("Voice I/O disabled via config.")
            return
        self._stop_event.clear()
        self._listen_thread = threading.Thread(
            target=self._listen_loop, args=(on_speech,), daemon=True
        )
        self._listen_thread.start()
        logger.info("Voice I/O started.")

    def stop(self) -> None:
        self._stop_event.set()

    # ── TTS ───────────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Convert text to speech."""
        if not self.enabled:
            return
        if config.TTS_ENGINE == "gtts":
            self._speak_gtts(text)
        else:
            self._speak_pyttsx3(text)

    def _speak_pyttsx3(self, text: str) -> None:
        try:
            import pyttsx3  # type: ignore

            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as exc:
            logger.error("pyttsx3 TTS error: %s", exc)

    def _speak_gtts(self, text: str) -> None:
        try:
            import os
            import tempfile

            from gtts import gTTS  # type: ignore
            import playsound  # type: ignore

            tts = gTTS(text=text, lang=config.VOICE_LANG.split("-")[0])
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                tmp = f.name
            tts.save(tmp)
            playsound.playsound(tmp)
            os.unlink(tmp)
        except Exception as exc:
            logger.error("gTTS error: %s", exc)

    # ── STT ───────────────────────────────────────────────────────────────────

    def _listen_loop(self, on_speech: Callable[[str], None]) -> None:
        try:
            import speech_recognition as sr  # type: ignore

            recognizer = sr.Recognizer()
            mic = sr.Microphone()
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Microphone calibrated. Listening…")
            while not self._stop_event.is_set():
                with mic as source:
                    try:
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                        text = recognizer.recognize_google(audio, language=config.VOICE_LANG)
                        logger.debug("Heard: %s", text)
                        on_speech(text)
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except Exception as exc:
                        logger.warning("STT error: %s", exc)
        except ImportError:
            logger.error("speech_recognition not installed – voice input disabled.")
        except Exception as exc:
            logger.error("Voice listen loop error: %s", exc)
