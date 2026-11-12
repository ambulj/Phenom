"""
Unit tests for Core P2P Mesh Engine and Guardian Kill Switch Integration
Verifies device management, session routing, instant Guardian halt,
and operations rejection during halted state.
"""

import os
import time
import pytest
from services.backend.schemas.mesh import MeshDeviceRole
from services.backend.mesh.crypto import MeshCryptoEngine
from services.backend.mesh.p2p_mesh_engine import P2PMeshEngine
from services.backend.safety.guardian import GuardianKillSwitch


def test_p2p_mesh_engine_pairing_and_devices(tmp_path):
    guardian = GuardianKillSwitch()
    engine = P2PMeshEngine(
        node_id="desktop-node-001",
        device_name="Phenom Desktop",
        guardian=guardian,
        registry_path=str(tmp_path / "devices.json")
    )

    # Initially empty
    assert len(engine.get_paired_devices()) == 0

    # Generate QR payload
    qr_payload = engine.generate_pairing_qr(ttl_seconds=60)
    assert qr_payload.token is not None

    # Verify pairing
    profile = engine.verify_pairing(
        node_id="phone-node-002",
        device_name="Companion Phone",
        device_role=MeshDeviceRole.COMPANION_MOBILE,
        token=qr_payload.token,
        client_ip="192.168.1.155"
    )
    assert profile is not None
    assert profile.node_id == "phone-node-002"

    devices = engine.get_paired_devices(include_offline=True)
    assert len(devices) == 1
    assert devices[0].device_name == "Companion Phone"

    # Unpair
    unpaired = engine.unpair_device("phone-node-002")
    assert unpaired is True
    assert len(engine.get_paired_devices()) == 0


def test_p2p_mesh_engine_session_and_message_routing(tmp_path):
    engine = P2PMeshEngine(
        node_id="desktop-node-001",
        registry_path=str(tmp_path / "devices.json")
    )

    shared_key = os.urandom(32)
    desktop_crypto = MeshCryptoEngine(key=shared_key)
    companion_crypto = MeshCryptoEngine(key=shared_key, session_prefix=desktop_crypto._session_prefix)

    # Register active session
    engine.register_session("companion-node", desktop_crypto)

    # Register handler for message type 10
    received_messages = []
    engine.register_handler(10, lambda nid, data: received_messages.append((nid, data)))

    # Companion sends encrypted frame to desktop
    test_msg = b"Hello from companion tablet!"
    frame = companion_crypto.encrypt_frame(test_msg, 10)

    # Dispatch frame into engine
    engine.dispatch_incoming_frame("companion-node", frame)
    assert len(received_messages) == 1
    assert received_messages[0] == ("companion-node", test_msg)


def test_p2p_mesh_engine_guardian_halt_sla(tmp_path):
    guardian = GuardianKillSwitch()
    engine = P2PMeshEngine(
        node_id="desktop-node-001",
        guardian=guardian,
        registry_path=str(tmp_path / "devices.json")
    )

    # Register session
    shared_key = os.urandom(32)
    engine.register_session("phone-node", MeshCryptoEngine(key=shared_key))

    # Trigger guardian kill switch
    t0 = time.perf_counter()
    guardian.trigger("emergency_test_stop")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Sub-25ms SLA assert (assert < 15ms in test)
    assert elapsed_ms < 25.0
    assert engine.is_halted is True

    # Operations must raise PermissionError immediately
    with pytest.raises(PermissionError, match="halted"):
        engine.generate_pairing_qr()

    with pytest.raises(PermissionError, match="halted"):
        engine.get_paired_devices()

    with pytest.raises(PermissionError, match="halted"):
        engine.send_frame("phone-node", 1, b"blocked")

    # Resume
    guardian.resume()
    assert engine.is_halted is False

    # Operations work again
    qr = engine.generate_pairing_qr()
    assert qr.token is not None
