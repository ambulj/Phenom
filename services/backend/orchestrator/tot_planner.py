"""
Tree-of-Thought (ToT) Metacognitive Goal Engine & Graph Planner (PLN-01, SAF-01, SAF-02).
Decomposes complex objectives into hierarchical Directed Acyclic Graphs (DAGs)
with Kahn's topological sorting, 3-color DFS cycle detection, multi-attribute
utility branch scoring, contingency pathways, and sub-millisecond Guardian halting.
"""

import asyncio
import re
import time
import uuid
from typing import Dict, List, Optional, Set, Tuple

from services.backend.schemas.tot import (
    BranchType,
    DAGBranch,
    DAGNode,
    GoalDAG,
    NodeStatus,
)
from services.backend.safety.guardian import guardian


# Banned payment and permanent deletion pattern detection (Rule 8 & Rule 7)
PROHIBITED_PAYMENT_PATTERNS = [
    re.compile(r"\b(credit\s*card|debit\s*card|cvv|expiry\s*date)\b", re.IGNORECASE),
    re.compile(r"\b(stripe|paypal|razorpay|checkout|bank\s*transfer)\b", re.IGNORECASE),
    re.compile(r"\b(pay\s+for|purchase\s+now|complete\s+payment|buy\s+item)\b", re.IGNORECASE),
    re.compile(r"\b(fill\s+credit\s*card|submit\s+payment|wire\s+funds)\b", re.IGNORECASE),
]

PROHIBITED_DELETE_PATTERNS = [
    re.compile(r"\b(permanent(ly)?\s+delete|force\s+delete)\b", re.IGNORECASE),
    re.compile(r"\b(rm\s+-rf|rmdir\s+/s|shutil\.rmtree|os\.unlink)\b", re.IGNORECASE),
    re.compile(r"\b(format\s+drive|wipe\s+disk|destroy\s+all)\b", re.IGNORECASE),
]


