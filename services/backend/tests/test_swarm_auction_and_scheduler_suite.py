"""Comprehensive Unit Test Suite for Multi-Agent Task Auction Protocol & VRAM Governance.

Phase 48-01: SWARM-01, SWARM-02, SWARM-03.
Tests agent role profiles, task auction bidding, time-sliced local scheduler serialization,
VRAM peak governance (<5.5 GB), sub-25ms Guardian kill switch SLA, and ToolRegistry tools.
"""

import asyncio
import time
import pytest
from typing import Dict, Any

from services.backend.schemas.swarm_auction import (
    AgentRole,
    AgentProfile,
    TaskBid,
    AuctionResult,
    VRAMMetrics,
    ScheduledTask,
    SwarmTaskStatus,
)
from services.backend.swarm.agent_roles import AgentRoleRegistry
from services.backend.swarm.auction_engine import TaskAuctionEngine
from services.backend.swarm.scheduler import SwarmScheduler, VRAMLimitExceededError
import services.backend.tools.swarm_tools
from services.backend.safety.registry import registry


# ============================================================================
# 1. Pydantic Schemas Validation
# ============================================================================

def test_swarm_auction_schemas():
    """Verify schema bounds, default values, and serialization."""
    bid = TaskBid(
        agent_role=AgentRole.CODER,
        node_id="node_123",
        fitness_score=0.88,
        estimated_tokens=850,
        estimated_duration_sec=1.5,
        confidence=0.92,
        rationale="Top fitness for code manipulation",
    )
    dumped = bid.model_dump()
    assert dumped["agent_role"] == "coder"
    assert dumped["fitness_score"] == 0.88
    assert dumped["confidence"] == 0.92

    # VRAMMetrics test
    vram = VRAMMetrics(
        allocated_mb=4800.0,
        reserved_mb=5000.0,
        peak_mb=5000.0,
        max_allowed_mb=5632.0,
        is_safe=True,
    )
    assert vram.is_safe is True
    assert vram.peak_mb == 5000.0

    # ScheduledTask test
    task = ScheduledTask(
        task_id="t_001",
        node_id="node_123",
        tool_name="validate_ast_syntax",
        arguments={"code": "x = 1"},
        assigned_role=AgentRole.CODER,
    )
    assert task.status == SwarmTaskStatus.PENDING
    assert task.tool_name == "validate_ast_syntax"


# ============================================================================
# 2. Agent Role Registry & Capability Profiles (SWARM-01)
# ============================================================================

def test_agent_role_registry_profiles():
    """Verify all 4 specialized roles, system prompts, priorities, and affinities."""
    all_roles = AgentRoleRegistry.get_all_roles()
    assert len(all_roles) == 4
    assert AgentRole.ARCHITECT in all_roles
    assert AgentRole.CODER in all_roles
    assert AgentRole.SECURITY_AUDITOR in all_roles
    assert AgentRole.WEB_SCOUT in all_roles

    # Check priority ordering
    profiles = AgentRoleRegistry.list_profiles()
    assert profiles[0].role == AgentRole.ARCHITECT  # Priority 10
    assert profiles[1].role == AgentRole.SECURITY_AUDITOR  # Priority 9
    assert profiles[2].role == AgentRole.CODER  # Priority 8
    assert profiles[3].role == AgentRole.WEB_SCOUT  # Priority 7

    # Check tool affinities
    assert AgentRoleRegistry.get_tool_affinity(AgentRole.CODER, "apply_workspace_diff") == 1.0
    assert AgentRoleRegistry.get_tool_affinity(AgentRole.SECURITY_AUDITOR, "check_mission_preconditions") == 1.0
    assert AgentRoleRegistry.get_tool_affinity(AgentRole.WEB_SCOUT, "deep_research_crawl") == 1.0
    assert AgentRoleRegistry.get_tool_affinity(AgentRole.ARCHITECT, "decompose_mission_goal") == 1.0

    # Default affinity for unlisted tool
    assert AgentRoleRegistry.get_tool_affinity(AgentRole.CODER, "unlisted_tool_xyz") == 0.1


# ============================================================================
# 3. Task Auction Engine Bidding & Winners (SWARM-02)
# ============================================================================

