#!/usr/bin/env python3
"""
user_profiles.py – MirAI_OS User Profile Settings
===================================================
Manages per-user persistent preferences such as preferred persona,
TTS voice, LLM temperature, and display options.

Profiles are stored as JSON in ``profiles.json`` (configurable via the
``PROFILES_FILE`` environment variable). Each profile is keyed by a
unique user identifier – the Telegram user_id (as a string) in bot mode,
or a custom name (default ``"cli"``) in CLI mode.

Usage example::

    from user_profiles import ProfileManager

    mgr = ProfileManager()

    # Load or create a profile
    profile = mgr.get("12345678")

    # Update a single setting
    mgr.set("12345678", preferred_persona="L Lawliet")

    # Persist changes
    mgr.save()
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("MirAI_Lab.profiles")

# Default path – can be overridden via environment variable
_DEFAULT_PROFILES_FILE = os.getenv("PROFILES_FILE", "profiles.json")

# ---------------------------------------------------------------------------
# Dataclass – one per user
# ---------------------------------------------------------------------------

@dataclass
class UserProfile:
    """All per-user settings for MirAI_OS."""

    user_id: str = "cli"

    # Persona / LLM preferences
    preferred_persona: Optional[str] = None   # None → let orchestrator decide
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048

    # Voice preferences
    use_voice: bool = False                   # TTS enabled for this user
    tts_voice: str = "en-US-GuyNeural"        # edge-tts voice name

    # Display preferences
    language: str = "en"                      # BCP-47 language tag
    verbose_responses: bool = False           # include reasoning trace

    # Meta
    display_name: str = ""                    # friendly name shown in greetings

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def summary(self) -> str:
        """Return a human-readable summary of this profile."""
        lines = [
            f"👤 Profile: {self.display_name or self.user_id}",
            f"🎭 Preferred persona : {self.preferred_persona or 'auto (orchestrator decides)'}",
            f"🌡  LLM temperature   : {self.llm_temperature}",
            f"📝 Max tokens        : {self.llm_max_tokens}",
            f"🔊 Voice output      : {'on' if self.use_voice else 'off'} ({self.tts_voice})",
            f"🌐 Language          : {self.language}",
            f"🔍 Verbose responses : {'on' if self.verbose_responses else 'off'}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Profile manager
# ---------------------------------------------------------------------------

class ProfileManager:
    """
    Load, update, and persist user profiles.

    All changes are written to *profiles_file* automatically when
    :meth:`save` is called.  Use :meth:`set` to update individual fields
    and :meth:`get` to retrieve (or auto-create) a profile.
    """

    def __init__(self, profiles_file: str = _DEFAULT_PROFILES_FILE):
        self._path = Path(profiles_file)
        self._profiles: Dict[str, UserProfile] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, user_id: str) -> UserProfile:
        """Return the profile for *user_id*, creating a default one if absent."""
        user_id = str(user_id)
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
            self.save()
        return self._profiles[user_id]

    def set(self, user_id: str, **kwargs: Any) -> UserProfile:
        """
        Update one or more fields in the user's profile.

        Unrecognised field names are silently ignored so that callers can
        pass arbitrary kwargs without raising exceptions.

        Returns the updated :class:`UserProfile`.
        """
        user_id = str(user_id)
        profile = self.get(user_id)
        valid_fields = set(UserProfile.__dataclass_fields__)  # type: ignore[attr-defined]
        for key, value in kwargs.items():
            if key in valid_fields and key != "user_id":
                try:
                    # Coerce to the declared type
                    field_type = UserProfile.__dataclass_fields__[key].type  # type: ignore[attr-defined]
                    if field_type in ("float", float):
                        value = float(value)
                    elif field_type in ("int", int):
                        value = int(value)
                    elif field_type in ("bool", bool):
                        if isinstance(value, str):
                            value = value.lower() in ("1", "true", "yes", "on")
                        else:
                            value = bool(value)
                    setattr(profile, key, value)
                except (ValueError, TypeError) as exc:
                    logger.warning("Profile field %r: bad value %r – %s", key, value, exc)
        self.save()
        return profile

    def delete(self, user_id: str) -> bool:
        """Remove a profile.  Returns True if it existed, False otherwise."""
        user_id = str(user_id)
        existed = user_id in self._profiles
        self._profiles.pop(user_id, None)
        if existed:
            self.save()
        return existed

    def all_profiles(self) -> Dict[str, UserProfile]:
        """Return a read-only view of all stored profiles."""
        return dict(self._profiles)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Write all profiles to *profiles_file*."""
        try:
            data = {uid: p.to_dict() for uid, p in self._profiles.items()}
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.error("Could not save profiles to %s: %s", self._path, exc)

    def _load(self) -> None:
        """Load profiles from *profiles_file* if it exists."""
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for uid, data in raw.items():
                try:
                    self._profiles[uid] = UserProfile.from_dict(data)
                except (TypeError, KeyError) as exc:
                    logger.warning("Skipping malformed profile %r: %s", uid, exc)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Could not load profiles from %s: %s", self._path, exc)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Return the module-level singleton :class:`ProfileManager`."""
    global _default_manager
    if _default_manager is None:
        _default_manager = ProfileManager()
    return _default_manager
