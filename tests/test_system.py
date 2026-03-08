"""
Tests for Legion Go hardware optimizer.
"""
import os
import importlib


def test_set_rocm_env():
    """_set_rocm_env() should set HIP_VISIBLE_DEVICES."""
    from system.legion_go_optimizer import LegionGoOptimizer
    # Clear env var if set so setdefault can be tested
    os.environ.pop("HIP_VISIBLE_DEVICES", None)
    LegionGoOptimizer._set_rocm_env()
    assert "HIP_VISIBLE_DEVICES" in os.environ


def test_set_thread_count():
    """_set_thread_count() should set OMP_NUM_THREADS."""
    from system.legion_go_optimizer import LegionGoOptimizer
    os.environ.pop("OMP_NUM_THREADS", None)
    LegionGoOptimizer._set_thread_count()
    assert "OMP_NUM_THREADS" in os.environ
    threads = int(os.environ["OMP_NUM_THREADS"])
    assert threads >= 1


def test_apply_does_not_crash():
    """apply() should not raise on any platform."""
    from system.legion_go_optimizer import LegionGoOptimizer
    LegionGoOptimizer.apply(verbose=False)


def test_kali_blocked_commands():
    """Kali integration should block dangerous commands."""
    from system.kali_integration import KaliIntegration
    ki = KaliIntegration()
    result = ki.run_command("rm -rf /")
    assert "Blocked" in result or "not configured" in result
