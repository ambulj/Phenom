"""Stream Sanitizer & Execution Shield for Phenom (Milestone 29 Phase 1).

Parses streaming and completed LLM message outputs, stripping raw tool markers,
JSON execution blocks, action stamps, and PID/diagnostic dumps so user-visible chat
is clean, natural, and human-readable (STREAM-01.1, STREAM-01.2).
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian

logger = logging.getLogger("phenom.conversation.sanitizer")


class Rule8ViolationError(Exception):
    """Raised when stream content or tool execution involves payment or checkout operations."""
    pass


class ToolExecutionMetadata(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    execution_timestamp: float = Field(default_factory=time.time)
    raw_snippet: Optional[str] = None


class SanitizedStreamChunk(BaseModel):
    clean_text: str
    has_stripped_telemetry: bool
    extracted_tools: List[ToolExecutionMetadata] = Field(default_factory=list)
    chars_removed: int = 0


class StreamShieldMetrics(BaseModel):
    total_chunks_processed: int = 0
    total_characters_sanitized: int = 0
    total_tools_intercepted: int = 0
    leaks_blocked_count: int = 0


class StreamSanitizer:
    """Real-time streaming parser and execution noise shield."""

    _RULE_8_PATTERN = re.compile(
        r"(?:\b|_)(checkout|pay|payment|purchase|buy|order|credit.?card|cvv|billing)(?:\b|_)",
        re.IGNORECASE,
    )

    # Patterns for tool call signatures, JSON execution blocks, action stamps, and result payloads
    _TOOL_HEADER_PATTERN = re.compile(
        r"\*{1,2}\s*Tool\s*:\s*\*{1,2}\s*[`'\"]?([a-zA-Z0-9_\-\.]+)(?:\([^\)]*\))?[`'\"]?",
        re.IGNORECASE,
    )

    _JSON_EXECUTION_HEADER_PATTERN = re.compile(
        r"\*{1,2}\s*JSON\s+Execution\s+Block\s*:\s*\*{1,2}",
        re.IGNORECASE,
    )

    _CODE_FENCE_JSON_PATTERN = re.compile(
        r"```(?:json)?\s*(\{\s*[\"']tool[\"']\s*:\s*[\s\S]*?\})\s*```",
        re.IGNORECASE,
    )

    _RAW_TOOL_JSON_OBJECT_PATTERN = re.compile(
        r"\{\s*[\"']tool[\"']\s*:\s*[\"']([a-zA-Z0-9_\-\.]+)[\"']\s*,\s*[\"']args[\"']\s*:\s*(\{[^\}]*\})\s*\}",
        re.IGNORECASE,
    )

    _ACTION_EXECUTED_PATTERN = re.compile(
        r"\[Action\s+Executed\s*:\s*[^\]]+\]",
        re.IGNORECASE,
    )

    _TOOL_RESULT_PATTERN = re.compile(
        r"\[Tool\s+([a-zA-Z0-9_\-\.]+)\s+Result\s*:\s*([^\n\]]+|[\s\S]*?)\]",
        re.IGNORECASE,
    )

    _LAUNCH_EXPLANATION_PATTERN = re.compile(
        r"This command will launch the [^\n\.]+\.",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.metrics = StreamShieldMetrics()

    def check_safety(self, text: str) -> None:
        """Enforces Guardian kill switch and Rule 8 payment defenses."""
        if guardian.is_halted:
            raise RuntimeError("Execution halted by Guardian kill switch (STREAM_SANITIZER_HALTED)")

        if self._RULE_8_PATTERN.search(text):
            raise Rule8ViolationError(
                "Rule 8 Violation: Payment, checkout, or billing directives detected in stream"
            )

    def extract_tools(self, text: str) -> List[ToolExecutionMetadata]:
        """Extracts structured tool metadata from raw execution text."""
        tools: List[ToolExecutionMetadata] = []

        # Find raw tool JSON objects
        for match in self._RAW_TOOL_JSON_OBJECT_PATTERN.finditer(text):
            tool_name = match.group(1)
            args_str = match.group(2)
            try:
                args = json.loads(args_str)
            except Exception:
                args = {"raw": args_str}
            tools.append(
                ToolExecutionMetadata(
                    tool_name=tool_name,
                    arguments=args,
                    raw_snippet=match.group(0),
                )
            )

        # Find tool results
        for match in self._TOOL_RESULT_PATTERN.finditer(text):
            tool_name = match.group(1)
            result_str = match.group(2).strip()
            try:
                result = json.loads(result_str)
            except Exception:
                result = {"raw": result_str}
            # Match existing or append
            matched = False
            for t in tools:
                if t.tool_name == tool_name and t.result is None:
                    t.result = result
                    matched = True
                    break
            if not matched:
                tools.append(
                    ToolExecutionMetadata(
                        tool_name=tool_name,
                        result=result,
                        raw_snippet=match.group(0),
                    )
                )

        return tools

    def sanitize(self, raw_text: str) -> SanitizedStreamChunk:
        """Sanitizes raw LLM output, extracting tool metadata and purifying chat prose."""
        self.check_safety(raw_text)

        initial_len = len(raw_text)
        extracted_tools = self.extract_tools(raw_text)

        cleaned = raw_text

        # 1. Strip Tool headers
        cleaned = self._TOOL_HEADER_PATTERN.sub("", cleaned)

        # 2. Strip JSON Execution headers
        cleaned = self._JSON_EXECUTION_HEADER_PATTERN.sub("", cleaned)

        # 3. Strip fenced json code blocks containing tools
        cleaned = self._CODE_FENCE_JSON_PATTERN.sub("", cleaned)

        # 4. Strip raw tool JSON objects
        cleaned = self._RAW_TOOL_JSON_OBJECT_PATTERN.sub("", cleaned)

        # 5. Strip launch explanation boilerplates
        cleaned = self._LAUNCH_EXPLANATION_PATTERN.sub("", cleaned)

        # 6. Strip [Action Executed: ...] stamps
        cleaned = self._ACTION_EXECUTED_PATTERN.sub("", cleaned)

        # 7. Strip [Tool ... Result: ...] stamps
        cleaned = self._TOOL_RESULT_PATTERN.sub("", cleaned)

        # 8. Clean up stray empty code blocks or orphaned 'json' labels
        cleaned = re.sub(r"(?m)^\s*```(?:json)?\s*$", "", cleaned)
        cleaned = re.sub(r"(?m)^\s*json\s*$", "", cleaned)

        # 9. Clean up multiple blank lines and whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        # 10. Deduplicate trailing repeated phrases (e.g. repeated "All set." or "Done.")
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        deduped_lines: List[str] = []
        for line in lines:
            if not deduped_lines or line != deduped_lines[-1]:
                deduped_lines.append(line)
        cleaned = "\n\n".join(deduped_lines)

        chars_removed = initial_len - len(cleaned)
        has_stripped = chars_removed > 0

        # Update metrics
        self.metrics.total_chunks_processed += 1
        if has_stripped:
            self.metrics.total_characters_sanitized += chars_removed
            self.metrics.leaks_blocked_count += 1
        if extracted_tools:
            self.metrics.total_tools_intercepted += len(extracted_tools)

        return SanitizedStreamChunk(
            clean_text=cleaned,
            has_stripped_telemetry=has_stripped,
            extracted_tools=extracted_tools,
            chars_removed=chars_removed,
        )

    def get_metrics(self) -> StreamShieldMetrics:
        """Returns cumulative sanitization metrics."""
        return self.metrics

    def reset_metrics(self) -> None:
        """Resets stream metrics."""
        self.metrics = StreamShieldMetrics()


# Global singleton instance
stream_sanitizer = StreamSanitizer()
