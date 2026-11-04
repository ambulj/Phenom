import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.cognitive_twin_tools as ctt
from services.backend.schemas.cognitive_twin import EpisodicNodeType


def test_cognitive_twin_tools_registered_in_registry():
    expected_tools = [
        ("cognitive_twin_get_status", 0),
        ("cognitive_twin_query_graph", 0),
        ("cognitive_twin_ingest_episode", 1),
        ("cognitive_twin_prune_graph", 1),
    ]

    for tool_name, expected_tier in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool {tool_name} not registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool {tool_name} tier mismatch"


def test_cognitive_twin_tier_0_queries_execute():
    if guardian.is_halted:
        guardian.resume()

    status_res = ctt.cognitive_twin_get_status(include_anticipations=True)
    assert "total_nodes" in status_res
    assert "total_edges" in status_res
    assert "is_locked" in status_res

    query_res = ctt.cognitive_twin_query_graph(node_type=EpisodicNodeType.ACTIVITY)
    assert "nodes" in query_res
    assert "count" in query_res


def test_cognitive_twin_tier_1_controls_with_preview():
    if guardian.is_halted:
        guardian.resume()

    # Ingest preview
    tool_ingest = registry.get("cognitive_twin_ingest_episode")
    preview_ingest = tool_ingest.preview_fn({
        "activity_label": "Writing safety test cases",
        "node_type": "activity",
        "related_labels": ["Testing"],
    })
    assert "Writing safety test cases" in preview_ingest

    res_ingest = ctt.cognitive_twin_ingest_episode(
        activity_label="Writing safety test cases",
        node_type=EpisodicNodeType.ACTIVITY,
        related_labels=["Testing"],
    )
    assert res_ingest["status"] == "ingested"
    assert res_ingest["node"]["label"] == "Writing safety test cases"

    # Prune preview
    tool_prune = registry.get("cognitive_twin_prune_graph")
    preview_prune = tool_prune.preview_fn({"min_affinity_weight": 0.20})
    assert "0.2" in preview_prune

    res_prune = ctt.cognitive_twin_prune_graph(min_affinity_weight=0.01)
    assert res_prune["status"] == "pruned"


def test_cognitive_twin_tools_fail_closed_under_guardian_halt():
    try:
        guardian.trigger("Cognitive Twin Safety Test Halt")
        assert guardian.is_halted

        with pytest.raises(PermissionError):
            ctt.cognitive_twin_get_status()

        with pytest.raises(PermissionError):
            ctt.cognitive_twin_query_graph()

        with pytest.raises(PermissionError):
            ctt.cognitive_twin_ingest_episode(activity_label="Test blocked")

        with pytest.raises(PermissionError):
            ctt.cognitive_twin_prune_graph()
    finally:
        guardian.resume()
