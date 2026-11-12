"""Ambient Context Watchdog & Telegram Super-Companion Tools for Phenom (Milestone 30 Phase 4).

Registers 4 specialized tools in ToolRegistry:
1. trigger_ambient_context_nudge (Tier 1)
2. query_ambient_companion_status (Tier 0)
3. process_remote_companion_request (Tier 1)
4. search_remote_desktop_file (Tier 0)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.ambient.context_watchdog import context_watchdog
from services.backend.remote.telegram_super_companion import telegram_super_companion


# ==========================================
# 1. Trigger Ambient Context Nudge (Tier 1)
# ==========================================

class TriggerAmbientContextNudgeArgs(BaseModel):
    category: str = Field(..., description="Alert category: 'FOCUS', 'CALENDAR', 'MILESTONE', or 'SYSTEM'.")
    message: str = Field(..., description="Context notification text for desktop toast.")
    voice_phrase: Optional[str] = Field(None, description="Optional brief spoken reminder phrase.")


def preview_trigger_ambient_context_nudge(args: Dict[str, Any]) -> str:
    cat = args.get("category", "SYSTEM")
    msg = args.get("message", "")
    return f"Trigger ambient context alert [{cat}]: '{msg[:60]}...'"


@registry.register(
    name="trigger_ambient_context_nudge",
    tier=1,
    description="Emits a non-intrusive desktop toast notification and optional speech reminder (Tier 1 action).",
    args_schema=TriggerAmbientContextNudgeArgs,
    preview_fn=preview_trigger_ambient_context_nudge,
    can_remember_per_folder=False,
)
def handle_trigger_ambient_context_nudge(
    category: str,
    message: str,
    voice_phrase: Optional[str] = None,
) -> Dict[str, Any]:
    nudge = context_watchdog.trigger_manual_nudge(
        category=category,
        message=message,
        voice_phrase=voice_phrase,
    )
    return nudge.model_dump()


# ==========================================
# 2. Query Ambient Companion Status (Tier 0)
# ==========================================

class QueryAmbientCompanionStatusArgs(BaseModel):
    pass


def preview_query_ambient_companion_status(args: Dict[str, Any]) -> str:
    return "Query context watchdog status, focused application, and Telegram remote companion metrics"


@registry.register(
    name="query_ambient_companion_status",
    tier=0,
    description="Returns real-time status of context watchdog and Telegram mobile companion (Tier 0 read-only).",
    args_schema=QueryAmbientCompanionStatusArgs,
    preview_fn=preview_query_ambient_companion_status,
    can_remember_per_folder=False,
)
def handle_query_ambient_companion_status() -> Dict[str, Any]:
    watchdog_st = context_watchdog.get_status()
    companion_st = telegram_super_companion.get_status()
    return {
        "watchdog": watchdog_st,
        "companion": companion_st,
    }


# ==========================================
# 3. Process Remote Companion Request (Tier 1)
# ==========================================

class ProcessRemoteCompanionRequestArgs(BaseModel):
    audio_transcript: str = Field(..., description="Transcribed voice note or text message from remote companion.")
    user_id: Optional[str] = Field("primary_operator", description="Telegram user identifier.")


def preview_process_remote_companion_request(args: Dict[str, Any]) -> str:
    txt = args.get("audio_transcript", "")
    return f"Process remote Telegram companion command: '{txt[:60]}...'"


@registry.register(
    name="process_remote_companion_request",
    tier=1,
    description="Processes incoming remote voice notes or commands from Telegram and dispatches responses (Tier 1 action).",
    args_schema=ProcessRemoteCompanionRequestArgs,
    preview_fn=preview_process_remote_companion_request,
    can_remember_per_folder=False,
)
def handle_process_remote_companion_request(
    audio_transcript: str,
    user_id: str = "primary_operator",
) -> Dict[str, Any]:
    res = telegram_super_companion.process_voice_note(
        audio_transcript=audio_transcript,
        user_id=user_id,
    )
    return res.model_dump()


# ==========================================
# 4. Search Remote Desktop File (Tier 0)
# ==========================================

class SearchRemoteDesktopFileArgs(BaseModel):
    query: str = Field(..., description="File name substring or extension to search.")
    max_results: Optional[int] = Field(5, description="Maximum number of files to return.")


def preview_search_remote_desktop_file(args: Dict[str, Any]) -> str:
    q = args.get("query", "")
    return f"Search desktop workspace for files matching '{q}' with Rule 11 secret masking"


@registry.register(
    name="search_remote_desktop_file",
    tier=0,
    description="Searches authorized workspace folders for files with strict Rule 11 secret filtering (Tier 0 read-only).",
    args_schema=SearchRemoteDesktopFileArgs,
    preview_fn=preview_search_remote_desktop_file,
    can_remember_per_folder=False,
)
def handle_search_remote_desktop_file(
    query: str,
    max_results: int = 5,
) -> Dict[str, Any]:
    files = telegram_super_companion.search_desktop_files(
        query=query,
        max_results=max_results,
    )
    return {
        "query": query,
        "matched_count": len(files),
        "files": files,
    }
