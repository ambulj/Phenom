"""
Phenom Autonomous Goal Planner & Checkpoint Engine
Decomposes high-level natural language user goals into structured, acyclic step plans
combining desktop GUI controls and Playwright browser actions.
Enforces:
1. Pre-flight safety validation: permanently prohibits payment, checkout, or destructive steps (Rule 8).
2. Structured TaskCheckpoint serialization for seamless resumption after interruption.
3. Maximum execution bounds (max 20 steps, max 300s timeout).
"""

import time
import json
import re
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Prohibited action patterns (Rule 8 and Tier 3 safety invariants)
PROHIBITED_ACTION_PATTERNS = [
    re.compile(r"\b(pay|payment|place\s*order|complete\s*checkout|buy\s*now|checkout)\b", re.IGNORECASE),
    re.compile(r"\b(credit\s*card|debit\s*card|cvv|otp|pin|password|bank\s*transfer)\b", re.IGNORECASE),
    re.compile(r"\b(permanent(ly)?\s*delete|wipe\s*disk|format\s*drive|rm\s*-rf|shred)\b", re.IGNORECASE),
]


class PlanStep(BaseModel):
    step_number: int = Field(..., description="1-indexed sequence order of the step")
    description: str = Field(..., description="Human-readable description of the step action")
    action_type: str = Field(..., description="Action primitive (e.g. browser_navigate, browser_click, mouse_click, type_text)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters for the action")
    tier: int = Field(default=2, description="Safety risk tier (0 or 2; Tier 3 prohibited)")
    status: str = Field(default="pending", description="Step execution status: pending, running, completed, failed, skipped")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Output or observation produced by the step")


class GoalPlan(BaseModel):
    task_id: str = Field(..., description="Unique UUID for this autonomous task")
    goal_description: str = Field(..., description="Original user prompt or high-level goal")
    steps: List[PlanStep] = Field(default_factory=list, description="Ordered sequence of execution steps")
    created_at: float = Field(default_factory=time.time, description="Creation epoch timestamp")
    total_steps: int = Field(default=0, description="Total count of steps in plan")
    estimated_duration_sec: float = Field(default=30.0, description="Estimated total execution duration in seconds")


class TaskCheckpoint(BaseModel):
    task_id: str = Field(..., description="Task identifier")
    current_step_index: int = Field(default=0, description="0-indexed pointer to currently executing step")
    state: str = Field(default="running", description="Checkpoint status: running, paused_takeover, completed, aborted, failed")
    step_results: List[Dict[str, Any]] = Field(default_factory=list, description="Cumulative results from completed steps")
    timestamp: float = Field(default_factory=time.time, description="Checkpoint save epoch timestamp")


