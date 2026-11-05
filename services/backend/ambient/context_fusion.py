"""
Phenom In-RAM Unified Context Fusion Engine (CTX-01.2, CTX-01.4, SAF-02)
Maintains a rolling ring buffer of active desktop workspace context,
sanitizes credentials under Rule 11, enriches ambiguous user queries,
and halts tracking immediately on Guardian kill switch.
Zero disk I/O; strictly in-memory.
"""

import os
import sys
import time
import asyncio
from collections import deque
from typing import Dict, Any, List, Optional, Tuple, Callable, Awaitable
from pydantic import BaseModel, Field

from services.backend.ambient.multi_app_tracker import multi_app_tracker, AppWindowInfo
from services.backend.ambient.context_sanitizer import context_sanitizer
from services.backend.safety.guardian import guardian


class ContextItem(BaseModel):
    id: str = Field(..., description="Unique context event ID")
    timestamp: float = Field(..., description="Timestamp of context capture")
    source: str = Field(..., description="Context source: window_focus, active_document, user_query, tool_event")
    category: str = Field(default="other", description="App category (ide, browser, terminal, notes, communication)")
    summary: str = Field(..., description="Sanitized human-readable context snippet")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Structured window and process metadata")


_broadcaster: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None


def register_broadcaster(broadcaster: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
    """Registers WebSocket broadcast callback."""
    global _broadcaster
    _broadcaster = broadcaster


def broadcast_context_event(event_type: str, payload: Dict[str, Any]):
    """Broadcasts context stream events to connected Electron clients."""
    broadcaster = _broadcaster
    if not broadcaster:
        main_mod = sys.modules.get("services.backend.main")
        if main_mod and hasattr(main_mod, "broadcast_message"):
            broadcaster = main_mod.broadcast_message
    if not broadcaster:
        return
    msg = {
        "id": f"ctx-{os.urandom(2).hex()}",
        "type": event_type,
        "ts": str(time.time()),
        "payload": payload
    }
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcaster(msg))
    except RuntimeError:
        pass


