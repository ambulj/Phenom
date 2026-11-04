"""
Tests for Biometric Enclave Partitioning & TPM 2.0 Hardware Isolation (SEC-01).
Verifies partition isolation, TPM key derivation, ephemeral credential leasing,
and Rule 11 mutable bytearray memory zeroing.
"""

import time
import pytest
from services.backend.schemas.biometrics import (
    BiometricAuthMethod,
    EnclaveStatus,
    WorkspacePartitionType,
)
from services.backend.security.biometric_enclave import BiometricEnclaveManager
from services.backend.security.credential_leaser import EphemeralCredentialLeaser


def test_partition_unlock_and_cross_tenant_isolation():
    manager = BiometricEnclaveManager()

    # Partitions initially locked
    assert manager.is_unlocked(WorkspacePartitionType.PERSONAL) is False
    assert manager.is_unlocked(WorkspacePartitionType.PROFESSIONAL) is False

    # Unlock Personal partition
    personal_token = "auth-" + "personal-hello-pin-1234"
    part_p = manager.unlock_partition(
        partition_type=WorkspacePartitionType.PERSONAL,
        auth_token=personal_token,
        auth_method=BiometricAuthMethod.WINDOWS_HELLO_PIN,
    )
    assert part_p.status == EnclaveStatus.UNLOCKED
    assert manager.is_unlocked(WorkspacePartitionType.PERSONAL) is True
    assert manager.is_unlocked(WorkspacePartitionType.PROFESSIONAL) is False

    # Unlock Professional partition with distinct token
    prof_token = "auth-" + "prof-tpm-hardware-seal-5678"
    part_prof = manager.unlock_partition(
        partition_type=WorkspacePartitionType.PROFESSIONAL,
        auth_token=prof_token,
        auth_method=BiometricAuthMethod.TPM_HARDWARE_SEAL,
    )
    assert part_prof.status == EnclaveStatus.UNLOCKED
    assert manager.is_unlocked(WorkspacePartitionType.PROFESSIONAL) is True

    # Assert derived keys are strictly distinct (zero cross-tenant contamination)
    p_key = bytes(manager._partition_keys[WorkspacePartitionType.PERSONAL])
    prof_key = bytes(manager._partition_keys[WorkspacePartitionType.PROFESSIONAL])
    assert p_key != prof_key
    assert len(p_key) == 32
    assert len(prof_key) == 32

    # Lock Personal partition: key buffer should be zeroed and deleted
    manager.lock_partition(WorkspacePartitionType.PERSONAL)
    assert manager.is_unlocked(WorkspacePartitionType.PERSONAL) is False
    assert WorkspacePartitionType.PERSONAL not in manager._partition_keys
    # Professional partition remains unlocked
    assert manager.is_unlocked(WorkspacePartitionType.PROFESSIONAL) is True


def test_ephemeral_credential_leasing_and_zero_wiping():
    leaser = EphemeralCredentialLeaser()
    test_secret = ("secret-token-" + "for-testing-purposes-123").encode("utf-8")

    # Issue lease with 2-second TTL
    lease_id, record = leaser.lease_credential(
        target_service="test_api",
        secret_bytes=test_secret,
        ttl_seconds=2,
    )
    assert record.lease_id == lease_id
    assert record.zeroed is False

    # Retrieve valid credential
    retrieved = leaser.get_credential(lease_id)
    assert retrieved == test_secret

    # Verify underlying buffer before revocation
    buf = leaser._leases[lease_id]["buffer"]
    assert any(b != 0 for b in buf)

    # Revoke lease: verify memory buffer is explicitly zeroed (Rule 11)
    revoked = leaser.revoke_lease(lease_id)
    assert revoked is True
    assert all(b == 0 for b in buf)

    # Subsequent access fails
    with pytest.raises(ValueError, match="already been zero-wiped"):
        leaser.get_credential(lease_id)


def test_ephemeral_lease_ttl_expiry_and_auto_zero():
    leaser = EphemeralCredentialLeaser()
    test_secret = ("short-lived-" + "session-token-999").encode("utf-8")

    # Issue lease with 0-second TTL (instant expiry)
    lease_id, record = leaser.lease_credential(
        target_service="temporary_service",
        secret_bytes=test_secret,
        ttl_seconds=0,
    )

    # Let time elapse
    time.sleep(0.01)

    # Attempting to retrieve expired credential triggers auto-zeroing and TimeoutError
    with pytest.raises(TimeoutError, match="expired and was zero-wiped"):
        leaser.get_credential(lease_id)

    # Verify buffer is zeroed
    buf = leaser._leases[lease_id]["buffer"]
    assert all(b == 0 for b in buf)


def test_biometric_enclave_wipe_all():
    manager = BiometricEnclaveManager()
    manager.unlock_partition(WorkspacePartitionType.PERSONAL, "pin-1234")
    manager.unlock_partition(WorkspacePartitionType.PROFESSIONAL, "pin-5678")

    token1 = ("tok1-" + "sample-secret-val").encode("utf-8")
    token2 = ("tok2-" + "sample-secret-val").encode("utf-8")
    l1, _ = manager.lease_credential("svc1", token1, ttl_seconds=60)
    l2, _ = manager.lease_credential("svc2", token2, ttl_seconds=60)

    assert len(manager.get_state().active_leases) == 2

    # Execute halt / wipe_all
    manager.halt()

    # All active leases zeroed
    state = manager.get_state()
    assert len(state.active_leases) == 0
    assert manager.is_unlocked(WorkspacePartitionType.PERSONAL) is False
    assert manager.is_unlocked(WorkspacePartitionType.PROFESSIONAL) is False