def test_task_auction_engine_fitness_and_bidding():
    """Verify fitness calculations, role bidding, and winner selection."""
    engine = TaskAuctionEngine()

    # Case 1: Coder task
    res_code = engine.conduct_auction_for_task(
        node_id="n_code",
        tool_name="validate_ast_syntax",
        node_title="AST Syntax Check",
        node_desc="Validate Python AST syntax for workspace patch",
    )
    assert res_code.winning_role == AgentRole.CODER
    assert res_code.winning_bid.fitness_score > 0.5
    assert len(res_code.all_bids) == 4

    # Case 2: Research task
    res_research = engine.conduct_auction_for_task(
        node_id="n_research",
        tool_name="deep_research_crawl",
        node_title="Deep Web Crawl",
        node_desc="Scrape arXiv and scientific papers on LLM agents",
    )
    assert res_research.winning_role == AgentRole.WEB_SCOUT
    assert res_research.winning_bid.fitness_score > 0.5

    # Case 3: Security audit task
    res_sec = engine.conduct_auction_for_task(
        node_id="n_security",
        tool_name="check_mission_preconditions",
        node_title="Precondition Audit",
        node_desc="Audit path traversal and safety preconditions before execution",
    )
    assert res_sec.winning_role == AgentRole.SECURITY_AUDITOR
    assert res_sec.winning_bid.fitness_score > 0.5

    # Case 4: Fallback to Architect for obscure task with low fitness
    res_obscure = engine.conduct_auction_for_task(
        node_id="n_obscure",
        tool_name="obscure_unknown_tool_xyz",
        node_title="Generic ambiguous objective",
        node_desc="Do something non-descript",
    )
    assert res_obscure.winning_role == AgentRole.ARCHITECT
    assert "Fallback assignment to Architect" in res_obscure.winning_bid.rationale


def test_task_auction_engine_dag_auction():
    """Verify multi-node DAG auction assignment and workload accounting."""
    engine = TaskAuctionEngine()
    tasks = [
        {
            "node_id": "step_1",
            "tool_name": "decompose_mission_goal",
            "title": "Decompose system goal",
            "description": "Architect DAG breakdown",
        },
        {
            "node_id": "step_2",
            "tool_name": "deep_research_crawl",
            "title": "Crawl documentation",
            "description": "Web research on API specs",
        },
        {
            "node_id": "step_3",
            "tool_name": "apply_workspace_diff",
            "title": "Apply workspace diff",
            "description": "Coding implementation patch",
        },
        {
            "node_id": "step_4",
            "tool_name": "check_mission_preconditions",
            "title": "Security audit",
            "description": "Preconditions and safety audit",
        },
    ]

    results = engine.conduct_auction_for_dag(tasks)
    assert len(results) == 4
    assert results["step_1"].winning_role == AgentRole.ARCHITECT
    assert results["step_2"].winning_role == AgentRole.WEB_SCOUT
    assert results["step_3"].winning_role == AgentRole.CODER
    assert results["step_4"].winning_role == AgentRole.SECURITY_AUDITOR

    # Verify active workloads tracked
    assert engine.active_workloads[AgentRole.ARCHITECT] >= 1
    assert engine.active_workloads[AgentRole.CODER] >= 1


# ============================================================================
# 4. Swarm Scheduler & VRAM Governance (SWARM-03)
# ============================================================================

@pytest.mark.asyncio
async def test_swarm_scheduler_time_slicing_and_queue():
    """Verify sequential FIFO task execution and serialized GPU lock."""
    scheduler = SwarmScheduler()
    execution_order = []

    def mock_executor(tool_name: str, args: Dict[str, Any]):
        execution_order.append(args.get("order"))
        return f"Executed {tool_name}"

    t1 = scheduler.enqueue_task("n1", "tool_a", {"order": 1}, AgentRole.ARCHITECT)
    t2 = scheduler.enqueue_task("n2", "tool_b", {"order": 2}, AgentRole.CODER)
    t3 = scheduler.enqueue_task("n3", "tool_c", {"order": 3}, AgentRole.WEB_SCOUT)

    assert len(scheduler.get_queue_status()) == 3
    results = await scheduler.run_all(mock_executor)

    assert len(results) == 3
    assert execution_order == [1, 2, 3]  # Strict FIFO order
    assert all(r.status == SwarmTaskStatus.COMPLETED for r in results)
    assert len(scheduler.get_history()) == 3


