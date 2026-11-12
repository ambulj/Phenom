"""
Tests for Semantic Intent Memory Graph & Temporal Decision Reasoning Engine.
Part of Phenom 22.0 Sovereign Swarm Intelligence (MEM-03, RSN-01, SAF-01, SAF-02).
"""

import time
import pytest
from typing import Dict, Any

from services.backend.memory.temporal_intent_graph import (
    TemporalIntentGraph,
    TemporalIntentNode,
    temporal_intent_graph,
)
from services.backend.reasoning.decision_explainer import (
    DecisionExplainer,
    DecisionAlternative,
    decision_explainer,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.automation.gui_controller import Rule8ViolationError
import services.backend.tools.temporal_reasoning_tools as reasoning_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_record_preference_and_point_in_time_validity():
    """Verify recording preferences with timestamped validity."""
    graph = TemporalIntentGraph()
    node = graph.record_preference(
        category="coding_style",
        statement="Always write type annotations for all Python functions",
    )

    assert node.intent_id.startswith("intent_")
    assert node.category == "coding_style"
    assert node.is_active is True
    assert node.valid_until is None

    # Query active
    active = graph.query_active_preferences(category="coding_style")
    assert len(active) == 1
    assert active[0].intent_id == node.intent_id


def test_preference_supersession_and_non_destructive_lineage():
    """Verify Rule 7: superseding a preference seals valid_until without deletion and maintains lineage."""
    graph = TemporalIntentGraph()

    # V1
    n1 = graph.record_preference(
        category="toolchain",
        statement="Use Node 18 for local builds",
    )
    time.sleep(0.01)

    # V2 supersedes V1
    n2 = graph.record_preference(
        category="toolchain",
        statement="Use Node 20 LTS for local builds",
        supersedes_id=n1.intent_id,
    )
    time.sleep(0.01)

    # V3 supersedes V2
    n3 = graph.record_preference(
        category="toolchain",
        statement="Use Node 22 Current for local builds",
        supersedes_id=n2.intent_id,
    )

    # Verify V1 and V2 are sealed
    assert n1.is_active is False
    assert n1.valid_until is not None
    assert n1.superseded_by == n2.intent_id

    assert n2.is_active is False
    assert n2.valid_until is not None
    assert n2.superseded_by == n3.intent_id

    # Verify V3 is currently active
    assert n3.is_active is True
    assert n3.valid_until is None

    # Query active should only return V3
    active = graph.query_active_preferences(category="toolchain")
    assert len(active) == 1
    assert active[0].intent_id == n3.intent_id

    # Lineage must trace V1 -> V2 -> V3
    lineage = graph.get_preference_lineage(n2.intent_id)
    assert len(lineage) == 3
    assert [n.intent_id for n in lineage] == [n1.intent_id, n2.intent_id, n3.intent_id]


def test_conflict_detection_opposing_directives():
    """Verify detection of opposing active directives within the same domain."""
    graph = TemporalIntentGraph()
    graph.record_preference(category="ui", statement="Enable verbose logging and high detail output")
    graph.record_preference(category="ui", statement="Keep all responses concise and minimal")

    conflicts = graph.detect_conflicts(category="ui")
    assert len(conflicts) >= 1
    assert "verbose" in conflicts[0]["reason"] or "concise" in conflicts[0]["reason"]


def test_counterfactual_decision_reasoning_synthesis():
    """Verify synthesis of counterfactual decision rationales with citations and alternatives."""
    explainer = DecisionExplainer()
    explanation = explainer.explain_decision(
        objective="Refactor authentication system",
        chosen_plan="Topological Swarm DAG with Worktree Isolation",
    )

    assert explanation.decision_id.startswith("dec_")
    assert explanation.chosen_plan == "Topological Swarm DAG with Worktree Isolation"
    assert len(explanation.alternatives) >= 2
    assert any("[1] SAFETY.md" in c for c in explanation.citations)
    assert explanation.confidence >= 0.90

    # Verify alternative structures
    for alt in explanation.alternatives:
        assert alt.name
        assert alt.rejected_reason
        assert alt.score <= 0.50


def test_guardian_kill_switch_sla_halt():
    """Guardian trigger must synchronously interrupt decision reasoning in < 25.0ms SLA."""
    guardian.trigger()
    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        decision_explainer.explain_decision(
            objective="Emergency test",
            chosen_plan="Halted plan",
        )
    latency_ms = (time.perf_counter() - t0) * 1000.0
    assert latency_ms < 25.0, f"Guardian SLA exceeded: {latency_ms:.4f}ms >= 25.0ms"


def test_rule_8_anti_checkout_enforcement():
    """Rule 8: Attempting to store payment/credit card preferences must raise Rule8ViolationError."""
    with pytest.raises(Rule8ViolationError):
        reasoning_tools.record_temporal_preference(
            category="finance",
            statement="Store user credit card number for one-click payment checkout",
        )


def test_tool_registry_and_previews():
    """Verify tool registration and preview generator functions in ToolRegistry."""
    tool_names = [
        "record_temporal_preference",
        "query_temporal_intent_graph",
        "explain_decision_rationale",
    ]
    for name in tool_names:
        tool = registry.get(name)
        assert tool is not None, f"Tool {name} is not registered in ToolRegistry"
        assert callable(tool.handler_fn)

    # Preview generators
    preview_rec = registry.get("record_temporal_preference").generate_preview({
        "category": "coding",
        "statement": "Enforce strict TypeScript",
    })
    assert "Record temporal preference" in preview_rec

    preview_exp = registry.get("explain_decision_rationale").generate_preview({
        "objective": "Build backend",
        "chosen_plan": "FastAPI with WebSockets",
    })
    assert "counterfactual explanation" in preview_exp.lower()
