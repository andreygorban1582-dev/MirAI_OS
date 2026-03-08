"""
Tests for the Context Optimizer (Legion Go hardware-aware context management).
"""
import pytest
from unittest.mock import patch


def test_context_optimizer_produces_budget():
    """ContextOptimizer.get_budget() should return a ContextBudget with valid values."""
    from core.context_optimizer import ContextOptimizer, ContextBudget
    opt = ContextOptimizer()
    budget = opt.get_budget()
    assert isinstance(budget, ContextBudget)
    assert budget.max_tokens >= 512
    assert budget.batch_size >= 1
    assert budget.gpu_layers >= 0


def test_embedding_cache_eviction():
    """Embedding cache should evict oldest entries when full."""
    from core.context_optimizer import ContextOptimizer
    opt = ContextOptimizer()
    opt._budget.embedding_cache_size = 3

    opt.cache_embedding("a", [0.1])
    opt.cache_embedding("b", [0.2])
    opt.cache_embedding("c", [0.3])
    opt.cache_embedding("d", [0.4])  # Should evict "a"

    assert opt.get_cached_embedding("a") is None
    assert opt.get_cached_embedding("d") == [0.4]


def test_embedding_cache_flush():
    """flush_cache() should clear all embeddings."""
    from core.context_optimizer import ContextOptimizer
    opt = ContextOptimizer()
    opt.cache_embedding("x", [1.0, 2.0])
    opt.flush_cache()
    assert opt.get_cached_embedding("x") is None


def test_ram_pressure_shrinks_context():
    """High RAM usage should reduce max_tokens."""
    from core.context_optimizer import ContextOptimizer, HardwareSnapshot
    opt = ContextOptimizer()

    # Simulate high RAM pressure
    snap = HardwareSnapshot(
        ram_total_gb=16.0,
        ram_available_gb=2.0,
        ram_used_pct=87.0,  # above HIGH_WATERMARK
        cpu_cores=8,
        is_legion_go=False,
    )
    budget = opt._compute_budget(snap)
    # With normal max_tokens (from settings), high pressure should give < original
    from config.settings import settings
    assert budget.max_tokens < settings.max_context_tokens


def test_low_ram_pressure_expands_context():
    """Low RAM usage should expand max_tokens."""
    from core.context_optimizer import ContextOptimizer, HardwareSnapshot
    opt = ContextOptimizer()

    snap = HardwareSnapshot(
        ram_total_gb=16.0,
        ram_available_gb=10.0,
        ram_used_pct=30.0,  # below LOW_WATERMARK
        cpu_cores=8,
        is_legion_go=False,
    )
    budget = opt._compute_budget(snap)
    from config.settings import settings
    assert budget.max_tokens > settings.max_context_tokens


def test_hardware_snapshot():
    """HardwareSnapshot should be populated."""
    from core.context_optimizer import ContextOptimizer
    opt = ContextOptimizer()
    snap = opt.get_snapshot()
    assert snap.ram_total_gb > 0
    assert snap.cpu_cores >= 1


def test_summary_string():
    """summary() should return a non-empty string."""
    from core.context_optimizer import ContextOptimizer
    opt = ContextOptimizer()
    s = opt.summary()
    assert isinstance(s, str)
    assert len(s) > 0
