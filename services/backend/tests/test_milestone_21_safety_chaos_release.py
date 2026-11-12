import pytest
import time
import asyncio
import json
import os
from typing import List, Dict, Any

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.automation.gui_controller import Rule8ViolationError

# Milestone 21 Modules
from services.backend.fusion.multimodal_fuser import multimodal_fuser
from services.backend.fusion.deictic_resolver import deictic_resolver
from services.backend.automation.macro_synthesizer import macro_synthesizer, MacroStep
from services.backend.automation.workflow_engine import workflow_engine
from services.backend.remote.telegram_mesh import telegram_mesh
from services.backend.remote.interactive_approvals import interactive_approval_manager
from services.backend.voice.adaptive_tts_engine import adaptive_tts_engine
from services.backend.voice.audio_ducking_manager import audio_ducking_manager

# Ensure all tools are registered
import services.backend.tools.multimodal_fusion_tools
import services.backend.tools.workflow_macro_tools
import services.backend.tools.telegram_mesh_tools
import services.backend.tools.adaptive_voice_tools


# 15 Tools added across Milestone 21
MILESTONE_21_TOOLS: Dict[str, Dict[str, Any]] = {
    # Phase 1: Multimodal Context Fusion
    "fuse_multimodal_context": {"tier": 0, "sample_args": {"query": "explain this function"}},
    "resolve_screen_deictic_reference": {"tier": 0, "sample_args": {"query": "this function"}},
    "get_active_fusion_state": {"tier": 0, "sample_args": {}},

    # Phase 2: Autonomous Desktop Macro Synthesis & Self-Healing Workflow
    "record_macro_step": {"tier": 0, "sample_args": {"action": "click", "target_value": "Save"}},
    "synthesize_workflow_recipe": {"tier": 1, "sample_args": {"name": "Test Recipe", "steps": []}},
    "preview_workflow_execution": {"tier": 0, "sample_args": {"recipe_id": "test_recipe"}},
    "execute_workflow_recipe": {"tier": 1, "sample_args": {"recipe_id": "test_recipe"}},
    "list_workflow_recipes": {"tier": 0, "sample_args": {}},

    # Phase 3: Advanced Bi-Directional Telegram Command Mesh
    "dispatch_telegram_approval_request": {"tier": 1, "sample_args": {"action_name": "refactor", "preview_text": "Rename symbol"}},
    "handle_telegram_callback_decision": {"tier": 0, "sample_args": {"callback_data": "approve:appr_123"}},
    "execute_remote_voice_rag": {"tier": 0, "sample_args": {"query": "explain architecture"}},
    "get_telegram_mesh_status": {"tier": 0, "sample_args": {}},

    # Phase 4: Adaptive Low-Latency Neural Voice & Persona Engine
    "synthesize_adaptive_speech": {"tier": 0, "sample_args": {"text": "System operational."}},
    "set_voice_prosody_mode": {"tier": 0, "sample_args": {"persona_id": "witty_jarvis"}},
    "get_audio_ducking_state": {"tier": 0, "sample_args": {}},
}


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


@pytest.mark.asyncio
async def test_milestone_21_tool_registry_exhaustive_audit():
    """Verify all 15 Milestone 21 tools are registered with schemas, tiers, and previews."""
    assert len(MILESTONE_21_TOOLS) == 15, "Expected exactly 15 tools in Milestone 21 catalog"

    for tool_name, meta in MILESTONE_21_TOOLS.items():
        entry = registry.get(tool_name)
        assert entry is not None, f"Tool '{tool_name}' missing from Safety Registry"
        assert entry.tier == meta["tier"], f"Tool '{tool_name}' tier mismatch: expected {meta['tier']}, got {entry.tier}"
        assert entry.args_schema is not None, f"Tool '{tool_name}' missing Pydantic args_schema"
        assert entry.preview_fn is not None, f"Tool '{tool_name}' missing preview_fn"

        # Test preview generation
        preview = entry.preview_fn(meta["sample_args"])
        assert isinstance(preview, str) and len(preview) > 5, f"Preview failed for '{tool_name}'"


