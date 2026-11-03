"""
Self-Healing DAG State Rollback Engine (PLN-01, SAF-01, SAF-02).
Captures immutable deep-copy checkpoints before speculative actions,
restores known-good system context upon failure, and hands execution
off to contingency branches without state corruption.
"""

import copy
import inspect
import time
import uuid
from typing import Any, Callable, Dict, Optional

from services.backend.orchestrator.metacognition import metacognitive_reflector
from services.backend.schemas.tot import (
    DAGCheckpoint,
    DAGNode,
    GoalDAG,
    NodeStatus,
)
from services.backend.safety.guardian import guardian


class DAGStateManager:
    """
    Self-Healing State Rollback Manager.
    Enforces deep-copy checkpoint immutability, manages step execution
    with retry budgets, integrates metacognitive reflection, and executes
    deterministic state restoration on failure.
    """

    def __init__(self) -> None:
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
        """Synchronously halt DAG state manager (< 1ms SLA)."""
        self._halted = True

    def reset(self) -> None:
        """Reset halted state when Guardian transitions to idle."""
        self._halted = False

    def create_checkpoint(self, dag: GoalDAG, step_index: int) -> DAGCheckpoint:
        """
        Capture an immutable deep-copy snapshot of node states and shared context variables.
        Enforces Plan Checker Recommendation #1: deep-copy prevents subsequent in-place
        modifications to dag.context_data from mutating historical snapshots.
        """
        if self._halted:
            raise PermissionError("DAGStateManager is halted by Guardian kill switch.")

        checkpoint_id = f"ckpt_{uuid.uuid4().hex[:8]}"
        # Immutable deep copy of context data and snapshot of current node states
        node_states_snapshot = {
            nid: node.status for nid, node in dag.nodes.items()
        }
        context_snapshot = copy.deepcopy(dag.context_data)

        checkpoint = DAGCheckpoint(
            checkpoint_id=checkpoint_id,
            dag_id=dag.dag_id,
            step_index=step_index,
            node_states=node_states_snapshot,
            context_snapshot=context_snapshot,
            timestamp=time.time(),
        )

        dag.checkpoints.append(checkpoint)
        dag.updated_at = time.time()
        return checkpoint

    def rollback_to_checkpoint(
        self,
        dag: GoalDAG,
        checkpoint_id: Optional[str] = None,
    ) -> bool:
        """
        Roll back DAG context and node states to a known-good checkpoint.
        Reverts modified variables and transitions failed or speculative nodes
        to NodeStatus.ROLLED_BACK.
        """
        if self._halted:
            raise PermissionError("DAGStateManager is halted by Guardian kill switch.")

        if not dag.checkpoints:
            return False

        # Select target checkpoint
        target_ckpt: Optional[DAGCheckpoint] = None
        if checkpoint_id:
            for c in reversed(dag.checkpoints):
                if c.checkpoint_id == checkpoint_id:
                    target_ckpt = c
                    break
        else:
            target_ckpt = dag.checkpoints[-1]

        if not target_ckpt:
            return False

        # Restore context data from immutable deep copy
        dag.context_data = copy.deepcopy(target_ckpt.context_snapshot)

        # Restore node states: if a node was executed or changed after the checkpoint,
        # transition it to ROLLED_BACK if it wasn't already COMPLETED at checkpoint time
        for nid, saved_status in target_ckpt.node_states.items():
            node = dag.nodes.get(nid)
            if not node:
                continue
            if saved_status == NodeStatus.COMPLETED:
                node.status = NodeStatus.COMPLETED
            elif node.status in (NodeStatus.FAILED, NodeStatus.RUNNING):
                node.status = NodeStatus.ROLLED_BACK
            else:
                node.status = saved_status

        dag.updated_at = time.time()
        return True

    def calculate_progress(self, dag: GoalDAG) -> float:
        """Calculate overall completed percentage of active branch nodes."""
        active_branch = dag.branches.get(dag.active_branch_id)
        if not active_branch or not active_branch.node_ids:
            return 0.0

        completed_count = sum(
            1 for nid in active_branch.node_ids
            if dag.nodes.get(nid) and dag.nodes[nid].status == NodeStatus.COMPLETED
        )
        pct = (completed_count / len(active_branch.node_ids)) * 100.0
        dag.overall_progress_pct = round(pct, 1)
        return dag.overall_progress_pct

    async def execute_node_with_retry_async(
        self,
        dag: GoalDAG,
        node: DAGNode,
        execute_fn: Callable[..., Any],
    ) -> Dict[str, Any]:
        """Async variant of node execution."""
        return self._execute_node_internal(dag, node, execute_fn, is_async=True)

    def execute_node_with_retry(
        self,
        dag: GoalDAG,
        node: DAGNode,
        execute_fn: Callable[..., Any],
    ) -> Dict[str, Any]:
        """
        Execute a node within its retry budget, handling checkpoints,
        metacognitive reflection, and automatic rollback on failure.
        """
        return self._execute_node_internal(dag, node, execute_fn, is_async=False)

    def _execute_node_internal(
        self,
        dag: GoalDAG,
        node: DAGNode,
        execute_fn: Callable[..., Any],
        is_async: bool = False,
    ) -> Dict[str, Any]:
        if self._halted:
            raise PermissionError("DAGStateManager is halted by Guardian kill switch.")

        # Capture checkpoint if marked
        if node.is_checkpoint:
            self.create_checkpoint(dag, step_index=len(dag.checkpoints) + 1)

        node.status = NodeStatus.RUNNING
        node.started_at = time.time()
        dag.status = "RUNNING"
        dag.updated_at = time.time()

        try:
            if is_async and inspect.iscoroutinefunction(execute_fn):
                import asyncio
                # In sync context or async caller
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(execute_fn(node=node, context=dag.context_data))
            else:
                result = execute_fn(node=node, context=dag.context_data)

            # Succeeded
            node.status = NodeStatus.COMPLETED
            node.completed_at = time.time()
            node.result_data = result if isinstance(result, dict) else {"output": result}
            node.error = None

            # Metacognitive reflection
            metacognitive_reflector.reflect_on_step(dag, node, status=NodeStatus.COMPLETED)
            self.calculate_progress(dag)

            # Check if all active branch nodes are completed
            active_branch = dag.branches.get(dag.active_branch_id)
            if active_branch and all(
                dag.nodes[nid].status == NodeStatus.COMPLETED
                for nid in active_branch.node_ids if nid in dag.nodes
            ):
                dag.status = "COMPLETED"

            return {
                "success": True,
                "node_id": node.node_id,
                "status": node.status,
                "result": node.result_data,
            }

        except Exception as exc:
            node.retry_count += 1
            node.error = str(exc)
            node.status = NodeStatus.FAILED
            node.completed_at = time.time()

            # Trigger metacognitive reflection
            reflection = metacognitive_reflector.reflect_on_step(
                dag, node, status=NodeStatus.FAILED, error=str(exc)
            )

            # If reflection says PRUNE_BRANCH or retries exhausted, perform self-healing rollback
            if reflection.recommended_action == "PRUNE_BRANCH" or node.retry_count >= node.max_retries:
                # Rollback to latest safe checkpoint
                self.rollback_to_checkpoint(dag)
                # Prune current branch and trigger contingency switch
                metacognitive_reflector.prune_branch(
                    dag,
                    node.branch_id,
                    reason=f"Failed node {node.node_id}: {exc}",
                )

            return {
                "success": False,
                "node_id": node.node_id,
                "status": node.status,
                "error": str(exc),
                "retry_count": node.retry_count,
                "reflection": reflection.model_dump(),
            }


# Global singleton instance
dag_state_manager = DAGStateManager()
