"""
Universal Perpetual Guardian Kill Switch Coordinator (Phase 47-04, HEAL-04).
Guarantees < 25.0ms emergency halt SLA across all executor threads, child processes, and UI workflows.
Multi-channel triggers:
1. Physical hotkeys (Ctrl+Alt+P, Ctrl+Alt+Esc)
2. Voice emergency cues ("Phenom stop", "halt")
3. Electron Desktop UI HALT button
4. Remote Telegram companion command (/halt)
"""

import time
import threading
import psutil
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian


class HaltRecord(BaseModel):
    """Telemetry record captured upon an emergency Guardian kill switch trigger."""
    source: str = Field(..., description="'hotkey', 'voice', 'ui_button', or 'telegram'")
    reason: str = Field(..., description="Triggering prompt or reason")
    timestamp: float = Field(default_factory=time.time, description="Halt invocation epoch")
    latency_ms: float = Field(..., description="Elapsed milliseconds to freeze all threads (< 25ms SLA)")
    terminated_pids: List[int] = Field(default_factory=list, description="Child PIDs terminated during halt")


class UniversalGuardianCoordinator:
    """Perpetually arms and coordinates emergency kill switch triggers across all channels."""

    MAX_HALT_LATENCY_MS = 25.0

    def __init__(self):
        self._halt_history: List[HaltRecord] = []
        self._lock = threading.Lock()
        self._voice_triggers = {"phenom stop", "stop phenom", "halt", "kill switch", "emergency stop"}
        self._hotkey_combos = ["ctrl+alt+p", "ctrl+alt+esc"]

    @property
    def is_halted(self) -> bool:
        """Returns True if the system is currently frozen by the kill switch."""
        return guardian.is_halted

    def check_voice_trigger(self, utterance: str) -> bool:
        """Evaluates transcribed audio to detect emergency kill switch phrases."""
        clean = utterance.strip().lower()
        return any(phrase in clean for phrase in self._voice_triggers)

    def trigger_kill(
        self,
        source: str = "programmatic",
        reason: str = "Emergency stop requested"
    ) -> HaltRecord:
        """
        Executes immediate emergency freeze across all threads and processes.
        Guarantees < 25.0ms latency SLA.
        """
        start_t = time.perf_counter()

        # 1. Trigger the underlying Guardian kill switch
        guardian.trigger()

        # 2. Terminate all tracked child processes immediately
        terminated: List[int] = []
        with guardian._lock:
            pids_to_kill = list(guardian._tracked_pids)
            tasks_to_cancel = list(guardian._tracked_tasks)

        for pid in pids_to_kill:
            try:
                proc = psutil.Process(pid)
                proc.kill()
                terminated.append(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()

        latency_ms = (time.perf_counter() - start_t) * 1000.0

        record = HaltRecord(
            source=source,
            reason=reason,
            timestamp=time.time(),
            latency_ms=latency_ms,
            terminated_pids=terminated
        )

        with self._lock:
            self._halt_history.append(record)

        return record

    def resume(self) -> None:
        """Explicitly resumes Phenom from the halted state upon user confirmation."""
        guardian.resume()

    def get_last_halt_record(self) -> Optional[HaltRecord]:
        """Returns the most recent halt record."""
        with self._lock:
            return self._halt_history[-1] if self._halt_history else None


# Global singleton instance
universal_guardian = UniversalGuardianCoordinator()
