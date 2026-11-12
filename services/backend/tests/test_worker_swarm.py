"""
Unit & Integration Test Suite for Phenom 6.0 Phase 2:
Hybrid Autonomous Worker Swarm

Verifies:
1. Headless Browser Worker: Zero focus interruption, Rule 8 zero-payment block.
2. Subprocess CLI Worker: Safe detached execution, destructive command blocking.
3. Swarm Checkpoint Store: SQLite persistence, step tracking, and recovery.
4. Swarm Manager: Concurrency limits, task dispatching, and status telemetry.
5. Swarm Tools: Safety Registry Tier 0 / Tier 1 classification and execution.
6. Guardian Kill Switch: Synchronous abort of all running workers (< 25ms SLA).
"""

import time
import pytest
import asyncio
from typing import Dict, Any, List

from services.backend.automation.headless_worker import HeadlessBrowserWorker, SubprocessCLIWorker
from services.backend.automation.swarm_store import SwarmCheckpointStore
from services.backend.automation.swarm_manager import WorkerSwarmManager, swarm_manager
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.tools.swarm_tools import get_swarm_status, dispatch_swarm_task, abort_swarm_task
from services.backend.main import on_guardian_state_change


# ==============================================================================
# TEST 1: Headless Worker Rule 8 Payment Rejection
# ==============================================================================

@pytest.mark.asyncio
async def test_headless_worker_rule_8_payment_block():
    worker = HeadlessBrowserWorker(worker_id="test-headless-1")

    # Payment in URL
    with pytest.raises(PermissionError) as exc_url:
        await worker.scrape_page("https://store.example.com/checkout/pay")
    assert "Rule 8" in str(exc_url.value)

    # Payment in step sequence
    with pytest.raises(PermissionError) as exc_step:
        await worker.execute_steps([
            {"action": "navigate", "target": "https://store.example.com/cart"},
            {"action": "click", "target": "Proceed to Pay Now"}
        ])
    assert "Rule 8" in str(exc_step.value)

    await worker.close()


# ==============================================================================
# TEST 2: Subprocess CLI Worker Execution & Destructive Blocking
# ==============================================================================

@pytest.mark.asyncio
async def test_subprocess_cli_worker():
    worker = SubprocessCLIWorker(worker_id="test-cli-1")

    # Safe command
    res = await worker.execute_command("echo PhenomSwarmReady")
    assert res["status"] == "completed"
    assert res["returncode"] == 0
    assert "PhenomSwarmReady" in res["stdout"]

    # Destructive command blocked
    with pytest.raises(PermissionError) as exc_dest:
        await worker.execute_command("format C: /y")
    assert "Destructive CLI command blocked" in str(exc_dest.value)


# ==============================================================================
# TEST 3: Swarm Checkpoint Store CRUD
# ==============================================================================

def test_swarm_checkpoint_store():
    store = SwarmCheckpointStore(db_path=":memory:")

    # 1. Save checkpoint
    saved = store.save_checkpoint(
        task_id="task-001",
        worker_id="worker-h01",
        worker_type="headless_browser",
        current_step=1,
        total_steps=3,
        status="running",
        history=[{"step": 1, "url": "https://example.com"}]
    )
    assert saved is True

    # 2. Retrieve checkpoint
    chk = store.get_checkpoint("task-001")
    assert chk is not None
    assert chk["task_id"] == "task-001"
    assert chk["current_step"] == 1
    assert chk["status"] == "running"
    assert len(chk["history"]) == 1

    # 3. Update checkpoint
    store.save_checkpoint(
        task_id="task-001",
        worker_id="worker-h01",
        worker_type="headless_browser",
        current_step=3,
        total_steps=3,
        status="completed",
        history=[{"step": 1}, {"step": 2}, {"step": 3}]
    )
    chk_updated = store.get_checkpoint("task-001")
    assert chk_updated["current_step"] == 3
    assert chk_updated["status"] == "completed"

    # 4. List and delete
    all_chks = store.list_checkpoints()
    assert len(all_chks) == 1

    deleted = store.delete_checkpoint("task-001")
    assert deleted is True
    assert store.get_checkpoint("task-001") is None

    store.close()


# ==============================================================================
# TEST 4: Swarm Manager Concurrency Bounds
# ==============================================================================

@pytest.mark.asyncio
async def test_swarm_manager_concurrency_bounds():
    store = SwarmCheckpointStore(db_path=":memory:")
    manager = WorkerSwarmManager(max_concurrency=2, store=store)

    # Fill active tasks up to capacity
    manager.active_tasks["task-1"] = {"status": "running"}
    manager.active_tasks["task-2"] = {"status": "running"}
    assert manager.get_active_count() == 2

    # Attempting to dispatch 3rd task must raise capacity error
    with pytest.raises(RuntimeError) as exc_cap:
        await manager.dispatch_task("subprocess_cli", {"command": "echo test"})
    assert "concurrency limit reached" in str(exc_cap.value)

    store.close()