class ContextFusionEngine:
    """
    In-memory context aggregator uniting multi-app window tracking with prompt enrichment.
    """

    def __init__(self, max_items: int = 50):
        self._ring_buffer: deque[ContextItem] = deque(maxlen=max_items)
        self._last_fg_hwnd: Optional[int] = None
        self._is_frozen: bool = False
        self._item_counter: int = 0

        # Guardian Kill Switch freeze hook (SAF-02 < 25ms SLA)
        guardian.add_state_callback(self._on_guardian_state_change)

    @property
    def is_frozen(self) -> bool:
        return self._is_frozen

    def update_context(self) -> Dict[str, Any]:
        """
        Samples active desktop windows, appends any changes to the ring buffer,
        and broadcasts live telemetry to the Cyber HUD.
        """
        if self._is_frozen:
            return {"status": "frozen", "message": "Context tracking frozen under Guardian kill switch."}

        windows = multi_app_tracker.enumerate_active_windows()
        fg_window = multi_app_tracker.get_foreground_window()

        if fg_window and fg_window.hwnd != self._last_fg_hwnd:
            self._last_fg_hwnd = fg_window.hwnd
            self._item_counter += 1

            summary = f"Focus switched to {fg_window.process_name}"
            if fg_window.active_document:
                summary += f" ({fg_window.active_document})"

            item = ContextItem(
                id=f"ctx-{self._item_counter}",
                timestamp=time.time(),
                source="window_focus",
                category=fg_window.category,
                summary=summary,
                metadata={
                    "hwnd": fg_window.hwnd,
                    "title": fg_window.title,
                    "process_name": fg_window.process_name,
                    "active_document": fg_window.active_document
                }
            )
            self._ring_buffer.append(item)
            self._broadcast_latest(fg_window, windows)

        return {
            "status": "success",
            "foreground_window": fg_window.model_dump() if fg_window else None,
            "total_windows": len(windows),
            "buffer_depth": len(self._ring_buffer)
        }

    def add_custom_context(self, source: str, summary: str, category: str = "other", metadata: Optional[Dict[str, Any]] = None):
        """Adds a sanitized custom context item into the in-RAM ring buffer."""
        if self._is_frozen:
            return

        clean_summary, _ = context_sanitizer.sanitize(summary)
        self._item_counter += 1
        item = ContextItem(
            id=f"ctx-{self._item_counter}",
            timestamp=time.time(),
            source=source,
            category=category,
            summary=clean_summary,
            metadata=metadata or {}
        )
        self._ring_buffer.append(item)

    def enrich_query(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Enriches ambiguous queries with foreground workspace context.
        Returns: (enriched_query_text, context_metadata)
        """
        fg_window = multi_app_tracker.get_foreground_window()
        context_meta: Dict[str, Any] = {
            "enriched": False,
            "foreground_app": fg_window.process_name if fg_window else None,
            "active_document": fg_window.active_document if fg_window else None,
            "category": fg_window.category if fg_window else "other"
        }

        if not fg_window:
            return query, context_meta

        q_lower = query.lower()
        ambiguous_triggers = [
            "this bug", "this error", "this code", "this function",
            "this file", "this page", "this document", "active window",
            "what am i looking at", "explain this", "summarize this", "fix this"
        ]

        if any(trigger in q_lower for trigger in ambiguous_triggers):
            context_meta["enriched"] = True
            annotation = f"[Active Workspace Context: {fg_window.category.upper()} - {fg_window.process_name}"
            if fg_window.active_document:
                annotation += f" ({fg_window.active_document})"
            annotation += f" | Window: {fg_window.title[:80]}]"

            enriched_query = f"{annotation}\n{query}"
            return enriched_query, context_meta

        return query, context_meta

    def clear_context(self) -> Dict[str, Any]:
        """Flushes the in-RAM context ring buffer."""
        count = len(self._ring_buffer)
        self._ring_buffer.clear()
        self._last_fg_hwnd = None
        broadcast_context_event("CONTEXT_STREAM_CLEARED", {
            "items_purged": count,
            "ts": time.time()
        })
        return {
            "status": "success",
            "message": f"Flushed {count} items from in-RAM context ring buffer."
        }

    def get_context_snapshot(self) -> Dict[str, Any]:
        """Returns structured active workspace context and recent stream."""
        fg = multi_app_tracker.get_foreground_window()
        windows = multi_app_tracker.enumerate_active_windows()
        return {
            "is_frozen": self._is_frozen,
            "foreground_window": fg.model_dump() if fg else None,
            "recent_stream": [item.model_dump() for item in list(self._ring_buffer)[-15:]],
            "open_apps_by_category": self._group_by_category(windows),
            "total_open_windows": len(windows)
        }

    def _group_by_category(self, windows: List[AppWindowInfo]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for w in windows:
            groups.setdefault(w.category, []).append(w.process_name)
        return {k: list(set(v)) for k, v in groups.items()}

    def _on_guardian_state_change(self, new_state: str):
        """Guardian freeze hook: halts context tracking in < 25ms SLA."""
        if new_state == "halted":
            self._is_frozen = True
            self._ring_buffer.clear()
            broadcast_context_event("CONTEXT_TRACKER_HALTED", {
                "frozen": True,
                "reason": "guardian_killswitch",
                "ts": time.time()
            })
        elif new_state == "idle":
            self._is_frozen = False
            self.update_context()

    def _broadcast_latest(self, fg: AppWindowInfo, windows: List[AppWindowInfo]):
        broadcast_context_event("CONTEXT_STREAM_UPDATED", {
            "foreground": fg.model_dump(),
            "recent_items": [item.model_dump() for item in list(self._ring_buffer)[-10:]],
            "categories": self._group_by_category(windows),
            "ts": time.time()
        })


context_fusion = ContextFusionEngine()
