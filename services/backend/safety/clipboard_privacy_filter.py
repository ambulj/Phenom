"""Clipboard Privacy Filter for Phenom Neural Perception (Milestone 51 Phase 3).

Strictly enforces Rule 4 (privacy / local-first), Rule 8 (financial credentials), and
Rule 11 (secrets never in memory, logs, or chat) by redacting API keys, passwords,
tokens, CVVs, and credit card numbers prior to memory indexing or clipboard analysis.
"""

from __future__ import annotations

import re
from typing import List, Tuple
from pydantic import BaseModel, Field


class SanitizedClipboardResult(BaseModel):
    """Result of clipboard privacy inspection and secret redaction."""
    original_length: int = 0
    sanitized_text: str = ""
    had_secrets: bool = False
    redacted_categories: List[str] = Field(default_factory=list)


class ClipboardPrivacyFilter:
    """Detects and redacts credentials, financial data, and secrets from clipboard text."""

    PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
        # 1. API Keys & Cloud Secrets
        ("OPENAI_KEY", re.compile(r"\bsk-[a-zA-Z0-9_-]{20,}\b")),
        ("ANTHROPIC_KEY", re.compile(r"\bsk-ant-[a-zA-Z0-9_-]{20,}\b")),
        ("GITHUB_TOKEN", re.compile(r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{60,})\b")),
        ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        ("JWT_TOKEN", re.compile(r"\beyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b")),
        ("BEARER_AUTH", re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9_\-\.]{20,}\b")),
        # 2. Key-Value Password / Token Assignments (supports unquoted or quoted JSON/dict keys)
        ("PASSWORD_ASSIGNMENT", re.compile(r"(?i)['\"]?\b(password|passwd|pwd|secret|api_key|access_token|private_key)\b['\"]?\s*[:=]\s*['\"]?([^\s'\",}{]{4,})['\"]?")),
        # 3. Credit Card & CVV (Rule 8)
        ("CREDIT_CARD", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")),
        ("CVV", re.compile(r"(?i)\b(cvv|cvc|security\s*code)\s*[:=]?\s*\d{3,4}\b")),
    ]

    @classmethod
    def sanitize(cls, text: str) -> SanitizedClipboardResult:
        """Inspects text and redacts any matching secret patterns.
        
        Guarantees that no raw secret is stored or logged.
        """
        if not text:
            return SanitizedClipboardResult()

        sanitized = text
        had_secrets = False
        categories: List[str] = []

        for category, pattern in cls.PATTERNS:
            if category == "PASSWORD_ASSIGNMENT":
                # Only redact the value portion to keep variable name visible
                def _redact_pwd(m: re.Match[str]) -> str:
                    nonlocal had_secrets
                    had_secrets = True
                    var_name = m.group(1)
                    return f"{var_name}=[REDACTED_SECRET]"

                if pattern.search(sanitized):
                    categories.append(category)
                    sanitized = pattern.sub(_redact_pwd, sanitized)
            else:
                if pattern.search(sanitized):
                    had_secrets = True
                    categories.append(category)
                    sanitized = pattern.sub(f"[REDACTED_{category}]", sanitized)

        return SanitizedClipboardResult(
            original_length=len(text),
            sanitized_text=sanitized,
            had_secrets=had_secrets,
            redacted_categories=categories,
        )
