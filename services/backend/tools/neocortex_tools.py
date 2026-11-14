"""
NEURAL-NEOCORTEX Screen Vision Tools
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 2)

Registers:
1. query_neocortex_visual_state (Tier 0 read-only):
   Queries real-time visual telemetry, active window classification, and in-RAM buffer metrics.
2. set_neocortex_capture_mode (Tier 1 confirmation required):
   Configures screen capture mode (HYBRID_DIFF, CONTINUOUS, MANUAL) and target FPS.
3. audit_screen_privacy_mask (Tier 0 read-only):
   Evaluates a text block or window title against PII redactor and sensitive window shield.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.vision.neocortex_streamer import neocortex_streamer
from services.backend.vision.privacy_masker import privacy_masker
from services.backend.vision.screen_classifier import screen_classifier


# ==========================================
# 1. Query Neocortex Visual State (Tier 0)
# ==========================================

class QueryNeocortexVisualStateArgs(BaseModel):
    pass


def preview_query_neocortex_visual_state(args: Dict[str, Any]) -> str:
    return "Query real-time Neocortex screen vision telemetry, active window class, and in-RAM buffer metrics"


@registry.register(
    name="query_neocortex_visual_state",
    tier=0,
    description="Returns real-time visual telemetry, active window classification, frame diff rate, and privacy shielding status (Tier 0 read-only).",
    args_schema=QueryNeocortexVisualStateArgs,
    preview_fn=preview_query_neocortex_visual_state,
    can_remember_per_folder=False,
)
def handle_query_neocortex_visual_state() -> Dict[str, Any]:
    telem = neocortex_streamer.get_telemetry()
    classification = screen_classifier.classify_window(
        title=telem.active_window,
        process_name=telem.process_name,
    )
    return {
        "telemetry": telem.model_dump(),
        "classification": classification.model_dump(),
    }


# ==========================================
# 2. Set Neocortex Capture Mode (Tier 1)
# ==========================================

class SetNeocortexCaptureModeArgs(BaseModel):
    capture_mode: Optional[str] = Field(None, description="HYBRID_DIFF, CONTINUOUS, or MANUAL")
    target_fps: Optional[float] = Field(None, description="Target frame capture rate (1.0 to 15.0 FPS)")


def preview_set_neocortex_capture_mode(args: Dict[str, Any]) -> str:
    mode = args.get("capture_mode", "unchanged")
    fps = args.get("target_fps", "unchanged")
    return f"Configure visual capture mode={mode}, target_fps={fps}"


@registry.register(
    name="set_neocortex_capture_mode",
    tier=1,
    description="Configures visual capture mode (HYBRID_DIFF, CONTINUOUS, MANUAL) and frame rate (Tier 1).",
    args_schema=SetNeocortexCaptureModeArgs,
    preview_fn=preview_set_neocortex_capture_mode,
    can_remember_per_folder=False,
)
def handle_set_neocortex_capture_mode(
    capture_mode: Optional[str] = None,
    target_fps: Optional[float] = None,
) -> Dict[str, Any]:
    if capture_mode:
        neocortex_streamer._capture_mode = capture_mode.upper()
    if target_fps:
        neocortex_streamer.target_fps = max(1.0, min(15.0, float(target_fps)))
    return {
        "status": "success",
        "capture_mode": neocortex_streamer._capture_mode,
        "target_fps": neocortex_streamer.target_fps,
    }


# ==========================================
# 3. Audit Screen Privacy Mask (Tier 0)
# ==========================================

class AuditScreenPrivacyMaskArgs(BaseModel):
    text_sample: Optional[str] = Field(None, description="Sample text to test for automated PII and credential redaction")
    window_title: Optional[str] = Field(None, description="Window title to check against sensitive window blinding policy")
    process_name: Optional[str] = Field(None, description="Process executable name to check")


def preview_audit_screen_privacy_mask(args: Dict[str, Any]) -> str:
    return "Audit text sample or window title against automated PII redactor and sensitive window shield"


@registry.register(
    name="audit_screen_privacy_mask",
    tier=0,
    description="Tests text or window metadata against visual PII redaction and sensitive window blinding rules (Tier 0 read-only).",
    args_schema=AuditScreenPrivacyMaskArgs,
    preview_fn=preview_audit_screen_privacy_mask,
    can_remember_per_folder=False,
)
def handle_audit_screen_privacy_mask(
    text_sample: Optional[str] = None,
    window_title: Optional[str] = None,
    process_name: Optional[str] = None,
) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    if text_sample:
        masked, red_count = privacy_masker.mask_pii_text(text_sample)
        res["masked_text"] = masked
        res["redactions_count"] = red_count
        res["is_redacted"] = red_count > 0

    if window_title or process_name:
        tit = window_title or "Untitled"
        proc = process_name or "unknown.exe"
        is_sens = privacy_masker.is_sensitive_window(tit, proc)
        classification = screen_classifier.classify_window(tit, proc)
        res["is_sensitive"] = is_sens
        res["category"] = classification.category.value
        res["security_context"] = classification.detected_security_context

    return res
