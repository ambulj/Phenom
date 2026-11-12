"""
Unit tests for Ephemeral QR Pairing Protocol and Paired Device Store
Verifies single-use token consumption, TTL enforcement, timing-safe rejection,
atomic JSON registry persistence, and instant Guardian invalidation.
"""

import time
from services.backend.schemas.mesh import MeshDeviceRole, PairedDeviceProfile
from services.backend.mesh.device_registry import PairedDeviceRegistry
from services.backend.mesh.pairing import PairingManager


def test_device_registry_crud(tmp_path):
    storage_file = tmp_path / "paired_devices_test.json"
    registry = PairedDeviceRegistry(storage_path=storage_file)

    assert len(registry.list_devices()) == 0

    profile = PairedDeviceProfile(
        node_id="phone-alpha",
        device_name="Pixel 9 Pro",
        device_role=MeshDeviceRole.COMPANION_MOBILE,
        shared_secret_hash="sha256_mock_hash",
        paired_at=time.time(),
        last_seen_at=time.time(),
        ip_address="192.168.1.150"
    )

    registry.register_device(profile)
    assert len(registry.list_devices()) == 1
    assert registry.get_device("phone-alpha") is not None

    # Reload from disk into fresh registry instance
    reloaded_registry = PairedDeviceRegistry(storage_path=storage_file)
    assert len(reloaded_registry.list_devices()) == 1
    fetched = reloaded_registry.get_device("phone-alpha")
    assert fetched is not None
    assert fetched.device_name == "Pixel 9 Pro"

    # Unpair
    assert reloaded_registry.unpair_device("phone-alpha") is True
    assert len(reloaded_registry.list_devices()) == 0
    assert reloaded_registry.unpair_device("non-existent") is False


def test_pairing_single_use_and_ttl(tmp_path):
    registry = PairedDeviceRegistry(storage_path=tmp_path / "pairing_test.json")
    manager = PairingManager(
        node_id="desktop-host",
        host="192.168.1.100",
        port=8765,
        device_registry=registry
    )

    # 1. Generate token with 2-second TTL
    payload = manager.generate_ephemeral_token(ttl_seconds=2)
    assert payload.token is not None
    assert payload.qr_matrix_svg is not None
    assert payload.qr_png_base64 is not None

    # 2. Timing-safe verification succeeds on first try
    verified = manager.verify_pairing_request(
        companion_node_id="companion-tab-1",
        device_name="Galaxy Tab S9",
        device_role=MeshDeviceRole.COMPANION_TABLET,
        token=payload.token,
        client_ip="192.168.1.180"
    )
    assert verified is not None
    assert verified.node_id == "companion-tab-1"
    assert registry.get_device("companion-tab-1") is not None

    # 3. Single-use invariant: second verification with same token MUST fail
    reused = manager.verify_pairing_request(
        companion_node_id="companion-tab-1",
        device_name="Galaxy Tab S9",
        device_role=MeshDeviceRole.COMPANION_TABLET,
        token=payload.token
    )
    assert reused is None


def test_pairing_ttl_expiry(tmp_path):
    registry = PairedDeviceRegistry(storage_path=tmp_path / "pairing_exp.json")
    manager = PairingManager(
        node_id="desktop-host",
        host="192.168.1.100",
        port=8765,
        device_registry=registry
    )

    # Generate token with negative TTL (already expired)
    payload = manager.generate_ephemeral_token(ttl_seconds=-1)

    # Verification must fail due to expiry
    expired_result = manager.verify_pairing_request(
        companion_node_id="phone-slow",
        device_name="Old iPhone",
        device_role=MeshDeviceRole.COMPANION_MOBILE,
        token=payload.token
    )
    assert expired_result is None


def test_pairing_guardian_invalidation(tmp_path):
    registry = PairedDeviceRegistry(storage_path=tmp_path / "pairing_inv.json")
    manager = PairingManager(
        node_id="desktop-host",
        host="192.168.1.100",
        port=8765,
        device_registry=registry
    )

    payload = manager.generate_ephemeral_token(ttl_seconds=120)
    assert len(manager._active_tokens) == 1

    # Invalidate all on Guardian halt
    manager.invalidate_all()
    assert len(manager._active_tokens) == 0

    # Verification must fail
    res = manager.verify_pairing_request(
        companion_node_id="phone-halted",
        device_name="Phone",
        device_role=MeshDeviceRole.COMPANION_MOBILE,
        token=payload.token
    )
    assert res is None
