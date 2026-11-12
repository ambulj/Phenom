"""
Phenom 5.0 Phase 1 Verification Suite
Comprehensive tests for:
1. AutonomousGoalPlanner: Goal decomposition, safety pre-flight checks, and Rule 8 payment prohibitions.
2. Checkpoint Engine: Serialization, step state preservation, and recovery.
3. AutonomousExecutionEngine: Supervised execution progression, telemetry events, and checkpoint saves.
4. Human Takeover Integration: Sub-second pause (< 1s), continue/stop decision handling.
5. Safety Layer Integration: Tier 2 registration and step-plan preview.
"""

import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from services.backend.automation.goal_planner import (
    AutonomousGoalPlanner,
    GoalPlan,
    PlanStep,
    TaskCheckpoint,
    goal_planner
)
from services.backend.automation.autonomous_engine import (
    AutonomousExecutionEngine,
    autonomous_engine
)
from services.backend.automation.human_takeover import takeover_manager
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.tools.automation_tools import execute_autonomous_task


# =====================================================================
# 1. GOAL PLANNER TESTS
# =====================================================================

def test_goal_planner_decomposition():
    planner = AutonomousGoalPlanner()
    plan = planner.plan_goal("Search for trending repositories on GitHub")
    
    assert plan.task_id.startswith("task-")
    assert plan.total_steps == 4
    assert len(plan.steps) == 4
    assert plan.steps[0].action_type == "browser_navigate"
    assert plan.steps[0].step_number == 1
    assert "github.com/trending" in plan.steps[0].params.get("url", "")
    assert plan.steps[-1].action_type == "save_result"
    assert plan.estimated_duration_sec > 0


def test_prohibited_payment_actions_blocked():
    planner = AutonomousGoalPlanner()
    prohibited_goals = [
        "Go to Amazon, buy shoes, and complete checkout",
        "Place order for pizza on Zomato",
        "Enter credit card details and pay now",
        "Submit payment OTP and confirm purchase",
        "Permanently delete all files on C: drive"
    ]
    for pg in prohibited_goals:
        with pytest.raises(PermissionError) as exc_info:
            planner.plan_goal(pg)
        assert "strictly prohibited by SAFETY.md" in str(exc_info.value)


def test_empty_goal_rejected():
    planner = AutonomousGoalPlanner()
    with pytest.raises(ValueError) as exc_info:
        planner.plan_goal("   ")
    assert "cannot be empty" in str(exc_info.value)


# =====================================================================
# 2. CHECKPOINT ENGINE TESTS
# =====================================================================

def test_checkpoint_serialization_and_recovery():
    planner = AutonomousGoalPlanner()
    checkpoint = TaskCheckpoint(
        task_id="task-test-1234",
        current_step_index=2,
        state="paused_takeover",
        step_results=[
            {"step": 1, "status": "success"},
            {"step": 2, "status": "success"}
        ]
    )
    serialized = planner.serialize_checkpoint(checkpoint)
    assert isinstance(serialized, str)
    assert "task-test-1234" in serialized

    recovered = planner.deserialize_checkpoint(serialized)
    assert recovered.task_id == "task-test-1234"
    assert recovered.current_step_index == 2
    assert recovered.state == "paused_takeover"
    assert len(recovered.step_results) == 2


# =====================================================================
# 3. SUPERVISED EXECUTION LOOP TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_autonomous_execution_progression():
    engine = AutonomousExecutionEngine()
    dispatched_events = []

    async def mock_bc(etype, payload):
        dispatched_events.append((etype, payload))

    engine.set_broadcaster(mock_bc)

    # 3-step test plan
    plan = GoalPlan(
        task_id="task-smoke-1",
        goal_description="Research Python libraries",
        steps=[
            PlanStep(step_number=1, description="Navigate to docs", action_type="browser_navigate", params={"url": "https://python.org"}),
            PlanStep(step_number=2, description="Click search input", action_type="mouse_click", params={"x": 400, "y": 250}),
            PlanStep(step_number=3, description="Extract text", action_type="extract_text", params={})
        ],
        total_steps=3
    )

    res = await engine.execute_plan(plan)
    assert res["status"] == "completed"
    assert res["steps_completed"] == 3
    assert engine.current_checkpoint.state == "completed"
    assert len(engine.current_checkpoint.step_results) == 3

    # Verify telemetry events emitted to Cyber HUD
    event_types = [e[0] for e in dispatched_events]
    assert "screen.overlay_state" in event_types
    assert "screen.action_ticker" in event_types
    assert "screen.click_highlight" in event_types


