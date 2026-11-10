"""Safety-Wrapped Predictive Resource Governor Tools.

Registers tools with ToolRegistry for host resource telemetry queries, throttle state
configuration, and safety headroom overrides (Phase 24-04 GOV-03 / RES-02).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.governor.resource_governor import resource_governor
from services.backend.governor.adaptive_throttler import adaptive_throttler


# ==========================================
# 1. Get Host Resource Telemetry (Tier 0)
# ==========================================

class GetHostResourceTelemetryArgs(BaseModel):
    pass


def get_host_resource_telemetry_preview(args: Dict[str, Any]) -> str:
    return "Query host resource telemetry: CPU load, RAM utilization, GPU VRAM allocation, and thermal stress metrics."


@registry.register(
    name="get_host_resource_telemetry",
    tier=0,
    description="Samples continuous host resource telemetry, thermal metrics, and composite load ratings.",
    args_schema=GetHostResourceTelemetryArgs,
    preview_fn=get_host_resource_telemetry_preview,
    can_remember_per_folder=False,
)
def handle_get_host_resource_telemetry() -> Dict[str, Any]:
    telem = resource_governor.sample_telemetry()
    return telem.model_dump()


# ==========================================
# 2. Set Governor Throttle Mode (Tier 1)
# ==========================================

class SetGovernorThrottleModeArgs(BaseModel):
    throttle_mode: str = Field(
        ...,
        description="Target governor throttle mode: 'NORMAL', 'CONSERVE', or 'EMERGENCY_THROTTLE'",
    )


def set_governor_throttle_mode_preview(args: Dict[str, Any]) -> str:
    mode = args.get("throttle_mode", "NORMAL")
    return f"Set resource governor throttle mode to '{mode}' (adjusts subagent concurrency & indexing budget)."


@registry.register(
    name="set_governor_throttle_mode",
    tier=1,
    description="Manually sets or overrides the system resource throttling mode to manage host responsiveness.",
    args_schema=SetGovernorThrottleModeArgs,
    preview_fn=set_governor_throttle_mode_preview,
    can_remember_per_folder=False,
)
def handle_set_governor_throttle_mode(throttle_mode: str) -> Dict[str, Any]:
    config = adaptive_throttler.sync_throttle_state(force_state=throttle_mode, manual=True)
    return config.model_dump()


# ==========================================
# 3. Override Resource Headroom (Tier 1)
# ==========================================

class OverrideResourceHeadroomArgs(BaseModel):
    vram_headroom_mb: float = Field(
        ...,
        description="Minimum VRAM headroom buffer in megabytes to preserve for host OS display (e.g. 1024.0)",
    )


def override_resource_headroom_preview(args: Dict[str, Any]) -> str:
    hr = args.get("vram_headroom_mb", 1024.0)
    return f"Override GPU VRAM safety headroom bound to {hr} MB."


@registry.register(
    name="override_resource_headroom",
    tier=1,
    description="Applies custom GPU VRAM safety headroom thresholds to prevent local host out-of-memory stalls.",
    args_schema=OverrideResourceHeadroomArgs,
    preview_fn=override_resource_headroom_preview,
    can_remember_per_folder=False,
)
def handle_override_resource_headroom(vram_headroom_mb: float) -> Dict[str, Any]:
    config = adaptive_throttler.override_headroom(vram_headroom_mb=vram_headroom_mb)
    return config.model_dump()
