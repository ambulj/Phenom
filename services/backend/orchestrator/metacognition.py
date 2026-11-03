"""
Metacognitive Reflector & Execution Loop Detector (PLN-01, SAF-01, SAF-02).
Monitors execution traces between actions to detect cognitive loops,
oscillation patterns, stagnation, and recommends dynamic branch pruning.
"""

import hashlib
import time
import uuid
from typing import Dict, List, Optional

from services.backend.schemas.tot import (
    DAGBranch,
    DAGNode,
    GoalDAG,
    MetacognitiveReflection,
    NodeStatus,
)
from services.backend.safety.guardian import guardian


class MetacognitiveReflector:
    """
    Metacognitive Reflector for autonomous goal execution.
    Inspects sliding-window execution traces, hashes step outcome signatures,
    detects repetitive stagnation and oscillation cycles, and initiates dynamic
    branch pruning and contingency transitions.
    """

    def __init__(self, history_window_size: int = 10) -> None:
        self.window_size: int = history_window_size
        self._execution_history: Dict[str, List[str]] = {}  # dag_id -> list of outcome signatures
        self._halted: bool = False
        guardian.add_state_callback(self.on_guardian_state)

    @property
    def is_halted(self) -> bool:
        return self._halted or guardian.is_halted

    def on_guardian_state(self, state: str) -> None:
        if state == "halted":
            self.halt()
        elif state == "idle":
            self.reset()

    def halt(self) -> None:
        """Synchronously halt reflection engine (< 1ms SLA)."""
        self._halted = True

    def reset(self) -> None:
        """Reset halted state when Guardian transitions back to idle."""
        self._halted = False
        self._execution_history.clear()

    def compute_signature(self, node: DAGNode, status: str, error: Optional[str] = None) -> str:
        """
        Compute deterministic SHA-256 outcome signature:
        SHA256(node_id || action_type || status || error).
        """
        err_str = error or ""
        raw = f"{node.node_id}|{node.action_type}|{status}|{err_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def detect_stagnation(self, signatures: List[str]) -> bool:
        """
        Detect repeated identical failure stagnation:
        >= 3 identical consecutive signatures at the tail of history.
        """
        if len(signatures) < 3:
            return False
        return signatures[-1] == signatures[-2] == signatures[-3]

    def detect_oscillation(self, signatures: List[str]) -> Optional[str]:
        """
        Detect cyclic ping-pong oscillation:
        2-cycle: [X, Y, X, Y] (length 4)
        3-cycle: [X, Y, Z, X, Y, Z] (length 6)
        """
        if len(signatures) >= 4:
            # Check 2-cycle [X, Y, X, Y]
            s = signatures[-4:]
            if s[0] == s[2] and s[1] == s[3] and s[0] != s[1]:
                return "oscillation_2cycle"

        if len(signatures) >= 6:
            # Check 3-cycle [X, Y, Z, X, Y, Z]
            s = signatures[-6:]
            if (
                s[0] == s[3]
                and s[1] == s[4]
                and s[2] == s[5]
                and (s[0] != s[1] or s[1] != s[2])
            ):
                return "oscillation_3cycle"

        return None

    def prune_branch(self, dag: GoalDAG, branch_id: str, reason: str) -> bool:
        """
        Dynamically prune an unviable branch:
        Marks branch pruned, sets pending nodes to PRUNED status,
        and switches to the best available contingency branch if active.
        """
        branch = dag.branches.get(branch_id)
        if not branch:
            return False

        branch.pruned = True
        branch.prune_reason = reason
        branch.is_active = False

        # Mark all pending nodes in this branch as PRUNED
        for nid in branch.node_ids:
            node = dag.nodes.get(nid)
            if node and node.status in (NodeStatus.PENDING, NodeStatus.RUNNING):
                node.status = NodeStatus.PRUNED

        # If this was the active branch, attempt to switch to contingency
        if dag.active_branch_id == branch_id:
            from services.backend.orchestrator.tot_planner import tot_planner
            switched = tot_planner.switch_to_contingency(dag)
            if not switched:
                dag.status = "FAILED"
                return False

        dag.updated_at = time.time()
        return True

    def reflect_on_step(
        self,
        dag: GoalDAG,
        completed_node: DAGNode,
        status: Optional[str] = None,
        error: Optional[str] = None,
    ) -> MetacognitiveReflection:
        """
        Evaluate step completion against progress, stagnation, and oscillation.
        Appends reflection to DAG and returns recommended action.
        """
        if self._halted:
            raise PermissionError("MetacognitiveReflector is halted by Guardian kill switch.")

        eff_status = status or completed_node.status
        eff_error = error or completed_node.error
        sig = self.compute_signature(completed_node, eff_status, eff_error)

        if dag.dag_id not in self._execution_history:
            self._execution_history[dag.dag_id] = []

        history = self._execution_history[dag.dag_id]
        history.append(sig)
        if len(history) > self.window_size:
            history.pop(0)

        step_idx = len(dag.reflections) + 1
        reflection_id = f"refl_{uuid.uuid4().hex[:8]}"
        now = time.time()

        # Check for stagnation & oscillation
        stagnation = self.detect_stagnation(history)
        oscillation = self.detect_oscillation(history)

        detected_loop = bool(stagnation or oscillation)
        loop_type = None
        if stagnation:
            loop_type = "stagnation"
        elif oscillation:
            loop_type = oscillation

        # Recommendation logic
        recommended_action = "CONTINUE"
        target_branch = None

        if detected_loop:
            recommended_action = "PRUNE_BRANCH"
            self.prune_branch(
                dag,
                completed_node.branch_id,
                reason=f"Metacognitive detected cognitive loop: {loop_type}",
            )
            target_branch = dag.active_branch_id
        elif eff_status == NodeStatus.FAILED:
            if completed_node.retry_count < completed_node.max_retries:
                recommended_action = "RETRY_STEP"
            else:
                recommended_action = "PRUNE_BRANCH"
                self.prune_branch(
                    dag,
                    completed_node.branch_id,
                    reason=f"Node {completed_node.node_id} retries exhausted ({completed_node.retry_count}/{completed_node.max_retries})",
                )
                target_branch = dag.active_branch_id
        else:
            recommended_action = "CONTINUE"

        reflection = MetacognitiveReflection(
            reflection_id=reflection_id,
            dag_id=dag.dag_id,
            step_index=step_idx,
            detected_loop=detected_loop,
            loop_type=loop_type,
            stagnation_detected=stagnation,
            recommended_action=recommended_action,
            target_branch_id=target_branch,
            confidence_score=0.95 if detected_loop else 1.0,
            timestamp=now,
        )

        dag.reflections.append(reflection)
        dag.updated_at = now
        return reflection


# Global singleton instance
metacognitive_reflector = MetacognitiveReflector()
