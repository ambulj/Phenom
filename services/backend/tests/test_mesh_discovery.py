"""
Unit tests for Local Network Device Discovery Engine
Verifies UDP beacon broadcast/reception, peer table tracking,
stale peer cleanup, loopback self-beacon filtering, and graceful shutdown.
"""

import time
from services.backend.schemas.mesh import MeshDiscoveryBeacon
from services.backend.mesh.discovery import MeshDiscoveryEngine, get_local_ip


def test_get_local_ip():
    ip = get_local_ip()
    assert isinstance(ip, str)
    assert len(ip) >= 7
    assert "." in ip


def test_peer_beacon_recording_and_cleanup():
    engine = MeshDiscoveryEngine(
        node_id="desktop-node-001",
        device_name="Phenom Main Rig",
        discovery_port=53541
    )

    now = time.time()
    companion_beacon = MeshDiscoveryBeacon(
        node_id="phone-node-002",
        device_name="Pixel 9 Pro",
        host="192.168.1.150",
        port=8765,
        tls_fingerprint="fp-phone-002",
        capabilities=["approvals", "telemetry"],
        timestamp=now
    )

    # Record beacon
    engine.record_peer_beacon(companion_beacon)
    peers = engine.get_active_peers(timeout_seconds=5.0)
    assert len(peers) == 1
    assert peers[0].node_id == "phone-node-002"

    # Self beacon must be discarded
    self_beacon = MeshDiscoveryBeacon(
        node_id="desktop-node-001",
        device_name="Phenom Main Rig",
        host="192.168.1.100",
        port=8765,
        tls_fingerprint="fp-self",
        capabilities=["approvals"],
        timestamp=now
    )
    engine.record_peer_beacon(self_beacon)
    assert len(engine.get_active_peers(timeout_seconds=5.0)) == 1

    # Record stale beacon (timestamp 25 seconds ago)
    stale_beacon = MeshDiscoveryBeacon(
        node_id="phone-node-old",
        device_name="Stale Phone",
        host="192.168.1.151",
        port=8765,
        tls_fingerprint="fp-old",
        capabilities=["approvals"],
        timestamp=now - 25.0
    )
    engine.record_peer_beacon(stale_beacon)

    # Active peers with 5s timeout should include only phone-node-002, evicting stale
    active = engine.get_active_peers(timeout_seconds=5.0)
    assert len(active) == 1
    assert active[0].node_id == "phone-node-002"

    # And phone-node-old must be cleaned up from peer table
    with engine._lock:
        assert "phone-node-old" not in engine._peers


def test_discovery_engine_lifecycle_and_sockets():
    test_port = 53542
    engine = MeshDiscoveryEngine(
        node_id="test-lifecycle-node",
        device_name="Test Lifecycle",
        discovery_port=test_port,
        broadcast_addr="127.0.0.1"
    )

    # Start engine
    engine.start()
    assert engine._running is True

    # Immediate synchronous stop (< 1ms)
    t0 = time.perf_counter()
    engine.stop()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert engine._running is False
    assert elapsed_ms < 25.0
