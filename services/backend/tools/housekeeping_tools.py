"""Phenom Autonomous Background Workers & Housekeeping Safety Tools.

Provides tool endpoints for workspace housekeeping, pre-meeting topic research,
and Obsidian daily note synchronization.
Strictly respects SAFETY.md:
- get_housekeeper_status (Tier 0): Read-only status and metrics.
- run_workspace_housekeeping (Tier 1): Requires interactive preview confirmation.
- dispatch_topic_research (Tier 1): Requires interactive preview confirmation.
- sync_obsidian_daily_note (Tier 1): Requires interactive preview confirmation.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.automation.topic_researcher import topic_researcher
from services.backend.automation.workspace_housekeeper import workspace_housekeeper
from services.backend.integrations.google_workspace import google_workspace
from services.backend.memory.daily_copilot import daily_copilot
from services.backend.safety.registry import registry


class GetHousekeeperStatusArgs(BaseModel):
    """Schema for get_housekeeper_status (no arguments required)."""
    pass


class RunWorkspaceHousekeepingArgs(BaseModel):
    directory: Optional[str] = Field(
        default=None,
        description="Target workspace/downloads directory to organize (defaults to user Downloads)",
    )


class DispatchTopicResearchArgs(BaseModel):
    topic: str = Field(..., description="Topic or meeting title to research")
    attendees: Optional[List[str]] = Field(default=None, description="List of participant names or emails")
    meeting_time: Optional[str] = Field(default=None, description="Meeting time or scheduled date/time string")
    reference_urls: Optional[List[str]] = Field(default=None, description="Optional reference documentation URLs")


class SyncObsidianDailyNoteArgs(BaseModel):
    date_str: Optional[str] = Field(
        default=None,
        description="Target date in YYYY-MM-DD format (defaults to today)",
    )


@registry.register(
    name="get_housekeeper_status",
    tier=0,
    description="Returns current status, idle detection state, and metrics for the workspace housekeeper. Read-only.",
    args_schema=GetHousekeeperStatusArgs,
    preview_fn=lambda a: "Inspect workspace housekeeper status and idle metrics (Read-only)",
)
def get_housekeeper_status(**kwargs) -> Dict[str, Any]:
    """Inspects the current state of workspace housekeeping."""
    return {
        "status": "ok",
        "housekeeper": workspace_housekeeper.get_status(),
    }


@registry.register(
    name="run_workspace_housekeeping",
    tier=1,
    description="Organizes unfiled downloads into categorized subfolders (Documents, Images, Archives, Code) and moves clutter to Windows Recycle Bin (Rule 7).",
    args_schema=RunWorkspaceHousekeepingArgs,
    preview_fn=lambda a: f"Organize workspace in '{a.get('directory') or 'Downloads'}' (Rule 7: Clutter to Recycle Bin)",
)
async def run_workspace_housekeeping(directory: Optional[str] = None) -> Dict[str, Any]:
    """Executes workspace housekeeping pass with user confirmation."""
    return await workspace_housekeeper.organize_workspace(
        directory=directory,
        enforce_idle_check=False,  # Manual invocation bypasses idle check
    )


@registry.register(
    name="dispatch_topic_research",
    tier=1,
    description="Dispatches autonomous background worker swarm to research an upcoming meeting topic and save a structured brief to the Obsidian vault.",
    args_schema=DispatchTopicResearchArgs,
    preview_fn=lambda a: f"Dispatch topic research worker for '{a.get('topic')}' (Generates Obsidian meeting brief)",
)
async def dispatch_topic_research(
    topic: str,
    attendees: Optional[List[str]] = None,
    meeting_time: Optional[str] = None,
    reference_urls: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Dispatches background headless research worker."""
    return await topic_researcher.research_topic(
        topic=topic,
        attendees=attendees,
        meeting_time=meeting_time,
        use_headless_browser=bool(reference_urls),
        reference_urls=reference_urls,
    )


@registry.register(
    name="sync_obsidian_daily_note",
    tier=1,
    description="Scaffolds or updates today's Obsidian Daily Note (vault/Daily Notes/YYYY-MM-DD.md) with calendar timeblocks and action items without overwriting user notes.",
    args_schema=SyncObsidianDailyNoteArgs,
    preview_fn=lambda a: f"Sync Obsidian Daily Note with calendar schedule for '{a.get('date_str') or 'today'}'",
)
def sync_obsidian_daily_note(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Synchronizes daily note with current calendar schedule and triage records."""
    # Ensure note exists
    target_path = daily_copilot.ensure_daily_note(date_str)

    # Ingest upcoming calendar events
    events: List[Dict[str, Any]] = []
    try:
        events = google_workspace.list_events(max_results=10)
    except Exception as exc:
        logger.debug("Could not fetch calendar events for daily sync: %s", exc)

    sync_res = daily_copilot.sync_calendar_timeblocks(events, date_str=date_str)
    return {
        "status": "ok",
        "file_path": target_path,
        "sync_result": sync_res,
    }