class AutonomousGoalPlanner:
    """
    Decomposes natural language goals into validated, multi-step execution plans.
    """

    def __init__(self, max_steps: int = 20, max_timeout_sec: float = 300.0):
        self.max_steps = max_steps
        self.max_timeout_sec = max_timeout_sec

    def plan_goal(self, goal: str) -> GoalPlan:
        """
        Plans a multi-step workflow from a high-level goal.
        Enforces pre-flight safety checks against payment and destructive commands.
        """
        goal_clean = goal.strip()
        if not goal_clean:
            raise ValueError("Goal description cannot be empty.")

        # 1. Pre-Flight Safety Verification (Rule 8 & Tier 3 prohibitions)
        for pattern in PROHIBITED_ACTION_PATTERNS:
            if pattern.search(goal_clean):
                raise PermissionError(
                    f"Execution of payment, checkout, or destructive operations is strictly prohibited by SAFETY.md (matched: '{pattern.pattern}')."
                )

        task_id = f"task-{uuid.uuid4().hex[:8]}"
        steps = self._decompose_steps(goal_clean)

        if len(steps) > self.max_steps:
            raise ValueError(f"Generated plan exceeds maximum step limit ({len(steps)} > {self.max_steps}).")

        # Verify each step tier
        for s in steps:
            if s.tier >= 3:
                raise PermissionError(f"Step {s.step_number} is Tier {s.tier}, which cannot be executed autonomously.")

        return GoalPlan(
            task_id=task_id,
            goal_description=goal_clean,
            steps=steps,
            total_steps=len(steps),
            estimated_duration_sec=min(float(len(steps) * 4.0), self.max_timeout_sec)
        )

    def _decompose_steps(self, goal: str) -> List[PlanStep]:
        """
        Heuristic decomposition engine mapping user goals into browser & OS steps.
        """
        steps: List[PlanStep] = []
        lower = goal.lower()

        # Pattern A: GitHub Search / Research
        if "github" in lower:
            steps.append(PlanStep(
                step_number=1,
                description="Navigate to GitHub Trending",
                action_type="browser_navigate",
                params={"url": "https://github.com/trending"},
                tier=2
            ))
            steps.append(PlanStep(
                step_number=2,
                description="Wait for trending repository list to render",
                action_type="wait_element",
                params={"selector": "article.Box-row", "timeout_ms": 5000},
                tier=0
            ))
            steps.append(PlanStep(
                step_number=3,
                description="Extract top repository names and descriptions",
                action_type="extract_text",
                params={"selector": "article.Box-row h2 a"},
                tier=0
            ))
            steps.append(PlanStep(
                step_number=4,
                description="Save research summary to project vault",
                action_type="save_result",
                params={"destination": "vault/Research/github_trending.md"},
                tier=2
            ))
            return steps

        # Pattern B: YouTube Video Search & Playback
        if "youtube" in lower:
            query_match = re.search(r"(?:search|play|find)\s+(?:for\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+on\s+youtube|$)", goal, re.IGNORECASE)
            search_query = query_match.group(1).strip() if query_match else "lo-fi chill beats"
            steps.append(PlanStep(
                step_number=1,
                description="Navigate to YouTube",
                action_type="browser_navigate",
                params={"url": f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"},
                tier=2
            ))
            steps.append(PlanStep(
                step_number=2,
                description="Wait for search results to load",
                action_type="wait_element",
                params={"selector": "ytd-video-renderer", "timeout_ms": 6000},
                tier=0
            ))
            steps.append(PlanStep(
                step_number=3,
                description="Click top video result",
                action_type="browser_click",
                params={"selector": "ytd-video-renderer a#video-title"},
                tier=2
            ))
            return steps

        # Pattern C: Generic Web Research
        if any(kw in lower for kw in ["search", "find", "lookup", "research", "browse"]):
            steps.append(PlanStep(
                step_number=1,
                description="Open browser and navigate to search engine",
                action_type="browser_navigate",
                params={"url": "https://duckduckgo.com"},
                tier=2
            ))
            steps.append(PlanStep(
                step_number=2,
                description=f"Type search query: '{goal}'",
                action_type="browser_type",
                params={"selector": "input[name='q']", "text": goal},
                tier=2
            ))
            steps.append(PlanStep(
                step_number=3,
                description="Extract visible search results",
                action_type="extract_text",
                params={"selector": "article"},
                tier=0
            ))
            return steps

        # Pattern D: Desktop Application Launch & Interaction
        steps.append(PlanStep(
            step_number=1,
            description="Inspect active desktop screen for targets",
            action_type="inspect_screen",
            params={"query": goal},
            tier=0
        ))
        steps.append(PlanStep(
            step_number=2,
            description="Locate target UI elements",
            action_type="find_on_screen",
            params={"element_name": goal.split()[-1] if goal.split() else "window"},
            tier=0
        ))
        steps.append(PlanStep(
            step_number=3,
            description="Perform primary user action",
            action_type="mouse_click",
            params={"x": 500, "y": 500},
            tier=2
        ))
        return steps

    def serialize_checkpoint(self, checkpoint: TaskCheckpoint) -> str:
        """Serializes a TaskCheckpoint to JSON."""
        return checkpoint.model_dump_json(indent=2)

    def deserialize_checkpoint(self, json_data: str) -> TaskCheckpoint:
        """Restores a TaskCheckpoint from JSON."""
        data = json.loads(json_data)
        return TaskCheckpoint(**data)


goal_planner = AutonomousGoalPlanner()
