"""Safety-Wrapped GUI Actor Tools.

Registers tools with ToolRegistry for declarative action plan synthesis,
step preview generation, and safe virtual GUI step dispatch (Phase 25-02 ACT-02 / EXEC-03).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.actor.gui_action_synthesizer import (
    gui_action_synthesizer,
    GuiActionStep,
)
from services.backend.actor.gui_step_executor import gui_step_executor


# ==========================================
# 1. Synthesize GUI Action Plan (Tier 1)
# ==========================================

class SynthesizeGuiActionPlanArgs(BaseModel):
    user_goal: str = Field(..., description="High-level natural language desktop task (e.g. 'search for main.py in the editor and open it')")


def synthesize_gui_action_plan_preview(args: Dict[str, Any]) -> str:
    goal = args.get("user_goal", "unspecified task")
    return f"Synthesize declarative multi-step GUI interaction plan for desktop task: '{goal}'"


@registry.register(
    name="synthesize_gui_action_plan",
    tier=1,
    description="Deconstructs a user goal into a validated sequence of declarative GUI interaction steps.",
    args_schema=SynthesizeGuiActionPlanArgs,
    preview_fn=synthesize_gui_action_plan_preview,
    can_remember_per_folder=False,
)
def handle_synthesize_gui_action_plan(user_goal: str) -> Dict[str, Any]:
    plan = gui_action_synthesizer.synthesize_plan(user_goal=user_goal)
    return plan.model_dump()


# ==========================================
# 2. Preview GUI Action Step (Tier 0)
# ==========================================

class PreviewGuiActionStepArgs(BaseModel):
    step_id: int = Field(..., description="Step sequence ID")
    action_type: str = Field(..., description="GUI action type (CLICK, TYPE_TEXT, KEY_SHORTCUT)")
    description: str = Field(..., description="Action step description")
    target_x: Optional[int] = Field(None, description="Target X coordinate")
    target_y: Optional[int] = Field(None, description="Target Y coordinate")


def preview_gui_action_step_preview(args: Dict[str, Any]) -> str:
    desc = args.get("description", "GUI action step")
    action = args.get("action_type", "CLICK")
    x = args.get("target_x")
    y = args.get("target_y")
    coord_str = f" at ({x}, {y})" if x is not None and y is not None else ""
    return f"Preview GUI action {action}{coord_str}: {desc}"


@registry.register(
    name="preview_gui_action_step",
    tier=0,
    description="Inspects and validates an individual GUI action step before execution.",
    args_schema=PreviewGuiActionStepArgs,
    preview_fn=preview_gui_action_step_preview,
    can_remember_per_folder=False,
)
def handle_preview_gui_action_step(
    step_id: int,
    action_type: str,
    description: str,
    target_x: Optional[int] = None,
    target_y: Optional[int] = None,
) -> Dict[str, Any]:
    step = GuiActionStep(
        step_id=step_id,
        action_type=action_type,
        target_coordinates=(target_x, target_y) if target_x is not None and target_y is not None else None,
        description=description,
    )
    res = gui_step_executor.execute_step(step, dry_run=True)
    return res.model_dump()


# ==========================================
# 3. Execute GUI Action Step (Tier 1)
# ==========================================

class ExecuteGuiActionStepArgs(BaseModel):
    step_id: int = Field(..., description="Step sequence ID to execute")
    action_type: str = Field(..., description="GUI action type: CLICK, DOUBLE_CLICK, TYPE_TEXT, KEY_SHORTCUT")
    description: str = Field(..., description="Step description")
    target_x: Optional[int] = Field(None, description="Target X coordinate")
    target_y: Optional[int] = Field(None, description="Target Y coordinate")
    text_payload: Optional[str] = Field(None, description="Text string to type")
    key_combination: Optional[str] = Field(None, description="Key combination e.g. 'Enter', 'Ctrl+,'")


def execute_gui_action_step_preview(args: Dict[str, Any]) -> str:
    action = args.get("action_type", "CLICK")
    desc = args.get("description", "GUI step")
    return f"Execute virtual GUI action {action}: '{desc}'"


@registry.register(
    name="execute_gui_action_step",
    tier=1,
    description="Dispatches a single validated virtual GUI interaction step with human takeover checks.",
    args_schema=ExecuteGuiActionStepArgs,
    preview_fn=execute_gui_action_step_preview,
    can_remember_per_folder=False,
)
def handle_execute_gui_action_step(
    step_id: int,
    action_type: str,
    description: str,
    target_x: Optional[int] = None,
    target_y: Optional[int] = None,
    text_payload: Optional[str] = None,
    key_combination: Optional[str] = None,
) -> Dict[str, Any]:
    step = GuiActionStep(
        step_id=step_id,
        action_type=action_type,
        target_coordinates=(target_x, target_y) if target_x is not None and target_y is not None else None,
        text_payload=text_payload,
        key_combination=key_combination,
        description=description,
    )
    res = gui_step_executor.execute_step(step, dry_run=False)
    return res.model_dump()
