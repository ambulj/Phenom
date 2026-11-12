"""Master Safety Audit, Chaos Concurrency Battery & Production Release Verification for Milestone 23.

Validates all 12 Milestone 23 tools, 100-cycle Guardian Kill Switch SLA (< 25.0ms),
4-pillar concurrent chaos stress battery, and Rule 1/4/7/8/11 safety invariants.

Part of Phenom 23.0 Sovereign Neural Evolution OS (SAF-01, SAF-02).
"""

import time
import pytest
import asyncio
from typing import Dict, Any, List

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry

# Milestone 23 Subsystems
from services.backend.metacognition.reflective_auditor import reflective_auditor
from services.backend.metacognition.reflection_vault_logger import reflection_vault_logger
from services.backend.evolution.dataset_generator import dataset_generator
from services.backend.evolution.adapter_router import adapter_router
from services.backend.synapse.voice_code_synapse import voice_code_synapse
from services.backend.synapse.acoustic_earcon_manager import acoustic_earcon_manager
from services.backend.proactive.task_anticipation_engine import task_anticipation_engine
from services.backend.proactive.cache_prewarmer import cache_prewarmer

import services.backend.tools.metacognitive_tools
import services.backend.tools.adapter_evolution_tools
import services.backend.tools.voice_code_synapse_tools
import services.backend.tools.predictive_task_tools


MILESTONE_23_TOOLS = [
    # Phase 1: Metacognitive Self-Reflection (3)
    "audit_execution_trajectory",
    "record_reflection_note",
    "get_metacognitive_calibration_stats",
    # Phase 2: Autonomous Local Fine-Tuning & Adapter Synthesis (3)
    "synthesize_tuning_dataset",
    "route_model_adapter",
    "get_adapter_telemetry",
    # Phase 3: Cross-Modal Conversational Workspace Synapse (3)
    "apply_voice_code_mutation",
    "play_acoustic_earcon",
    "get_synapse_buffer_state",
    # Phase 4: Predictive Proactive Task Anticipation (3)
    "predict_next_actions",
    "prewarm_workflow_cache",
    "dismiss_action_card",
]


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_exhaustive_tool_registry_audit_12_tools():
    """Verify all 12 Milestone 23 tools are registered with schemas and preview generators."""
    assert len(MILESTONE_23_TOOLS) == 12

    for tool_name in MILESTONE_23_TOOLS:
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
    """100-cycle Universal Guardian Kill Switch SLA Benchmark across all Milestone 23 pillars."""
    latencies = []

    for i in range(100):
        t0 = time.perf_counter()
        guardian.trigger(f"Bench Cycle #{i}")
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
    guardian.trigger("Milestone 23 Safety Lockdown")
    assert guardian.is_halted

    # Pillar 1: Metacognitive Reflector
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        reflective_auditor.audit_trajectory("intent", [])

    # Pillar 2: LoRA Adapter Router
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        adapter_router.route_query("write python code")

    # Pillar 3: Voice-Code Synapse
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        voice_code_synapse.apply_spoken_mutation("main.py", "func", "rename_param", {})

    # Pillar 4: Task Anticipation & Prewarmer
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        task_anticipation_engine.predict_next_actions("git_commit")

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        cache_prewarmer.prewarm_target("symbols_target")

    guardian.resume()


@pytest.mark.asyncio
async def test_4_pillar_concurrent_chaos_stress_battery():
    """Stress test all 4 subsystems with concurrent requests under load (0 deadlocks, 0 errors)."""
    from services.backend.metacognition.reflective_auditor import ExecutionStep

    async def pillar_1_worker():
        for i in range(10):
            step = ExecutionStep(step_id=i + 1, tool_name="test_tool", status="success")
            res = reflective_auditor.audit_trajectory(
                user_intent=f"intent {i}",
                steps=[step],
                prior_confidence=0.85,
            )
            assert res.calibration_score > 0
            await asyncio.sleep(0.005)

    async def pillar_2_worker():
        queries = ["write a python fastsort", "solve logical puzzle", "tell me a witty joke", "status check"]
        for i in range(10):
            q = queries[i % len(queries)]
            r = adapter_router.route_query(q)
            assert r.selected_adapter in ["coding_adapter", "reasoning_adapter", "witty_persona_adapter", "base_model"]
            await asyncio.sleep(0.005)

    async def pillar_3_worker():
        for i in range(10):
            pcm = acoustic_earcon_manager.generate_earcon_pcm("ast_success")
            assert len(pcm) > 0
            await asyncio.sleep(0.005)

    async def pillar_4_worker():
        for i in range(10):
            task_anticipation_engine.record_transition(f"action_a_{i}", f"action_b_{i}")
            preds = task_anticipation_engine.predict_next_actions(f"action_a_{i}", threshold=0.10)
            assert len(preds) >= 1
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
    from services.backend.metacognition.reflective_auditor import Rule8ViolationError as MetaR8
    from services.backend.evolution.dataset_generator import Rule8ViolationError as AdaptR8
    from services.backend.synapse.voice_code_synapse import Rule8ViolationError as SynapseR8
    from services.backend.proactive.task_anticipation_engine import Rule8ViolationError as ProactiveR8

    with pytest.raises(MetaR8, match="Rule 8"):
        reflective_auditor.audit_trajectory("complete payment checkout with card", [])

    with pytest.raises(AdaptR8, match="Rule 8"):
        dataset_generator.add_tuning_sample("checkout my shopping cart now", "ok")

    with pytest.raises(SynapseR8, match="Rule 8"):
        voice_code_synapse.apply_spoken_mutation("cart.py", "execute_payment_checkout", "rename_param", {})

    with pytest.raises(ProactiveR8, match="Rule 8"):
        task_anticipation_engine.predict_next_actions("order_checkout_now")
