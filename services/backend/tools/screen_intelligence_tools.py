"""Screen Intelligence & Visual Task Tracker Tools for Phenom (Milestone 30 Phase 1).

Registers 5 vision and OCR tools in ToolRegistry:
1. capture_screen_intelligence_context (Tier 0)
2. extract_screen_region_ocr (Tier 0)
3. diagnose_on_screen_errors (Tier 0)
4. set_screen_intelligence_tracking_mode (Tier 1)
5. get_screen_intelligence_metrics (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.vision.screen_intelligence_tracker import (
    screen_intelligence_tracker,
    TrackingMode,
)


# ==========================================
# 1. Capture Screen Intelligence Context (Tier 0)
# ==========================================

class CaptureScreenContextArgs(BaseModel):
    window_title_filter: Optional[str] = Field(
        None, description="Optional target window title to focus screen intelligence tracking upon."
    )


def preview_capture_screen_context(args: Dict[str, Any]) -> str:
    target = args.get("window_title_filter") or "Active Foreground Window"
    return f"Capture local screen visual context and detected UI elements for: '{target}'"


@registry.register(
    name="capture_screen_intelligence_context",
    tier=0,
    description="Captures active window context, coordinates, and detected UI bounding boxes locally without cloud egress (Tier 0 read-only).",
    args_schema=CaptureScreenContextArgs,
    preview_fn=preview_capture_screen_context,
    can_remember_per_folder=False,
)
def handle_capture_screen_intelligence_context(
    window_title_filter: Optional[str] = None,
) -> Dict[str, Any]:
    ctx = screen_intelligence_tracker.capture_window_context(window_title_filter=window_title_filter)
    return {
        "window_title": ctx.window_title,
        "process_name": ctx.process_name,
        "window_bounds": ctx.window_bounds,
        "elements_detected": [e.model_dump() for e in ctx.elements_detected],
        "capture_latency_ms": ctx.capture_latency_ms,
        "tracking_mode": ctx.tracking_mode.value,
        "timestamp": ctx.timestamp,
    }


# ==========================================
# 2. Extract Screen Region OCR (Tier 0)
# ==========================================

class ExtractRegionOcrArgs(BaseModel):
    bbox: Optional[Dict[str, int]] = Field(
        None, description="Optional bounding box dictionary with keys 'x', 'y', 'width', 'height'."
    )
    window_title: Optional[str] = Field(
        None, description="Optional target window title context."
    )


def preview_extract_region_ocr(args: Dict[str, Any]) -> str:
    bbox = args.get("bbox") or "Full Screen / Active Window"
    return f"Perform local OCR on screen coordinates {bbox} with Rule 11 credential scrubbing"


@registry.register(
    name="extract_screen_region_ocr",
    tier=0,
    description="Extracts on-screen text from specified screen coordinates or active window with automatic credential scrubbing (Tier 0 read-only).",
    args_schema=ExtractRegionOcrArgs,
    preview_fn=preview_extract_region_ocr,
    can_remember_per_folder=False,
)
def handle_extract_screen_region_ocr(
    bbox: Optional[Dict[str, int]] = None,
    window_title: Optional[str] = None,
) -> Dict[str, Any]:
    res = screen_intelligence_tracker.extract_region_ocr(bbox=bbox, window_title=window_title)
    return {
        "text": res.text,
        "word_count": res.word_count,
        "confidence": res.confidence,
        "scrubbed_secret_count": res.scrubbed_secret_count,
        "latency_ms": res.latency_ms,
        "timestamp": res.timestamp,
    }


# ==========================================
# 3. Diagnose On-Screen Errors (Tier 0)
# ==========================================

class DiagnoseErrorsArgs(BaseModel):
    simulated_screen_text: Optional[str] = Field(
        None, description="Optional text or OCR buffer to inspect for crash dialogs and error banners."
    )


def preview_diagnose_errors(args: Dict[str, Any]) -> str:
    return "Scan active screen regions and OCR output for crash dialogs, unhandled exceptions, and fatal error banners"


@registry.register(
    name="diagnose_on_screen_errors",
    tier=0,
    description="Scans on-screen visual regions for crash dialogs, error banners, and unhandled exceptions (Tier 0 read-only).",
    args_schema=DiagnoseErrorsArgs,
    preview_fn=preview_diagnose_errors,
    can_remember_per_folder=False,
)
def handle_diagnose_on_screen_errors(
    simulated_screen_text: Optional[str] = None,
) -> Dict[str, Any]:
    res = screen_intelligence_tracker.diagnose_on_screen_errors(simulated_screen_text=simulated_screen_text)
    return {
        "has_error_dialog": res.has_error_dialog,
        "error_title": res.error_title,
        "error_message": res.error_message,
        "severity": res.severity,
        "suggestions": res.suggestions,
        "detected_timestamp": res.detected_timestamp,
    }


# ==========================================
# 4. Set Screen Intelligence Tracking Mode (Tier 1)
# ==========================================

class SetTrackingModeArgs(BaseModel):
    mode: str = Field(
        ..., description="Desired tracking mode: 'OFF', 'ACTIVE', or 'LOW_POWER'."
    )


def preview_set_tracking_mode(args: Dict[str, Any]) -> str:
    mode = args.get("mode", "ACTIVE")
    return f"Update screen intelligence background tracking mode to '{mode}'"


@registry.register(
    name="set_screen_intelligence_tracking_mode",
    tier=1,
    description="Configures continuous background visual task tracking mode between OFF, ACTIVE, and LOW_POWER (Tier 1 reversible state change).",
    args_schema=SetTrackingModeArgs,
    preview_fn=preview_set_tracking_mode,
    can_remember_per_folder=False,
)
def handle_set_screen_intelligence_tracking_mode(
    mode: str,
) -> Dict[str, Any]:
    norm_mode = mode.upper().strip()
    valid_modes = [m.value for m in TrackingMode]
    if norm_mode not in valid_modes:
        raise ValueError(f"Invalid tracking mode: '{mode}'. Must be one of {valid_modes}")

    new_mode = screen_intelligence_tracker.set_tracking_mode(TrackingMode(norm_mode))
    return {
        "status": "UPDATED",
        "new_mode": new_mode.value,
    }


# ==========================================
# 5. Get Screen Intelligence Metrics (Tier 0)
# ==========================================

class GetTrackerMetricsArgs(BaseModel):
    pass


def preview_get_tracker_metrics(args: Dict[str, Any]) -> str:
    return "Query screen intelligence tracking metrics, OCR word counts, and error diagnosis stats"


@registry.register(
    name="get_screen_intelligence_metrics",
    tier=0,
    description="Returns aggregate tracking metrics, total captures, and diagnosed error counts (Tier 0 read-only).",
    args_schema=GetTrackerMetricsArgs,
    preview_fn=preview_get_tracker_metrics,
    can_remember_per_folder=False,
)
def handle_get_screen_intelligence_metrics() -> Dict[str, Any]:
    return screen_intelligence_tracker.get_tracker_metrics()
