"""
Unit tests for Milestone 41 Phase 4: CUDA Tuner & Terminal TUI
Validates:
1. Dynamic RTX 3050 CUDA detection and VRAM partitioning.
2. Terminal TUI ANSI ASCII dashboard generation.
3. Universal Guardian kill switch (<25ms SLA) enforcement.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.platform.cuda_tuner import cuda_tuner
from services.backend.ui.terminal_tui import terminal_tui


@pytest.fixture(autouse=True)
def ensure_guardian_active():
    guardian.resume()
    yield
    guardian.resume()


def test_cuda_tuner_detection_and_allocations():
    telemetry = cuda_tuner.detect_cuda_environment()
    assert "device_name" in telemetry
    assert "total_vram_mb" in telemetry
    assert telemetry["total_vram_mb"] >= 4096
    assert "allocations" in telemetry
    alloc = telemetry["allocations"]
    assert "local_8b_llm_mb" in alloc
    assert "analysis_dbi_workers_mb" in alloc
    assert "system_headroom_mb" in alloc
    # Total allocations should match total VRAM
    assert alloc["local_8b_llm_mb"] + alloc["analysis_dbi_workers_mb"] + alloc["system_headroom_mb"] == telemetry["total_vram_mb"]
    assert telemetry["speculative_decoding_ready"] is True


def test_terminal_tui_dashboard_rendering():
    snapshot = terminal_tui.render_dashboard_snapshot()
    assert "PHENOM APEX-SOVEREIGN" in snapshot
    assert "HOST PLATFORM:" in snapshot
    assert "GUARDIAN:" in snapshot
    assert "HARDWARE & ACCELERATION" in snapshot
    assert "SPECTRAL-NEXUS" in snapshot
    assert "SOVEREIGN TACTICAL SWARM" in snapshot
    assert "ZERO-TRACE POSTURE" in snapshot


def test_cuda_tuner_guardian_sla():
    guardian.trigger("Emergency drill")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError):
        cuda_tuner.detect_cuda_environment()
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA violation: {latency_ms:.3f}ms >= 25.0ms"
