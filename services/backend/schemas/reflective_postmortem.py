"""Pydantic schemas for Self-Reflective Post-Mortem & Proactive Workflow Synthesis (Milestone 49 Phase 2).

Covers:
- Failure trace capture, root-cause classification, and deterministic error signatures (REFL-01).
- Executable programmatic heuristics and planner prompt guidelines (REFL-02).
- Proactive routine anticipation, workspace pre-staging, and concise spoken morning briefings (REFL-03).
"""

from __future__ import annotations

from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class FailureCategory(str, Enum):
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    SAFETY_RESTRICTION = "SAFETY_RESTRICTION"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class FailureTrace(BaseModel):
    """Raw execution failure context captured from tool/subagent execution."""
    task_id: str = Field(description="Unique task or mission node ID")
    tool_name: str = Field(description="Name of tool or subagent role that failed")
    input_arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the failing invocation")
    exception_type: str = Field(description="Exception class name (e.g. FileNotFoundError, TimeoutError)")
    error_message: str = Field(description="Sanitized exception message string")
    call_stack: List[str] = Field(default_factory=list, description="High-level call frames")
    timestamp: float = Field(default_factory=time.time, description="Failure epoch timestamp")


class PostMortemAnalysis(BaseModel):
    """Structured diagnostic evaluation of a failure trace."""
    analysis_id: str = Field(description="Unique post-mortem identifier")
    task_id: str = Field(description="Associated task ID")
    tool_name: str = Field(description="Failing tool name")
    category: FailureCategory = Field(description="Classified failure taxonomy")
    failure_signature: str = Field(description="Deterministic signature string for matching future occurrences")
    root_cause_summary: str = Field(description="Human-readable root cause explanation")
    remediation_strategy: str = Field(description="Recommended prevention or compensatory policy")
    proposed_heuristic: Optional[Dict[str, Any]] = Field(default=None, description="Proposed heuristic schema dictionary")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    timestamp: float = Field(default_factory=time.time, description="Analysis timestamp")


class HeuristicRule(BaseModel):
    """An executable constraint and prompt guideline compiled to prevent recurring failures."""
    rule_id: str = Field(description="Unique heuristic rule identifier")
    tool_name: str = Field(description="Associated tool name or '*' for global")
    failure_signature: str = Field(description="Signature regex or identifier this rule prevents")
    description: str = Field(description="Explanation of the heuristic constraint")
    constraint_expression: str = Field(description="Executable Python boolean expression or assertion snippet")
    planner_guideline: str = Field(description="Natural language instruction for DAG planner context injection")
    is_active: bool = Field(default=True, description="Whether this rule is actively enforced")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Heuristic reliability confidence")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")


class ProactiveRoutine(BaseModel):
    """An anticipated recurring workflow pattern mined from temporal episodic history."""
    routine_id: str = Field(description="Unique routine identifier")
    title: str = Field(description="Descriptive routine title")
    target_time_window: str = Field(description="Time of day window (e.g. '08:00-10:00')")
    frequency_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Historical recurrence frequency")
    anticipated_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Ordered action steps")
    rationale: str = Field(default="", description="Reasoning for anticipation")


class WorkspacePreStagePlan(BaseModel):
    """Actionable blueprint to stage desktop applications, files, and environment for user routines."""
    plan_id: str = Field(description="Unique pre-stage plan identifier")
    target_workspace_name: str = Field(description="Project or activity workspace label")
    apps_to_launch: List[Dict[str, Any]] = Field(default_factory=list, description="Apps and flags to start")
    directories_to_open: List[str] = Field(default_factory=list, description="File explorer paths to open")
    env_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables to export")
    spoken_announcement: str = Field(default="", description="Concise verbal update (< 25 words)")


class SpokenMorningBriefing(BaseModel):
    """Crisp spoken morning update synthesizing priorities and pre-staged workflows."""
    date_str: str = Field(description="Date formatted string (YYYY-MM-DD)")
    briefing_text: str = Field(description="Acoustic voice script strictly <= 60 words")
    word_count: int = Field(default=0, description="Computed word count")
    priorities: List[str] = Field(default_factory=list, description="Top 1-3 focus items")
    suggested_routine_ids: List[str] = Field(default_factory=list, description="Referenced proactive routines")

    @field_validator("briefing_text")
    def validate_briefing_length(cls, v: str) -> str:
        words = len(v.strip().split())
        if words > 60:
            raise ValueError(f"Spoken morning briefing length ({words} words) exceeds strict 60-word acoustic limit.")
        return v
