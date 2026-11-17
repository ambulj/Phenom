"""Clipboard Content Classifier for Multimodal Data Ingestion (Milestone 51 Phase 3).

Classifies clipboard contents into CODE, JSON, TABULAR, STACK_TRACE, URL, or PLAIN_TEXT,
with AST validation for Python and syntax heuristics for TypeScript, SQL, and HTML.
"""

from __future__ import annotations

import ast
import json
import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClipboardContentType(str, Enum):
    """Categorical types of clipboard payloads."""
    CODE = "CODE"
    JSON_DATA = "JSON_DATA"
    TABULAR_DATA = "TABULAR_DATA"
    STACK_TRACE = "STACK_TRACE"
    URL = "URL"
    IMAGE = "IMAGE"
    PLAIN_TEXT = "PLAIN_TEXT"


class ClassifiedClipboardPayload(BaseModel):
    """Structured analysis of classified clipboard data."""
    content_type: ClipboardContentType
    sub_type: Optional[str] = Field(default=None, description="e.g. python, typescript, csv, markdown_table")
    is_valid_syntax: bool = True
    char_count: int = 0
    line_count: int = 0
    preview: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClipboardClassifier:
    """Classifies raw clipboard text into structured multimodal payloads."""

    URL_REGEX = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
    STACK_TRACE_PATTERNS = [
        re.compile(r"Traceback \(most recent call last\):"),
        re.compile(r'File ".*", line \d+, in '),
        re.compile(r"^\s+at\s+.*\(.*:\d+:\d+\)", re.MULTILINE),
        re.compile(r"Exception in thread \".*\" java\."),
        re.compile(r"Error:\s+.*at\s+.*:\d+:\d+"),
    ]

    @classmethod
    def classify(cls, text: str) -> ClassifiedClipboardPayload:
        """Analyzes text and returns structured classification metadata."""
        if not text:
            return ClassifiedClipboardPayload(
                content_type=ClipboardContentType.PLAIN_TEXT,
                char_count=0,
                line_count=0,
            )

        stripped = text.strip()
        lines = stripped.splitlines()
        line_count = len(lines)
        char_count = len(text)
        preview = stripped[:200]

        # 1. Check URL
        if cls.URL_REGEX.match(stripped):
            return ClassifiedClipboardPayload(
                content_type=ClipboardContentType.URL,
                sub_type="web_url",
                char_count=char_count,
                line_count=line_count,
                preview=preview,
            )

        # 2. Check JSON
        if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
            try:
                parsed = json.loads(stripped)
                is_dict = isinstance(parsed, dict)
                return ClassifiedClipboardPayload(
                    content_type=ClipboardContentType.JSON_DATA,
                    sub_type="json_object" if is_dict else "json_array",
                    is_valid_syntax=True,
                    char_count=char_count,
                    line_count=line_count,
                    preview=preview,
                    metadata={"keys_count": len(parsed) if is_dict else len(parsed)},
                )
            except Exception:
                pass

        # 3. Check Stack Trace / Error Dumps
        for pattern in cls.STACK_TRACE_PATTERNS:
            if pattern.search(stripped):
                return ClassifiedClipboardPayload(
                    content_type=ClipboardContentType.STACK_TRACE,
                    sub_type="python_traceback" if "Traceback" in stripped else "error_trace",
                    char_count=char_count,
                    line_count=line_count,
                    preview=preview,
                )

        # 4. Check Tabular Data (Markdown Table or CSV/TSV)
        if any(line.strip().startswith("|") and line.strip().endswith("|") for line in lines) and line_count >= 2:
            return ClassifiedClipboardPayload(
                content_type=ClipboardContentType.TABULAR_DATA,
                sub_type="markdown_table",
                char_count=char_count,
                line_count=line_count,
                preview=preview,
            )

        if line_count >= 2:
            comma_counts = [line.count(",") for line in lines[:5]]
            if len(comma_counts) > 1 and comma_counts[0] > 0 and all(c == comma_counts[0] for c in comma_counts):
                return ClassifiedClipboardPayload(
                    content_type=ClipboardContentType.TABULAR_DATA,
                    sub_type="csv",
                    char_count=char_count,
                    line_count=line_count,
                    preview=preview,
                    metadata={"columns": comma_counts[0] + 1},
                )

        # 5. Check Code
        # Python check via AST
        try:
            ast.parse(stripped)
            # Ensure it actually looks like Python code rather than trivial plain text
            has_py_cues = bool(re.search(r"\b(def|class|import|from|return|if|for|while|try|except|with|elif)\b", stripped))
            if has_py_cues or "=" in stripped or ":" in stripped:
                return ClassifiedClipboardPayload(
                    content_type=ClipboardContentType.CODE,
                    sub_type="python",
                    is_valid_syntax=True,
                    char_count=char_count,
                    line_count=line_count,
                    preview=preview,
                )
        except SyntaxError:
            pass

        # TypeScript / JavaScript heuristics
        ts_cues = re.search(r"\b(const|let|var|function|interface|type|export|import\s+.*\s+from|console\.log)\b", stripped)
        if ts_cues:
            return ClassifiedClipboardPayload(
                content_type=ClipboardContentType.CODE,
                sub_type="typescript",
                char_count=char_count,
                line_count=line_count,
                preview=preview,
            )

        # SQL heuristics
        sql_cues = re.search(r"(?i)\b(SELECT\s+.*\s+FROM|INSERT\s+INTO|CREATE\s+TABLE|UPDATE\s+.*\s+SET|DELETE\s+FROM)\b", stripped)
        if sql_cues:
            return ClassifiedClipboardPayload(
                content_type=ClipboardContentType.CODE,
                sub_type="sql",
                char_count=char_count,
                line_count=line_count,
                preview=preview,
            )

        # HTML / XML heuristics
        if re.search(r"<[a-zA-Z][^>]*>.*</[a-zA-Z]+>", stripped, re.DOTALL):
            return ClassifiedClipboardPayload(
                content_type=ClipboardContentType.CODE,
                sub_type="html_xml",
                char_count=char_count,
                line_count=line_count,
                preview=preview,
            )

        # Default fallback: plain text
        return ClassifiedClipboardPayload(
            content_type=ClipboardContentType.PLAIN_TEXT,
            sub_type="text",
            char_count=char_count,
            line_count=line_count,
            preview=preview,
        )
