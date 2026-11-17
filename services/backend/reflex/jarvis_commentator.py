"""Jarvis Persona Voice Commentator for Desktop Reflexes (Milestone 51 Phase 2).

Generates contextual, witty, concise spoken debriefs strictly constrained to <= 20 words,
matching Jarvis's refined, playful, and observant demeanor without disrupting the user.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from services.backend.schemas.reflex_events import ReflexEvent, ReflexEventType, ReflexSeverity


class JarvisCommentator:
    """Synthesizes witty, concise spoken commentary for desktop reflex events."""

    MAX_WORD_LIMIT = 20

    # Curated contextual voice response templates by event type and severity
    TEMPLATES: Dict[Tuple[ReflexEventType, ReflexSeverity], List[str]] = {
        (ReflexEventType.BUILD_FAILED, ReflexSeverity.CRITICAL): [
            "Build broke on line {line}, sir. Shall I patch the syntax?",
            "Your build tripped on {diagnostic}, sir. Ready to inspect.",
            "A slight hiccup in the compilation, sir. I have the error details staged.",
        ],
        (ReflexEventType.TESTS_FAILED, ReflexSeverity.CRITICAL): [
            "Test suite stumbled on {diagnostic}, sir. Want me to isolate the regression?",
            "A few tests failed to cooperate, sir. Standing by for diagnostics.",
        ],
        (ReflexEventType.TESTS_PASSED, ReflexSeverity.SUCCESS): [
            "All tests passed with flying colors, sir. Immaculate work.",
            "Test suite passed completely, sir. Ready when you are.",
            "All green across the board, sir. Crisp and clean.",
        ],
        (ReflexEventType.BUILD_SUCCEEDED, ReflexSeverity.SUCCESS): [
            "Compilation completed cleanly, sir. All artifacts assembled.",
            "Build succeeded without complaint, sir. Ready for launch.",
        ],
        (ReflexEventType.TERMINAL_COMPLETED, ReflexSeverity.SUCCESS): [
            "Terminal command completed with exit code zero, sir.",
            "Process wrapped up cleanly, sir. Output is waiting.",
        ],
        (ReflexEventType.TERMINAL_COMPLETED, ReflexSeverity.CRITICAL): [
            "Terminal command exited with code {exit_code}, sir. A quick review might be prudent.",
            "Process terminated abruptly with an error code, sir.",
        ],
        (ReflexEventType.ERROR_DIALOG, ReflexSeverity.CRITICAL): [
            "An unexpected error dialog just surfaced from {app_name}, sir.",
            "System alert from {app_name}, sir. Something went sideways.",
        ],
        (ReflexEventType.TOAST_NOTIFICATION, ReflexSeverity.WARNING): [
            "Incoming alert from {app_name}, sir. Might need a glance.",
            "Notification from {app_name}: {title}, sir.",
        ],
        (ReflexEventType.TOAST_NOTIFICATION, ReflexSeverity.INFO): [
            "New notification arrived from {app_name}, sir.",
        ],
    }

    @staticmethod
    def count_words(text: str) -> int:
        """Accurately counts words in string ignoring punctuation."""
        clean = re.sub(r"[^\w\s]", "", text)
        return len(clean.split())

    @classmethod
    def condense_text(cls, text: str, max_words: int = 20) -> str:
        """Condenses text to strictly adhere to the max words limit."""
        words = text.split()
        if len(words) <= max_words:
            return text

        # Truncate to max_words and ensure proper punctuation
        truncated = " ".join(words[:max_words])
        if not truncated.endswith((".", "!", "?")):
            truncated = re.sub(r"[,;:\s]+$", "", truncated) + "."
        return truncated

    def format_commentary(self, event: ReflexEvent) -> Tuple[str, int]:
        """Synthesizes voice text for an incoming ReflexEvent and returns (text, word_count).
        
        Guarantees word count <= 20 words.
        """
        key = (event.event_type, event.severity)
        template_list = self.TEMPLATES.get(key)

        # Fallback key check
        if not template_list:
            if event.is_failure:
                template_list = ["Something ran into an error, sir. Ready to take a look."]
            elif event.is_success:
                template_list = ["Process finished successfully, sir."]
            else:
                template_list = ["Desktop event noticed, sir."]

        template = template_list[0]

        # Extract interpolation parameters
        app_name = "Application"
        title = "Alert"
        diagnostic = "error"
        line = "unknown"
        exit_code = "1"

        if event.toast_details:
            app_name = event.toast_details.app_name or "System"
            title = event.toast_details.title or "Alert"

        if event.visual_details:
            app_name = event.visual_details.process_name or event.visual_details.window_title or "App"
            exit_code = str(event.visual_details.exit_code or 1)
            raw = event.visual_details.raw_text
            # Extract line number if present
            line_match = re.search(r"\((\d+)[,:]\d+\)|line (\d+)", raw, re.IGNORECASE)
            if line_match:
                line = line_match.group(1) or line_match.group(2)
            # Extract short diagnostic summary
            if "error TS" in raw:
                diagnostic = "TypeScript error"
            elif "SyntaxError" in raw:
                diagnostic = "SyntaxError"
            elif "ModuleNotFoundError" in raw:
                diagnostic = "missing module"
            elif "pytest" in raw or "passed" in raw:
                diagnostic = "test suite"

        # Interpolate
        try:
            rendered = template.format(
                app_name=app_name,
                title=title,
                diagnostic=diagnostic,
                line=line,
                exit_code=exit_code,
            )
        except Exception:
            rendered = template

        # Strictly enforce <= 20 words
        final_text = self.condense_text(rendered, max_words=self.MAX_WORD_LIMIT)
        word_count = self.count_words(final_text)

        # Double check invariant
        if word_count > self.MAX_WORD_LIMIT:
            words = final_text.split()[:self.MAX_WORD_LIMIT]
            final_text = " ".join(words).rstrip(",;:") + "."
            word_count = len(words)

        return final_text, word_count
