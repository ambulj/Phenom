"""
Biometric Enclave Partitioning & TPM 2.0 Hardware Isolation Schemas.
Pydantic v2 schemas for hardware-backed key sealing, multi-tenant workspace
partitioning, and ephemeral credential leasing (Rule 11).
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EnclaveStatus(str, Enum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    QUARANTINED = "QUARANTINED"
    DISABLED = "DISABLED"


class WorkspacePartitionType(str, Enum):
    PERSONAL = "PERSONAL"
    PROFESSIONAL = "PROFESSIONAL"
    SHARED_SYSTEM = "SHARED_SYSTEM"


class BiometricAuthMethod(str, Enum):
    WINDOWS_HELLO_PIN = "WINDOWS_HELLO_PIN"
    WINDOWS_HELLO_BIOMETRIC = "WINDOWS_HELLO_BIOMETRIC"
    TPM_HARDWARE_SEAL = "TPM_HARDWARE_SEAL"
    CREDENTIAL_MANAGER_KEY = "CREDENTIAL_MANAGER_KEY"


class PartitionMetadata(BaseModel):
    partition_id: str = Field(..., description="Unique partition identifier")
    name: str = Field(..., description="Human-readable partition name")
    partition_type: WorkspacePartitionType = Field(..., description="Workspace classification")
    status: EnclaveStatus = Field(EnclaveStatus.LOCKED, description="Current partition lock status")
    encryption_cipher: str = Field("AES-256-GCM / SQLCipher", description="Cryptographic cipher used for sealing")
    last_unlocked_at: Optional[float] = Field(None, description="UNIX timestamp when last unlocked")
    active_lease_count: int = Field(0, ge=0, description="Number of currently active credential leases")


class LeasedCredentialRecord(BaseModel):
    lease_id: str = Field(..., description="Unique lease identifier")
    target_service: str = Field(..., description="Target service identifier (e.g. 'github', 'gmail')")
    leased_at: float = Field(..., description="UNIX timestamp when lease was granted")
    expires_at: float = Field(..., description="UNIX timestamp when lease expires and memory is zeroed")
    zeroed: bool = Field(False, description="Whether credential memory buffer has been zero-wiped")


class BiometricEnclaveState(BaseModel):
    hardware_tpm_present: bool = Field(True, description="Whether TPM 2.0 hardware security module is detected")
    partitions: Dict[str, PartitionMetadata] = Field(default_factory=dict, description="Managed workspace partitions")
    total_leases_issued: int = Field(0, ge=0, description="Cumulative count of leases issued")
    active_leases: List[LeasedCredentialRecord] = Field(default_factory=list, description="Currently valid leases")


# =============================================================================
# Tool Argument Models
# =============================================================================

class EnclaveGetStatusArgs(BaseModel):
    """Arguments for querying biometric enclave status."""
    pass


class EnclaveUnlockPartitionArgs(BaseModel):
    """Arguments for unlocking a partition via Windows Hello or TPM seal."""
    partition_type: WorkspacePartitionType = Field(..., description="Target partition: PERSONAL or PROFESSIONAL")
    auth_token: str = Field(..., description="Biometric authentication verification token or PIN")
    auth_method: BiometricAuthMethod = Field(
        BiometricAuthMethod.WINDOWS_HELLO_BIOMETRIC,
        description="Authentication method used",
    )


class EnclaveLockPartitionArgs(BaseModel):
    """Arguments for locking an active workspace partition."""
    partition_type: WorkspacePartitionType = Field(..., description="Target partition: PERSONAL or PROFESSIONAL")


class EnclaveLeaseCredentialArgs(BaseModel):
    """Arguments for requesting an ephemeral, auto-expiring credential lease."""
    target_service: str = Field(..., description="Name of the service (e.g. 'github_token', 'gmail_pass')")
    ttl_seconds: int = Field(30, ge=5, le=300, description="Lease duration in seconds before memory zeroing")


class EnclaveRevokeLeaseArgs(BaseModel):
    """Arguments for immediately revoking and zeroing an active credential lease."""
    lease_id: str = Field(..., description="ID of the lease to immediately revoke and memory-wipe")