@pytest.mark.asyncio
async def test_swarm_scheduler_vram_governor():
    """Verify VRAM governor allows execution under 5.5 GB and halts when exceeded."""
    scheduler = SwarmScheduler(max_vram_mb=5632.0)

    # 1. Safe VRAM (4900 MB < 5632 MB)
    scheduler.set_simulated_vram(4900.0)
    vram_safe = scheduler.get_vram_metrics()
    assert vram_safe.is_safe is True

    t_safe = scheduler.enqueue_task("n_safe", "safe_tool", {}, AgentRole.CODER)
    res_safe = await scheduler.execute_task(t_safe, lambda t, a: "OK")
    assert res_safe.status == SwarmTaskStatus.COMPLETED

    # 2. Unsafe VRAM (6000 MB > 5632 MB)
    scheduler.set_simulated_vram(6000.0)
    vram_unsafe = scheduler.get_vram_metrics()
    assert vram_unsafe.is_safe is False

    t_unsafe = scheduler.enqueue_task("n_unsafe", "unsafe_tool", {}, AgentRole.CODER)
    with pytest.raises(VRAMLimitExceededError):
        await scheduler.execute_task(t_unsafe, lambda t, a: "OK")

    assert t_unsafe.status == SwarmTaskStatus.FAILED
    assert "VRAMLimitExceededError" in t_unsafe.error


# ============================================================================
# 5. Universal Guardian Emergency Kill Switch (< 25ms SLA)
# ============================================================================

def test_swarm_scheduler_guardian_kill_switch_sla():
    """Verify scheduler cancels all queued tasks within < 25.0ms SLA."""
    scheduler = SwarmScheduler()

    # Enqueue 20 tasks
    for i in range(20):
        scheduler.enqueue_task(f"n_{i}", "tool_test", {"idx": i}, AgentRole.CODER)

    assert len(scheduler.get_queue_status()) == 20

    # Measure halt execution time
    t_start = time.perf_counter()
    cancelled = scheduler.halt()
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    assert cancelled == 20
    assert len(scheduler.get_queue_status()) == 0
    assert len(scheduler.get_history()) == 20
    assert all(t.status == SwarmTaskStatus.HALTED for t in scheduler.get_history())

    # Hard SLA: Must complete in < 25.0 ms
    assert elapsed_ms < 25.0, f"Guardian kill switch took {elapsed_ms:.2f}ms, exceeding 25ms SLA"


# ============================================================================
# 6. Tool Registry Integration & Execution
# ============================================================================

def test_swarm_tools_registry():
    """Verify tool registration, tier numbers, preview generation, and execution."""
    # Check registration
    tool_dispatch = registry.get("dispatch_swarm_auction")
    tool_roster = registry.get("get_swarm_roster_status")
    tool_bids = registry.get("query_agent_bids")

    assert tool_dispatch is not None
    assert tool_dispatch.tier == 1  # Tier 1 for auction dispatch
    assert tool_roster is not None
    assert tool_roster.tier == 0  # Tier 0 read-only
    assert tool_bids is not None
    assert tool_bids.tier == 0  # Tier 0 read-only

    # Execute get_swarm_roster_status
    roster_res = tool_roster.handler_fn()
    assert roster_res["agent_count"] == 4
    assert "vram_metrics" in roster_res
    assert roster_res["vram_metrics"]["max_allowed_mb"] == 5632.0

    # Execute query_agent_bids
    bids_res = tool_bids.handler_fn(
        node_id="test_bids_node",
        tool_name="apply_workspace_diff",
        title="Apply diff patch",
        description="Write patch to workspace",
    )
    assert bids_res["winning_role"] == "coder"
    assert len(bids_res["bids"]) == 4

    # Execute dispatch_swarm_auction
    tasks = [
        {"node_id": "t1", "tool_name": "deep_research_crawl", "title": "Scrape research"},
        {"node_id": "t2", "tool_name": "validate_ast_syntax", "title": "AST check"},
    ]
    dispatch_res = tool_dispatch.handler_fn(tasks=tasks)
    assert dispatch_res["auction_count"] == 2
    assert dispatch_res["assignments"]["t1"] == "web_scout"
    assert dispatch_res["assignments"]["t2"] == "coder"