# ==============================================================================
# TEST 5: Swarm Manager Subprocess CLI Task Dispatching
# ==============================================================================

@pytest.mark.asyncio
async def test_swarm_manager_dispatch_subprocess_cli():
    store = SwarmCheckpointStore(db_path=":memory:")
    manager = WorkerSwarmManager(max_concurrency=3, store=store)

    events = []
    async def mock_broadcaster(event_type: str, payload: Dict[str, Any]):
        events.append((event_type, payload))

    manager.set_broadcaster(mock_broadcaster)

    res = await manager.dispatch_task(
        task_type="subprocess_cli",
        payload={"command": "echo SwarmManagerActive", "timeout_sec": 10.0}
    )
    assert res["status"] == "completed"
    assert "SwarmManagerActive" in res["stdout"]

    # Checkpoint should be saved
    chks = store.list_checkpoints()
    assert len(chks) >= 1
    assert chks[0]["status"] == "completed"

    # Telemetry events emitted
    event_types = [e[0] for e in events]
    assert "swarm.worker_spawned" in event_types
    assert "swarm.worker_finished" in event_types

    store.close()


# ==============================================================================
# TEST 6: Swarm Manager Abort Task and Abort All
# ==============================================================================

@pytest.mark.asyncio
async def test_swarm_manager_abort_task_and_abort_all():
    store = SwarmCheckpointStore(db_path=":memory:")
    manager = WorkerSwarmManager(max_concurrency=3, store=store)

    # Setup mock active workers
    worker1 = SubprocessCLIWorker(worker_id="w1")
    worker2 = SubprocessCLIWorker(worker_id="w2")
    manager.active_tasks["t1"] = {"status": "running", "worker_id": "w1", "worker_type": "cli"}
    manager.active_tasks["t2"] = {"status": "running", "worker_id": "w2", "worker_type": "cli"}
    manager.active_workers["t1"] = worker1
    manager.active_workers["t2"] = worker2

    # Single task abort
    aborted = manager.abort_task("t1")
    assert aborted is True
    assert manager.active_tasks["t1"]["status"] == "aborted"

    # Abort all remaining
    count = manager.abort_all("test_abort")
    assert count >= 1
    assert manager.active_tasks["t2"]["status"] == "aborted"
    assert manager.get_active_count() == 0

    store.close()


# ==============================================================================
# TEST 7: Swarm Tools in Safety Registry
# ==============================================================================

@pytest.mark.asyncio
async def test_swarm_tools_registration():
    # Verify get_swarm_status (Tier 0)
    status_entry = registry.get("get_swarm_status")
    assert status_entry is not None
    assert status_entry.tier == 0

    status = get_swarm_status()
    assert "active_count" in status
    assert "max_concurrency" in status
    assert "guardian_halted" in status

    # Verify dispatch_swarm_task (Tier 1)
    dispatch_entry = registry.get("dispatch_swarm_task")
    assert dispatch_entry is not None
    assert dispatch_entry.tier == 1
    assert dispatch_entry.preview_fn is not None

    # Verify abort_swarm_task (Tier 1)
    abort_entry = registry.get("abort_swarm_task")
    assert abort_entry is not None
    assert abort_entry.tier == 1


# ==============================================================================
# TEST 8: Guardian Synchronous Abort Latency (< 25ms SLA)
# ==============================================================================

def test_guardian_synchronous_swarm_abort_latency():
    guardian.resume()
    assert guardian.is_halted is False

    # Register mock running task in global swarm manager
    mock_worker = SubprocessCLIWorker(worker_id="mock-worker")
    swarm_manager.active_tasks["t-guard"] = {"status": "running", "worker_id": "mock-worker", "worker_type": "cli"}
    swarm_manager.active_workers["t-guard"] = mock_worker

    # Measure halt execution time of guardian.trigger (which invokes registered on_guardian_state_change)
    t_start = time.perf_counter()
    guardian.trigger("Test Swarm Synchronous Kill Switch")
    t_elapsed = time.perf_counter() - t_start

    latency_ms = t_elapsed * 1000.0
    print(f"\n[GUARDIAN SWARM SLA] Synchronous abort latency: {latency_ms:.3f} ms (SLA < 25.0 ms)")
    assert t_elapsed < 0.025, f"Swarm abort exceeded 25ms SLA: {latency_ms:.2f} ms"

    # Verify swarm and guardian state
    assert guardian.is_halted is True
    assert swarm_manager.get_active_count() == 0
    assert mock_worker.is_aborted is True

    # Clean up
    guardian.resume()
    assert guardian.is_halted is False
