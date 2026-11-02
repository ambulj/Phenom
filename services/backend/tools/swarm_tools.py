"""
Phenom Swarm Management Tools
Provides tool endpoints for dispatching, monitoring, and aborting autonomous background workers.
Strictly respects SAFETY.md:
- get_swarm_status (Tier 0): Read-only status overview.
- dispatch_swarm_task (Tier 1): Requires interactive preview confirmation.
- abort_swarm_task (Tier 1): Requires confirmation to cancel active worker.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.automation.swarm_manager import swarm_manager


class GetSwarmStatusArgs(BaseModel):
    """Schema for get_swarm_status query (no arguments required)."""
    pass


class DispatchSwarmTaskArgs(BaseModel):
    task_type: str = Field(
        description="Type of worker to spawn: 'headless_browser' (background research/scraping) or 'subprocess_cli' (background scripts/commands)"
    )
    url: Optional[str] = Field(
        default=None,
        description="URL for headless_browser tasks"
    )
    command: Optional[str] = Field(
        default=None,
        description="Shell command for subprocess_cli tasks"
    )
    selectors: Optional[List[str]] = Field(
        default=None,
        description="Optional CSS selectors to extract from web page"
    )


class AbortSwarmTaskArgs(BaseModel):
    task_id: str = Field(
        description="ID of the active swarm task to abort"
    )


@registry.register(
    name="get_swarm_status",
    tier=0,
    description="Returns real-time status of active background autonomous workers, queue capacity, and task progress. Read-only.",
    args_schema=GetSwarmStatusArgs,
    preview_fn=lambda a: "Inspect active autonomous worker swarm status (Read-only)"
)
def get_swarm_status() -> Dict[str, Any]:
    """Returns status overview of all swarm workers."""
    return swarm_manager.get_swarm_status()


@registry.register(
    name="dispatch_swarm_task",
    tier=1,
    description="Dispatches an autonomous background worker (headless browser scraper or background CLI runner) without stealing user focus.",
    args_schema=DispatchSwarmTaskArgs,
    preview_fn=lambda a: f"Dispatch swarm task: type='{a.get('task_type')}', target='{a.get('url') or a.get('command')}'"
)
async def dispatch_swarm_task(
    task_type: str,
    url: Optional[str] = None,
    command: Optional[str] = None,
    selectors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Dispatches a task to the swarm manager."""
    payload: Dict[str, Any] = {}
    if url:
        payload["url"] = url
    if command:
        payload["command"] = command
    if selectors:
        payload["selectors"] = selectors

    return await swarm_manager.dispatch_task(task_type, payload)


@registry.register(
    name="abort_swarm_task",
    tier=1,
    description="Aborts an active autonomous swarm task immediately.",
    args_schema=AbortSwarmTaskArgs,
    preview_fn=lambda a: f"Abort active swarm task: id='{a.get('task_id')}'"
)
def abort_swarm_task(task_id: str) -> Dict[str, Any]:
    """Aborts a specific swarm worker task."""
    aborted = swarm_manager.abort_task(task_id)
    return {
        "status": "aborted" if aborted else "not_found",
        "task_id": task_id,
        "success": aborted
    }
