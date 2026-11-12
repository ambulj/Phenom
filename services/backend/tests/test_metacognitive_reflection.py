"""
Tests for Metacognitive Self-Reflection & Execution Calibration Engine.
Part of Phenom 23.0 Sovereign Neural Evolution (META-01, COG-01, SAF-01, SAF-02).
"""

import time
import os
import pytest
from typing import Dict, Any

from services.backend.metacognition.reflective_auditor import (
    ReflectiveAuditor,
    ExecutionStep,
    TrajectoryAudit,
    reflective_auditor,
)
from services.backend.metacognition.reflection_vault_logger import (
    ReflectionVaultLogger,
    reflection_vault_logger,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.automation.gui_controller import Rule8ViolationError
import services.backend.tools.metacognitive_tools as meta_tools


@pytest.fixture(autouse=True)
def reset_guardian():
    guardian.resume()
    yield
    guardian.resume()


def test_trajectory_audit_successful_run():
    """Verify trajectory audit accurately computes calibration score on nominal run."""
    auditor = ReflectiveAuditor()
    steps = [
        ExecutionStep(step_id=1, tool_name="detect_display_topology", status="success", latency_ms=12.4),
        ExecutionStep(step_id=2, tool_name="apply_window_layout_preset", status="success", latency_ms=45.1),
    ]

    audit = auditor.audit_trajectory(
        user_intent="Tile windows into coding focus preset",
        steps=steps,
        prior_confidence=0.95,
    )

    assert audit.audit_id.startswith("audit_")
    assert audit.steps_count == 2
    assert audit.successful_steps == 2
    assert audit.failed_steps == 0
    # Success rate is 1.0; prior confidence is 0.95; calibration is 1.0 - |0.95 - 1.0| = 0.95
    assert abs(audit.calibration_score - 0.95) < 0.01
    assert "nominal" in audit.root_cause_analysis.lower() or "succeeded" in audit.root_cause_analysis.lower()


def test_trajectory_audit_partial_failure_root_cause():
    """Verify failed steps trigger root cause identification and tool mitigation advice."""
    auditor = ReflectiveAuditor()
    steps = [
        ExecutionStep(step_id=1, tool_name="hybrid_rag_search", status="success", latency_ms=22.0),
        ExecutionStep(step_id=2, tool_name="execute_macro_step", status="error", latency_ms=110.0, error_message="Element not found"),
    ]

    audit = auditor.audit_trajectory(
        user_intent="Search docs and click export button",
        steps=steps,
        prior_confidence=0.90,
    )

    assert audit.successful_steps == 1
    assert audit.failed_steps == 1
    # Actual success rate is 0.5; prior confidence is 0.90; calibration is 1.0 - |0.90 - 0.50| = 0.60
    assert abs(audit.calibration_score - 0.60) < 0.01
    assert "execute_macro_step" in audit.root_cause_analysis
    assert "Element not found" in audit.root_cause_analysis
    assert "Verify preconditions" in audit.suggested_prompt_mitigation


def test_reflection_note_vault_logging(tmp_path):
    """Verify non-destructive markdown reflection note writing with YAML frontmatter."""
    logger = ReflectionVaultLogger(reflection_dir=str(tmp_path))
    audit = TrajectoryAudit(
        audit_id="audit_test_99",
        user_intent="Test automated logging",
        steps_count=3,
        successful_steps=3,
        failed_steps=0,
        epistemic_confidence=0.95,
        calibration_score=0.95,
        root_cause_analysis="Nominal test execution.",
        suggested_prompt_mitigation="Keep standard heuristics.",
        created_at=time.time(),
    )

    filepath = logger.log_reflection_note(audit)
    assert os.path.exists(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "audit_id: \"audit_test_99\"" in content
    assert "calibration_score: 0.95" in content
    assert "Test automated logging" in content
    assert "Nominal test execution." in content


def test_aggregate_calibration_statistics():
    """Verify calculation of mean calibration scores across multiple audits."""
    auditor = ReflectiveAuditor()
    auditor.audit_trajectory(user_intent="Task 1", steps=[ExecutionStep(step_id=1, tool_name="t1", status="success")], prior_confidence=1.0)
    auditor.audit_trajectory(user_intent="Task 2", steps=[ExecutionStep(step_id=1, tool_name="t2", status="error", error_message="Fail")], prior_confidence=0.8)

    stats = auditor.get_calibration_stats()
    assert stats["total_audits"] == 2
    assert 0.0 <= stats["average_calibration_score"] <= 1.0
    assert len(stats["recent_audits"]) == 2


def test_rule_8_anti_checkout_enforcement():
    """Rule 8: Attempting to audit tasks targeting payments must raise Rule8ViolationError."""
    auditor = ReflectiveAuditor()
    with pytest.raises(Rule8ViolationError):
        auditor.audit_trajectory(
            user_intent="Complete order and payment for $149",
            steps=[],
        )


def test_guardian_kill_switch_sla_halt():
    """Guardian trigger must synchronously interrupt trajectory auditing in < 25.0ms SLA."""
    guardian.trigger()
    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        reflective_auditor.audit_trajectory(user_intent="Audit under halt", steps=[])
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA exceeded: {latency_ms:.4f}ms >= 25.0ms"


def test_tool_registry_and_previews():
    """Verify tool registration and preview generator functions in ToolRegistry."""
    tool_names = [
        "audit_execution_trajectory",
        "record_reflection_note",
        "get_metacognitive_calibration_stats",
    ]
    for name in tool_names:
        tool = registry.get(name)
        assert tool is not None, f"Tool {name} is not registered in ToolRegistry"
        assert callable(tool.handler_fn)

    # Preview generators
    preview_audit = registry.get("audit_execution_trajectory").generate_preview({
        "user_intent": "Run isolated test suite",
        "steps": [{"step_id": 1, "tool_name": "run_test"}],
    })
    assert "Audit trajectory" in preview_audit

    preview_stats = registry.get("get_metacognitive_calibration_stats").generate_preview({})
    assert "calibration" in preview_stats.lower()
