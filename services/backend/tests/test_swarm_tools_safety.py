"""Safety registry and execution tests for Milestone 13 Phase 3: Swarm Compute Tools (SAF-01, SAF-02)."""

import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.swarm_compute.node_manager import swarm_node_manager
from services.backend.swarm_compute.workload_scheduler import swarm_workload_scheduler
import services.backend.tools.swarm_compute_tools as swarm_tools


EXPECTED_SWARM_COMPUTE_TOOLS = {
    "swarm_compute_get_topology": 0,
    "swarm_compute_register_node": 1,
    "swarm_compute_offload_workload": 1,
    "swarm_compute_abort_workload": 1,
}


@pytest.fixture(autouse=True)
def clean_swarm_state():
    guardian.resume()
    swarm_workload_scheduler.reset()
    yield
    guardian.resume()
    swarm_workload_scheduler.reset()


def test_swarm_compute_tools_registered_in_registry():
    """Verify all 4 swarm compute tools exist in ToolRegistry with their required risk tiers."""
    for tool_name, expected_tier in EXPECTED_SWARM_COMPUTE_TOOLS.items():
        assert tool_name in registry._tools, f"Tool '{tool_name}' must be in ToolRegistry"
        meta = registry._tools[tool_name]
        assert meta.tier == expected_tier, (
            f"Tool '{tool_name}' must have Risk Tier {expected_tier}, but got {meta.tier}"
        )
        assert meta.args_schema is not None
        assert meta.preview_fn is not None


def test_swarm_compute_get_topology_tier_0():
    """Verify Tier 0 query executes cleanly."""
    res = swarm_tools.swarm_compute_get_topology()
    assert res["status"] == "success"
    assert "cluster_state" in res
    assert res["cluster_state"]["active_node_count"] >= 1


def test_swarm_compute_lifecycle_tier_1():
    """Verify Tier 1 operations with previews, registration, offload, and abort."""
    reg_meta = registry._tools["swarm_compute_register_node"]
    preview = reg_meta.preview_fn({
        "node_id": "test-edge-1",
        "device_name": "Edge Rig",
        "node_type": "EDGE_NODE",
        "battery_percent": 100,
    })
    assert "test-edge-1" in preview
    assert "Edge Rig" in preview

    # Register node
    reg_res = swarm_tools.swarm_compute_register_node(
        node_id="test-edge-1",
        device_name="Edge Rig",
        node_type="EDGE_NODE",
        available_vram_mb=4096,
        available_ram_mb=8192,
        battery_percent=100,
        is_plugged_in=True,
        thermal_throttled=False,
        compute_flops_rating=3.0,
    )
    assert reg_res["status"] == "success"
    assert reg_res["node"]["node_id"] == "test-edge-1"

    # Offload workload
    offload_res = swarm_tools.swarm_compute_offload_workload(
        workload_type="SPECULATIVE_DECODING",
        items_count=8,
    )
    assert offload_res["status"] == "success"
    task = offload_res["task"]
    assert task["status"] == "COMPLETED"

    # Abort workload
    abort_res = swarm_tools.swarm_compute_abort_workload(task_id=task["task_id"])
    assert abort_res["status"] == "success"


def test_swarm_compute_tools_fail_closed_under_guardian_halt():
    """Verify fail-closed behavior under Guardian kill switch lockdown."""
    try:
        guardian.trigger("Emergency test halt")
        swarm_workload_scheduler.halt()

        assert swarm_workload_scheduler.is_halted() is True

        # Tier 1 tools must raise PermissionError
        with pytest.raises(PermissionError, match="halted by Guardian"):
            swarm_tools.swarm_compute_register_node(node_id="blocked", device_name="Blocked")

        with pytest.raises(PermissionError, match="halted by Guardian"):
            swarm_tools.swarm_compute_offload_workload(workload_type="EMBEDDING_BATCH")

        with pytest.raises(PermissionError, match="halted by Guardian"):
            swarm_tools.swarm_compute_abort_workload(task_id="swm_dummy")

    finally:
        guardian.resume()
        swarm_workload_scheduler.reset()
