"""
Phenom ZERO-TRACE: Ephemeral RAM-Only Operating Mode & Anti-Forensic Memory Scrubbing
Features:
1. Volatile In-Memory Storage: Retains security telemetry and action logs strictly within volatile RAM buffers.
2. Zero Disk Persistence: Suppresses disk writes while stealth mode is active.
3. Cryptographic Memory Zeroization: Overwrites memory buffers with cryptographic random entropy and zeroes.
4. Emergency Auto-Sanitization: Hooks directly into the Guardian Kill Switch (<25ms SLA) to sanitize RAM upon abort.

Invariants:
- Rule 3: Guardian Kill Switch automatically purges volatile telemetry.
- Rule 4: Zero cloud telemetry egress.
- Rule 7: Preserves non-destructive containment while erasing volatile telemetry.
"""

import os
import secrets
import threading
import time
from typing import Dict, Any, List, Optional
from services.backend.safety.guardian import guardian


class ZeroTraceEngine:
    """Ephemeral RAM-only execution manager with cryptographic memory zeroization."""

    def __init__(self):
        self._is_stealth_active = False
        self._volatile_buffer: List[bytearray] = []
        self._volatile_logs: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

        # Register callback with Guardian to auto-zeroize on emergency kill
        guardian.add_state_callback(self._on_guardian_state_change)

    def _on_guardian_state_change(self, state: str):
        if state == "halted":
            self.purge_and_zeroize()

    def set_stealth_mode(self, active: bool) -> Dict[str, Any]:
        """Toggles Ephemeral RAM-Only mode."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch active. Aborting stealth mode change.")

        with self._lock:
            self._is_stealth_active = active

        return {
            "stealth_mode_active": self._is_stealth_active,
            "storage_layer": "VOLATILE_RAM" if self._is_stealth_active else "PERSISTENT_SQLITE",
            "disk_writes_suppressed": self._is_stealth_active,
            "timestamp": time.time()
        }

    def record_volatile_trace(self, category: str, payload: str) -> None:
        """Records an in-memory trace without disk persistence."""
        with self._lock:
            raw_bytes = bytearray(payload.encode("utf-8"))
            self._volatile_buffer.append(raw_bytes)
            self._volatile_logs.append({
                "timestamp": time.time(),
                "category": category,
                "byte_size": len(raw_bytes)
            })

    def purge_and_zeroize(self) -> Dict[str, Any]:
        """Cryptographically overwrites volatile buffers and empties telemetry queues."""
        t0 = time.perf_counter()
        bytes_scrubbed = 0
        buffers_cleared = 0

        with self._lock:
            buffers_cleared = len(self._volatile_buffer)
            for buf in self._volatile_buffer:
                bytes_scrubbed += len(buf)
                # Pass 1: Overwrite with random cryptographic noise
                noise = secrets.token_bytes(len(buf))
                for i in range(len(buf)):
                    buf[i] = noise[i]
                # Pass 2: Overwrite with zeros
                for i in range(len(buf)):
                    buf[i] = 0

            self._volatile_buffer.clear()
            self._volatile_logs.clear()

        duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        return {
            "status": "ZEROIZED",
            "buffers_cleared": buffers_cleared,
            "bytes_scrubbed": bytes_scrubbed,
            "scrub_duration_ms": duration_ms,
            "sla_met": duration_ms < 25.0
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns volatile memory footprint metrics."""
        with self._lock:
            total_bytes = sum(len(b) for b in self._volatile_buffer)
            entry_count = len(self._volatile_logs)
            active = self._is_stealth_active

        return {
            "stealth_mode_active": active,
            "volatile_entries_count": entry_count,
            "volatile_bytes_allocated": total_bytes,
            "zeroization_ready": True
        }


zero_trace = ZeroTraceEngine()
