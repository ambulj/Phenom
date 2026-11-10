"""
Dynamic Directed Acyclic Graph (DAG) Swarm Task Orchestrator.
Decomposes complex objectives into dependency-aware topological execution waves,
dispatches parallel subagents, manages intermediate checkpoints, and heals failed nodes.

Part of Phenom 22.0 Sovereign Swarm Intelligence (SWM-01.1 / AUT-03.1).
"""

import time
import uuid
import asyncio
import re
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.swarm.subagent_pool import subagent_pool
from services.backend.automation.gui_controller import Rule8ViolationError

RULE_8_PAYMENT_RE = re.compile(
    r"\b(?:checkout|place\s+order|pay\s+now|buy\s+now|complete\s+purchase|complete\s+payment|payment|credit\s+card|cvv|password)\b",
    re.IGNORECASE
)


class DAGNode(BaseModel):
    node_id: str = Field(..., description="Unique node identifier")
    name: str = Field(..., description="Human-readable node task name")
    role: str = Field(default="general", description="researcher, coder, tester, reviewer, synthesizer")
    action_type: str = Field(default="execute", description="Action verb")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Input parameters and task instructions")
    dependencies: List[str] = Field(default_factory=list, description="List of upstream node_ids that must complete first")
    status: str = Field(default="pending", description="pending, running, completed, failed, skipped")
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    duration_ms: float = 0.0


class SwarmDAG(BaseModel):
    dag_id: str = Field(..., description="Unique DAG run identifier")
    goal: str = Field(..., description="Overarching user objective")
    nodes: Dict[str, DAGNode] = Field(default_factory=dict, description="Nodes map by node_id")
    waves: List[List[str]] = Field(default_factory=list, description="Ordered parallel execution waves [[node_id, ...], ...]")
    current_wave_index: int = 0
    status: str = Field(default="pending", description="pending, running, completed, failed, halted")
    created_at: float = Field(default_factory=time.time)
    total_duration_ms: float = 0.0


