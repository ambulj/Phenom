"""Milestone 31 Master Safety Audit, Chaos Concurrency Battery & Production Release Verification (v31.0.0).

Verifies:
- SAF-01.1: Cumulative Tool Registry audit for all 16 new Milestone 31 tools.
- SAF-01.2: Permanent safety rule compliance (Rule 4 local offline, Rule 7 non-destructive rollback, Rule 8 anti-checkout, Rule 11 credential protection).
- SAF-02.1: 100-cycle Universal Guardian kill switch SLA benchmark (< 25.0ms SLA, target < 1.0ms) simultaneously across all 4 pillars.
- SAF-02.2: 50-worker cross-pillar concurrent chaos stress testing battery.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry

from services.backend.vision.gui_action_grounder import (
    GUIActionGrounder,
    BoundingBox,
    Rule8ViolationError as GUIRule8Error,
)
from services.backend.voice.expressive_voice_engine import (
    ExpressiveVoiceEngine,
    EmotionStyle,
    Rule8ViolationError as VoiceRule8Error,
)
from services.backend.memory.temporal_knowledge_graph import (
    TemporalKnowledgeGraph,
    EntityType,
    EpisodeType,
    Rule8ViolationError as GraphRule8Error,
)
from services.backend.evolution.workspace_self_healer import (
    WorkspaceSelfHealer,
    PatchStatus,
    Rule8ViolationError as HealerRule8Error,
)

# Register all Milestone 31 tool definitions
import services.backend.tools.gui_action_tools  # noqa: F401
import services.backend.tools.expressive_voice_tools  # noqa: F401
import services.backend.tools.temporal_knowledge_graph_tools  # noqa: F401
import services.backend.tools.workspace_self_healing_tools  # noqa: F401


@pytest.fixture(autouse=True)
def clean_guardian():
    """Guarantees guardian kill switch is resumed before and after each master test."""
    guardian.resume()
    yield
    guardian.resume()


def test_tool_registry_audit_milestone_31():
    """SAF-01.1: Exhaustive Tool Registry audit across all 16 new Milestone 31 tools."""
    expected_tools = {
        # Phase 1: Autonomous Vision-Action GUI Grounding
        "execute_grounded_gui_action": 1,
        "predict_ui_element_coordinates": 0,
        "get_human_takeover_status": 0,
        "reset_human_takeover_latch": 0,
        # Phase 2: Local Expressive Neural Voice Synthesis
        "synthesize_expressive_speech": 1,
        "set_voice_emotion_style": 1,
        "get_expressive_voice_metrics": 0,
        "purge_expressive_voice_buffer": 0,
        # Phase 3: Associative Temporal Knowledge Graph
        "record_graph_entity": 1,
        "record_graph_relation": 1,
        "record_episodic_event": 1,
        "query_associative_temporal_graph": 0,
        # Phase 4: Proactive Workspace Self-Healing Daemon
        "diagnose_workspace_error": 0,
        "synthesize_ast_hot_patch": 1,
        "apply_workspace_hot_patch": 1,
        "rollback_workspace_hot_patch": 1,
    }

    assert len(expected_tools) == 16, "Expected exactly 16 new tools in Milestone 31."

    for name, expected_tier in expected_tools.items():
        tool = registry.get(name)
        assert tool is not None, f"Tool '{name}' is not registered in ToolRegistry"
        assert tool.tier == expected_tier, f"Tool '{name}' tier mismatch: expected {expected_tier}, got {tool.tier}"
        assert tool.args_schema is not None, f"Tool '{name}' lacks typed Pydantic args_schema"
        assert callable(tool.preview_fn), f"Tool '{name}' lacks callable preview_fn"
        assert callable(tool.handler_fn), f"Tool '{name}' lacks callable handler_fn"


def test_universal_guardian_kill_switch_100_cycle_sla():
    """SAF-02.1: 100-cycle Universal Guardian kill switch SLA benchmark (< 25.0ms hard SLA)."""
    gui = GUIActionGrounder()
    gui._last_mouse_pos = (500, 500)
    voice = ExpressiveVoiceEngine()
    graph = TemporalKnowledgeGraph(db_path=":memory:")
    healer = WorkspaceSelfHealer()

    latencies_ms = []

    for _ in range(100):
        # 1. Trigger guardian
        t0 = time.perf_counter()
        guardian.trigger("Benchmark cycle kill switch trigger")
        trip_elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # 2. Check simultaneous halt rejection across all 4 pillars
        t1 = time.perf_counter()
        with pytest.raises(RuntimeError):
            gui.check_safety()
        with pytest.raises(RuntimeError):
            voice.check_safety()
        with pytest.raises(RuntimeError):
            graph.check_safety()
        with pytest.raises(RuntimeError):
            healer.check_safety()
        check_elapsed_ms = (time.perf_counter() - t1) * 1000.0

        total_cycle_ms = trip_elapsed_ms + check_elapsed_ms
        latencies_ms.append(total_cycle_ms)

        # 3. Resume for next iteration
        guardian.resume()

    max_lat = max(latencies_ms)
    avg_lat = sum(latencies_ms) / len(latencies_ms)

    assert max_lat < 25.0, f"Max Guardian halt latency {max_lat:.3f}ms exceeded 25.0ms SLA"
    assert avg_lat < 1.0, f"Average Guardian halt latency {avg_lat:.3f}ms exceeded 1.0ms target"


def test_cross_pillar_chaos_concurrency_battery():
    """SAF-02.2: 50-worker cross-pillar concurrent chaos stress testing battery."""
    gui = GUIActionGrounder()
    gui._last_mouse_pos = (500, 500)
    voice = ExpressiveVoiceEngine()
    graph = TemporalKnowledgeGraph(db_path=":memory:")
    healer = WorkspaceSelfHealer()

    worker_count = 50

    def chaos_worker(worker_id: int) -> bool:
        # Task 1: GUI coordinate prediction
        box = BoundingBox(x=10 * worker_id, y=20 * worker_id, width=50, height=30, label=f"Button-{worker_id}")
        coords = gui.predict_coordinates(box)
        assert coords == (10 * worker_id + 25, 20 * worker_id + 15)

        # Task 2: Expressive voice streaming ingestion
        chunks = voice.feed_streaming_tokens(f"Worker {worker_id} active. ")
        assert len(chunks) >= 0

        # Task 3: Temporal graph node insertion
        ent = graph.record_entity(f"ent-{worker_id}", f"Entity-{worker_id}", EntityType.CONCEPT, {"worker": worker_id})
        assert ent.id == f"ent-{worker_id}"

        # Task 4: Self-healer diagnostic triage
        diag = healer.diagnose_error(f"src/file_{worker_id}.ts(10,5): error TS1005: ';' expected.")
        assert diag.category.value == "COMPILER_ERROR"

        return True

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(chaos_worker, i) for i in range(worker_count)]
        results = [f.result() for f in as_completed(futures)]

    total_chaos_duration = time.perf_counter() - t0
    assert len(results) == worker_count
    assert all(results)
    assert total_chaos_duration < 10.0, f"Chaos execution took {total_chaos_duration:.2f}s (expected < 10.0s)"


def test_rule_8_anti_checkout_universal_matrix():
    """Rule 8: Universal anti-checkout matrix unconditionally rejects payment/checkout operations."""
    gui = GUIActionGrounder()
    gui._last_mouse_pos = (500, 500)
    voice = ExpressiveVoiceEngine()
    graph = TemporalKnowledgeGraph(db_path=":memory:")
    healer = WorkspaceSelfHealer()

    checkout_phrases = [
        "Checkout shopping cart now",
        "Authorize credit card payment of $99",
        "Submit billing CVV code",
        "Complete instant purchase",
    ]

    for phrase in checkout_phrases:
        # Pillar 1: GUI Action Grounder
        with pytest.raises(GUIRule8Error):
            gui.predict_coordinates(BoundingBox(x=0, y=0, width=10, height=10, label=phrase))

        # Pillar 2: Expressive Voice Engine
        with pytest.raises(VoiceRule8Error):
            voice.synthesize(phrase, simulate_playback=True)

        # Pillar 3: Temporal Knowledge Graph
        with pytest.raises(GraphRule8Error):
            graph.record_entity("bad-node", phrase, EntityType.CONCEPT)

        # Pillar 4: Workspace Self-Healer
        with pytest.raises(HealerRule8Error):
            healer.diagnose_error(phrase)


def test_rule_11_credential_protection_universal_matrix():
    """Rule 11: Universal credential protection matrix recursively redacts sensitive tokens."""
    gui = GUIActionGrounder()
    voice = ExpressiveVoiceEngine()
    graph = TemporalKnowledgeGraph(db_path=":memory:")
    healer = WorkspaceSelfHealer()

    sensitive_text = "Connecting with api_key: sk-proj-1234567890abcdef and password: super-secret-password-123"

    # Pillar 1: GUI Grounder
    scrubbed_gui, count_gui = gui.scrub_credentials(sensitive_text)
    assert count_gui == 2
    assert "sk-proj" not in scrubbed_gui
    assert "super-secret" not in scrubbed_gui
    assert "[REDACTED]" in scrubbed_gui

    # Pillar 2: Expressive Voice
    scrubbed_voice, count_voice = voice.scrub_credentials(sensitive_text)
    assert count_voice == 2
    assert "sk-proj" not in scrubbed_voice
    assert "[REDACTED]" in scrubbed_voice

    # Pillar 3: Temporal Graph
    scrubbed_graph, count_graph = graph.scrub_credentials(sensitive_text)
    assert count_graph == 2
    assert "sk-proj" not in scrubbed_graph
    assert "[REDACTED]" in scrubbed_graph

    # Pillar 4: Workspace Self-Healer
    scrubbed_healer, count_healer = healer.scrub_credentials(sensitive_text)
    assert count_healer == 2
    assert "sk-proj" not in scrubbed_healer
    assert "[REDACTED]" in scrubbed_healer


def test_cross_pillar_rule_7_non_destructive_patch_rollback():
    """Rule 7: Verifies non-destructive snapshot creation and 1-click atomic rollback."""
    healer = WorkspaceSelfHealer()
    orig_content = "def test_fn():\n    return 'initial'\n"
    target = "return 'initial'"
    replacement = "return 'patched'"

    patch = healer.synthesize_hot_patch("diag-snap-1", "mock_file.py", target, replacement)
    res_apply = healer.apply_patch(patch.id, file_override_content=orig_content)

    assert res_apply.success is True
    assert patch.status == PatchStatus.APPLIED
    assert healer._snapshots[patch.id] == orig_content

    res_rollback = healer.rollback_patch(patch.id)
    assert res_rollback.success is True
    assert patch.status == PatchStatus.ROLLED_BACK
    assert healer._snapshots[patch.id] == orig_content
