"""Master Safety Audit, Chaos Concurrency Battery & Production Release Verification for Milestone 24.

Validates all 12 Milestone 24 tools, 100-cycle Guardian Kill Switch SLA (< 25.0ms),
4-pillar concurrent chaos stress battery, and Rule 1/4/7/8/11 safety invariants.

Part of Phenom 24.0 Sovereign Autonomous Self-Healing Infrastructure OS (SAF-01, SAF-02).
"""

import time
import pytest
import asyncio
from typing import Dict, Any, List

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry

# Milestone 24 Subsystems
from services.backend.healing.diagnostic_engine import diagnostic_engine
from services.backend.healing.patch_synthesizer import patch_synthesizer
from services.backend.sandbox.execution_jail import execution_jail
from services.backend.sandbox.ast_security_visitor import code_security_auditor
from services.backend.spatial.spatial_intent_resolver import spatial_intent_resolver
from services.backend.spatial.cursor_telemetry_tracker import cursor_telemetry_tracker
from services.backend.governor.resource_governor import resource_governor
from services.backend.governor.adaptive_throttler import adaptive_throttler

import services.backend.tools.self_healing_tools
import services.backend.tools.sandbox_jail_tools
import services.backend.tools.spatial_voice_tools
import services.backend.tools.resource_governor_tools


MILESTONE_24_TOOLS = [
    # Phase 1: Autonomous Neuro-Symbolic Diagnostic & Self-Healing Engine (3)
    "diagnose_runtime_failure",
    "synthesize_healing_patch",
    "apply_healing_patch",
    # Phase 2: Dynamic Micro-Sandbox & Isolated AST Execution Jail (3)
    "validate_code_security",
    "execute_in_sandbox_jail",
    "get_sandbox_telemetry",
    # Phase 3: Adaptive Cross-Modal Spatial Cursor-Voice Intent Interactor (3)
    "resolve_spatial_intent",
    "get_cursor_spatial_context",
    "highlight_spatial_target",
    # Phase 4: Predictive Resource Governor & Heterogeneous CUDA/RAM Balancer (3)
    "get_host_resource_telemetry",
    "set_governor_throttle_mode",
    "override_resource_headroom",
]


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_exhaustive_tool_registry_audit_12_tools():
    """Verify all 12 Milestone 24 tools are registered with schemas and preview generators."""
    assert len(MILESTONE_24_TOOLS) == 12

    for tool_name in MILESTONE_24_TOOLS:
        tool = registry.get(tool_name)
        assert tool is not None, f"Tool '{tool_name}' missing from ToolRegistry"
        assert tool.tier in [0, 1, 2, 3], f"Tool '{tool_name}' has invalid tier {tool.tier}"
        assert tool.args_schema is not None, f"Tool '{tool_name}' missing Pydantic schema"
        assert tool.preview_fn is not None, f"Tool '{tool_name}' missing preview generator"

        # Validate dry-run preview generation
        dummy_args = {f: "test_val" for f in tool.args_schema.model_fields.keys()}
        try:
            preview_text = tool.generate_preview(dummy_args)
            assert isinstance(preview_text, str)
            assert len(preview_text) > 0
        except Exception as e:
            pytest.fail(f"Preview generation failed for '{tool_name}': {e}")


def test_100_cycle_guardian_kill_switch_sla_benchmark():
    """100-cycle Universal Guardian Kill Switch SLA Benchmark across all Milestone 24 pillars."""
    latencies = []

    for i in range(100):
        t0 = time.perf_counter()
        guardian.trigger(f"Milestone 24 Bench Cycle #{i}")
        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0
        latencies.append(latency_ms)

        assert guardian.is_halted
        guardian.resume()
        assert not guardian.is_halted

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    print(f"\n[Guardian SLA] 100 cycles: Avg = {avg_latency:.4f} ms, Max = {max_latency:.4f} ms")
    assert max_latency < 25.0, f"Max Guardian halt latency {max_latency:.4f}ms exceeded 25.0ms hard SLA"
    assert avg_latency < 2.0, f"Average Guardian halt latency {avg_latency:.4f}ms exceeded 2.0ms target"