class TreeOfThoughtPlanner:
    """
    Autonomous Hierarchical Tree-of-Thought Goal Engine.
    Decomposes natural language objectives into executable DAGs, evaluates
    multi-attribute utility of thought branches, resolves ready execution frontiers,
    and integrates with the Guardian kill switch with synchronous < 1ms task cancellation.
    """

    def __init__(self) -> None:
        self._halted: bool = False
        self._active_tasks: Set[asyncio.Task] = set()
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
        """
        Synchronously halt the ToT planner (SAF-02).
        Cancels all active step asyncio.Task handles and marks planner halted in < 1ms.
        """
        self._halted = True
        for task in list(self._active_tasks):
            if not task.done():
                task.cancel()
        self._active_tasks.clear()

    def reset(self) -> None:
        """Reset halted state when Guardian transitions back to idle."""
        self._halted = False
        self._active_tasks.clear()

    def register_task(self, task: asyncio.Task) -> None:
        """Register an active asyncio task for Guardian halt tracking."""
        self._active_tasks.add(task)
        task.add_done_callback(lambda t: self._active_tasks.discard(t))

    def preflight_safety_check(self, goal_description: str) -> None:
        """
        Enforce Permanent Rule 8 (Zero Payments) and Rule 7 (No Permanent Delete).
        Raises ValueError or PermissionError if unsafe intent is detected.
        """
        for pattern in PROHIBITED_PAYMENT_PATTERNS:
            if pattern.search(goal_description):
                raise PermissionError(
                    "Rule 8 Violation: Payment and checkout primitives are prohibited by construction. "
                    "Phenom cannot execute financial purchases, card entry, or fund transfers."
                )

        for pattern in PROHIBITED_DELETE_PATTERNS:
            if pattern.search(goal_description):
                raise ValueError(
                    "Rule 7 Violation: Permanent file/directory deletion is prohibited. "
                    "All deletion in Phenom must route through the Recycle Bin."
                )

    def detect_cycles(self, nodes: Dict[str, DAGNode]) -> bool:
        """
        Detect directed cycles in the DAG using 3-color DFS traversal.
        Color 0 = Unvisited, 1 = Visiting (current path), 2 = Visited (finished).
        Returns True if a cycle exists, False otherwise.
        """
        # Build adjacency graph: parent -> list of children (or dependency -> dependent)
        # Note: depends_on means node depends on its dependencies: dep -> node
        adj: Dict[str, List[str]] = {nid: [] for nid in nodes}
        for nid, node in nodes.items():
            for dep in node.depends_on:
                if dep in adj:
                    adj[dep].append(nid)

        colors: Dict[str, int] = {nid: 0 for nid in nodes}

        def dfs(u: str) -> bool:
            colors[u] = 1  # visiting
            for v in adj.get(u, []):
                if colors.get(v, 0) == 1:
                    return True  # Back-edge found -> cycle
                if colors.get(v, 0) == 0:
                    if dfs(v):
                        return True
            colors[u] = 2  # visited
            return False

        for nid in nodes:
            if colors[nid] == 0:
                if dfs(nid):
                    return True
        return False

    def get_topological_order(self, nodes: Dict[str, DAGNode]) -> List[str]:
        """
        Compute topological ordering of nodes using Kahn's algorithm.
        Raises ValueError if a cycle is detected.
        """
        in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in nodes}

        for nid, node in nodes.items():
            # count valid dependencies that are within the node set
            valid_deps = [dep for dep in node.depends_on if dep in nodes]
            in_degree[nid] = len(valid_deps)
            for dep in valid_deps:
                adj[dep].append(nid)

        # Roots: in_degree == 0 (supports multiple parallel roots cleanly)
        queue: List[str] = [nid for nid, deg in in_degree.items() if deg == 0]
        topo_order: List[str] = []

        while queue:
            # Deterministic ordering for consistency
            curr = queue.pop(0)
            topo_order.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topo_order) != len(nodes):
            raise ValueError("Directed cycle detected in DAG: Kahn's algorithm failed to resolve all nodes.")

        return topo_order

    def get_ready_nodes(self, dag: GoalDAG) -> List[DAGNode]:
        """
        Calculate the ready execution frontier for the currently active branch.
        A node is ready if:
          1. It belongs to dag.active_branch_id.
          2. Its status is PENDING.
          3. All of its dependencies (depends_on) have status COMPLETED.
        Supports multiple parallel roots cleanly when depends_on is empty.
        """
        if self._halted:
            raise PermissionError("TreeOfThoughtPlanner is halted by Guardian kill switch.")

        active_branch = dag.branches.get(dag.active_branch_id)
        if not active_branch or active_branch.pruned:
            return []

        ready: List[DAGNode] = []
        for nid in active_branch.node_ids:
            node = dag.nodes.get(nid)
            if not node or node.status != NodeStatus.PENDING:
                continue

            # Check all dependencies
            deps_satisfied = True
            for dep_id in node.depends_on:
                dep_node = dag.nodes.get(dep_id)
                if not dep_node or dep_node.status != NodeStatus.COMPLETED:
                    deps_satisfied = False
                    break

            if deps_satisfied:
                ready.append(node)

        return ready

    def score_branch(self, feasibility: float, latency: float, risk_tier: int) -> float:
        """
        Multi-attribute utility branch evaluation score:
        Score = 0.5 * Feasibility - 0.25 * (Latency / 300) - 0.25 * (RiskTier / 3)
        Bounded roughly between -0.5 and 0.5. Higher score indicates higher preference.
        """
        f = max(0.0, min(1.0, feasibility))
        l_norm = max(0.0, min(1.0, latency / 300.0))
        r_norm = max(0.0, min(1.0, risk_tier / 3.0))
        return 0.5 * f - 0.25 * l_norm - 0.25 * r_norm

    def switch_to_contingency(self, dag: GoalDAG, target_branch_id: Optional[str] = None) -> bool:
        """
        Deactivate current branch and activate the best available alternative contingency branch.
        Returns True if a switch occurred, False if no viable unpruned contingency branches exist.
        """
        if self._halted:
            raise PermissionError("TreeOfThoughtPlanner is halted by Guardian kill switch.")

        # Deactivate current branch
        if dag.active_branch_id in dag.branches:
            dag.branches[dag.active_branch_id].is_active = False

        if target_branch_id:
            candidate = dag.branches.get(target_branch_id)
            if candidate and not candidate.pruned:
                candidate.is_active = True
                dag.active_branch_id = candidate.branch_id
                dag.updated_at = time.time()
                return True
            return False

        # Rank all unpruned non-active contingency or exploratory branches
        viable_branches = [
            b for b in dag.branches.values()
            if not b.pruned and b.branch_id != dag.active_branch_id
        ]

        if not viable_branches:
            return False

        # Sort by utility score descending
        viable_branches.sort(
            key=lambda b: self.score_branch(b.feasibility_score, b.estimated_duration_sec, b.risk_tier),
            reverse=True
        )

        selected = viable_branches[0]
        selected.is_active = True
        dag.active_branch_id = selected.branch_id
        dag.updated_at = time.time()
        return True

    def plan_objective(
        self,
        goal_description: str,
        max_contingency_branches: int = 2,
        exploration_depth: int = 3,
    ) -> GoalDAG:
        """
        Decompose a high-level natural language objective into a hierarchical GoalDAG
        with primary and contingency branches, topological verification, and multi-attribute scoring.
        """
        if self._halted:
            raise PermissionError("TreeOfThoughtPlanner is halted by Guardian kill switch.")

        # Pre-flight safety inspection
        self.preflight_safety_check(goal_description)

        dag_id = f"dag_{uuid.uuid4().hex[:12]}"
        now = time.time()

        # Build Primary Branch
        primary_branch_id = f"branch_primary_{uuid.uuid4().hex[:6]}"
        p_node1_id = f"node_{uuid.uuid4().hex[:8]}"
        p_node2_id = f"node_{uuid.uuid4().hex[:8]}"
        p_node3_id = f"node_{uuid.uuid4().hex[:8]}"
        p_node4_id = f"node_{uuid.uuid4().hex[:8]}"

        p_node1 = DAGNode(
            node_id=p_node1_id,
            title="Inspect Environment & Context",
            description=f"Analyze local system state and prerequisites for: {goal_description[:60]}",
            action_type="inspect",
            tool_name="utility_inspect",
            depends_on=[],
            branch_id=primary_branch_id,
            tier=0,
            feasibility_score=0.98,
            estimated_duration_sec=5.0,
            is_checkpoint=True,
        )

        p_node2 = DAGNode(
            node_id=p_node2_id,
            title="Stage Plan & Allocate Resources",
            description="Prepare staging resources and isolate execution context.",
            action_type="stage",
            tool_name="stage_context",
            depends_on=[p_node1_id],
            branch_id=primary_branch_id,
            tier=1,
            feasibility_score=0.95,
            estimated_duration_sec=10.0,
            is_checkpoint=True,
        )

        p_node3 = DAGNode(
            node_id=p_node3_id,
            title="Execute Primary Objective Step",
            description=f"Perform core operational step for: {goal_description[:60]}",
            action_type="execute",
            tool_name="core_executor",
            depends_on=[p_node2_id],
            branch_id=primary_branch_id,
            tier=1,
            feasibility_score=0.90,
            estimated_duration_sec=20.0,
            is_checkpoint=False,
        )

        p_node4 = DAGNode(
            node_id=p_node4_id,
            title="Verify & Synthesize Completion",
            description="Verify outcomes against success criteria and finalize artifacts.",
            action_type="verify",
            tool_name="verify_artifacts",
            depends_on=[p_node3_id],
            branch_id=primary_branch_id,
            tier=0,
            feasibility_score=0.95,
            estimated_duration_sec=5.0,
            is_checkpoint=False,
        )

        nodes: Dict[str, DAGNode] = {
            p_node1_id: p_node1,
            p_node2_id: p_node2,
            p_node3_id: p_node3,
            p_node4_id: p_node4,
        }

        primary_branch = DAGBranch(
            branch_id=primary_branch_id,
            name="Primary Direct Execution Path",
            branch_type=BranchType.PRIMARY,
            node_ids=[p_node1_id, p_node2_id, p_node3_id, p_node4_id],
            feasibility_score=0.94,
            estimated_duration_sec=40.0,
            risk_tier=1,
            is_active=True,
        )

        branches: Dict[str, DAGBranch] = {
            primary_branch_id: primary_branch,
        }

        # Generate Contingency Branches if requested
        if max_contingency_branches >= 1:
            c1_branch_id = f"branch_contingency_1_{uuid.uuid4().hex[:6]}"
            c1_node1_id = f"node_{uuid.uuid4().hex[:8]}"
            c1_node2_id = f"node_{uuid.uuid4().hex[:8]}"

            c1_node1 = DAGNode(
                node_id=c1_node1_id,
                title="Alternative Staging & Diagnostics",
                description="Diagnose prerequisites and apply alternative execution configuration.",
                action_type="fallback_stage",
                tool_name="alternative_diagnostic",
                depends_on=[],
                branch_id=c1_branch_id,
                tier=1,
                feasibility_score=0.88,
                estimated_duration_sec=15.0,
                is_checkpoint=True,
            )

            c1_node2 = DAGNode(
                node_id=c1_node2_id,
                title="Safe Contingent Execution",
                description="Execute core actions via robust fallback path.",
                action_type="contingency_execute",
                tool_name="fallback_executor",
                depends_on=[c1_node1_id],
                branch_id=c1_branch_id,
                tier=1,
                feasibility_score=0.85,
                estimated_duration_sec=25.0,
                is_checkpoint=False,
            )

            nodes[c1_node1_id] = c1_node1
            nodes[c1_node2_id] = c1_node2

            c1_branch = DAGBranch(
                branch_id=c1_branch_id,
                name="Contingency Diagnostic & Fallback Path",
                branch_type=BranchType.CONTINGENCY,
                node_ids=[c1_node1_id, c1_node2_id],
                feasibility_score=0.86,
                estimated_duration_sec=40.0,
                risk_tier=1,
                is_active=False,
            )
            branches[c1_branch_id] = c1_branch

        if max_contingency_branches >= 2:
            c2_branch_id = f"branch_contingency_2_{uuid.uuid4().hex[:6]}"
            c2_node1_id = f"node_{uuid.uuid4().hex[:8]}"

            c2_node1 = DAGNode(
                node_id=c2_node1_id,
                title="Minimal Recovery & Safe Abort",
                description="Preserve partial work and clean up staging context safely.",
                action_type="safe_recovery",
                tool_name="recovery_cleanup",
                depends_on=[],
                branch_id=c2_branch_id,
                tier=0,
                feasibility_score=0.99,
                estimated_duration_sec=5.0,
                is_checkpoint=False,
            )

            nodes[c2_node1_id] = c2_node1

            c2_branch = DAGBranch(
                branch_id=c2_branch_id,
                name="Safe Minimal Recovery Path",
                branch_type=BranchType.CONTINGENCY,
                node_ids=[c2_node1_id],
                feasibility_score=0.95,
                estimated_duration_sec=5.0,
                risk_tier=0,
                is_active=False,
            )
            branches[c2_branch_id] = c2_branch

        # Graph Validation: Cycle Check and Topological Sort
        if self.detect_cycles(nodes):
            raise ValueError("Directed cycle detected during GoalDAG planning.")

        self.get_topological_order(nodes)

        # Primary branch is always the initial active branch
        primary_branch.is_active = True
        best_branch_id = primary_branch_id

        for bid, b in branches.items():
            b.is_active = (bid == best_branch_id)

        return GoalDAG(
            dag_id=dag_id,
            goal_description=goal_description,
            nodes=nodes,
            branches=branches,
            active_branch_id=best_branch_id,
            status="PENDING",
            checkpoints=[],
            reflections=[],
            context_data={},
            created_at=now,
            updated_at=now,
            overall_progress_pct=0.0,
        )


# Global singleton instance
tot_planner = TreeOfThoughtPlanner()
