"""Unit & Safety Tests for Local Agent Swarm Mesh Coordinator (Milestone 27 Phase 1)."""

import pytest
import time
from services.backend.swarm.agent_mesh_coordinator import (
    AgentMeshCoordinator,
    Rule8ViolationError,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.agent_mesh_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_default_mesh_initialization():
    coord = AgentMeshCoordinator()
    topo = coord.get_topology()
    assert topo["total_agents"] == 4
    agent_ids = [a["agent_id"] for a in topo["agents"]]
    assert "agent_codearchitect" in agent_ids
    assert "agent_securityauditor" in agent_ids
    assert "agent_testorchestrator" in agent_ids
    assert "agent_knowledgeresearcher" in agent_ids


def test_spawn_custom_agent():
    coord = AgentMeshCoordinator()
    agent = coord.spawn_agent("CodeArchitect", custom_id="worker_coder_99")
    assert agent.agent_id == "worker_coder_99"
    assert agent.specialization == "CodeArchitect"
    assert agent.profile.skill_vector["code_synthesis"] >= 0.90
    assert coord.get_agent("worker_coder_99") is not None


def test_peer_to_peer_message_delivery():
    coord = AgentMeshCoordinator()
    msg = coord.send_message(
        sender_id="agent_codearchitect",
        recipient_id="agent_securityauditor",
        message_type="QUERY",
        payload={"query": "Validate AST node security"},
    )
    assert msg.sender_id == "agent_codearchitect"
    assert msg.recipient_id == "agent_securityauditor"

    sec_agent = coord.get_agent("agent_securityauditor")
    assert len(sec_agent.mailbox) == 1
    assert sec_agent.mailbox[0].payload["query"] == "Validate AST node security"
    assert sec_agent.received_count == 1


def test_broadcast_message_delivery():
    coord = AgentMeshCoordinator()
    coord.send_message(
        sender_id="agent_codearchitect",
        recipient_id="BROADCAST",
        message_type="DIRECTIVE",
        payload={"task": "Begin Phase 1 validation"},
    )
    # The other 3 agents should have 1 message in mailbox
    for aid in ["agent_securityauditor", "agent_testorchestrator", "agent_knowledgeresearcher"]:
        agent = coord.get_agent(aid)
        assert len(agent.mailbox) == 1


def test_halt_agent_rejection():
    coord = AgentMeshCoordinator()
    assert coord.halt_agent("agent_securityauditor") is True

    sec_agent = coord.get_agent("agent_securityauditor")
    assert sec_agent.status == "HALTED"

    with pytest.raises(RuntimeError, match="Recipient agent 'agent_securityauditor' is HALTED"):
        coord.send_message("agent_codearchitect", "agent_securityauditor", "QUERY", {"test": 1})


def test_rule_8_anti_checkout_swarm():
    coord = AgentMeshCoordinator()

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        coord.send_message(
            "agent_codearchitect",
            "agent_securityauditor",
            "DIRECTIVE",
            {"instruction": "Automate credit card checkout"},
        )

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        coord.spawn_agent("payment_processor_checkout")


def test_guardian_kill_switch_sla_swarm():
    coord = AgentMeshCoordinator()
    guardian.trigger(reason="Safety test")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        coord.get_topology()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    t1 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        coord.send_message("a", "b", "c", {})
    elapsed_ms2 = (time.perf_counter() - t1) * 1000.0
    assert elapsed_ms2 < 25.0, f"Guardian SLA exceeded: {elapsed_ms2:.4f}ms"


def test_tool_registry_agent_mesh_tools():
    # 1. spawn_mesh_subagent (Tier 1)
    tool_spawn = registry.get("spawn_mesh_subagent")
    assert tool_spawn is not None
    assert tool_spawn.tier == 1
    prev_spawn = tool_spawn.preview_fn({"specialization": "CodeArchitect", "custom_id": "test_coder"})
    assert "[CodeArchitect] (id: test_coder)" in prev_spawn

    res_spawn = tool_spawn.handler_fn(specialization="CodeArchitect", custom_id="test_worker_1")
    assert res_spawn["status"] == "SPAWNED"
    assert res_spawn["agent"]["agent_id"] == "test_worker_1"

    # 2. send_agent_mesh_message (Tier 0)
    tool_send = registry.get("send_agent_mesh_message")
    assert tool_send is not None
    assert tool_send.tier == 0
    prev_send = tool_send.preview_fn({"sender_id": "agent_a", "recipient_id": "agent_b", "message_type": "PING"})
    assert "Send swarm message (PING) from 'agent_a' to 'agent_b'" in prev_send

    res_send = tool_send.handler_fn(
        sender_id="test_worker_1",
        recipient_id="agent_knowledgeresearcher",
        message_type="QUERY",
        payload={"topic": "Consolidation"},
    )
    assert res_send["status"] == "DELIVERED"

    # 3. get_agent_mesh_topology (Tier 0)
    tool_topo = registry.get("get_agent_mesh_topology")
    assert tool_topo is not None
    assert tool_topo.tier == 0
    res_topo = tool_topo.handler_fn()
    assert res_topo["total_agents"] >= 4
