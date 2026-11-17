"""
Phenom Observable Motion & Dual Handoff Tool Registrations (WKF-05)
Registers:
- drive_observable_motion (Tier 1)
- generate_dual_handoff_briefing (Tier 0)
"""

from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.desktop.observable_motion_driver import observable_motion_driver
from services.backend.workflows.dual_handoff_briefing import dual_handoff_generator


class DriveObservableMotionArgs(BaseModel):
    start_x: int = Field(description="Starting cursor X coordinate")
    start_y: int = Field(description="Starting cursor Y coordinate")
    target_x: int = Field(description="Target destination X coordinate")
    target_y: int = Field(description="Target destination Y coordinate")
    target_name: str = Field(description="Human-readable label of target element")
    bbox_x: int = Field(description="Target bounding box X")
    bbox_y: int = Field(description="Target bounding box Y")
    bbox_w: int = Field(description="Target bounding box width")
    bbox_h: int = Field(description="Target bounding box height")


class GenerateDualHandoffBriefingArgs(BaseModel):
    dag_id: str = Field(description="Completed workflow DAG ID")
    goal: str = Field(description="Workflow objective or prompt")
    step_count: int = Field(description="Total steps executed")
    success: bool = Field(description="Whether workflow completed without divergence")
    duration_s: float = Field(description="Execution duration in seconds")
    screenshots_attached: int = Field(default=1, description="Number of step screenshots captured")


@registry.register(
    name="drive_observable_motion",
    tier=1,
    description="Drives observable cursor glide using cubic Bezier curves at 1.2x human speed with target halos and takeover hooks.",
    args_schema=DriveObservableMotionArgs,
    preview_fn=lambda a: f"Drive observable cursor glide to '{a.get('target_name')}' at ({a.get('target_x')}, {a.get('target_y')}) at 1.2x speed"
)
def drive_observable_motion(
    start_x: int,
    start_y: int,
    target_x: int,
    target_y: int,
    target_name: str,
    bbox_x: int,
    bbox_y: int,
    bbox_w: int,
    bbox_h: int
) -> Dict[str, Any]:
    res = observable_motion_driver.plan_and_drive_motion(
        start_pos=(start_x, start_y),
        target_pos=(target_x, target_y),
        target_name=target_name,
        bounding_box=(bbox_x, bbox_y, bbox_w, bbox_h)
    )
    return res.model_dump()


@registry.register(
    name="generate_dual_handoff_briefing",
    tier=0,
    description="Synthesizes witty Jarvis spoken debrief (<25 words) and rich Telegram companion card upon macro completion.",
    args_schema=GenerateDualHandoffBriefingArgs,
    preview_fn=lambda a: f"Generate dual handoff briefing for workflow '{a.get('dag_id')}'"
)
def generate_dual_handoff_briefing(
    dag_id: str,
    goal: str,
    step_count: int,
    success: bool,
    duration_s: float,
    screenshots_attached: int = 1
) -> Dict[str, Any]:
    briefing = dual_handoff_generator.generate_briefing(
        dag_id=dag_id,
        goal=goal,
        step_count=step_count,
        success=success,
        duration_s=duration_s,
        screenshots_attached=screenshots_attached
    )
    return briefing.model_dump()
