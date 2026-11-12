"""
Phenom Sovereign Unattended Overnight Missions Schemas.
Pydantic V2 models for mission execution plans, iterations, status, and ToolRegistry schemas.

Part of Phenom Milestone 9.0 Phase 4 (MIS-01, SAF-01, SAF-02).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


def current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_mission_id() -> str:
    return f"msn_{uuid.uuid4().hex[:8]}"


class MissionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    HEALING = "healing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    HALTED = "halted"


class MissionIteration(BaseModel):
    iteration_index: int = Field(..., description="1-based index of this healing iteration")
    test_command: str = Field(..., description="Test command executed")
    passed: bool = Field(..., description="True if test command passed with returncode 0")
    error_type: Optional[str] = Field(default=None, description="Error classification from TracebackParser")
    error_message: Optional[str] = Field(default=None, description="Extracted error summary or failure line")
    patch_diff: Optional[str] = Field(default=None, description="Unified git diff applied in this iteration")
    timestamp: str = Field(default_factory=current_iso_time, description="ISO timestamp of iteration")


class MissionExecutionPlan(BaseModel):
    mission_id: str = Field(default_factory=generate_mission_id, description="Unique mission identifier")
    title: str = Field(..., description="Descriptive title of mission objective")
    prompt: str = Field(..., description="Detailed instructions, bug description, or refactoring intent")
    repo_path: str = Field(..., description="Absolute path to root git repository")
    test_command: str = Field(default="pytest", description="Test/lint command to run inside sandbox worktree")
    max_iterations: int = Field(default=5, ge=1, le=20, description="Max healing iterations before exhaustion")
    timeout_seconds: int = Field(default=120, ge=1, le=600, description="Timeout in seconds per test run")



class MissionResult(BaseModel):
    mission_id: str = Field(..., description="Unique mission identifier")
    title: str = Field(..., description="Mission title")
    status: MissionStatus = Field(default=MissionStatus.PENDING, description="Final mission execution status")
    iterations: List[MissionIteration] = Field(default_factory=list, description="Record of each healing iteration")
    tests_passed: int = Field(default=0, description="Number of passing tests on final run")
    tests_fixed: int = Field(default=0, description="Number of tests healed during this mission")
    lines_added: int = Field(default=0, description="Total lines added in mission commits")
    lines_deleted: int = Field(default=0, description="Total lines deleted in mission commits")
    files_changed: List[str] = Field(default_factory=list, description="Relative paths of modified files")
    branch_name: str = Field(default="", description="Dedicated git branch created for this mission")
    worktree_path: str = Field(default="", description="Sandbox worktree path")
    started_at: str = Field(default_factory=current_iso_time, description="Start timestamp")
    completed_at: Optional[str] = Field(default=None, description="Completion or termination timestamp")
    diagnostic_log: str = Field(default="", description="Summary log or diagnostic output on failure/exhaustion")


# ==========================================
# ToolRegistry Argument Schemas (SAF-01)
# ==========================================

class MissionStartArgs(BaseModel):
    title: str = Field(..., description="Objective or title of the overnight mission")
    prompt: str = Field(..., description="Detailed instructions or refactoring prompt")
    repo_path: Optional[str] = Field(default=None, description="Repository root; defaults to project root")
    test_command: str = Field(default="pytest", description="Command to verify tests in sandbox worktree")
    max_iterations: int = Field(default=5, ge=1, le=20, description="Maximum self-healing iterations")
    timeout_seconds: int = Field(default=120, ge=1, le=600, description="Subprocess timeout per test run")



class MissionStatusArgs(BaseModel):
    mission_id: Optional[str] = Field(default=None, description="Optional mission ID; defaults to latest")


class MissionAbortArgs(BaseModel):
    mission_id: str = Field(..., description="ID of the mission to abort")
    reason: Optional[str] = Field(default="user_aborted", description="Reason for abortion")


class MissionDebriefArgs(BaseModel):
    date_str: Optional[str] = Field(default=None, description="Date in YYYY-MM-DD format; defaults to today")


class MorningDebriefSummary(BaseModel):
    date: str = Field(..., description="Debrief date YYYY-MM-DD")
    total_missions: int = Field(default=0, description="Total overnight missions executed")
    successful_missions: int = Field(default=0, description="Missions successfully completed")
    failed_missions: int = Field(default=0, description="Missions that failed or exhausted iterations")
    tests_fixed: int = Field(default=0, description="Aggregated tests healed across all missions")
    lines_added: int = Field(default=0, description="Total lines added")
    lines_deleted: int = Field(default=0, description="Total lines deleted")
    touched_files: List[str] = Field(default_factory=list, description="List of files touched")
    missions: List[MissionResult] = Field(default_factory=list, description="Individual mission records")
    executive_summary: str = Field(default="", description="Witty Jarvis-style morning briefing text")
