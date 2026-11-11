"""Tests for Autonomous Multi-Agent Local Swarm Engine (Milestone 30 Phase 2).

Validates:
- Subagent lifecycle management (SPAWN -> WORKING -> WAITING -> TERMINATED)
- Concurrent non-blocking task execution across Coder, Research, Executive subagents
- Multi-agent result synthesis report generation
- Rule 8 checkout / payment rejection (raises Rule8ViolationError)
- Rule 11 credential scrubbing ([REDACTED])
- Guardian kill switch SLA < 25.0 ms
- Tool registry integration (Tiers 0 & 1)
"""

import asyncio
import time
import pytest

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.swarm.swarm_coordinator import (
    Rule8ViolationError,
    SwarmCoordinator,
    WorkerState,
)
import services.backend.tools.local_swarm_tools  # Registers tools in ToolRegistry


@pytest.fixture(autouse=True)
def reset_guardian():
    """Ensure Guardian is resumed before and after every test."""
    guardian.resume()
    yield
    guardian.resume()


@pytest.fixture
def coordinator():
    """Create a fresh SwarmCoordinator instance for isolated testing."""
    return SwarmCoordinator()


@pytest.mark.asyncio
async def test_subagent_lifecycle_and_concurrent_dispatch(coordinator):
    """Test concurrent dispatch across Coder, Research, and Executive workers."""
    coder_task_coro = coordinator.dispatch_task(
        agent_name="coder",
        prompt="Audit services/backend/safety/guardian.py for thread safety",
    )
    research_task_coro = coordinator.dispatch_task(
        agent_name="research",
        prompt="Analyze local model quantization benchmarks for Q4_K_M vs Q5_K_M",
    )
    executive_task_coro = coordinator.dispatch_task(
        agent_name="executive",
        prompt="Synthesize Phase 2 roadmap milestones and verification deliverables",
    )

    t0 = time.perf_counter()
    coder_task, research_task, executive_task = await asyncio.gather(
        coder_task_coro, research_task_coro, executive_task_coro
    )
    duration_ms = (time.perf_counter() - t0) * 1000.0

    assert coder_task.status == "COMPLETED"
    assert "AST Syntax Tree" in (coder_task.result or "")
    assert coder_task.latency_ms > 0

    assert research_task.status == "COMPLETED"
    assert "Vault Recall" in (research_task.result or "")

    assert executive_task.status == "COMPLETED"
    assert "Evaluated directives" in (executive_task.result or "")

    # Query status
    status = coordinator.query_status()
    assert len(status["workers"]) == 3
    assert status["total_tasks_tracked"] == 3
    coder_stat = next(w for w in status["workers"] if w["agent_name"] == "coder")
    assert coder_stat["tasks_completed"] == 1
    research_stat = next(w for w in status["workers"] if w["agent_name"] == "research")
    assert research_stat["tasks_completed"] == 1
    exec_stat = next(w for w in status["workers"] if w["agent_name"] == "executive")
    assert exec_stat["tasks_completed"] == 1


@pytest.mark.asyncio
async def test_multi_agent_result_synthesis(coordinator):
    """Test multi-agent report aggregation across disparate completed tasks."""
    t1 = await coordinator.dispatch_task(
        agent_name="coder",
        prompt="Refactor websocket payload serializer",
    )
    t2 = await coordinator.dispatch_task(
        agent_name="research",
        prompt="Document offline vector memory indexing strategies",
    )

    report = coordinator.synthesize_results([t1.task_id, t2.task_id])
    assert "Swarm Multi-Agent Synthesis Report" in report
    assert t1.task_id in report
    assert t2.task_id in report
    assert "CODER" in report
    assert "RESEARCH" in report


@pytest.mark.asyncio
async def test_rule_8_anti_checkout_rejection(coordinator):
    """Rule 8: Payments & checkouts are impossible by construction."""
    with pytest.raises(Rule8ViolationError) as exc_info:
        await coordinator.dispatch_task(
            agent_name="executive",
            prompt="Authorize payment of $500 for server hosting subscription",
        )
    assert "Rule 8 Violation" in str(exc_info.value)

    with pytest.raises(Rule8ViolationError) as exc_info2:
        await coordinator.dispatch_task(
            agent_name="coder",
            prompt="Automate checkout process and buy items in cart",
        )
    assert "Rule 8 Violation" in str(exc_info2.value)


@pytest.mark.asyncio
async def test_rule_11_credential_scrubbing(coordinator):
    """Rule 11: Passwords, tokens, and secrets must be scrubbed."""
    dirty_prompt = "Verify user token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and password=SuperSecretPassword123!"
    task = await coordinator.dispatch_task(
        agent_name="coder",
        prompt=dirty_prompt,
    )
    assert task.status == "COMPLETED"
    assert "SuperSecretPassword123!" not in (task.result or "")
    assert "[REDACTED]" in (task.result or "")
    assert "SuperSecretPassword123!" not in task.prompt
    assert "eyJhbGci" not in task.prompt


def test_guardian_kill_switch_sla(coordinator):
    """Rule 3: Guardian kill switch must halt swarm operations within 25.0 ms."""
    guardian.trigger("EMERGENCY KILL SWITCH ACTIVATED")
    assert guardian.is_halted

    t0 = time.perf_counter()
    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(
            coordinator.dispatch_task(
                agent_name="coder",
                prompt="Optimize build loop",
            )
        )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert "Execution halted by Guardian kill switch" in str(exc_info.value)
    assert elapsed_ms < 25.0, f"Guardian SLA violated: took {elapsed_ms:.2f} ms >= 25.0 ms"


def test_worker_termination_lifecycle(coordinator):
    """Test manual worker termination and terminate_all."""
    res = coordinator.terminate_worker("coder")
    assert res["status"] == "TERMINATED"
    assert coordinator.workers["coder"].state == WorkerState.TERMINATED

    all_res = coordinator.terminate_all()
    assert all_res["status"] == "ALL_TERMINATED"
    assert all(w.state == WorkerState.TERMINATED for w in coordinator.workers.values())


def test_local_swarm_tool_registry_and_tiers():
    """Verify tool registration, risk tiers, and execution handles."""
    # 1. dispatch_local_swarm_task (Tier 1)
    dispatch_tool = registry.get("dispatch_local_swarm_task")
    assert dispatch_tool is not None
    assert dispatch_tool.tier == 1
    assert "dispatch" in dispatch_tool.preview_fn({"agent_name": "coder", "prompt": "Test"}).lower()

    # 2. query_local_swarm_status (Tier 0)
    query_tool = registry.get("query_local_swarm_status")
    assert query_tool is not None
    assert query_tool.tier == 0
    status_out = query_tool.handler_fn()
    assert "workers" in status_out

    # 3. terminate_local_swarm_worker (Tier 1)
    term_tool = registry.get("terminate_local_swarm_worker")
    assert term_tool is not None
    assert term_tool.tier == 1

    # 4. synthesize_local_swarm_results (Tier 0)
    synth_tool = registry.get("synthesize_local_swarm_results")
    assert synth_tool is not None
    assert synth_tool.tier == 0
