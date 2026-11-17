"""
Phenom Neural Perception & Active Desktop Reflex Tools (Milestone 51 Phase 1).

Registers:
- inspect_reflex_sentinel_state (Tier 0)
- sample_desktop_reflex_frame (Tier 0)
- simulate_reflex_event (Tier 0)
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.reflex import visual_sentinel, notification_sentinel
from services.backend.schemas.reflex_events import (
    ReflexEvent,
    ReflexEventType,
    ReflexSeverity,
    ToastNotificationDetails,
)


class InspectReflexSentinelStateArgs(BaseModel):
    include_recent: bool = Field(default=True, description="Whether to include recent detected events")


class SampleDesktopReflexFrameArgs(BaseModel):
    extracted_text: str = Field(default="", description="Visible or OCR text from foreground window region")
    window_title: Optional[str] = Field(default="", description="Foreground window title")
    process_name: Optional[str] = Field(default="", description="Foreground executable name (e.g. WindowsTerminal.exe)")
    force_process: bool = Field(default=True, description="Force pattern parsing even if visual hash is static")


class SimulateReflexEventArgs(BaseModel):
    event_type: str = Field(description="ReflexEventType name (e.g. TERMINAL_COMPLETED, BUILD_FAILED, TOAST_NOTIFICATION)")
    severity: Optional[str] = Field(default="INFO", description="Severity: INFO, SUCCESS, WARNING, CRITICAL")
    title: Optional[str] = Field(default="", description="Event title or window heading")
    message: Optional[str] = Field(default="", description="Event message or diagnostic snippet")
    source: Optional[str] = Field(default="simulated", description="Event source origin")


@registry.register(
    name="inspect_reflex_sentinel_state",
    tier=0,
    description="Inspects active low-latency reflex sentinel status, event counts, latency, and CPU metrics.",
    args_schema=InspectReflexSentinelStateArgs,
    preview_fn=lambda a: "Inspect active desktop reflex sentinel status and CPU overhead"
)
def inspect_reflex_sentinel_state(include_recent: bool = True) -> Dict[str, Any]:
    status = visual_sentinel.get_status()
    dump = status.model_dump()
    if not include_recent:
        dump["recent_events"] = []
    return dump


@registry.register(
    name="sample_desktop_reflex_frame",
    tier=0,
    description="Samples a foreground window region, computes perceptual diff hash, and parses visual cues.",
    args_schema=SampleDesktopReflexFrameArgs,
    preview_fn=lambda a: f"Sample desktop reflex frame for '{a.get('window_title') or 'foreground window'}'"
)
def sample_desktop_reflex_frame(
    extracted_text: str = "",
    window_title: Optional[str] = "",
    process_name: Optional[str] = "",
    force_process: bool = True
) -> Dict[str, Any]:
    event, elapsed_ms = visual_sentinel.process_frame(
        image_or_buffer=extracted_text,
        extracted_text=extracted_text,
        window_title=window_title or "",
        process_name=process_name or "",
        force_process=force_process,
    )
    return {
        "event_detected": event is not None,
        "elapsed_ms": round(elapsed_ms, 2),
        "event": event.model_dump() if event else None,
    }


@registry.register(
    name="simulate_reflex_event",
    tier=0,
    description="Simulates a desktop reflex event (toast alert or terminal completion) for automated pipelines.",
    args_schema=SimulateReflexEventArgs,
    preview_fn=lambda a: f"Simulate reflex event '{a.get('event_type')}' ({a.get('severity')})"
)
def simulate_reflex_event(
    event_type: str,
    severity: Optional[str] = "INFO",
    title: Optional[str] = "",
    message: Optional[str] = "",
    source: Optional[str] = "simulated"
) -> Dict[str, Any]:
    try:
        ev_type = ReflexEventType(event_type)
    except ValueError:
        ev_type = ReflexEventType.UNKNOWN

    try:
        ev_sev = ReflexSeverity(severity or "INFO")
    except ValueError:
        ev_sev = ReflexSeverity.INFO

    if ev_type == ReflexEventType.TOAST_NOTIFICATION:
        event = notification_sentinel.process_toast(
            app_name=source or "System",
            title=title or "Notification",
            message=message or "",
            urgency="normal"
        )
        if event is None:
            # Fallback if debounced
            event = ReflexEvent(
                event_type=ev_type,
                severity=ev_sev,
                source=source or "simulated",
                toast_details=ToastNotificationDetails(
                    app_name=source or "System",
                    title=title or "Notification",
                    message=message or "",
                )
            )
    else:
        event = ReflexEvent(
            event_type=ev_type,
            severity=ev_sev,
            source=source or "simulated",
            metadata={"title": title, "message": message}
        )

    return {
        "success": True,
        "event": event.model_dump()
    }