@pytest.mark.asyncio
async def test_checkpoint_resume_execution():
    engine = AutonomousExecutionEngine()
    plan = GoalPlan(
        task_id="task-resume-1",
        goal_description="Multi-step download",
        steps=[
            PlanStep(step_number=1, description="Step 1", action_type="test_step"),
            PlanStep(step_number=2, description="Step 2", action_type="test_step"),
            PlanStep(step_number=3, description="Step 3", action_type="test_step")
        ],
        total_steps=3
    )
    checkpoint = TaskCheckpoint(
        task_id="task-resume-1",
        current_step_index=1,  # Resume from Step 2
        state="paused_takeover"
    )

    res = await engine.resume_from_checkpoint(checkpoint, plan)
    assert res["status"] == "completed"
    # Should have executed steps from index 1 to 2 (2 steps executed)
    assert len(engine.current_checkpoint.step_results) == 2


# =====================================================================
# 4. HUMAN TAKEOVER TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_takeover_continue_decision():
    engine = AutonomousExecutionEngine()
    plan = GoalPlan(
        task_id="task-takeover-continue",
        goal_description="Test takeover resume",
        steps=[
            PlanStep(step_number=1, description="Step 1", action_type="step1"),
            PlanStep(step_number=2, description="Step 2", action_type="step2")
        ],
        total_steps=2
    )

    try:
        # Schedule user takeover pause during step 1 (50ms in), and continue at 100ms
        async def trigger_takeover_and_continue():
            await asyncio.sleep(0.05)
            takeover_manager._trigger_pause("test_user_mouse")
            await asyncio.sleep(0.05)
            engine.handle_takeover_decision("continue")

        asyncio.create_task(trigger_takeover_and_continue())

        res = await engine.execute_plan(plan)
        assert res["status"] == "completed"
        assert res["steps_completed"] == 2
    finally:
        takeover_manager.end_automation()


@pytest.mark.asyncio
async def test_takeover_stop_decision():
    engine = AutonomousExecutionEngine()
    plan = GoalPlan(
        task_id="task-takeover-stop",
        goal_description="Test takeover abort",
        steps=[
            PlanStep(step_number=1, description="Step 1", action_type="step1"),
            PlanStep(step_number=2, description="Step 2", action_type="step2"),
            PlanStep(step_number=3, description="Step 3", action_type="step3")
        ],
        total_steps=3
    )

    try:
        # Schedule user takeover pause during step 1 (50ms in), and stop at 100ms
        async def trigger_takeover_and_stop():
            await asyncio.sleep(0.05)
            takeover_manager._trigger_pause("test_user_keyboard")
            await asyncio.sleep(0.05)
            engine.handle_takeover_decision("stop")

        asyncio.create_task(trigger_takeover_and_stop())

        res = await engine.execute_plan(plan)
        assert res["status"] == "stopped_by_user"
        # Stopped after step 1 was finished and before step 2
        assert res["steps_completed"] == 1
    finally:
        takeover_manager.end_automation()


# =====================================================================
# 5. SAFETY REGISTRY & PREVIEW TESTS
# =====================================================================

def test_execute_autonomous_task_safety_registration():
    tool = registry.get("execute_autonomous_task")
    assert tool is not None, "execute_autonomous_task must be registered in Safety Registry"
    assert tool.tier == 2, "execute_autonomous_task must be classified as Tier 2"
    assert tool.preview_fn is not None, "execute_autonomous_task must have a preview function"

    preview = tool.preview_fn({"goal": "Search GitHub for trending repos"})
    assert "Search GitHub for trending repos" in preview
    assert "Navigate to GitHub Trending" in preview
    assert "(Supervised execution with sub-second takeover pause)" in preview
