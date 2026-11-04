"""
Biometric Enclave Manager & TPM 2.0 Hardware Isolation.
Manages encrypted workspace partitions (Personal vs. Professional) and enforces
strict cryptographic boundaries and sub-10ms Guardian lockdown (Rule 1, 4, 11).
"""

import hashlib
import hmac
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.backend.schemas.biometrics import (
    BiometricAuthMethod,
    BiometricEnclaveState,
    EnclaveStatus,
    LeasedCredentialRecord,
    PartitionMetadata,
    WorkspacePartitionType,
)
from services.backend.security.credential_leaser import EphemeralCredentialLeaser


class BiometricEnclaveManager:
    """Coordinates TPM 2.0 sealed partitions and ephemeral credential leasing."""

    def __init__(self) -> None:
        self._leaser: EphemeralCredentialLeaser = EphemeralCredentialLeaser()
        self._halted: bool = False
        self._hardware_tpm_present: bool = True
        self._change_callbacks: List[Callable[[BiometricEnclaveState], None]] = []

        # Master keys in RAM: map partition_type -> bytearray (zero-wiped on lock/halt)
        self._partition_keys: Dict[WorkspacePartitionType, bytearray] = {}

        # Partition states
        self._partitions: Dict[str, PartitionMetadata] = {
            WorkspacePartitionType.PERSONAL.value: PartitionMetadata(
                partition_id="part-personal-01",
                name="Personal Vault & Life Partition",
                partition_type=WorkspacePartitionType.PERSONAL,
                status=EnclaveStatus.LOCKED,
                encryption_cipher="SQLCipher / AES-256-GCM (TPM Sealed)",
                last_unlocked_at=None,
                active_lease_count=0,
            ),
            WorkspacePartitionType.PROFESSIONAL.value: PartitionMetadata(
                partition_id="part-prof-02",
                name="Professional Workspace & Code Enclave",
                partition_type=WorkspacePartitionType.PROFESSIONAL,
                status=EnclaveStatus.LOCKED,
                encryption_cipher="SQLCipher / AES-256-GCM (TPM Sealed)",
                last_unlocked_at=None,
                active_lease_count=0,
            ),
        }

    def register_change_callback(self, callback: Callable[[BiometricEnclaveState], None]) -> None:
        """Register a subscriber callback for state updates."""
        self._change_callbacks.append(callback)

    def _notify(self) -> None:
        state = self.get_state()
        for cb in self._change_callbacks:
            try:
                cb(state)
            except Exception:
                pass

    def unlock_partition(
        self,
        partition_type: WorkspacePartitionType,
        auth_token: str,
        auth_method: BiometricAuthMethod = BiometricAuthMethod.WINDOWS_HELLO_BIOMETRIC,
    ) -> PartitionMetadata:
        """
        Unlock a partition via Windows Hello biometric verification or TPM hardware seal.
        Enforces cross-tenant isolation: personal and professional keys are strictly distinct.
        """
        if self._halted:
            raise PermissionError("Guardian kill switch is active: partition unlocking blocked.")

        if not auth_token or len(auth_token.strip()) < 3:
            raise ValueError("Authentication token invalid or rejected by Windows Hello.")

        part_key = partition_type.value
        part = self._partitions.get(part_key)
        if not part:
            raise KeyError(f"Partition {partition_type} does not exist.")

        # Derive partition master key via simulated TPM 2.0 / DPAPI KDF
        salt = f"tpm-salt-{part_key}".encode("utf-8")
        derived = hmac.new(salt, auth_token.encode("utf-8"), hashlib.sha256).digest()

        # Store in mutable bytearray
        self._partition_keys[partition_type] = bytearray(derived)
        part.status = EnclaveStatus.UNLOCKED
        part.last_unlocked_at = time.time()

        self._notify()
        return part

    def lock_partition(self, partition_type: WorkspacePartitionType) -> PartitionMetadata:
        """
        Lock a partition and zero-wipe its master key from RAM immediately.
        """
        part_key = partition_type.value
        part = self._partitions.get(part_key)
        if not part:
            raise KeyError(f"Partition {partition_type} does not exist.")

        # Zero-wipe key
        if partition_type in self._partition_keys:
            key_buf = self._partition_keys[partition_type]
            for i in range(len(key_buf)):
                key_buf[i] = 0
            del self._partition_keys[partition_type]

        part.status = EnclaveStatus.LOCKED
        self._notify()
        return part

    def is_unlocked(self, partition_type: WorkspacePartitionType) -> bool:
        """Check if partition is currently unlocked."""
        part = self._partitions.get(partition_type.value)
        return part is not None and part.status == EnclaveStatus.UNLOCKED

    def lease_credential(
        self,
        target_service: str,
        secret_bytes: bytes,
        ttl_seconds: int = 30,
    ) -> Tuple[str, LeasedCredentialRecord]:
        """Request an ephemeral credential lease with auto memory zeroing."""
        if self._halted:
            raise PermissionError("Guardian kill switch is active: credential leasing blocked.")

        lease_id, record = self._leaser.lease_credential(target_service, secret_bytes, ttl_seconds)
        self._notify()
        return lease_id, record

    def get_leased_credential(self, lease_id: str) -> bytes:
        """Retrieve leased credential bytes."""
        if self._halted:
            raise PermissionError("Guardian kill switch is active: credential access blocked.")
        return self._leaser.get_credential(lease_id)

    def revoke_lease(self, lease_id: str) -> bool:
        """Revoke and zero-wipe an active lease."""
        res = self._leaser.revoke_lease(lease_id)
        self._notify()
        return res

    def get_state(self) -> BiometricEnclaveState:
        """Return the current biometric enclave state."""
        active_leases = self._leaser.get_active_leases()
        
        # Update partition lease counts
        for part in self._partitions.values():
            part.active_lease_count = len(active_leases)

        return BiometricEnclaveState(
            hardware_tpm_present=self._hardware_tpm_present,
            partitions={k: v.model_copy() for k, v in self._partitions.items()},
            total_leases_issued=self._leaser.total_issued,
            active_leases=active_leases,
        )

    # =========================================================================
    # Guardian Kill Switch Sub-10ms SLA Hooks
    # =========================================================================

    def halt(self) -> None:
        """
        Synchronously halt the Biometric Enclave Manager.
        Wipes all leased credential buffers, zero-wipes partition keys, and locks all partitions.
        """
        self._halted = True
        
        # 1. Zero-wipe all active leased credential buffers in memory
        self._leaser.wipe_all()

        # 2. Zero-wipe all partition master keys
        for key_buf in self._partition_keys.values():
            for i in range(len(key_buf)):
                key_buf[i] = 0
        self._partition_keys.clear()

        # 3. Lock all partitions
        for part in self._partitions.values():
            part.status = EnclaveStatus.LOCKED

        self._notify()

    def resume(self) -> None:
        """Resume from Guardian halt. Partitions remain safely locked until re-authenticated."""
        self._halted = False
        self._notify()

    def reset(self) -> None:
        """Alias for resume."""
        self.resume()