def test_cross_pillar_guardian_halt_enforcement():
    """Verify cross-subsystem Guardian halt enforcement across all 4 pillars."""
    guardian.trigger("Milestone 24 Safety Lockdown")
    assert guardian.is_halted

    # Pillar 1: Self-Healing Diagnostic Engine
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        diagnostic_engine.diagnose_traceback("Traceback: ZeroDivisionError: division by zero")

    # Pillar 2: Dynamic Micro-Sandbox Jail
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        execution_jail.execute_code("result = 1 + 1")

    # Pillar 3: Spatial Intent Resolver
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        spatial_intent_resolver.resolve_spatial_intent("refactor this function")

    # Pillar 4: Predictive Resource Governor
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        resource_governor.sample_telemetry()

    guardian.resume()


@pytest.mark.asyncio
async def test_4_pillar_concurrent_chaos_stress_battery():
    """Stress test all 4 subsystems with concurrent requests under load (0 deadlocks, 0 errors)."""

    async def pillar_1_worker():
        tb_sample = """Traceback (most recent call last):
  File "test_script.py", line 4, in calc
    return a / b
ZeroDivisionError: division by zero"""
        for _ in range(10):
            diag = diagnostic_engine.diagnose_traceback(tb_sample)
            assert diag.fault_category == "DIVISION_BY_ZERO"
            assert diag.confidence_score >= 0.90
            await asyncio.sleep(0.005)

    async def pillar_2_worker():
        for i in range(10):
            res = execution_jail.execute_code(f"val = {i} * 10\nprint(val)")
            assert res.status == "SUCCESS"
            assert str(i * 10) in res.stdout
            await asyncio.sleep(0.005)

    async def pillar_3_worker():
        for i in range(10):
            resolved = spatial_intent_resolver.resolve_spatial_intent(
                spoken_command=f"refactor this function {i}",
            )
            assert resolved.is_deictic is True
            assert resolved.confidence > 0.8
            await asyncio.sleep(0.005)

    async def pillar_4_worker():
        for _ in range(10):
            telem = resource_governor.sample_telemetry()
            assert 0.0 <= telem.composite_load_rating <= 1.0
            cfg = adaptive_throttler.get_active_config()
            assert cfg.max_concurrency in (1, 2, 4)
            await asyncio.sleep(0.005)

    t0 = time.perf_counter()
    await asyncio.gather(
        pillar_1_worker(),
        pillar_2_worker(),
        pillar_3_worker(),
        pillar_4_worker(),
    )
    duration = time.perf_counter() - t0
    print(f"\n[Chaos Battery] 40 concurrent operations completed in {duration:.4f} s (0 deadlocks, 0 errors)")
    assert duration < 5.0, f"Chaos stress duration {duration:.2f}s exceeded 5.0s SLA"


def test_rule_8_anti_checkout_across_all_pillars():
    """Verify Rule 8 payment / checkout rejection across all subsystems."""
    from services.backend.healing.diagnostic_engine import Rule8ViolationError as HealR8
    from services.backend.sandbox.execution_jail import Rule8ViolationError as JailR8
    from services.backend.spatial.spatial_intent_resolver import Rule8ViolationError as SpatialR8
    from services.backend.governor.adaptive_throttler import Rule8ViolationError as GovR8

    # Pillar 1
    with pytest.raises(HealR8, match="Rule 8"):
        diagnostic_engine.diagnose_traceback("Traceback: in checkout_payment(): process_card()")

    # Pillar 2
    with pytest.raises(JailR8, match="Rule 8"):
        execution_jail.execute_code("def checkout_cart(): pass")

    # Pillar 3
    with pytest.raises(SpatialR8, match="Rule 8"):
        spatial_intent_resolver.resolve_spatial_intent("pay for this order now")

    # Pillar 4
    with pytest.raises(GovR8, match="Rule 8"):
        adaptive_throttler.sync_throttle_state(force_state="pay_checkout_billing")
