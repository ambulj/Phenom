"""Persona & Stream Shield Tools for Phenom (Milestone 29 Phase 1).

Registers 3 conversation and execution-shield tools in ToolRegistry:
1. sanitize_chat_stream (Tier 0)
2. set_adaptive_persona_mode (Tier 1)
3. get_stream_shield_metrics (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.conversation.stream_sanitizer import (
    stream_sanitizer,
)
from services.backend.conversation.adaptive_persona import (
    adaptive_persona_engine,
    PersonaMode,
)


# ==========================================
# 1. Sanitize Chat Stream (Tier 0)
# ==========================================

class SanitizeChatStreamArgs(BaseModel):
    raw_text: str = Field(..., description="Raw LLM stream output or message containing potential tool syntax, JSON blocks, or PID noise.")


def preview_sanitize_chat_stream(args: Dict[str, Any]) -> str:
    text = args.get("raw_text", "")
    preview_snippet = (text[:60] + "...") if len(text) > 60 else text
    return f"Sanitize raw stream output and extract tool telemetry: '{preview_snippet}'"


@registry.register(
    name="sanitize_chat_stream",
    tier=0,
    description="Sanitizes raw LLM output by removing tool execution headers, raw JSON blocks, and PID noise, separating tool metadata from clean user-visible chat.",
    args_schema=SanitizeChatStreamArgs,
    preview_fn=preview_sanitize_chat_stream,
    can_remember_per_folder=False,
)
def handle_sanitize_chat_stream(
    raw_text: str,
) -> Dict[str, Any]:
    res = stream_sanitizer.sanitize(raw_text)
    return {
        "clean_text": res.clean_text,
        "has_stripped_telemetry": res.has_stripped_telemetry,
        "extracted_tools": [t.model_dump() for t in res.extracted_tools],
        "chars_removed": res.chars_removed,
    }


# ==========================================
# 2. Set Adaptive Persona Mode (Tier 1)
# ==========================================

class SetAdaptivePersonaModeArgs(BaseModel):
    mode: str = Field(
        ...,
        description="Persona mode to activate: 'SILENT_EXECUTION', 'MINIMAL_CONFIRMATION', 'CONVERSATIONAL_WITTY', or 'ADAPTIVE_AUTO'.",
    )


def preview_set_adaptive_persona_mode(args: Dict[str, Any]) -> str:
    mode = args.get("mode", "ADAPTIVE_AUTO")
    return f"Switch conversational persona mode to '{mode}'."


@registry.register(
    name="set_adaptive_persona_mode",
    tier=1,
    description="Configures the active conversational persona mode (SILENT_EXECUTION, MINIMAL_CONFIRMATION, CONVERSATIONAL_WITTY, ADAPTIVE_AUTO).",
    args_schema=SetAdaptivePersonaModeArgs,
    preview_fn=preview_set_adaptive_persona_mode,
    can_remember_per_folder=False,
)
def handle_set_adaptive_persona_mode(
    mode: str,
) -> Dict[str, Any]:
    mode_upper = mode.strip().upper()
    valid_modes = [m.value for m in PersonaMode]
    if mode_upper not in valid_modes:
        raise ValueError(f"Invalid persona mode '{mode}'. Expected one of: {valid_modes}")

    prev = adaptive_persona_engine.get_mode().value
    new_mode = PersonaMode(mode_upper)
    adaptive_persona_engine.set_mode(new_mode)

    return {
        "previous_mode": prev,
        "new_mode": new_mode.value,
        "status": "UPDATED",
    }


# ==========================================
# 3. Get Stream Shield Metrics (Tier 0)
# ==========================================

class GetStreamShieldMetricsArgs(BaseModel):
    pass


def preview_get_stream_shield_metrics(args: Dict[str, Any]) -> str:
    return "Retrieve cumulative chat stream sanitization and execution shield metrics."


@registry.register(
    name="get_stream_shield_metrics",
    tier=0,
    description="Returns telemetry metrics on blocked tool execution leaks, stripped characters, and current persona mode.",
    args_schema=GetStreamShieldMetricsArgs,
    preview_fn=preview_get_stream_shield_metrics,
    can_remember_per_folder=False,
)
def handle_get_stream_shield_metrics() -> Dict[str, Any]:
    metrics = stream_sanitizer.get_metrics()
    return {
        "total_chunks_processed": metrics.total_chunks_processed,
        "total_characters_sanitized": metrics.total_characters_sanitized,
        "total_tools_intercepted": metrics.total_tools_intercepted,
        "leaks_blocked_count": metrics.leaks_blocked_count,
        "current_persona_mode": adaptive_persona_engine.get_mode().value,
    }
