"""Adaptive Persona Engine for Phenom (Milestone 29 Phase 1).

Dynamically balances conversational personality with zero-noise desktop execution.
Supports SILENT_EXECUTION, MINIMAL_CONFIRMATION, CONVERSATIONAL_WITTY, and ADAPTIVE_AUTO modes
(PERSONA-02.1).
"""

from __future__ import annotations

from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.conversation.stream_sanitizer import Rule8ViolationError

logger = logging.getLogger("phenom.conversation.persona")


class PersonaMode(str, Enum):
    SILENT_EXECUTION = "SILENT_EXECUTION"
    MINIMAL_CONFIRMATION = "MINIMAL_CONFIRMATION"
    CONVERSATIONAL_WITTY = "CONVERSATIONAL_WITTY"
    ADAPTIVE_AUTO = "ADAPTIVE_AUTO"


class PersonaContext(BaseModel):
    user_prompt: str
    tool_name: Optional[str] = None
    target_name: Optional[str] = None
    is_desktop_action: bool = False
    intent_type: str = "query"  # "action", "query", "research", "system"


class FormattedResponse(BaseModel):
    formatted_text: str
    mode_applied: PersonaMode
    is_silent: bool
    tool_name: Optional[str] = None
    target_name: Optional[str] = None


class AdaptivePersonaEngine:
    """Intelligent response shaper adjusting verbosity according to task domain."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    # Tool names that represent immediate desktop actions where chattiness should be minimized
    _DESKTOP_ACTION_TOOLS = {
        "open_app",
        "close_app",
        "focus_window",
        "minimize_window",
        "maximize_window",
        "tile_windows",
        "set_volume",
        "mute_audio",
        "unmute_audio",
        "capture_screen",
        "copy_to_clipboard",
    }

    def __init__(self, default_mode: PersonaMode = PersonaMode.ADAPTIVE_AUTO) -> None:
        self.current_mode: PersonaMode = default_mode

    def check_safety(self, text: str) -> None:
        """Enforces Guardian kill switch and Rule 8 payment defenses."""
        if guardian.is_halted:
            raise RuntimeError("Execution halted by Guardian kill switch (ADAPTIVE_PERSONA_HALTED)")

        if self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                "Rule 8 Violation: Payment, checkout, or billing directives detected in persona context"
            )

    def set_mode(self, mode: PersonaMode) -> None:
        """Sets active persona mode."""
        self.current_mode = mode
        logger.info("Adaptive persona mode set to: %s", mode)

    def get_mode(self) -> PersonaMode:
        """Gets active persona mode."""
        return self.current_mode

    def format_action_response(
        self,
        tool_name: str,
        target_name: Optional[str] = None,
        user_prompt: Optional[str] = None,
        custom_msg: Optional[str] = None,
    ) -> FormattedResponse:
        """Formats the response for a completed tool action based on active persona mode."""
        check_text = f"{tool_name} {target_name or ''} {user_prompt or ''} {custom_msg or ''}"
        self.check_safety(check_text)

        target = target_name or "application"
        mode = self.current_mode

        if mode == PersonaMode.ADAPTIVE_AUTO:
            if tool_name in self._DESKTOP_ACTION_TOOLS:
                effective_mode = PersonaMode.MINIMAL_CONFIRMATION
            else:
                effective_mode = PersonaMode.CONVERSATIONAL_WITTY
        else:
            effective_mode = mode

        if effective_mode == PersonaMode.SILENT_EXECUTION:
            return FormattedResponse(
                formatted_text="",
                mode_applied=PersonaMode.SILENT_EXECUTION,
                is_silent=True,
                tool_name=tool_name,
                target_name=target_name,
            )

        if effective_mode == PersonaMode.MINIMAL_CONFIRMATION:
            if tool_name == "open_app":
                text = f"Opening {target}..."
            elif tool_name == "close_app":
                text = f"Closed {target}."
            elif "volume" in tool_name:
                text = f"Volume set to {target}."
            elif custom_msg:
                text = custom_msg.strip()
            else:
                text = "Done."

            return FormattedResponse(
                formatted_text=text,
                mode_applied=PersonaMode.MINIMAL_CONFIRMATION,
                is_silent=False,
                tool_name=tool_name,
                target_name=target_name,
            )

        # PersonaMode.CONVERSATIONAL_WITTY
        if tool_name == "open_app":
            text = f"Opening {target} for you, bro!"
        elif tool_name == "close_app":
            text = f"Closed {target}. Out of your way!"
        elif custom_msg:
            text = custom_msg.strip()
        else:
            text = f"All sorted, bro! Handled {tool_name} smoothly."

        return FormattedResponse(
            formatted_text=text,
            mode_applied=PersonaMode.CONVERSATIONAL_WITTY,
            is_silent=False,
            tool_name=tool_name,
            target_name=target_name,
        )

    def format_dialogue(self, raw_content: str, intent_type: str = "query") -> FormattedResponse:
        """Formats conversational dialogue or research output."""
        self.check_safety(raw_content)

        mode = self.current_mode
        if mode == PersonaMode.SILENT_EXECUTION and intent_type == "action":
            return FormattedResponse(
                formatted_text="",
                mode_applied=PersonaMode.SILENT_EXECUTION,
                is_silent=True,
            )

        return FormattedResponse(
            formatted_text=raw_content.strip(),
            mode_applied=mode,
            is_silent=False,
        )


# Global singleton instance
adaptive_persona_engine = AdaptivePersonaEngine()
