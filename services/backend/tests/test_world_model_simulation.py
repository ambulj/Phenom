"""Unit & Safety Tests for World-Model Simulation & Counterfactual Plan Evaluator (Milestone 26 Phase 3)."""

import pytest
import time
from services.backend.simulation.world_model_simulator import (
    WorldModelSimulator,
    Rule8ViolationError,
)
from services.backend.simulation.counterfactual_evaluator import CounterfactualEvaluator
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.world_model_tools  # Ensure registered


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_world_model_simulator_get_and_step():
    sim = WorldModelSimulator()
    state = sim.get_state()
    assert len(state.files) >= 2
    assert 1001 in state.processes
    assert state.active_window == "Phenom Cyber Desktop"

    # Simulate steps
    step1 = sim.simulate_step("FILE_WRITE", "C:/Phenom/test.py", {"content": "print('hello')"})
    assert step1.outcome == "SUCCESS"
    assert step1.state_delta["file_modified"] == "C:/Phenom/test.py"
    assert len(step1.side_effects) >= 1

    step2 = sim.simulate_step("SWITCH_WINDOW", "Visual Studio Code")
    assert step2.outcome == "SUCCESS"
    assert step2.state_delta["new_window"] == "Visual Studio Code"


def test_world_model_snapshot_and_rollback():
    sim = WorldModelSimulator()
    sim.snapshot()
    sim.simulate_step("FILE_DELETE", "C:/Phenom/test.py")
    assert sim.rollback() is True


def test_counterfactual_evaluator_nominal():
    evaluator = CounterfactualEvaluator()
    steps = [
        {"action": "WRITE_FILE", "target": "utils.py", "payload": {"content": "def add(a, b): return a + b"}},
        {"action": "FOCUS_WINDOW", "target": "Terminal"},
    ]
    report = evaluator.evaluate_plan("Safe Utility Update", steps)
    assert report.plan_title == "Safe Utility Update"
    assert report.nominal_feasibility_score >= 0.80
    assert report.overall_safety_rating == "SAFE_TO_DISPATCH"
    assert len(report.branches) == 3
    assert report.branches[0].branch_name == "NOMINAL_SUCCESS"
    assert report.branches[0].final_verdict == "PASS"


def test_counterfactual_evaluator_risky_plan():
    evaluator = CounterfactualEvaluator()
    steps = [
        {"action": "FILE_DELETE", "target": "legacy_db.sqlite"},
        {"action": "KILL_PROCESS", "target": "1002"},
        {"action": "EXEC_COMMAND", "target": "shell", "payload": {"command": "rm -rf build"}},
    ]
    report = evaluator.evaluate_plan("Destructive Cleanup Plan", steps)
    assert report.nominal_feasibility_score <= 0.60
    assert report.overall_safety_rating in ("REQUIRES_CONFIRMATION", "BLOCKED")
    assert len(report.predicted_side_effects) >= 3


def test_forecast_side_effects():
    evaluator = CounterfactualEvaluator()
    steps = [
        {"action": "FILE_WRITE", "target": "config.json", "payload": {"content": "{}"}},
        {"action": "SWITCH_WINDOW", "target": "Obsidian"},
    ]
    effects = evaluator.forecast_side_effects(steps)
    assert len(effects) >= 2


def test_rule_8_enforcement_simulation():
    sim = WorldModelSimulator()
    evaluator = CounterfactualEvaluator()

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        sim.simulate_step("PROCESS_KILL", "stripe_payment_service")

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        evaluator.evaluate_plan("Checkout Process Plan", [{"action": "CLICK", "target": "order_checkout"}])

    with pytest.raises(Rule8ViolationError, match="Rule 8 violation"):
        evaluator.forecast_side_effects([{"action": "INPUT", "target": "credit_card_input"}])


def test_guardian_kill_switch_sla_simulation():
    sim = WorldModelSimulator()
    evaluator = CounterfactualEvaluator()
    guardian.trigger(reason="Safety test")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        sim.get_state()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 25.0, f"Guardian SLA exceeded: {elapsed_ms:.4f}ms"

    t1 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch is TRIPPED"):
        evaluator.evaluate_plan("Test", [{"action": "WRITE_FILE", "target": "test.txt"}])
    elapsed_ms2 = (time.perf_counter() - t1) * 1000.0
    assert elapsed_ms2 < 25.0, f"Guardian SLA exceeded: {elapsed_ms2:.4f}ms"


def test_tool_registry_world_model_tools():
    # 1. simulate_plan_counterfactuals (Tier 0)
    tool_sim = registry.get("simulate_plan_counterfactuals")
    assert tool_sim is not None
    assert tool_sim.tier == 0
    prev_sim = tool_sim.preview_fn({"plan_title": "Build Test", "steps": [{"action": "BUILD"}]})
    assert "Simulate plan counterfactuals for 'Build Test'" in prev_sim

    res_sim = tool_sim.handler_fn(
        plan_title="Build Test",
        steps=[{"action": "FILE_WRITE", "target": "test.py", "payload": {"content": "print(1)"}}],
    )
    assert res_sim["nominal_feasibility_score"] >= 0.80

    # 2. evaluate_world_model_state (Tier 0)
    tool_eval = registry.get("evaluate_world_model_state")
    assert tool_eval is not None
    assert tool_eval.tier == 0
    res_eval = tool_eval.handler_fn(include_files=True)
    assert "files" in res_eval
    assert "processes" in res_eval

    # 3. forecast_side_effects (Tier 0)
    tool_forecast = registry.get("forecast_side_effects")
    assert tool_forecast is not None
    assert tool_forecast.tier == 0
    res_forecast = tool_forecast.handler_fn(
        steps=[{"action": "SWITCH_WINDOW", "target": "Browser"}]
    )
    assert res_forecast["side_effect_count"] >= 1
