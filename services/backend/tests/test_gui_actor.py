"""Unit and Safety Integration Tests for Intent-Driven GUI Action Synthesizer & Safe Step Executor.

Validates action plan synthesis, coordinate bounds checking, human takeover aborts,
dry-run simulations, Rule 8 payment defenses, and Guardian SLA halt.
Phase 25-02 (ACT-02, EXEC-03, SAF-01, SAF-02).
"""

import time
import pytest

from services.backend.actor.gui_action_synthesizer import (
    GuiActionSynthesizer,
    GuiActionStep,
    Rule8ViolationError as SynthR8,
    gui_action_synthesizer,
)
from services.backend.actor.gui_step_executor import (
    GuiStepExecutor,
    Rule8ViolationError as ExecR8,
    gui_step_executor,
)
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
import services.backend.tools.gui_actor_tools  # Ensure tools are loaded


@pytest.fixture(autouse=True)
def reset_state():
    guardian.resume()
    gui_step_executor.reset_human_takeover()
    yield
    guardian.resume()
    gui_step_executor.reset_human_takeover()


def test_action_plan_synthesis_from_user_goal():
    """Verify high-level user tasks decompose into validated multi-step action plans."""
    synth = GuiActionSynthesizer()

    # Task 1: Search and open file
    plan1 = synth.synthesize_plan("search for main.py in the editor and open it")
    assert plan1.safety_tier == 1
    assert len(plan1.steps) == 3
    assert plan1.steps[0].action_type == "CLICK"
    assert plan1.steps[0].target_coordinates is not None
    assert plan1.steps[1].action_type == "TYPE_TEXT"
    assert plan1.steps[1].text_payload == "main.py"
    assert plan1.steps[2].action_type == "KEY_SHORTCUT"
    assert plan1.steps[2].key_combination == "Enter"

    # Task 2: Save and run tests
    plan2 = synth.synthesize_plan("save the file and run unit tests")
    assert len(plan2.steps) == 2
    assert plan2.steps[0].action_type == "CLICK"
    assert plan2.steps[1].action_type == "CLICK"


def test_step_executor_success_and_dry_run():
    """Verify safe step execution and dry-run preview mode."""
    executor = GuiStepExecutor()

    step = GuiActionStep(
        step_id=1,
        action_type="CLICK",
        target_coordinates=(500, 300),
        description="Click at valid screen anchor",
    )

    # Dry-run
    res_dry = executor.execute_step(step, dry_run=True)
    assert res_dry.status == "DRY_RUN"
    assert "Dry-Run" in res_dry.message
    assert res_dry.execution_duration_ms > 0

    # Live dispatch
    res_live = executor.execute_step(step, dry_run=False)
    assert res_live.status == "SUCCESS"
    assert "Successfully dispatched" in res_live.message


def test_human_takeover_abort_detection():
    """Verify execution aborts immediately upon human mouse or keyboard intervention."""
    executor = GuiStepExecutor()
    synth = GuiActionSynthesizer()

    plan = synth.synthesize_plan("search for api.py in the editor and open it")
    assert len(plan.steps) == 3

    # Human intervenes at step 2
    summary = executor.execute_plan(plan, dry_run=False, takeover_at_step=2)
    assert summary.status == "ABORTED_BY_HUMAN"
    assert summary.completed_steps == 1
    assert len(summary.step_results) == 2
    assert summary.step_results[1].status == "ABORTED_BY_HUMAN"
    assert "Human operator touched mouse" in summary.step_results[1].message


def test_coordinate_out_of_bounds_detection():
    """Verify execution rejects coordinates beyond display resolution bounds."""
    executor = GuiStepExecutor()

    step_oob = GuiActionStep(
        step_id=1,
        action_type="CLICK",
        target_coordinates=(2400, 1500),  # Exceeds 1920x1080
        description="Click far outside monitor",
    )

    res = executor.execute_step(step_oob)
    assert res.status == "OUT_OF_BOUNDS"
    assert "exceed screen bounds" in res.message


def test_rule_8_anti_checkout_enforcement():
    """Verify payment and checkout actions are blocked with Rule8ViolationError."""
    synth = GuiActionSynthesizer()
    executor = GuiStepExecutor()

    with pytest.raises(SynthR8, match="Rule 8"):
        synth.synthesize_plan("open cart and click checkout payment button")

    with pytest.raises(SynthR8, match="Rule 8"):
        synth.synthesize_plan("enter credit card number to buy item")

    bad_step = GuiActionStep(
        step_id=1,
        action_type="TYPE_TEXT",
        text_payload="card_cvv_123",
        description="Type billing credit card payment info",
    )
    with pytest.raises(ExecR8, match="Rule 8"):
        executor.execute_step(bad_step)


def test_guardian_kill_switch_sla_halt():
    """Verify Guardian kill switch synchronously interrupts GUI actions in < 25.0ms SLA."""
    guardian.trigger("Emergency GUI Action Abort")
    assert guardian.is_halted

    t0 = time.perf_counter()
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        gui_action_synthesizer.synthesize_plan("save changes and test")
    halt_duration_ms = (time.perf_counter() - t0) * 1000.0

    assert halt_duration_ms < 25.0, f"Halt latency {halt_duration_ms:.4f}ms exceeded 25.0ms SLA"

    step = GuiActionStep(step_id=1, action_type="CLICK", target_coordinates=(100, 100), description="Click")
    with pytest.raises(PermissionError, match="Guardian kill switch"):
        gui_step_executor.execute_step(step)

    guardian.resume()
    assert not guardian.is_halted


def test_tool_registry_and_previews():
    """Verify tool registration, tier classifications, and preview generations."""
    synth_tool = registry.get("synthesize_gui_action_plan")
    assert synth_tool is not None
    assert synth_tool.tier == 1
    preview_synth = synth_tool.generate_preview({"user_goal": "open main.py"})
    assert "open main.py" in preview_synth

    preview_tool = registry.get("preview_gui_action_step")
    assert preview_tool is not None
    assert preview_tool.tier == 0
    preview_step = preview_tool.generate_preview({
        "step_id": 1,
        "action_type": "CLICK",
        "description": "Click search",
        "target_x": 400,
        "target_y": 50,
    })
    assert "Click search" in preview_step

    exec_tool = registry.get("execute_gui_action_step")
    assert exec_tool is not None
    assert exec_tool.tier == 1
    preview_exec = exec_tool.generate_preview({
        "step_id": 1,
        "action_type": "CLICK",
        "description": "Click run tests button",
    })
    assert "Click run tests button" in preview_exec
