"""
Phenom Proactive Scheduler & Event Daemon Tools (SAF-01 & SAF-02).
Registers Milestone 19 Phase 3 tools in ToolRegistry:
1. schedule_proactive_job (Tier 1)
2. list_scheduled_jobs (Tier 0)
3. cancel_scheduled_job (Tier 1)
4. trigger_morning_briefing (Tier 0)
5. get_scheduler_daemon_status (Tier 0)
All tools enforce strict Pydantic schemas, preview generation, and Guardian SLA integration.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.scheduler.event_daemon import event_daemon
from services.backend.scheduler.morning_briefing import morning_briefing_service


class ScheduleProactiveJobArgs(BaseModel):
    name: str = Field(..., description="Human-readable title for the scheduled task")
    interval_seconds: float = Field(..., ge=10.0, description="Recurrence interval in seconds (minimum 10s)")
    job_type: str = Field(default="interval", description="Job type: 'interval', 'cron', or 'reminder'")
    target_time_str: Optional[str] = Field(default=None, description="Optional target time string (e.g. '08:30')")


class ListScheduledJobsArgs(BaseModel):
    pass


class CancelScheduledJobArgs(BaseModel):
    job_id: str = Field(..., description="Unique job ID to cancel")


class TriggerMorningBriefingArgs(BaseModel):
    include_weather: bool = Field(default=True, description="Whether to include weather forecast")
    include_calendar: bool = Field(default=True, description="Whether to include agenda meetings")


class GetSchedulerDaemonStatusArgs(BaseModel):
    pass


@registry.register(
    name="schedule_proactive_job",
    tier=1,
    description="Registers a new recurring job or timer with the background event daemon.",
    args_schema=ScheduleProactiveJobArgs,
    preview_fn=lambda a: f"Schedule task '{getattr(a, 'name', 'task')}' every {getattr(a, 'interval_seconds', 0)}s"
)
async def schedule_proactive_job(
    name: str,
    interval_seconds: float,
    job_type: str = "interval",
    target_time_str: Optional[str] = None
) -> Dict[str, Any]:
    """Registers scheduled task."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    import uuid
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    # Dummy no-op callback for external user jobs
    async def _dummy_task():
        return {"status": "executed", "name": name}

    job = event_daemon.register_job(
        job_id=job_id,
        name=name,
        interval_seconds=interval_seconds,
        callback=_dummy_task,
        job_type=job_type,
        target_time_str=target_time_str
    )

    return {
        "status": "scheduled",
        "job_id": job.job_id,
        "name": job.name,
        "interval_seconds": job.interval_seconds,
        "next_run": job.next_run
    }


@registry.register(
    name="list_scheduled_jobs",
    tier=0,
    description="Lists all active scheduled daemon tasks and upcoming run times. Read-only.",
    args_schema=ListScheduledJobsArgs,
    preview_fn=lambda a: "Inspect active background daemon tasks (Read-only)"
)
async def list_scheduled_jobs() -> List[Dict[str, Any]]:
    """Returns list of active scheduled tasks."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    return event_daemon.list_jobs()


@registry.register(
    name="cancel_scheduled_job",
    tier=1,
    description="Cancels an active scheduled task by job ID.",
    args_schema=CancelScheduledJobArgs,
    preview_fn=lambda a: f"Cancel scheduled daemon task '{getattr(a, 'job_id', '')}'"
)
async def cancel_scheduled_job(job_id: str) -> Dict[str, Any]:
    """Cancels task from event daemon."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    success = event_daemon.cancel_job(job_id)
    return {
        "status": "cancelled" if success else "not_found",
        "job_id": job_id
    }


@registry.register(
    name="trigger_morning_briefing",
    tier=0,
    description="Generates executive morning briefing, spoken voice prompt, and Obsidian daily note.",
    args_schema=TriggerMorningBriefingArgs,
    preview_fn=lambda a: "Generate 08:30 Morning Briefing & Sync Obsidian Daily Note"
)
async def trigger_morning_briefing(
    include_weather: bool = True,
    include_calendar: bool = True
) -> Dict[str, Any]:
    """Generates morning briefing immediately."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    return morning_briefing_service.generate_briefing(
        include_weather=include_weather,
        include_calendar=include_calendar
    )


@registry.register(
    name="get_scheduler_daemon_status",
    tier=0,
    description="Returns scheduler daemon loop status, watched folders, and recent trigger history.",
    args_schema=GetSchedulerDaemonStatusArgs,
    preview_fn=lambda a: "Inspect scheduler daemon health and activity (Read-only)"
)
async def get_scheduler_daemon_status() -> Dict[str, Any]:
    """Returns scheduler daemon status."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active.")

    return {
        "is_running": event_daemon.is_running,
        "is_paused": event_daemon.is_paused,
        "active_jobs_count": len(event_daemon._jobs),
        "watched_directories": list(event_daemon._watch_dirs),
        "recent_triggers": event_daemon.trigger_history[-5:]
    }
