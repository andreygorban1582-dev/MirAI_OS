"""
Context Optimizer — Legion Go Hardware-Aware Memory and Context Management

Dynamically adjusts context window size, caches embeddings, and manages
available RAM/VRAM on the Lenovo Legion Go (16 GB RAM, AMD 780M iGPU).
"""
from __future__ import annotations

import gc
import os
import platform
import threading
from dataclasses import dataclass, field
from typing import Optional

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

from config.settings import settings, LegionGoProfile


@dataclass
class HardwareSnapshot:
    """Current hardware utilisation snapshot."""

    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    ram_used_pct: float = 0.0
    cpu_cores: int = 1
    cpu_freq_mhz: float = 0.0
    gpu_name: str = "unknown"
    gpu_vram_mb: int = 0
    platform: str = "unknown"
    is_legion_go: bool = False


@dataclass
class ContextBudget:
    """Derived context allocation for the current run."""

    max_tokens: int = 4096
    max_history_turns: int = 20
    embedding_cache_size: int = 500
    batch_size: int = 4
    gpu_layers: int = 0


class ContextOptimizer:
    """
    Monitors system resources and produces an optimal ContextBudget.

    Specifically tuned for Legion Go constraints:
    - 16 GB LPDDR5X shared between CPU and iGPU
    - AMD Radeon 780M with up to 4 GB dynamic VRAM
    - AMD Ryzen Z1 Extreme: 8c/16t
    """

    # Thresholds for dynamic scaling
    RAM_HIGH_WATERMARK = 0.80   # >80 % used → shrink context
    RAM_LOW_WATERMARK = 0.50    # <50 % used → allow expansion

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: HardwareSnapshot = HardwareSnapshot()
        self._budget: ContextBudget = ContextBudget()
        self._embedding_cache: dict[str, list[float]] = {}
        self._refresh()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def get_budget(self) -> ContextBudget:
        """Return current context budget, refreshing hardware snapshot."""
        self._refresh()
        return self._budget

    def get_snapshot(self) -> HardwareSnapshot:
        """Return the latest hardware snapshot."""
        self._refresh()
        return self._snapshot

    def cache_embedding(self, key: str, vector: list[float]) -> None:
        with self._lock:
            if len(self._embedding_cache) >= self._budget.embedding_cache_size:
                # Evict oldest entry (simple FIFO)
                oldest = next(iter(self._embedding_cache))
                del self._embedding_cache[oldest]
            self._embedding_cache[key] = vector

    def get_cached_embedding(self, key: str) -> Optional[list[float]]:
        with self._lock:
            return self._embedding_cache.get(key)

    def flush_cache(self) -> None:
        with self._lock:
            self._embedding_cache.clear()
        gc.collect()

    def summary(self) -> str:
        snap = self._snapshot
        budget = self._budget
        return (
            f"[Hardware] {snap.platform} | RAM {snap.ram_available_gb:.1f}/{snap.ram_total_gb:.1f} GB "
            f"({snap.ram_used_pct:.0f}% used) | GPU {snap.gpu_name} {snap.gpu_vram_mb} MB\n"
            f"[Budget] max_tokens={budget.max_tokens} | history={budget.max_history_turns} turns | "
            f"batch={budget.batch_size} | gpu_layers={budget.gpu_layers}"
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        snap = self._detect_hardware()
        budget = self._compute_budget(snap)
        with self._lock:
            self._snapshot = snap
            self._budget = budget

    def _detect_hardware(self) -> HardwareSnapshot:
        snap = HardwareSnapshot(platform=platform.system())
        snap.is_legion_go = settings.legion_go_enabled and settings.hardware_profile == "legion_go"

        if _PSUTIL:
            vm = psutil.virtual_memory()
            snap.ram_total_gb = vm.total / (1024 ** 3)
            snap.ram_available_gb = vm.available / (1024 ** 3)
            snap.ram_used_pct = vm.percent
            snap.cpu_cores = psutil.cpu_count(logical=False) or 1
            freq = psutil.cpu_freq()
            snap.cpu_freq_mhz = freq.current if freq else 0.0
        else:
            # Fallback to Legion Go defaults
            snap.ram_total_gb = 16.0
            snap.ram_available_gb = 10.0
            snap.ram_used_pct = 37.5
            snap.cpu_cores = 8

        if snap.is_legion_go:
            profile = LegionGoProfile.load()
            hw = profile.get("hardware", {})
            snap.gpu_name = hw.get("gpu", "AMD Radeon 780M")
            snap.gpu_vram_mb = hw.get("gpu_vram_mb", 4096)
        else:
            snap.gpu_name = "Generic GPU"
            snap.gpu_vram_mb = 0

        # Try ROCm / CUDA GPU detection
        snap.gpu_name, snap.gpu_vram_mb = self._detect_gpu(snap)
        return snap

    def _detect_gpu(self, snap: HardwareSnapshot) -> tuple[str, int]:
        name, vram = snap.gpu_name, snap.gpu_vram_mb

        # PyTorch ROCm / CUDA
        try:
            import torch  # noqa: PLC0415
            if torch.cuda.is_available():
                idx = torch.cuda.current_device()
                name = torch.cuda.get_device_name(idx)
                vram = torch.cuda.get_device_properties(idx).total_memory // (1024 * 1024)
        except ImportError:
            pass

        return name, vram

    def _compute_budget(self, snap: HardwareSnapshot) -> ContextBudget:
        budget = ContextBudget()

        if snap.is_legion_go:
            profile = LegionGoProfile.load()
            ai = profile.get("ai_performance", {})
            budget.max_tokens = ai.get("max_context_tokens", 4096)
            budget.batch_size = ai.get("max_batch_size", 4)
            budget.gpu_layers = ai.get("gpu_layers", 20)
            budget.embedding_cache_size = profile.get("memory", {}).get("embedding_cache_size", 1000)
        else:
            budget.max_tokens = settings.max_context_tokens
            budget.batch_size = 4
            budget.gpu_layers = settings.gpu_layers
            budget.embedding_cache_size = 500

        # Dynamic scaling based on live RAM pressure
        if snap.ram_used_pct > self.RAM_HIGH_WATERMARK * 100:
            budget.max_tokens = int(budget.max_tokens * 0.6)
            budget.batch_size = max(1, budget.batch_size - 2)
            budget.max_history_turns = 10
        elif snap.ram_used_pct < self.RAM_LOW_WATERMARK * 100:
            budget.max_tokens = int(budget.max_tokens * 1.2)
            budget.max_history_turns = 30

        budget.max_tokens = max(512, budget.max_tokens)
        return budget


# Module-level singleton
optimizer = ContextOptimizer()
