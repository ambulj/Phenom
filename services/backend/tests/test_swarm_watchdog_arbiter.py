"""Unit & Safety Tests for Byzantine Worker Watchdog & Failover Arbiter (Milestone 27 Phase 4)."""

import pytest
import time
from services.backend.swarm.byzantine_watchdog import (
    ByzantineWatchdog,
    WorkerHealthReport,
)
from services.backend.swarm.failover_arbiter import FailoverArbiter
from services.backend.swarm.agent_mesh_coordinator import AgentMeshCoordinator, Rule8ViolationError
from services.backend.swarm.task_auction_engine import TaskAuctionEngine
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.swarm_watchdog_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_watchdog_record_heartbeat_healthy():
    coord = AgentMeshCoordinator()
    watchdog = ByzantineWatchdog(coordinator=coord)
    report = watchdog.record_heartbeat("agent_codearchitect", latency_ms=15.0, is_error=False)
    assert report.health_status == "HEALTHY"
    assert report.anomaly_score < 0.20


def test_watchdog_record_heartbeat_byzantine():
    coord = AgentMeshCoordinator()
    watchdog = ByzantineWatchdog(coordinator=coord)
    # Trigger repeated high latency and errors
    for _ in range(4):
        watchdog.record_heartbeat("agent_codearchitect", latency_ms=850.0, is_error=True)

    report = watchdog.record_heartbeat("agent_codearchitect", latency_ms=1200.0, is_error=True)
    assert report.health_status == "BYZANTINE_FAULT"
    assert report.anomaly_score >= 0.70


def test_failover_arbiter_quarantine():
    coord = AgentMeshCoordinator()
    engine = TaskAuctionEngine(coordinator=coord)
    # Assign task_002 to codearchitect
    engine.conduct_auction("task_002")
    assert engine.get_dag()[1].assigned_agent_id == "agent_codearchitect"

    arbiter = FailoverArbiter(coordinator=coord, auction_engine=engine)
    record = arbiter.quarantine_worker("agent_codearchitect", reason="Heartbeat timeout > 2000ms")

    assert record.faulty_agent_id == "agent_codearchitect"
    assert "task_002" in record.orphaned_task_ids

    # Agent is halted in mesh
    assert coord.get_agent("agent_codearchitect").status == "HALTED"
    # Task is reset to OPEN
    assert engine.get_dag()[1].status == "OPEN"
    assert engine.get_dag()[1].assigned_agent_id is None


def test_failover_arbiter_reassign():
    coord = AgentMeshCoordinator()
    engine = TaskAuctionEngine(coordinator=coord)
    engine.conduct_auction("task_002")

    arbiter = FailoverArbiter(coordinator=coord, auction_engine=engine)
    arbiter.quarantine_worker("agent_codearchitect")

    # Reassign orphaned tasks to healthy remaining agents
    awards = arbiter.reassign_orphaned_tasks(["task_002"])
    assert len(awards) == 1
    assert awards[0]["task_id"] == "task_002"
    assert awards[0]["status"] == "AWARDED"
    # Winner should be one of the other healthy agents (e.g. securityauditor or testorchestrator)
    assert awards[0]["winning_agent_id"] != "agent_codearchitect"


def test_rule_8_anti_checkout_watchdog():
    coord = AgentMeshCoordinator()
    watchdog = ByzantineWatchdog(coordinator=coord)
    arbiter = FailoverArbiter(coordinator=coord)

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        watchdog.record_heartbeat("agent_payment_processor_checkout")

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        arbiter.quarantine_worker("agent_a", reason="Billing and checkout error")


def test_guardian_kill_switch_sla_watchdog():
    coord = AgentMeshCoordinator()
    watchdog = ByzantineWatchdog(coordinator=coord)
    arbiter = FailoverArbiter(coordinator=coord)
    guardian.trigger(reason="Safety test")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        watchdog.inspect_health()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    t1 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        arbiter.quarantine_worker("agent_codearchitect")
    elapsed_ms2 = (time.perf_counter() - t1) * 1000.0
    assert elapsed_ms2 < 25.0, f"Guardian SLA exceeded: {elapsed_ms2:.4f}ms"


def test_tool_registry_swarm_watchdog_tools():
    # 1. inspect_swarm_health (Tier 0)
    tool_insp = registry.get("inspect_swarm_health")
    assert tool_insp is not None
    assert tool_insp.tier == 0
    res_insp = tool_insp.handler_fn()
    assert res_insp["worker_count"] >= 4

    # 2. arbitrate_byzantine_fault (Tier 1)
    tool_arb = registry.get("arbitrate_byzantine_fault")
    assert tool_arb is not None
    assert tool_arb.tier == 1
    prev_arb = tool_arb.preview_fn({"agent_id": "worker_99", "reason": "Timeout"})
    assert "Quarantine worker node 'worker_99'" in prev_arb

    res_arb = tool_arb.handler_fn(agent_id="agent_knowledgeresearcher", reason="Test fault")
    assert res_arb["status"] == "QUARANTINED"

    # 3. reassign_orphaned_tasks (Tier 1)
    tool_reassign = registry.get("reassign_orphaned_tasks")
    assert tool_reassign is not None
    assert tool_reassign.tier == 1
    res_reassign = tool_reassign.handler_fn()
    assert res_reassign["status"] == "REASSIGNMENT_COMPLETE"
