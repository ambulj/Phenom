"""
Phenom Vision & Resource Governor Tools (SAF-01)
Registers Phase 1 tools in ToolRegistry with strict Pydantic argument schemas,
risk tiering (Tier 0 and Tier 1), and preview functions per SAFETY.md.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.system.resource_governor import resource_governor
from services.backend.vision.ambient_copilot import ambient_copilot


class VisionGetAmbientContextArgs(BaseModel):
    refresh_if_stale: bool = Field(
        default=False,
        description="Whether to trigger an immediate frame capture cycle if copilot is idle"
    )


class VisionConfigureAmbientCopilotArgs(BaseModel):
    enabled: Optional[bool] = Field(
        default=None,
        description="Enable or disable continuous ambient vision loop"
    )
    interval_seconds: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=60.0,
        description="Loop sampling interval in seconds (3-5s recommended)"
    )
    delta_threshold: Optional[float] = Field(
        default=None,
        ge=0.001,
        le=1.0,
        description="Perceptual change threshold (default 0.02 = 2% change)"
    )
    add_blacklists: Optional[List[str]] = Field(
        default=None,
        description="Additional window title / process regex patterns to blacklist"
    )


class GovernorGetResourceStatusArgs(BaseModel):
    poll_now: bool = Field(
        default=True,
        description="Whether to poll latest live hardware metrics before returning"
    )


@registry.register(
    name="vision_get_ambient_screen_context",
    tier=0,
    description="Returns the latest in-memory ambient screen context including active window, visual scene description, and detected errors. Read-only.",
    args_schema=VisionGetAmbientContextArgs,
    preview_fn=lambda a: "Inspect current ambient screen vision context (Read-only)"
)
async def vision_get_ambient_screen_context(refresh_if_stale: bool = False) -> Dict[str, Any]:
    """Retrieves current ambient screen context captured in RAM."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active. Operation halted.")

    if refresh_if_stale and not ambient_copilot.is_suspended and not ambient_copilot.is_halted:
        try:
            ctx = await ambient_copilot.step()
        except Exception:
            ctx = ambient_copilot.get_context()
    else:
        ctx = ambient_copilot.get_context()

    return {
        "status": "success",
        "context": ctx.model_dump()
    }


@registry.register(
    name="vision_configure_ambient_copilot",
    tier=1,
    description="Configures ambient vision co-pilot runtime parameters (interval, enabled, custom blacklists).",
    args_schema=VisionConfigureAmbientCopilotArgs,
    preview_fn=lambda a: f"Configure ambient vision copilot settings: enabled={a.get('enabled')}, interval={a.get('interval_seconds')}s"
)
async def vision_configure_ambient_copilot(
    enabled: Optional[bool] = None,
    interval_seconds: Optional[float] = None,
    delta_threshold: Optional[float] = None,
    add_blacklists: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Updates ambient vision copilot configuration."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active. Operation halted.")

    ambient_copilot.configure(
        is_enabled=enabled,
        interval_seconds=interval_seconds,
        delta_threshold=delta_threshold,
        custom_blacklists=add_blacklists,
    )

    return {
        "status": "success",
        "config": ambient_copilot.config.model_dump()
    }


@registry.register(
    name="governor_get_resource_status",
    tier=0,
    description="Returns current GPU, VRAM, CPU utilization, 3D gaming status, and background task throttling state from the Adaptive Resource Governor. Read-only.",
    args_schema=GovernorGetResourceStatusArgs,
    preview_fn=lambda a: "Inspect GPU and system resource governor status (Read-only)"
)
async def governor_get_resource_status(poll_now: bool = True) -> Dict[str, Any]:
    """Retrieves current system resource and gaming governor state."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active. Operation halted.")

    if poll_now and not resource_governor.is_halted:
        state = resource_governor.poll_metrics()
    else:
        state = resource_governor.get_state()

    return {
        "status": "success",
        "governor_state": state.model_dump()
    }
