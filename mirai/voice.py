"""
mirai/voice.py
──────────────
Voice I/O – Text-to-Speech & Speech Recognition
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Text-to-Speech (TTS): converts MirAI's text replies into spoken audio using
  the Coqui TTS library (compatible with Sesame CSM-style models).
• Speech-to-Text (STT): captures audio from the microphone, detects silence
  to stop recording, then uses Google's speech recognition (offline-capable
  via Vosk in the future) to transcribe it.
• Both features are guarded by VOICE_ENABLED=true so the agent runs silently
  by default on headless servers.

Dependencies (installed by requirements.txt)
────────────────────────────────────────────
  TTS       – Coqui TTS (tts package)
  pyaudio   – microphone access
  SpeechRecognition – STT engine wrapper

Notes on WSL2
─────────────
WSL2 does not forward PulseAudio by default.  The install script configures
PulseAudio TCP forwarding so audio works transparently.
"""

from __future__ import annotations

import io
import wave
from typing import Optional

from loguru import logger

from mirai.settings import settings

# Guard heavy imports so the rest of the package still loads even when voice
# dependencies are not installed.
_tts_available = False
_sr_available = False

try:
    from TTS.api import TTS as CoquiTTS  # noqa: N811

    _tts_available = True
except ImportError:
    logger.debug("TTS library not installed – text-to-speech disabled.")

try:
    import speech_recognition as sr  # noqa: N813

    _sr_available = True
except ImportError:
    logger.debug("SpeechRecognition library not installed – STT disabled.")

try:
    import pyaudio  # noqa: F401

    _pyaudio_available = True
except ImportError:
    _pyaudio_available = False


class VoiceIO:
    """
    Handles microphone input and speaker output for MirAI.

    Parameters
    ----------
    tts_model : str, optional
        Coqui TTS model name.  Defaults to settings.voice_tts_model.
    language : str, optional
        Language code for STT (e.g. "en-US").
    """

    def __init__(
        self,
        tts_model: str | None = None,
        language: str = "en-US",
    ) -> None:
        self._enabled = settings.voice_enabled
        self._language = language
        self._tts: Optional[object] = None
        self._recogniser = None

        if not self._enabled:
            logger.info("Voice I/O is disabled (VOICE_ENABLED=false).")
            return

        # Initialise TTS
        if _tts_available:
            model_name = tts_model or settings.voice_tts_model
            try:
                self._tts = CoquiTTS(model_name=model_name, progress_bar=False)
                logger.info(f"TTS engine ready: {model_name}")
            except Exception as exc:
                logger.warning(f"TTS init failed: {exc}")
        else:
            logger.warning("TTS library missing – install 'TTS' package.")

        # Initialise STT recogniser
        if _sr_available:
            self._recogniser = sr.Recognizer()
            logger.info("Speech recogniser ready.")
        else:
            logger.warning("SpeechRecognition library missing.")

    # ── Text → Speech ─────────────────────────────────────────────────────────

    def speak(self, text: str) -> bool:
        """
        Convert `text` to speech and play it on the default audio output.

        Returns True on success.
        """
        if not self._enabled or not self._tts:
            return False
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            self._tts.tts_to_file(text=text, file_path=tmp_path)  # type: ignore[union-attr]
            self._play_wav(tmp_path)
            import os as _os
            _os.unlink(tmp_path)
            return True
        except Exception as exc:
            logger.error(f"speak() failed: {exc}")
            return False

    def _play_wav(self, path: str) -> None:
        """Play a WAV file using PyAudio."""
        if not _pyaudio_available:
            logger.warning("PyAudio not installed – cannot play audio.")
            return
        import pyaudio as pa  # noqa: PLC0415 – deferred to avoid ImportError on headless systems

        with wave.open(path, "rb") as wf:
            p = pa.PyAudio()
            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
            )
            chunk = 1024
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)
            stream.stop_stream()
            stream.close()
            p.terminate()

    # ── Speech → Text ─────────────────────────────────────────────────────────

    def listen(self) -> Optional[str]:
        """
        Record audio from the microphone until silence is detected, then
        transcribe and return the text string.

        Returns None if transcription failed or voice is disabled.
        """
        if not self._enabled or not self._recogniser or not _pyaudio_available:
            return None

        # Use the module-level sr alias (already imported at top of file under guard)
        if not _sr_available:
            return None
        import speech_recognition as sr  # noqa: PLC0415 – deferred for headless envs

        recogniser: sr.Recognizer = self._recogniser  # type: ignore[assignment]
        try:
            with sr.Microphone() as source:
                recogniser.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("Listening…")
                audio = recogniser.listen(source, timeout=10, phrase_time_limit=30)
            text = recogniser.recognize_google(audio, language=self._language)
            logger.info(f"Heard: {text}")
            return text
        except sr.WaitTimeoutError:
            logger.debug("No speech detected within timeout.")
            return None
        except sr.UnknownValueError:
            logger.debug("Speech not understood.")
            return None
        except Exception as exc:
            logger.error(f"listen() failed: {exc}")
            return None

    @property
    def is_enabled(self) -> bool:
        return self._enabled
