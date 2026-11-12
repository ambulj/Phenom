import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.mesh_protocol import local_mesh_peer_discovery
import services.backend.tools.multi_agent_mesh_tools as mmt


def test_multi_agent_mesh_tools_registered_in_registry():
    expected_tools = [
        ("mesh_get_status", 0),
        ("mesh_discover_peers", 0),
        ("mesh_delegate_task", 1),
        ("mesh_disconnect_peer", 1),
    ]

    for tool_name, expected_tier in expected_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool {tool_name} not registered in ToolRegistry"
        assert tool_def.tier == expected_tier, f"Tool {tool_name} tier mismatch"


def test_multi_agent_mesh_tier_0_queries_execute():
    if guardian.is_halted:
        guardian.resume()

    status_res = mmt.mesh_get_status()
    assert "local_node_id" in status_res
    assert "is_advertising" in status_res

    discover_res = mmt.mesh_discover_peers(scan_timeout_seconds=0.5)
    assert "peers" in discover_res
    assert "count" in discover_res


def test_multi_agent_mesh_tier_1_controls_with_preview():
    if guardian.is_halted:
        guardian.resume()

    local_mesh_peer_discovery.register_peer(
        node_id="peer-test-01",
        device_name="Test Peer",
        ip_address="192.168.1.200",
        capabilities=["gpu_compute"],
    )

    # Delegate task preview & execution
    tool_dlg = registry.get("mesh_delegate_task")
    preview_dlg = tool_dlg.preview_fn({
        "target_node_id": "peer-test-01",
        "capability_required": "gpu_compute",
    })
    assert "gpu_compute" in preview_dlg
    assert "peer-test-01" in preview_dlg

    res_dlg = mmt.mesh_delegate_task(
        target_node_id="peer-test-01",
        capability_required="gpu_compute",
        payload={"batch_size": 4},
    )
    assert res_dlg["status"] == "completed"

    # Disconnect peer preview & execution
    tool_disc = registry.get("mesh_disconnect_peer")
    preview_disc = tool_disc.preview_fn({"node_id": "peer-test-01"})
    assert "peer-test-01" in preview_disc

    res_disc = mmt.mesh_disconnect_peer(node_id="peer-test-01")
    assert res_disc["disconnected"]


def test_multi_agent_mesh_tools_fail_closed_under_guardian_halt():
    try:
        guardian.trigger("Mesh Safety Test Halt")
        assert guardian.is_halted

        with pytest.raises(PermissionError):
            mmt.mesh_get_status()

        with pytest.raises(PermissionError):
            mmt.mesh_discover_peers()

        with pytest.raises(PermissionError):
            mmt.mesh_delegate_task(target_node_id="peer-test", capability_required="gpu_compute")

        with pytest.raises(PermissionError):
            mmt.mesh_disconnect_peer(node_id="peer-test")
    finally:
        guardian.resume()
