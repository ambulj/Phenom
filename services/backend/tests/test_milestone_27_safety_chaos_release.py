"""Milestone 27.0 Master Safety Audit, Chaos Concurrency Battery & Release Verification.

Validates all 12 Milestone 27 tools, benchmarks 100-cycle Guardian kill switch SLA (< 25.0ms),
runs cross-pillar concurrent chaos stress tests, and verifies Rule 8 invariant compliance.
"""

import concurrent.futures
import pytest
import time
from typing import List, Dict, Any

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.swarm.subagent_registry import SPECIALIST_PROFILES
from services.backend.swarm.agent_mesh_coordinator import (
    AgentMeshCoordinator,
    Rule8ViolationError,
)
from services.backend.swarm.capability_bidder import CapabilityBidder
from services.backend.swarm.task_auction_engine import TaskAuctionEngine
from services.backend.swarm.crdt_consensus_engine import CRDTStateRegister
from services.backend.swarm.state_reconciler import StateReconciler
from services.backend.swarm.byzantine_watchdog import ByzantineWatchdog
from services.backend.swarm.failover_arbiter import FailoverArbiter

# Import all tool modules to ensure registration
import services.backend.tools.agent_mesh_tools
import services.backend.tools.task_auction_tools
import services.backend.tools.swarm_consensus_tools
import services.backend.tools.swarm_watchdog_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_milestone_27_tool_registry_audit():
    """Verify all 12 Milestone 27 tools are registered with schemas and preview generators."""
    m27_tools = [
        # Phase 1: Mesh Coordinator & Specialist Subagents
        ("spawn_mesh_subagent", 1),
        ("send_agent_mesh_message", 0),
        ("get_agent_mesh_topology", 0),
        # Phase 2: Task Auction & Capability Bidding
        ("auction_task_to_swarm", 1),
        ("evaluate_worker_bids", 0),
        ("get_swarm_task_dag", 0),
        # Phase 3: CRDT State & Consensus Engine
        ("propose_state_crdt_delta", 1),
        ("reconcile_swarm_consensus", 0),
        ("get_lamport_vector_clocks", 0),
        # Phase 4: Byzantine Watchdog & Failover Arbiter
        ("inspect_swarm_health", 0),
        ("arbitrate_byzantine_fault", 1),
        ("reassign_orphaned_tasks", 1),
    ]

    for tool_name, expected_tier in m27_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' expected tier {expected_tier}, got {tool_def.tier}"
        assert tool_def.preview_fn is not None, f"Tool '{tool_name}' must declare a callable preview function"
        assert tool_def.args_schema is not None, f"Tool '{tool_name}' must declare a valid Pydantic args_schema"
        assert tool_def.handler_fn is not None, f"Tool '{tool_name}' must declare a handler function"


def test_guardian_kill_switch_100_cycle_sla():
    """Benchmark 100 consecutive Guardian kill switch halts to verify SLA strictly < 25.0ms (typical < 1.0ms)."""
    coordinator = AgentMeshCoordinator()
    coordinator.spawn_agent("CodeArchitect", custom_id="arch_sla_1")
    auction = TaskAuctionEngine(coordinator=coordinator)
    crdt = CRDTStateRegister()
    watchdog = ByzantineWatchdog(coordinator=coordinator)
    arbiter = FailoverArbiter(coordinator=coordinator, auction_engine=auction)

    timings_ms: List[float] = []

    for _ in range(100):
        guardian.trigger(reason="100_cycle_sla_test_m27")
        t0 = time.perf_counter()
        with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
            # Exercise multiple swarm subsystems under tripped state
            coordinator.send_message("arch_sla_1", "BROADCAST", "QUERY", {"test": "val"})
            auction.create_contract("Test task", {"architecture": 0.8})
            crdt.apply_delta("arch_sla_1", "state_key", "value_1")
            watchdog.inspect_health()
            arbiter.quarantine_worker("arch_sla_1", "Tripped check")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        timings_ms.append(elapsed_ms)
        guardian.resume()

    avg_ms = sum(timings_ms) / len(timings_ms)
    max_ms = max(timings_ms)

    assert avg_ms < 1.0, f"Guardian SLA average exceeds 1.0ms: {avg_ms:.4f}ms"
    assert max_ms < 25.0, f"Guardian SLA max exceeds hard limit 25.0ms: {max_ms:.4f}ms"


