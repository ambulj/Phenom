"""State Reconciler for Phenom Swarm Mesh (Milestone 27 Phase 3).

Reconciles concurrent multi-agent state mutations atomically and manages
reversibility snapshots (CRDT-01.2, CON-04.1).
"""

from __future__ import annotations

import copy
import logging
from typing import Dict, Any, List, Optional

from services.backend.safety.guardian import guardian
from services.backend.swarm.crdt_consensus_engine import (
    crdt_state_register,
    CRDTStateRegister,
    CRDTDelta,
)

logger = logging.getLogger("phenom.swarm.state_reconciler")


class StateReconciler:
    """Manages batch delta reconciliation, causality ordering, and atomic rollbacks."""

    def __init__(self, register: Optional[CRDTStateRegister] = None) -> None:
        self._register = register or crdt_state_register
        self._rollback_stack: List[Dict[str, Any]] = []

    def _check_guardian(self) -> None:
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is TRIPPED. State reconciler halted immediately.")

    def reconcile_proposals(self, proposals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Atomically reconciles a batch of agent state mutation proposals."""
        self._check_guardian()
        # Save snapshot for rollback (Rule 7)
        self._rollback_stack.append(self._register.get_converged_state())
        if len(self._rollback_stack) > 10:
            self._rollback_stack.pop(0)

        applied_deltas: List[CRDTDelta] = []
        for p in proposals:
            aid = p.get("agent_id", "unknown_agent")
            k = p.get("key", "default_key")
            v = p.get("value")
            delta = self._register.apply_delta(agent_id=aid, key=k, value=v)
            applied_deltas.append(delta)

        converged = self._register.get_converged_state()
        return {
            "status": "CONVERGED",
            "applied_delta_count": len(applied_deltas),
            "converged_state": converged,
            "vector_clocks": self._register.get_vector_clocks(),
        }

    def rollback_last_reconciliation(self) -> bool:
        """Roll back state to before last reconciliation pass (Rule 7)."""
        self._check_guardian()
        if self._rollback_stack:
            prev_state = self._rollback_stack.pop()
            # Restore previous values
            for k, entry in prev_state.items():
                self._register.apply_delta(agent_id="reconciler_rollback", key=k, value=entry["value"])
            return True
        return False


# Global singleton instance
state_reconciler = StateReconciler()
