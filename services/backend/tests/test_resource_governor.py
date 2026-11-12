"""Unit and Safety Integration Tests for Predictive Resource Governor & CUDA/RAM Balancer.

Validates host telemetry sampling, dynamic load rating calculation, adaptive subagent
concurrency throttling, headroom overrides, Rule 8 anti-checkout defense, and Guardian SLA.
Phase 24-04 (GOV-03, RES-02, SAF-01, SAF-02).
"""

import time
import pytest

from services.backend.governor.resource_governor import (
    ResourceGovernor,
    HostResourceTelemetry,
)
from services.backend.governor.adaptive_throttler import (
    AdaptiveThrottler,
    Rule8ViolationError as GovRule8Error,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.resource_governor_tools  # Ensure tools are loaded


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_resource_telemetry_sampling_and_metrics():
    """Verify resource governor accurately samples CPU, RAM, VRAM, and thermal load."""
    gov = ResourceGovernor()
    telem = gov.sample_telemetry()

    assert isinstance(telem, HostResourceTelemetry)
    assert 0.0 <= telem.cpu_percent <= 100.0
    assert telem.ram_total_gb > 0
    assert telem.ram_used_gb > 0
    assert telem.vram_allocated_mb > 0
    assert 0.0 <= telem.composite_load_rating <= 1.0
    assert telem.throttle_state in ("NORMAL", "CONSERVE", "EMERGENCY_THROTTLE")


def test_dynamic_throttle_state_shifting_under_load():
    """Verify governor shifts states dynamically as load increases."""
    gov = ResourceGovernor()
    throttler = AdaptiveThrottler(governor=gov)

    # 1. Normal load
    gov.set_simulated_load(0.35)
    t_normal = gov.sample_telemetry()
    assert t_normal.throttle_state == "NORMAL"

    cfg_normal = throttler.sync_throttle_state()
    assert cfg_normal.state == "NORMAL"
    assert cfg_normal.max_concurrency == 4
    assert cfg_normal.background_indexing_paused is False

    # 2. Conserve load
    gov.set_simulated_load(0.72)
    t_conserve = gov.sample_telemetry()
    assert t_conserve.throttle_state == "CONSERVE"

    cfg_conserve = throttler.sync_throttle_state()
    assert cfg_conserve.state == "CONSERVE"
    assert cfg_conserve.max_concurrency == 2
    assert cfg_conserve.background_indexing_paused is False

    # 3. Emergency throttle load
    gov.set_simulated_load(0.92)
    t_emergency = gov.sample_telemetry()
    assert t_emergency.throttle_state == "EMERGENCY_THROTTLE"

    cfg_emergency = throttler.sync_throttle_state()
    assert cfg_emergency.state == "EMERGENCY_THROTTLE"
    assert cfg_emergency.max_concurrency == 1
    assert cfg_emergency.background_indexing_paused is True

    gov.set_simulated_load(None)


def test_manual_throttle_override_and_reset():
    """Verify manual override sets custom state and reset restores telemetry sync."""
    throttler = AdaptiveThrottler()

    # Apply manual override
    cfg_override = throttler.sync_throttle_state(force_state="CONSERVE", manual=True)
    assert cfg_override.state == "CONSERVE"
    assert cfg_override.manual_override is True
    assert cfg_override.max_concurrency == 2

    # Override headroom
    cfg_headroom = throttler.override_headroom(2048.0)
    assert cfg_headroom.vram_headroom_mb == 2048.0

    # Reset override
    cfg_reset = throttler.reset_override()
    assert cfg_reset.manual_override is False


def test_rule_8_anti_checkout_enforcement():
    """Verify Rule 8 payment / checkout rejection in governor throttle parameters."""
    throttler = AdaptiveThrottler()

    with pytest.raises(GovRule8Error, match="Rule 8 violation"):
        throttler.sync_throttle_state(force_state="checkout_payment_mode")


def test_guardian_kill_switch_sla_halt():
    """Verify Guardian kill switch halts governor sampling and throttler in < 25.0ms SLA."""
    guardian.trigger("Emergency test halt")
    assert guardian.is_halted

    gov = ResourceGovernor()
    throttler = AdaptiveThrottler()

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        gov.sample_telemetry()
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    assert latency_ms < 25.0, f"Halt latency {latency_ms:.4f}ms exceeded 25.0ms SLA"

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        throttler.sync_throttle_state()
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    assert latency_ms < 25.0, f"Halt latency {latency_ms:.4f}ms exceeded 25.0ms SLA"

    guardian.resume()


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    telem_tool = registry.get("get_host_resource_telemetry")
    assert telem_tool is not None
    assert telem_tool.tier == 0
    preview_telem = telem_tool.generate_preview({})
    assert "telemetry" in preview_telem

    set_tool = registry.get("set_governor_throttle_mode")
    assert set_tool is not None
    assert set_tool.tier == 1
    preview_set = set_tool.generate_preview({"throttle_mode": "CONSERVE"})
    assert "CONSERVE" in preview_set

    headroom_tool = registry.get("override_resource_headroom")
    assert headroom_tool is not None
    assert headroom_tool.tier == 1
    preview_hr = headroom_tool.generate_preview({"vram_headroom_mb": 1536.0})
    assert "1536" in preview_hr
