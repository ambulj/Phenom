"""
Mission Precondition Engine & Safety Escalation Gate (Phase 47-01).
Enforces:
1. Tool registry verification for all requested DAG node actions.
2. Path allowlist and system denylist validation via path_guard.py.
3. Input file existence checking prior to execution dispatch.
4. Dynamic safety tier escalation and confirmation enforcement (DAG-03, DAG-04).
"""

from typing import Dict, List, Any, Optional
import os

from services.backend.schemas.mission_dag import (
    MissionDAG,
    DAGNode,
    PreconditionCheckResult
)
from services.backend.safety.registry import registry
from services.backend.safety.path_guard import (
    validate_path,
    PathSecurityViolation
)
from services.backend.safety.taint import taint_tracker
from services.backend.safety.guardian import guardian


class MissionPreconditionError(PermissionError):
    """Raised when a mission DAG node violates path boundaries, missing tools, or security prerequisites."""
    pass


class PreconditionEngine:
    """Validates pre-flight environmental, path, and safety prerequisites for autonomous missions."""

    PATH_KEYS = {
        "path", "src", "dest", "folder", "directory", "filename",
        "source_path", "workspace_dir", "file_path", "target_path"
    }

    WRITE_TOOLS = {
        "create_file", "write_file", "create_folder", "copy_file",
        "move_file", "generate_document", "vault_write_note", "apply_code_edit"
    }

    DELETE_TOOLS = {
        "recycle_delete", "delete_file", "delete_folder", "cleanup_folder"
    }

    def __init__(self):
        pass

    def check_node_preconditions(self, node: DAGNode) -> PreconditionCheckResult:
        """
        Validates a single DAGNode's prerequisites:
        1. Tool presence in registry.
        2. All file paths conform to path_guard allowlists.
        3. File existence for input files.
        4. Tier alignment against registry and taint tracker.
        """
        checked_paths: List[str] = []
        checked_tools: List[str] = [node.tool_name]
        violations: List[str] = []

        # 1. Tool Registry Verification
        tool_def = registry.get(node.tool_name)
        if not tool_def:
            violations.append(f"Tool '{node.tool_name}' is not registered in ToolRegistry.")
        else:
            # Sync node declared tier with registry tier
            if node.tier < tool_def.tier:
                node.tier = tool_def.tier

        # Check taint escalation
        eff_tier, taint_warning = taint_tracker.check_tool_escalation(node.tool_name, node.tier)
        if eff_tier > node.tier:
            node.tier = eff_tier
            if taint_warning:
                violations.append(f"Taint Warning for node '{node.node_id}': {taint_warning}")

        # 2. Path Security & Allowlist Auditing
        path_mode = "read"
        if node.tool_name in self.WRITE_TOOLS:
            path_mode = "write"
        elif node.tool_name in self.DELETE_TOOLS:
            path_mode = "delete"

        for key, val in node.arguments.items():
            if key in self.PATH_KEYS and isinstance(val, str):
                # If dynamic placeholder reference (e.g. $node-1.output.path), skip pre-flight path check
                if val.strip().startswith("$"):
                    continue

                checked_paths.append(val)
                try:
                    validate_path(val, mode=path_mode)
                except PathSecurityViolation as pse:
                    violations.append(f"Node '{node.node_id}' argument '{key}'={val} violates path security: {pse}")
                except Exception as ex:
                    violations.append(f"Node '{node.node_id}' argument '{key}' path error: {ex}")

                # For read mode, check file existence if path appears to be a specific existing file
                if path_mode == "read" and not violations:
                    norm = os.path.expanduser(os.path.expandvars(val))
                    if os.path.splitext(norm)[1] and not os.path.exists(norm):
                        violations.append(f"Node '{node.node_id}' input file not found: {val}")

        passed = len(violations) == 0
        return PreconditionCheckResult(
            passed=passed,
            checked_paths=checked_paths,
            checked_tools=checked_tools,
            violations=violations
        )

    def check_mission_preconditions(
        self,
        dag: MissionDAG,
        raise_on_error: bool = False,
        strict: Optional[bool] = None,
    ) -> PreconditionCheckResult:
        """
        Validates all nodes across a complete MissionDAG.
        Optionally raises MissionPreconditionError if any violation is detected.
        """
        if strict is not None:
            raise_on_error = strict

        all_checked_paths: List[str] = []
        all_checked_tools: List[str] = []
        all_violations: List[str] = []

        if guardian.is_halted:
            all_violations.append("Guardian kill switch is active. Autonomous planning and execution halted.")

        for node in dag.nodes:
            res = self.check_node_preconditions(node)
            all_checked_paths.extend(res.checked_paths)
            all_checked_tools.extend(res.checked_tools)
            all_violations.extend(res.violations)

        # Recompute DAG risk after tier synchronization
        dag.recalculate_risk()

        passed = len(all_violations) == 0

        if not passed and raise_on_error:
            error_msg = f"Mission '{dag.mission_id}' failed pre-flight preconditions:\n" + "\n".join(f"- {v}" for v in all_violations)
            raise MissionPreconditionError(error_msg)

        return PreconditionCheckResult(
            passed=passed,
            checked_paths=all_checked_paths,
            checked_tools=all_checked_tools,
            violations=all_violations
        )


precondition_engine = PreconditionEngine()
