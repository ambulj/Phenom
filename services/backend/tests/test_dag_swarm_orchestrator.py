"""
Tests for Dynamic DAG Swarm Task Orchestrator & Autonomous Subagent Delegation.
Part of Phenom 22.0 Sovereign Swarm Intelligence (SWM-01, AUT-03, SAF-01, SAF-02).
"""

import time
import pytest
import asyncio
from typing import Dict, Any

from services.backend.swarm.dag_orchestrator import (
    DAGOrchestrator,
    DAGNode,
    SwarmDAG,
    dag_orchestrator,
)
from services.backend.swarm.subagent_pool import (
    SubagentPoolManager,
    subagent_pool,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.automation.gui_controller import Rule8ViolationError
import services.backend.tools.swarm_orchestrator_tools as swarm_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_topological_wave_partitioning_kahns_algorithm():
    """Verify that Kahn's algorithm correctly groups independent tasks into concurrent waves."""
    nodes = [
        DAGNode(node_id="A", name="Task A", dependencies=[]),
        DAGNode(node_id="B", name="Task B", dependencies=[]),
        DAGNode(node_id="C", name="Task C", dependencies=["A", "B"]),
        DAGNode(node_id="D", name="Task D", dependencies=["C"]),
        DAGNode(node_id="E", name="Task E", dependencies=["C"]),
    ]
    orchestrator = DAGOrchestrator()
    dag = orchestrator.create_dag(goal="Test DAG", nodes_list=nodes)

    assert len(dag.waves) == 3
    assert set(dag.waves[0]) == {"A", "B"}
    assert set(dag.waves[1]) == {"C"}
    assert set(dag.waves[2]) == {"D", "E"}


def test_circular_dependency_cycle_detection():
    """Circular dependency must raise ValueError immediately during partition."""
    nodes = [
        DAGNode(node_id="A", name="Task A", dependencies=["B"]),
        DAGNode(node_id="B", name="Task B", dependencies=["C"]),
        DAGNode(node_id="C", name="Task C", dependencies=["A"]),
    ]
    orchestrator = DAGOrchestrator()
    with pytest.raises(ValueError, match="Circular dependency cycle"):
        orchestrator.create_dag(goal="Cycle DAG", nodes_list=nodes)


def test_missing_upstream_dependency_detection():
    """Referencing a non-existent parent node must raise ValueError."""
    nodes = [
        DAGNode(node_id="A", name="Task A", dependencies=["NON_EXISTENT"]),
    ]
    orchestrator = DAGOrchestrator()
    with pytest.raises(ValueError, match="references non-existent upstream dependency"):
        orchestrator.create_dag(goal="Missing Dep DAG", nodes_list=nodes)


def test_goal_decomposition_standard_waves():
    """Verify standard 3-wave decomposition for software engineering goals."""
    dag = dag_orchestrator.decompose_goal_into_dag("Refactor billing service with atomic worktrees")
    assert dag.status == "pending"
    assert len(dag.nodes) == 5
    assert len(dag.waves) == 3

    # Wave 0: Research & AST Map
    assert "node_research" in dag.waves[0]
    assert "node_ast_map" in dag.waves[0]

    # Wave 1: Implement
    assert "node_implement" in dag.waves[1]

    # Wave 2: Test & Review
    assert "node_test" in dag.waves[2]
    assert "node_review" in dag.waves[2]


@pytest.mark.asyncio
async def test_concurrent_wave_execution_and_output_propagation():
    """Verify wave-by-wave execution, worker pool sharing, and upstream data passing."""
    dag = dag_orchestrator.decompose_goal_into_dag("Implement vector cache")

    # Execute Wave 0 (Research & AST Map)
    res_w0 = await dag_orchestrator.execute_wave(dag.dag_id)
    assert res_w0["status"] == "completed"
    assert res_w0["wave_index"] == 0
    assert dag.nodes["node_research"].status == "completed"
    assert dag.nodes["node_ast_map"].status == "completed"
    assert "findings" in dag.nodes["node_research"].output

    # Execute Wave 1 (Implement - consumes Wave 0 output)
    res_w1 = await dag_orchestrator.execute_wave(dag.dag_id)
    assert res_w1["status"] == "completed"
    assert res_w1["wave_index"] == 1
    assert dag.nodes["node_implement"].status == "completed"
    assert "code_patch" in dag.nodes["node_implement"].output

    # Execute Wave 2 (Test & Review)
    res_w2 = await dag_orchestrator.execute_wave(dag.dag_id)
    assert res_w2["status"] == "completed"
    assert res_w2["is_final_wave"] is True
    assert dag.status == "completed"
    assert dag.nodes["node_test"].status == "completed"
    assert dag.nodes["node_review"].status == "completed"


@pytest.mark.asyncio
async def test_subagent_pool_resource_governance():
    """Verify max worker constraints and pool status reporting."""
    pool = SubagentPoolManager(max_workers=3)
    status = pool.get_pool_status()
    assert len(status) == 3
    assert all(w["status"] == "idle" for w in status)


@pytest.mark.asyncio
async def test_guardian_kill_switch_sla_halt():
    """Guardian trigger must immediately abort swarm wave execution in < 25.0ms SLA."""
    dag = dag_orchestrator.decompose_goal_into_dag("Mission under threat")

    guardian.trigger()
    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        await dag_orchestrator.execute_wave(dag.dag_id)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA exceeded: {latency_ms:.4f}ms >= 25.0ms"


def test_tool_registry_and_previews():
    """Verify that all Phase 1 swarm tools are registered with schemas and previews."""
    tool_names = [
        "create_swarm_task_dag",
        "execute_swarm_dag_wave",
        "get_swarm_dag_status",
        "abort_swarm_execution",
    ]
    for name in tool_names:
        tool = registry.get(name)
        assert tool is not None, f"Tool {name} is not registered in ToolRegistry"
        assert callable(tool.handler_fn)

    # Test preview generators
    preview_dag = registry.get("create_swarm_task_dag").generate_preview({"goal": "Build dynamic microservice"})
    assert "Swarm Task DAG" in preview_dag or "topologically sorted" in preview_dag

    preview_wave = registry.get("execute_swarm_dag_wave").generate_preview({"dag_id": "dag_123", "wave_index": 0})
    assert "swarm task DAG" in preview_wave or "wave" in preview_wave


def test_rule_8_anti_checkout_enforcement():
    """Verify Rule 8 blocks task creation or execution targeting payments."""
    payment_goal = "Automatically buy 5 stocks and complete payment $199"
    with pytest.raises(Rule8ViolationError):
        swarm_tools.create_swarm_task_dag(goal=payment_goal)
