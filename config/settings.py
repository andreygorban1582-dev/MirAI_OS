"""
MirAI_OS Configuration Settings
Pydantic-based settings with Legion Go hardware profile support.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


class LegionGoProfile:
    """Legion Go hardware profile loader."""

    _profile: dict | None = None

    @classmethod
    def load(cls) -> dict:
        if cls._profile is None:
            profile_path = CONFIG_DIR / "legion_go_profile.json"
            with open(profile_path) as f:
                cls._profile = json.load(f)
        return cls._profile

    @classmethod
    def get(cls, *keys: str, default=None):
        data = cls.load()
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, default)
            else:
                return default
        return data


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenRouter / LLM
    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    default_model: str = Field(default="mistralai/mistral-7b-instruct")

    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # HuggingFace
    huggingface_token: str = Field(default="")

    # Hardware Profile
    hardware_profile: Literal["legion_go", "generic", "high_end", "low_end"] = Field(
        default="legion_go"
    )
    legion_go_enabled: bool = Field(default=True)
    amd_rocm_enabled: bool = Field(default=True)
    rocm_home: str = Field(default="/opt/rocm")

    # AI Performance
    max_context_tokens: int = Field(default=4096)
    gpu_layers: int = Field(default=20)
    cpu_threads: int = Field(default=8)
    quantization: str = Field(default="Q4_K_M")

    # Voice
    voice_enabled: bool = Field(default=True)
    voice_sample_rate: int = Field(default=22050)
    voice_language: str = Field(default="en")

    # Lab
    lab_enabled: bool = Field(default=True)
    lab_port: int = Field(default=7860)

    # Kali Integration
    kali_ssh_host: str = Field(default="")
    kali_ssh_user: str = Field(default="")
    kali_ssh_key_path: str = Field(default="")

    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/mirai.log")

    # Codespace SSH
    codespace_ssh_host: str = Field(default="")
    codespace_ssh_user: str = Field(default="")
    codespace_ssh_key: str = Field(default="")

    def legion_go_ai_settings(self) -> dict:
        """Return AI performance settings tuned for Legion Go."""
        if self.hardware_profile == "legion_go":
            profile = LegionGoProfile.load()
            return profile.get("ai_performance", {})
        return {
            "max_context_tokens": self.max_context_tokens,
            "gpu_layers": self.gpu_layers,
            "cpu_threads": self.cpu_threads,
            "quantization": self.quantization,
        }


settings = Settings()
