"""
Tests for Phase 47-01: Mission DAG Decomposer, Precondition Engine & Upfront Approval Modal.
Verifies requirements: DAG-01, DAG-02, DAG-03, DAG-04.
"""

import time
import pytest
from typing import Dict, Any, List

from services.backend.schemas.mission_dag import (
    DAGNode,
    DAGNodeStatus,
    RiskLevel,
    MissionDAG,
    PreconditionCheckResult,
)
from services.backend.orchestrator.dag_decomposer import (
    MissionDAGDecomposer,
    CycleDetectedError,
)
from services.backend.safety.precondition_engine import (
    PreconditionEngine,
    MissionPreconditionError,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.file_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    """Ensure Guardian kill switch is clear before and after every test."""
    guardian.resume()
    yield
    guardian.resume()


# ============================================================================
# 1. Pydantic DAG Schema Validation (DAG-01)
# ============================================================================

def test_dag_schema_validation():
    """Validates Pydantic v2 DAGNode and MissionDAG models serialization, validation, and defaults."""
    node = DAGNode(
        node_id="step_1",
        title="Read source file",
        tool_name="read_file",
        arguments={"path": "services/backend/main.py"},
        tier=0,
    )
    assert node.status in (DAGNodeStatus.pending, DAGNodeStatus.PENDING)
    assert node.depends_on == []
    assert node.timeout_seconds == 60
    assert node.result is None

    dag = MissionDAG(
        mission_id="mission_test_001",
        goal="Audit codebase security",
        nodes=[node],
        risk_level=RiskLevel.low,
    )
    assert dag.mission_id == "mission_test_001"
    assert dag.requires_confirmation is False
    assert dag.is_approved is False
    assert len(dag.nodes) == 1

    # Verify JSON serialization round-trip
    dumped = dag.model_dump()
    assert dumped["mission_id"] == "mission_test_001"
    assert dumped["nodes"][0]["node_id"] == "step_1"
    restored = MissionDAG.model_validate(dumped)
    assert restored.mission_id == dag.mission_id
    assert restored.nodes[0].title == "Read source file"


# ============================================================================
# 2. Topological Sort & Wave Partitioning via Kahn's Algorithm (DAG-01)
# ============================================================================

def test_topological_sort_and_waves_kahns_algorithm():
    """Verifies that Kahn's algorithm correctly groups independent tasks into concurrent waves."""
    nodes = [
        DAGNode(node_id="A", title="Fetch requirements", tool_name="search_codebase", tier=0),
        DAGNode(node_id="B", title="Read config", tool_name="read_file", tier=0),
        DAGNode(node_id="C", title="Generate patch", tool_name="edit_file", depends_on=["A", "B"], tier=1),
        DAGNode(node_id="D", title="Run unit tests", tool_name="run_command", depends_on=["C"], tier=1),
        DAGNode(node_id="E", title="Run type check", tool_name="run_command", depends_on=["C"], tier=1),
        DAGNode(node_id="F", title="Create commit", tool_name="git_commit", depends_on=["D", "E"], tier=2),
    ]

    decomposer = MissionDAGDecomposer()
    sorted_order = decomposer.topological_sort(nodes)
    assert len(sorted_order) == 6

    # Verify order constraints: dependencies must precede dependents
    pos = {node.node_id: idx for idx, node in enumerate(sorted_order)}
    assert pos["A"] < pos["C"]
    assert pos["B"] < pos["C"]
    assert pos["C"] < pos["D"]
    assert pos["C"] < pos["E"]
    assert pos["D"] < pos["F"]
    assert pos["E"] < pos["F"]

    # Verify wave partitioning
    waves = decomposer.partition_into_waves(nodes)
    assert len(waves) == 4
    assert {n.node_id for n in waves[0]} == {"A", "B"}
    assert {n.node_id for n in waves[1]} == {"C"}
    assert {n.node_id for n in waves[2]} == {"D", "E"}
    assert {n.node_id for n in waves[3]} == {"F"}


# ============================================================================
# 3. Circular Dependency & Cycle Detection (DAG-01)
# ============================================================================

def test_dag_cycle_detection_rejection():
    """Verifies that circular dependencies are detected immediately and raise CycleDetectedError."""
    cyclic_nodes = [
        DAGNode(node_id="alpha", title="Alpha", tool_name="read_file", depends_on=["gamma"]),
        DAGNode(node_id="beta", title="Beta", tool_name="edit_file", depends_on=["alpha"]),
        DAGNode(node_id="gamma", title="Gamma", tool_name="run_command", depends_on=["beta"]),
    ]

    decomposer = MissionDAGDecomposer()
    with pytest.raises(CycleDetectedError) as exc_info:
        decomposer.topological_sort(cyclic_nodes)

    err_msg = str(exc_info.value)
    assert "Cycle detected" in err_msg


# ============================================================================
# 4. Dynamic Argument Resolution (DAG-01)
# ============================================================================

def test_dynamic_argument_resolution():
    """Verifies resolution of dynamic input references ($node_id.output.key) across nodes."""
    decomposer = MissionDAGDecomposer()
    node = DAGNode(
        node_id="test_step",
        title="Execute test",
        tool_name="run_command",
        arguments={
            "command": "pytest $build_step.output.target_path",
            "working_dir": "$setup_step.output.cwd",
            "static_flag": "-v",
        },
    )

    completed_outputs = {
        "build_step": {"target_path": "services/backend/tests/test_safety.py"},
        "setup_step": {"cwd": "C:/Phenom"},
    }

    resolved = decomposer.resolve_node_arguments(node, completed_outputs)
    assert resolved["command"] == "pytest services/backend/tests/test_safety.py"
    assert resolved["working_dir"] == "C:/Phenom"
    assert resolved["static_flag"] == "-v"


# ============================================================================
# 5. Natural Language Goal Decomposition (DAG-01)
# ============================================================================

def test_natural_language_goal_decomposition_coding():
    """Verifies decomposition of software engineering prompts into multi-step DAG."""
    decomposer = MissionDAGDecomposer()
    goal = "Fix the authentication bug in services/backend/main.py and run the pytest suite"
    dag = decomposer.decompose_goal(goal)

    assert bool(dag.mission_id)
    assert len(dag.nodes) >= 3
    # First step should inspect, clone, or read
    assert dag.nodes[0].tool_name in ("clone_workspace", "search_codebase", "read_file")
    # Later step should test
    test_nodes = [n for n in dag.nodes if n.tool_name in ("run_tests", "run_command")]
    assert len(test_nodes) >= 1
    assert len(dag.nodes) >= 3


def test_natural_language_goal_decomposition_research():
    """Verifies decomposition of deep research prompts into multi-step DAG."""
    decomposer = MissionDAGDecomposer()
    goal = "Research offline vector embeddings and summarize findings into vault notes"
    dag = decomposer.decompose_goal(goal)

    assert len(dag.nodes) >= 3
    # Step tools should include search and notes
    tool_names = [n.tool_name for n in dag.nodes]
    assert any("search" in t or "read" in t for t in tool_names)
    assert any("note" in t or "write" in t for t in tool_names)


# ============================================================================
# 6. Precondition Engine Path Validation (DAG-03)
# ============================================================================

def test_precondition_engine_path_validation():
    """Verifies path allowlist validation blocks forbidden paths and permits allowed paths."""
    engine = PreconditionEngine()

    # Allowlisted repo path
    valid_node = DAGNode(
        node_id="valid_node",
        title="Read backend file",
        tool_name="read_file",
        arguments={"path": "services/backend/main.py"},
        tier=0,
    )
    dag_valid = MissionDAG(mission_id="m_val", goal="Valid task", nodes=[valid_node])
    res_valid = engine.check_mission_preconditions(dag_valid, strict=False)
    assert res_valid.passed is True
    assert len(res_valid.violations) == 0

    # Unallowlisted path outside any safe folder (e.g. Windows System32)
    invalid_node = DAGNode(
        node_id="invalid_node",
        title="Read sensitive file",
        tool_name="read_file",
        arguments={"path": "C:\\Windows\\System32\\drivers\\etc\\hosts"},
        tier=0,
    )
    dag_invalid = MissionDAG(mission_id="m_inval", goal="Invalid task", nodes=[invalid_node])
    res_invalid = engine.check_mission_preconditions(dag_invalid, strict=False)
    assert res_invalid.passed is False
    assert any("prohibited" in v.lower() or "path security" in v.lower() or "denied" in v.lower() or "allowlist" in v.lower() for v in res_invalid.violations)

    # In strict mode, should raise MissionPreconditionError
    with pytest.raises(MissionPreconditionError):
        engine.check_mission_preconditions(dag_invalid, strict=True)


# ============================================================================
# 7. Precondition Engine Tool Availability (DAG-03)
# ============================================================================

def test_precondition_engine_missing_tool():
    """Verifies that referencing an unregistered tool fails precondition validation."""
    engine = PreconditionEngine()
    phantom_node = DAGNode(
        node_id="phantom_step",
        title="Execute unregistered action",
        tool_name="phantom_unregistered_tool_12345",
        arguments={"data": "test"},
        tier=0,
    )
    dag = MissionDAG(mission_id="m_tool", goal="Missing tool task", nodes=[phantom_node])
    res = engine.check_mission_preconditions(dag, strict=False)
    assert res.passed is False
    assert any("phantom_unregistered_tool_12345" in v for v in res.violations)


# ============================================================================
# 8. Tier 2 / Tier 3 Escalation and Upfront Approval Gating (DAG-02, DAG-04)
# ============================================================================

def test_tier2_tier3_confirmation_escalation():
    """Verifies that presence of Tier 2 or Tier 3 actions escalates risk and marks requires_confirmation=True."""
    engine = PreconditionEngine()

    tier3_node = DAGNode(
        node_id="dangerous_step",
        title="Execute system install",
        tool_name="install_package",
        arguments={"package_name": "curl"},
        tier=3,
    )
    dag = MissionDAG(
        mission_id="m_tier3",
        goal="System modification task",
        nodes=[tier3_node],
        risk_level=RiskLevel.low,
        requires_confirmation=False,
    )

    res = engine.check_mission_preconditions(dag, strict=False)
    assert dag.requires_confirmation is True
    assert dag.risk_level in (RiskLevel.high, RiskLevel.critical, RiskLevel.HIGH, RiskLevel.CRITICAL)


# ============================================================================
# 9. Guardian Kill Switch SLA During Mission Planning (DAG-04)
# ============================================================================

def test_guardian_kill_switch_during_dag_planning():
    """Verifies that Guardian halt immediately prevents mission execution within < 25.0ms SLA."""
    # Trigger kill switch
    t_start = time.perf_counter()
    guardian.trigger()
    t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    # Must halt within < 25ms SLA
    assert t_elapsed_ms < 25.0, f"Guardian kill switch took {t_elapsed_ms:.2f}ms (exceeded 25ms SLA)"
    assert guardian.is_halted is True

    # Precondition check or execution under halted Guardian must be rejected
    engine = PreconditionEngine()
    node = DAGNode(node_id="step_x", title="Action", tool_name="read_file", tier=0)
    dag = MissionDAG(mission_id="m_halted", goal="Goal", nodes=[node])

    # Precondition check under halt
    with pytest.raises(MissionPreconditionError, match="Guardian kill switch is active"):
        engine.check_mission_preconditions(dag, strict=True)
