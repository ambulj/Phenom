"""Unit & Safety Tests for Decentralized Task Auction & Capability-Based Bidding (Milestone 27 Phase 2)."""

import pytest
import time
from services.backend.swarm.task_auction_engine import (
    TaskAuctionEngine,
    TaskContract,
)
from services.backend.swarm.capability_bidder import CapabilityBidder
from services.backend.swarm.agent_mesh_coordinator import AgentMeshCoordinator, Rule8ViolationError
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.task_auction_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_dag_initialization_and_dependencies():
    coord = AgentMeshCoordinator()
    engine = TaskAuctionEngine(coordinator=coord)
    dag = engine.get_dag()
    assert len(dag) >= 3
    t1 = next(t for t in dag if t.task_id == "task_001")
    t2 = next(t for t in dag if t.task_id == "task_002")
    assert t1.task_id in t2.prerequisites


def test_decompose_objective_into_dag():
    coord = AgentMeshCoordinator()
    engine = TaskAuctionEngine(coordinator=coord)
    contracts = engine.decompose_objective("Implement Secure Token Storage")
    assert len(contracts) == 3
    assert "Research & Audit" in contracts[0].title
    assert "Synthesize Architecture" in contracts[1].title
    assert "Execute Chaos" in contracts[2].title
    assert contracts[0].task_id in contracts[1].prerequisites
    assert contracts[1].task_id in contracts[2].prerequisites


def test_capability_bidder_calculation():
    coord = AgentMeshCoordinator()
    coder = coord.get_agent("agent_codearchitect")
    bid = CapabilityBidder.calculate_bid(
        agent=coder,
        task_id="task_test_01",
        required_skills={"code_synthesis": 0.9, "ast_manipulation": 0.8},
    )
    assert bid is not None
    assert bid.suitability_score >= 0.85
    assert bid.estimated_latency_ms < 60.0


def test_conduct_auction_award():
    coord = AgentMeshCoordinator()
    engine = TaskAuctionEngine(coordinator=coord)

    # Auction task_002 (Synthesize Core Feature Implementation)
    result = engine.conduct_auction("task_002")
    assert result["status"] == "AWARDED"
    # CodeArchitect should win code synthesis task
    assert result["winning_specialization"] == "CodeArchitect"
    assert result["suitability_score"] >= 0.85

    dag = {t.task_id: t for t in engine.get_dag()}
    assert dag["task_002"].status == "AWARDED"
    assert dag["task_002"].assigned_agent_id == result["winning_agent_id"]


def test_mark_completed():
    coord = AgentMeshCoordinator()
    engine = TaskAuctionEngine(coordinator=coord)
    assert engine.mark_completed("task_001") is True
    dag = {t.task_id: t for t in engine.get_dag()}
    assert dag["task_001"].status == "COMPLETED"


def test_rule_8_anti_checkout_auction():
    coord = AgentMeshCoordinator()
    engine = TaskAuctionEngine(coordinator=coord)

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        engine.create_contract("Process payment and billing checkout", {"code_synthesis": 0.8})

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        engine.decompose_objective("Automate credit card checkout transactions")


def test_guardian_kill_switch_sla_auction():
    coord = AgentMeshCoordinator()
    engine = TaskAuctionEngine(coordinator=coord)
    guardian.trigger(reason="Safety test")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        engine.get_dag()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    t1 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        engine.conduct_auction("task_001")
    elapsed_ms2 = (time.perf_counter() - t1) * 1000.0
    assert elapsed_ms2 < 25.0, f"Guardian SLA exceeded: {elapsed_ms2:.4f}ms"


def test_tool_registry_task_auction_tools():
    # 1. auction_task_to_swarm (Tier 1)
    tool_auction = registry.get("auction_task_to_swarm")
    assert tool_auction is not None
    assert tool_auction.tier == 1
    prev_auc = tool_auction.preview_fn({"task_id": "task_001"})
    assert "Auction task contract 'task_001'" in prev_auc

    res_auc = tool_auction.handler_fn(task_id="task_001")
    assert res_auc["status"] == "AUCTION_COMPLETE"
    assert res_auc["result"]["status"] == "AWARDED"

    # 2. evaluate_worker_bids (Tier 0)
    tool_eval = registry.get("evaluate_worker_bids")
    assert tool_eval is not None
    assert tool_eval.tier == 0
    res_eval = tool_eval.handler_fn(task_id="task_003")
    assert res_eval["bid_count"] >= 4
    # TestOrchestrator should be top bidder for testing task
    assert res_eval["bids"][0]["specialization"] == "TestOrchestrator"

    # 3. get_swarm_task_dag (Tier 0)
    tool_dag = registry.get("get_swarm_task_dag")
    assert tool_dag is not None
    assert tool_dag.tier == 0
    res_dag = tool_dag.handler_fn()
    assert res_dag["contract_count"] >= 3
