"""
Guardian Kill Switch Sub-25ms SLA Test Suite for Phase 2 ToT Engine (SAF-02).
Benchmarks synchronous halt latency (< 25ms SLA, assert < 1ms typical),
verifies immediate task cancellation, and asserts complete denial of planning,
step execution, and state manipulation while halted.
"""

import asyncio
import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.orchestrator.tot_planner import tot_planner
from services.backend.orchestrator.dag_state import dag_state_manager
from services.backend.orchestrator.metacognition import metacognitive_reflector
import services.backend.tools.tot_tools as tt
from services.backend.schemas.tot import DAGNode


@pytest.fixture(autouse=True)
def clean_guardian_state():
    if guardian.is_halted:
        guardian.resume()
    tot_planner.reset()
    dag_state_manager.reset()
    metacognitive_reflector.reset()
    tt._active_dags.clear()
    yield
    if guardian.is_halted:
        guardian.resume()
    tot_planner.reset()
    dag_state_manager.reset()
    metacognitive_reflector.reset()
    tt._active_dags.clear()


def test_guardian_halt_latency_sla():
    # Benchmark synchronous halt latency
    t0 = time.perf_counter()
    guardian.trigger("sla_tot_benchmark_halt")
    t1 = time.perf_counter()

    latency_ms = (t1 - t0) * 1000.0

    # Assert synchronous Guardian halt SLA < 25.0ms (typically < 1.0ms)
    assert latency_ms < 25.0, f"Guardian halt SLA breached: {latency_ms:.3f}ms >= 25.0ms"
    assert tot_planner.is_halted is True
    assert dag_state_manager.is_halted is True
    assert metacognitive_reflector.is_halted is True


@pytest.mark.asyncio
async def test_guardian_active_task_cancellation():
    # Enforce Plan Checker recommendation #4:
    # In TreeOfThoughtPlanner.halt(), cancel any active step asyncio.Task handles immediately.
    async def dummy_long_task():
        await asyncio.sleep(10.0)

    task = asyncio.create_task(dummy_long_task())
    tot_planner.register_task(task)
    assert not task.done()

    # Trigger halt
    guardian.trigger("task_cancellation_test")

    # Give event loop a microsecond to propagate cancellation
    await asyncio.sleep(0.01)

    assert task.cancelled() or task.done()
    assert len(tot_planner._active_tasks) == 0


def test_operations_denied_while_halted():
    # Prepare a valid DAG prior to halt
    dag = tot_planner.plan_objective("Safe baseline objective")
    tt.register_active_dag(dag)

    guardian.trigger("halt_for_denial_test")

    # 1. Planner operations denied
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        tot_planner.plan_objective("Another goal")

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        tot_planner.get_ready_nodes(dag)

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        tot_planner.switch_to_contingency(dag)

    # 2. State manager operations denied
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        dag_state_manager.create_checkpoint(dag, 1)

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        dag_state_manager.rollback_to_checkpoint(dag)

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        dag_state_manager.execute_node_with_retry(dag, next(iter(dag.nodes.values())), lambda n, c: None)

    # 3. Metacognitive operations denied
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        metacognitive_reflector.reflect_on_step(dag, next(iter(dag.nodes.values())))

    # 4. Tool calls denied
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        tt.tot_create_goal_dag("Goal while halted")

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        tt.tot_execute_step(dag.dag_id)

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        tt.tot_prune_branch(dag.dag_id, dag.active_branch_id)

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        tt.tot_abort_goal(dag.dag_id)


def test_clean_resumption_after_resume():
    guardian.trigger("halt_temp")
    assert tot_planner.is_halted is True

    guardian.resume()
    assert tot_planner.is_halted is False
    assert dag_state_manager.is_halted is False
    assert metacognitive_reflector.is_halted is False

    # Operations succeed normally after resume
    res = tt.tot_create_goal_dag("Post-resume safe goal")
    assert res["success"] is True
