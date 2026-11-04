"""Unit tests for Milestone 13 Phase 3: Cross-Device Distributed Swarm Compute (SWM-01)."""

import pytest
from services.backend.schemas.swarm_compute import (
    ComputeNodeType,
    WorkloadStatus,
    WorkloadType,
)
from services.backend.swarm_compute.node_manager import SwarmNodeManager
from services.backend.swarm_compute.workload_scheduler import SwarmWorkloadScheduler


def test_node_manager_registration_and_cluster_state():
    mgr = SwarmNodeManager(host_node_id="test-host")

    # Host should be present initially
    state0 = mgr.get_cluster_state()
    assert state0.active_node_count == 1
    assert state0.total_vram_mb == 8192

    # Register laptop peer
    laptop = mgr.register_node(
        node_id="peer-laptop",
        device_name="ThinkPad P14s",
        node_type=ComputeNodeType.LAPTOP_HYBRID,
        available_vram_mb=4096,
        available_ram_mb=16384,
        battery_percent=85,
        is_plugged_in=True,
        compute_flops_rating=3.5,
    )
    assert laptop.node_id == "peer-laptop"
    assert laptop.node_type == ComputeNodeType.LAPTOP_HYBRID

    # Register phone peer
    phone = mgr.register_node(
        node_id="peer-phone",
        device_name="Galaxy S24",
        node_type=ComputeNodeType.MOBILE_COMPANION,
        available_vram_mb=0,
        available_ram_mb=2048,
        battery_percent=90,
        is_plugged_in=False,
        compute_flops_rating=1.2,
    )
    assert phone.node_id == "peer-phone"

    state1 = mgr.get_cluster_state()
    assert state1.active_node_count == 3
    assert state1.total_vram_mb == 8192 + 4096


def test_scheduler_evaluates_battery_and_thermal_constraints():
    mgr = SwarmNodeManager(host_node_id="test-host")
    scheduler = SwarmWorkloadScheduler(node_manager=mgr)

    # 1. Throttled node
    mgr.register_node(
        node_id="hot-laptop",
        device_name="Hot Laptop",
        node_type=ComputeNodeType.LAPTOP_HYBRID,
        available_vram_mb=4096,
        thermal_throttled=True,
    )

    # 2. Low battery unplugged node
    mgr.register_node(
        node_id="low-battery-phone",
        device_name="Low Battery Phone",
        node_type=ComputeNodeType.MOBILE_COMPANION,
        available_ram_mb=2048,
        battery_percent=15,
        is_plugged_in=False,
    )

    # 3. Healthy laptop
    mgr.register_node(
        node_id="healthy-laptop",
        device_name="Healthy Laptop",
        node_type=ComputeNodeType.LAPTOP_HYBRID,
        available_vram_mb=4096,
        available_ram_mb=8192,
        battery_percent=80,
        is_plugged_in=True,
        compute_flops_rating=4.0,
    )

    candidates = scheduler.evaluate_candidate_nodes(WorkloadType.EMBEDDING_BATCH)
    candidate_ids = [c.node_id for c in candidates]

    # Must include healthy-laptop and host, must exclude hot-laptop and low-battery-phone
    assert "healthy-laptop" in candidate_ids
    assert "test-host" in candidate_ids
    assert "hot-laptop" not in candidate_ids
    assert "low-battery-phone" not in candidate_ids


def test_speculative_decoding_routes_to_high_vram_node():
    mgr = SwarmNodeManager(host_node_id="test-host")
    scheduler = SwarmWorkloadScheduler(node_manager=mgr)

    # Register mobile node (no VRAM)
    mgr.register_node(
        node_id="mobile-1",
        device_name="Mobile Device",
        node_type=ComputeNodeType.MOBILE_COMPANION,
        available_vram_mb=0,
    )

    # Register fast laptop with VRAM
    mgr.register_node(
        node_id="gpu-laptop",
        device_name="GPU Laptop",
        node_type=ComputeNodeType.LAPTOP_HYBRID,
        available_vram_mb=6144,
        compute_flops_rating=8.0,
    )

    task = scheduler.dispatch_workload(
        workload_type=WorkloadType.SPECULATIVE_DECODING,
        items_count=5,
    )

    assert task.status == WorkloadStatus.COMPLETED
    assert task.assigned_node_id in ("test-host", "gpu-laptop")
    assert task.result is not None
    assert "tokens_generated" in task.result
    assert task.result["tokens_generated"] == 5 * 16


def test_dynamic_failover_rerouting():
    mgr = SwarmNodeManager(host_node_id="test-host")
    scheduler = SwarmWorkloadScheduler(node_manager=mgr)

    # Register worker laptop
    mgr.register_node(
        node_id="flaky-worker",
        device_name="Flaky Worker",
        node_type=ComputeNodeType.LAPTOP_HYBRID,
        available_vram_mb=4096,
        compute_flops_rating=5.0,
    )

    task = scheduler.dispatch_workload(
        workload_type=WorkloadType.EMBEDDING_BATCH,
        items_count=20,
        preferred_node_id="flaky-worker",
    )
    assert task.assigned_node_id == "flaky-worker"
    assert task.failover_count == 0

    # Trigger failover
    reassigned_task = scheduler.failover_task(task.task_id)
    assert reassigned_task.task_id == task.task_id
    assert reassigned_task.assigned_node_id == "test-host"
    assert reassigned_task.failover_count == 1
    assert reassigned_task.status == WorkloadStatus.COMPLETED


def test_workload_manual_abort():
    mgr = SwarmNodeManager(host_node_id="test-host")
    scheduler = SwarmWorkloadScheduler(node_manager=mgr)

    task = scheduler.dispatch_workload(
        workload_type=WorkloadType.DOCUMENT_INDEXING,
        items_count=10,
    )
    task_id = task.task_id

    aborted = scheduler.abort_workload(task_id)
    assert aborted is True
    assert scheduler.get_task(task_id).status == WorkloadStatus.ABORTED