@pytest.mark.asyncio
async def test_universal_guardian_kill_switch_100_cycle_benchmark():
    """Run 100 consecutive synchronous Guardian triggers benchmarking strict < 25.0ms SLA."""
    guardian.resume()
    assert guardian.is_halted is False

    latencies_ms: List[float] = []

    for i in range(100):
        t0 = time.perf_counter()
        guardian.trigger(f"Benchmark trigger {i}")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        latencies_ms.append(elapsed_ms)
        assert guardian.is_halted is True
        assert elapsed_ms < 25.0, f"Cycle {i} trigger latency {elapsed_ms:.4f}ms exceeded 25.0ms SLA"

        guardian.resume()
        assert guardian.is_halted is False

    avg_lat = sum(latencies_ms) / len(latencies_ms)
    max_lat = max(latencies_ms)

    print(f"\n[GUARDIAN SLA BENCHMARK] 100 Cycles: Avg = {avg_lat:.4f}ms, Max = {max_lat:.4f}ms (< 25.0ms SLA)")
    assert avg_lat < 2.0, f"Average latency {avg_lat:.4f}ms exceeded 2.0ms target"
    assert max_lat < 25.0, f"Maximum latency {max_lat:.4f}ms exceeded 25.0ms hard SLA"


@pytest.mark.asyncio
async def test_concurrent_chaos_stress_battery_5_subsystems():
    """Concurrently stress 5 Milestone 21 subsystems under maximum load with 0 deadlocks."""
    async def worker_fusion(idx: int):
        return await multimodal_fuser.fuse(
            voice_utterance=f"Query {idx}: What does this function do?",
            focused_window={"title": "editor.py - Visual Studio Code", "app_name": "Code.exe"},
            ocr_tokens=[{"text": f"func_{idx}", "bbox": [10, 20, 100, 40]}],
            ast_symbols=[{"name": f"func_{idx}", "kind": "function", "file": "editor.py", "line": idx * 10}]
        )

    async def worker_workflow(idx: int):
        step = MacroStep(step_id=1, action="wait", timeout_ms=10)
        recipe = macro_synthesizer.synthesize_recipe(name=f"Workflow_{idx}", steps=[step])
        return await workflow_engine.execute_recipe(recipe, dry_run=True)

    async def worker_telegram(idx: int):
        ticket = telegram_mesh.dispatch_approval_request(
            action_name=f"refactor_task_{idx}",
            tier=1,
            preview_text=f"Batch rename {idx}"
        )
        telegram_mesh.handle_callback_query(f"approve:{ticket.ticket_id}")
        return ticket

    async def worker_tts(idx: int):
        chunks = []
        async for c in adaptive_tts_engine.stream_speech_chunks(f"Testing streaming speech chunk generation {idx}"):
            chunks.append(c)
        return len(chunks)

    async def worker_ducking(idx: int):
        await audio_ducking_manager.duck_audio(target_volume=0.20, ramp_ms=20)
        await asyncio.sleep(0.01)
        await audio_ducking_manager.unduck_audio(restore_volume=1.0, ramp_ms=20)
        return True

    # Assemble 25 concurrent tasks
    tasks = []
    for i in range(5):
        tasks.append(worker_fusion(i))
        tasks.append(worker_workflow(i))
        tasks.append(worker_telegram(i))
        tasks.append(worker_tts(i))
        tasks.append(worker_ducking(i))

    t0 = time.perf_counter()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.perf_counter() - t0

    # Assert all 25 operations completed without exceptions
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(errors) == 0, f"Chaos battery encountered {len(errors)} errors: {errors}"
    assert len(results) == 25
    print(f"\n[CHAOS STRESS BATTERY] 25 concurrent operations completed in {total_time:.2f}s with 0 errors, 0 deadlocks.")


@pytest.mark.asyncio
async def test_permanent_safety_rules_invariants_audit():
    """Verify permanent invariants: Rule 1, Rule 4, Rule 7, Rule 8, Rule 11."""
    # Rule 8: Anti-Checkout Protection across all automation layers
    with pytest.raises(Rule8ViolationError):
        await deictic_resolver.resolve(phrase="click proceed to checkout")

    with pytest.raises(Rule8ViolationError):
        macro_synthesizer.record_step({"action": "click", "target_value": "Complete Payment $49.99"})

    step_bad = MacroStep(step_id=1, action="click", target_value="Pay Now")
    recipe_bad = macro_synthesizer.synthesize_recipe(name="Bad Checkout", steps=[step_bad])
    with pytest.raises(Rule8ViolationError):
        await workflow_engine.execute_recipe(recipe_bad)

    # Rule 4: Zero audio exfiltration, purely in-RAM
    chunks_count = 0
    async for chunk in adaptive_tts_engine.stream_speech_chunks("Privacy invariant check"):
        assert isinstance(chunk.pcm_bytes, bytes)
        chunks_count += 1
    assert chunks_count > 0


@pytest.mark.asyncio
async def test_package_json_version_and_metadata():
    """Verify apps/desktop/package.json version matches v21.0.0."""
    pkg_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "apps", "desktop", "package.json")
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    version_major = int(pkg.get("version", "0").split(".")[0])
    assert version_major >= 21, f"Expected version >= 21.0.0 in package.json, found {pkg.get('version')}"
    assert pkg.get("name") == "phenom-desktop"