def test_cross_pillar_chaos_concurrency_stress():
    """Run concurrent multi-threaded stress tests across all 4 Milestone 27 pillars without deadlocks or race conditions."""
    coordinator = AgentMeshCoordinator()
    # coordinator already has agent_codearchitect, agent_securityauditor, agent_testorchestrator, agent_knowledgeresearcher

    auction = TaskAuctionEngine(coordinator=coordinator)
    crdt = CRDTStateRegister()
    reconciler = StateReconciler(register=crdt)
    watchdog = ByzantineWatchdog(coordinator=coordinator)
    arbiter = FailoverArbiter(coordinator=coordinator, auction_engine=auction)

    def worker_mesh(idx: int):
        coordinator.send_message(
            sender_id="agent_codearchitect",
            recipient_id="agent_securityauditor",
            message_type="QUERY",
            payload={"request": f"audit_request_{idx}", "priority": "NORMAL"},
        )
        return coordinator.get_topology()

    def worker_auction(idx: int):
        contract = auction.create_contract(
            title=f"Subtask_{idx}",
            required_skills={"code_synthesis": 0.7, "security_audit": 0.3},
        )
        auction.conduct_auction(contract.task_id)
        return auction.get_dag()

    def worker_crdt(idx: int):
        return reconciler.reconcile_proposals([
            {
                "agent_id": "agent_testorchestrator",
                "key": f"shared_metric_{idx % 3}",
                "value": {"score": idx * 10, "step": idx},
            }
        ])

    def worker_watchdog(idx: int):
        watchdog.record_heartbeat("agent_knowledgeresearcher", latency_ms=12.5 + idx)
        return watchdog.inspect_health()

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = []
        for i in range(10):
            futures.append(pool.submit(worker_mesh, i))
            futures.append(pool.submit(worker_auction, i))
            futures.append(pool.submit(worker_crdt, i))
            futures.append(pool.submit(worker_watchdog, i))

        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    total_time = time.perf_counter() - t0
    assert len(results) == 40
    assert total_time < 5.0, f"Chaos concurrency test took too long: {total_time:.2f}s"


def test_rule_8_anti_checkout_cross_pillar_compliance():
    """Verify strict Rule 8 payment/checkout keyword screening across all 4 pillars."""
    coordinator = AgentMeshCoordinator()
    coordinator.spawn_agent("CodeArchitect", custom_id="arch_r8")
    auction = TaskAuctionEngine(coordinator=coordinator)
    crdt = CRDTStateRegister()
    watchdog = ByzantineWatchdog(coordinator=coordinator)
    arbiter = FailoverArbiter(coordinator=coordinator, auction_engine=auction)

    # 1. Mesh pillar (Message & Payload screening)
    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        coordinator.send_message(
            sender_id="arch_r8",
            recipient_id="BROADCAST",
            message_type="DIRECTIVE",
            payload={"action": "Please proceed to checkout and enter credit card details"},
        )

    # 2. Auction pillar (Task Title & Directive screening)
    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        auction.create_contract(
            title="Integrate stripe payment and process purchase billing",
            required_skills={"security_audit": 0.9},
        )

    # 3. CRDT pillar (State Key & Value screening)
    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        crdt.apply_delta(
            agent_id="arch_r8",
            key="checkout_payment_gateway",
            value={"status": "pay_now"},
        )

    # 4. Watchdog & Arbiter pillar (Fault Reason & Node Screening)
    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        watchdog.record_heartbeat("agent_credit_card_checkout")

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        arbiter.quarantine_worker("arch_r8", "Agent attempted to trigger order checkout")
