"""
Ephemeral Credential Leaser.
Issues short-lived, auto-expiring credential leases stored in mutable bytearrays
and zeroes memory buffers upon expiry, revocation, or Guardian halt (Permanent Rule 11).
"""

import time
import uuid
from typing import Dict, List, Optional, Tuple
from services.backend.schemas.biometrics import LeasedCredentialRecord


class EphemeralCredentialLeaser:
    """Manages ephemeral in-memory credential leases with zero-knowledge bytearray wiping."""

    def __init__(self) -> None:
        # Map lease_id -> {"record": LeasedCredentialRecord, "buffer": bytearray}
        self._leases: Dict[str, Dict] = {}
        self._total_issued: int = 0

    def lease_credential(
        self,
        target_service: str,
        secret_bytes: bytes,
        ttl_seconds: int = 30,
    ) -> Tuple[str, LeasedCredentialRecord]:
        """
        Create a new ephemeral lease wrapping a mutable bytearray.
        """
        now = time.time()
        lease_id = f"lease-{uuid.uuid4().hex[:10]}"
        record = LeasedCredentialRecord(
            lease_id=lease_id,
            target_service=target_service,
            leased_at=now,
            expires_at=now + ttl_seconds,
            zeroed=False,
        )

        # Store in mutable bytearray for in-place zero-wiping
        buf = bytearray(secret_bytes)
        self._leases[lease_id] = {
            "record": record,
            "buffer": buf,
        }
        self._total_issued += 1
        return lease_id, record

    def get_credential(self, lease_id: str) -> bytes:
        """
        Retrieve leased secret bytes if not expired or zeroed.
        """
        entry = self._leases.get(lease_id)
        if not entry:
            raise KeyError(f"Lease {lease_id} not found.")

        record: LeasedCredentialRecord = entry["record"]
        if record.zeroed:
            raise ValueError(f"Lease {lease_id} has already been zero-wiped.")

        if time.time() > record.expires_at:
            self.revoke_lease(lease_id)
            raise TimeoutError(f"Lease {lease_id} has expired and was zero-wiped.")

        return bytes(entry["buffer"])

    def revoke_lease(self, lease_id: str) -> bool:
        """
        In-place zeroing of the secret bytearray buffer (Permanent Rule 11).
        """
        entry = self._leases.get(lease_id)
        if not entry:
            return False

        buf: bytearray = entry["buffer"]
        for i in range(len(buf)):
            buf[i] = 0

        entry["record"].zeroed = True
        return True

    def wipe_all(self) -> int:
        """
        Synchronously zero-wipe all active leased buffers in memory.
        Used during Guardian kill switch halt or emergency lockdown.
        """
        wiped_count = 0
        for lease_id in list(self._leases.keys()):
            if not self._leases[lease_id]["record"].zeroed:
                self.revoke_lease(lease_id)
                wiped_count += 1
        return wiped_count

    def get_active_leases(self) -> List[LeasedCredentialRecord]:
        """Return list of unexpired, un-zeroed leases."""
        now = time.time()
        active = []
        for lease_id, entry in list(self._leases.items()):
            rec: LeasedCredentialRecord = entry["record"]
            if not rec.zeroed:
                if now <= rec.expires_at:
                    active.append(rec)
                else:
                    self.revoke_lease(lease_id)
        return active

    @property
    def total_issued(self) -> int:
        return self._total_issued