class DAGOrchestrator:
    """
    Orchestrates swarm task DAGs: topological sorting, wave scheduling, state checkpointing, and backtracking.
    """

    def __init__(self):
        self._dags: Dict[str, SwarmDAG] = {}

    def get_dag(self, dag_id: str) -> Optional[SwarmDAG]:
        return self._dags.get(dag_id)

    def _partition_into_waves(self, nodes: Dict[str, DAGNode]) -> List[List[str]]:
        """
        Computes topological waves using Kahn's algorithm.
        Ensures nodes within the same wave are mutually independent and can execute concurrently.
        Raises ValueError if circular dependency is detected.
        """
        in_degrees: Dict[str, int] = {nid: len(node.dependencies) for nid, node in nodes.items()}
        dependents: Dict[str, List[str]] = {nid: [] for nid in nodes}

        for nid, node in nodes.items():
            for dep in node.dependencies:
                if dep in dependents:
                    dependents[dep].append(nid)
                else:
                    raise ValueError(f"Node '{nid}' references non-existent upstream dependency '{dep}'")

        waves: List[List[str]] = []
        current_wave = [nid for nid, deg in in_degrees.items() if deg == 0]
        processed_count = 0

        while current_wave:
            waves.append(sorted(current_wave))
            processed_count += len(current_wave)
            next_wave = []

            for nid in current_wave:
                for child in dependents[nid]:
                    in_degrees[child] -= 1
                    if in_degrees[child] == 0:
                        next_wave.append(child)

            current_wave = next_wave

        if processed_count < len(nodes):
            raise ValueError("Circular dependency cycle detected in swarm task DAG.")

        return waves

    def create_dag(self, goal: str, nodes_list: List[DAGNode], dag_id: Optional[str] = None) -> SwarmDAG:
        """Creates a validated, topologically partitioned SwarmDAG."""
        if guardian.is_halted:
            raise PermissionError("Guardian kill switch is active. Swarm DAG creation blocked.")

        if RULE_8_PAYMENT_RE.search(goal):
            raise Rule8ViolationError(f"Rule 8 Violation: Cannot create swarm task DAG targeting payment or checkout: {goal}")

        for n in nodes_list:
            if RULE_8_PAYMENT_RE.search(n.name) or RULE_8_PAYMENT_RE.search(str(n.payload)):
                raise Rule8ViolationError(f"Rule 8 Violation: Cannot create swarm task node targeting payment or checkout: {n.name}")

        did = dag_id or f"dag_{uuid.uuid4().hex[:8]}"
        nodes_dict = {n.node_id: n for n in nodes_list}
        waves = self._partition_into_waves(nodes_dict)

        dag = SwarmDAG(
            dag_id=did,
            goal=goal,
            nodes=nodes_dict,
            waves=waves,
            current_wave_index=0,
            status="pending",
        )
        self._dags[did] = dag
        return dag

    def decompose_goal_into_dag(self, goal: str) -> SwarmDAG:
        """
        Heuristically decomposes a high-level goal into a standard 3-wave swarm development DAG:
        Wave 0: Research & Codebase AST Mapping (Parallel)
        Wave 1: Implementation & Patch Synthesis
        Wave 2: Isolated Verification Testing & Security Review (Parallel)
        """
        nodes = [
            DAGNode(
                node_id="node_research",
                name="Research Requirements & Architectural Patterns",
                role="researcher",
                action_type="research",
                payload={"goal": goal},
                dependencies=[]
            ),
            DAGNode(
                node_id="node_ast_map",
                name="Map Codebase Symbols & AST Dependencies",
                role="synthesizer",
                action_type="ast_map",
                payload={"goal": goal},
                dependencies=[]
            ),
            DAGNode(
                node_id="node_implement",
                name="Synthesize Code Implementation Patch",
                role="coder",
                action_type="code_patch",
                payload={"goal": goal},
                dependencies=["node_research", "node_ast_map"]
            ),
            DAGNode(
                node_id="node_test",
                name="Run Isolated Diagnostic Test Battery",
                role="tester",
                action_type="run_tests",
                payload={"goal": goal},
                dependencies=["node_implement"]
            ),
            DAGNode(
                node_id="node_review",
                name="Verify Security Boundaries & Rule 8 Invariants",
                role="reviewer",
                action_type="safety_review",
                payload={"goal": goal},
                dependencies=["node_implement"]
            )
        ]

        return self.create_dag(goal=goal, nodes_list=nodes)

    async def execute_wave(self, dag_id: str, wave_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes a single wave of DAG nodes concurrently using the subagent worker pool.
        Includes automatic retry backtracking on failed nodes.
        Strictly halts on Guardian trigger (< 25.0ms SLA).
        """
        dag = self.get_dag(dag_id)
        if not dag:
            raise KeyError(f"Swarm DAG '{dag_id}' not found")

        if guardian.is_halted:
            dag.status = "halted"
            raise PermissionError("Guardian kill switch is active. Swarm wave execution halted.")

        t0 = time.perf_counter()
        w_idx = wave_index if wave_index is not None else dag.current_wave_index

        if w_idx >= len(dag.waves):
            dag.status = "completed"
            return {"status": "completed", "message": "All waves already executed"}

        node_ids = dag.waves[w_idx]
        dag.status = "running"

        # Collect upstream outputs for each node in this wave
        async def run_single_node(nid: str) -> Dict[str, Any]:
            node = dag.nodes[nid]
            node.status = "running"

            # Gather all outputs from dependencies
            upstream_data = {}
            for dep_id in node.dependencies:
                dep_node = dag.nodes.get(dep_id)
                if dep_node and dep_node.output:
                    upstream_data[dep_node.role] = dep_node.output

            # Execute via subagent pool with automatic retry backtracking
            for attempt in range(node.max_retries + 1):
                if guardian.is_halted:
                    node.status = "failed"
                    node.error = "Interrupted by Guardian kill switch"
                    raise PermissionError("Guardian kill switch triggered during swarm node execution.")

                res = await subagent_pool.execute_subagent_task(
                    node_id=node.node_id,
                    role=node.role,
                    action_type=node.action_type,
                    payload=node.payload,
                    upstream_outputs=upstream_data,
                )

                if res.get("status") == "completed":
                    node.status = "completed"
                    node.output = res.get("output")
                    node.duration_ms = res.get("duration_ms", 0.0)
                    return res
                else:
                    node.retry_count += 1
                    node.error = res.get("error", "Unknown error")
                    if attempt < node.max_retries:
                        await asyncio.sleep(0.01)  # Brief backoff before retry

            node.status = "failed"
            return {"node_id": nid, "status": "failed", "error": node.error}

        # Execute all nodes in the wave in parallel
        wave_results = await asyncio.gather(*(run_single_node(nid) for nid in node_ids), return_exceptions=True)

        # Check if any exceptions or failed nodes
        any_failed = any(
            isinstance(r, Exception) or (isinstance(r, dict) and r.get("status") == "failed")
            for r in wave_results
        )

        wave_duration = (time.perf_counter() - t0) * 1000.0
        dag.total_duration_ms += wave_duration

        if any_failed:
            dag.status = "failed"
            return {
                "wave_index": w_idx,
                "status": "failed",
                "nodes": node_ids,
                "duration_ms": wave_duration,
            }

        # Advance wave
        dag.current_wave_index += 1
        if dag.current_wave_index >= len(dag.waves):
            dag.status = "completed"

        return {
            "wave_index": w_idx,
            "status": "completed",
            "nodes": node_ids,
            "is_final_wave": dag.current_wave_index >= len(dag.waves),
            "duration_ms": wave_duration,
        }

    async def execute_all_waves(self, dag_id: str) -> SwarmDAG:
        """Executes all remaining waves of the DAG sequentially to completion."""
        dag = self.get_dag(dag_id)
        if not dag:
            raise KeyError(f"Swarm DAG '{dag_id}' not found")

        while dag.current_wave_index < len(dag.waves) and dag.status != "failed" and dag.status != "halted":
            res = await self.execute_wave(dag_id)
            if res.get("status") == "failed":
                break

        return dag

    def abort_dag(self, dag_id: str) -> bool:
        """Immediately aborts an active swarm DAG."""
        dag = self.get_dag(dag_id)
        if dag:
            dag.status = "halted"
            for n in dag.nodes.values():
                if n.status in ("pending", "running"):
                    n.status = "skipped"
            return True
        return False


# Global singleton
dag_orchestrator = DAGOrchestrator()
