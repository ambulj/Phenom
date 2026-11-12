import pytest
from services.backend.schemas.multi_agent_mesh import MeshNodeStatus
from services.backend.mesh_protocol.beacon import LocalMeshPeerDiscovery


def test_mesh_node_initialization_and_registration():
    mesh = LocalMeshPeerDiscovery(local_node_id="test-primary-node")
    assert mesh.local_node_id == "test-primary-node"
    assert mesh.is_advertising

    peer = mesh.register_peer(
        node_id="peer-gpu-server-01",
        device_name="Phenom Rig Alpha",
        ip_address="192.168.1.150",
        port=8000,
        capabilities=["gpu_compute", "audio_transcription"],
    )
    assert peer.node_id == "peer-gpu-server-01"
    assert peer.status == MeshNodeStatus.CONNECTED
    assert "gpu_compute" in peer.capabilities

    status = mesh.get_status()
    assert status.local_node_id == "test-primary-node"
    assert "peer-gpu-server-01" in status.peers


def test_mesh_peer_discovery_scan():
    mesh = LocalMeshPeerDiscovery()
    mesh.register_peer("peer-laptop", "Phenom Laptop", "192.168.1.151")

    discovered = mesh.discover_peers(scan_timeout_seconds=0.5)
    assert len(discovered) == 1
    assert discovered[0].node_id == "peer-laptop"


def test_mesh_task_delegation():
    mesh = LocalMeshPeerDiscovery()
    mesh.register_peer(
        node_id="peer-worker-01",
        device_name="Worker Alpha",
        ip_address="192.168.1.152",
        capabilities=["audio_transcription"],
    )

    # Delegate task with matching capability
    task = mesh.delegate_task(
        target_node_id="peer-worker-01",
        capability_required="audio_transcription",
        payload={"audio_chunks": 12},
    )
    assert task.status == "completed"
    assert task.target_node_id == "peer-worker-01"
    assert task.latency_ms > 0

    # Delegate task with missing capability -> ValueError
    with pytest.raises(ValueError):
        mesh.delegate_task(
            target_node_id="peer-worker-01",
            capability_required="unsupported_quantum_compute",
            payload={},
        )


def test_mesh_peer_disconnect():
    mesh = LocalMeshPeerDiscovery()
    mesh.register_peer("peer-to-disconnect", "Worker Beta", "192.168.1.153")
    assert mesh._peers["peer-to-disconnect"].status == MeshNodeStatus.CONNECTED

    success = mesh.disconnect_peer("peer-to-disconnect")
    assert success
    assert mesh._peers["peer-to-disconnect"].status == MeshNodeStatus.DISCONNECTED

    # Attempting to delegate to disconnected peer -> ConnectionError
    with pytest.raises(ConnectionError):
        mesh.delegate_task("peer-to-disconnect", "general_compute", {})
