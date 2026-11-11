"""Unit and Safety Integration Tests for Cross-Application Workflow Automator & Window Context Synchronizer.

Validates multi-app workflow execution, data pipelining, window focus coordination,
stack restoration, Rule 8 payment defenses, and Guardian SLA halt.
Phase 25-03 (AUT-05, WIN-02, SAF-01, SAF-02).
"""

import time
import pytest

from services.backend.orchestrator.cross_app_orchestrator import (
    CrossAppOrchestrator,
    CrossAppStep,
    Rule8ViolationError as WorkflowR8,
    cross_app_orchestrator,
)
from services.backend.orchestrator.window_focus_synchronizer import (
    WindowFocusSynchronizer,
    Rule8ViolationError as WindowR8,
    window_focus_synchronizer,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.cross_app_workflow_tools  # Ensure tools are loaded


@pytest.fixture(autouse=True)
def reset_state():
    guardian.resume()
    yield
    guardian.resume()


def test_cross_app_workflow_execution_and_data_piping():
    """Verify multi-app workflow executes steps and pipes output variables between apps."""
    orchestrator = CrossAppOrchestrator()

    steps = [
        CrossAppStep(
            step_id=1,
            app_name="Edge",
            action="EXTRACT_SELECTION",
            output_variable="api_docs",
        ),
        CrossAppStep(
            step_id=2,
            app_name="VSCode",
            action="PASTE_TRANSFORM",
            input_payload="Implement interface from ${api_docs}",
            output_variable="code_diff",
        ),
        CrossAppStep(
            step_id=3,
            app_name="Windows Terminal",
            action="EXECUTE_COMMAND",
            input_payload="pytest tests/ -k 'test_api'",
        ),
    ]

    wf = orchestrator.create_workflow("Documentation to Test Pipeline", steps)
    assert wf.status == "INITIALIZED"

    executed = orchestrator.execute_workflow()
    assert executed.status == "COMPLETED"
    assert len(executed.steps) == 3
    assert all(s.status == "SUCCESS" for s in executed.steps)
    assert "api_docs" in executed.shared_pipeline_context
    assert "code_diff" in executed.shared_pipeline_context
    assert "Extracted from Edge" in executed.shared_pipeline_context["api_docs"]


def test_window_focus_switching_and_stack_restoration():
    """Verify window focus switching, layout querying, and LIFO stack restoration."""
    syncer = WindowFocusSynchronizer()

    layout = syncer.get_layout()
    assert layout.active_window is not None
    assert len(layout.open_windows) == 3

    # Switch to Terminal
    focused_term = syncer.switch_focus("Terminal")
    assert focused_term.process_name == "WindowsTerminal.exe"
    assert focused_term.is_foreground is True

    # Switch to Edge
    focused_edge = syncer.switch_focus("msedge.exe")
    assert focused_edge.process_name == "msedge.exe"

    # Restore previous (should be Terminal)
    restored_term = syncer.restore_previous_focus()
    assert restored_term is not None
    assert restored_term.process_name == "WindowsTerminal.exe"

    # Restore again (should be initial IDE)
    restored_ide = syncer.restore_previous_focus()
    assert restored_ide is not None
    assert restored_ide.process_name == "Code.exe"


def test_rule_8_anti_checkout_enforcement():
    """Verify payment and checkout workflows and window targets are blocked with Rule8ViolationError."""
    orchestrator = CrossAppOrchestrator()
    syncer = WindowFocusSynchronizer()

    with pytest.raises(WorkflowR8, match="Rule 8"):
        orchestrator.create_workflow(
            "Amazon Checkout Workflow",
            [CrossAppStep(step_id=1, app_name="Edge", action="CLICK")],
        )

    with pytest.raises(WorkflowR8, match="Rule 8"):
        orchestrator.create_workflow(
            "Process Data",
            [CrossAppStep(step_id=1, app_name="Edge", action="PASTE", input_payload="credit card cvv pay")],
        )

    with pytest.raises(WindowR8, match="Rule 8"):
        syncer.switch_focus("checkout payment portal")


def test_guardian_kill_switch_sla_halt():
    """Verify Guardian kill switch synchronously interrupts cross-app workflow in < 25.0ms SLA."""
    guardian.trigger("Emergency Cross-App Halt")
    assert guardian.is_halted

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        cross_app_orchestrator.create_workflow("Test", [])
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    assert halt_duration_ms < 25.0, f"Halt latency {halt_duration_ms:.4f}ms exceeded 25.0ms SLA"

    with pytest.raises(PermissionError, match="Guardian kill switch"):
        window_focus_synchronizer.get_layout()

    guardian.resume()
    assert not guardian.is_halted


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    wf_tool = registry.get("orchestrate_cross_app_workflow")
    assert wf_tool is not None
    assert wf_tool.tier == 1
    preview_wf = wf_tool.generate_preview({
        "title": "Doc Sync",
        "steps": [{"app_name": "Edge"}, {"app_name": "VSCode"}],
    })
    assert "Doc Sync" in preview_wf
    assert "2 application step" in preview_wf

    focus_tool = registry.get("sync_window_workspace_focus")
    assert focus_tool is not None
    assert focus_tool.tier == 0
    preview_focus = focus_tool.generate_preview({"target_window": "VSCode"})
    assert "VSCode" in preview_focus

    status_tool = registry.get("get_ambient_workflow_status")
    assert status_tool is not None
    assert status_tool.tier == 0
    preview_status = status_tool.generate_preview({})
    assert "ambient cross-application workflow" in preview_status
