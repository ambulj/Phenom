"""
Mission DAG Decomposer with Topological Sorting & Cycle Detection (Phase 47-01).
Enforces:
1. Kahn's algorithm topological sorting and execution wave partitioning.
2. Cycle detection raising CycleDetectedError on circular dependencies.
3. Dynamic argument resolution from predecessor node outputs ($node_id.output.key).
4. Goal decomposition into valid, typed MissionDAG instances.
"""

from typing import Dict, List, Any, Optional, Set
from collections import deque
import re
import json

from services.backend.schemas.mission_dag import (
    MissionDAG,
    DAGNode,
    DAGNodeStatus,
    RiskLevel
)
from services.backend.safety.registry import registry


class CycleDetectedError(ValueError):
    """Raised when a circular dependency is detected in a Mission DAG."""
    pass


class MissionDAGDecomposer:
    """Decomposes natural language goals into validated, acyclic Directed Acyclic Graphs."""

    def __init__(self):
        pass

    @staticmethod
    def topological_sort(nodes: List[DAGNode]) -> List[DAGNode]:
        """
        Orders DAGNodes in topological order using Kahn's algorithm.
        Raises CycleDetectedError if circular dependencies are detected.
        """
        node_map: Dict[str, DAGNode] = {n.node_id: n for n in nodes}
        in_degree: Dict[str, int] = {n.node_id: 0 for n in nodes}
        adjacency: Dict[str, List[str]] = {n.node_id: [] for n in nodes}

        # Build dependency graph
        for node in nodes:
            for dep_id in node.depends_on:
                if dep_id not in node_map:
                    raise ValueError(f"Node '{node.node_id}' depends on undefined node '{dep_id}'")
                adjacency[dep_id].append(node.node_id)
                in_degree[node.node_id] += 1

        # Enqueue nodes with zero in-degree
        queue: deque = deque([nid for nid, deg in in_degree.items() if deg == 0])
        sorted_nodes: List[DAGNode] = []

        while queue:
            curr_id = queue.popleft()
            sorted_nodes.append(node_map[curr_id])

            for neighbor_id in adjacency[curr_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        if len(sorted_nodes) != len(nodes):
            remaining = [nid for nid, deg in in_degree.items() if deg > 0]
            raise CycleDetectedError(f"Cycle detected in DAG among nodes: {remaining}")

        return sorted_nodes

    @staticmethod
    def partition_into_waves(nodes: List[DAGNode]) -> List[List[DAGNode]]:
        """
        Partitions topologically sorted nodes into parallel execution waves.
        Nodes in Wave K only depend on nodes in Waves < K.
        """
        if not nodes:
            return []

        # Validate acyclic first
        sorted_nodes = MissionDAGDecomposer.topological_sort(nodes)
        node_map: Dict[str, DAGNode] = {n.node_id: n for n in sorted_nodes}
        node_level: Dict[str, int] = {}

        for node in sorted_nodes:
            if not node.depends_on:
                node_level[node.node_id] = 0
            else:
                max_parent_level = max(node_level[dep_id] for dep_id in node.depends_on)
                node_level[node.node_id] = max_parent_level + 1

        max_wave = max(node_level.values(), default=0)
        waves: List[List[DAGNode]] = [[] for _ in range(max_wave + 1)]

        for node_id, level in node_level.items():
            waves[level].append(node_map[node_id])

        return waves

    @staticmethod
    def resolve_node_arguments(node_or_arguments: Any, completed_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively replaces dynamic placeholders like '$node-1.output.path' or '$node-1.output'
        with actual values from completed_results. Supports passing DAGNode or Dict.
        """
        if hasattr(node_or_arguments, "arguments"):
            arguments = node_or_arguments.arguments
        elif isinstance(node_or_arguments, dict):
            arguments = node_or_arguments
        else:
            return {}

        resolved: Dict[str, Any] = {}
        exact_pattern = re.compile(r"^\$([a-zA-Z0-9_\-]+)\.output(?:\.([a-zA-Z0-9_\.]+))?$")
        sub_pattern = re.compile(r"\$([a-zA-Z0-9_\-]+)\.output(?:\.([a-zA-Z0-9_\.]+))?")

        def _get_val(dep_id: str, prop: Optional[str]) -> Any:
            if dep_id not in completed_results:
                return None
            res_val = completed_results[dep_id]
            if prop and isinstance(res_val, dict):
                parts = prop.split(".")
                curr = res_val
                for p in parts:
                    if isinstance(curr, dict) and p in curr:
                        curr = curr[p]
                    else:
                        return None
                return curr
            return res_val

        for key, val in arguments.items():
            if isinstance(val, str):
                exact_match = exact_pattern.match(val.strip())
                if exact_match:
                    dep_id = exact_match.group(1)
                    prop_path = exact_match.group(2)
                    extracted = _get_val(dep_id, prop_path)
                    resolved[key] = extracted if extracted is not None else val
                else:
                    def _replace_sub(m):
                        d = m.group(1)
                        p = m.group(2)
                        v = _get_val(d, p)
                        return str(v) if v is not None else m.group(0)
                    resolved[key] = sub_pattern.sub(_replace_sub, val)
            elif isinstance(val, dict):
                resolved[key] = MissionDAGDecomposer.resolve_node_arguments(val, completed_results)
            elif isinstance(val, list):
                res_list = []
                for item in val:
                    if isinstance(item, str):
                        exact_m = exact_pattern.match(item.strip())
                        if exact_m:
                            ex = _get_val(exact_m.group(1), exact_m.group(2))
                            res_list.append(ex if ex is not None else item)
                        else:
                            def _repl(m):
                                v = _get_val(m.group(1), m.group(2))
                                return str(v) if v is not None else m.group(0)
                            res_list.append(sub_pattern.sub(_repl, item))
                    elif isinstance(item, dict):
                        res_list.append(MissionDAGDecomposer.resolve_node_arguments(item, completed_results))
                    else:
                        res_list.append(item)
                resolved[key] = res_list
            else:
                resolved[key] = val

        return resolved

    def decompose_goal(self, goal: str) -> MissionDAG:
        """
        Decomposes a high-level natural language prompt into a structured, acyclic MissionDAG.
        Uses intelligent task matching heuristics aligned with Phenom tools.
        """
        goal_lower = goal.lower()
        nodes: List[DAGNode] = []

        # 1. Coding / Bugfix / Test mission pattern
        if any(w in goal_lower for w in ["code", "bug", "fix", "test", "clone", "git", "repo", "refactor"]):
            nodes.append(
                DAGNode(
                    node_id="node-1",
                    title="Clone project to isolated workspace sandbox",
                    tool_name="clone_workspace",
                    arguments={"project_name": "target_project", "source_path": "."},
                    tier=1,
                    depends_on=[]
                )
            )
            nodes.append(
                DAGNode(
                    node_id="node-2",
                    title="Run test suite to verify initial state or reproduce issue",
                    tool_name="run_tests",
                    arguments={"workspace_dir": "$node-1.output.workspace_dir"},
                    tier=1,
                    depends_on=["node-1"]
                )
            )
            nodes.append(
                DAGNode(
                    node_id="node-3",
                    title="Apply code transformation with AST syntax validation",
                    tool_name="apply_code_edit",
                    arguments={"workspace_dir": "$node-1.output.workspace_dir", "task": goal},
                    tier=1,
                    depends_on=["node-2"]
                )
            )
            nodes.append(
                DAGNode(
                    node_id="node-4",
                    title="Run regression tests to verify fix",
                    tool_name="run_tests",
                    arguments={"workspace_dir": "$node-1.output.workspace_dir"},
                    tier=1,
                    depends_on=["node-3"]
                )
            )
            nodes.append(
                DAGNode(
                    node_id="node-5",
                    title="Generate unified diff and apply changes to repository",
                    tool_name="git_command",
                    arguments={"action": "commit", "message": f"fix: resolve {goal[:50]}"},
                    tier=2,
                    depends_on=["node-4"]
                )
            )

        # 2. Deep Research / Literature / Vault synthesis pattern
        elif any(w in goal_lower for w in ["research", "paper", "arxiv", "literature", "summarize", "vault", "study"]):
            nodes.append(
                DAGNode(
                    node_id="node-1",
                    title="Search research papers and technical documentation",
                    tool_name="search_research_papers",
                    arguments={"query": goal},
                    tier=0,
                    depends_on=[]
                )
            )
            nodes.append(
                DAGNode(
                    node_id="node-2",
                    title="Synthesize document extracts and cross-reference findings",
                    tool_name="summarize_long_document",
                    arguments={"source_data": "$node-1.output.results"},
                    tier=0,
                    depends_on=["node-1"]
                )
            )
            nodes.append(
                DAGNode(
                    node_id="node-3",
                    title="Commit synthesized report to Obsidian Vault",
                    tool_name="vault_write_note",
                    arguments={
                        "title": f"Research - {goal[:40]}",
                        "content": "$node-2.output.summary",
                        "folder": "Research"
                    },
                    tier=1,
                    depends_on=["node-2"]
                )
            )

        # 3. Desktop Automation / App / Cleanup pattern
        elif any(w in goal_lower for w in ["clean", "download", "organize", "desktop", "file", "sort"]):
            nodes.append(
                DAGNode(
                    node_id="node-1",
                    title="Inspect downloads folder and compute organization preview",
                    tool_name="organize_downloads_dry_run",
                    arguments={},
                    tier=0,
                    depends_on=[]
                )
            )
            nodes.append(
                DAGNode(
                    node_id="node-2",
                    title="Apply file movements with pre-action snapshot",
                    tool_name="organize_downloads_apply",
                    arguments={"manifest": "$node-1.output.manifest"},
                    tier=1,
                    depends_on=["node-1"]
                )
            )

        # 4. Default generic single/two-step fallback
        else:
            nodes.append(
                DAGNode(
                    node_id="node-1",
                    title="Inspect environment and system context",
                    tool_name="list_files",
                    arguments={"path": "."},
                    tier=0,
                    depends_on=[]
                )
            )
            nodes.append(
                DAGNode(
                    node_id="node-2",
                    title=f"Execute task: {goal[:60]}",
                    tool_name="desktop_execute_plan",
                    arguments={"task": goal},
                    tier=2,
                    depends_on=["node-1"]
                )
            )

        # Verify tool tiers against Registry if registered
        for node in nodes:
            tool_def = registry.get(node.tool_name)
            if tool_def:
                node.tier = tool_def.tier

        # Verify topological sort passes without cycles
        sorted_nodes = self.topological_sort(nodes)

        dag = MissionDAG(
            goal=goal,
            nodes=sorted_nodes
        )
        dag.recalculate_risk()
        return dag


dag_decomposer = MissionDAGDecomposer()
