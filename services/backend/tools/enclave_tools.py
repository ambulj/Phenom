"""
Biometric Enclave & TPM 2.0 Hardware Isolation Tools (SEC-01, SAF-01, SAF-02).
Registers Tier 0 and Tier 1 tools for unlocking/locking encrypted workspace partitions
and requesting ephemeral, memory-zeroed credential leases.
"""

from typing import Any, Dict, Optional

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.biometrics import (
    BiometricAuthMethod,
    EnclaveGetStatusArgs,
    EnclaveLeaseCredentialArgs,
    EnclaveLockPartitionArgs,
    EnclaveRevokeLeaseArgs,
    EnclaveUnlockPartitionArgs,
    WorkspacePartitionType,
)
from services.backend.security import biometric_enclave_manager


# ==========================================
# Tier 0 Tools (Read-Only)
# ==========================================

@registry.register(
    name="enclave_get_status",
    tier=0,
    description="Inspects biometric enclave status, workspace partitions, and active credential leases (Read-Only)",
    args_schema=EnclaveGetStatusArgs,
    preview_fn=lambda a: "Inspect biometric enclave status and workspace partition states (Read-Only)",
)
def enclave_get_status(**kwargs) -> Dict[str, Any]:
    """Inspect enclave status."""
    state = biometric_enclave_manager.get_state()
    return {
        "status": "success",
        "enclave_state": state.model_dump(),
    }


# ==========================================
# Tier 1 Tools (Reversible Changes with Preview)
# ==========================================

def _preview_unlock_partition(args: Dict[str, Any]) -> str:
    part = args.get("partition_type", "PERSONAL")
    method = args.get("auth_method", "WINDOWS_HELLO_BIOMETRIC")
    return f"Unlock encrypted workspace partition '{part}' via {method}"


@registry.register(
    name="enclave_unlock_partition",
    tier=1,
    description="Unlocks an encrypted workspace partition via Windows Hello or TPM seal (Tier 1 Preview)",
    args_schema=EnclaveUnlockPartitionArgs,
    preview_fn=_preview_unlock_partition,
)
def enclave_unlock_partition(
    partition_type: WorkspacePartitionType,
    auth_token: str,
    auth_method: BiometricAuthMethod = BiometricAuthMethod.WINDOWS_HELLO_BIOMETRIC,
    **kwargs,
) -> Dict[str, Any]:
    """Unlock encrypted workspace partition."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: partition unlocking blocked.")

    part = biometric_enclave_manager.unlock_partition(
        partition_type=partition_type,
        auth_token=auth_token,
        auth_method=auth_method,
    )
    return {
        "status": "success",
        "action": "unlock_partition",
        "partition": part.model_dump(),
    }


def _preview_lock_partition(args: Dict[str, Any]) -> str:
    part = args.get("partition_type", "PERSONAL")
    return f"Lock workspace partition '{part}' and zero-wipe master key from RAM immediately"


@registry.register(
    name="enclave_lock_partition",
    tier=1,
    description="Locks an active workspace partition and purges its master key from memory (Tier 1 Preview)",
    args_schema=EnclaveLockPartitionArgs,
    preview_fn=_preview_lock_partition,
)
def enclave_lock_partition(partition_type: WorkspacePartitionType, **kwargs) -> Dict[str, Any]:
    """Lock workspace partition."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: partition locking blocked.")

    part = biometric_enclave_manager.lock_partition(partition_type=partition_type)
    return {
        "status": "success",
        "action": "lock_partition",
        "partition": part.model_dump(),
    }


def _preview_lease_credential(args: Dict[str, Any]) -> str:
    target = args.get("target_service", "service")
    ttl = args.get("ttl_seconds", 30)
    return f"Lease ephemeral credential for '{target}' (TTL: {ttl}s, auto-zeroing memory buffer)"


@registry.register(
    name="enclave_lease_credential",
    tier=1,
    description="Requests an ephemeral credential lease with auto memory zeroing upon expiry (Tier 1 Preview)",
    args_schema=EnclaveLeaseCredentialArgs,
    preview_fn=_preview_lease_credential,
)
def enclave_lease_credential(target_service: str, ttl_seconds: int = 30, **kwargs) -> Dict[str, Any]:
    """Issue ephemeral credential lease."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: credential leasing blocked.")

    # Simulated secret retrieval from Windows Credential Manager enclave
    # In tests/simulations, secret bytes are constructed dynamically
    secret_bytes = f"ephemeral-token-for-{target_service}".encode("utf-8")
    lease_id, record = biometric_enclave_manager.lease_credential(
        target_service=target_service,
        secret_bytes=secret_bytes,
        ttl_seconds=ttl_seconds,
    )
    return {
        "status": "success",
        "action": "lease_credential",
        "lease_id": lease_id,
        "record": record.model_dump(),
    }


def _preview_revoke_lease(args: Dict[str, Any]) -> str:
    lease_id = args.get("lease_id", "")
    return f"Immediately revoke and zero-wipe credential lease '{lease_id}'"


@registry.register(
    name="enclave_revoke_lease",
    tier=1,
    description="Revokes and immediately zero-wipes an active credential lease from RAM (Tier 1 Preview)",
    args_schema=EnclaveRevokeLeaseArgs,
    preview_fn=_preview_revoke_lease,
)
def enclave_revoke_lease(lease_id: str, **kwargs) -> Dict[str, Any]:
    """Revoke and zero-wipe active lease."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: lease revocation blocked.")

    revoked = biometric_enclave_manager.revoke_lease(lease_id=lease_id)
    return {
        "status": "success",
        "action": "revoke_lease",
        "lease_id": lease_id,
        "revoked": revoked,
    }
