"""Unit & Safety Tests for Adaptive Multi-Path Speculative Planner & Branch Pruner (Milestone 28 Phase 2)."""

import pytest
import time
from services.backend.planning.speculative_planner import (
    SpeculativePlanner,
    PlanBranch,
    BranchType,
)
from services.backend.planning.branch_pruner import (
    BranchPruner,
    PruningAuditRecord,
)
from services.backend.planning.goal_decomposition_engine import Rule8ViolationError
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.speculative_planning_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_default_speculative_matrix_initialization():
    planner = SpeculativePlanner()
    branches = planner.get_branches()
    assert len(branches) == 3

    b_types = [b.branch_type for b in branches]
    assert BranchType.NOMINAL_PRIMARY in b_types
    assert BranchType.CONTINGENCY_EXPEDIENT in b_types
    assert BranchType.DEFENSIVE_CONSERVATIVE in b_types

    selected = [b for b in branches if b.is_selected]
    assert len(selected) == 1
    assert selected[0].branch_type == BranchType.NOMINAL_PRIMARY


def test_generate_speculative_branches_custom_goal():
    planner = SpeculativePlanner()
    branches = planner.generate_speculative_branches("Deploy Micro-Sandbox Isolation Container")
    assert len(branches) == 3

    nominal = next(b for b in branches if b.branch_type == BranchType.NOMINAL_PRIMARY)
    expedient = next(b for b in branches if b.branch_type == BranchType.CONTINGENCY_EXPEDIENT)
    defensive = next(b for b in branches if b.branch_type == BranchType.DEFENSIVE_CONSERVATIVE)

    # Check distinct risk and feasibility profiles
    assert nominal.feasibility_score >= 0.90
    assert expedient.estimated_total_latency_ms < nominal.estimated_total_latency_ms
    assert defensive.risk_score < nominal.risk_score
    assert len(defensive.steps) >= 4


def test_evaluate_risk_matrix():
    planner = SpeculativePlanner()
    pruner = BranchPruner(planner=planner)
    target = "Verify Zero-Trust File Permissions"
    planner.generate_speculative_branches(target)

    matrix = pruner.evaluate_risk_matrix(target)
    assert len(matrix) == 3

    for item in matrix:
        assert "composite_utility" in item
        expected = round(item["feasibility_score"] * (1.0 - item["risk_score"]), 3)
        assert item["composite_utility"] == expected


def test_prune_high_risk_branches():
    planner = SpeculativePlanner()
    pruner = BranchPruner(planner=planner)
    target = "Perform High-Throughput Stream Transformation"
    planner.generate_speculative_branches(target)

    # Prune with max_acceptable_risk = 0.25 (should prune expedient with risk 0.38)
    result = pruner.prune_branches(
        target_id=target,
        max_acceptable_risk=0.25,
        min_acceptable_feasibility=0.70,
    )

    assert result["pruned_branch_count"] == 1
    assert result["viable_branch_count"] == 2
    assert result["selected_branch_id"] is not None

    branches = planner.get_branches(target)
    expedient = next(b for b in branches if b.branch_type == BranchType.CONTINGENCY_EXPEDIENT)
    assert expedient.is_pruned is True
    assert expedient.is_selected is False

    history = pruner.get_audit_history()
    assert len(history) >= 1
    assert history[-1]["target_id"] == target


def test_prune_all_exceeding_fallback():
    planner = SpeculativePlanner()
    pruner = BranchPruner(planner=planner)
    target = "Ultra Conservative Goal"
    planner.generate_speculative_branches(target)

    # Threshold so strict that even normal branches would exceed (max_risk = 0.01)
    result = pruner.prune_branches(
        target_id=target,
        max_acceptable_risk=0.01,
        min_acceptable_feasibility=0.99,
    )

    # Should safely fallback to safest branch rather than zero viable branches
    assert result["viable_branch_count"] == 1
    assert "safest fallback" in result["selection_reason"]


def test_manual_branch_selection():
    planner = SpeculativePlanner()
    target = "Manual Switch Target"
    branches = planner.generate_speculative_branches(target)
    defensive = next(b for b in branches if b.branch_type == BranchType.DEFENSIVE_CONSERVATIVE)

    selected = planner.select_branch(target, defensive.branch_id)
    assert selected.branch_id == defensive.branch_id
    assert selected.is_selected is True

    nominal = next(b for b in branches if b.branch_type == BranchType.NOMINAL_PRIMARY)
    assert nominal.is_selected is False


def test_rule_8_anti_checkout_speculative():
    planner = SpeculativePlanner()
    pruner = BranchPruner(planner=planner)

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        planner.generate_speculative_branches("Initiate checkout order payment")

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        pruner.evaluate_risk_matrix("Pay credit card invoice")

    with pytest.raises(Rule8ViolationError, match="Rule 8"):
        pruner.prune_branches("Stripe purchase subscription")


def test_guardian_kill_switch_sla_speculative():
    planner = SpeculativePlanner()
    pruner = BranchPruner(planner=planner)

    guardian.trigger(reason="Test Kill Switch Halt")
    t0 = time.perf_counter()

    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        planner.generate_speculative_branches("Should be halted immediately")

    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        pruner.evaluate_risk_matrix("Should be halted immediately")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    guardian.resume()
    res = planner.generate_speculative_branches("Resumed execution")
    assert len(res) == 3


def test_tool_registry_speculative_planning_tools():
    phase2_tools = [
        ("generate_speculative_plan_branches", 0),
        ("prune_nonviable_branches", 1),
        ("evaluate_branch_risk_matrix", 0),
    ]

    for tool_name, expected_tier in phase2_tools:
        tool_def = registry.get(tool_name)
        assert tool_def is not None, f"Tool '{tool_name}' must be registered"
        assert tool_def.tier == expected_tier, f"Tool '{tool_name}' tier mismatch"
        assert tool_def.preview_fn is not None
        assert tool_def.args_schema is not None
        assert tool_def.handler_fn is not None
