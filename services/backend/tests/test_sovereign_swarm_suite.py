"""
Unit & Integration Test Suite for Milestone 40 Phase 3: 5-Agent Sovereign Tactical Swarm & Hybrid LLM Super-Coordinator
Validates:
- 5-Agent Swarm roster registration & real-time status.
- Inter-agent message board pub/sub queue.
- Parallel multi-agent mission execution DAG with zero deadlocks.
- Sub-25ms Universal Guardian Kill Switch enforcement.
- ToolRegistry registration audit for all sovereign swarm tools.
"""

import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.orchestrator.sovereign_swarm import sovereign_swarm, SWARM_ROSTER
import services.backend.tools.sovereign_swarm_tools


@pytest.fixture(autouse=True)
def reset_swarm_test_environment():
    guardian.resume()
    sovereign_swarm.clear_state()
    yield
    guardian.resume()
    sovereign_swarm.clear_state()


def test_swarm_roster_and_status():
    """Verify all 5 specialized agents are registered with active hybrid routing."""
    status = sovereign_swarm.get_swarm_status()
    assert len(status["roster"]) == 5
    for expected_agent in ["Vanguard", "Sentinel", "Specter", "Synapse", "Prime"]:
        assert expected_agent in status["roster"]
        assert status["agent_states"][expected_agent] == "IDLE"

    assert "hybrid_routing" in status
    assert status["hybrid_routing"]["mode"] == "HYBRID_LOCAL_CLOUD"


def test_swarm_message_board_posting():
    """Verify thread-safe inter-agent message posting and retrieval."""
    post_res = sovereign_swarm.post_message(
        sender="Prime",
        recipient="Sentinel",
        message="Audit /proc memory pages for PID 1337",
        message_type="TASK_BRIEF"
    )
    assert post_res["success"] is True
    assert "message_id" in post_res

    board = sovereign_swarm.get_message_board(limit=10)
    assert len(board) >= 1
    last_msg = board[-1]
    assert last_msg["sender"] == "Prime"
    assert last_msg["recipient"] == "Sentinel"
    assert "Audit /proc" in last_msg["message"]


def test_dispatch_swarm_mission_parallel():
    """Verify parallel multi-agent mission dispatch executes all 5 agents with zero deadlocks."""
    res = sovereign_swarm.dispatch_swarm_mission("OPERATION_OMNI_SWEEP", target_scope="127.0.0.1")

    assert res["mission_name"] == "OPERATION_OMNI_SWEEP"
    assert res["verdict"] == "SWARM_MISSION_ACCOMPLISHED"
    assert res["agents_executed"] == 5
    assert len(res["results"]) == 5

    for agent in SWARM_ROSTER:
        assert agent in res["results"]
        assert "findings" in res["results"][agent]

    # Verify messages were posted to board
    board = sovereign_swarm.get_message_board()
    assert len(board) >= 6  # 1 initial brief + 5 status reports


def test_guardian_killswitch_swarm_sla():
    """Verify Universal Guardian Kill Switch halts swarm mission dispatch instantly (<25ms SLA)."""
    # Trigger emergency halt
    t0 = time.perf_counter()
    guardian.trigger("Swarm emergency kill-switch abort")
    abort_latency_ms = (time.perf_counter() - t0) * 1000.0
    assert abort_latency_ms < 25.0, f"Guardian trigger exceeded 25ms SLA: {abort_latency_ms}ms"

    # Verify all operations raise PermissionError synchronously
    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        sovereign_swarm.get_swarm_status()

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        sovereign_swarm.post_message("Prime", "ALL", "Should abort")

    with pytest.raises(PermissionError, match="Guardian kill switch active"):
        sovereign_swarm.dispatch_swarm_mission("ABORT_MISSION")


def test_sovereign_swarm_tool_registry():
    """Verify all 4 sovereign swarm tools are registered with correct risk tiers and valid schemas."""
    expected_tools = {
        "dispatch_sovereign_swarm": 1,
        "get_swarm_status": 0,
        "post_swarm_message": 0,
        "get_swarm_message_board": 0,
    }

    for tool_name, expected_tier in expected_tools.items():
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch: {tool_def.tier} != {expected_tier}"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' missing args_schema"
        assert callable(tool_def.preview_fn), f"Tool '{tool_name}' missing preview_fn"
        preview_text = tool_def.preview_fn({"mission_name": "TEST", "sender": "Prime", "recipient": "ALL"})
        assert isinstance(preview_text, str) and len(preview_text) > 0
