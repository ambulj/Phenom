"""Contextual World-Model Simulator for Phenom (Milestone 26 Phase 3).

Maintains an in-memory symbolic representation of the operating environment (files,
processes, windows, workspace) to project state transitions non-destructively (SIM-01.1).
"""

from __future__ import annotations

import copy
import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.simulation.world_model")


class Rule8ViolationError(Exception):
    """Raised when world-model simulation encounters payment or checkout actions."""
    pass


class VirtualSystemState(BaseModel):
    files: Dict[str, str] = Field(default_factory=dict)
    processes: Dict[int, str] = Field(default_factory=dict)
    active_window: str = "Phenom Cyber Desktop"
    network_egress_blocked: bool = True
    timestamp: float = Field(default_factory=time.time)


class SimulatedStepResult(BaseModel):
    step_id: str
    action_type: str
    target: str
    outcome: str  # SUCCESS, BLOCKED, PERMISSION_ERROR, FAILED
    state_delta: Dict[str, Any]
    side_effects: List[str] = Field(default_factory=list)


class WorldModelSimulator:
    """Simulates plan steps in a virtual sandbox environment without physical OS side-effects."""

    _RULE_8_PATTERN = re.compile(
        r"\b(checkout|pay|payment|purchase|buy|credit.?card|cvv|billing|stripe|paypal|place.?order|order.?checkout)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._current_state = VirtualSystemState(
            files={
                "C:/Phenom/PROJECT.md": "Phenom OS",
                "C:/Phenom/SAFETY.md": "Safety invariants",
            },
            processes={
                1001: "phenom_backend.exe",
                1002: "electron.exe",
            },
            active_window="Phenom Cyber Desktop",
        )
        self._history_snapshots: List[VirtualSystemState] = []

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. World model simulator halted immediately.")

    def _validate_rule_8(self, text: str) -> None:
        cleaned = re.sub(r"[_]+", " ", text).lower()
        if self._RULE_8_PATTERN.search(cleaned):
            raise Rule8ViolationError(
                f"Rule 8 violation: world-model simulation of payment actions is strictly prohibited. Found: {text}"
            )

    def get_state(self) -> VirtualSystemState:
        """Returns deep copy of current virtual state."""
        self._check_guardian()
        return copy.deepcopy(self._current_state)

    def snapshot(self) -> None:
        """Snapshot current state for non-destructive rollbacks (Rule 7)."""
        self._check_guardian()
        self._history_snapshots.append(copy.deepcopy(self._current_state))
        if len(self._history_snapshots) > 20:
            self._history_snapshots.pop(0)

    def rollback(self) -> bool:
        """Roll back to last saved snapshot."""
        self._check_guardian()
        if self._history_snapshots:
            self._current_state = self._history_snapshots.pop()
            return True
        return False

    def simulate_step(self, action_type: str, target: str, payload: Optional[Dict[str, Any]] = None) -> SimulatedStepResult:
        """Simulate a single action step against the virtual world state."""
        self._check_guardian()
        self._validate_rule_8(action_type)
        self._validate_rule_8(target)
        if payload:
            for k, v in payload.items():
                if isinstance(v, str):
                    self._validate_rule_8(v)

        payload = payload or {}
        delta: Dict[str, Any] = {}
        side_effects: List[str] = []
        outcome = "SUCCESS"

        act = action_type.upper()
        if act in ("FILE_WRITE", "WRITE_FILE"):
            delta["file_modified"] = target
            delta["content_length"] = len(payload.get("content", ""))
            side_effects.append(f"In-memory mutation of file '{target}'")
        elif act in ("FILE_DELETE", "DELETE_FILE"):
            delta["file_deleted"] = target
            side_effects.append(f"Simulated soft-delete (recycle bin) of file '{target}'")
        elif act in ("PROCESS_KILL", "KILL_PROCESS"):
            pid = int(target) if target.isdigit() else 9999
            delta["process_terminated"] = pid
            side_effects.append(f"Simulated termination of process PID {pid}")
        elif act in ("SWITCH_WINDOW", "FOCUS_WINDOW"):
            delta["previous_window"] = self._current_state.active_window
            delta["new_window"] = target
            side_effects.append(f"Focus shift from '{self._current_state.active_window}' to '{target}'")
        elif act in ("EXEC_COMMAND", "RUN_COMMAND"):
            cmd = payload.get("command", target)
            if "rm -rf" in cmd or "del /f" in cmd:
                side_effects.append("High risk destructive command pattern detected")
            delta["command_simulated"] = cmd
        else:
            delta["generic_action"] = act
            side_effects.append(f"Generic action '{act}' evaluated")

        return SimulatedStepResult(
            step_id=f"step_{int(time.time() * 1000) % 1000000}",
            action_type=act,
            target=target,
            outcome=outcome,
            state_delta=delta,
            side_effects=side_effects,
        )


# Global singleton instance
world_model_simulator = WorldModelSimulator()
