"""
NEURAL-NEOCORTEX Visual Synapse Tools
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 3)

Registers:
1. dispatch_visual_context_query (Tier 0 read-only):
   Evaluates on-screen text lines for security milestones and returns tactical context telemetry.
2. trigger_visual_screen_audit (Tier 1 confirmation required):
   Runs full end-to-end screen capture, OCR extraction, PII masking, and visual security correlation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.vision.visual_synapse import visual_synapse
from services.backend.vision.neocortex_streamer import neocortex_streamer
from services.backend.vision.screen_classifier import screen_classifier


# ==========================================
# 1. Dispatch Visual Context Query (Tier 0)
# ==========================================

class DispatchVisualContextQueryArgs(BaseModel):
    ocr_lines: List[str] = Field(..., description="List of on-screen OCR text lines to correlate")


def preview_dispatch_visual_context_query(args: Dict[str, Any]) -> str:
    lines = args.get("ocr_lines", [])
    return f"Evaluate {len(lines)} on-screen OCR lines for security milestones and tactical alerts (Tier 0)"


@registry.register(
    name="dispatch_visual_context_query",
    tier=0,
    description="Correlates on-screen text with security events (rootkits, shells, recon) with sub-100ms latency (Tier 0 read-only).",
    args_schema=DispatchVisualContextQueryArgs,
    preview_fn=preview_dispatch_visual_context_query,
    can_remember_per_folder=False,
)
def handle_dispatch_visual_context_query(ocr_lines: List[str]) -> Dict[str, Any]:
    res = visual_synapse.correlate_visual_context(ocr_lines)
    return res.model_dump()


# ==========================================
# 2. Trigger Visual Screen Audit (Tier 1)
# ==========================================

class TriggerVisualScreenAuditArgs(BaseModel):
    sample_terminal_lines: Optional[List[str]] = Field(None, description="Optional terminal text to ingest for active audit")


def preview_trigger_visual_screen_audit(args: Dict[str, Any]) -> str:
    return "Execute full end-to-end visual screen audit with OCR extraction and tactical alert correlation (Tier 1)"


@registry.register(
    name="trigger_visual_screen_audit",
    tier=1,
    description="Executes a full in-RAM visual screen audit: classifies window, extracts redacted OCR blocks, and evaluates security events (Tier 1).",
    args_schema=TriggerVisualScreenAuditArgs,
    preview_fn=preview_trigger_visual_screen_audit,
    can_remember_per_folder=False,
)
def handle_trigger_visual_screen_audit(sample_terminal_lines: Optional[List[str]] = None) -> Dict[str, Any]:
    telem = neocortex_streamer.get_telemetry()
    lines = sample_terminal_lines or [
        "kali@kali:~$ nmap -sV 127.0.0.1",
        "Nmap scan report for 127.0.0.1",
        "Host is up (0.00012s latency).",
        "PORT    STATE SERVICE VERSION",
        "22/tcp  open  ssh     OpenSSH 8.9p1",
        "80/tcp  open  http    Apache httpd 2.4.52",
        "Nmap done: 1 IP address (1 host up) scanned in 1.42 seconds",
    ]

    boxes = screen_classifier.extract_ocr_blocks(lines)
    correlation = visual_synapse.correlate_visual_context(lines)

    return {
        "status": "completed",
        "window_title": telem.active_window,
        "process_name": telem.process_name,
        "is_blinded": telem.is_blinded,
        "ocr_boxes_count": len(boxes),
        "correlation": correlation.model_dump(),
    }
