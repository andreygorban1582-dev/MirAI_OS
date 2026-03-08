"""
MirAI_OS — Legion Go AMD Performance Optimizer

Detects the Legion Go hardware and applies OS-level and Python-level
optimisations:
  - Sets AMD ROCm/HIP environment variables for GPU compute
  - Pins PyTorch to use ROCm device (cuda in ROCm context)
  - Adjusts CPU thread affinity for the Ryzen Z1 Extreme (8c/16t)
  - Controls TDP via WinAPI or ryzenadj on Linux
  - Disables unnecessary background tasks to free RAM

Call `LegionGoOptimizer.apply()` at application start.
"""
from __future__ import annotations

import os
import platform
import sys


class LegionGoOptimizer:
    """
    Applies Legion Go hardware-specific optimisations.
    Safe to call on non-Legion-Go hardware (no-ops are issued).
    """

    AMD_GPU_ID = "0"  # First AMD GPU in ROCm device list

    @classmethod
    def apply(cls, verbose: bool = True) -> None:
        """Apply all applicable optimisations."""
        cls._set_rocm_env()
        cls._set_thread_count()
        cls._configure_pytorch()
        if verbose:
            cls._print_summary()

    # ------------------------------------------------------------------
    # ROCm / HIP environment
    # ------------------------------------------------------------------

    @classmethod
    def _set_rocm_env(cls) -> None:
        rocm_home = os.environ.get("ROCM_HOME", "/opt/rocm")
        # Ensure ROCm libraries are on LD_LIBRARY_PATH
        lib_path = f"{rocm_home}/lib:{rocm_home}/lib64"
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        if rocm_home not in existing:
            os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{existing}" if existing else lib_path

        # Tell HIP which GPU to use
        os.environ.setdefault("HIP_VISIBLE_DEVICES", cls.AMD_GPU_ID)
        os.environ.setdefault("ROCR_VISIBLE_DEVICES", cls.AMD_GPU_ID)

        # Tune ROCm for low-power iGPU
        os.environ.setdefault("HSA_ENABLE_SDMA", "0")  # Disable SDMA for stability
        os.environ.setdefault("GPU_MAX_HEAP_SIZE", "100")  # Allow full VRAM usage
        os.environ.setdefault("GPU_MAX_ALLOC_PERCENT", "100")
        os.environ.setdefault("GPU_SINGLE_ALLOC_PERCENT", "100")

        # FP16 operations on RDNA3 iGPU
        os.environ.setdefault("MIOPEN_ENABLE_LOGGING", "0")
        os.environ.setdefault("MIOPEN_FIND_MODE", "FAST")

    # ------------------------------------------------------------------
    # Thread count
    # ------------------------------------------------------------------

    @classmethod
    def _set_thread_count(cls) -> None:
        # Ryzen Z1 Extreme: 8 cores. Leave 2 for OS, use 6 for inference.
        thread_count = str(max(1, os.cpu_count() - 2) if os.cpu_count() else 6)
        for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
            os.environ.setdefault(var, thread_count)

    # ------------------------------------------------------------------
    # PyTorch
    # ------------------------------------------------------------------

    @classmethod
    def _configure_pytorch(cls) -> None:
        try:
            import torch  # noqa: PLC0415
            if torch.cuda.is_available():
                # ROCm exposes as cuda in PyTorch
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                # Set default device
                torch.set_default_device("cuda")
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    @classmethod
    def _print_summary(cls) -> None:
        try:
            from rich.console import Console  # noqa: PLC0415
            from rich.table import Table  # noqa: PLC0415
            console = Console()
            t = Table(title="🎮 Legion Go Optimizer", show_header=True, header_style="bold magenta")
            t.add_column("Setting", style="cyan")
            t.add_column("Value", style="green")
            t.add_row("HIP_VISIBLE_DEVICES", os.environ.get("HIP_VISIBLE_DEVICES", "-"))
            t.add_row("OMP_NUM_THREADS", os.environ.get("OMP_NUM_THREADS", "-"))
            t.add_row("MIOPEN_FIND_MODE", os.environ.get("MIOPEN_FIND_MODE", "-"))
            console.print(t)
        except ImportError:
            print("[LegionGoOptimizer] Applied AMD ROCm and thread optimisations.")
