"""
Phenom Sovereign Unattended Overnight Mission Tools.
Provides tool endpoints for starting unattended missions in isolated git worktrees,
checking mission status, aborting active missions, and retrieving morning debrief summaries.

Strictly respects SAFETY.md:
- mission_start_unattended (Tier 1): Reversible change creating sandbox worktree, requires preview.
- mission_get_status (Tier 0): Read-only status query.
- mission_abort (Tier 1): Reversible change stopping active mission execution.
- mission_get_morning_debrief (Tier 0): Read-only debrief aggregation.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Optional

from services.backend.missions.morning_debrief import morning_debrief_synthesizer
from services.backend.missions.unattended_runner import unattended_mission_runner
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.missions import (
    MissionAbortArgs,
    MissionDebriefArgs,
    MissionExecutionPlan,
    MissionStartArgs,
    MissionStatus,
    MissionStatusArgs,
    generate_mission_id,
)

logger = logging.getLogger("phenom.mission_tools")


@registry.register(
    name="mission_start_unattended",
    tier=1,
    description="Starts an autonomous overnight refactoring or testing mission in an isolated git worktree sandbox. Reversible change.",
    args_schema=MissionStartArgs,
    preview_fn=lambda a: f"Start unattended sovereign mission '{a.get('title')}' in isolated git worktree (Reversible change)"
)
def mission_start_unattended(
    title: str,
    prompt: str,
    repo_path: Optional[str] = None,
    test_command: str = "pytest",
    max_iterations: int = 5,
    timeout_seconds: int = 120,
    async_execution: bool = True,
) -> Dict[str, Any]:
    """Launches an unattended overnight coding mission in an isolated git worktree."""
    if unattended_mission_runner.is_halted or getattr(guardian, "is_halted", False):
        raise PermissionError("Unattended mission runner operations are halted by Guardian.")

    root_path = os.path.abspath(repo_path or os.getcwd())
    mission_id = generate_mission_id()
    plan = MissionExecutionPlan(
        mission_id=mission_id,
        title=title,
        prompt=prompt,
        repo_path=root_path,
        test_command=test_command,
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
    )

    if async_execution:
        worker_thread = threading.Thread(
            target=unattended_mission_runner.run_mission,
            args=(plan,),
            daemon=True,
            name=f"mission-worker-{mission_id}",
        )
        worker_thread.start()
        return {
            "status": "started",
            "mission_id": mission_id,
            "branch_name": f"mission/{mission_id}",
            "title": title,
            "message": f"Mission '{title}' launched in background worktree sandbox.",
        }
    else:
        res = unattended_mission_runner.run_mission(plan)
        return {
            "status": res.status.value,
            "mission_id": mission_id,
            "result": res.model_dump(),
        }


@registry.register(
    name="mission_get_status",
    tier=0,
    description="Inspects the real-time execution status, iterations, or completion metrics of an unattended mission. Read-only.",
    args_schema=MissionStatusArgs,
    preview_fn=lambda a: f"Get status of unattended mission '{a.get('mission_id') or 'latest'}' (Read-only)"
)
def mission_get_status(mission_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves status and telemetry for an unattended mission."""
    if unattended_mission_runner.is_halted or getattr(guardian, "is_halted", False):
        raise PermissionError("Unattended mission runner operations are halted by Guardian.")

    if mission_id:
        result = unattended_mission_runner.get_mission(mission_id)
    else:
        result = unattended_mission_runner.get_latest_mission()

    if not result:
        return {
            "status": "not_found",
            "mission_id": mission_id,
            "message": "No matching mission found in active or completed registry.",
        }

    return {
        "status": "success",
        "mission_id": result.mission_id,
        "mission": result.model_dump(),
    }


@registry.register(
    name="mission_abort",
    tier=1,
    description="Aborts an active unattended mission, immediately terminating running test subprocesses. Reversible change.",
    args_schema=MissionAbortArgs,
    preview_fn=lambda a: f"Abort unattended sovereign mission '{a.get('mission_id')}' (Reversible change)"
)
def mission_abort(mission_id: str, reason: Optional[str] = "user_aborted") -> Dict[str, Any]:
    """Aborts a running or pending unattended mission."""
    success = unattended_mission_runner.abort_mission(mission_id, reason=reason or "user_aborted")
    return {
        "status": "aborted" if success else "not_running",
        "mission_id": mission_id,
        "success": success,
        "message": f"Mission '{mission_id}' {'successfully aborted' if success else 'was not active'}.",
    }


@registry.register(
    name="mission_get_morning_debrief",
    tier=0,
    description="Synthesizes overnight mission accomplishments, healed tests, diff statistics, and Jarvis morning brief. Read-only.",
    args_schema=MissionDebriefArgs,
    preview_fn=lambda a: f"Generate sovereign morning debrief for '{a.get('date_str') or 'today'}' (Read-only)"
)
def mission_get_morning_debrief(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Returns the morning debrief summary across nocturnal autonomous missions."""
    if unattended_mission_runner.is_halted or getattr(guardian, "is_halted", False):
        raise PermissionError("Unattended mission runner operations are halted by Guardian.")

    summary = morning_debrief_synthesizer.aggregate_debrief(date_str)
    return {
        "status": "success",
        "debrief": summary.model_dump(),
    }
