"""
Phenom Milestone 9.0 Phase 1: Guardian Kill Switch Sub-25ms SLA & Safety Verification (SAF-01, SAF-02)

Verifies:
1. Synchronous execution time of Guardian trigger is strictly < 25.0ms SLA (< 1ms typical).
2. Synchronous halt cascade halts both AmbientVisionCopilot and AdaptiveResourceGovernor immediately.
3. Universal rejection of subsequent vision and governor operations with PermissionError while halted.
4. Clean state restoration and resumption via guardian.resume().
5. Strict ToolRegistry registration, Pydantic argument validation, and preview generation (SAF-01).
"""

import asyncio
import time
import pytest

from services.backend.main import on_guardian_state_change
from services.backend.safety.engine import safety_engine
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.system.resource_governor import resource_governor
from services.backend.vision.ambient_copilot import ambient_copilot
import services.backend.tools.vision_tools


@pytest.fixture(autouse=True)
def reset_milestone_9_components():
    """Ensure clean state before and after each test."""
    guardian.resume()
    ambient_copilot.reset()
    resource_governor.reset()
    yield
    guardian.resume()
    ambient_copilot.reset()
    resource_governor.reset()


def test_tool_registry_registration_and_metadata():
    """SAF-01: Verifies all Phase 1 tools are registered with correct tiers, schemas, and previews."""
    # 1. vision_get_ambient_screen_context (Tier 0 Read-Only)
    tool_ambient = registry.get("vision_get_ambient_screen_context")
    assert tool_ambient is not None
    assert tool_ambient.tier == 0
    preview_ambient = tool_ambient.generate_preview({})
    assert "Inspect current ambient screen vision context" in preview_ambient

    # 2. vision_configure_ambient_copilot (Tier 1 Reversible)
    tool_config = registry.get("vision_configure_ambient_copilot")
    assert tool_config is not None
    assert tool_config.tier == 1
    preview_config = tool_config.generate_preview({"enabled": True, "interval_seconds": 4.0})
    assert "Configure ambient vision copilot settings" in preview_config

    # 3. governor_get_resource_status (Tier 0 Read-Only)
    tool_gov = registry.get("governor_get_resource_status")
    assert tool_gov is not None
    assert tool_gov.tier == 0
    preview_gov = tool_gov.generate_preview({})
    assert "Inspect GPU and system resource governor status" in preview_gov


def test_guardian_halt_sla_benchmark_sub_25ms():
    """SAF-02: Measures synchronous halt latency across Ambient Vision and Governor (< 25ms SLA)."""
    # 1. Setup active monitoring state
    ambient_copilot.configure(is_enabled=True, interval_seconds=3.0)
    resource_governor.set_mock_state(is_gaming=False, gpu_load=45.0)

    # 2. Trigger Guardian kill switch and benchmark latency
    start_time = time.perf_counter()
    guardian.trigger("emergency_killswitch_sla_test")
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    # 3. Assert strict SLA compliance (< 25.0ms)
    assert elapsed_ms < 25.0, (
        f"Guardian kill switch cascade latency {elapsed_ms:.3f}ms exceeded the 25.0ms SLA!"
    )

    # 4. Assert both Phase 1 subsystems are synchronously halted immediately
    assert guardian.is_halted is True
    assert ambient_copilot.is_halted is True
    assert resource_governor.is_halted is True
    assert resource_governor.vision_suspended is True
    assert resource_governor.swarms_suspended is True


@pytest.mark.asyncio
async def test_subsystems_reject_operations_while_halted():
    """SAF-02: Verifies all vision and governor operations raise PermissionError while halted."""
    guardian.trigger("halt_rejection_test")

    # 1. Direct copilot step
    with pytest.raises(PermissionError, match="HALTED by Guardian"):
        await ambient_copilot.step()

    # 2. Direct tool invocation: vision_get_ambient_screen_context
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await services.backend.tools.vision_tools.vision_get_ambient_screen_context()

    # 3. Direct tool invocation: vision_configure_ambient_copilot
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await services.backend.tools.vision_tools.vision_configure_ambient_copilot(enabled=False)

    # 4. Direct tool invocation: governor_get_resource_status
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await services.backend.tools.vision_tools.governor_get_resource_status()

    # 5. Safety engine dispatch: execute_tool
    with pytest.raises(PermissionError, match="Guardian kill switch is active"):
        await safety_engine.execute_tool("vision_get_ambient_screen_context", {})


@pytest.mark.asyncio
async def test_clean_resumption_after_guardian_resume():
    """SAF-02: Verifies systems cleanly recover and allow operations after guardian.resume()."""
    # 1. Trigger halt
    guardian.trigger("halt_then_resume_test")
    assert guardian.is_halted is True
    assert ambient_copilot.is_halted is True
    assert resource_governor.is_halted is True

    # 2. Resume Guardian
    guardian.resume()
    assert guardian.is_halted is False
    assert ambient_copilot.is_halted is False
    assert resource_governor.is_halted is False

    # 3. Operations succeed normally post-resume
    res_gov = await services.backend.tools.vision_tools.governor_get_resource_status(poll_now=False)
    assert res_gov["status"] == "success"
    assert "governor_state" in res_gov

    res_ambient = await services.backend.tools.vision_tools.vision_get_ambient_screen_context(refresh_if_stale=False)
    assert res_ambient["status"] == "success"
    assert "context" in res_ambient
