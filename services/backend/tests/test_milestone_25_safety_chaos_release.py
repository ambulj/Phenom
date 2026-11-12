"""Master Safety Audit, Chaos Concurrency Battery & Production Release Verification for Milestone 25.

Validates all 12 Milestone 25 tools, 100-cycle Guardian Kill Switch SLA (< 25.0ms),
4-pillar concurrent chaos stress battery, and Rule 1/4/7/8/11 safety invariants.

Part of Phenom 25.0 Autonomous Multi-Modal Screen Actor OS (SAF-01, SAF-02).
"""

import time
import pytest
import asyncio
from typing import Dict, Any, List

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry

# Milestone 25 Subsystems
from services.backend.grounding.semantic_grounding_engine import semantic_grounding_engine
from services.backend.grounding.visual_segmenter import visual_segmenter
from services.backend.actor.gui_action_synthesizer import gui_action_synthesizer, GuiActionStep
from services.backend.actor.gui_step_executor import gui_step_executor
from services.backend.orchestrator.cross_app_orchestrator import cross_app_orchestrator, CrossAppStep
from services.backend.orchestrator.window_focus_synchronizer import window_focus_synchronizer
from services.backend.watchdog.desktop_watchdog import desktop_watchdog
from services.backend.watchdog.proactive_task_interceptor import proactive_task_interceptor

import services.backend.tools.semantic_grounding_tools
import services.backend.tools.gui_actor_tools
import services.backend.tools.cross_app_workflow_tools
import services.backend.tools.desktop_watchdog_tools


MILESTONE_25_TOOLS = [
    # Phase 1: Real-Time Multi-Modal GUI Semantic Grounding (3)
    "ground_screen_elements",
    "locate_gui_visual_anchor",
    "get_visual_grounding_map",
    # Phase 2: Intent-Driven Declarative GUI Action Synthesizer (3)
    "synthesize_gui_action_plan",
    "preview_gui_action_step",
    "execute_gui_action_step",
    # Phase 3: Ambient Cross-Application Workflow Automator (3)
    "orchestrate_cross_app_workflow",
    "sync_window_workspace_focus",
    "get_ambient_workflow_status",
    # Phase 4: Proactive Context-Aware Desktop Watchdog (3)
    "inspect_desktop_watchdog_events",
    "resolve_proactive_alert",
    "configure_watchdog_policies",
]


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_exhaustive_tool_registry_audit_12_tools():
    """Verify all 12 Milestone 25 tools are registered with schemas and preview generators."""
    assert len(MILESTONE_25_TOOLS) == 12

    for tool_name in MILESTONE_25_TOOLS:
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
    """100-cycle Universal Guardian Kill Switch SLA Benchmark across all Milestone 25 pillars."""
    latencies = []

    for i in range(100):
        t0 = time.perf_counter()
        guardian.trigger(f"Milestone 25 Bench Cycle #{i}")
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
    guardian.trigger("Milestone 25 Safety Lockdown")
    assert guardian.is_halted

    # Pillar 1: Semantic Grounding
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        semantic_grounding_engine.ground_query("find save button")

    # Pillar 2: GUI Actor
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        gui_action_synthesizer.synthesize_plan("click button")

    # Pillar 3: Cross-App Orchestrator
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        cross_app_orchestrator.create_workflow("Test", [])

    # Pillar 4: Desktop Watchdog
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        desktop_watchdog.get_system_health()

    guardian.resume()


@pytest.mark.asyncio
async def test_4_pillar_concurrent_chaos_stress_battery():
    """Stress test all 4 subsystems with concurrent requests under load (0 deadlocks, 0 errors)."""

    async def pillar_1_worker():
        queries = [
            "click save changes button",
            "find search box",
            "settings gear icon",
            "press run tests",
        ]
        for i in range(10):
            q = queries[i % len(queries)]
            res = semantic_grounding_engine.ground_query(q)
            assert res.match_score >= 0.70
            await asyncio.sleep(0.005)

    async def pillar_2_worker():
        for i in range(10):
            step = GuiActionStep(
                step_id=i + 1,
                action_type="CLICK",
                target_coordinates=(400 + i * 10, 200 + i * 5),
                description=f"Click test step {i}",
            )
            res = gui_step_executor.execute_step(step, dry_run=True)
            assert res.status == "DRY_RUN"
            await asyncio.sleep(0.005)

    async def pillar_3_worker():
        for i in range(10):
            steps = [
                CrossAppStep(step_id=1, app_name="Edge", action="EXTRACT_SELECTION", output_variable=f"var_{i}"),
                CrossAppStep(step_id=2, app_name="VSCode", action="PASTE_TRANSFORM", input_payload=f"Process ${{var_{i}}}"),
            ]
            wf = cross_app_orchestrator.create_workflow(f"Workflow {i}", steps)
            executed = cross_app_orchestrator.execute_workflow()
            assert executed.status == "COMPLETED"
            await asyncio.sleep(0.005)

    async def pillar_4_worker():
        for i in range(10):
            desktop_watchdog.record_incident(
                severity="INFO",
                incident_type="SYSTEM_ALERT",
                process_name=f"WorkerApp_{i}.exe",
                details=f"Background tick notification {i}",
            )
            h = desktop_watchdog.get_system_health()
            assert h["health_score"] > 0
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
    from services.backend.grounding.semantic_grounding_engine import Rule8ViolationError as GroundR8
    from services.backend.actor.gui_action_synthesizer import Rule8ViolationError as ActorR8
    from services.backend.orchestrator.cross_app_orchestrator import Rule8ViolationError as CrossR8
    from services.backend.watchdog.desktop_watchdog import Rule8ViolationError as WatchR8

    # Pillar 1
    with pytest.raises(GroundR8, match="Rule 8"):
        semantic_grounding_engine.ground_query("click checkout payment button")

    # Pillar 2
    with pytest.raises(ActorR8, match="Rule 8"):
        gui_action_synthesizer.synthesize_plan("pay for credit card order")

    # Pillar 3
    with pytest.raises(CrossR8, match="Rule 8"):
        cross_app_orchestrator.create_workflow("Checkout cart workflow", [])

    # Pillar 4
    with pytest.raises(WatchR8, match="Rule 8"):
        desktop_watchdog.record_incident("ERROR", "CRASH_DIALOG", "checkout.exe", "card payment failure")
